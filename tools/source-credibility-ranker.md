# Tool Spec: source_credibility_ranker

## 目标

对资料来源进行可信度分级，避免把弱来源当事实。

## 输入字段

- source_url
- publisher
- author
- published_at
- cited_sources
- is_primary_source
- has_data_methodology
- conflict_with_other_sources

## 评分规则

| 分数 | 含义 |
|---|---|
| 90-100 | 一级来源，强证据 |
| 70-89 | 二级来源，可靠但需核验口径 |
| 50-69 | 三级来源，可做线索 |
| 0-49 | 弱来源，不可直接支撑结论 |

