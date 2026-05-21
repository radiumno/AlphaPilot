"""集成测试 — E2E 全流水线测试（Mock 数据 + 全阶段验证）"""

import pytest
from typing import Optional
import pandas as pd
import numpy as np
from portfolio.models import Portfolio, Position, AssetType, MarketType
from analysis.pipeline import AnalysisPipeline, AnalysisContext
from analysis.analyzers.optimization import PortfolioOptimizationResult
from analysis.analyzers.rebalance import RebalancingPlan


# ── Mock 数据 ─────────────────────────────────────────

def _mock_nav(n_days=252, base=1.0, drift=0.0005, vol=0.01, seed=42):
    np.random.seed(seed)
    returns = np.random.normal(drift, vol, n_days)
    prices = base * np.cumprod(1 + returns)
    return pd.Series(prices, name="nav")


class _MockCNProvider:
    def name(self): return "MockCN"
    def get_etf_nav(self, symbol): return _mock_nav(seed=hash(symbol) % 1000)
    def get_etf_daily(self, symbol, period="1y"):
        close = _mock_nav(252, 100.0)
        return pd.DataFrame({"open": close * 0.99, "high": close * 1.01,
                             "low": close * 0.98, "close": close,
                             "volume": np.random.randint(10000, 1000000, 252)})
    def get_fund_nav(self, symbol): return _mock_nav(seed=hash(symbol) % 1000, vol=0.008)
    def get_fund_info(self, symbol):
        return {"name": f"基金{symbol}", "manager": "测试经理", "size": 10e8,
                "founded": "2020-01-01", "fee_rate": 0.015}
    def get_fund_holdings(self, symbol):
        return pd.DataFrame({"stock": ["A", "B", "C"], "weight": [0.4, 0.35, 0.25]})


class _MockGlobalProvider:
    def name(self): return "MockGlobal"
    def get_etf_nav(self, symbol): return _mock_nav(seed=hash(symbol) % 1000, drift=0.0008)
    def get_etf_daily(self, symbol, period="1y"):
        close = _mock_nav(252, 450.0, seed=hash(symbol) % 1000)
        return pd.DataFrame({"close": close})
    def get_fund_nav(self, symbol): return _mock_nav(seed=hash(symbol) % 1000)
    def get_fund_info(self, symbol):
        return {"name": f"Global Fund {symbol}", "manager": "Test",
                "size": 50e8, "founded": "2019-06-01", "fee_rate": 0.012}
    def get_fund_holdings(self, symbol):
        return pd.DataFrame({"stock": ["X", "Y", "Z"], "weight": [0.5, 0.3, 0.2]})


# ── Session 级 fixture（流水线只跑一次）───────────────

@pytest.fixture(scope="session")
def mock_portfolio():
    positions = [
        Position(symbol="510050", name="上证50ETF", asset_type=AssetType.ETF,
                 shares=10000, cost_price=3.0, market_price=3.2, market=MarketType.CN),
        Position(symbol="159915", name="创业板ETF", asset_type=AssetType.ETF,
                 shares=20000, cost_price=1.5, market_price=1.6, market=MarketType.CN),
        Position(symbol="110011", name="易方达中小盘", asset_type=AssetType.FUND,
                 shares=5000, cost_price=2.0, market_price=2.1, market=MarketType.CN),
        Position(symbol="SPY", name="SPDR S&P 500", asset_type=AssetType.ETF,
                 shares=100, cost_price=450, market_price=480, market=MarketType.US),
    ]
    p = Portfolio(positions=positions)
    p.recalc()
    return p


@pytest.fixture(scope="session")
def pipeline():
    return AnalysisPipeline(
        cn_provider=_MockCNProvider(),
        global_provider=_MockGlobalProvider(),
    )


@pytest.fixture(scope="session")
def ctx(pipeline, mock_portfolio):
    return pipeline.run(mock_portfolio)


# ── 各阶段输出验证 ─────────────────────────────────────

def test_pipeline_returns_context(ctx):
    assert isinstance(ctx, AnalysisContext)


def test_p1_data_collection(ctx, mock_portfolio):
    p1 = ctx.phase_outputs["P1"]
    assert p1["status"] in ("done", "partial")
    assert len(ctx.collected_data.assets) >= 2


def test_p2_asset_checkup(ctx):
    p2 = ctx.phase_outputs["P2"]
    assert p2.get("status") == "done"


def test_p3_portfolio_analysis(ctx):
    p3 = ctx.phase_outputs["P3"]
    assert p3["status"] == "done"
    assert ctx.optimization_result is not None
    assert isinstance(ctx.optimization_result, PortfolioOptimizationResult)


def test_p3_optimization_metrics(ctx):
    cur = ctx.optimization_result.current
    assert cur.diversification_ratio > 0


def test_p4_theory_evaluation(ctx):
    p4 = ctx.phase_outputs["P4"]
    assert p4["status"] == "done"
    assert len(p4.get("theories", [])) >= 3


def test_p5_debate_skippable(ctx):
    """P5 在无 API Key 时可安全跳过"""
    p5 = ctx.phase_outputs["P5"]
    assert p5.get("status") in ("done", "skipped")


def test_p6_risk_assessment(ctx):
    p6 = ctx.phase_outputs["P6"]
    assert p6["status"] == "done"
    assert 0 <= p6.get("risk_score", 0) <= 100


def test_p7_recommendation(ctx, mock_portfolio):
    p7 = ctx.phase_outputs["P7"]
    assert p7["status"] == "done"
    assert 0 <= p7.get("composite_score", 0) <= 100
    assert len(p7.get("position_actions", [])) == 4


def test_p7_rebalancing_plan(ctx):
    assert ctx.rebalancing_plan is not None
    assert isinstance(ctx.rebalancing_plan, RebalancingPlan)
    assert len(ctx.rebalancing_plan.trades) > 0


def test_pipeline_full_cycle(ctx):
    for phase in ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]:
        assert phase in ctx.phase_outputs
        assert ctx.phase_outputs[phase] is not None


def test_pipeline_stress_result(ctx):
    assert ctx.stress_test_result is not None
    assert len(ctx.stress_test_result.scenarios) >= 5


def test_pipeline_single_asset():
    """单一资产流水线也能正常工作（无优化/相关性）"""
    pos = [Position(symbol="510050", name="上证50ETF", asset_type=AssetType.ETF,
                    shares=10000, cost_price=3.0, market_price=3.2, market=MarketType.CN)]
    portfolio = Portfolio(positions=pos)
    portfolio.recalc()
    ctx = AnalysisPipeline(cn_provider=_MockCNProvider()).run(portfolio)
    assert ctx.optimization_result is None
    assert ctx.correlation_result is None
