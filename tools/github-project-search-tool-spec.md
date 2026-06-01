# Tool Spec: github_project_search

## 目标

搜索目标领域已有开源项目、Agent、RAG、MCP、工具链和数据集。

## 输入

```json
{
  "domain": "目标领域",
  "keywords": ["agent", "rag", "mcp", "dataset"],
  "language": "any",
  "min_stars": 0,
  "updated_after": "YYYY-MM-DD"
}
```

## 输出

```json
{
  "projects": [
    {
      "name": "项目名",
      "url": "链接",
      "summary": "功能简介",
      "stars": 0,
      "last_updated": "日期",
      "license": "许可证",
      "tech_stack": [],
      "reusable_parts": [],
      "integration_difficulty": "low/medium/high",
      "maintenance_risk": "low/medium/high",
      "risks": [],
      "recommendation": "adopt/reference/reject"
    }
  ]
}
```

## 调用规则

- 必须记录 stars、最近更新时间、许可证和维护风险。
- 如果无法直接调用 GitHub API，至少用通用网页检索生成候选清单，再人工或 Agent 二次核验。
- 不得只根据 stars 判断是否采用。
