from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from .queue import JobQueue


REQUIRED_FILES = [
    "scripts/harness.py",
    "scripts/harness_server.py",
    "scripts/harness_mcp.py",
    "scripts/harness_queue.py",
    "scripts/rag_index.py",
    "scripts/rapid_expert.py",
    "harness/config/tool_registry.json",
    "harness/config/permission_profile.json",
    "harness/schemas/task.schema.json",
    "deploy/agent-manifest.json",
    "README.md",
    "LICENSE",
    "DISCLAIMER.md",
    "SECURITY.md",
]

EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

EXCLUDED_PREFIXES = (
    "sessions/",
    "queue/jobs/",
    "queue/locks/",
    "outputs/",
    "dist/",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def session_stats(root: Path) -> dict[str, Any]:
    sessions_dir = root / "sessions"
    by_status: dict[str, int] = {}
    total = 0
    if not sessions_dir.exists():
        return {"total": 0, "by_status": {}}
    for state_path in sessions_dir.glob("*/session.json"):
        try:
            payload = load_json(state_path)
        except json.JSONDecodeError:
            status = "invalid_json"
        else:
            status = str(payload.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        total += 1
    return {"total": total, "by_status": by_status}


def config_status(root: Path) -> dict[str, Any]:
    results = {}
    for rel in ["harness/config/tool_registry.json", "harness/config/permission_profile.json", "deploy/agent-manifest.json"]:
        path = root / rel
        try:
            load_json(path)
            results[rel] = "ok"
        except Exception as exc:  # noqa: BLE001 - diagnostics should collect all failures.
            results[rel] = f"error: {exc}"
    return results


def health_report(root: Path) -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    queue_stats = JobQueue(root).stats()
    report = {
        "ok": not missing and all(value == "ok" for value in config_status(root).values()),
        "missing": missing,
        "configs": config_status(root),
        "queue": queue_stats,
        "sessions": session_stats(root),
    }
    report["ok"] = report["ok"] and queue_stats.get("lock_count", 0) == 0
    return report


def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if path.name.endswith((".pyc", ".pyo", ".log")):
        return False
    if path.name.startswith(".env"):
        return False
    return path.is_file()


def export_package(root: Path, output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not should_include(path, root):
                continue
            archive.write(path, path.relative_to(root).as_posix())
            count += 1
    return {"output": str(output), "files": count, "bytes": output.stat().st_size}
