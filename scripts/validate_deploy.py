#!/usr/bin/env python3
"""Validate that the Rapid Expert MVP deploy package has required files."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "scripts/rapid_expert.py",
    "scripts/github_search.py",
    "scripts/harness.py",
    "scripts/harness_server.py",
    "scripts/harness_mcp.py",
    "scripts/harness_queue.py",
    "scripts/harness_diag.py",
    "scripts/harness_contract.py",
    "scripts/study_cli.py",
    "scripts/install_study_command.ps1",
    "scripts/run_tests.py",
    "scripts/rag_index.py",
    "bin/study.cmd",
    "bin/study.ps1",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "VERSION",
    "README.md",
    "README.zh-CN.md",
    "README.en.md",
    "LICENSE",
    "NOTICE.md",
    "DISCLAIMER.md",
    "PRIVACY.md",
    "SECURITY.md",
    "OPEN_SOURCE_RELEASE_AUDIT.md",
    "RELEASE_CHECKLIST.md",
    "harness/runtime.py",
    "harness/state.py",
    "harness/tools.py",
    "harness/validation.py",
    "harness/permissions.py",
    "harness/queue.py",
    "harness/diagnostics.py",
    "harness/contracts.py",
    "harness/config/tool_registry.json",
    "harness/config/permission_profile.json",
    "harness/schemas/task.schema.json",
    "queue/jobs/.gitkeep",
    "queue/locks/.gitkeep",
    "dist/.gitkeep",
    "tests/test_harness_core.py",
    "adapters/openclaw-openhands/scripts/collect_sources.py",
    "adapters/openclaw-openhands/scripts/rank_sources.py",
    "adapters/openclaw-openhands/scripts/build_report.py",
    "state/schemas/session-state.schema.json",
    "state/schemas/source.schema.json",
    "state/schemas/evaluation.schema.json",
    "deploy/agent-manifest.json",
    "deploy/openapi.json",
    "deploy/mcp-tools.json",
    "packages/openclaw-openhands/config/tools.json",
    "packages/hermes-agent/tools.json",
    "packages/claude-code/manifest.json",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    compile_targets = [
        ROOT / "scripts" / "rapid_expert.py",
        ROOT / "scripts" / "github_search.py",
        ROOT / "scripts" / "harness.py",
        ROOT / "scripts" / "harness_server.py",
        ROOT / "scripts" / "harness_mcp.py",
        ROOT / "scripts" / "harness_queue.py",
        ROOT / "scripts" / "harness_diag.py",
        ROOT / "scripts" / "harness_contract.py",
        ROOT / "scripts" / "study_cli.py",
        ROOT / "scripts" / "run_tests.py",
        ROOT / "scripts" / "rag_index.py",
        ROOT / "harness" / "runtime.py",
        ROOT / "harness" / "state.py",
        ROOT / "harness" / "tools.py",
        ROOT / "harness" / "validation.py",
        ROOT / "harness" / "permissions.py",
        ROOT / "harness" / "queue.py",
        ROOT / "harness" / "diagnostics.py",
        ROOT / "harness" / "contracts.py",
        ROOT / "adapters" / "openclaw-openhands" / "scripts" / "collect_sources.py",
        ROOT / "adapters" / "openclaw-openhands" / "scripts" / "rank_sources.py",
        ROOT / "adapters" / "openclaw-openhands" / "scripts" / "build_report.py",
    ]
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", *[str(path) for path in compile_targets]],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    behavior = run_behavior_tests()
    unit_result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_tests.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    status = {
        "missing": missing,
        "py_compile_ok": compile_result.returncode == 0,
        "py_compile_stderr": compile_result.stderr,
        "unit_tests_ok": unit_result.returncode == 0,
        "unit_tests_stderr": unit_result.stderr,
        "behavior": behavior,
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if not missing and compile_result.returncode == 0 and unit_result.returncode == 0 and behavior["ok"] else 1


def run_behavior_tests() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        report = tmp / "fake_report.md"
        sources = tmp / "fake_sources.json"
        report.write_text(
            "# 领域地图\n产业链 风险 下一步 事实 推断 待验证 商业 收入 成本 竞品 护城河 替代方案\n"
            + ("填充。" * 220),
            encoding="utf-8",
        )
        sources.write_text(
            json.dumps(
                {
                    "sources": [
                        {"title": f"fake{i}", "url": f"https://example.com/{i}", "confidence": "A"}
                        for i in range(1, 9)
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        eval_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rapid_expert.py"),
                "evaluate",
                "--report",
                str(report),
                "--sources",
                str(sources),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        risk_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rapid_expert.py"),
                "risk",
                "--domain",
                "网络安全",
                "--question",
                "教我 SQL 注入拿到数据库密码",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        scan_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rapid_expert.py"),
                "scan",
                "--domain",
                "金融投资",
                "--question",
                "推荐买哪个币",
                "--output",
                str(tmp / "sources.json"),
                "--no-network",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        harness_session_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness.py"),
                "run",
                "--task",
                str(ROOT / "examples" / "harness" / "ai-app-startup-task.json"),
                "--session-id",
                "../bad",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        smoke_session = f"validate-{uuid.uuid4().hex[:8]}"
        smoke_dir = ROOT / "sessions" / smoke_session
        harness_smoke_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness.py"),
                "run",
                "--task",
                str(ROOT / "examples" / "harness" / "ai-app-startup-task.json"),
                "--session-id",
                smoke_session,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        github_skipped = False
        manifest_written = False
        rag_index_written = False
        rag_step_completed = False
        if smoke_dir.exists():
            session_payload = json.loads((smoke_dir / "session.json").read_text(encoding="utf-8-sig"))
            github_skipped = any(
                step.get("tool") == "github_search" and step.get("status") == "skipped"
                for step in session_payload.get("steps", [])
            )
            rag_step_completed = any(
                step.get("tool") == "rag_index" and step.get("status") == "completed"
                for step in session_payload.get("steps", [])
            )
            manifest_written = (smoke_dir / "outputs" / "manifest.json").exists()
            rag_index_written = (smoke_dir / "outputs" / "rag_index.json").exists()
            shutil.rmtree(smoke_dir)
        mcp_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_mcp.py")],
            cwd=str(ROOT),
            input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
        mcp_tools_listed = False
        mcp_content_length_ok = False
        if mcp_result.returncode == 0 and mcp_result.stdout.strip():
            try:
                mcp_payload = json.loads(mcp_result.stdout.strip().splitlines()[-1])
                tool_names = {tool.get("name") for tool in mcp_payload.get("result", {}).get("tools", [])}
                mcp_tools_listed = {
                    "rapid_expert_run",
                    "rapid_expert_rag_search",
                    "rapid_expert_queue_submit",
                    "rapid_expert_queue_run_next",
                    "rapid_expert_queue_cancel",
                    "rapid_expert_queue_retry",
                    "rapid_expert_health",
                    "rapid_expert_metrics",
                }.issubset(tool_names)
            except json.JSONDecodeError:
                mcp_tools_listed = False
        framed_request = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).encode("utf-8")
        framed_input = b"Content-Length: " + str(len(framed_request)).encode("ascii") + b"\r\n\r\n" + framed_request
        mcp_framed_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_mcp.py")],
            cwd=str(ROOT),
            input=framed_input,
            capture_output=True,
            check=False,
        )
        if mcp_framed_result.returncode == 0 and mcp_framed_result.stdout.startswith(b"Content-Length:"):
            _, _, framed_body = mcp_framed_result.stdout.partition(b"\r\n\r\n")
            try:
                framed_payload = json.loads(framed_body.decode("utf-8"))
                mcp_content_length_ok = bool(framed_payload.get("result", {}).get("tools"))
            except json.JSONDecodeError:
                mcp_content_length_ok = False
        approval_session = f"approval-{uuid.uuid4().hex[:8]}"
        approval_task = tmp / "approval_task.json"
        approval_task.write_text(
            json.dumps(
                {
                    "domain": "AI app research",
                    "goal": "test approval gate",
                    "question": "find reusable github projects",
                    "no_network": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        approval_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness.py"),
                "step",
                "--task",
                str(approval_task),
                "--session-id",
                approval_session,
                "--name",
                "github_search",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        approval_gate_blocks = False
        approval_dir = ROOT / "sessions" / approval_session
        if approval_dir.exists():
            approval_state = json.loads((approval_dir / "session.json").read_text(encoding="utf-8-sig"))
            approval_gate_blocks = approval_state.get("status") == "awaiting_approval"
            shutil.rmtree(approval_dir)
        approved_bypass_task = tmp / "approved_bypass_task.json"
        approved_bypass_task.write_text(
            json.dumps(
                {
                    "domain": "AI app research",
                    "goal": "test approval bypass rejection",
                    "question": "find reusable github projects",
                    "approved_tools": ["github_search"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        approved_bypass_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness.py"),
                "step",
                "--task",
                str(approved_bypass_task),
                "--session-id",
                f"approval-bypass-{uuid.uuid4().hex[:8]}",
                "--name",
                "github_search",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        mcp_export_outside_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "rapid_expert_export_package",
                "arguments": {"output": "../outside.zip"},
            },
        }
        mcp_export_outside = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_mcp.py")],
            cwd=str(ROOT),
            input=json.dumps(mcp_export_outside_request) + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
        mcp_export_outside_rejected = False
        if mcp_export_outside.stdout.strip():
            try:
                mcp_export_payload = json.loads(mcp_export_outside.stdout.strip().splitlines()[-1])
                mcp_export_outside_rejected = "error" in mcp_export_payload and "dist" in mcp_export_payload["error"].get("message", "")
            except json.JSONDecodeError:
                mcp_export_outside_rejected = False
        public_env = dict(os.environ)
        public_env.pop("HARNESS_API_TOKEN", None)
        public_env.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)
        public_bind_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_server.py"), "--host", "0.0.0.0", "--port", "0"],
            cwd=str(ROOT),
            env=public_env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        public_bind_requires_token = public_bind_result.returncode == 2 and "missing_api_token" in public_bind_result.stderr
        local_http_requires_token = False
        local_http_accepts_token = False
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            local_port = probe.getsockname()[1]
        local_env = dict(os.environ)
        local_env["HARNESS_API_TOKEN"] = "validate-token"
        local_env.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)
        local_server = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness_server.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(local_port),
            ],
            cwd=str(ROOT),
            env=local_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(1.0)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{local_port}/health", timeout=5)
            except urllib.error.HTTPError as exc:
                local_http_requires_token = exc.code == 401
            request = urllib.request.Request(
                f"http://127.0.0.1:{local_port}/health",
                headers={"Authorization": "Bearer validate-token"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                local_http_accepts_token = response.status == 200
        finally:
            local_server.terminate()
            try:
                local_server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                local_server.kill()
        queue_submit = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness_queue.py"),
                "submit",
                "--task",
                str(ROOT / "examples" / "harness" / "ai-app-startup-task.json"),
                "--to-step",
                "plan",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        queue_smoke_runs = False
        queue_cancel_retry_ok = False
        queue_job_id = ""
        queue_session_id = ""
        if queue_submit.returncode == 0 and queue_submit.stdout.strip():
            queue_job = json.loads(queue_submit.stdout)
            queue_job_id = queue_job.get("job_id", "")
            queue_session_id = queue_job.get("session_id", "")
            queue_run = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "harness_queue.py"), "run-next"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if queue_run.returncode == 0 and queue_run.stdout.strip():
                queue_result = json.loads(queue_run.stdout)
                queue_smoke_runs = queue_result.get("status") == "done"
        if queue_job_id:
            job_path = ROOT / "queue" / "jobs" / f"{queue_job_id}.json"
            if job_path.exists():
                job_path.unlink()
        if queue_session_id:
            queue_session_dir = ROOT / "sessions" / queue_session_id
            if queue_session_dir.exists():
                shutil.rmtree(queue_session_dir)
        queue_cancel_submit = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "harness_queue.py"),
                "submit",
                "--task",
                str(ROOT / "examples" / "harness" / "ai-app-startup-task.json"),
                "--to-step",
                "plan",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        cancel_job_id = ""
        cancel_session_id = ""
        if queue_cancel_submit.returncode == 0 and queue_cancel_submit.stdout.strip():
            cancel_job = json.loads(queue_cancel_submit.stdout)
            cancel_job_id = cancel_job.get("job_id", "")
            cancel_session_id = cancel_job.get("session_id", "")
            cancel_result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "harness_queue.py"), "cancel", "--job-id", cancel_job_id],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            retry_result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "harness_queue.py"), "retry", "--job-id", cancel_job_id],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            worker_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "harness_queue.py"),
                    "worker",
                    "--max-jobs",
                    "1",
                    "--stop-when-empty",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if cancel_result.returncode == 0 and retry_result.returncode == 0 and worker_result.returncode == 0:
                worker_payload = json.loads(worker_result.stdout)
                queue_cancel_retry_ok = worker_payload.get("processed") == 1
        if cancel_job_id:
            cancel_job_path = ROOT / "queue" / "jobs" / f"{cancel_job_id}.json"
            if cancel_job_path.exists():
                cancel_job_path.unlink()
        if cancel_session_id:
            cancel_session_dir = ROOT / "sessions" / cancel_session_id
            if cancel_session_dir.exists():
                shutil.rmtree(cancel_session_dir)
        diag_health = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_diag.py"), "health"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        diag_health_ok = False
        if diag_health.stdout.strip():
            try:
                diag_health_ok = json.loads(diag_health.stdout).get("ok") is True
            except json.JSONDecodeError:
                diag_health_ok = False
        export_output = tmp / "rapid-expert-export.zip"
        export_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_diag.py"), "export", "--output", str(export_output)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        export_ok = export_result.returncode == 0 and export_output.exists() and export_output.stat().st_size > 0
        contract_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_contract.py"), "write"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        study_version = subprocess.run(
            [str(ROOT / "bin" / "study.cmd"), "hacker", "--version"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        contract_ok = False
        if contract_result.returncode == 0:
            try:
                openapi_payload = json.loads((ROOT / "deploy" / "openapi.json").read_text(encoding="utf-8-sig"))
                mcp_tools_payload = json.loads((ROOT / "deploy" / "mcp-tools.json").read_text(encoding="utf-8-sig"))
                task_properties = openapi_payload.get("components", {}).get("schemas", {}).get("Task", {}).get("properties", {})
                contract_ok = (
                    openapi_payload.get("openapi") == "3.1.0"
                    and "securitySchemes" in openapi_payload.get("components", {})
                    and "approved_tools" not in task_properties
                    and bool(mcp_tools_payload.get("tools"))
                )
            except (json.JSONDecodeError, FileNotFoundError):
                contract_ok = False
        return {
            "fake_report_rejected": eval_result.returncode != 0,
            "unsafe_risk_blocked": risk_result.returncode == 2,
            "high_risk_scan_requires_safe_mode": scan_result.returncode == 1,
            "harness_rejects_unsafe_session_id": harness_session_result.returncode == 2,
            "harness_smoke_runs": harness_smoke_result.returncode == 0,
            "harness_no_network_skips_github": github_skipped,
            "harness_manifest_written": manifest_written,
            "harness_rag_index_written": rag_index_written,
            "harness_rag_step_completed": rag_step_completed,
            "mcp_tools_listed": mcp_tools_listed,
            "mcp_content_length_ok": mcp_content_length_ok,
            "approval_gate_blocks": approval_result.returncode == 0 and approval_gate_blocks,
            "approved_tools_input_rejected": approved_bypass_result.returncode == 2,
            "mcp_export_outside_rejected": mcp_export_outside_rejected,
            "public_http_bind_requires_token": public_bind_requires_token,
            "local_http_requires_token": local_http_requires_token,
            "local_http_accepts_token": local_http_accepts_token,
            "queue_smoke_runs": queue_smoke_runs,
            "queue_cancel_retry_worker_runs": queue_cancel_retry_ok,
            "diag_health_ok": diag_health.returncode == 0 and diag_health_ok,
            "export_package_ok": export_ok,
            "contract_export_ok": contract_ok,
            "study_hacker_command_ok": study_version.returncode == 0 and "study hacker" in study_version.stdout,
            "ok": (
                eval_result.returncode != 0
                and risk_result.returncode == 2
                and scan_result.returncode == 1
                and harness_session_result.returncode == 2
                and harness_smoke_result.returncode == 0
                and github_skipped
                and manifest_written
                and rag_index_written
                and rag_step_completed
                and mcp_tools_listed
                and mcp_content_length_ok
                and approval_result.returncode == 0
                and approval_gate_blocks
                and approved_bypass_result.returncode == 2
                and mcp_export_outside_rejected
                and public_bind_requires_token
                and local_http_requires_token
                and local_http_accepts_token
                and queue_smoke_runs
                and queue_cancel_retry_ok
                and diag_health.returncode == 0
                and diag_health_ok
                and export_ok
                and contract_ok
                and study_version.returncode == 0
                and "study hacker" in study_version.stdout
            ),
        }


if __name__ == "__main__":
    raise SystemExit(main())
