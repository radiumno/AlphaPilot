"""AlphaPilot — 可复用图表组件"""

from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def correlation_heatmap(
    symbols: list[str],
    matrix: list[list[float]],
    height: int = 400,
) -> go.Figure:
    """生成相关性矩阵热力图"""
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=symbols,
        y=symbols,
        colorscale="RdBu_r",
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in matrix],
        texttemplate="%{text}",
        textfont={"size": 10},
    ))
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def theory_bar_chart(
    theories: list[str],
    scores: dict[str, list[float]],
    labels: dict[str, str],
    height: int = 400,
) -> go.Figure:
    """生成理论评分柱状图"""
    rows = []
    colors = []
    cmap = {"价值投资": "#636EFA", "成长投资": "#EF553B",
            "全天候投资": "#00CC96", "量化多因子": "#FFA15A",
            "行为金融": "#AB63FA"}
    for tn in theories:
        label = labels.get(tn, tn)
        vals = scores.get(tn, [0])
        avg = sum(vals) / len(vals) if vals else 0
        rows.append({"理论": label, "评分": round(avg, 1)})
        colors.append(cmap.get(label, "#636EFA"))

    df = pd.DataFrame(rows)
    fig = px.bar(df, x="理论", y="评分", text_auto=".0f", range_y=[0, 100])
    fig.update_traces(marker_color=colors)
    fig.update_layout(showlegend=False, height=height,
                      margin=dict(l=20, r=20, t=20, b=20))
    fig.add_hline(y=60, line_dash="dash", line_color="green")
    fig.add_hline(y=40, line_dash="dash", line_color="red")
    return fig


def stress_test_chart(
    scenarios: list[dict],
    height: int = 350,
) -> Optional[go.Figure]:
    """生成压力测试柱状图"""
    data = [{"场景": s.get("name", ""), "影响(%)": s.get("impact_pct", 0)}
            for s in scenarios if isinstance(s, dict)]
    if not data:
        return None
    fig = px.bar(pd.DataFrame(data), x="场景", y="影响(%)",
                 color="影响(%)", color_continuous_scale="RdYlGn_r",
                 text_auto=".1f")
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def portfolio_pie_chart(
    symbols: list[str],
    values: list[float],
    names: list[str],
    height: int = 400,
) -> go.Figure:
    """生成组合市值饼图"""
    fig = go.Figure(data=[go.Pie(
        labels=[f"{s} {n}" for s, n in zip(symbols, names)],
        values=values,
        textinfo="label+percent",
        hole=0.4,
    )])
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=20, b=20))
    return fig
