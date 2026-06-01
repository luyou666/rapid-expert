#!/usr/bin/env python3
"""Diagnostics and packaging utilities for the Rapid Expert Harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.diagnostics import export_package, health_report  # noqa: E402
from harness.queue import JobQueue  # noqa: E402


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapid Expert Harness diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("metrics")

    export = sub.add_parser("export")
    export.add_argument("--output", default="dist/rapid-expert-harness.zip")

    args = parser.parse_args()
    if args.command == "health":
        report = health_report(ROOT)
        print_json(report)
        return 0 if report.get("ok") else 1
    if args.command == "metrics":
        print_json({"queue": JobQueue(ROOT).stats(), "health": health_report(ROOT)})
        return 0
    if args.command == "export":
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        print_json(export_package(ROOT, output))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
