#!/usr/bin/env python3
"""Rank collected source candidates by rough credibility tier."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from pathlib import Path


TIER_1_HINTS = [
    ".gov",
    ".edu",
    "sec.gov",
    "europa.eu",
    "who.int",
    "worldbank.org",
    "oecd.org",
    "nist.gov",
    "gov.uk",
    "usability.gov",
    "iso.org",
    "arxiv.org",
]

TIER_2_HINTS = [
    "mckinsey",
    "bcg",
    "bain",
    "gartner",
    "forrester",
    "deloitte",
    "pwc",
    "kpmg",
    "ey.com",
    "cbinsights",
    "statista",
]

TIER_3_HINTS = [
    "medium.com",
    "substack.com",
    "techcrunch.com",
    "forbes.com",
    "wired.com",
    "36kr.com",
    "huxiu.com",
]


def classify(url: str, title: str) -> tuple[str, str, int]:
    text = f"{url} {title}".lower()
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(hint in text for hint in TIER_1_HINTS):
        return "一级", "A", 95
    if any(hint in text for hint in TIER_2_HINTS):
        return "二级", "B", 80
    if "github.com" in host:
        return "二级", "B", 78
    if any(hint in text for hint in TIER_3_HINTS):
        return "三级", "C", 60
    if re.search(r"blog|forum|reddit|zhihu|weibo|x\.com|twitter", text):
        return "四级", "D", 40
    return "三级", "C", 55


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ranked = []
    for item in payload.get("sources", []):
        tier, confidence, score = classify(item.get("url", ""), item.get("title", ""))
        ranked.append(
            {
                **item,
                "source_tier": tier,
                "confidence": confidence,
                "credibility_score": score,
                "verification_required": confidence in {"C", "D"},
            }
        )
    ranked.sort(key=lambda row: row["credibility_score"], reverse=True)
    payload["sources"] = ranked
    payload["ranking_note"] = (
        "Heuristic ranking only. Agents must verify important claims with primary sources."
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
