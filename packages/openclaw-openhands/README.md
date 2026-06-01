# Rapid Expert MVP for OpenClaw / OpenHands

这是一个可交给编程 Agent 的标准项目包。

## Disclaimer

This package is for learning, research, source organization, and workflow assistance only. It is not professional advice and must not be used for illegal, harmful, deceptive, or unauthorized activity.

## Run

```bash
python scripts/rapid_expert.py plan --domain "AI应用创业" --user-level "零基础" --daily-time "1小时" --goal "创业验证" --output outputs/plan.json
python scripts/rapid_expert.py scan --domain "AI应用创业" --question "创业验证" --output outputs/sources_raw.json
python scripts/rapid_expert.py rank --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/rapid_expert.py build --domain "AI应用创业" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
python scripts/rapid_expert.py evaluate --report outputs/domain_kit_report.md --sources outputs/sources_ranked.json --output outputs/evaluation.json
```

## Agent Task

Read `config/agent-task.md` first. Do not generate a domain kit before intake and risk classification.
