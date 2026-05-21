"""analyze 子命令业务逻辑 — 显示持仓摘要 + 全流水线分析结果"""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from portfolio.loader import load_positions_from_csv
from portfolio.models import Portfolio
from analysis.pipeline import AnalysisPipeline

console = Console()


def _show_positions(portfolio: Portfolio) -> None:
    """显示持仓摘要表格"""
    table = Table(title=f"持仓分析 ({len(portfolio.positions)} 只标的)")
    table.add_column("代码", style="cyan")
    table.add_column("名称")
    table.add_column("类型")
    table.add_column("市值", justify="right")
    table.add_column("盈亏%", justify="right")

    for p in portfolio.positions:
        pnl_str = f"{p.unrealized_pnl_pct*100:.1f}%"
        color = "green" if p.unrealized_pnl_pct >= 0 else "red"
        table.add_row(
            p.symbol, p.name, p.asset_type.value,
            f"{p.market_value:,.0f}",
            f"[{color}]{pnl_str}[/{color}]",
        )

    console.print(table)
    console.print(f"\n组合总市值: [bold]{portfolio.total_value:,.0f}[/bold]\n")


def _show_p3_portfolio(ctx) -> None:
    """显示组合分析结果"""
    p3 = ctx.phase_outputs.get("P3", {})
    if p3.get("status") != "done":
        return

    conc = p3.get("concentration", {})
    table = Table(title="组合集中度分析")
    table.add_column("指标", style="cyan")
    table.add_column("数值", justify="right")
    table.add_row("HHI 集中度", f"{conc.get('hhi', 0):.0f}")
    table.add_row("有效持仓数", f"{conc.get('effective_n', 0)}")
    table.add_row("前 5 大占比", f"{conc.get('top5_pct', 0):.1f}%")
    table.add_row("压力场景数", f"{p3.get('stress_test_scenarios', 0)}")

    risk_flags = p3.get("risk_flags", [])
    if risk_flags:
        table.add_row("风险提示", "\n".join(risk_flags[:3]))

    console.print(table)

    if p3.get("sectors"):
        sec_table = Table(title="行业分布")
        sec_table.add_column("行业", style="cyan")
        sec_table.add_column("占比", justify="right")
        for sec in p3["sectors"]:
            sec_table.add_row(sec, "—")
        console.print(sec_table)


def _show_p5_debate(ctx) -> None:
    """显示辩论引擎结果"""
    p5 = ctx.phase_outputs.get("P5", {})
    if p5.get("status") == "skipped":
        console.print(Panel("辩论引擎已跳过（未配置 API Key）", style="dim"))
        console.print()
        return
    if p5.get("status") != "done":
        return

    from rich.tree import Tree as RTree

    debate_results = ctx.debate_results
    if not debate_results:
        return

    tree = RTree("[bold magenta]辩论引擎 — 3 阶段多智能体对抗[/bold magenta]")

    for stage_name, debate in debate_results.items():
        label = {"structure": "阶段1: 持仓结构合理性",
                 "rebalance": "阶段2: 调仓方案",
                 "priority": "阶段3: 优先级裁决"}.get(stage_name, stage_name)
        decision_cn = {"hold": "持有", "adjust": "调整",
                       "reduce": "减仓", "buy": "加仓",
                       "skip": "跳过"}.get(debate.decision, debate.decision)

        stage = tree.add(
            f"[bold]{label}[/bold] — "
            f"决策: [{'green' if debate.decision in ('hold','buy') else 'yellow'}]{decision_cn}[/] "
            f"置信度: {debate.confidence:.0%}"
        )
        if debate.final_consensus:
            stage.add(f"[dim]共识: {debate.final_consensus[:300]}[/dim]")

        for rnd in debate.rounds:
            rnd_label = f"辩论{rnd.round_number}"
            if rnd.consensus:
                rnd_label += f" (共识: {rnd.consensus[:100]})"
            rnd_branch = stage.add(rnd_label)
            for arg in rnd.arguments:
                agent_label = {
                    "conservative": "保守派分析师",
                    "aggressive": "进取派分析师",
                    "neutral": "首席分析师",
                }.get(arg.agent_name, arg.agent_name)
                rnd_branch.add(f"[cyan]{agent_label}[/]: {arg.content[:200]}")

    console.print(tree)
    console.print()


