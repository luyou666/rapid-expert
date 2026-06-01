from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import SessionState
from .tools import ToolRegistry, ToolResult


STEP_ORDER = ["risk", "plan", "scan", "rank", "rag_index", "github_search", "build", "evaluate"]


class HarnessRuntime:
    def __init__(self, root: Path, session_id: str) -> None:
        self.root = root
        self.state = SessionState(root, session_id)
        self.tools = ToolRegistry(root)

    def default_values(self, task: dict[str, Any]) -> dict[str, Any]:
        outputs = self.state.outputs_dir
        return {
            "domain": task.get("domain", ""),
            "question": task.get("question") or task.get("goal", ""),
            "goal": task.get("goal", ""),
            "user_level": task.get("user_level", ""),
            "daily_time": task.get("daily_time", ""),
            "region": task.get("region", ""),
            "time_range": task.get("time_range", ""),
            "no_network_flag": "--no-network" if task.get("no_network", False) else "",
            "github_query": task.get("github_query") or f"{task.get('domain', '')} agent rag",
            "min_stars": task.get("min_stars", 0),
            "github_limit": task.get("github_limit", 10),
            "risk_output": outputs / "risk.json",
            "plan_output": outputs / "plan.json",
            "sources_raw": outputs / "sources_raw.json",
            "sources_ranked": outputs / "sources_ranked.json",
            "rag_index_output": outputs / "rag_index.json",
            "github_output": outputs / "github_projects.json",
            "report_output": outputs / "domain_kit_report.md",
            "evaluation_output": outputs / "evaluation.json",
            "duration": 7,
        }

    def refresh_derived_values(self, values: dict[str, Any]) -> None:
        plan_payload = self.read_json_if_exists(Path(values["plan_output"]))
        values["duration"] = plan_payload.get("recommended_days", values.get("duration", 7))

    def read_json_if_exists(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def run(
        self,
        task: dict[str, Any],
        resume: bool = False,
        from_step: str | None = None,
        to_step: str | None = None,
        approved_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        self.state.init(task, resume=resume)
        for tool_name in approved_tools or []:
            self.state.approve_tool(tool_name)
        self.state.event("run_started", {"session_dir": str(self.state.session_dir)})
        values = self.default_values(task)
        steps = self.selected_steps(from_step, to_step)
        evaluation: ToolResult | None = None

        for tool_name in steps:
            self.refresh_derived_values(values)
            if resume and self.state.is_step_done(tool_name):
                self.state.event("tool_skipped_resume", {"tool": tool_name})
                continue
            result = self.run_tool_step(tool_name, task, values)
            if tool_name == "risk" and result.returncode == 2:
                self.state.event("run_blocked", {"reason": result.stdout or result.stderr})
                return self.finish("blocked")
            if result.returncode == 3:
                return self.finish("awaiting_approval")
            if tool_name == "evaluate":
                evaluation = result

        if to_step and to_step != "evaluate":
            return self.finish("paused")
        if evaluation is None:
            latest_eval = self.state.latest_step("evaluate")
            final_status = "completed" if latest_eval and latest_eval.get("returncode") == 0 else "needs_review"
        else:
            final_status = "completed" if evaluation.ok else "needs_review"
        return self.finish(final_status)

    def run_single_step(self, task: dict[str, Any], tool_name: str, resume: bool = True) -> dict[str, Any]:
        self.state.init(task, resume=resume)
        values = self.default_values(task)
        self.refresh_derived_values(values)
        result = self.run_tool_step(tool_name, task, values)
        if tool_name == "risk" and result.returncode == 2:
            return self.finish("blocked")
        if result.returncode == 3:
            return self.finish("awaiting_approval")
        if tool_name == "evaluate":
            return self.finish("completed" if result.ok else "needs_review")
        return self.finish("paused")

    def selected_steps(self, from_step: str | None, to_step: str | None) -> list[str]:
        if from_step and from_step not in STEP_ORDER:
            raise ValueError(f"Unknown from_step: {from_step}")
        if to_step and to_step not in STEP_ORDER:
            raise ValueError(f"Unknown to_step: {to_step}")
        start = STEP_ORDER.index(from_step) if from_step else 0
        end = STEP_ORDER.index(to_step) if to_step else len(STEP_ORDER) - 1
        if start > end:
            raise ValueError("from_step cannot be after to_step.")
        return STEP_ORDER[start : end + 1]

    def run_tool_step(self, tool_name: str, task: dict[str, Any], values: dict[str, Any]) -> ToolResult:
        if tool_name == "github_search" and task.get("no_network", False):
            Path(values["github_output"]).write_text(
                json.dumps(
                    {
                        "status": "skipped_no_network",
                        "projects": [],
                        "reason": "Task requested no_network=true.",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            step = {"tool": "github_search", "status": "skipped", "returncode": 0, "reason": "no_network"}
            self.state.record_step(step)
            self.state.event("optional_tool_skipped", {"tool": "github_search", "reason": "no_network"})
            return ToolResult("github_search", [], 0, "", "")
        if self.tools.permissions.requires_approval(tool_name) and not self.state.is_tool_approved(tool_name):
            step = {
                "tool": tool_name,
                "status": "pending_approval",
                "returncode": 3,
                "reason": "tool_requires_approval",
            }
            self.state.record_step(step)
            self.state.event("tool_pending_approval", {"tool": tool_name})
            return ToolResult(tool_name, [], 3, "", "tool requires approval")
        allow_fail = tool_name in {"risk", "github_search", "evaluate"}
        result = self.run_step(tool_name, values, allow_fail=allow_fail)
        if tool_name == "github_search" and not result.ok:
            self.state.event("optional_tool_failed", {"tool": "github_search", "stderr": result.stderr})
        return result

    def run_step(self, tool_name: str, values: dict[str, Any], allow_fail: bool = False) -> ToolResult:
        self.state.event("tool_started", {"tool": tool_name})
        result = self.tools.run(tool_name, values)
        status = "completed" if result.ok else "failed"
        if tool_name == "risk" and result.returncode == 2:
            status = "blocked"
        step = {
            "tool": tool_name,
            "status": status,
            "returncode": result.returncode,
            "argv": result.argv,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }
        self.state.record_step(step)
        if not result.ok and not allow_fail:
            self.state.event("tool_failed", step)
            raise RuntimeError(f"Tool failed: {tool_name}\n{result.stderr or result.stdout}")
        return result

    def finish(self, status: str) -> dict[str, Any]:
        state = self.state.read()
        state["status"] = status
        self.state.write(state)
        self.write_manifest(state)
        self.state.event("run_finished", {"status": status})
        return state

    def write_manifest(self, state: dict[str, Any]) -> None:
        outputs = []
        for path in sorted(self.state.outputs_dir.glob("*")):
            if path.is_file():
                outputs.append({"name": path.name, "path": str(path), "bytes": path.stat().st_size})
        manifest = {
            "session_id": self.state.session_id,
            "status": state.get("status"),
            "outputs": outputs,
            "steps": [
                {"tool": step.get("tool"), "status": step.get("status"), "returncode": step.get("returncode")}
                for step in state.get("steps", [])
            ],
        }
        (self.state.outputs_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
