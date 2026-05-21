"""AlphaPilot 阿尔法领航者 — Streamlit 仪表盘主入口"""

import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from portfolio.loader import load_positions_from_csv
from portfolio.models import Portfolio
from analysis.pipeline import AnalysisPipeline
from data.cache import SQLiteCache, CachedProvider

# 缓存
_cache = SQLiteCache()

st.set_page_config(
    page_title="AlphaPilot 阿尔法领航者",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main > div { padding-top: 1.5rem; }
    .stAppHeader { display: none; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🧠 AlphaPilot")
    st.markdown("**阿尔法领航者** — AI 基金/ETF 智能分析系统")
    st.divider()

    uploaded_file = st.file_uploader(
        "上传持仓 CSV",
        type=["csv"],
        help="CSV 需包含 symbol/代码, name/名称, asset_type/类型, shares/份额, cost_price/成本价, market/市场 列",
    )

    st.divider()
    st.caption("支持市场: cn(A股) / us(美股) / hk(港股)")
    st.caption("数据源: akshare · yfinance")
    st.caption("辩论引擎: DeepSeek Flash")

# ── 主区域 ──────────────────────────────────────────────

if uploaded_file is None:
    st.markdown("""
    # AlphaPilot 阿尔法领航者

    ## AI 驱动的投资组合智能分析

    上传你的持仓 CSV 文件，系统将通过 **7 阶段分析流水线** 对你的组合进行全面诊断：

    | 阶段 | 内容 |
    |------|------|
    | P1 数据采集 | 从 akshare/yfinance 拉取实时行情 |
    | P2 标的体检 | ETF 跟踪误差 / 基金夏普比率 |
    | P3 组合分析 | 相关性矩阵 · HHI 集中度 · 压力测试 |
    | P4 理论评估 | 5 大投资理论评分 |
    | P5 辩论引擎 | AI 多智能体对抗辩论 |
    | P6 风险评估 | VaR/CVaR · 风险等级 |
    | P7 操作推荐 | 综合评分 · 逐标的建议 |

    ### 快速开始

    1. 准备一个持仓 CSV（参考[格式说明](#)）
    2. 点击左侧 **"上传持仓 CSV"**
    3. 等待系统完成 7 阶段分析
    4. 在标签页中查看完整结果

    ---
    *仅供参考，不构成投资建议。投资有风险，决策需谨慎。*
    """)
    st.stop()

# ── 已上传文件，运行分析 ──────────────────────────────

# 保存上传文件到临时位置
tmp_csv = ROOT / "data" / "uploads" / uploaded_file.name
tmp_csv.parent.mkdir(parents=True, exist_ok=True)
tmp_csv.write_bytes(uploaded_file.getvalue())

with st.spinner("正在运行 7 阶段分析流水线..."):
    positions = load_positions_from_csv(str(tmp_csv))
    portfolio = Portfolio(positions=positions)
    portfolio.recalc()

    # 尝试创建数据提供者（带缓存）
    cn_provider = None
    global_provider = None
    try:
        from data.providers.akshare_provider import AkshareProvider
        cn_provider = CachedProvider(AkshareProvider(), _cache)
    except Exception:
        pass
    try:
        from data.providers.yfinance_provider import YFinanceProvider
        global_provider = CachedProvider(YFinanceProvider(), _cache)
    except Exception:
        pass

    pipeline = AnalysisPipeline(cn_provider=cn_provider, global_provider=global_provider)
    ctx = pipeline.run(portfolio)

# 存入 session_state 供子页面使用
st.session_state["portfolio"] = portfolio
st.session_state["ctx"] = ctx
st.session_state["positions"] = positions

# ── 持仓概览 ──────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("持仓数量", f"{len(portfolio.positions)} 只")
col2.metric("组合总市值", f"¥{portfolio.total_value:,.0f}")

pnl = sum(p.unrealized_pnl_pct * p.market_value for p in portfolio.positions) / max(portfolio.total_value, 1) * 100
col3.metric("综合盈亏", f"{pnl:+.1f}%", delta_color="inverse")

risk_level = ctx.phase_outputs.get("P6", {}).get("risk_level", "—")
level_color = {"低": "normal", "中": "off", "高": "inverse"}
col4.metric("风险等级", risk_level)

# 持仓表格
st.subheader("📋 持仓明细")
rows = []
for p in portfolio.positions:
    rows.append({
        "代码": p.symbol,
        "名称": p.name,
        "类型": p.asset_type.value,
        "份额": p.shares,
        "成本价": p.cost_price,
        "市值": p.market_value,
        "盈亏%": f"{p.unrealized_pnl_pct*100:+.1f}%",
        "权重%": f"{p.market_value/max(portfolio.total_value,1)*100:.1f}%",
    })
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.success("✅ 分析完成！请在左侧标签页查看详细结果。")
