# Rapid Expert

Language: [中文](README.zh-CN.md) | English

![Rapid Expert project showcase](docs/assets/rapid-expert-showcase.svg)

Rapid Expert is a general-purpose "domain expert acceleration agent." Users talk directly with the agent in a terminal, and the agent understands goals, tracks context, plans the learning path, invokes local tools, retrieves sources, executes tasks, and produces deliverables.

It is not a static template bundle or a document factory. Through interactive dialogue, structured learning guidance, source retrieval, risk-boundary checks, and local harness execution, it helps beginners build enough practical understanding of a new field in 5 to 12 days to participate in real business tasks with the support of AI or agent tools.

## Project Positioning

- Interactive CLI agent, with `study hacker` as the main interaction entrypoint.
- Built for learning and business execution: not only chat, not only document generation, but guided task completion.
- Local-first by default, with optional model APIs, GitHub, search, and harness tools.
- Extensible harness layer supporting CLI, HTTP, MCP/stdio, queues, and platform packages.
- Vertical goal: help users quickly enter investment research, startup validation, job search, consulting, and product development contexts.

## Disclaimer

This project is for learning, research, source organization, and agent workflow orchestration only. It is not legal, investment, medical, psychological, cybersecurity, chemical, biosafety, tax, accounting, audit, compliance, regulatory, or other professional advice.

High-risk decisions must be reviewed by qualified professionals with current facts, local laws, and applicable regulations. See [DISCLAIMER.md](DISCLAIMER.md).

## Privacy and Security

This project is local-first and does not intentionally include telemetry or user tracking.

The interactive CLI may create local runtime files such as `.env.local`, `.study-hacker.local.json`, `sessions/`, `outputs/`, `queue/`, and `dist/`. These files may contain prompts, configuration, logs, reports, or execution state. They are excluded by `.gitignore` and should not be committed to GitHub.

If you configure an external model provider, search API, GitHub token, proxy gateway, or custom API base URL, review the provider's privacy policy, data retention behavior, and terms of use first. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

## License

This project is released under the MIT License. See [LICENSE](LICENSE).

## Intended Users

- Investment researchers who need to understand a new industry quickly.
- Founders or product leaders validating a startup direction.
- Job seekers preparing for career transition, interviews, or portfolio work.
- Consultants or analysts who need to produce short-cycle research outputs.
- Product, BD, operations, or strategy teams doing domain research.

## Default Goal

Within 5 to 12 days, the user should be able to:

1. Build a domain map and core vocabulary.
2. Identify upstream and downstream players, key roles, revenue sources, cost structure, moat, and risk boundaries.
3. Use agents to search recent sources, company updates, policies, news, GitHub projects, and existing tools.
4. Complete at least one practical deliverable close to a real business task.
5. Pass a final check: with AI or agent support, the user can discuss the domain, decompose tasks, search for evidence, and make bounded judgments.

## How to Use

1. Run the intake flow in `system/intake-questions.md`.
2. The agent uses `domain-kit-template/` to organize the domain learning path, source structure, and business deliverables.
3. Use `system/adaptive-learning-protocol.md` to create a 5 to 12 day learning plan.
4. Use the skills in `skills/` to drive research, analysis, practice, and evaluation.
5. Use `rag/` for retrieval and evidence management rules.
6. Use `memory/` to track user level, progress, weak points, and formed frameworks.
7. Choose a target platform adapter from `adapters/`.
8. For OpenClaw / OpenHands-style coding agent platforms, use the minimal script chain in `adapters/openclaw-openhands/scripts/` for source collection, ranking, and report generation.

## Compatibility and Adapters

This project is itself a runnable CLI agent, and it also provides adapter materials for:

- Claude Code / Claude Skills
- Hermes Agent
- OpenClaw / OpenHands-style coding agents
- Generic Markdown workflows

## Key Principles

- Clarify domain, user level, goal, and risk before creating the learning route and execution plan.
- Online research must include source, access time, evidence strength, and uncertainty.
- Prefer reuse: search existing agents, open-source projects, skills, RAG systems, courses, and databases before building from scratch.
- In high-risk domains, support learning, risk identification, and compliance framing only. Do not replace qualified professionals.
- Outputs must support real work, not vague concept lists.

## Acceptance Criteria

A valid kit should help the user complete at least one practical task, such as:

- Write an industry analysis report.
- Decide whether a startup direction deserves further validation.
- Decompose a company's business model.
- Compare three competitors.
- Identify risks in a plan.
- Prepare industry knowledge and case answers for interviews.
- Produce verifiable domain hypotheses for product development.

## Agent Harness Layer

This project includes a minimal runnable agent harness that can serve as an execution core for OpenClaw / OpenHands-style coding agent platforms:

