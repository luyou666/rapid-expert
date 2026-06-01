#!/usr/bin/env python3
"""Run the Rapid Expert Harness loop."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.runtime import HarnessRuntime  # noqa: E402
from harness.runtime import STEP_ORDER  # noqa: E402
from harness.validation import validate_task  # noqa: E402


def load_task(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def print_state(session_id: str) -> int:
    runtime = HarnessRuntime(ROOT, session_id)
    if not runtime.state.exists():
        print(json.dumps({"error": "session_not_found", "session_id": session_id}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    state = runtime.state.read()
    outputs = sorted(path.name for path in runtime.state.outputs_dir.glob("*") if path.is_file())
    print(
        json.dumps(
            {
                "session_id": session_id,
                "status": state.get("status"),
                "steps": [{"tool": step.get("tool"), "status": step.get("status"), "returncode": step.get("returncode")} for step in state.get("steps", [])],
                "outputs": outputs,
                "session_dir": str(runtime.state.session_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapid Expert Agent Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--task", required=True)
    run.add_argument("--session-id", default="")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--from-step", choices=STEP_ORDER)
    run.add_argument("--to-step", choices=STEP_ORDER)

    step = sub.add_parser("step")
    step.add_argument("--task", required=True)
    step.add_argument("--session-id", required=True)
    step.add_argument("--name", required=True, choices=STEP_ORDER)
    step.add_argument("--resume", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--session-id", required=True)

    approve = sub.add_parser("approve")
    approve.add_argument("--session-id", required=True)
    approve.add_argument("--tool", required=True, choices=STEP_ORDER)

    args = parser.parse_args()
    if args.command == "run":
        task = load_task(Path(args.task))
        task_errors = validate_task(task)
        if task_errors:
            print(json.dumps({"error": "invalid_task", "details": task_errors}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        session_id = args.session_id or f"session-{uuid.uuid4().hex[:8]}"
        try:
            runtime = HarnessRuntime(ROOT, session_id)
            state = runtime.run(task, resume=args.resume, from_step=args.from_step, to_step=args.to_step)
        except (FileExistsError, ValueError) as exc:
            print(json.dumps({"error": "invalid_session", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        print(json.dumps({"session_id": session_id, "status": state["status"], "session_dir": str(runtime.state.session_dir)}, ensure_ascii=False, indent=2))
        return 0 if state["status"] in {"completed", "needs_review", "paused", "awaiting_approval"} else 2
    if args.command == "step":
        task = load_task(Path(args.task))
        task_errors = validate_task(task)
        if task_errors:
            print(json.dumps({"error": "invalid_task", "details": task_errors}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        try:
            runtime = HarnessRuntime(ROOT, args.session_id)
            state = runtime.run_single_step(task, args.name, resume=args.resume)
        except (FileExistsError, ValueError, RuntimeError) as exc:
            print(json.dumps({"error": "step_failed", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        print(json.dumps({"session_id": args.session_id, "status": state["status"], "session_dir": str(runtime.state.session_dir)}, ensure_ascii=False, indent=2))
        return 0 if state["status"] in {"completed", "needs_review", "paused", "awaiting_approval"} else 2
    if args.command == "status":
        try:
            return print_state(args.session_id)
        except ValueError as exc:
            print(json.dumps({"error": "invalid_session", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
    if args.command == "approve":
        try:
            runtime = HarnessRuntime(ROOT, args.session_id)
            if not runtime.state.exists():
                print(json.dumps({"error": "session_not_found", "session_id": args.session_id}, ensure_ascii=False, indent=2), file=sys.stderr)
                return 2
            state = runtime.state.approve_tool(args.tool)
            print(json.dumps({"session_id": args.session_id, "approved_tools": state.get("approved_tools", [])}, ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(json.dumps({"error": "invalid_session", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
