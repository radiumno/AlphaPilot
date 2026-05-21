"""再平衡方案生成 — 基于优化结果对比当前 vs 最优权重，生成具体买卖建议"""

from typing import Optional
from pydantic import BaseModel, Field
from analysis.analyzers.optimization import OptimizationResult


class RebalanceTrade(BaseModel):
    """单笔再平衡交易"""
    symbol: str
    name: str
    current_weight: float = Field(description="当前权重(%)")
    target_weight: float = Field(description="目标权重(%)")
    weight_diff: float = Field(description="权重差(%)")
    current_value: float = Field(description="当前市值")
    trade_value: float = Field(description="交易金额，正=买入，负=卖出")
    trade_shares: float = Field(description="交易份额")
    action: str = Field(description="买入/卖出/持有")
    urgency: str = Field(description="高/中/低")


class RebalancingPlan(BaseModel):
    """完整再平衡方案"""
    target_method: str = Field(description="目标策略")
    current_weights: dict[str, float] = Field(default_factory=dict)
    target_weights: dict[str, float] = Field(default_factory=dict)
    trades: list[RebalanceTrade] = Field(default_factory=list)
    total_turnover: float = Field(description="总换手率(%)")
    n_trades: int = Field(description="触发交易的标的数")
    estimated_cost: float = Field(default=0.0, description="预估交易成本")
    estimated_cost_pct: float = Field(default=0.0, description="成本占比(%)")


def _get_target(
    opt: OptimizationResult, method: str = "max_sharpe",
) -> Optional[OptimizationResult]:
    """根据方法名选择目标最优结果"""
    return opt if opt.method == method else None


def generate_rebalancing_plan(
    current_weights: dict[str, float],
    names: dict[str, str],
    current_prices: dict[str, float],
    optimal_result: OptimizationResult,
    total_value: float = 100000,
    transaction_cost_pct: float = 0.001,
    min_trade_value: float = 100,
    min_weight_change: float = 0.5,
) -> RebalancingPlan:
    """生成再平衡方案

    参数:
        current_weights: {symbol: 当前权重(小数)}
        names: {symbol: 名称}
        current_prices: {symbol: 当前价格}
        optimal_result: 优化结果（max_sharpe 或 risk_parity）
        total_value: 组合总市值
        transaction_cost_pct: 交易成本比例
        min_trade_value: 最小交易金额
        min_weight_change: 最小触发调整的权重差(%)
    """
    targets = optimal_result.weights
    target_method = optimal_result.method

    trades: list[RebalanceTrade] = []
    total_turnover_value = 0.0

    all_symbols = set(list(current_weights.keys()) + list(targets.keys()))

    for sym in sorted(all_symbols):
        cw = current_weights.get(sym, 0.0)
        tw = targets.get(sym, 0.0)
        diff = (tw - cw) * 100  # 转为百分比

        # 偏差过小不触发交易
        if abs(diff) < min_weight_change:
            trades.append(RebalanceTrade(
                symbol=sym,
                name=names.get(sym, sym),
                current_weight=round(cw * 100, 2),
                target_weight=round(tw * 100, 2),
                weight_diff=round(diff, 2),
                current_value=round(total_value * cw, 2),
                trade_value=0.0,
                trade_shares=0.0,
                action="持有",
                urgency="—",
            ))
            continue

        trade_value = total_value * (tw - cw)
        price = current_prices.get(sym, 1.0)
        trade_shares = trade_value / max(price, 0.01)
        abs_value = abs(trade_value)

        if abs_value < min_trade_value:
            trades.append(RebalanceTrade(
                symbol=sym,
                name=names.get(sym, sym),
                current_weight=round(cw * 100, 2),
                target_weight=round(tw * 100, 2),
                weight_diff=round(diff, 2),
                current_value=round(total_value * cw, 2),
                trade_value=0.0,
                trade_shares=0.0,
                action="持有",
                urgency="—",
            ))
            continue

        action = "买入" if trade_value > 0 else "卖出"
        abs_diff = abs(diff)
        if abs_diff >= 10:
            urgency = "高"
        elif abs_diff >= 5:
            urgency = "中"
        else:
            urgency = "低"

        total_turnover_value += abs(trade_value)
        trades.append(RebalanceTrade(
            symbol=sym,
            name=names.get(sym, sym),
            current_weight=round(cw * 100, 2),
            target_weight=round(tw * 100, 2),
            weight_diff=round(diff, 2),
            current_value=round(total_value * cw, 2),
            trade_value=round(trade_value, 2),
            trade_shares=round(trade_shares, 2),
            action=action,
            urgency=urgency,
        ))

    total_turnover_pct = total_turnover_value / max(total_value, 1) * 100
    estimated_cost = total_turnover_value * transaction_cost_pct

    return RebalancingPlan(
        target_method=target_method,
        current_weights={k: round(v * 100, 2) for k, v in current_weights.items()},
        target_weights={k: round(v * 100, 2) for k, v in targets.items()},
        trades=trades,
        total_turnover=round(total_turnover_pct, 2),
        n_trades=sum(1 for t in trades if t.action != "持有"),
        estimated_cost=round(estimated_cost, 2),
        estimated_cost_pct=round(estimated_cost / max(total_value, 1) * 100, 4),
    )
