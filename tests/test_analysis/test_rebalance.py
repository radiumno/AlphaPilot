"""再平衡方案测试"""

from analysis.analyzers.rebalance import (
    generate_rebalancing_plan, RebalancingPlan, RebalanceTrade,
)
from analysis.analyzers.optimization import OptimizationResult


def _make_opt(weights: dict[str, float]) -> OptimizationResult:
    return OptimizationResult(
        method="max_sharpe",
        weights=weights,
        expected_return=15.0,
        expected_volatility=12.0,
        sharpe_ratio=1.0,
    )


def test_rebalance_hold_when_aligned():
    """权重一致时全部持有"""
    opt = _make_opt({"A": 0.5, "B": 0.3, "C": 0.2})
    plan = generate_rebalancing_plan(
        current_weights={"A": 0.5, "B": 0.3, "C": 0.2},
        names={"A": "Asset A", "B": "Asset B", "C": "Asset C"},
        current_prices={"A": 100, "B": 50, "C": 20},
        optimal_result=opt,
        total_value=100000,
    )
    assert plan.total_turnover == 0.0
    assert all(t.action == "持有" for t in plan.trades)


def test_rebalance_generates_trades():
    """偏差大于阈值时生成交易"""
    opt = _make_opt({"A": 0.6, "B": 0.4})
    plan = generate_rebalancing_plan(
        current_weights={"A": 0.8, "B": 0.2},
        names={"A": "Asset A", "B": "Asset B"},
        current_prices={"A": 100, "B": 50},
        optimal_result=opt,
        total_value=100000,
        min_weight_change=0.1,
    )
    trades = {t.symbol: t for t in plan.trades}
    assert trades["A"].action == "卖出"
    assert trades["B"].action == "买入"
    assert plan.total_turnover > 0
    assert plan.n_trades == 2


def test_rebalance_urgency():
    """偏差越大优先级越高"""
    opt = _make_opt({"A": 0.5, "B": 0.3, "C": 0.2})

    # A: 当前 30% -> 目标 50%, diff = +20% => 高
    # B: 当前 30% -> 目标 30%, diff = 0   => 持有
    # C: 当前 40% -> 目标 20%, diff = -20% => 高
    plan = generate_rebalancing_plan(
        current_weights={"A": 0.3, "B": 0.3, "C": 0.4},
        names={"A": "A", "B": "B", "C": "C"},
        current_prices={"A": 100, "B": 50, "C": 20},
        optimal_result=opt,
        total_value=100000,
        min_weight_change=0.1,
    )
    trades = {t.symbol: t for t in plan.trades}
    assert trades["A"].urgency == "高"
    assert trades["B"].action == "持有"
    assert trades["C"].urgency == "高"


def test_rebalance_min_trade_filter():
    """低于最小交易金额的不触发"""
    opt = _make_opt({"A": 0.51, "B": 0.49})
    plan = generate_rebalancing_plan(
        current_weights={"A": 0.5, "B": 0.5},
        names={"A": "A", "B": "B"},
        current_prices={"A": 100, "B": 50},
        optimal_result=opt,
        total_value=10000,
        min_weight_change=0.1,
        min_trade_value=5000,
    )
    # 总市值 10000, 偏差 1% => trade_value = 100, 小于 5000
    assert all(t.action == "持有" for t in plan.trades)


def test_rebalance_estimated_cost():
    """估算交易成本"""
    opt = _make_opt({"A": 0.0, "B": 1.0})
    plan = generate_rebalancing_plan(
        current_weights={"A": 0.5, "B": 0.5},
        names={"A": "A", "B": "B"},
        current_prices={"A": 100, "B": 50},
        optimal_result=opt,
        total_value=100000,
        min_weight_change=0.1,
        transaction_cost_pct=0.001,
    )
    assert plan.estimated_cost > 0
    assert plan.estimated_cost_pct > 0


def test_rebalance_result_model():
    """RebalancingPlan 数据模型"""
    plan = RebalancingPlan(
        target_method="max_sharpe",
        total_turnover=50.0,
        n_trades=2,
    )
    assert plan.target_method == "max_sharpe"
    assert plan.trades == []


def test_rebalance_trade_model():
    """RebalanceTrade 数据模型"""
    t = RebalanceTrade(
        symbol="000300",
        name="沪深300",
        current_weight=30.0,
        target_weight=40.0,
        weight_diff=10.0,
        current_value=30000,
        trade_value=10000,
        trade_shares=100,
        action="买入",
        urgency="高",
    )
    assert t.symbol == "000300"
    assert t.action == "买入"
