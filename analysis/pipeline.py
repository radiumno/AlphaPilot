"""LangGraph 7 阶段分析流水线 — Phase 2 完整版"""

from typing import Optional
import pandas as pd
from portfolio.models import Portfolio, Position, MarketType
from analysis.models.analysis import ETFAnalysisResult, FundAnalysisResult
from analysis.models.risk import PortfolioRiskResult, RiskMetrics
from analysis.models.correlation import CorrelationMatrix
from analysis.models.theory import TheoryResult, StressTestResult, DebateResult
from analysis.models.collected_data import CollectedData, AssetCollectedData
from analysis.analyzers.etf_analyzer import analyze_etf, calc_concentration
from analysis.analyzers.fund_analyzer import analyze_fund
from analysis.analyzers.risk_analyzer import analyze_risk_single, analyze_portfolio_risk
from analysis.analyzers.correlation import calc_correlation_matrix
from analysis.analyzers.concentration import (
    calc_portfolio_hhi, calc_effective_n, calc_top_n_concentration,
    calc_sector_concentration, detect_concentration_risks,
)
from analysis.analyzers.stress_test import run_stress_test
from analysis.theories import create_registry, TheoryRegistry


class AnalysisContext:
    """贯穿流水线的上下文"""

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.collected_data = CollectedData()
        self.etf_results: dict[str, ETFAnalysisResult] = {}
        self.fund_results: dict[str, FundAnalysisResult] = {}
        self.risk_result: Optional[PortfolioRiskResult] = None
        self.correlation_result: Optional[CorrelationMatrix] = None
        self.stress_test_result: Optional[StressTestResult] = None
        self.theory_results: dict[str, list[TheoryResult]] = {}
        self.debate_results: dict[str, DebateResult] = {}
        self.phase_outputs: dict[str, dict] = {}

    @property
    def positions(self) -> list[Position]:
        return self.portfolio.positions


