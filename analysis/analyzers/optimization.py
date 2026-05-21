"""投资组合优化 — 均值-方差优化、风险平价、有效前沿"""

from typing import Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class OptimizationResult(BaseModel):
    """优化结果"""
    method: str = Field(description="优化方法: max_sharpe / min_vol / risk_parity")
    weights: dict[str, float] = Field(default_factory=dict, description="{symbol: weight}")
    expected_return: float = Field(default=0.0, description="预期年化收益(%)")
    expected_volatility: float = Field(default=0.0, description="预期年化波动率(%)")
    sharpe_ratio: float = Field(default=0.0, description="夏普比率")
    diversification_ratio: float = Field(default=0.0, description="分散化比率")


class EfficientFrontierPoint(BaseModel):
    """有效前沿上的一个点"""
    volatility: float
    return_val: float
    sharpe: float
    weights: dict[str, float]


class PortfolioOptimizationResult(BaseModel):
    """完整优化结果"""
    current: OptimizationResult = Field(description="当前组合")
    max_sharpe: Optional[OptimizationResult] = Field(default=None, description="最大夏普组合")
    min_vol: Optional[OptimizationResult] = Field(default=None, description="最小波动组合")
    risk_parity: Optional[OptimizationResult] = Field(default=None, description="风险平价组合")
    efficient_frontier: list[EfficientFrontierPoint] = Field(default_factory=list)
    improvement_potential: float = Field(default=0.0, description="夏普比率提升空间(%)")


def _ensure_positive_definite(cov: np.ndarray) -> np.ndarray:
    """将协方差矩阵修正为半正定（防止数值误差）"""
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.maximum(eigvals, 1e-8)
    return eigvecs @ np.diag(eigvals) @ eigvecs.T


def optimize_max_sharpe(
    returns: pd.DataFrame,
    cov: Optional[np.ndarray] = None,
    risk_free_rate: float = 0.03,
    weight_bounds: tuple[float, float] = (0.0, 1.0),
) -> OptimizationResult:
    """最大化夏普比率 — 解析解（考虑做空限制时使用数值优化）"""
    from scipy.optimize import minimize

    if cov is None:
        cov = returns.cov().values * 252
    cov = _ensure_positive_definite(cov)

    n = returns.shape[1]
    mean_returns = returns.mean().values * 252

    # 目标：负夏普最小化
    def neg_sharpe(w):
        w = np.array(w)
        port_ret = w @ mean_returns
        port_vol = np.sqrt(w @ cov @ w)
        if port_vol < 1e-10:
            return 1e10
        rf = risk_free_rate
        return -(port_ret - rf) / port_vol

    # 约束：权重和为1
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [weight_bounds] * n

    # 多次初始点尝试避免局部最优
    best_result = None
    best_sharpe = -1e10
    for seed in [np.ones(n) / n, None]:
        init = seed if seed is not None else np.random.dirichlet(np.ones(n))
        result = minimize(neg_sharpe, init, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-12})
        if result.success:
            w = result.x / result.x.sum()
            port_ret = w @ mean_returns
            port_vol = np.sqrt(w @ cov @ w)
            sharpe = (port_ret - risk_free_rate) / max(port_vol, 1e-10)
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_result = result

    if best_result is None:
        return OptimizationResult(
            method="max_sharpe",
            weights={returns.columns[i]: 1.0 / n for i in range(n)},
        )

    w = best_result.x / best_result.x.sum()
    port_ret = w @ mean_returns
    port_vol = np.sqrt(w @ cov @ w)
    sharpe = (port_ret - risk_free_rate) / max(port_vol, 1e-10)

    # 分散化比率
    weighted_avg_vol = sum(w[i] * np.sqrt(cov[i, i]) for i in range(n))
    div_ratio = weighted_avg_vol / max(port_vol, 1e-10)

    return OptimizationResult(
        method="max_sharpe",
        weights={returns.columns[i]: round(float(w[i]), 4) for i in range(n)},
        expected_return=round(float(port_ret * 100), 4),
        expected_volatility=round(float(port_vol * 100), 4),
        sharpe_ratio=round(float(sharpe), 4),
        diversification_ratio=round(float(div_ratio), 4),
    )


