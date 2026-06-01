from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class PermissionError(RuntimeError):
    pass


class PermissionProfile:
    def __init__(self, root: Path, profile_path: Path | None = None) -> None:
        self.root = root
        self.profile_path = profile_path or root / "harness" / "config" / "permission_profile.json"
        self.profile = json.loads(self.profile_path.read_text(encoding="utf-8-sig"))

    def check_tool(self, tool_name: str, argv: list[str]) -> None:
        allowed_tools = set(self.profile.get("allowed_tools", []))
        if tool_name not in allowed_tools:
            raise PermissionError(f"Tool is not allowed by permission profile: {tool_name}")
        if not argv:
            raise PermissionError("Tool argv cannot be empty.")
        executable_name = Path(argv[0]).name.lower()
        if executable_name in {item.lower() for item in self.profile.get("deny_shell_executables", [])}:
            raise PermissionError(f"Shell executable is denied: {executable_name}")
        if executable_name.startswith("python") or Path(argv[0]) == Path(sys.executable):
            self.check_python_script(argv)
            return
        raise PermissionError(f"Executable is not allowed: {argv[0]}")

    def check_python_script(self, argv: list[str]) -> None:
        if len(argv) < 2:
            raise PermissionError("Python tool must include a script path.")
        script = Path(argv[1])
        if script.is_absolute():
            try:
                script_rel = script.resolve().relative_to(self.root.resolve()).as_posix()
            except ValueError as exc:
                raise PermissionError(f"Python script must stay inside project root: {script}") from exc
        else:
            script_rel = script.as_posix()
        allowed_scripts = set(self.profile.get("allowed_python_scripts", []))
        if script_rel not in allowed_scripts:
            raise PermissionError(f"Python script is not allowed: {script_rel}")

    def requires_approval(self, tool_name: str) -> bool:
        return tool_name in set(self.profile.get("approval_required_tools", []))
