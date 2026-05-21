"""测试 ETF 分析器"""

import pandas as pd
import numpy as np
from analysis.analyzers.etf_analyzer import analyze_etf, calc_tracking_error, calc_concentration


def test_calc_tracking_error():
    """跟踪误差计算"""
    etf_returns = pd.Series([0.01, 0.02, -0.01, 0.015])
    index_returns = pd.Series([0.012, 0.019, -0.008, 0.016])
    te = calc_tracking_error(etf_returns, index_returns)
    assert te >= 0
    assert isinstance(te, float)


def test_calc_concentration():
    """HHI 集中度计算"""
    weights = [50.0, 30.0, 20.0]
    hhi = calc_concentration(weights)
    # HHI = 50^2 + 30^2 + 20^2 = 2500 + 900 + 400 = 3800
    assert hhi == 3800.0


def test_calc_concentration_single():
    """单一持仓 HHI = 10000"""
    assert calc_concentration([100.0]) == 10000.0


def test_calc_concentration_empty():
    assert calc_concentration([]) == 0.0
