"""压力测试引擎 — 预设和历史场景分析"""

from typing import Optional
from portfolio.models import Position, AssetType
from analysis.models.theory import StressTestScenario, StressTestResult


# 预设压力场景：{(场景名, 描述): {过滤条件: 冲击幅度(%)}}
_BUILTIN_SCENARIOS: list[tuple[str, str, dict[str, float]]] = [
    (
        "2008 金融危机",
        "模拟 2008 年全球金融危机冲击：股票 -50%，REIT -40%，债券 +5%",
        {"stock": -50.0, "reit": -40.0, "bond": 5.0, "etf": -45.0, "fund": -40.0},
    ),
    (
        "2022 加息冲击",
        "模拟 2022 年激进加息环境：成长股 -30%，债券 -15%，商品 +20%",
        {"stock": -25.0, "etf": -20.0, "bond": -15.0, "reit": -25.0, "fund": -20.0},
    ),
    (
        "新冠疫情式冲击",
        "模拟 2020 年 3 月疫情冲击：全部风险资产 -30%",
        {"stock": -30.0, "etf": -30.0, "fund": -25.0, "reit": -35.0, "bond": 2.0},
    ),
    (
        "通胀飙升",
        "模拟高通胀环境：债券 -10%，商品相关 +15%，股票 -15%",
        {"bond": -10.0, "stock": -15.0, "etf": -10.0, "fund": -10.0, "reit": -5.0},
    ),
    (
        "温和回调",
        "模拟正常市场回调：股票 -10%，债券 +1%",
        {"stock": -10.0, "etf": -8.0, "fund": -8.0, "reit": -12.0, "bond": 1.0},
    ),
]


def _asset_type_label(asset_type: AssetType) -> str:
    """将 AssetType 映射为场景中的标签"""
    return asset_type.value  # "etf", "fund", "stock", "bond", "reit"


def run_stress_test(positions: list[Position]) -> StressTestResult:
    """对持仓组合运行预设压力测试

    参数:
        positions: 持仓列表
    """
    if not positions:
        return StressTestResult()

    total_value = sum(p.market_value for p in positions)
    if total_value == 0:
        return StressTestResult()

    scenarios: list[StressTestScenario] = []
    all_impacts: list[float] = []
    asset_shocks: dict[str, list[float]] = {p.symbol: [] for p in positions}

    for name, description, type_shocks in _BUILTIN_SCENARIOS:
        shock_map: dict[str, float] = {}
        impact_values: list[float] = []

        for p in positions:
            if p.market_value == 0:
                shock_map[p.symbol] = 0.0
                impact_values.append(0.0)
                continue

            type_key = _asset_type_label(p.asset_type)
            shock = type_shocks.get(type_key, -10.0)  # 默认 -10%
            # 细分：纯股票型 ETF 用 stock 档位
            if type_key == "etf" and "stock" in type_shocks and p.name:
                # 偏股 ETF 按 stock 档
                stock_keywords = ["股", "指数", "300", "500", "科创", "创业", "成长"]
                if any(kw in p.name for kw in stock_keywords):
                    shock = type_shocks.get("stock", shock)

            shock_map[p.symbol] = shock
            impact = p.market_value * shock / 100
            impact_values.append(impact)
            asset_shocks[p.symbol].append(impact)

        total_impact = sum(impact_values)
        impact_pct = round(total_impact / total_value * 100, 2)

        scenarios.append(StressTestScenario(
            name=name,
            description=description,
            shock_pct=shock_map,
            impact_pct=impact_pct,
        ))
        all_impacts.append(impact_pct)

    worst_case = min(all_impacts) if all_impacts else 0.0

    # 抗压资产 = 平均冲击最小的资产
    resilient = sorted(
        [(s, sum(shocks) / len(shocks)) for s, shocks in asset_shocks.items()],
        key=lambda x: x[1],
    )
    vulnerable = list(reversed(resilient))

    return StressTestResult(
        scenarios=scenarios,
        worst_case_loss=round(abs(worst_case), 2),
        resilient_assets=[s for s, _ in resilient[:3]] if resilient else [],
        vulnerable_assets=[s for s, _ in vulnerable[:3]] if vulnerable else [],
    )
