#!/usr/bin/env python3
"""Build a practical domain-kit report from ranked sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DISCLAIMER = (
    "本报告仅用于学习、研究、资料整理和 Agent 工作流辅助，不构成法律、投资、医疗、"
    "心理、网络安全攻击、化工、生物安全、税务、会计、审计、合规或监管意见。"
    "高风险领域的关键判断必须由具备资质的专业人士确认。"
)


def load_sources(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return list(payload.get("sources", []))


def source_table(sources: list[dict]) -> str:
    rows = ["| 来源 | 层级 | 可信度 | 可复用价值 |", "|---|---|---|---|"]
    for item in sources[:12]:
        title = item.get("title") or item.get("url", "")
        url = item.get("url", "")
        tier = item.get("source_tier", "未分层")
        confidence = item.get("confidence", "C")
        summary = item.get("summary") or item.get("collector", "source")
        rows.append(f"| [{title}]({url}) | {tier} | {confidence} | {summary} |")
    return "\n".join(rows)


def source_bullets(sources: list[dict], limit: int = 5) -> str:
    bullets = []
    for item in sources[:limit]:
        title = item.get("title") or item.get("url", "")
        url = item.get("url", "")
        bullets.append(f"- 事实：已收录来源《{title}》，URL：{url}")
    return "\n".join(bullets)


def is_foundation_first(user_level: str) -> bool:
    text = user_level.replace(" ", "").lower()
    hints = ["0基础", "零基础", "完全0基础", "小白", "新手", "入门", "没基础", "没有基础", "听过概念", "不了解", "不懂"]
    return any(hint.replace(" ", "").lower() in text for hint in hints)


def foundation_block(domain: str, user_level: str) -> str:
    if is_foundation_first(user_level):
        return f"""## 2. 低基础启动方式

用户基础：{user_level or "未说明，按 0 基础保守处理"}。

启动原则：先讲概念，再布置任务。Agent 不应一开始要求用户完成复杂行业判断、模型搭建、投资结论或完整商业方案。

通俗比喻：学习“{domain}”像第一次进入一座新城市，先认识地图、路标、常见角色和危险路口，再决定要去哪里办事。

第一轮轻任务：

- 先记住一句话定义：“{domain}”就是发现问题、想办法、试试看。
- 只理解 3 个最小词：问题、办法、试试。
- 找 1 个生活小例子，用“谁遇到什么问题、用了什么办法、试了以后怎样”来复述。
- Agent 每轮都要主动追问用户一个问题，用来收窄场景、基础薄弱点或验收标准。
"""
    return f"""## 2. 启动方式

用户基础：{user_level or "未说明"}。

