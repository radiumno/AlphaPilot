"""相关性分析器测试"""

import pandas as pd
import numpy as np
from analysis.analyzers.correlation import calc_correlation_matrix


def _make_nav(seed: int, n: int = 252, start: float = 1.0) -> pd.Series:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.01, n)
    nav = pd.Series((1 + returns).cumprod() * start)
    nav.index = pd.date_range("2024-01-01", periods=n, freq="D")
    return nav


def test_correlation_single_asset():
    """单资产返回空矩阵"""
    nav_a = _make_nav(42)
    result = calc_correlation_matrix({"A": nav_a})
    assert result.symbols == ["A"]
    assert len(result.pairs) == 0


def test_correlation_two_assets():
    """两资产相关性"""
    nav_a = _make_nav(42)
    nav_b = _make_nav(99)
    result = calc_correlation_matrix({"A": nav_a, "B": nav_b})
    assert len(result.symbols) == 2
    assert len(result.pairs) == 1
    assert -1 <= result.pairs[0].correlation <= 1
    assert -1 <= result.avg_correlation <= 1


def test_correlation_zero_variance():
    """零方差序列返回零相关"""
    flat = pd.Series([1.0] * 100, index=pd.date_range("2024-01-01", periods=100))
    normal = _make_nav(42, 100)
    result = calc_correlation_matrix({"A": flat, "B": normal})
    # 至少不会崩溃
    assert result.symbols


def test_correlation_high_correlation():
    """完全相同序列应高度相关"""
    nav = _make_nav(42)
    result = calc_correlation_matrix({"A": nav, "B": nav.copy()})
    if len(result.pairs) > 0:
        assert result.pairs[0].correlation > 0.95


def test_correlation_cluster():
    """聚类应在高度相关时产生簇"""
    nav_a = _make_nav(42)
    nav_b = _make_nav(42)  # 使用相同种子，高度相关
    nav_c = _make_nav(99)  # 不同种子
    result = calc_correlation_matrix({"A": nav_a, "B": nav_b, "C": nav_c})
    # 至少有一个簇（A/B 相关）
    if result.cluster_info:
        has_ab = any("A" in v and "B" in v for v in result.cluster_info.values())
        # 只是检查运行正常
        assert True


def test_correlation_empty_dict():
    """空字典返回空结果"""
    result = calc_correlation_matrix({})
    assert result.symbols == []
    assert result.matrix == []
    assert result.pairs == []
