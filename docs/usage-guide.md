# 使用指南 — 基金/ETF 智能分析系统

## 一、环境准备

### 1.1 安装依赖

```bash
cd fund

# 最小安装（仅 CLI 核心功能）
pip install -e ".[dev]"

# 完整安装（含 akshare + yfinance 数据源）
pip install -e ".[dev,all]"

# 或分开安装
pip install -e ".[dev,cn]"      # 仅 A 股数据
pip install -e ".[dev,global]"  # 仅全球数据
```

### 1.2 配置 API Key（可选）

辩论引擎需要 DeepSeek API Key。在项目根目录创建 `.env` 文件：

```env
FUND_DEEPSEEK_API_KEY=sk-你的key
```

没有 API Key 时 P5 辩论阶段会自动跳过，不影响其他 6 个阶段。

### 1.3 验证安装

```bash
pytest tests/ -v
# 预期输出: 75 passed
```

---

## 二、准备持仓 CSV

系统从 CSV 文件读取持仓数据，支持中文和英文列名。

### 2.1 必需列

| 英文列名 | 中文列名 | 说明 | 示例 |
|---------|---------|------|------|
| `symbol` | `代码` | 标的代码 | `510050`, `SPY` |
| `name` | `名称` | 标的名称 | `上证50ETF` |
| `asset_type` | `类型` | 资产类型 | `etf`, `fund`, `stock`, `bond`, `reit` |
| `shares` | `份额` | 持有份额 | `10000` |
| `cost_price` | `成本价` | 持仓成本单价 | `3.2` |
| `market` | `市场` | 所属市场 | `cn`, `us`, `hk` |

### 2.2 可选列

| 列名 | 说明 | 默认值 |
|------|------|--------|
| `market_price` | 当前市价（不填则按成本价计） | `0`（等于成本价） |
| `currency` | 币种 | `CNY` |

### 2.3 示例 CSV

**英文列名：**

```csv
symbol,name,asset_type,shares,cost_price,market,market_price
510050,上证50ETF,etf,10000,3.2,cn,3.5
511880,银华日利,bond,5000,100.5,cn,100.8
159915,创业板ETF,etf,8000,1.5,cn,1.2
QQQ,纳斯达克ETF,etf,200,370.5,us,380.0
```

**中文列名（同样支持）：**

```csv
代码,名称,类型,份额,成本价,市场,市价
510050,上证50ETF,etf,10000,3.2,cn,3.5
511880,银华日利,bond,5000,100.5,cn,100.8
```

### 2.4 字段说明

| 字段 | 取值 | 说明 |
|------|------|------|
| `asset_type` | `etf` / `fund` / `stock` / `bond` / `reit` | ETF 会跑跟踪误差分析，基金跑夏普/回撤 |
| `market` | `cn` / `us` / `hk` | 决定使用哪个数据源（akshare 或 yfinance） |

> **注意：** CSV 文件必须用 UTF-8 编码保存。Windows 用户建议用 VS Code 或记事本另存为 UTF-8。

---

## 三、运行分析

### 3.1 基础用法

```bash
python -m cli.main analyze holdings.csv
```

执行全部 7 阶段流水线，终端输出：

```
1. 持仓摘要表格     ← 标的列表 + 市值 + 盈亏%
2. 组合集中度分析   ← HHI、有效持仓数、前 5 大占比
3. 投资理论评估     ← 5 大理论评分
4. 综合风险评估     ← VaR、风险等级、最坏损失
5. 操作推荐         ← 综合评分 + 逐标的建议
```

### 3.2 仅运行指定阶段

```bash
# 仅运行 P3（组合分析）+ P4（理论评估）
python -m cli.main analyze holdings.csv --stages P3,P4

# 仅运行 P6（风险评估）+ P7（操作推荐）
python -m cli.main analyze holdings.csv --stages P6,P7
```

### 3.3 各阶段含义

