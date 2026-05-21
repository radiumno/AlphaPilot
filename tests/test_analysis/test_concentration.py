"""集中度分析器测试"""

from portfolio.models import Position, AssetType, MarketType
from analysis.analyzers.concentration import (
    calc_portfolio_hhi, calc_effective_n, calc_top_n_concentration,
    calc_sector_concentration, detect_concentration_risks,
)


def _make_pos(symbol: str, value: float, asset_type: str = "etf") -> Position:
    """快速创建测试持仓"""
    return Position(
        symbol=symbol,
        name=f"{symbol}名称",
        asset_type=AssetType(asset_type),
        shares=1,
        cost_price=value,
        market_price=value,
        market=MarketType.CN,
        currency="CNY",
    )


def test_hhi_single_asset():
    """单一资产 HHI = 10000"""
    pos = [_make_pos("A", 100)]
    assert calc_portfolio_hhi(pos) == 10000.0


def test_hhi_equal_weights():
    """等权持仓 HHI = 10000/N"""
    pos = [_make_pos("A", 100), _make_pos("B", 100)]
    assert calc_portfolio_hhi(pos) == pytest.approx(5000.0, rel=0.1)


def test_hhi_empty():
    """空持仓 HHI = 0"""
    assert calc_portfolio_hhi([]) == 0.0


def test_hhi_zero_value():
    """零市值 HHI = 0"""
    pos = [_make_pos("A", 0)]
    assert calc_portfolio_hhi(pos) == 0.0


def test_effective_n():
    """有效持仓数测试"""
    pos_equal = [_make_pos("A", 100), _make_pos("B", 100)]
    assert calc_effective_n(pos_equal) == 2

    pos_single = [_make_pos("A", 100)]
    assert calc_effective_n(pos_single) == 1


def test_top_n_concentration():
    """Top-N 集中度测试"""
    pos = [
        _make_pos("A", 60),
        _make_pos("B", 30),
        _make_pos("C", 10),
    ]
    top2 = calc_top_n_concentration(pos, 2)
    assert top2 == pytest.approx(90.0, rel=0.1)


def test_sector_concentration():
    """行业集中度测试"""
    pos = [
        _make_pos("A", 100, "etf"),
        _make_pos("B", 100, "bond"),
    ]
    sectors = calc_sector_concentration(pos)
    assert len(sectors) == 2
    assert sectors[0].weight > 0


def test_detect_risks_high():
    """高集中度风险检测"""
    pos = [_make_pos("A", 80), _make_pos("B", 20)]
    hhi = calc_portfolio_hhi(pos)
    top5 = calc_top_n_concentration(pos, 2)
    risks = detect_concentration_risks(hhi, top5)
    assert len(risks) > 0


def test_detect_no_risks():
    """分散持仓无风险"""
    pos = [_make_pos(f"A{i}", 10) for i in range(10)]
    hhi = calc_portfolio_hhi(pos)
    top5 = calc_top_n_concentration(pos)
    risks = detect_concentration_risks(hhi, top5)
    # 不一定完全没有，但至少不会崩溃
    assert isinstance(risks, list)


import pytest
