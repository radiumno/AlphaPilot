# Contributing to AlphaPilot

感谢您对 AlphaPilot 的关注！欢迎贡献代码、报告问题或提出新功能建议。

## 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m "feat: add your feature"`)
4. 推送到分支 (`git push origin feat/your-feature`)
5. 创建 Pull Request

## 代码规范

- **Python 版本**: 3.11+
- **代码风格**: 遵循 PEP 8，使用 `ruff` 格式化
- **类型注解**: 所有公共函数和类需要类型注解
- **测试**: 新功能需包含测试，运行 `pytest tests/ -v` 确认全部通过

## 提交信息格式

```
<type>: <简短描述>

<详细说明（可选）>
```

类型: `feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore`

## 项目结构

```
alphapilot/
├── portfolio/      # 持仓管理
├── analysis/       # 核心分析引擎
│   ├── analyzers/  # 金融计算模块
│   ├── theories/   # 投资理论
│   ├── debate/     # AI 辩论引擎
│   └── pipeline.py # 7 阶段流水线
├── data/           # 数据层（适配器模式）
├── cli/            # Typer CLI
├── web/            # Streamlit 仪表盘
├── config/         # 配置管理
└── tests/          # 测试
```

## 首次贡献

1. 安装开发依赖: `pip install -e ".[dev]"`
2. 运行测试: `pytest tests/ -v`
3. 确认 75+ 测试全部通过
