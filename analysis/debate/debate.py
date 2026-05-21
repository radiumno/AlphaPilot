"""AI 辩论引擎 — 3 阶段多智能体辩论

辩论流程:
  Stage 1 (结构辩论): 评估组合的整体结构合理性
  Stage 2 (调仓辩论): 逐标的审查是否需要调整
  Stage 3 (优先级排序): 对调仓建议排序并给出最终决策

每个阶段使用两个不同立场的智能体进行对抗性辩论。
"""

from typing import Optional
from portfolio.models import Position
from analysis.models.theory import DebateResult, DebateRound, DebateArgument
from data.llm import LLMClient


# 智能体角色定义
_AGENTS = {
    "conservative": {
        "name": "保守派分析师",
        "persona": "你是一位保守派投资分析师，重视风险控制和资产安全，对任何调整都倾向谨慎。"
                   "你的核心原则是：保护本金优先，避免追涨杀跌，强调分散化。",
    },
    "aggressive": {
        "name": "进取派分析师",
        "persona": "你是一位进取派投资分析师，重视收益机会和市场趋势，对调整持开放态度。"
                   "你的核心原则是：抓住市场机会，优化收益潜力，敢于在高确信时集中。",
    },
    "neutral": {
        "name": "首席分析师",
        "persona": "你是一位首席投资分析师，负责综合保守派和进取派的意见做出最终裁决。"
                   "你平衡风险和收益，基于数据做出理性判断。",
    },
}


def _build_portfolio_summary(positions: list[Position]) -> str:
    """构建持仓摘要文本"""
    if not positions:
        return "空持仓"

    total = sum(p.market_value for p in positions) or 1
    lines = ["当前持仓:"]
    for p in positions:
        pnl = (p.market_price - p.cost_price) / p.cost_price * 100 if p.cost_price > 0 else 0
        weight = p.market_value / total * 100
        lines.append(
            f"  - {p.symbol} {p.name}: 市值={p.market_value:.0f}, "
            f"权重={weight:.1f}%, 盈亏={pnl:+.1f}%, 类型={p.asset_type.value}, 市场={p.market.value}"
        )
    lines.append(f"组合总市值: {total:.0f}")
    return "\n".join(lines)


def _call_agent(
    client: LLMClient,
    agent_key: str,
    topic: str,
    context: str,
    opponent_arg: Optional[str] = None,
    temperature: float = 0.7,
) -> tuple[str, float]:
    """调用单个智能体发表观点"""
    agent = _AGENTS.get(agent_key, _AGENTS["neutral"])
    system_prompt = f"{agent['persona']}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"【辩论主题】\n{topic}\n\n【背景信息】\n{context}"},
    ]

    if opponent_arg:
        messages.append({"role": "user", "content": f"【对方观点】\n{opponent_arg}\n\n请针对对方观点进行反驳或补充。"})

    messages.append({
        "role": "user",
        "content": "请给出你的分析和建议（200字以内），并在最后一行以 [confidence:0.X] 格式给出你的置信度。"
    })

    reply = client.chat(messages, temperature=temperature)
    confidence = 0.5

    # 从回复中提取置信度
    import re
    match = re.search(r'\[confidence:\s*([0-9.]+)\]', reply)
    if match:
        try:
            confidence = float(match.group(1))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            pass

    return reply, confidence


def _consensus_round(
    client: LLMClient,
    topic: str,
    context: str,
    stage: str = "structure",
) -> DebateRound:
    """执行一轮辩论（保守 vs 进取 + 首席裁决）"""
    round_num = {"structure": 1, "rebalance": 2, "priority": 3}.get(stage, 1)

    # 保守派先发言
    conservative_reply, con_conf = _call_agent(client, "conservative", topic, context, temperature=0.5)
    arg1 = DebateArgument(
        agent_name="保守派分析师",
        position="审慎",
        content=conservative_reply[:500],
        confidence=con_conf,
    )

    # 进取派对保守派观点进行反驳
    aggressive_reply, agg_conf = _call_agent(
        client, "aggressive", topic, context,
        opponent_arg=conservative_reply[:300], temperature=0.6,
    )
    arg2 = DebateArgument(
        agent_name="进取派分析师",
        position="积极",
        content=aggressive_reply[:500],
        confidence=agg_conf,
    )

    # 首席分析师综合裁决
    neutral_prompt = (
        f"【辩论记录】\n"
        f"保守派观点: {conservative_reply[:300]}\n\n"
        f"进取派观点: {aggressive_reply[:300]}\n\n"
        f"请综合双方意见，给出最终裁决，在最后一行以 [consensus:...] 格式给出共识摘要。"
    )
    neutral_reply = client.chat([
        {"role": "system", "content": _AGENTS["neutral"]["persona"]},
        {"role": "user", "content": neutral_prompt},
    ], temperature=0.3)

    # 提取共识
    consensus = None
    import re
    match = re.search(r'\[consensus:(.*?)\]', neutral_reply)
    if match:
        consensus = match.group(1).strip()

    return DebateRound(
        round_number=round_num,
        arguments=[arg1, arg2],
        consensus=consensus,
        summary=neutral_reply[:300],
    )


