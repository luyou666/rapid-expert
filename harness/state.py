from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def validate_session_id(session_id: str) -> str:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise ValueError("session_id must be 1-80 chars: letters, numbers, dot, underscore, or hyphen; it cannot start with dot.")
    if ".." in session_id:
        raise ValueError("session_id cannot contain '..'.")
    return session_id


def strip_internal_task_fields(task: dict[str, Any]) -> dict[str, Any]:
    clean = dict(task)
    clean.pop("approved_tools", None)
    return clean


class SessionState:
    def __init__(self, root: Path, session_id: str) -> None:
        self.root = root
        self.session_id = validate_session_id(session_id)
        self.session_dir = root / "sessions" / session_id
        self.outputs_dir = self.session_dir / "outputs"
        self.events_path = self.session_dir / "events.jsonl"
        self.state_path = self.session_dir / "session.json"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.state_path.exists()

    def init(self, task: dict[str, Any], resume: bool = False) -> None:
        task = strip_internal_task_fields(task)
        if self.state_path.exists():
            if not resume:
                raise FileExistsError(f"Session already exists: {self.session_id}. Use --resume or choose a new session id.")
            self.event("session_resumed", {"task": task})
            return
        self.write(
            {
                "session_id": self.session_id,
                "task": task,
                "approved_tools": [],
                "status": "created",
                "steps": [],
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        self.event("session_created", {"task": task})

    def read(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8-sig"))

    def task(self) -> dict[str, Any]:
        return strip_internal_task_fields(self.read().get("task", {}))

    def update_task(self, task: dict[str, Any]) -> None:
        state = self.read()
        state["task"] = strip_internal_task_fields(task)
        self.write(state)
        self.event("task_updated", {"task": task})

    def approve_tool(self, tool_name: str) -> dict[str, Any]:
        state = self.read()
        approved = set(state.get("approved_tools", []))
        legacy_task = state.setdefault("task", {})
        approved.update(legacy_task.pop("approved_tools", []))
        approved.add(tool_name)
        state["approved_tools"] = sorted(approved)
        self.write(state)
        self.event("tool_approved", {"tool": tool_name})
        return state

    def is_tool_approved(self, tool_name: str) -> bool:
        if not self.state_path.exists():
            return False
        return tool_name in set(self.read().get("approved_tools", []))

    def write(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = utc_now()
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def event(self, event_type: str, payload: dict[str, Any]) -> None:
        row = {"ts": utc_now(), "type": event_type, "payload": payload}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def record_step(self, step: dict[str, Any]) -> None:
        state = self.read()
        state.setdefault("steps", []).append(step)
        state["status"] = step.get("status", state.get("status", "running"))
        self.write(state)
        self.event("step_recorded", step)

    def latest_step(self, tool_name: str) -> dict[str, Any] | None:
        for step in reversed(self.read().get("steps", [])):
            if step.get("tool") == tool_name:
                return step
        return None

    def is_step_done(self, tool_name: str) -> bool:
        step = self.latest_step(tool_name)
        return bool(step and step.get("status") in {"completed", "skipped"})

    def output_path(self, name: str) -> Path:
        return self.outputs_dir / name
