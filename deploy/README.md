# 部署说明

本目录说明如何把“急速专家 MVP”交给 Agent 平台使用。

## 免责声明

本项目仅用于学习、研究、资料整理和 Agent 工作流编排，不构成任何专业意见。部署者应确保最终 Agent 不被用于违法、欺诈、规避监管、未授权攻击、非法获取数据或其他有害行为。详见 `../DISCLAIMER.md` 和 `../SECURITY.md`。

## 最小运行环境

- Python 3.10+
- 无强制第三方依赖
- 可选：`GITHUB_TOKEN`，用于提高 GitHub API 额度

## 统一 CLI

根目录提供统一入口：

```bash
python scripts/rapid_expert.py --help
```

常用命令：

```bash
python scripts/rapid_expert.py risk --domain "AI应用创业" --question "创业方向验证"
python scripts/rapid_expert.py plan --domain "AI应用创业" --user-level "零基础" --daily-time "1小时" --goal "创业验证"
python scripts/rapid_expert.py scan --domain "AI应用创业" --question "创业方向验证" --output outputs/sources_raw.json
python scripts/rapid_expert.py rank --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/rapid_expert.py build --domain "AI应用创业" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
python scripts/rapid_expert.py evaluate --report outputs/domain_kit_report.md --sources outputs/sources_ranked.json --output outputs/evaluation.json
```

高风险领域必须显式进入 safe mode：

```bash
python scripts/rapid_expert.py scan --domain "金融投资" --question "政策和风险学习" --safe-mode --output outputs/sources_raw.json
```

## 平台部署包

- Claude Code：见 `packages/claude-code/`
- Hermes Agent：见 `packages/hermes-agent/`
- OpenClaw / OpenHands：见 `packages/openclaw-openhands/`

## 部署前检查

```bash
python -m py_compile scripts/rapid_expert.py scripts/github_search.py adapters/openclaw-openhands/scripts/*.py
python scripts/rapid_expert.py scan --domain "AI应用创业" --question "创业验证" --no-network --output outputs/sources_raw.json
python scripts/rapid_expert.py rank --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/rapid_expert.py build --domain "AI应用创业" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
python scripts/rapid_expert.py evaluate --report outputs/domain_kit_report.md --sources outputs/sources_ranked.json --output outputs/evaluation.json
```

## 部署成熟度说明

当前包已具备最小 CLI、风险拦截、状态 schema、搜索候选收集、来源分级、报告骨架生成和自动验收。部署校验会运行行为反例测试。真实平台的工具注册字段仍可能需要根据平台版本微调。
