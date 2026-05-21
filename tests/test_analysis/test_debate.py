"""辩论引擎测试"""

from portfolio.models import Position, AssetType, MarketType
from analysis.debate.debate import run_debate
from analysis.models.theory import DebateResult, DebateRound, DebateArgument
from data.llm import LLMClient


def _make_pos(symbol: str, value: float = 10000) -> Position:
    return Position(
        symbol=symbol, name=f"{symbol}名称",
        asset_type=AssetType.ETF, shares=value, cost_price=1.0,
        market_price=1.0, market=MarketType.CN, currency="CNY",
    )


def test_debate_no_key():
    """无 API Key 时跳过辩论"""
    positions = [_make_pos("510050"), _make_pos("511880")]
    client = LLMClient(api_key="")
    results = run_debate(positions, llm_client=client)
    assert "structure" in results
    assert results["structure"].decision == "skip"
    assert "未配置" in results["structure"].final_consensus


def test_debate_empty_positions():
    """空持仓辩论"""
    client = LLMClient(api_key="")
    results = run_debate([], llm_client=client)
    assert "structure" in results


def test_debate_result_model():
    """DebateResult 数据模型"""
    result = DebateResult(
        topic="测试主题",
        rounds=[
            DebateRound(
                round_number=1,
                arguments=[
                    DebateArgument(
                        agent_name="保守派", position="审慎",
                        content="建议谨慎", confidence=0.6,
                    ),
                ],
                consensus="综合意见",
                summary="保守优先",
            ),
        ],
        final_consensus="保持现状",
        decision="hold",
        confidence=0.6,
    )
    assert result.topic == "测试主题"
    assert len(result.rounds) == 1
    assert result.rounds[0].arguments[0].agent_name == "保守派"
    assert result.decision == "hold"
    assert result.confidence == 0.6


def test_debate_argument_model():
    """DebateArgument 数据模型"""
    arg = DebateArgument(
        agent_name="进取派", position="积极",
        content="建议加仓", confidence=0.8,
    )
    assert arg.position == "积极"
    assert 0 <= arg.confidence <= 1
