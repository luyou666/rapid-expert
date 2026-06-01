# OpenClaw / OpenHands 类编程 Agent 适配说明

本适配包用于把“急速专家 MVP”作为一个可执行仓库交给编程 Agent。

## 免责声明

本适配包仅用于学习、研究、资料整理和工作流辅助，不构成任何专业意见。编程 Agent 不得把输出当成法律、投资、医疗、网络安全攻击、合规或其他高风险领域的确定性结论。

## 适配目标

让编程 Agent 能够：

- 读取系统规则。
- 访谈用户。
- 生成 5-12 天学习计划。
- 联网检索最新资料和开源项目。
- 写入领域包文件。
- 运行测试和验收。
- 维护任务状态。

## 推荐仓库结构

```text
repo/
├─ README.md
├─ config/
│  ├─ agent-task.md
│  └─ safety-boundaries.md
├─ knowledge/
│  └─ generated-domain-kit/
├─ scripts/
│  ├─ collect_sources.py
│  ├─ rank_sources.py
│  └─ build_report.py
├─ tests/
│  └─ evaluation_checklist.md
└─ outputs/
```

## Agent 执行顺序

1. 读取 `agent-task-template.md`。
2. 询问用户启动问题。
3. 根据难度选择 5、7、9 或 12 天路线。
4. 创建 `knowledge/generated-domain-kit/`。
5. 搜索最新资料和可复用项目。
6. 写入领域地图、产业链、术语、案例、工具、测试。
7. 生成最终业务交付物。
8. 对照验收清单检查。

## 已提供的最小脚本

本适配目录已经提供：

- `scripts/collect_sources.py`
- `scripts/rank_sources.py`
- `scripts/build_report.py`

示例：

```bash
python scripts/collect_sources.py --domain "跨境电商 SaaS" --question "创业方向验证" --region "中国/全球" --time-range "最近 24 个月" --output outputs/sources_raw.json
python scripts/rank_sources.py --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/build_report.py --domain "跨境电商 SaaS" --sources outputs/sources_ranked.json --duration 9 --output outputs/domain_kit_report.md
```

如果网络检索失败，`collect_sources.py` 会输出检索关键词和失败原因，Agent 必须补充人工或平台联网检索。