def optimize_min_volatility(
    returns: pd.DataFrame,
    cov: Optional[np.ndarray] = None,
    weight_bounds: tuple[float, float] = (0.0, 1.0),
) -> OptimizationResult:
    """最小化组合波动率"""
    from scipy.optimize import minimize

    if cov is None:
        cov = returns.cov().values * 252
    cov = _ensure_positive_definite(cov)

    n = returns.shape[1]
    mean_returns = returns.mean().values * 252

    def portfolio_vol(w):
        return np.sqrt(w @ cov @ w)

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [weight_bounds] * n

    best_result = None
    best_vol = 1e10
    for seed in [np.ones(n) / n, None]:
        init = seed if seed is not None else np.random.dirichlet(np.ones(n))
        result = minimize(portfolio_vol, init, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-12})
        if result.success and result.fun < best_vol:
            best_vol = result.fun
            best_result = result

    if best_result is None:
        return OptimizationResult(
            method="min_vol",
            weights={returns.columns[i]: 1.0 / n for i in range(n)},
        )

    w = best_result.x / best_result.x.sum()
    port_vol = w @ cov @ w
    port_ret = w @ mean_returns

    weighted_avg_vol = sum(w[i] * np.sqrt(cov[i, i]) for i in range(n))
    div_ratio = weighted_avg_vol / max(np.sqrt(port_vol), 1e-10)

    return OptimizationResult(
        method="min_vol",
        weights={returns.columns[i]: round(float(w[i]), 4) for i in range(n)},
        expected_return=round(float(port_ret * 100), 4),
        expected_volatility=round(float(np.sqrt(port_vol) * 100), 4),
        sharpe_ratio=round(float((port_ret - 0.03) / max(np.sqrt(port_vol), 1e-10)), 4),
        diversification_ratio=round(float(div_ratio), 4),
    )


def risk_parity_weights(cov: np.ndarray, symbols: list[str]) -> OptimizationResult:
    """风险平价 — 每个资产贡献相等的组合风险"""
    from scipy.optimize import minimize

    cov = _ensure_positive_definite(cov)
    n = cov.shape[0]

    def risk_contribution(w):
        w = np.array(w)
        port_var = w @ cov @ w
        marginal_risk = cov @ w
        rc = w * marginal_risk
        return rc / max(port_var, 1e-10)

    def risk_parity_objective(w):
        rc = risk_contribution(w)
        target = 1.0 / n
        return sum((rc[i] - target) ** 2 for i in range(n))

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [(0.0, 1.0)] * n

    best_result = None
    best_obj = 1e10
    for seed in [np.ones(n) / n, None]:
        init = seed if seed is not None else np.random.dirichlet(np.ones(n))
        result = minimize(risk_parity_objective, init, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-12})
        if result.success and result.fun < best_obj:
            best_obj = result.fun
            best_result = result

    if best_result is None:
        return OptimizationResult(
            method="risk_parity",
            weights={symbols[i]: 1.0 / n for i in range(n)},
        )

    w = best_result.x / best_result.x.sum()
    port_vol = np.sqrt(w @ cov @ w)
    weighted_avg_vol = sum(w[i] * np.sqrt(cov[i, i]) for i in range(n))
    div_ratio = weighted_avg_vol / max(port_vol, 1e-10)

    return OptimizationResult(
        method="risk_parity",
        weights={symbols[i]: round(float(w[i]), 4) for i in range(n)},
        expected_return=0.0,
        expected_volatility=round(float(port_vol * 100), 4),
        diversification_ratio=round(float(div_ratio), 4),
    )


