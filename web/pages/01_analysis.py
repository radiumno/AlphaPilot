"""AlphaPilot — 分析结果页"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="分析结果 — AlphaPilot", layout="wide")

if "ctx" not in st.session_state:
    st.warning("请先在首页上传持仓 CSV")
    st.stop()

ctx = st.session_state["ctx"]
portfolio = st.session_state["portfolio"]

st.title("📊 分析结果")
st.markdown("---")

# ── 标签页导航 ─────────────────────────────────────────

tabs = st.tabs([
    "📈 组合分析 P3",
    "🏛️ 理论评估 P4",
    "🤖 辩论引擎 P5",
    "📋 操作推荐 P7",
])

# ── P3 组合分析 ────────────────────────────────────────

with tabs[0]:
    p3 = ctx.phase_outputs.get("P3", {})

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("集中度指标")
        conc = p3.get("concentration", {})
        metrics_df = pd.DataFrame([
            ("HHI 集中度", f"{conc.get('hhi', 0):.0f}", "＜1000分散 · ＞2000高度集中"),
            ("有效持仓数", f"{conc.get('effective_n', 0)}", "越大越分散"),
            ("前5大占比", f"{conc.get('top5_pct', 0):.1f}%", "＜40%合理"),
        ], columns=["指标", "数值", "说明"])
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        risk_flags = p3.get("risk_flags", [])
        if risk_flags:
            for flag in risk_flags:
                st.warning(flag)

    with col2:
        st.subheader("行业分布")
        sectors = p3.get("sectors", [])
        if sectors:
            st.dataframe(
                pd.DataFrame([(s, "—") for s in sectors], columns=["行业", "占比"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("无行业分类数据")

    # 压力测试
    st.subheader("压力测试")
    scenarios = p3.get("stress_test_scenarios", [])
    if scenarios and isinstance(scenarios, list) and len(scenarios) > 0:
        scenario_data = []
        for sc in scenarios:
            if isinstance(sc, dict) and "name" in sc and "impact_pct" in sc:
                scenario_data.append({"场景": sc["name"], "影响(%)": sc["impact_pct"]})

        if scenario_data:
            df_sc = pd.DataFrame(scenario_data)
            fig = px.bar(df_sc, x="场景", y="影响(%)",
                         color="影响(%)", color_continuous_scale="RdYlGn_r",
                         text_auto=".1f")
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # 相关性矩阵
    corr = ctx.correlation_result
    if corr and corr.matrix:
        st.subheader("相关性矩阵")
        n = len(corr.symbols)
        if n > 1:
            fig = go.Figure(data=go.Heatmap(
                z=corr.matrix,
                x=corr.symbols,
                y=corr.symbols,
                colorscale="RdBu_r",
                zmin=-1, zmax=1,
                text=[[f"{v:.2f}" for v in row] for row in corr.matrix],
                texttemplate="%{text}",
                textfont={"size": 10},
            ))
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("需要 2 只以上标的相关性矩阵")

    # 组合优化
    opt = ctx.optimization_result
    if opt:
        st.subheader("投资组合优化")
        col_a, col_b = st.columns(2)
        col_a.metric("夏普提升空间", f"{opt.improvement_potential:.1f}%",
                     delta=None if opt.improvement_potential < 5 else "建议优化")

        best = opt.max_sharpe or opt.min_vol
        if best:
            col_b.metric("最优夏普比率", f"{best.sharpe_ratio:.2f}",
                         delta=f"{best.expected_return:.1f}% 收益 / {best.expected_volatility:.1f}% 波动")

        opts = []
        for name, res in [("当前组合", opt.current), ("最大夏普", opt.max_sharpe),
                          ("最小波动", opt.min_vol), ("风险平价", opt.risk_parity)]:
            if res:
                opts.append({
                    "策略": name,
                    "预期收益(%)": res.expected_return,
                    "预期波动(%)": res.expected_volatility,
                    "夏普比率": res.sharpe_ratio,
                    "分散化比率": res.diversification_ratio,
                })

        if opts:
            st.dataframe(pd.DataFrame(opts), use_container_width=True, hide_index=True)

        # 有效前沿
        ef = opt.efficient_frontier
        if len(ef) > 2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[p.volatility for p in ef],
                y=[p.return_val for p in ef],
                mode="markers+lines",
                name="有效前沿",
                marker=dict(color="blue", size=6),
                line=dict(dash="dot", width=1),
            ))
            # 标记当前/最优组合
            for label, res, color in [
                ("当前", opt.current, "red"),
                ("最大夏普", opt.max_sharpe, "green"),
                ("最小波动", opt.min_vol, "orange"),
            ]:
                if res:
                    fig.add_trace(go.Scatter(
                        x=[res.expected_volatility], y=[res.expected_return],
                        mode="markers+text",
                        name=label,
                        marker=dict(color=color, size=12, symbol="star"),
                        text=[label],
                        textposition="top center",
                    ))
            fig.update_layout(
                title="有效前沿",
                xaxis_title="预期波动率(%)",
                yaxis_title="预期收益率(%)",
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("需要 2 只以上有足够历史数据的标的进行组合优化")

# ── P4 理论评估 ────────────────────────────────────────

with tabs[1]:
    p4 = ctx.phase_outputs.get("P4", {})
    scores = p4.get("scores", {})

    labels = {"value": "价值投资", "growth": "成长投资",
              "all_weather": "全天候投资", "quant": "量化多因子",
              "behavioral": "行为金融"}
    colors = {"价值投资": "#636EFA", "成长投资": "#EF553B",
              "全天候投资": "#00CC96", "量化多因子": "#FFA15A",
              "行为金融": "#AB63FA"}

    theory_names = p4.get("theories", [])
    if theory_names and scores:
        rows = []
        for tn in theory_names:
            avg = sum(scores.get(tn, [0])) / len(scores.get(tn, [0])) if scores.get(tn) else 0
            rows.append({"理论": labels.get(tn, tn), "评分": round(avg, 1)})

        df_t = pd.DataFrame(rows)
        fig = px.bar(df_t, x="理论", y="评分", color="理论",
                     color_discrete_map=colors, text_auto=".0f",
                     range_y=[0, 100])
        fig.update_layout(showlegend=False, height=400,
                          margin=dict(l=20, r=20, t=20, b=20))
        fig.add_hline(y=60, line_dash="dash", line_color="green",
                      annotation_text="及格线 60")
        fig.add_hline(y=40, line_dash="dash", line_color="red",
                      annotation_text="警戒线 40")
        st.plotly_chart(fig, use_container_width=True)

        # 详细评分表
        st.subheader("理论评分明细")
        for tn in theory_names:
            label = labels.get(tn, tn)
            vals = scores.get(tn, [])
            if vals:
                avg = sum(vals) / len(vals)
                st.metric(label, f"{avg:.0f}/100",
                          delta=f"标的数: {len(vals)}")

    else:
        st.caption("暂无理论评估结果")

# ── P5 辩论引擎 ────────────────────────────────────────

with tabs[2]:
    p5 = ctx.phase_outputs.get("P5", {})

    if p5.get("status") == "skipped":
        st.info("💡 辩论引擎已跳过 — 如需启用，请配置 DeepSeek API Key")
    elif p5.get("status") != "done":
        st.caption("辩论引擎未运行")
    else:
        debate_results = ctx.debate_results
        if not debate_results:
            st.caption("暂无辩论结果")
        else:
            stage_labels = {
                "structure": "阶段1: 持仓结构合理性",
                "rebalance": "阶段2: 调仓方案",
                "priority": "阶段3: 优先级裁决",
            }
            decision_cn = {"hold": "持有", "adjust": "调整",
                           "reduce": "减仓", "buy": "加仓",
                           "skip": "跳过"}

            for stage_name, debate in debate_results.items():
                label = stage_labels.get(stage_name, stage_name)
                dec = decision_cn.get(debate.decision, debate.decision)

                with st.expander(f"{label} — 决策: {dec} (置信度: {debate.confidence:.0%})", expanded=True):
                    if debate.final_consensus:
                        st.markdown(f"**共识:** {debate.final_consensus[:500]}")

                    for rnd in debate.rounds:
                        st.markdown(f"**辩论{rnd.round_number}**")
                        for arg in rnd.arguments:
                            agent_label = {
                                "conservative": "🛡️ 保守派",
                                "aggressive": "⚡ 进取派",
                                "neutral": "⚖️ 首席分析师",
                            }.get(arg.agent_name, arg.agent_name)
                            with st.container(border=True):
                                st.markdown(f"**{agent_label}** (置信度: {arg.confidence:.0%})")
                                st.caption(arg.content[:500])
                        if rnd.consensus:
                            st.info(f"**本轮共识:** {rnd.consensus[:200]}")

# ── P7 操作推荐 ────────────────────────────────────────

with tabs[3]:
    p7 = ctx.phase_outputs.get("P7", {})

    col1, col2, col3 = st.columns(3)
    col1.metric("综合评分", f"{p7.get('composite_score', 0):.1f}/100")
    col2.metric("建议行动", p7.get("action", "—"))
    col3.metric("风险等级", p7.get("risk_level", "—"))

    pos_actions = p7.get("position_actions", [])
    if pos_actions:
        st.subheader("逐标的建议")
        rows = []
        for pa in pos_actions:
            action_color = {"持有": "🟢", "观察": "🟡", "关注": "🟠", "减仓": "🔴",
                            "建议调整": "🔴"}.get(pa["action"], "⚪")
            rows.append({
                "": action_color,
                "代码": pa["symbol"],
                "名称": pa["name"],
                "建议": pa["action"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.caption("本分析仅供参考，不构成投资建议。")
