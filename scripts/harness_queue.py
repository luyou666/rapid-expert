#!/usr/bin/env python3
"""File-backed job queue for the Rapid Expert Harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.queue import JobQueue  # noqa: E402
from harness.runtime import STEP_ORDER  # noqa: E402


def load_task(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapid Expert Harness queue")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit")
    submit.add_argument("--task", required=True)
    submit.add_argument("--session-id")
    submit.add_argument("--from-step", choices=STEP_ORDER)
    submit.add_argument("--to-step", choices=STEP_ORDER)
    submit.add_argument("--max-attempts", type=int, default=3)

    status = sub.add_parser("status")
    status.add_argument("--job-id", required=True)

    sub.add_parser("list")
    sub.add_parser("run-next")
    run_all = sub.add_parser("run-all")
    run_all.add_argument("--limit", type=int, default=100)

    approve = sub.add_parser("approve")
    approve.add_argument("--job-id", required=True)
    approve.add_argument("--tool", required=True, choices=STEP_ORDER)

    cancel = sub.add_parser("cancel")
    cancel.add_argument("--job-id", required=True)

    retry = sub.add_parser("retry")
    retry.add_argument("--job-id", required=True)

    worker = sub.add_parser("worker")
    worker.add_argument("--poll-interval", type=float, default=float(os.environ.get("HARNESS_WORKER_POLL_INTERVAL", "2")))
    worker.add_argument("--max-jobs", type=int, default=int(os.environ.get("HARNESS_WORKER_MAX_JOBS", "0")))
    worker.add_argument("--stop-when-empty", action="store_true")

    args = parser.parse_args()
    queue = JobQueue(ROOT)
    try:
        if args.command == "submit":
            job = queue.submit(load_task(Path(args.task)), args.session_id, args.from_step, args.to_step, args.max_attempts)
            print_json(job)
            return 0
        if args.command == "status":
            print_json(queue.read(args.job_id))
            return 0
        if args.command == "list":
            print_json({"jobs": queue.list_jobs()})
            return 0
        if args.command == "run-next":
            job = queue.run_next()
            print_json(job or {"status": "empty"})
            return 0
        if args.command == "run-all":
            results = []
            for _ in range(args.limit):
                job = queue.run_next()
                if not job:
                    break
                results.append(job)
            print_json({"processed": len(results), "jobs": results})
            return 0
        if args.command == "approve":
            print_json(queue.approve_tool(args.job_id, args.tool))
            return 0
        if args.command == "cancel":
            print_json(queue.cancel(args.job_id))
            return 0
        if args.command == "retry":
            print_json(queue.retry(args.job_id))
            return 0
        if args.command == "worker":
            processed = []
            while True:
                if args.max_jobs and len(processed) >= args.max_jobs:
                    break
                job = queue.run_next()
                if job:
                    processed.append(job)
                    continue
                if args.stop_when_empty:
                    break
                time.sleep(max(args.poll_interval, 0.1))
            print_json({"processed": len(processed), "jobs": processed})
            return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports JSON.
        print_json({"error": str(exc)})
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
