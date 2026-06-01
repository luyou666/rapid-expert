#!/usr/bin/env python3
"""Search GitHub repositories using the public REST API."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--min-stars", type=int, default=0)
    parser.add_argument("--updated-after", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    terms = [args.query]
    if args.min_stars:
        terms.append(f"stars:>={args.min_stars}")
    if args.updated_after:
        terms.append(f"pushed:>={args.updated_after}")
    query = " ".join(terms)
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": min(args.limit, 50)}
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "rapid-expert-mvp/0.3",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    payload: dict
    failed = False
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = json.loads(response.read().decode("utf-8"))
        repos = []
        for item in raw.get("items", []):
            repos.append(
                {
                    "name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "summary": item.get("description") or "",
                    "stars": item.get("stargazers_count", 0),
                    "last_updated": item.get("pushed_at", ""),
                    "license": (item.get("license") or {}).get("spdx_id", "NOASSERTION"),
                    "language": item.get("language") or "",
                    "maintenance_risk": "low" if item.get("pushed_at", "")[:4] >= "2025" else "medium",
                    "recommendation": "reference"
                }
            )
        payload = {
            "query": query,
            "accessed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "projects": repos,
            "status": "ok",
        }
    except Exception as exc:  # noqa: BLE001
        failed = True
        payload = {
            "query": query,
            "accessed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "projects": [],
            "status": "failed",
            "error": str(exc),
            "manual_fallback": True
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