| 阶段 | 名称 | 输出内容 |
|------|------|---------|
| P1 | 数据采集 | 从 akshare/yfinance 拉取净值、日线、持仓（需安装对应库） |
| P2 | 标的体检 | ETF 跟踪误差 / 基金夏普比率和最大回撤 |
| P3 | 组合分析 | HHI 集中度、有效持仓数、5 种压力测试、相关性 |
| P4 | 理论评估 | 5 大投资理论各自给出评分 0-100 |
| P5 | 辩论引擎 | AI 多智能体对抗辩论（需 API Key） |
| P6 | 风险评估 | VaR/CVaR、风险等级低/中/高、风险评分 |
| P7 | 操作推荐 | 综合评分、持有/观察/关注建议 |

---

## 四、导出 JSON 报告

```bash
# 输出到终端
python -m cli.main report holdings.csv

# 输出到文件
python -m cli.main report holdings.csv -o report.json
```

JSON 报告包含：

```json
{
  "portfolio": {                           // 持仓摘要
    "total_value": 539000,
    "positions": [ { "symbol": "510050", "unrealized_pnl_pct": 9.38 } ]
  },
  "phases": {                              // 各阶段详细结果
    "P3": { "concentration": { "hhi": 8484 } },
    "P4": { "theories": ["value", "growth", ...] },
    "P6": { "risk_score": 75, "risk_level": "中" },
    "P7": { "composite_score": 63.9, "action": "谨慎持有" }
  },
  "theory_scores": {                       // 理论评分明细
    "value": [{"score": 65}],
    "all_weather": [{"score": 70}]
  },
  "stress_test": {                         // 压力测试结果
    "worst_case_loss": 15.5,
    "resilient_assets": ["511880"]
  }
}
```

---

## 五、输出解读

### 5.1 集中度指标

| 指标 | 含义 | 参考值 |
|------|------|--------|
| HHI | Σ(权重²)×10000 | <1000 分散, 1000-2000 中度, >2000 高度集中 |
| 有效持仓数 | 1/HHI×10000 | >10 较分散 |
| 前 5 大占比 | Top5 市值占比 | <40% 较合理 |

### 5.2 理论评分

| 评分区间 | 含义 |
|----------|------|
| 0-39 | 理论认为该标的不符合其投资哲学 |
| 40-59 | 中性 |
| 60-79 | 基本符合 |
| 80-100 | 强烈符合 |

### 5.3 风险等级

| 等级 | 条件 | 建议 |
|------|------|------|
| 低 | 压力测试损失<15%, HHI<1000 | 维持 |
| 中 | 损失15-25% 或 HHI 1000-2000 | 关注 |
| 高 | 损失>25% 或 HHI>2000 | 需调整 |

### 5.4 操作建议

| 建议 | 触发条件 |
|------|---------|
| 持有并关注 | 综合评分≥70 且风险等级低/中 |
| 谨慎持有 | 综合评分 50-70 |
| 减仓评估 | 综合评分 30-50 |
| 建议调整 | 综合评分<30 |

---

## 六、端到端示例

```bash
# 1. 安装
pip install -e ".[dev,all]"

# 2. 准备数据 — 创建 my_holdings.csv
cat > my_holdings.csv << 'CSV'
symbol,name,asset_type,shares,cost_price,market,market_price
510050,上证50ETF,etf,10000,3.2,cn,3.5
511880,银华日利,bond,5000,100.5,cn,100.8
159915,创业板ETF,etf,8000,1.5,cn,1.2
CSV

# 3. 运行分析
python -m cli.main analyze my_holdings.csv

# 4. 导出报告
python -m cli.main report my_holdings.csv -o my_report.json

# 5. 查看报告
cat my_report.json
```

---

## 七、常见问题

**Q: 终端显示乱码？**
A: Windows 终端默认 GBK 编码，建议用 `chcp 65001` 切换 UTF-8，或使用 Windows Terminal。

**Q: P5 辩论阶段显示 "skipped"?**
A: 需要配置 DeepSeek API Key。在 `.env` 中添加 `FUND_DEEPSEEK_API_KEY=sk-xxx`。

**Q: 如何添加美股？**
A: 安装 yfinance（`pip install yfinance`），在 CSV 中填写 `market=us` 和美股代码。

**Q: 市价怎么填？**
A: 不填 `market_price` 列时，系统用成本价计算，盈亏为 0。建议填入当前市价以准确反映持仓盈亏。

**Q: 支持哪些资产类型？**
A: `etf`（ETF）、`fund`（主动基金）、`stock`（股票）、`bond`（债券）、`reit`（REIT）。
