#!/usr/bin/env python3
"""Small standard-library HTTP wrapper for the Rapid Expert Harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.contracts import openapi_spec  # noqa: E402
from harness.diagnostics import health_report  # noqa: E402
from harness.queue import JobQueue  # noqa: E402
from harness.runtime import HarnessRuntime  # noqa: E402
from harness.validation import validate_task  # noqa: E402


MAX_BODY_BYTES = int(os.environ.get("HARNESS_MAX_BODY_BYTES", str(1024 * 1024)))


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    try:
        length = int(handler.headers.get("Content-Length", "0") or "0")
    except ValueError as exc:
        raise ValueError("Invalid Content-Length header.") from exc
    if length > MAX_BODY_BYTES:
        raise ValueError(f"Request body exceeds {MAX_BODY_BYTES} bytes.")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8-sig"))


class HarnessRequestHandler(BaseHTTPRequestHandler):
    server_version = "RapidExpertHarness/0.9.1"

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def is_authorized(self) -> bool:
        token = os.environ.get("HARNESS_API_TOKEN", "")
        if not token:
            return os.environ.get("HARNESS_ALLOW_UNAUTHENTICATED") == "1"
        auth = self.headers.get("Authorization", "")
        bearer = f"Bearer {token}"
        return auth == bearer or self.headers.get("X-Harness-Token", "") == token

    def require_authorized(self) -> bool:
        if self.is_authorized():
            return True
        self.send_json(401, {"error": "unauthorized", "message": "Missing or invalid harness API token."})
        return False

    def do_GET(self) -> None:
        if not self.require_authorized():
            return
        path = urlparse(self.path).path.strip("/")
        if path == "health":
            report = health_report(ROOT)
            self.send_json(200 if report.get("ok") else 503, {"service": "rapid-expert-harness", **report})
            return
        if path == "metrics":
            self.send_json(200, {"queue": JobQueue(ROOT).stats(), "health": health_report(ROOT)})
            return
        if path == "openapi.json":
            self.send_json(200, openapi_spec())
            return
        parts = path.split("/")
        if path == "jobs":
            self.send_json(200, {"jobs": JobQueue(ROOT).list_jobs()})
            return
        if len(parts) == 2 and parts[0] == "jobs":
            self.handle_job_status(parts[1])
            return
        if len(parts) == 2 and parts[0] == "sessions":
            self.handle_session_status(parts[1])
            return
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "events":
            self.handle_session_events(parts[1])
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if not self.require_authorized():
            return
        path = urlparse(self.path).path.strip("/")
        try:
            payload = read_json_body(self)
        except json.JSONDecodeError as exc:
            self.send_json(400, {"error": "invalid_json", "message": str(exc)})
            return
        except ValueError as exc:
            self.send_json(413, {"error": "request_too_large", "message": str(exc)})
            return
        parts = path.split("/")
        if path == "jobs":
            self.handle_job_submit(payload)
            return
        if path == "jobs/run-next":
            self.handle_job_run_next()
            return
        if path == "jobs/run-all":
            self.handle_job_run_all(payload)
            return
        if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "approve":
            self.handle_job_approve(parts[1], payload)
            return
        if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "cancel":
            self.handle_job_cancel(parts[1])
            return
        if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "retry":
            self.handle_job_retry(parts[1])
            return
        if path == "sessions":
            self.handle_create_or_run(payload)
            return
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "run":
            self.handle_run_existing(parts[1], payload)
            return
        if len(parts) == 4 and parts[0] == "sessions" and parts[2] == "steps":
            self.handle_step(parts[1], parts[3], payload)
            return
        self.send_json(404, {"error": "not_found"})

    def handle_job_submit(self, payload: dict) -> None:
        task = payload.get("task", {})
        errors = validate_task(task)
        if errors:
            self.send_json(400, {"error": "invalid_task", "details": errors})
            return
        try:
            job = JobQueue(ROOT).submit(task, payload.get("session_id"), payload.get("from_step"), payload.get("to_step"))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns JSON.
            self.send_json(400, {"error": "job_submit_failed", "message": str(exc)})
            return
        self.send_json(200, job)

    def handle_job_status(self, job_id: str) -> None:
        try:
            self.send_json(200, JobQueue(ROOT).read(job_id))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns JSON.
            self.send_json(404, {"error": "job_not_found", "message": str(exc)})

    def handle_job_run_next(self) -> None:
        job = JobQueue(ROOT).run_next()
        self.send_json(200, job or {"status": "empty"})

    def handle_job_run_all(self, payload: dict) -> None:
        queue = JobQueue(ROOT)
        limit = int(payload.get("limit", 100))
        results = []
        for _ in range(max(limit, 0)):
            job = queue.run_next()
            if not job:
                break
            results.append(job)
        self.send_json(200, {"processed": len(results), "jobs": results})

    def handle_job_approve(self, job_id: str, payload: dict) -> None:
        tool = payload.get("tool")
        if not isinstance(tool, str):
            self.send_json(400, {"error": "invalid_tool", "message": "tool must be a string"})
            return
        try:
            self.send_json(200, JobQueue(ROOT).approve_tool(job_id, tool))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns JSON.
            self.send_json(400, {"error": "approval_failed", "message": str(exc)})

    def handle_job_cancel(self, job_id: str) -> None:
        try:
            self.send_json(200, JobQueue(ROOT).cancel(job_id))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns JSON.
            self.send_json(400, {"error": "cancel_failed", "message": str(exc)})

    def handle_job_retry(self, job_id: str) -> None:
        try:
            self.send_json(200, JobQueue(ROOT).retry(job_id))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns JSON.
            self.send_json(400, {"error": "retry_failed", "message": str(exc)})

    def handle_create_or_run(self, payload: dict) -> None:
        task = payload.get("task", {})
        errors = validate_task(task)
        if errors:
            self.send_json(400, {"error": "invalid_task", "details": errors})
            return
        session_id = payload.get("session_id") or f"session-{uuid.uuid4().hex[:8]}"
        self.run_session(session_id, task, bool(payload.get("resume", False)), payload.get("from_step"), payload.get("to_step"))

    def handle_run_existing(self, session_id: str, payload: dict) -> None:
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            if payload.get("task"):
                task = payload["task"]
            elif runtime.state.exists():
                task = runtime.state.task()
            else:
                self.send_json(404, {"error": "session_not_found", "session_id": session_id})
                return
        except ValueError as exc:
            self.send_json(400, {"error": "invalid_session", "message": str(exc)})
            return
        errors = validate_task(task)
        if errors:
            self.send_json(400, {"error": "invalid_task", "details": errors})
            return
        self.run_session(session_id, task, True, payload.get("from_step"), payload.get("to_step"))

    def handle_step(self, session_id: str, tool_name: str, payload: dict) -> None:
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            task = payload.get("task") or (runtime.state.task() if runtime.state.exists() else {})
            errors = validate_task(task)
            if errors:
                self.send_json(400, {"error": "invalid_task", "details": errors})
                return
            state = runtime.run_single_step(task, tool_name, resume=True)
        except Exception as exc:  # noqa: BLE001 - boundary handler returns JSON instead of traceback.
            self.send_json(400, {"error": "step_failed", "message": str(exc)})
            return
        self.send_json(200, self.summary(session_id, state, runtime))

    def run_session(self, session_id: str, task: dict, resume: bool, from_step: str | None, to_step: str | None) -> None:
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            state = runtime.run(task, resume=resume, from_step=from_step, to_step=to_step)
        except Exception as exc:  # noqa: BLE001 - boundary handler returns JSON instead of traceback.
            self.send_json(400, {"error": "run_failed", "message": str(exc)})
            return
        self.send_json(200, self.summary(session_id, state, runtime))

    def handle_session_status(self, session_id: str) -> None:
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            if not runtime.state.exists():
                self.send_json(404, {"error": "session_not_found", "session_id": session_id})
                return
            self.send_json(200, self.summary(session_id, runtime.state.read(), runtime))
        except ValueError as exc:
            self.send_json(400, {"error": "invalid_session", "message": str(exc)})

    def handle_session_events(self, session_id: str) -> None:
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            if not runtime.state.exists():
                self.send_json(404, {"error": "session_not_found", "session_id": session_id})
                return
            events = []
            if runtime.state.events_path.exists():
                for line in runtime.state.events_path.read_text(encoding="utf-8-sig").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
            self.send_json(200, {"session_id": session_id, "events": events})
        except ValueError as exc:
            self.send_json(400, {"error": "invalid_session", "message": str(exc)})

    def summary(self, session_id: str, state: dict, runtime: HarnessRuntime) -> dict:
        outputs = sorted(path.name for path in runtime.state.outputs_dir.glob("*") if path.is_file())
        return {
            "session_id": session_id,
            "status": state.get("status"),
            "steps": [
                {"tool": step.get("tool"), "status": step.get("status"), "returncode": step.get("returncode")}
                for step in state.get("steps", [])
            ],
            "outputs": outputs,
            "session_dir": str(runtime.state.session_dir),
        }

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapid Expert Harness HTTP server")
    parser.add_argument("--host", default=os.environ.get("HARNESS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("HARNESS_PORT", "8765")))
    args = parser.parse_args()
    public_hosts = {"0.0.0.0", "::"}
    if args.host in public_hosts and not os.environ.get("HARNESS_API_TOKEN") and os.environ.get("HARNESS_ALLOW_UNAUTHENTICATED") != "1":
        print(
            json.dumps(
                {
                    "error": "missing_api_token",
                    "message": "Set HARNESS_API_TOKEN before binding the HTTP server to a public interface, or set HARNESS_ALLOW_UNAUTHENTICATED=1 only for isolated local development.",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    server = ThreadingHTTPServer((args.host, args.port), HarnessRequestHandler)
    print(json.dumps({"service": "rapid-expert-harness", "host": args.host, "port": args.port}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
