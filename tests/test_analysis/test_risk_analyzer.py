"""风险分析器测试"""

import pandas as pd
import numpy as np
from analysis.analyzers.risk_analyzer import (
    calc_var_parametric, calc_var_historical, calc_cvar,
    calc_downside_volatility, analyze_drawdown,
    analyze_risk_single, analyze_portfolio_risk,
)
from analysis.models.risk import VaRResult, DrawdownInfo, RiskMetrics, PortfolioRiskResult


def _make_returns(seed: int = 42, n: int = 252) -> pd.Series:
    """生成测试用收益率序列"""
    rng = np.random.default_rng(seed)
    # 均值 0.0005 (约年化 12.6%)，标准差 0.01 (约年化 16%)
    vals = rng.normal(0.0005, 0.01, n)
    return pd.Series(vals)


def _make_nav_from_returns(returns: pd.Series, start: float = 1.0) -> pd.Series:
    """从收益率序列生成净值"""
    nav = (1 + returns).cumprod() * start
    nav.index = pd.date_range("2024-01-01", periods=len(nav), freq="D")
    return nav


def test_var_parametric_basic():
    """参数法 VaR 基本计算"""
    returns = _make_returns(42, 1000)
    var95 = calc_var_parametric(returns, 0.95)
    var99 = calc_var_parametric(returns, 0.99)
    assert var95 >= 0  # VaR 应为正数
    assert var99 > var95  # 99% VaR > 95% VaR


def test_var_parametric_short_series():
    """短序列返回 0"""
    assert calc_var_parametric(pd.Series([0.01, 0.02, 0.03]), 0.95) == 0.0


def test_var_historical_basic():
    """历史法 VaR 基本计算"""
    returns = _make_returns(42, 1000)
    var95 = calc_var_historical(returns, 0.95)
    var99 = calc_var_historical(returns, 0.99)
    assert var95 >= 0
    assert var99 >= var95


def test_cvar_basic():
    """CVaR 基本计算"""
    returns = _make_returns(42, 1000)
    cvar95 = calc_cvar(returns, 0.95)
    cvar99 = calc_cvar(returns, 0.99)
    assert cvar95 >= 0
    assert cvar99 >= cvar95


def test_downside_volatility():
    """下行波动率计算"""
    # 全部为正收益 → 下行波动为 0
    positive = pd.Series([0.01, 0.02, 0.015, 0.03])
    assert calc_downside_volatility(positive) == 0.0

    # 混合收益
    mixed = pd.Series([0.01, -0.02, 0.015, -0.01, -0.03, 0.02])
    dv = calc_downside_volatility(mixed)
    assert dv > 0


def test_analyze_drawdown_basic():
    """回撤分析基本功能"""
    nav = pd.Series([1.0, 1.1, 1.2, 1.15, 1.05, 1.1, 1.2], index=pd.date_range("2024-01-01", periods=7))
    dd = analyze_drawdown(nav)
    assert dd.max_drawdown > 0
    assert dd.drawdown_days >= 0


def test_analyze_drawdown_flat():
    """平坦净值无回撤"""
    nav = pd.Series([1.0] * 10, index=pd.date_range("2024-01-01", periods=10))
    dd = analyze_drawdown(nav)
    assert dd.max_drawdown == 0.0


def test_analyze_risk_single_basic():
    """单资产风险分析"""
    returns = _make_returns(42, 500)
    nav = _make_nav_from_returns(returns)
    metrics = analyze_risk_single("TEST", "测试资产", nav)
    assert metrics.symbol == "TEST"
    assert metrics.volatility > 0
    assert metrics.var.historical_95 > 0
    assert metrics.var.parametric_95 > 0


def test_analyze_risk_single_with_benchmark():
    """含基准的风险分析"""
    returns = _make_returns(42, 500)
    bench_returns = _make_returns(99, 500)
    nav = _make_nav_from_returns(returns)
    bench_nav = _make_nav_from_returns(bench_returns)
    metrics = analyze_risk_single("TEST", "测试资产", nav, bench_nav)
    assert metrics.beta is not None


def test_analyze_risk_single_no_data():
    """无数据时返回默认值"""
    metrics = analyze_risk_single("TEST", "测试资产")
    assert metrics.volatility == 0.0
    assert metrics.var.parametric_95 == 0.0


def test_analyze_portfolio_risk_single_asset():
    """单资产组合风险"""
    returns = _make_returns(42, 252)
    nav = _make_nav_from_returns(returns)
    result = analyze_portfolio_risk(
        {"A": nav}, {"A": "资产A"}, {"A": 1.0}
    )
    assert len(result.asset_risks) == 1
    assert result.asset_risks[0].volatility > 0


def test_analyze_portfolio_risk_multi_asset():
    """多资产组合风险"""
    navs = {}
    for i, seed in enumerate([42, 99, 123]):
        r = _make_returns(seed, 252)
        navs[chr(65 + i)] = _make_nav_from_returns(r)

    names = {"A": "资产A", "B": "资产B", "C": "资产C"}
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    result = analyze_portfolio_risk(navs, names, weights)
    assert len(result.asset_risks) == 3
    # 多资产应有组合波动率
    assert result.portfolio_volatility is not None and result.portfolio_volatility > 0
