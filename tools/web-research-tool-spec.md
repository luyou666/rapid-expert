# Tool Spec: web_research

## 目标

检索目标领域的最新资料，并按来源层级、时间和可信度整理。

## 输入

```json
{
  "domain": "目标领域",
  "question": "要回答的问题",
  "region": "地区",
  "time_range": "时间范围",
  "accessed_at": "访问时间，由工具自动记录",
  "source_priority": ["official", "report", "news", "community"]
}
```

## 输出

```json
{
  "findings": [
    {
      "claim": "结论",
      "source_url": "链接",
      "source_title": "标题",
      "published_at": "发布时间",
      "accessed_at": "访问时间",
      "source_tier": "一级/二级/三级/四级",
      "confidence": "A/B/C/D",
      "verification_required": true,
      "notes": "备注"
    }
  ],
  "conflicts": [],
  "needs_verification": []
}
```

## 调用规则

- 当前状态类问题必须调用。
- 高风险领域必须优先官方和监管来源。
- 输出不得丢失来源时间。
- 网络失败时必须输出检索关键词、失败原因和人工补检建议。
- 运行时可使用 `adapters/openclaw-openhands/scripts/collect_sources.py` 作为最小实现。