启动原则：先补框架盲点，再推进实战交付。Agent 应主动追问用户已掌握部分、薄弱点、业务场景和验收标准。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--duration", default="7")
    parser.add_argument("--user-level", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    sources = load_sources(Path(args.sources))
    report = f"""# {args.domain} 专家速成学习包

## 免责声明

{DISCLAIMER}

## 1. 学习周期

建议周期：{args.duration} 天。

推断：该周期适合 0 基础学习者在 AI 或 Agent 工具辅助下完成资料检索、业务拆解、竞品扫描、风险识别和一个可验收的小型交付物。若每天投入低于 1 小时，应延长到 9-12 天；若已有业务背景，可压缩到 5 天。

{foundation_block(args.domain, args.user_level)}

## 3. 资料来源库

{source_table(sources)}

## 4. 领域地图

- 事实：本包围绕“{args.domain}”建立业务理解、资料复用、Agent 执行和交付验收四个模块。
- 推断：新手最容易卡在概念泛化、资料来源不可靠、业务链条不完整和没有明确交付物。
- 待验证：用户实际行业、目标公司、地区政策和可投入时间会影响最终路线。
- 核心问题：如何在短周期内理解客户、场景、价值、成本、收入和风险。
- 主要客户：创业者、求职者、咨询分析师、产品经理和投资研究人员。

## 5. 产业链

| 环节 | 典型玩家 | 价值 | 风险 | 证据使用方式 |
|---|---|---|---|---|
| 上游 | 数据、模型、工具、课程和开源项目提供方 | 提供资料、能力和执行基础 | 来源失真、版本过期、许可限制 | 优先核对官方文档、GitHub、政策和一线资料 |
| 中游 | 产品团队、Agent 编排者、咨询顾问 | 把资料转化为流程、判断和交付物 | 过度自动化、结论缺证据 | 用 RAG、检查清单和人工复核做约束 |
| 下游 | 业务团队、候选人、投资研究者、创业团队 | 使用交付物做决策准备和执行 | 把学习报告误当专业意见 | 设置免责声明、风险边界和验收标准 |

## 6. 可复用方案

| 名称 | 类型 | 可复用部分 | 风险 | 是否采用 |
|---|---|---|---|---|
| 官方文档与行业资料 | 数据源 | 术语、流程、政策、风险边界 | 资料可能不覆盖本地市场 | 采用 |
| GitHub 项目 | 开源项目 | Agent、RAG、CLI、评估脚本 | 许可证、维护状态和安全风险 | 条件采用 |
| 课程与知识库 | 学习资源 | 路线、案例、作业 | 商业宣传偏差 | 条件采用 |
| 本地 harness | 执行框架 | 任务队列、审批、RAG、报告和评估 | 需要人工确认高风险结论 | 采用 |

## 7. 护城河和竞品判断

- 真实护城河：可验证资料库、稳定执行流程、清晰验收标准、用户对具体业务场景的理解。
- 伪护城河：只堆提示词、只收集链接、只生成泛泛总结。
- 关键竞品：通用 Chatbot、课程平台、咨询模板库、垂直 Agent、开源 RAG 项目。
- 替代方案：直接使用 Claude Code、OpenHands、Hermes Agent、NotebookLM、Perplexity 或行业数据库。
- 商业判断：收入来自节省调研时间、提升交付质量和缩短新手上手周期；成本主要来自资料检索、模型调用、人工复核和持续维护。

## 8. 风险边界

- 法律 / 合规风险：不得把报告当作法律、监管、税务、会计或审计意见。
- 金融投资风险：只能辅助研究和资料整理，不能给出买卖建议或收益承诺。
- 数据 / 隐私风险：不得上传敏感个人信息、商业机密或未经授权的数据。
- 网络安全风险：不得生成攻击、绕过、入侵或恶意自动化方案。
- 执行风险：AI 输出必须区分事实、推断、经验判断和待验证内容。

## 9. 实战任务

目标交付物：在 {args.duration} 天内完成一份小型业务研究包，包含领域地图、产业链、资料来源库、竞品判断、风险边界、行动计划和验收清单。

Agent 主动追问规则：每个阶段至少追问用户一个问题，优先确认“我是否讲清楚了基础概念、下一步是否太难、交付物要给谁看、验收标准是什么”。

验收标准：

- 结论有来源支撑，并标明 accessed_at。
- 区分事实、推断、经验判断和待验证内容。
- 至少形成一个可执行动作，例如竞品矩阵、求职项目、创业假设验证、投资研究备忘录或产品 PRD 草案。
- 高风险领域只输出学习、研究和风险识别，不输出专业决策建议。

## 10. 证据摘录

{source_bullets(sources)}

## 11. 后续动作

1. 先回答 Agent 的追问，确认基础水平、业务场景和最终交付物。
2. 如果是低基础，先完成一句话定义、3 个最小词和 1 个生活化案例，再进入复杂任务。
3. 用来源库补充 5-10 条事实，并标记事实、推断、经验判断和待验证。
4. 建立竞品矩阵：目标用户、核心功能、收入模式、成本结构、风险和差异化。
5. 用 Agent 生成第一版交付物，再用验收清单逐项检查。
6. 对涉及法律、金融、医疗、网络安全等高风险部分，交给专业人士复核。
"""

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
