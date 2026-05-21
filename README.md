# 🧠 AlphaPilot 阿尔法领航者

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/radiumno/AlphaPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/radiumno/AlphaPilot/actions/workflows/ci.yml)

**AlphaPilot** — AI 驱动的基金/ETF 智能分析系统。上传持仓 CSV，通过 **7 阶段分析流水线 + 多智能体辩论 + 5 大投资理论**，输出量化的操作推荐。

支持 **A 股基金**（akshare）和 **美股 ETF**（yfinance）混合持仓。

---

## 快速开始

```bash
# 安装（含 CLI + 数据源）
pip install -e ".[dev,all]"

# 分析持仓
python -m cli.main analyze holdings.csv

# 导出 JSON 报告
python -m cli.main report holdings.csv -o report.json

# 启动 Web 仪表盘
streamlit run web/app.py

# 运行测试
pytest tests/ -v
```

## 功能特性

| 特性 | 说明 |
|------|------|
| 📊 **多市场支持** | A 股 ETF/基金 + 美股 ETF 混合分析 |
| 🔬 **标的体检** | 跟踪误差、夏普比率、最大回撤 |
| 📈 **组合分析** | 相关性矩阵、HHI 集中度、5 种压力场景 |
| 🧠 **投资理论** | 价值/成长/全天候/量化因子/行为金融 |
| 🗣️ **AI 辩论引擎** | 保守派 vs 进取派 3 阶段对抗辩论 |
| 🛡️ **风险评估** | VaR/CVaR、波动率、集中度评级 |
| 🌐 **Web 仪表盘** | Streamlit 可视化分析界面 |

## 7 阶段流水线

```
P1 数据采集 ─┬─ akshare: A 股 ETF/基金净值、日线
              └─ yfinance: 美股/全球 ETF 行情

P2 标的体检 ─┬─ ETF: 跟踪误差
              └─ 基金: 夏普比率、最大回撤

P3 组合分析 ─┬─ 相关性矩阵 + 聚类
              ├─ HHI 集中度 + 有效持仓数
              └─ 5 种压力场景测试

P4 理论评估 ─┬─ 价值投资 (Graham/Buffett)
              ├─ 成长投资 (Fisher/Lynch)
              ├─ 全天候 (Dalio 风险平价)
              ├─ 量化多因子 (动量/质量/低波)
              └─ 行为金融 (偏差检测)

P5 辩论引擎 ─┬─ 阶段1: 持仓结构合理性
              ├─ 阶段2: 逐标的调仓辩论
              └─ 阶段3: 优先级裁决

P6 风险评估 ─┬─ VaR (参数法/历史法)
              ├─ CVaR (尾部风险)
              ├─ 下行波动率
              └─ 综合风险等级

P7 操作推荐 ─┬─ 组合综合评分
              ├─ 逐标的操作建议
              └─ 调仓优先级
```

## 决策逻辑

```
综合评分 = 理论评估 × 0.6 + 风险评分 × 0.4 + 辩论加分(0~+5)

          ≥ 70 + 低风险 → 持有并关注
          ≥ 70 + 高风险 → 关注风险敞口
评分区间:  50-70        → 谨慎持有
          30-50        → 减仓评估
          < 30         → 建议调整
```

## Web 仪表盘

```bash
streamlit run web/app.py
```

上传持仓 CSV 即可查看交互式分析结果，包含：
- 持仓概览 + 盈亏分析
- 组合分析 / 理论评估 / 辩论结果 / 操作推荐
- 风险仪表盘（VaR/CVaR/波动率/压力测试）

## 配置

在 `.env` 文件中配置（不进版本控制）：

```env
FUND_DEEPSEEK_API_KEY=sk-xxx  # 辩论引擎需要（选配）
```

无 API Key 时 P5 自动跳过，不影响其他阶段。

## 项目结构

```
AlphaPilot/
├── portfolio/       # 持仓管理（导入/跟踪/再平衡）
├── analysis/        # 核心分析引擎
│   ├── analyzers/   # 金融计算（ETF/基金/风险/相关性/集中度/压力）
│   ├── theories/    # 5 大投资理论
│   ├── debate/      # AI 辩论引擎
│   └── pipeline.py  # 7 阶段流水线编排
├── data/            # 数据层（适配器模式）
│   ├── providers/   # akshare / yfinance
│   └── llm.py       # DeepSeek/OpenAI 兼容客户端
├── web/             # Streamlit 交互式仪表盘
│   ├── app.py       # 主入口
│   ├── pages/       # 分析/风险/历史追踪
│   └── components/  # 可复用图表组件
├── cli/             # Typer 命令行工具
├── config/          # Pydantic Settings 配置
└── tests/           # 75+ 测试
```

## 数据来源

| 市场 | 数据源 | 安装 |
|------|--------|------|
| A 股/中国基金 | [akshare](https://github.com/akfamily/akshare) | `pip install akshare` |
| 美股/全球 ETF | [yfinance](https://github.com/ranaroussi/yfinance) | `pip install yfinance` |

## 安全声明

> **AI 只给建议，不自动交易** — 所有推荐输出需用户手动确认才能执行。
> 每个分析结论都标注数据来源，每个操作建议附带风险提示。
> **投资有风险，此建议仅供参考。**

## 许可证

[MIT](LICENSE)

---

<p align="center">Built with ❤️ and DeepSeek Flash</p>
