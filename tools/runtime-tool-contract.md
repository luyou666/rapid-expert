# 运行时工具契约

本文件用于把 `tools/` 中的规格落到可执行工作流，避免 Agent 只读到原则但不知道怎么运行。

## 最小可执行链路

OpenClaw / OpenHands 类 Agent 可按以下顺序执行：

```bash
python adapters/openclaw-openhands/scripts/collect_sources.py --domain "目标领域" --question "核心问题" --region "地区" --time-range "最近 24 个月" --output outputs/sources_raw.json
python adapters/openclaw-openhands/scripts/rank_sources.py --input outputs/sources_raw.json --output outputs/sources_ranked.json
python adapters/openclaw-openhands/scripts/build_report.py --domain "目标领域" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
```

## 失败降级

如果网络检索失败，`collect_sources.py` 会输出：

- 已生成的检索关键词
- 错误原因
- `manual_fallback: true`

Agent 必须在报告中标注该状态，并提示需要人工或平台联网工具补检。

## 强制字段

每条来源必须尽量包含：

- title
- url
- query
- accessed_at
- source_tier
- confidence
- verification_required

## 重要限制

`rank_sources.py` 只是启发式评分，不等于事实核验。所有关键结论仍必须回到一级来源或多个独立来源交叉验证。

