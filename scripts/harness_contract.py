#!/usr/bin/env python3
"""Generate machine-readable platform contracts for the harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.contracts import openapi_spec, write_contracts  # noqa: E402
from scripts.harness_mcp import tool_definitions  # noqa: E402


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapid Expert Harness contract generator")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write")
    sub.add_parser("openapi")
    sub.add_parser("mcp-tools")
    args = parser.parse_args()
    if args.command == "write":
        print_json(write_contracts(ROOT))
        return 0
    if args.command == "openapi":
        print_json(openapi_spec())
        return 0
    if args.command == "mcp-tools":
        print_json({"tools": tool_definitions()})
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