def _run_stage1_structure(client: LLMClient, positions: list[Position]) -> DebateResult:
    """Stage 1: 组合结构辩论"""
    topic = "当前投资组合的结构是否合理？"
    context = _build_portfolio_summary(positions)
    context += "\n\n请从以下方面评估组合结构：资产配置比例、市场分散度、风险集中度、整体健康度。"

    debate_round = _consensus_round(client, topic, context, "structure")

    return DebateResult(
        topic="组合结构合理性评估",
        rounds=[debate_round],
        final_consensus=debate_round.consensus or debate_round.summary,
        decision=debate_round.consensus or "需进一步分析",
        confidence=sum(a.confidence for a in debate_round.arguments) / len(debate_round.arguments) if debate_round.arguments else 0.5,
    )


def _run_stage2_rebalance(
    client: LLMClient,
    positions: list[Position],
    structure_result: DebateResult,
) -> DebateResult:
    """Stage 2: 调仓辩论 — 逐标的需要调整"""
    topic = "是否需要调整当前持仓？哪些标的需要减仓或加仓？"
    context = _build_portfolio_summary(positions)
    context += f"\n\n结构评估摘要: {structure_result.final_consensus}"
    context += "\n\n请逐标地分析是否需要调整，并说明理由。"

    debate_round = _consensus_round(client, topic, context, "rebalance")

    return DebateResult(
        topic="调仓方案评估",
        rounds=[debate_round],
        final_consensus=debate_round.consensus or debate_round.summary,
        decision=debate_round.consensus or "维持当前持仓",
        confidence=sum(a.confidence for a in debate_round.arguments) / len(debate_round.arguments) if debate_round.arguments else 0.5,
    )


def _run_stage3_priorities(
    client: LLMClient,
    positions: list[Position],
    structure_result: DebateResult,
    rebalance_result: DebateResult,
) -> DebateResult:
    """Stage 3: 优先级辩论 — 排序并给出最终决策"""
    topic = "调仓建议的优先级排序和最终决策"
    context = _build_portfolio_summary(positions)
    context += f"\n\n结构评估: {structure_result.final_consensus}"
    context += f"\n调仓建议: {rebalance_result.final_consensus}"
    context += "\n\n请给出以下最终决策：1) 最重要的前3条调仓建议 2) 建议的执行时间 3) 综合风险提示"

    debate_round = _consensus_round(client, topic, context, "priority")

    return DebateResult(
        topic="操作优先级与最终决策",
        rounds=[debate_round],
        final_consensus=debate_round.consensus or debate_round.summary,
        decision=debate_round.consensus or "等待更多数据",
        confidence=sum(a.confidence for a in debate_round.arguments) / len(debate_round.arguments) if debate_round.arguments else 0.5,
    )


def run_debate(
    positions: list[Position],
    llm_client: Optional[LLMClient] = None,
    structure_result: Optional[DebateResult] = None,
) -> dict[str, DebateResult]:
    """运行完整 3 阶段辩论

    参数:
        positions: 持仓列表
        llm_client: LLM 客户端（默认使用 DeepSeek 配置）
        structure_result: 可选的 Stage 1 结果（用于单独调仓/优先级辩论）
    返回:
        {"structure": ..., "rebalance": ..., "priority": ...}
    """
    client = llm_client or LLMClient()

    if not client.api_key:
        no_key_result = DebateResult(
            topic="辩论不可用", rounds=[],
            final_consensus="未配置 LLM API Key，跳过辩论阶段",
            decision="skip", confidence=0.0,
        )
        return {"structure": no_key_result, "rebalance": no_key_result, "priority": no_key_result}

    # Stage 1
    s1 = _run_stage1_structure(client, positions)

    # Stage 2
    s2 = _run_stage2_rebalance(client, positions, s1)

    # Stage 3
    s3 = _run_stage3_priorities(client, positions, s1, s2)

    return {"structure": s1, "rebalance": s2, "priority": s3}