def compute_efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 20,
) -> list[EfficientFrontierPoint]:
    """计算有效前沿"""
    from scipy.optimize import minimize

    cov = returns.cov().values * 252
    cov = _ensure_positive_definite(cov)
    mean_returns = returns.mean().values * 252
    n = returns.shape[1]

    # 先找到最小波动和最大收益组合
    min_vol, max_ret = 1e10, -1e10
    for _ in range(50):
        w = np.random.dirichlet(np.ones(n))
        vol = np.sqrt(w @ cov @ w)
        ret = w @ mean_returns
        min_vol = min(min_vol, vol)
        max_ret = max(max_ret, ret)

    target_returns = np.linspace(min_vol * 2, max_ret * 0.95, n_points)
    frontier = []

    def portfolio_vol(w):
        return np.sqrt(w @ cov @ w)

    constraints_base = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [(0.0, 1.0)] * n

    for target in target_returns:
        constraints = constraints_base + [
            {"type": "eq", "fun": lambda w, t=target: w @ mean_returns - t}
        ]
        result = minimize(portfolio_vol, np.ones(n) / n, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-12})
        if result.success:
            w = result.x / result.x.sum()
            vol = np.sqrt(w @ cov @ w)
            ret = w @ mean_returns
            sharpe = (ret - 0.03) / max(vol, 1e-10)
            frontier.append(EfficientFrontierPoint(
                volatility=round(float(vol * 100), 4),
                return_val=round(float(ret * 100), 4),
                sharpe=round(float(sharpe), 4),
                weights={returns.columns[i]: round(float(w[i]), 4) for i in range(n)},
            ))

    return frontier


def compute_current_portfolio(
    weights: dict[str, float],
    returns: pd.DataFrame,
) -> OptimizationResult:
    """计算当前组合的风险收益特征"""
    cov = returns.cov().values * 252
    symbols = list(weights.keys())
    n = len(symbols)

    w = np.array([weights.get(s, 0) for s in returns.columns[:n]])
    w = w / max(w.sum(), 1e-10)

    if len(w) != returns.shape[1]:
        return OptimizationResult(method="current", weights=weights)

    mean_returns = returns.mean().values * 252
    port_ret = w @ mean_returns
    port_vol = np.sqrt(w @ cov @ w)
    sharpe = (port_ret - 0.03) / max(port_vol, 1e-10)

    weighted_avg_vol = sum(w[i] * np.sqrt(cov[i, i]) for i in range(len(w)))
    div_ratio = weighted_avg_vol / max(port_vol, 1e-10)

    return OptimizationResult(
        method="current",
        weights=weights,
        expected_return=round(float(port_ret * 100), 4),
        expected_volatility=round(float(port_vol * 100), 4),
        sharpe_ratio=round(float(sharpe), 4),
        diversification_ratio=round(float(div_ratio), 4),
    )


def full_portfolio_optimization(
    weights: dict[str, float],
    returns: pd.DataFrame,
    risk_free_rate: float = 0.03,
) -> PortfolioOptimizationResult:
    """一站式组合优化：当前组合 + 最大夏普 + 最小波动 + 风险平价 + 有效前沿"""
    if returns.shape[1] < 2:
        return PortfolioOptimizationResult(
            current=compute_current_portfolio(weights, returns),
        )

    current = compute_current_portfolio(weights, returns)
    max_sharpe = optimize_max_sharpe(returns, risk_free_rate=risk_free_rate)
    min_vol = optimize_min_volatility(returns)
    cov = returns.cov().values * 252
    rp = risk_parity_weights(cov, list(returns.columns))
    frontier = compute_efficient_frontier(returns)

    improvement = 0.0
    if current.sharpe_ratio > 0 and max_sharpe.sharpe_ratio > 0:
        improvement = (max_sharpe.sharpe_ratio - current.sharpe_ratio) / current.sharpe_ratio * 100

    return PortfolioOptimizationResult(
        current=current,
        max_sharpe=max_sharpe,
        min_vol=min_vol,
        risk_parity=rp,
        efficient_frontier=frontier,
        improvement_potential=round(float(improvement), 2),
    )
