#!/usr/bin/env python3
"""Minimal MCP-style JSON-RPC stdio wrapper for Rapid Expert Harness.

This is intentionally dependency-free. It implements the subset needed by
stdio-based agent hosts: initialize, tools/list, and tools/call.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.diagnostics import export_package, health_report  # noqa: E402
from harness.queue import JobQueue  # noqa: E402
from harness.runtime import HarnessRuntime, STEP_ORDER  # noqa: E402
from harness.validation import validate_task  # noqa: E402
from scripts import rag_index  # noqa: E402


MAX_MCP_BODY_BYTES = int(os.environ.get("HARNESS_MCP_MAX_BODY_BYTES", str(1024 * 1024)))


def rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def text_content(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}


def resolve_export_output(value: Any) -> Path:
    output = Path(str(value or "dist/rapid-expert-harness.zip"))
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    dist = (ROOT / "dist").resolve()
    try:
        output.relative_to(dist)
    except ValueError as exc:
        raise ValueError("export output must stay inside the project dist/ directory.") from exc
    if output.suffix.lower() != ".zip":
        raise ValueError("export output must be a .zip file.")
    return output


def summarize(runtime: HarnessRuntime, state: dict[str, Any]) -> dict[str, Any]:
    outputs = sorted(path.name for path in runtime.state.outputs_dir.glob("*") if path.is_file())
    return {
        "session_id": runtime.state.session_id,
        "status": state.get("status"),
        "steps": [
            {"tool": step.get("tool"), "status": step.get("status"), "returncode": step.get("returncode")}
            for step in state.get("steps", [])
        ],
        "outputs": outputs,
        "session_dir": str(runtime.state.session_dir),
    }


def tool_definitions() -> list[dict[str, Any]]:
    task_schema = {
        "type": "object",
        "required": ["domain", "goal"],
        "properties": {
            "domain": {"type": "string", "maxLength": 120},
            "goal": {"type": "string", "maxLength": 4000},
            "question": {"type": "string", "maxLength": 4000},
            "user_level": {"type": "string", "maxLength": 120},
            "daily_time": {"type": "string", "maxLength": 120},
            "region": {"type": "string", "maxLength": 120},
            "time_range": {"type": "string", "maxLength": 120},
            "no_network": {"type": "boolean"},
            "github_query": {"type": "string", "maxLength": 300},
            "min_stars": {"type": "integer"},
            "github_limit": {"type": "integer"},
        },
    }
    return [
        {
            "name": "rapid_expert_run",
            "description": "Run the Rapid Expert Harness loop for a task.",
            "inputSchema": {
                "type": "object",
                "required": ["task"],
                "properties": {
                    "task": task_schema,
                    "session_id": {"type": "string"},
                    "resume": {"type": "boolean"},
                    "from_step": {"type": "string", "enum": STEP_ORDER},
                    "to_step": {"type": "string", "enum": STEP_ORDER},
                },
            },
        },
        {
            "name": "rapid_expert_step",
            "description": "Run one Rapid Expert Harness step.",
            "inputSchema": {
                "type": "object",
                "required": ["session_id", "task", "name"],
                "properties": {
                    "session_id": {"type": "string"},
                    "task": task_schema,
                    "name": {"type": "string", "enum": STEP_ORDER},
                },
            },
        },
        {
            "name": "rapid_expert_status",
            "description": "Read a Rapid Expert Harness session status.",
            "inputSchema": {
                "type": "object",
                "required": ["session_id"],
                "properties": {"session_id": {"type": "string"}},
            },
        },
        {
            "name": "rapid_expert_events",
            "description": "Read JSONL events for a Rapid Expert Harness session.",
            "inputSchema": {
                "type": "object",
                "required": ["session_id"],
                "properties": {"session_id": {"type": "string"}},
            },
        },
        {
            "name": "rapid_expert_rag_search",
            "description": "Search a session RAG index.",
            "inputSchema": {
                "type": "object",
                "required": ["session_id", "query"],
                "properties": {
                    "session_id": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "rapid_expert_queue_submit",
            "description": "Submit a task to the file-backed harness job queue.",
            "inputSchema": {
                "type": "object",
                "required": ["task"],
                "properties": {
                    "task": task_schema,
                    "session_id": {"type": "string"},
                    "from_step": {"type": "string", "enum": STEP_ORDER},
                    "to_step": {"type": "string", "enum": STEP_ORDER},
                },
            },
        },
        {
            "name": "rapid_expert_queue_run_next",
            "description": "Run the next queued harness job.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rapid_expert_queue_list",
            "description": "List queued harness jobs.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rapid_expert_queue_status",
            "description": "Read a queued job by job_id.",
            "inputSchema": {
                "type": "object",
                "required": ["job_id"],
                "properties": {"job_id": {"type": "string"}},
            },
        },
        {
            "name": "rapid_expert_queue_approve",
            "description": "Approve a tool for a queued or awaiting-approval job.",
            "inputSchema": {
                "type": "object",
                "required": ["job_id", "tool"],
                "properties": {"job_id": {"type": "string"}, "tool": {"type": "string", "enum": STEP_ORDER}},
            },
        },
        {
            "name": "rapid_expert_queue_cancel",
            "description": "Cancel a non-running queued harness job.",
            "inputSchema": {
                "type": "object",
                "required": ["job_id"],
                "properties": {"job_id": {"type": "string"}},
            },
        },
        {
            "name": "rapid_expert_queue_retry",
            "description": "Requeue a failed or cancelled harness job if retry attempts remain.",
            "inputSchema": {
                "type": "object",
                "required": ["job_id"],
                "properties": {"job_id": {"type": "string"}},
            },
        },
        {
            "name": "rapid_expert_health",
            "description": "Run harness health diagnostics.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rapid_expert_metrics",
            "description": "Read queue and health metrics.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rapid_expert_export_package",
            "description": "Export a clean deployment zip without runtime outputs.",
            "inputSchema": {
                "type": "object",
                "properties": {"output": {"type": "string"}},
            },
        },
    ]


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "rapid_expert_run":
        task = args.get("task", {})
        errors = validate_task(task)
        if errors:
            return text_content({"error": "invalid_task", "details": errors})
        session_id = args.get("session_id") or f"session-{uuid.uuid4().hex[:8]}"
        runtime = HarnessRuntime(ROOT, session_id)
        state = runtime.run(
            task,
            resume=bool(args.get("resume", False)),
            from_step=args.get("from_step"),
            to_step=args.get("to_step"),
        )
        return text_content(summarize(runtime, state))
    if name == "rapid_expert_step":
        task = args.get("task", {})
        errors = validate_task(task)
        if errors:
            return text_content({"error": "invalid_task", "details": errors})
        runtime = HarnessRuntime(ROOT, args["session_id"])
        state = runtime.run_single_step(task, args["name"], resume=True)
        return text_content(summarize(runtime, state))
    if name == "rapid_expert_status":
        runtime = HarnessRuntime(ROOT, args["session_id"])
        if not runtime.state.exists():
            return text_content({"error": "session_not_found", "session_id": args["session_id"]})
        return text_content(summarize(runtime, runtime.state.read()))
    if name == "rapid_expert_events":
        runtime = HarnessRuntime(ROOT, args["session_id"])
        if not runtime.state.exists():
            return text_content({"error": "session_not_found", "session_id": args["session_id"]})
        events = []
        if runtime.state.events_path.exists():
            for line in runtime.state.events_path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        return text_content({"session_id": args["session_id"], "events": events})
    if name == "rapid_expert_rag_search":
        runtime = HarnessRuntime(ROOT, args["session_id"])
        index_path = runtime.state.outputs_dir / "rag_index.json"
        if not index_path.exists():
            return text_content({"error": "rag_index_not_found", "session_id": args["session_id"]})
        index = json.loads(index_path.read_text(encoding="utf-8-sig"))
        query_tokens = set(rag_index.tokenize(args["query"]))
        results = []
        for doc in index.get("documents", []):
            overlap = sorted(query_tokens & set(doc.get("tokens", [])))
            if not overlap:
                continue
            results.append(
                {
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "score": len(overlap),
                    "matched_terms": overlap[:20],
                }
            )
        results.sort(key=lambda row: -row["score"])
        return text_content({"query": args["query"], "results": results[: int(args.get("limit", 5))]})
    if name == "rapid_expert_queue_submit":
        task = args.get("task", {})
        errors = validate_task(task)
        if errors:
            return text_content({"error": "invalid_task", "details": errors})
        job = JobQueue(ROOT).submit(task, args.get("session_id"), args.get("from_step"), args.get("to_step"))
        return text_content(job)
    if name == "rapid_expert_queue_run_next":
        job = JobQueue(ROOT).run_next()
        return text_content(job or {"status": "empty"})
    if name == "rapid_expert_queue_list":
        return text_content({"jobs": JobQueue(ROOT).list_jobs()})
    if name == "rapid_expert_queue_status":
        return text_content(JobQueue(ROOT).read(args["job_id"]))
    if name == "rapid_expert_queue_approve":
        return text_content(JobQueue(ROOT).approve_tool(args["job_id"], args["tool"]))
    if name == "rapid_expert_queue_cancel":
        return text_content(JobQueue(ROOT).cancel(args["job_id"]))
    if name == "rapid_expert_queue_retry":
        return text_content(JobQueue(ROOT).retry(args["job_id"]))
    if name == "rapid_expert_health":
        return text_content(health_report(ROOT))
    if name == "rapid_expert_metrics":
        return text_content({"queue": JobQueue(ROOT).stats(), "health": health_report(ROOT)})
    if name == "rapid_expert_export_package":
        return text_content(export_package(ROOT, resolve_export_output(args.get("output"))))
    return text_content({"error": "unknown_tool", "name": name})


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    try:
        if method == "initialize":
            return rpc_result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "rapid-expert-harness", "version": "0.9.1"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return rpc_result(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            params = request.get("params", {})
            return rpc_result(request_id, call_tool(params.get("name", ""), params.get("arguments", {})))
        return rpc_error(request_id, -32601, f"Unknown method: {method}")
    except Exception as exc:  # noqa: BLE001 - JSON-RPC boundary must not leak tracebacks.
        return rpc_error(request_id, -32000, str(exc))


def write_response(response: dict[str, Any], mode: str) -> None:
    body = json.dumps(response, ensure_ascii=False)
    if mode == "content-length":
        raw = body.encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw)
        sys.stdout.buffer.flush()
        return
    print(body, flush=True)


def read_content_length_message(first_header: bytes) -> dict[str, Any]:
    headers = [first_header]
    while True:
        line = sys.stdin.buffer.readline()
        if line in {b"\r\n", b"\n", b""}:
            break
        headers.append(line)
    content_length = None
    for header in headers:
        name, _, value = header.decode("ascii", errors="ignore").partition(":")
        if name.lower() == "content-length":
            content_length = int(value.strip())
            break
    if content_length is None:
        raise ValueError("Missing Content-Length header.")
    if content_length > MAX_MCP_BODY_BYTES:
        raise ValueError(f"Content-Length exceeds {MAX_MCP_BODY_BYTES} bytes.")
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def main() -> int:
    while True:
        line = sys.stdin.buffer.readline(MAX_MCP_BODY_BYTES + 1)
        if not line:
            break
        if len(line) > MAX_MCP_BODY_BYTES:
            write_response(rpc_error(None, -32700, f"JSON-RPC line exceeds {MAX_MCP_BODY_BYTES} bytes."), "jsonl")
            break
        if not line.strip():
            continue
        mode = "jsonl"
        try:
            if line.lower().startswith(b"content-length:"):
                mode = "content-length"
                request = read_content_length_message(line)
            else:
                request = json.loads(line.decode("utf-8"))
            response = handle(request)
        except (json.JSONDecodeError, ValueError) as exc:
            response = rpc_error(None, -32700, str(exc))
        if response is not None:
            write_response(response, mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
