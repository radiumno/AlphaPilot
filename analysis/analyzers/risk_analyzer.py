"""风险分析器 — VaR、CVaR、回撤、波动率分析"""

from typing import Optional
import pandas as pd
import numpy as np
from analysis.models.risk import VaRResult, DrawdownInfo, RiskMetrics, PortfolioRiskResult


def calc_var_parametric(returns: pd.Series, confidence: float = 0.95) -> float:
    """参数法 VaR — 假设正态分布"""
    if len(returns) < 5:
        return 0.0
    z = {0.95: 1.645, 0.99: 2.326}.get(confidence, 1.645)
    return round(float(returns.std() * z * 100), 4)


def calc_var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """历史法 VaR — 经验分位数"""
    if len(returns) < 10:
        return 0.0
    return round(float(abs(returns.quantile(1 - confidence)) * 100), 4)


def calc_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """条件 VaR (CVaR / Expected Shortfall) — 尾部均值"""
    if len(returns) < 10:
        return 0.0
    threshold = returns.quantile(1 - confidence)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return 0.0
    return round(float(abs(tail.mean()) * 100), 4)


def calc_downside_volatility(returns: pd.Series) -> float:
    """下行波动率 — 仅考虑负收益"""
    negative = returns[returns < 0]
    if len(negative) < 2:
        return 0.0
    return round(float(negative.std() * np.sqrt(252) * 100), 4)


def analyze_drawdown(nav: pd.Series) -> DrawdownInfo:
    """分析回撤特征"""
    if len(nav) < 5:
        return DrawdownInfo()

    rolling_max = nav.expanding().max()
    drawdowns = (nav - rolling_max) / rolling_max
    mdd = abs(float(drawdowns.min()))

    current = abs(float(drawdowns.iloc[-1])) if len(drawdowns) > 0 else 0.0

    # 识别所有回撤期
    in_drawdown = drawdowns < -0.001  # 忽略微小回撤
    dd_days = int(in_drawdown.sum())

    # 平均回撤（排除零）
    non_zero = drawdowns[drawdowns < 0]
    avg_dd = float(abs(non_zero.mean())) if len(non_zero) > 0 else 0.0

    # 从最大回撤恢复的天数
    max_dd_idx = drawdowns.idxmin()
    recovery_days = 0
    if max_dd_idx != nav.index[-1]:
        recovery_series = nav.loc[max_dd_idx:]
        peak_after = recovery_series.expanding().max()
        recovered = peak_after >= rolling_max.loc[max_dd_idx]
        recovered_idx = recovered[recovered].index
        if len(recovered_idx) > 0 and recovered_idx[0] != max_dd_idx:
            recovery_days = len(nav.loc[max_dd_idx:recovered_idx[0]]) - 1

    return DrawdownInfo(
        max_drawdown=round(mdd * 100, 2),
        current_drawdown=round(current * 100, 2),
        avg_drawdown=round(avg_dd * 100, 2),
        drawdown_days=dd_days,
        recovery_days=recovery_days,
    )


def analyze_risk_single(
    symbol: str,
    name: str,
    nav: Optional[pd.Series] = None,
    benchmark_nav: Optional[pd.Series] = None,
    data_source: str = "",
) -> RiskMetrics:
    """分析单一资产的风险指标"""
    metrics = RiskMetrics(symbol=symbol, name=name, data_source=data_source)

    if nav is None or len(nav) < 10:
        return metrics

    returns = nav.pct_change().dropna()

    # 年化波动率
    metrics.volatility = round(float(returns.std() * np.sqrt(252) * 100), 4)
    metrics.downside_volatility = calc_downside_volatility(returns)

    # VaR / CVaR
    metrics.var = VaRResult(
        parametric_95=calc_var_parametric(returns, 0.95),
        parametric_99=calc_var_parametric(returns, 0.99),
        historical_95=calc_var_historical(returns, 0.95),
        historical_99=calc_var_historical(returns, 0.99),
        cvar_95=calc_cvar(returns, 0.95),
        cvar_99=calc_cvar(returns, 0.99),
    )

    # 回撤
    metrics.drawdown = analyze_drawdown(nav)

    # Beta / Alpha
    if benchmark_nav is not None and len(benchmark_nav) > 20:
        bench_returns = benchmark_nav.pct_change().dropna()
        common = returns.index.intersection(bench_returns.index)
        if len(common) > 20:
            r = returns.loc[common]
            b = bench_returns.loc[common]
            cov = np.cov(r, b)
            if cov[1, 1] != 0:
                metrics.beta = round(float(cov[0, 1] / cov[1, 1]), 4)
                rf_daily = 0.03 / 252
                metrics.alpha = round(
                    float((r.mean() - rf_daily - metrics.beta * (b.mean() - rf_daily)) * 252 * 100), 4
                )

    return metrics


def analyze_portfolio_risk(
    asset_navs: dict[str, pd.Series],
    asset_names: dict[str, str],
    weights: dict[str, float],
    benchmark_nav: Optional[pd.Series] = None,
    data_source: str = "",
) -> PortfolioRiskResult:
    """分析组合级风险

    参数:
        asset_navs: {symbol: nav_series}
        asset_names: {symbol: name}
        weights: {symbol: weight_in_portfolio (0-1)} 市值权重
        benchmark_nav: 基准净值序列
    """
    result = PortfolioRiskResult()

    # 逐一分析
    for symbol in asset_navs:
        metrics = analyze_risk_single(
            symbol=symbol,
            name=asset_names.get(symbol, symbol),
            nav=asset_navs[symbol],
            benchmark_nav=benchmark_nav,
            data_source=data_source,
        )
        result.asset_risks.append(metrics)

    # 组合波动率（需要完整的协方差矩阵）
    common_returns = None
    valid_symbols = []
    for symbol, nav in asset_navs.items():
        if len(nav) > 20:
            r = nav.pct_change().dropna()
            if common_returns is None:
                common_returns = pd.DataFrame({symbol: r})
                valid_symbols.append(symbol)
            else:
                common_returns[symbol] = r
                valid_symbols.append(symbol)

    if common_returns is not None and len(valid_symbols) > 1:
        common_returns = common_returns.dropna()
        if len(common_returns) > 10:
            w = np.array([weights.get(s, 0) for s in valid_symbols])
            w = w / w.sum()  # 归一化
            cov = common_returns.cov() * 252
            port_var = w @ cov.values @ w
            result.portfolio_volatility = round(float(np.sqrt(port_var) * 100), 4)

            # 组合 VaR (参数法)
            z95 = 1.645
            z99 = 2.326
            result.portfolio_var = VaRResult(
                parametric_95=round(float(z95 * np.sqrt(port_var) * 100), 4),
                parametric_99=round(float(z99 * np.sqrt(port_var) * 100), 4),
            )

            # 分散化比率 = 加权平均波动 / 组合波动
            weighted_avg_vol = sum(
                weights.get(s, 0) * (asset_navs[s].pct_change().dropna().std() * np.sqrt(252))
                for s in valid_symbols if s in asset_navs and len(asset_navs[s]) > 20
            )
            if result.portfolio_volatility > 0:
                result.diversification_ratio = round(float(weighted_avg_vol / (result.portfolio_volatility / 100)), 4)

    return result
