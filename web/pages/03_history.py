"""AlphaPilot — 历史追踪页（占位）"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="历史追踪 — AlphaPilot", layout="wide")

if "ctx" not in st.session_state:
    st.warning("请先在首页上传持仓 CSV")
    st.stop()

st.title("📅 历史追踪")

st.info("""
💡 **即将推出**

历史追踪功能将支持：
- **分析记录保存** — 每次分析结果存入 SQLite，可回顾历史
- **组合变化追踪** — 对比不同时间点的持仓结构和风险变化
- **收益曲线** — 组合净值走势图
- **再平衡提醒** — 当偏离目标配置时自动提醒
""")

st.markdown("---")

st.subheader("示例 — 组合风险趋势")
st.caption("数据积累后将生成趋势图表")

cols = st.columns(3)
cols[0].metric("分析次数", "—", delta=None)
cols[1].metric("上次分析", "—", delta=None)
cols[2].metric("组合变化", "—", delta=None)
