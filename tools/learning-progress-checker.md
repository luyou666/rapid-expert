# Tool Spec: learning_progress_checker

## 目标

根据用户测试表现和交付物质量，判断是否需要压缩或延长学习周期。

## 输入

```json
{
  "current_day": 3,
  "planned_days": 7,
  "quiz_scores": [],
  "deliverables": [],
  "weaknesses": [],
  "risk_level": "low/medium/high"
}
```

`planned_days` 和 `recommended_days` 只能取 5、7、9、12。

## 输出

```json
{
  "status": "on_track/extend/shorten",
  "recommended_days": 9,
  "reason": "原因",
  "next_actions": []
}
```
