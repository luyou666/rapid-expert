from __future__ import annotations

import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from .runtime import HarnessRuntime, STEP_ORDER
from .state import validate_session_id
from .validation import validate_task


JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_job_id(job_id: str) -> str:
    if not JOB_ID_RE.fullmatch(job_id) or ".." in job_id:
        raise ValueError("job_id must be 1-80 chars: letters, numbers, dot, underscore, or hyphen; it cannot contain '..'.")
    return job_id


class JobQueue:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.jobs_dir = root / "queue" / "jobs"
        self.locks_dir = root / "queue" / "locks"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    def job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{validate_job_id(job_id)}.json"

    def submit(
        self,
        task: dict[str, Any],
        session_id: str | None = None,
        from_step: str | None = None,
        to_step: str | None = None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        errors = validate_task(task)
        if errors:
            raise ValueError("; ".join(errors))
        job_id = f"job-{uuid.uuid4().hex[:10]}"
        resolved_session_id = validate_session_id(session_id or job_id.replace("job-", "session-"))
        job = {
            "job_id": job_id,
            "session_id": resolved_session_id,
            "status": "queued",
            "task": task,
            "from_step": from_step,
            "to_step": to_step,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "attempts": 0,
            "max_attempts": max(1, max_attempts),
            "approved_tools": [],
            "result": {},
            "error": "",
        }
        self.write(job)
        return job

    def read(self, job_id: str) -> dict[str, Any]:
        path = self.job_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Job not found: {job_id}")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def write(self, job: dict[str, Any]) -> None:
        job["updated_at"] = utc_now()
        self.job_path(job["job_id"]).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_jobs(self) -> list[dict[str, Any]]:
        jobs = []
        for path in sorted(self.jobs_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            jobs.append(
                {
                    "job_id": payload.get("job_id"),
                    "session_id": payload.get("session_id"),
                    "status": payload.get("status"),
                    "attempts": payload.get("attempts", 0),
                    "max_attempts": payload.get("max_attempts", 1),
                    "created_at": payload.get("created_at"),
                    "updated_at": payload.get("updated_at"),
                }
            )
        return jobs

    def stats(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        jobs = self.list_jobs()
        for job in jobs:
            status = str(job.get("status") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        locks = [path.name for path in sorted(self.locks_dir.glob("*.lock")) if path.is_dir()]
        return {
            "total": len(jobs),
            "by_status": by_status,
            "locks": locks,
            "lock_count": len(locks),
        }

    def lock_path(self, job_id: str) -> Path:
        return self.locks_dir / f"{validate_job_id(job_id)}.lock"

    def acquire_lock(self, job_id: str) -> bool:
        lock_path = self.lock_path(job_id)
        try:
            lock_path.mkdir()
        except FileExistsError:
            return False
        (lock_path / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "locked_at": utc_now()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def release_lock(self, job_id: str) -> None:
        lock_path = self.lock_path(job_id)
        if lock_path.exists():
            for child in lock_path.iterdir():
                if child.is_file():
                    child.unlink()
            lock_path.rmdir()

    def next_queued(self) -> dict[str, Any] | None:
        for path in sorted(self.jobs_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if payload.get("status") == "queued":
                return payload
        return None

    def claim_next(self) -> dict[str, Any] | None:
        for path in sorted(self.jobs_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if payload.get("status") != "queued":
                continue
            job_id = payload.get("job_id", "")
            if not self.acquire_lock(job_id):
                continue
            latest = self.read(job_id)
            if latest.get("status") != "queued":
                self.release_lock(job_id)
                continue
            return latest
        return None

    def run_job(self, job: dict[str, Any]) -> dict[str, Any]:
        job["status"] = "running"
        job["error"] = ""
        job["attempts"] = int(job.get("attempts", 0)) + 1
        self.write(job)
        try:
            runtime = HarnessRuntime(self.root, job["session_id"])
            state = runtime.run(
                job["task"],
                resume=runtime.state.exists(),
                from_step=job.get("from_step"),
                to_step=job.get("to_step"),
                approved_tools=job.get("approved_tools", []),
            )
            job["result"] = {
                "session_id": job["session_id"],
                "session_status": state.get("status"),
                "session_dir": str(runtime.state.session_dir),
            }
            job["status"] = state.get("status", "failed")
            if job["status"] in {"completed", "needs_review", "paused"}:
                job["status"] = "done"
            if job["status"] == "awaiting_approval":
                job["error"] = "Waiting for approval."
        except Exception as exc:  # noqa: BLE001 - queue boundary stores failures as data.
            job["status"] = "failed"
            job["error"] = str(exc)
        self.write(job)
        return job

    def run_next(self) -> dict[str, Any] | None:
        job = self.claim_next()
        if not job:
            return None
        try:
            return self.run_job(job)
        finally:
            self.release_lock(job["job_id"])

    def cancel(self, job_id: str) -> dict[str, Any]:
        if not self.acquire_lock(job_id):
            raise RuntimeError("Cannot cancel a locked job.")
        try:
            job = self.read(job_id)
            if job.get("status") == "running":
                raise RuntimeError("Cannot cancel a running job with the file-backed queue.")
            job["status"] = "cancelled"
            job["error"] = "Cancelled by user."
            self.write(job)
            return job
        finally:
            self.release_lock(job_id)

    def retry(self, job_id: str) -> dict[str, Any]:
        if not self.acquire_lock(job_id):
            raise RuntimeError("Cannot retry a locked job.")
        try:
            job = self.read(job_id)
            if job.get("status") == "running":
                raise RuntimeError("Cannot retry a running job.")
            attempts = int(job.get("attempts", 0))
            max_attempts = int(job.get("max_attempts", 1))
            if attempts >= max_attempts:
                raise RuntimeError("Retry limit reached.")
            job["status"] = "queued"
            job["error"] = ""
            self.write(job)
            return job
        finally:
            self.release_lock(job_id)

    def approve_tool(self, job_id: str, tool_name: str) -> dict[str, Any]:
        if tool_name not in STEP_ORDER:
            raise ValueError(f"Unknown tool: {tool_name}")
        if not self.acquire_lock(job_id):
            raise RuntimeError("Cannot approve a locked job.")
        try:
            job = self.read(job_id)
            approved = set(job.get("approved_tools", []))
            approved.add(tool_name)
            job["approved_tools"] = sorted(approved)
            if job.get("status") == "awaiting_approval":
                job["status"] = "queued"
            self.write(job)
            if (self.root / "sessions" / job["session_id"] / "session.json").exists():
                runtime = HarnessRuntime(self.root, job["session_id"])
                runtime.state.approve_tool(tool_name)
            return job
        finally:
            self.release_lock(job_id)