- `scripts/harness.py`: unified run entrypoint.
- `harness/runtime.py`: fixed execution loop: `risk -> plan -> scan -> rank -> github_search -> build -> evaluate`.
- `harness/tools.py`: argv-based tool registry and safe execution.
- `harness/permissions.py`: tool permission checks.
- `harness/state.py`: session state, event logs, and output directories.
- `harness/config/tool_registry.json`: machine-readable tool registry.
- `harness/config/permission_profile.json`: permission profile.
- `harness/schemas/task.schema.json`: task input schema.
- `scripts/harness_server.py`: standard-library HTTP API wrapper.
- `scripts/harness_mcp.py`: dependency-free MCP-style JSON-RPC stdio wrapper.
- `scripts/harness_queue.py`: file-backed task queue and worker.
- `scripts/rag_index.py`: lightweight RAG index build and search script.

## Interactive CLI

Install the `study hacker` command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_study_command.ps1
study hacker
```

`study hacker` starts a cyberpunk-style Study Hacker interactive shell. It is the main agent interface: it supports direct chat, adaptive learning guidance, local harness execution, and optional online research.

When a user says they want to become an expert in a field, the CLI first checks their level. For low-level or zero-background users, it starts with a simple definition, three minimum terms, analogies, and small examples before moving into practical tasks.

On first interactive launch, the CLI asks for API provider, base URL, model, and API key. The configuration is stored only in ignored local files: `.study-hacker.local.json` and `.env.local`. After successful setup, it will not ask again. Reconfigure with `/config` inside the shell or run:

```powershell
study hacker --reset-config
```

## Minimal Harness Commands

```bash
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo
python scripts/harness.py status --session-id demo
```

Step-by-step:

```bash
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo --to-step plan
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo --resume --from-step scan
python scripts/harness.py step --task examples/harness/ai-app-startup-task.json --session-id demo-risk --name risk
```

## HTTP API

```bash
export HARNESS_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python scripts/harness_server.py --host 127.0.0.1 --port 8765
curl -H "Authorization: Bearer $HARNESS_API_TOKEN" http://127.0.0.1:8765/health
```

`HARNESS_API_TOKEN` is required by default, including for `127.0.0.1`. Use `HARNESS_ALLOW_UNAUTHENTICATED=1` only for isolated local development where no untrusted local process can reach the port.

Endpoints:

- `GET /health`
- `POST /sessions`
- `POST /sessions/{session_id}/run`
- `POST /sessions/{session_id}/steps/{tool_name}`
- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/events`

## MCP / Stdio

```bash
python scripts/harness_mcp.py
```

Current tools:

- `rapid_expert_run`
- `rapid_expert_step`
- `rapid_expert_status`
- `rapid_expert_events`
- `rapid_expert_rag_search`
- `rapid_expert_queue_submit`
- `rapid_expert_queue_run_next`
- `rapid_expert_queue_status`
- `rapid_expert_queue_approve`

## Queue

```bash
python scripts/harness_queue.py submit --task examples/harness/ai-app-startup-task.json
python scripts/harness_queue.py run-next
python scripts/harness_queue.py worker --max-jobs 10 --stop-when-empty
python scripts/harness_queue.py list
python scripts/harness_queue.py status --job-id <job_id>
```

Approval gate:

```bash
python scripts/harness.py approve --session-id <session_id> --tool github_search
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id <session_id> --resume --from-step github_search
```

For queued jobs:

```bash
python scripts/harness_queue.py approve --job-id <job_id> --tool github_search
python scripts/harness_queue.py run-next
```

`approved_tools` is internal approval state and must not be placed in external task JSON. Approvals must be written through CLI, HTTP, or MCP actions.

Cancel and retry:

```bash
python scripts/harness_queue.py cancel --job-id <job_id>
python scripts/harness_queue.py retry --job-id <job_id>
```

## RAG Index

```bash
python scripts/rag_index.py build --sources outputs/sources_ranked.json --output outputs/rag_index.json
python scripts/rag_index.py search --index outputs/rag_index.json --query "target question"
```

If `no_network=true`, the harness skips GitHub online search and sets the final status to `needs_review` to avoid treating offline placeholder data as a deliverable.

## Diagnostics and Export

```bash
python scripts/harness_diag.py health
python scripts/harness_diag.py metrics
python scripts/harness_diag.py export --output dist/rapid-expert-harness.zip
```

The exported zip excludes runtime directories, queue jobs, locks, local outputs, caches, logs, and `.env*` files.

## Platform Contracts

```bash
python scripts/harness_contract.py write
```

This writes:

- `deploy/openapi.json`
- `deploy/mcp-tools.json`

## Docker

```bash
copy .env.example .env
# Edit .env and set HARNESS_API_TOKEN to a long random token before starting the HTTP API.
docker compose up --build
curl -H "Authorization: Bearer <HARNESS_API_TOKEN>" http://127.0.0.1:8765/health
```

Environment defaults are documented in `.env.example`.

## Release

Before publishing:

```bash
python scripts/harness_contract.py write
python scripts/run_tests.py
python scripts/validate_deploy.py
python scripts/harness_diag.py health
python scripts/harness_diag.py export --output dist/rapid-expert-harness.zip
```

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
