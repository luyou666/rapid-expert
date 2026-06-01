# Claude Code 适配说明

## 免责声明

本 Skill 仅用于学习、研究、资料整理和工作流辅助，不构成任何专业意见。高风险领域必须提示用户咨询具备资质的专业人士。

## 使用方式

1. 将本目录作为 Claude Skill 的入口。
2. 本目录已包含最小启动知识：`knowledge/intake-questions.md` 和 `knowledge/adaptive-learning-protocol.md`。
3. 如果平台支持额外知识文件，把根目录下的 `system/`、`skills/`、`rag/`、`memory/`、`safety/` 一并提供给 Claude。
4. 用户发起任务时，Claude 必须先执行启动访谈。
5. Claude 根据学习难度选择 5、7、9 或 12 天路线。

## 推荐文件映射

- `SKILL.md`：主 Skill 说明。
- `knowledge/intake-questions.md`：本地启动访谈问题。
- `knowledge/adaptive-learning-protocol.md`：本地周期选择规则。
- `../../system/master-instructions.md`：总控系统规则。
- `../../system/adaptive-learning-protocol.md`：学习周期规则。
- `../../skills/*.md`：可调用技能。
- `../../safety/*.md`：安全边界。

## Claude Code 项目任务模板

```markdown
请使用“急速专家生成器”Skill，为我生成某领域的 5-12 天实战学习包。

先问我启动访谈问题，不要直接生成完整套件。
```
