"""AlphaPilot — 风险仪表盘"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="风险仪表盘 — AlphaPilot", layout="wide")

if "ctx" not in st.session_state:
    st.warning("请先在首页上传持仓 CSV")
    st.stop()

ctx = st.session_state["ctx"]
portfolio = st.session_state["portfolio"]
p6 = ctx.phase_outputs.get("P6", {})

st.title("🛡️ 风险仪表盘")
st.markdown("---")

# ── 风险概览卡片 ─────────────────────────────────────

level = p6.get("risk_level", "未知")
level_color = {"低": "green", "中": "orange", "高": "red"}.get(level, "grey")

col1, col2, col3, col4 = st.columns(4)
col1.metric("风险评分", f"{p6.get('risk_score', 0):.0f}/100")
col2.markdown(f"<h3 style='color:{level_color}'>风险等级: {level}</h3>", unsafe_allow_html=True)
col3.metric("HHI 集中度", f"{p6.get('concentration_hhi', 0):.0f}")
col4.metric("最坏损失", f"{p6.get('worst_case_loss_pct', 0):.1f}%")

risk_flags = p6.get("risk_flags", [])
for flag in risk_flags:
    st.warning(flag)

# ── VaR 指标 ──────────────────────────────────────────

st.subheader("VaR / CVaR 风险价值")

var_data = {}
for key, label in [("var_95", "VaR 95%"), ("var_99", "VaR 99%"),
                     ("cvar_95", "CVaR 95%"), ("cvar_99", "CVaR 99%")]:
    val = p6.get(key)
    if val is not None:
        var_data[label] = val

if var_data:
    df_var = pd.DataFrame([var_data])
    cols = st.columns(len(var_data))
    for i, (k, v) in enumerate(var_data.items()):
        cols[i].metric(k, f"{v:.2f}%", delta=None)

    fig = go.Figure(data=[
        go.Bar(name="VaR/CVaR", x=list(var_data.keys()), y=list(var_data.values()),
               marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"],
               text=[f"{v:.2f}%" for v in var_data.values()],
               textposition="outside")
    ])
    fig.update_layout(height=350, title="风险价值指标对比",
                      margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ── 波动率分析 ────────────────────────────────────────

st.subheader("波动率分析")
col1, col2 = st.columns(2)
col1.metric("组合波动率(年化)", f"{p6.get('portfolio_vol', 0):.2f}%")
col2.metric("下行波动率", f"{p6.get('downside_vol', 0):.2f}%")

# ── 压力测试详情 ──────────────────────────────────────

p3 = ctx.phase_outputs.get("P3", {})
scenarios = p3.get("stress_test_scenarios", [])
if scenarios and isinstance(scenarios, list):
    st.subheader("压力测试场景")
    scenario_data = []
    for sc in scenarios:
        if isinstance(sc, dict):
            scenario_data.append({
                "场景": sc.get("name", ""),
                "影响(%)": sc.get("impact_pct", 0),
            })
    if scenario_data:
        df_sc = pd.DataFrame(scenario_data)
        fig = px.bar(df_sc, x="场景", y="影响(%)",
                     color="影响(%)", color_continuous_scale="RdYlGn_r",
                     text_auto=".1f")
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
        fig.add_hline(y=0, line_color="black", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_sc, use_container_width=True, hide_index=True)

# ── 相关系数详情 ──────────────────────────────────────

corr = ctx.correlation_result
if corr and corr.pairs:
    st.subheader("相关性分析")
    pairs_data = []
    for pair in corr.pairs:
        color = "🔴" if abs(pair.correlation) > 0.7 else "🟡" if abs(pair.correlation) > 0.4 else "🟢"
        risk_label = "高相关" if abs(pair.correlation) > 0.7 else "中相关" if abs(pair.correlation) > 0.4 else "低相关"
        pairs_data.append({
            "": color,
            "标的A": pair.symbol_a,
            "标的B": pair.symbol_b,
            "相关系数": f"{pair.correlation:.3f}",
            "风险提示": risk_label,
        })
    st.dataframe(pd.DataFrame(pairs_data), use_container_width=True, hide_index=True)

# ── 风险调整指标 ──────────────────────────────────────

p2 = ctx.phase_outputs.get("P2", {})
asset_metrics = p2.get("metrics", [])
if asset_metrics:
    st.subheader("标的风险指标")
    rows = []
    for m in asset_metrics:
        if isinstance(m, dict):
            rows.append({
                "标的": m.get("symbol", ""),
                "波动率%": m.get("volatility", 0),
                "最大回撤%": m.get("max_drawdown", 0),
                "夏普比率": m.get("sharpe", 0),
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption("本分析仅供参考，不构成投资建议。")
