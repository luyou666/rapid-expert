# Tool Spec: case_extractor

## 目标

从资料中提取成功、失败、争议、监管和商业模式变化案例。

## 输入

```json
{
  "documents": [],
  "case_types": ["success", "failure", "controversy", "regulatory_change"],
  "domain": "目标领域"
}
```

## 输出

```json
{
  "cases": [
    {
      "name": "案例名称",
      "type": "failure",
      "background": "",
      "key_events": [],
      "stakeholders": [],
      "decision_logic": "",
      "result": "",
      "lesson": "",
      "sources": []
    }
  ]
}
```

