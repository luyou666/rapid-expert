# Hermes RAG Config

## Knowledge Folders

- system/
- domain-kit-template/
- skills/
- rag/
- memory/
- tests/
- safety/

## Retrieval Priority

1. safety/
2. system/
3. skills/
4. rag/
5. domain-kit-template/
6. tests/
7. memory/

## Runtime Retrieval Rules

- 高风险请求先检索 safety。
- 计划排期先检索 adaptive-learning-protocol。
- 资料可信度问题先检索 rag。
- 用户进度问题先检索 memory。

## Required Metadata

RAG 索引中每个切片应保留：

- source_path
- section_title
- updated_at
- source_tier
- safety_relevance
- retrieval_priority
