# Hermes Agent Workflow

免责声明：本 workflow 仅用于学习、研究、资料整理和工作流辅助，不构成任何专业意见。

## Commands

本文件描述命令语义；机器可读配置见 `config.yaml`。

### /intake

运行启动访谈，生成用户需求画像。

### /plan

根据领域难度选择 5、7、9 或 12 天路线。

### /scan

联网检索最新资料和已有可复用方案。

最小实现：

```bash
python ../openclaw-openhands/scripts/collect_sources.py --domain "<domain>" --question "<question>" --output outputs/sources_raw.json
python ../openclaw-openhands/scripts/rank_sources.py --input outputs/sources_raw.json --output outputs/sources_ranked.json
```

### /map

生成领域地图、产业链、术语表、护城河分析。

### /train

执行当天学习任务和实战训练。

### /evaluate

运行最终实战验收。

## State

Hermes 应持续维护：

- user_profile
- target_domain
- learning_days
- daily_progress
- weak_points
- source_library
- final_deliverable
- safety_flags

## Completion Criteria

只有当用户完成一个真实业务交付物，并通过 `tests/final-practical-evaluation.md` 的最低标准时，才可判断目标完成。
