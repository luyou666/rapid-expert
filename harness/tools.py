from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .permissions import PermissionProfile


PLACEHOLDER_RE = re.compile(r"{([A-Za-z0-9_]+)}")


@dataclass
class ToolResult:
    name: str
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class ToolRegistry:
    def __init__(self, root: Path, registry_path: Path | None = None) -> None:
        self.root = root
        self.registry_path = registry_path or root / "harness" / "config" / "tool_registry.json"
        self.registry = json.loads(self.registry_path.read_text(encoding="utf-8-sig"))
        self.permissions = PermissionProfile(root)

    def render_argv(self, tool_name: str, values: dict[str, Any]) -> list[str]:
        tool = self.registry["tools"][tool_name]
        rendered: list[str] = []
        for item in tool["argv"]:
            value = item
            for key in PLACEHOLDER_RE.findall(item):
                if key not in values:
                    raise KeyError(f"Missing tool value: {key}")
                value = value.replace("{" + key + "}", str(values[key]))
            if value == "":
                continue
            if value == "python":
                value = sys.executable
            rendered.append(value)
        return rendered

    def run(self, tool_name: str, values: dict[str, Any], timeout: int = 120) -> ToolResult:
        argv = self.render_argv(tool_name, values)
        self.permissions.check_tool(tool_name, argv)
        proc = subprocess.run(
            argv,
            cwd=str(self.root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return ToolResult(
            name=tool_name,
            argv=argv,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
