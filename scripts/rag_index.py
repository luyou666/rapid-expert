#!/usr/bin/env python3
"""Build and search a lightweight JSON RAG index for ranked sources."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return [item.lower() for item in TOKEN_RE.findall(text)]


def source_text(row: dict[str, Any]) -> str:
    fields = [
        row.get("title", ""),
        row.get("summary", ""),
        row.get("snippet", ""),
        row.get("description", ""),
        row.get("query", ""),
        row.get("url", ""),
    ]
    return "\n".join(str(item) for item in fields if item)


def command_build(args: argparse.Namespace) -> int:
    payload = read_json(Path(args.sources))
    sources = payload.get("sources", [])
    documents = []
    for idx, row in enumerate(sources):
        text = source_text(row)
        tokens = sorted(set(tokenize(text)))
        documents.append(
            {
                "id": f"source-{idx + 1}",
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "confidence": row.get("confidence", ""),
                "accessed_at": row.get("accessed_at", ""),
                "text": text[:2000],
                "tokens": tokens[:500],
            }
        )
    index = {
        "status": "ready" if documents else "empty",
        "source_count": len(documents),
        "documents": documents,
    }
    write_json(Path(args.output), index)
    print(args.output)
    return 0


def command_search(args: argparse.Namespace) -> int:
    index = read_json(Path(args.index))
    query_tokens = set(tokenize(args.query))
    results = []
    for doc in index.get("documents", []):
        doc_tokens = set(doc.get("tokens", []))
        overlap = sorted(query_tokens & doc_tokens)
        score = len(overlap)
        if score <= 0:
            continue
        results.append(
            {
                "id": doc.get("id"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "confidence": doc.get("confidence"),
                "score": score,
                "matched_terms": overlap[:20],
                "text": doc.get("text", "")[:500],
            }
        )
    results.sort(key=lambda row: (-row["score"], row.get("confidence", "")))
    payload = {"query": args.query, "results": results[: args.limit]}
    if args.output:
        write_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rapid Expert lightweight RAG index")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--sources", required=True)
    build.add_argument("--output", required=True)
    build.set_defaults(func=command_build)

    search = sub.add_parser("search")
    search.add_argument("--index", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--output")
    search.set_defaults(func=command_search)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
