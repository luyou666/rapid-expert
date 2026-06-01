# 通用 Markdown 运行手册

## 免责声明

本手册仅用于学习、研究、资料整理和工作流辅助，不构成任何专业意见。高风险领域必须咨询具备资质的专业人士。

## 第一步：启动访谈

复制 `system/intake-questions.md` 给任意 AI 助手，让它先问用户，不要直接生成领域包。

## 第二步：选择学习天数

使用 `system/adaptive-learning-protocol.md`，根据领域难度选择：

- 5 天：轻量领域、目标简单、用户有基础。
- 7 天：默认路线。
- 9 天：需要额外政策、竞品、开源生态研究。
- 12 天：高风险、高专业、强监管或用户完全 0 基础。

## 第三步：生成领域包

使用 `domain-kit-template/` 逐项填充：

- 领域地图
- 产业链
- 护城河
- 工作流
- 术语黑话
- 案例库
- 专家判断框架

## 第四步：执行 Skills

按顺序调用：

1. domain-intake-skill
2. latest-research-skill
3. existing-agent-search-skill
4. industry-map-skill
5. business-model-analysis-skill
6. moat-diagnosis-skill
7. risk-detection-skill
8. practical-task-coach-skill
9. evaluation-skill

## 第五步：验收

使用 `tests/final-practical-evaluation.md` 判断用户是否可以参与业务。