def _show_p4_theories(ctx) -> None:
    """显示理论评估结果"""
    p4 = ctx.phase_outputs.get("P4", {})
    if p4.get("status") != "done":
        return

    table = Table(title="投资理论评估")
    table.add_column("理论", style="cyan")
    table.add_column("评分", justify="right")

    scores = p4.get("scores", {})
    for theory_name in p4.get("theories", []):
        theory_scores = scores.get(theory_name, [0])
        avg = sum(theory_scores) / len(theory_scores) if theory_scores else 0
        color = "green" if avg >= 60 else "yellow" if avg >= 40 else "red"
        table.add_row(
            _theory_label(theory_name),
            f"[{color}]{avg:.0f}[/{color}]",
        )

    console.print(table)
    console.print()


def _show_p6_risk(ctx) -> None:
    """显示风险评估结果"""
    p6 = ctx.phase_outputs.get("P6", {})
    if p6.get("status") != "done":
        return

    level = p6.get("risk_level", "未知")
    level_color = {"低": "green", "中": "yellow", "高": "red"}.get(level, "white")

    table = Table(title="综合风险评估")
    table.add_column("指标", style="cyan")
    table.add_column("数值", justify="right")
    table.add_row("风险评分", f"{p6.get('risk_score', 0):.0f}/100")
    table.add_row("风险等级", f"[{level_color}]{level}[/{level_color}]")
    table.add_row("最坏损失", f"{p6.get('worst_case_loss_pct', 0):.1f}%")
    table.add_row("HHI 集中度", f"{p6.get('concentration_hhi', 0):.0f}")

    vol = p6.get("portfolio_vol")
    if vol is not None:
        table.add_row("组合波动率", f"{vol:.2f}%")

    risk_flags = p6.get("risk_flags", [])
    if risk_flags:
        table.add_row("风险提示", "\n".join(risk_flags[:3]))

    console.print(table)
    console.print()


def _show_p7_recommendation(ctx) -> None:
    """显示操作推荐结果"""
    p7 = ctx.phase_outputs.get("P7", {})
    if p7.get("status") != "done":
        return

    tree = Tree("[bold cyan]操作推荐[/bold cyan]")
    tree.add(f"[bold]行动: {p7.get('action', '')}[/bold]")
    tree.add(f"综合评分: {p7.get('composite_score', 0):.1f}")
    tree.add(f"风险等级: {p7.get('risk_level', '未知')}")
    tree.add(f"理论平均: {p7.get('theory_avg_score', 0):.1f}")
    tree.add(f"风险评分: {p7.get('risk_score', 0):.0f}")

    reason = p7.get("reason", "")
    if reason:
        tree.add(f"理由: {reason}")

    pos_actions = p7.get("position_actions", [])
    if pos_actions:
        pos_branch = tree.add("标的建议")
        for pa in pos_actions:
            color = {"持有": "green", "观察": "yellow", "关注": "red"}.get(pa["action"], "white")
            pos_branch.add(f"{pa['symbol']} {pa['name']}: [{color}]{pa['action']}[/{color}]")

    disclaimer = p7.get("disclaimer", "")
    if disclaimer:
        tree.add(f"[dim]{disclaimer}[/dim]")

    console.print(tree)
    console.print()


def _theory_label(name: str) -> str:
    labels = {
        "value": "价值投资",
        "growth": "成长投资",
        "all_weather": "全天候投资",
        "quant": "量化多因子",
        "behavioral": "行为金融",
    }
    return labels.get(name, name)


def analyze_cmd(csv_path: str, stages: Optional[str] = None) -> None:
    """加载持仓 CSV、运行全流水线分析、显示各阶段结果"""
    positions = load_positions_from_csv(csv_path)
    portfolio = Portfolio(positions=positions)
    portfolio.recalc()

    _show_positions(portfolio)

    # 运行分析流水线
    target_stages = stages.split(",") if stages else None
    pipeline = AnalysisPipeline()
    ctx = pipeline.run(portfolio, stages=target_stages)

    # 显示各阶段结果
    for phase in (target_stages or ["P2", "P3", "P4", "P5", "P6", "P7"]):
        output = ctx.phase_outputs.get(phase, {})
        status = output.get("status", "unknown")
        if status == "not_implemented" or status == "skipped":
            continue

        if phase == "P3":
            _show_p3_portfolio(ctx)
        elif phase == "P4":
            _show_p4_theories(ctx)
        elif phase == "P5":
            _show_p5_debate(ctx)
        elif phase == "P6":
            _show_p6_risk(ctx)
        elif phase == "P7":
            _show_p7_recommendation(ctx)

    console.print("[green]OK 分析完成[/green]")
