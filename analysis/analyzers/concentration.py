"""集中度分析器 — 组合级别 HHI、行业集中度、Top-N 集中度"""

from typing import Optional
from dataclasses import dataclass
from portfolio.models import Position
from analysis.models.holdings import SectorExposure


def calc_portfolio_hhi(positions: list[Position]) -> float:
    """计算组合 HHI 集中度 = Σ(weight_i²)，weight 为百分比

    HHI < 10: 分散
    HHI 10-20: 中度集中
    HHI > 20: 高度集中
    """
    if not positions:
        return 0.0
    total_value = sum(p.market_value for p in positions)
    if total_value == 0:
        return 0.0
    weights = [(p.market_value / total_value) for p in positions]
    hhi = sum(w ** 2 for w in weights)
    return round(hhi * 10000, 2)  # HHI 惯例乘以 10000


def calc_effective_n(positions: list[Position]) -> int:
    """有效持仓数 = 1 / Σ(weight_i²)，即 HHI 的倒数"""
    hhi = calc_portfolio_hhi(positions)
    if hhi == 0:
        return 0
    return int(round(10000 / hhi, 0))


def calc_top_n_concentration(positions: list[Position], n: int = 5) -> float:
    """前 N 大持仓的集中度(%)"""
    if not positions:
        return 0.0
    total_value = sum(p.market_value for p in positions)
    if total_value == 0:
        return 0.0
    sorted_pos = sorted(positions, key=lambda p: p.market_value, reverse=True)
    top_value = sum(p.market_value for p in sorted_pos[:n])
    return round(top_value / total_value * 100, 2)


def calc_sector_concentration(positions: list[Position]) -> list[SectorExposure]:
    """计算组合的行业集中度（需要持仓已有行业标签）

    当 Position 本身不包含 sector 字段时，可通过外部提供。
    此处返回按资产类型(e.g. etf/fund)归类作为 fallback。
    """
    if not positions:
        return []
    total_value = sum(p.market_value for p in positions)
    if total_value == 0:
        return []

    sector_map: dict[str, float] = {}
    for p in positions:
        # 用 asset_type 作为默认行业分类
        sector = p.asset_type.value.upper()
        sector_map[sector] = sector_map.get(sector, 0) + p.market_value

    return [
        SectorExposure(sector=sector, weight=round(value / total_value * 100, 2))
        for sector, value in sorted(sector_map.items(), key=lambda x: -x[1])
    ]


def detect_concentration_risks(hhi: float, top_n_pct: float) -> list[str]:
    """根据集中度指标检测风险"""
    risks = []
    if hhi > 2000:
        risks.append(f"HHI={hhi:.0f} > 2000，组合高度集中，缺乏分散")
    elif hhi > 1000:
        risks.append(f"HHI={hhi:.0f} > 1000, 组合中度集中，建议增加分散")

    if top_n_pct > 60:
        risks.append(f"前 5 大持仓占比 {top_n_pct:.1f}% > 60%，集中度过高")
    elif top_n_pct > 40:
        risks.append(f"前 5 大持仓占比 {top_n_pct:.1f}% > 40%，集中度偏高")

    return risks
