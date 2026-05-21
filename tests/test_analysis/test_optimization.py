"""投资组合优化测试"""

import pandas as pd
import numpy as np
from analysis.analyzers.optimization import (
    optimize_max_sharpe, optimize_min_volatility, risk_parity_weights,
    compute_current_portfolio, full_portfolio_optimization,
    OptimizationResult, PortfolioOptimizationResult,
)


def _make_returns(n_assets=3, n_days=252) -> pd.DataFrame:
    """生成模拟日收益率"""
    np.random.seed(42)
    data = {}
    for i in range(n_assets):
        r = np.random.normal(0.0005, 0.01, n_days)
        data[f"ASSET_{i}"] = r
    return pd.DataFrame(data)


def test_optimization_result_model():
    """OptimizationResult 数据模型"""
    r = OptimizationResult(
        method="max_sharpe",
        weights={"A": 0.6, "B": 0.4},
        expected_return=12.0,
        expected_volatility=15.0,
        sharpe_ratio=0.6,
    )
    assert r.method == "max_sharpe"
    assert r.weights["A"] == 0.6
    assert r.sharpe_ratio == 0.6


def test_optimize_max_sharpe():
    """最大夏普优化返回有效权重"""
    returns = _make_returns()
    result = optimize_max_sharpe(returns)
    assert result.method == "max_sharpe"
    assert len(result.weights) == 3
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 0.01


def test_optimize_min_vol():
    """最小波动优化"""
    returns = _make_returns()
    result = optimize_min_volatility(returns)
    assert result.method == "min_vol"
    assert len(result.weights) == 3


def test_risk_parity():
    """风险平价权重"""
    returns = _make_returns()
    cov = returns.cov().values * 252
    result = risk_parity_weights(cov, list(returns.columns))
    assert result.method == "risk_parity"
    total = sum(result.weights.values())
    assert abs(total - 1.0) < 0.01


def test_current_portfolio():
    """当前组合特征计算"""
    returns = _make_returns()
    weights = {"ASSET_0": 0.5, "ASSET_1": 0.3, "ASSET_2": 0.2}
    result = compute_current_portfolio(weights, returns)
    assert result.method == "current"
    assert result.expected_volatility > 0


def test_full_optimization():
    """一站式优化"""
    returns = _make_returns()
    weights = {"ASSET_0": 0.5, "ASSET_1": 0.3, "ASSET_2": 0.2}
    result = full_portfolio_optimization(weights, returns)
    assert isinstance(result, PortfolioOptimizationResult)
    assert result.current is not None
    assert result.max_sharpe is not None
    assert result.min_vol is not None
    assert result.risk_parity is not None


def test_full_optimization_single_asset():
    """单一资产优化返回基础结果"""
    returns = _make_returns(1)
    weights = {"ASSET_0": 1.0}
    result = full_portfolio_optimization(weights, returns)
    assert result.max_sharpe is None


def test_portfolio_optimization_result_model():
    """PortfolioOptimizationResult 模型"""
    r = PortfolioOptimizationResult(
        current=OptimizationResult(method="current", weights={"A": 1.0}),
    )
    assert r.current.method == "current"
    assert r.improvement_potential == 0.0
