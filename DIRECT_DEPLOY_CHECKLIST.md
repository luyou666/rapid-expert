# 直接部署检查清单

## 法律和安全前置

- [x] 已加入 MIT License
- [x] 已加入免责声明
- [x] 已加入 SECURITY.md
- [x] 已加入 CONTRIBUTING.md
- [x] 已加入 NOTICE.md
- [x] 已加入 .gitignore，避免提交缓存、环境变量和运行输出

部署前请确认使用者理解：本项目仅用于学习、研究、资料整理和 Agent 工作流编排，不构成任何专业意见。

## 已满足

- [x] 根级统一 CLI：`scripts/rapid_expert.py`
- [x] 最小 Agent Harness：`scripts/harness.py`
- [x] Harness 会话状态、事件日志和输出目录：`sessions/<session-id>/`
- [x] Harness session-id 路径穿越防护
- [x] Harness `no_network=true` 时跳过 GitHub 网络调用
- [x] Harness 工具执行权限白名单：`harness/config/permission_profile.json`
- [x] Harness 支持单步执行：`scripts/harness.py step`
- [x] Harness 支持分段执行：`--from-step` / `--to-step`
- [x] Harness 输出 `manifest.json`
- [x] 标准库 HTTP API：`scripts/harness_server.py`
- [x] MCP 风格 stdio JSON-RPC 外壳：`scripts/harness_mcp.py`
- [x] 文件型任务队列和 Worker：`scripts/harness_queue.py`
- [x] 队列任务锁：`queue/locks/`
- [x] 队列取消、重试、连续 Worker 模式
- [x] 敏感工具审批闸门：`approval_required_tools`，审批状态只允许由审批动作写入
- [x] 轻量 RAG 索引构建和检索：`scripts/rag_index.py`
- [x] Python 标准库运行，无强制第三方依赖
- [x] 风险分类和不安全请求拦截
- [x] 5 / 7 / 9 / 12 天自动排期
- [x] 资料候选收集
- [x] 来源启发式分级
- [x] GitHub API 搜索入口
- [x] 报告骨架生成
- [x] 自动验收评分
- [x] 状态 JSON schema
- [x] 来源 JSON schema
- [x] 评估 JSON schema
- [x] OpenClaw / OpenHands 自包含脚本包
- [x] Hermes 工具清单和配置草案
- [x] Claude Code Skill 包说明
- [x] 完整示例领域包
- [x] 部署校验脚本：`scripts/validate_deploy.py`
- [x] 反例测试：假报告必须失败、危险请求必须 blocked、高风险 scan 必须 safe-mode

## 部署前必须做

1. 确认 Python 版本 >= 3.10。
2. 如需更高 GitHub API 额度，设置 `GITHUB_TOKEN`。
3. 运行：

```bash
python scripts/validate_deploy.py
```

4. 用 Harness 实际执行一次：

```bash
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id deploy-smoke
python scripts/harness.py status --session-id deploy-smoke
```

5. 如目标平台支持 HTTP 调用，启动本地 Harness API：

```bash
export HARNESS_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python scripts/harness_server.py --host 127.0.0.1 --port 8765
```

HTTP API 默认需要 `HARNESS_API_TOKEN`，包括本地 `127.0.0.1`。仅在隔离开发环境中使用
`HARNESS_ALLOW_UNAUTHENTICATED=1` 临时关闭鉴权。

健康检查：

```bash
curl -H "Authorization: Bearer <HARNESS_API_TOKEN>" http://127.0.0.1:8765/health
```

6. 如目标平台支持 stdio MCP / JSON-RPC，启动：

```bash
python scripts/harness_mcp.py
```

7. 如目标平台需要队列/Worker 模式：

```bash
python scripts/harness_queue.py submit --task examples/harness/ai-app-startup-task.json
python scripts/harness_queue.py run-next
python scripts/harness_queue.py worker --max-jobs 10 --stop-when-empty
```

8. 用目标平台实际执行一次底层工具链：

```bash
python scripts/rapid_expert.py scan --domain "测试领域" --question "测试问题" --no-network --output outputs/sources_raw.json
python scripts/rapid_expert.py rank --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/rapid_expert.py build --domain "测试领域" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
python scripts/rapid_expert.py evaluate --report outputs/domain_kit_report.md --sources outputs/sources_ranked.json --output outputs/evaluation.json
```

高风险领域必须显式使用 safe mode：

```bash
python scripts/rapid_expert.py scan --domain "金融投资" --question "政策和风险学习" --safe-mode --output outputs/sources_raw.json
```

## 仍需按平台微调

- Hermes 的真实注册 schema 可能因版本不同需要改字段名。
- Claude Code Skill 的知识文件上传方式取决于实际 Skill 安装方式。
- OpenClaw / OpenHands 的工具调用格式可能需要按 runner 的任务配置格式转换。
- 如果目标平台要求 MCP 协议而不是 HTTP，应在当前 CLI / HTTP Harness 外再包一层 MCP server。

## 判断

当前版本已经达到“可交给编程 Agent 部署和执行”的最低标准；若要达到“平台商店级插件”，还需要针对目标平台做实机注册验证。
## Diagnostics and Export

```bash
python scripts/harness_diag.py health
python scripts/harness_diag.py metrics
python scripts/harness_diag.py export --output dist/rapid-expert-harness.zip
```

Export excludes runtime sessions, queued jobs, locks, outputs, caches, logs, and `.env*` files.

## Docker

```bash
docker compose up --build
curl -H "Authorization: Bearer <HARNESS_API_TOKEN>" http://127.0.0.1:8765/health
```

Environment variables are listed in `.env.example`.
