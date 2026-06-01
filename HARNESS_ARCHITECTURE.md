# Harness Architecture

This layer turns the project from a prompt/tool kit into a minimal agent harness.

## Components

- `scripts/harness.py`: CLI entrypoint for the harness loop.
- `harness/runtime.py`: fixed MVP agent loop: risk -> plan -> scan -> rank -> optional GitHub search -> build -> evaluate.
- `harness/tools.py`: safe argv-based tool registry executor. It never concatenates shell strings.
- `harness/permissions.py`: permission checks for allowed tools and Python scripts.
- `harness/state.py`: session directory, `session.json`, `events.jsonl`, and outputs.
- `harness/config/tool_registry.json`: machine-readable tool registry.
- `harness/config/permission_profile.json`: execution allowlist profile.
- `scripts/harness_server.py`: standard-library HTTP wrapper for external agent platforms.
- `scripts/harness_mcp.py`: dependency-free MCP-style JSON-RPC stdio wrapper.
- `scripts/harness_queue.py`: file-backed task queue and worker CLI.
- `scripts/harness_diag.py`: health, metrics, and clean package export CLI.
- `scripts/harness_contract.py`: OpenAPI and MCP tools contract generator.
- `scripts/rag_index.py`: lightweight JSON RAG index builder and searcher.
- `sessions/`: runtime workspace for harness sessions.
- `queue/jobs/`: queued job metadata.
- `queue/locks/`: atomic job claim locks.
- `Dockerfile` and `docker-compose.yml`: containerized HTTP server entrypoint.
- `.env.example`: local environment variable contract.
- `RELEASE_CHECKLIST.md`: release and open-source publishing checklist.

## Current Loop

```text
task.json
  -> risk
  -> plan
  -> scan
  -> rank
  -> rag_index
  -> github_search (optional)
  -> build
  -> evaluate
  -> session state
```

## Safety

- Blocked risk exits the run before tool execution continues.
- High-risk scans use `--safe-mode`.
- Tools are executed via argv lists, not shell command strings.
- Tools and Python script entrypoints are checked against `permission_profile.json`.
- Tools listed in `approval_required_tools` pause at `awaiting_approval` until an approval action records the tool in session or queue state.
- `approved_tools` is internal state and is rejected from external task input.
- Evaluation blocks placeholder, fake, stale example, or fallback-only sources.
- Session IDs are validated to prevent path traversal.
- `no_network=true` skips optional GitHub network search.

## CLI

```bash
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo
python scripts/harness.py status --session-id demo
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo --to-step plan
python scripts/harness.py run --task examples/harness/ai-app-startup-task.json --session-id demo --resume --from-step scan
python scripts/harness.py step --task examples/harness/ai-app-startup-task.json --session-id demo-risk --name risk
```

The `run` command fails on an existing session unless `--resume` is explicitly provided.

## HTTP API

```bash
python scripts/harness_server.py --host 127.0.0.1 --port 8765
```

- `GET /health`
- `POST /sessions`
- `POST /sessions/{session_id}/run`
- `POST /sessions/{session_id}/steps/{tool_name}`
- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/events`
- `POST /jobs`
- `POST /jobs/run-next`
- `POST /jobs/run-all`
- `POST /jobs/{job_id}/approve`
- `POST /jobs/{job_id}/cancel`
- `POST /jobs/{job_id}/retry`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /metrics`
- `GET /openapi.json`

## MCP-Style Stdio

```bash
python scripts/harness_mcp.py
```

The wrapper accepts both newline-delimited JSON-RPC and MCP-style `Content-Length` framed stdio messages.

Supported JSON-RPC methods:

- `initialize`
- `tools/list`
- `tools/call`

Exposed tools:

- `rapid_expert_run`
- `rapid_expert_step`
- `rapid_expert_status`
- `rapid_expert_events`
- `rapid_expert_rag_search`
- `rapid_expert_queue_submit`
- `rapid_expert_queue_run_next`
- `rapid_expert_queue_status`
- `rapid_expert_queue_approve`
- `rapid_expert_queue_cancel`
- `rapid_expert_queue_retry`
- `rapid_expert_health`
- `rapid_expert_metrics`
- `rapid_expert_export_package`

## Queue Worker

```bash
python scripts/harness_queue.py submit --task examples/harness/ai-app-startup-task.json
python scripts/harness_queue.py run-next
python scripts/harness_queue.py worker --max-jobs 10 --stop-when-empty
python scripts/harness_queue.py list
python scripts/harness_queue.py approve --job-id <job_id> --tool github_search
python scripts/harness_queue.py cancel --job-id <job_id>
python scripts/harness_queue.py retry --job-id <job_id>
```

## Diagnostics

```bash
python scripts/harness_diag.py health
python scripts/harness_diag.py metrics
python scripts/harness_diag.py export --output dist/rapid-expert-harness.zip
```

The export command excludes runtime outputs such as `sessions/`, `queue/jobs/`, `queue/locks/`, `outputs/`, `dist/`, caches, logs, and `.env*` files.

## Contracts

```bash
python scripts/harness_contract.py write
python scripts/harness_contract.py openapi
python scripts/harness_contract.py mcp-tools
```

Generated files:

- `deploy/openapi.json`
- `deploy/mcp-tools.json`

## RAG Index

The `rag_index` step writes `sessions/<session-id>/outputs/rag_index.json`.

Standalone usage:

```bash
python scripts/rag_index.py build --sources outputs/sources_ranked.json --output outputs/rag_index.json
python scripts/rag_index.py search --index outputs/rag_index.json --query "target question"
```

## Next Steps

- Replace fixed planner with model-driven planner.
- Add stricter MCP protocol conformance tests against target hosts.
- Add a web UI or operator dashboard.
