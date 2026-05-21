"""测试主动基金分析器"""

import pandas as pd
from analysis.analyzers.fund_analyzer import analyze_fund, calc_sharpe_ratio, calc_max_drawdown


def test_calc_sharpe_ratio():
    returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005])
    sharpe = calc_sharpe_ratio(returns, risk_free=0.03)
    assert isinstance(sharpe, float)


def test_calc_max_drawdown():
    nav = pd.Series([1.0, 1.1, 1.05, 1.2, 1.15, 1.25])
    mdd = calc_max_drawdown(nav)
    assert mdd > 0
    # 滚动最大回撤计算：
    #   峰值=1.1, 谷值=1.05 => (1.05-1.1)/1.1 = -4.55%
    #   峰值=1.2, 谷值=1.15 => (1.15-1.2)/1.2 = -4.17%
    # 最大回撤为 4.55%（从 1.1 到 1.05）
    assert round(mdd, 2) == 4.55


def test_calc_max_drawdown_flat():
    nav = pd.Series([1.0, 1.0, 1.0])
    assert calc_max_drawdown(nav) == 0.0
