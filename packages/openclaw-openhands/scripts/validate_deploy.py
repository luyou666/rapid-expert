#!/usr/bin/env python3
"""Validate that the Rapid Expert MVP deploy package has required files."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "scripts/rapid_expert.py",
    "scripts/github_search.py",
    "adapters/openclaw-openhands/scripts/collect_sources.py",
    "adapters/openclaw-openhands/scripts/rank_sources.py",
    "adapters/openclaw-openhands/scripts/build_report.py",
    "state/schemas/session-state.schema.json",
    "state/schemas/source.schema.json",
    "state/schemas/evaluation.schema.json",
    "deploy/agent-manifest.json",
    "packages/openclaw-openhands/config/tools.json",
    "packages/hermes-agent/tools.json",
    "packages/claude-code/manifest.json",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    compile_targets = [
        ROOT / "scripts" / "rapid_expert.py",
        ROOT / "scripts" / "github_search.py",
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
    status = {
        "missing": missing,
        "py_compile_ok": compile_result.returncode == 0,
        "py_compile_stderr": compile_result.stderr,
        "behavior": behavior,
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if not missing and compile_result.returncode == 0 and behavior["ok"] else 1


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
        return {
            "fake_report_rejected": eval_result.returncode != 0,
            "unsafe_risk_blocked": risk_result.returncode == 2,
            "high_risk_scan_requires_safe_mode": scan_result.returncode == 1,
            "ok": eval_result.returncode != 0 and risk_result.returncode == 2 and scan_result.returncode == 1,
        }


if __name__ == "__main__":
    raise SystemExit(main())
