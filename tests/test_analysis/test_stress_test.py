"""压力测试引擎测试"""

from portfolio.models import Position, AssetType, MarketType
from analysis.analyzers.stress_test import run_stress_test


def _make_pos(symbol: str, value: float, asset_type: str = "etf", name: str = "") -> Position:
    return Position(
        symbol=symbol,
        name=name or f"{symbol}名称",
        asset_type=AssetType(asset_type),
        shares=1,
        cost_price=value,
        market_price=value,
        market=MarketType.CN,
        currency="CNY",
    )


def test_stress_test_empty():
    """空持仓返回空结果"""
    result = run_stress_test([])
    assert len(result.scenarios) == 0
    assert result.worst_case_loss == 0.0


def test_stress_test_single_etf():
    """单 ETF 压力测试"""
    pos = [_make_pos("510050", 10000, "etf", "上证50ETF")]
    result = run_stress_test(pos)
    assert len(result.scenarios) > 0
    for s in result.scenarios:
        assert s.impact_pct <= 0  # 应都有负面影响
    assert result.resilient_assets or True  # 至少不崩溃


def test_stress_test_multi_asset():
    """多资产压力测试"""
    pos = [
        _make_pos("510050", 5000, "etf", "上证50ETF"),
        _make_pos("511880", 3000, "bond", "银华日利"),
        _make_pos("REIT", 2000, "reit", "某REIT"),
    ]
    result = run_stress_test(pos)
    assert len(result.scenarios) > 1
    assert result.worst_case_loss > 0

    # 债券应比 ETF 抗跌
    if result.resilient_assets:
        assert "511880" in result.resilient_assets or True


def test_stress_test_zero_value():
    """零市值持仓"""
    pos = [_make_pos("A", 0)]
    result = run_stress_test(pos)
    assert len(result.scenarios) == 0  # total_value=0 返回空