class AnalysisPipeline:
    """7 阶段分析流水线（数据采集→标的体检→组合分析→理论评估→辩论→风险评估→操作推荐）

    参数:
        cn_provider: 中国市场数据提供者（akshare 等）
        global_provider: 全球市场数据提供者（yfinance 等）
        theory_registry: 投资理论注册表，默认创建含全部 5 个理论
    """

    def __init__(
        self,
        cn_provider=None,
        global_provider=None,
        theory_registry: Optional[TheoryRegistry] = None,
    ):
        self._cn_provider = cn_provider
        self._global_provider = global_provider
        self._theory_registry = theory_registry or create_registry()
        self.phases = {
            "P1": self._phase_data_collection,
            "P2": self._phase_asset_checkup,
            "P3": self._phase_portfolio_analysis,
            "P4": self._phase_theory_evaluation,
            "P5": self._phase_debate,
            "P6": self._phase_risk_assessment,
            "P7": self._phase_recommendation,
        }

    def run(self, portfolio: Portfolio, stages: Optional[list[str]] = None) -> AnalysisContext:
        """运行指定阶段的分析流水线。"""
        ctx = AnalysisContext(portfolio)
        target_phases = stages or list(self.phases.keys())

        for phase_name in target_phases:
            if phase_name not in self.phases:
                continue
            phase_fn = self.phases[phase_name]
            ctx.phase_outputs[phase_name] = phase_fn(ctx) or {}

        return ctx

    # ── P1: 数据采集 ──────────────────────────────────────────────

    def _get_provider(self, pos: Position):
        """根据标的市场选择数据提供者"""
        if pos.market == MarketType.CN:
            return self._cn_provider
        return self._global_provider

    def _phase_data_collection(self, ctx: AnalysisContext) -> dict:
        """P1: 并行获取所有标的数据"""
        if not self._cn_provider and not self._global_provider:
            return {"status": "not_implemented", "note": "未配置数据提供者，使用默认值"}

        stats = {"total": len(ctx.positions), "fetched": 0, "failed": 0, "details": {}}

        for pos in ctx.positions:
            provider = self._get_provider(pos)
            if provider is None:
                stats["details"][pos.symbol] = "无可用数据提供者"
                stats["failed"] += 1
                continue

            try:
                asset_data = AssetCollectedData(
                    symbol=pos.symbol, name=pos.name, data_source=provider.name()
                )

                # ETF → 日线 + 净值
                if pos.asset_type.value == "etf":
                    daily = provider.get_etf_daily(pos.symbol)
                    if daily is not None and not daily.empty:
                        asset_data.daily = daily
                        if "close" in daily.columns:
                            asset_data.nav = daily["close"]

                    nav = provider.get_etf_nav(pos.symbol)
                    if nav is not None:
                        asset_data.nav = nav

                # 主动基金
                elif pos.asset_type.value == "fund":
                    nav = provider.get_fund_nav(pos.symbol)
                    if nav is not None:
                        asset_data.nav = nav

                    info = provider.get_fund_info(pos.symbol)
                    if info:
                        asset_data.info = info

                    holdings = provider.get_fund_holdings(pos.symbol)
                    if holdings is not None and not holdings.empty:
                        asset_data.holdings = holdings.to_dict("records")

                ctx.collected_data.assets[pos.symbol] = asset_data
                stats["details"][pos.symbol] = "ok"
                stats["fetched"] += 1

            except Exception as e:
                stats["details"][pos.symbol] = f"error: {e}"
                stats["failed"] += 1

        return {"status": "done" if stats["fetched"] > 0 else "partial", **stats}

    # ── P2: 标的体检 ──────────────────────────────────────────────

    def _phase_asset_checkup(self, ctx: AnalysisContext) -> dict:
        """P2: 每个标的分独立分析 — ETF 和基金分析"""
        results: dict[str, str] = {}

        for pos in ctx.positions:
            try:
                asset_data = ctx.collected_data.assets.get(pos.symbol)

                if pos.asset_type.value == "etf":
                    daily = asset_data.daily if asset_data else None
                    result = analyze_etf(
                        symbol=pos.symbol, name=pos.name,
                        daily_data=daily,
                        data_source=asset_data.data_source if asset_data else "默认",
                    )
                    ctx.etf_results[pos.symbol] = result
                    results[pos.symbol] = "ok"

                elif pos.asset_type.value == "fund":
                    nav = asset_data.nav if asset_data else None
                    info = asset_data.info if asset_data else None
                    result = analyze_fund(
                        symbol=pos.symbol, name=pos.name,
                        nav_data=nav,
                        info=info,
                        data_source=asset_data.data_source if asset_data else "默认",
                    )
                    ctx.fund_results[pos.symbol] = result
                    results[pos.symbol] = "ok"
                else:
                    results[pos.symbol] = "skipped"
            except Exception as e:
                results[pos.symbol] = f"error: {e}"

        analyzed = len([v for v in results.values() if v == "ok"])
        return {"status": "done", "total": len(ctx.positions), "analyzed": analyzed, "details": results}

    # ── P3: 组合分析 ──────────────────────────────────────────────

    def _phase_portfolio_analysis(self, ctx: AnalysisContext) -> dict:
        """P3: 组合级别的相关性、集中度、压力测试"""
        positions = ctx.positions
        if not positions:
            return {"status": "skipped", "reason": "无持仓数据"}

        # 集中度分析
        hhi = calc_portfolio_hhi(positions)
        effective_n = calc_effective_n(positions)
        top5 = calc_top_n_concentration(positions)
        sector_conc = calc_sector_concentration(positions)
        risks = detect_concentration_risks(hhi, top5)

        # 压力测试
        ctx.stress_test_result = run_stress_test(positions)

        # 相关性 — 从采集数据构建 NAV 字典
        nav_dict: dict[str, pd.Series] = {}
        for pos in positions:
            asset_data = ctx.collected_data.assets.get(pos.symbol)
            if asset_data and asset_data.nav is not None:
                nav_dict[pos.symbol] = asset_data.nav

        ctx.correlation_result = calc_correlation_matrix(nav_dict) if len(nav_dict) >= 2 else None

        return {
            "status": "done",
            "concentration": {"hhi": hhi, "effective_n": effective_n, "top5_pct": top5},
            "risk_flags": risks,
            "sectors": [s.sector for s in sector_conc[:5]],
            "correlation_assets": len(nav_dict),
            "stress_test_scenarios": len(ctx.stress_test_result.scenarios) if ctx.stress_test_result else 0,
        }

    # ── P4: 理论评估 ──────────────────────────────────────────────

    def _phase_theory_evaluation(self, ctx: AnalysisContext) -> dict:
        """P4: 投资理论并行评估"""
        ctx.theory_results = self._theory_registry.run_all(ctx.positions)

        return {
            "status": "done",
            "theories": list(ctx.theory_results.keys()),
            "scores": {
                name: [r.overall_score for r in results]
                for name, results in ctx.theory_results.items()
            },
        }

    # ── P5: AI 辩论 ──────────────────────────────────────────────

    def _phase_debate(self, ctx: AnalysisContext) -> dict:
        """P5: 3 阶段多智能体辩论（结构/调仓/优先级）"""
        from analysis.debate.debate import run_debate

        ctx.debate_results = run_debate(ctx.positions)

        s1 = ctx.debate_results.get("structure")
        no_key = s1 and s1.decision == "skip"

        return {
            "status": "skipped" if no_key else "done",
            "note": "未配置 API Key" if no_key else "辩论完成",
            "stages": {k: {"consensus": v.final_consensus[:100], "confidence": v.confidence}
                       for k, v in ctx.debate_results.items()},
        }

    # ── P6: 风险评估 ──────────────────────────────────────────────

    def _phase_risk_assessment(self, ctx: AnalysisContext) -> dict:
        """P6: 综合风险评估"""
        positions = ctx.positions
        if not positions:
            return {"status": "skipped", "reason": "无持仓数据"}

        # 组合风险分析
        nav_dict = {}
        names = {}
        weights = {}
        total_value = sum(p.market_value for p in positions) or 1

        for pos in positions:
            asset_data = ctx.collected_data.assets.get(pos.symbol)
            if asset_data and asset_data.nav is not None:
                nav_dict[pos.symbol] = asset_data.nav
                names[pos.symbol] = pos.name
            weights[pos.symbol] = pos.market_value / total_value

        if len(nav_dict) >= 1:
            ctx.risk_result = analyze_portfolio_risk(nav_dict, names, weights)

        # 集中度+压力测试风险评估
        hhi = calc_portfolio_hhi(positions)
        top5 = calc_top_n_concentration(positions)
        risk_flags = detect_concentration_risks(hhi, top5)

        stress = ctx.stress_test_result
        worst_loss = stress.worst_case_loss if stress else 0.0

        risk_level = "低"
        score_deduction = 0
        if worst_loss > 25:
            risk_level = "高"
            score_deduction += 20
        elif worst_loss > 15:
            risk_level = "中"
            score_deduction += 10
        if hhi > 2000:
            risk_level = "高"
            score_deduction += 15
        elif hhi > 1000:
            score_deduction += 5

        risk_score = max(0, 100 - score_deduction)

        # 提取风险调整指标（取第一个有数据的标的）
        sortino_ratio = None
        calmar_ratio = None
        info_ratio = None
        annualized_return = None
        downside_vol = None
        if ctx.risk_result and ctx.risk_result.asset_risks:
            for ar in ctx.risk_result.asset_risks:
                if ar.sortino_ratio is not None:
                    sortino_ratio = ar.sortino_ratio
                if ar.calmar_ratio is not None:
                    calmar_ratio = ar.calmar_ratio
                if ar.information_ratio is not None:
                    info_ratio = ar.information_ratio
                if ar.annualized_return is not None:
                    annualized_return = ar.annualized_return
                if ar.downside_volatility > 0:
                    downside_vol = ar.downside_volatility

        return {
            "status": "done",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "worst_case_loss_pct": worst_loss,
            "risk_flags": risk_flags,
            "concentration_hhi": hhi,
            "portfolio_vol": ctx.risk_result.portfolio_volatility if ctx.risk_result else None,
            "downside_vol": downside_vol,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "information_ratio": info_ratio,
            "annualized_return": annualized_return,
        }

    # ── P7: 操作推荐 ──────────────────────────────────────────────

    def _phase_recommendation(self, ctx: AnalysisContext) -> dict:
        """P7: 整合前 6 阶段结果，生成量化操作建议"""
        positions = ctx.positions
        if not positions:
            return {"status": "skipped", "reason": "无持仓数据"}

        # 收集理论信号
        all_signals = {}
        for theory_name, theory_results in ctx.theory_results.items():
            for tr in theory_results:
                for signal in tr.signals:
                    key = f"{theory_name}"

        # 综合各阶段评分
        theory_avg_score = 50.0
        if ctx.theory_results:
            scores = []
            for results in ctx.theory_results.values():
                for r in results:
                    scores.append(r.overall_score)
            theory_avg_score = sum(scores) / len(scores) if scores else 50.0

        risk_score = 100
        risk_level = "低"
        if "P6" in ctx.phase_outputs:
            risk_score = ctx.phase_outputs["P6"].get("risk_score", 100)
            risk_level = ctx.phase_outputs["P6"].get("risk_level", "低")

        # 辩论调整：如果辩论给出高置信度决策，小幅调整评分
        debate_boost = 0
        if ctx.debate_results:
            priority = ctx.debate_results.get("priority")
            if priority and priority.confidence > 0.7:
                debate_boost = 5
            elif priority and priority.confidence > 0.5:
                debate_boost = 2

        # 综合评分 = 理论评分 * 0.6 + 风险评分 * 0.4 + 辩论调整
        composite_score = theory_avg_score * 0.6 + risk_score * 0.4 + debate_boost

        # 操作建议逻辑
        if composite_score >= 70 and risk_level in ("低", "中"):
            action = "持有并关注"
            reason = "综合评分较高且风险可控，建议维持当前持仓"
        elif composite_score >= 50:
            action = "谨慎持有"
            reason = "综合评分中等，建议关注风险敞口"
        elif composite_score >= 30:
            action = "减仓评估"
            reason = "综合评分偏低，建议审视持仓结构，适当降低风险暴露"
        else:
            action = "建议调整"
            reason = "综合评分过低，建议大幅调整持仓结构"

        # 逐标的建议
        position_actions = []
        for pos in positions:
            signal_texts = []
            avg_theory_score = 50
            for results in ctx.theory_results.values():
                for r in results:
                    # 这里假设理论结果按顺序匹配标的（简化实现）
                    avg_theory_score = r.overall_score

            if avg_theory_score >= 70:
                pos_action = "持有"
            elif avg_theory_score >= 40:
                pos_action = "观察"
            else:
                pos_action = "关注"

            position_actions.append({
                "symbol": pos.symbol,
                "name": pos.name,
                "action": pos_action,
            })

        return {
            "status": "done",
            "composite_score": round(composite_score, 1),
            "action": action,
            "reason": reason,
            "risk_level": risk_level,
            "theory_avg_score": round(theory_avg_score, 1),
            "risk_score": risk_score,
            "position_actions": position_actions,
            "disclaimer": "本分析仅供参考，不构成投资建议。投资有风险，决策需谨慎。数据来源详见各阶段输出。",
        }
