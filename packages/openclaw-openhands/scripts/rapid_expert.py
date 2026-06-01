#!/usr/bin/env python3
"""Unified CLI for Rapid Expert MVP.

The CLI intentionally uses only the Python standard library so coding agents
can run it in constrained environments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENHANDS_SCRIPTS = ROOT / "adapters" / "openclaw-openhands" / "scripts"
if not OPENHANDS_SCRIPTS.exists():
    OPENHANDS_SCRIPTS = ROOT / "scripts"

DISCLAIMER = (
    "For learning, research, source organization, and workflow assistance only. "
    "Not legal, financial, medical, psychological, cybersecurity, compliance, tax, "
    "accounting, audit, regulatory, chemical safety, or biosafety advice. "
    "High-risk decisions require qualified professional confirmation."
)


HIGH_RISK_KEYWORDS = {
    "finance": ["投资", "股票", "基金", "期货", "币", "证券", "融资", "估值", "financial", "investment", "stock", "crypto"],
    "legal": ["法律", "诉讼", "合同纠纷", "律师", "起诉", "legal", "lawsuit", "contract"],
    "medical": ["医疗", "诊断", "处方", "治疗", "药物", "medical", "diagnosis", "prescription", "treatment"],
    "cybersecurity": [
        "漏洞", "渗透", "攻击", "绕过", "sql注入", "sql 注入", "注入", "数据库密码", "脱库",
        "撞库", "提权", "木马", "后门", "免杀", "爆破", "钓鱼", "抓包", "payload",
        "exploit", "bypass", "malware", "phishing", "privilege escalation", "credential",
    ],
    "chemical_bio": ["化工", "生物安全", "制备", "合成", "爆炸物", "毒物", "chemical", "biosafety", "synthesis"],
    "privacy": ["隐私", "个人信息", "爬取用户", "身份证", "数据库密码", "手机号库", "privacy", "personal data"],
    "minor": ["未成年人", "儿童", "minor", "child"],
}

UNSAFE_ACTION_KEYWORDS = [
    "规避监管",
    "绕过审查",
    "行贿",
    "造假",
    "操纵市场",
    "欺骗客户",
    "非法获取",
    "未授权攻击",
    "拿到数据库密码",
    "脱库",
    "撞库",
    "免杀",
    "木马",
    "后门",
    "提权",
    "sql 注入",
    "sql注入",
    "steal",
    "evade detection",
    "bypass regulation",
    "market manipulation",
    "dump database",
    "steal password",
]

PLACEHOLDER_PATTERNS = [
    "待补充",
    "待检索",
    "待判断",
    "待分级",
    "需要人工检索",
    "重新运行 collect_sources",
]

LOW_LEVEL_HINTS = {"0", "zero", "0基础", "零基础", "完全0基础", "完全 0 基础", "小白", "新手", "入门", "没基础", "没有基础", "听过概念"}
MID_LEVEL_HINTS = {"了解一点", "懂一点", "有基础", "做过简单调研", "学过", "用过"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_python(script: Path, args: list[str]) -> int:
    cmd = [sys.executable, str(script), *args]
    return subprocess.call(cmd, cwd=str(ROOT))


def classify_risk_text(text: str) -> dict:
    lower = text.lower()
    flags = []
    for category, keywords in HIGH_RISK_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in lower]
        if hits:
            flags.append({"category": category, "hits": hits[:5]})
    unsafe_hits = [kw for kw in UNSAFE_ACTION_KEYWORDS if kw.lower() in lower]
    risk_level = "high" if flags else "low"
    if unsafe_hits:
        risk_level = "blocked"
    return {
        "risk_level": risk_level,
        "flags": flags,
        "unsafe_hits": unsafe_hits,
        "safe_mode_required": risk_level in {"high", "blocked"},
        "disclaimer": DISCLAIMER,
        "message": (
            "Request must be transformed into learning, risk identification, compliance checks, or professional-confirmation questions."
            if risk_level in {"high", "blocked"}
            else "No high-risk keyword matched. Continue normal evidence-based workflow."
        ),
    }


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def user_level_score(user_level: str) -> int:
    compact = compact_text(user_level)
    if any(compact_text(hint) in compact for hint in LOW_LEVEL_HINTS):
        return 2
    if any(compact_text(hint) in compact for hint in MID_LEVEL_HINTS):
        return 1
    return 0


def foundation_first_required(user_level: str) -> bool:
    return user_level_score(user_level) >= 1


def command_risk(args: argparse.Namespace) -> int:
    text = " ".join(item for item in [args.domain, args.question] if item)
    result = classify_risk_text(text)
    if args.output:
        write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["risk_level"] == "blocked":
        return 2
    return 1 if result["risk_level"] == "high" and args.fail_on_high else 0


def command_init_state(args: argparse.Namespace) -> int:
    state = read_json(ROOT / "state" / "default_state.json")
    state.update(
        {
            "target_domain": args.domain or "",
            "learning_days": args.days,
            "created_at": now(),
            "updated_at": now(),
        }
    )
    if args.user_level:
        state["user_profile"]["baseline_level"] = args.user_level
    if args.goal:
        state["user_profile"]["business_goal"] = args.goal
    write_json(Path(args.output), state)
    print(args.output)
    return 0


def command_plan(args: argparse.Namespace) -> int:
    text = " ".join([args.domain, args.user_level, args.goal, args.daily_time])
    risk = classify_risk_text(text)
    score = 0
    score += user_level_score(args.user_level)
    if "30" in args.daily_time or "60" in args.daily_time or "1小时" in args.daily_time:
        score += 1
    if risk["risk_level"] in {"high", "blocked"}:
        score += 3
    if any(word in args.goal for word in ["投资", "咨询", "复杂", "监管", "产品方案"]):
        score += 2
    days = 5 if score <= 1 else 7 if score <= 3 else 9 if score <= 5 else 12
    payload = {
        "domain": args.domain,
        "recommended_days": days,
        "risk": risk,
        "disclaimer": DISCLAIMER,
        "reason": {
            "score": score,
            "user_level": args.user_level,
            "daily_time": args.daily_time,
            "goal": args.goal,
        },
        "learning_mode": {
            "foundation_first": foundation_first_required(args.user_level),
            "first_task_policy": (
                "Start with plain-language concepts, analogies, core terms, and one simple case before assigning business tasks."
                if foundation_first_required(args.user_level)
                else "Start with framework gap-finding, evidence collection, and practical deliverables."
            ),
            "follow_up_required": True,
        },
    }
    if args.output:
        write_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_scan(args: argparse.Namespace) -> int:
    risk = classify_risk_text(f"{args.domain} {args.question}")
    if risk["risk_level"] == "blocked" and not args.allow_blocked:
        print(json.dumps(risk, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    if risk["risk_level"] == "high" and not args.safe_mode:
        print(
            json.dumps(
                {
                    **risk,
                    "error": "High-risk domain requires --safe-mode for scan. Use safe-mode to collect learning, compliance, and risk-identification sources only.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    return run_python(
        OPENHANDS_SCRIPTS / "collect_sources.py",
        [
            "--domain",
            args.domain,
            "--question",
            args.question,
            "--region",
            args.region,
            "--time-range",
            args.time_range,
            "--output",
            args.output,
            *(["--no-network"] if args.no_network else []),
        ],
    )


def command_rank(args: argparse.Namespace) -> int:
    return run_python(
        OPENHANDS_SCRIPTS / "rank_sources.py",
        ["--input", args.input, "--output", args.output],
    )


def command_build(args: argparse.Namespace) -> int:
    return run_python(
        OPENHANDS_SCRIPTS / "build_report.py",
        [
            "--domain",
            args.domain,
            "--sources",
            args.sources,
            "--duration",
            str(args.duration),
            "--user-level",
            args.user_level,
            "--output",
            args.output,
        ],
    )


def score_report_text(text: str, sources_payload: dict | None) -> dict:
    checks = {
        "has_domain_map": bool(re.search(r"领域地图|domain map", text, re.I)),
        "has_industry_chain": bool(re.search(r"产业链|value chain|industry chain", text, re.I)),
        "has_risk": bool(re.search(r"风险|risk", text, re.I)),
        "has_next_steps": bool(re.search(r"下一步|后续|next", text, re.I)),
        "has_fact_inference_distinction": bool(re.search(r"事实|推断|待验证|inference", text, re.I)),
    }
    source_count = 0
    strong_source_count = 0
    sources_status = ""
    manual_fallback = False
    stale_or_example_sources = False
    invalid_sources = 0
    if sources_payload:
        sources_status = str(sources_payload.get("status", ""))
        manual_fallback = bool(sources_payload.get("manual_fallback", False))
        stale_or_example_sources = sources_status in {"example_requires_refresh", "query_plan_only", "failed"}
        sources = sources_payload.get("sources", [])
        source_count = len(sources)
        for row in sources:
            if row.get("confidence") in {"A", "B"} and row.get("url") and row.get("accessed_at"):
                strong_source_count += 1
            if not row.get("url") or not row.get("accessed_at") or row.get("url", "").startswith("https://example.com"):
                invalid_sources += 1
    checks["source_count"] = source_count
    checks["strong_source_count"] = strong_source_count
    checks["sources_status"] = sources_status
    checks["manual_fallback"] = manual_fallback
    checks["invalid_sources"] = invalid_sources
    checks["placeholder_count"] = sum(text.count(pattern) for pattern in PLACEHOLDER_PATTERNS)
    score = 0
    score += 15 if checks["has_domain_map"] else 0
    score += 15 if source_count >= 8 and strong_source_count >= 2 else 8 if source_count >= 3 else 0
    score += 15 if "商业" in text or "收入" in text or "成本" in text else 0
    score += 15 if "竞品" in text or "护城河" in text or "替代方案" in text else 0
    score += 15 if checks["has_risk"] else 0
    score += 15 if len(text) >= 1200 and checks["has_next_steps"] else 8 if len(text) >= 600 else 0
    score += 10 if checks["has_fact_inference_distinction"] else 0
    blocking = []
    if "编造" in text or "fake" in text.lower():
        blocking.append("Report appears to mention fabricated sources.")
    if source_count == 0:
        blocking.append("No ranked sources were provided.")
    if checks["placeholder_count"] > 0:
        blocking.append("Report still contains placeholders and cannot be accepted as final.")
    if manual_fallback or stale_or_example_sources:
        blocking.append("Sources require refresh or manual fallback, so final pass is blocked.")
    if invalid_sources > 0:
        blocking.append("One or more sources are invalid, missing accessed_at, or example URLs.")
    if strong_source_count < 2:
        blocking.append("Fewer than two strong sources with URL and accessed_at.")
    status = "pass" if score >= 80 and not blocking else "conditional_pass" if score >= 65 and not blocking else "fail"
    return {
        "score": score,
        "status": status,
        "checks": checks,
        "blocking_issues": blocking,
        "disclaimer": DISCLAIMER,
    }


def command_evaluate(args: argparse.Namespace) -> int:
    report_text = Path(args.report).read_text(encoding="utf-8")
    sources_payload = read_json(Path(args.sources)) if args.sources and Path(args.sources).exists() else None
    result = score_report_text(report_text, sources_payload)
    if args.output:
        write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "fail" else 1


def command_github(args: argparse.Namespace) -> int:
    return run_python(
        ROOT / "scripts" / "github_search.py",
        [
            "--query",
            args.query,
            "--min-stars",
            str(args.min_stars),
            "--updated-after",
            args.updated_after,
            "--limit",
            str(args.limit),
            "--output",
            args.output,
        ],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rapid Expert MVP unified CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    risk = sub.add_parser("risk")
    risk.add_argument("--domain", default="")
    risk.add_argument("--question", default="")
    risk.add_argument("--output")
    risk.add_argument("--fail-on-blocked", action="store_true")
    risk.add_argument("--fail-on-high", action="store_true")
    risk.set_defaults(func=command_risk)

    init = sub.add_parser("init-state")
    init.add_argument("--domain", default="")
    init.add_argument("--days", type=int, choices=[5, 7, 9, 12], default=7)
    init.add_argument("--user-level", default="")
    init.add_argument("--goal", default="")
    init.add_argument("--output", required=True)
    init.set_defaults(func=command_init_state)

    plan = sub.add_parser("plan")
    plan.add_argument("--domain", required=True)
    plan.add_argument("--user-level", default="")
    plan.add_argument("--daily-time", default="")
    plan.add_argument("--goal", default="")
    plan.add_argument("--output")
    plan.set_defaults(func=command_plan)

    scan = sub.add_parser("scan")
    scan.add_argument("--domain", required=True)
    scan.add_argument("--question", default="")
    scan.add_argument("--region", default="")
    scan.add_argument("--time-range", default="")
    scan.add_argument("--no-network", action="store_true")
    scan.add_argument("--allow-blocked", action="store_true")
    scan.add_argument("--safe-mode", action="store_true")
    scan.add_argument("--output", required=True)
    scan.set_defaults(func=command_scan)

    rank = sub.add_parser("rank")
    rank.add_argument("--input", required=True)
    rank.add_argument("--output", required=True)
    rank.set_defaults(func=command_rank)

    build = sub.add_parser("build")
    build.add_argument("--domain", required=True)
    build.add_argument("--sources", required=True)
    build.add_argument("--duration", type=int, choices=[5, 7, 9, 12], required=True)
    build.add_argument("--user-level", default="")
    build.add_argument("--output", required=True)
    build.set_defaults(func=command_build)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--report", required=True)
    evaluate.add_argument("--sources")
    evaluate.add_argument("--output")
    evaluate.set_defaults(func=command_evaluate)

    github = sub.add_parser("github-search")
    github.add_argument("--query", required=True)
    github.add_argument("--min-stars", type=int, default=0)
    github.add_argument("--updated-after", default="")
    github.add_argument("--limit", type=int, default=10)
    github.add_argument("--output", required=True)
    github.set_defaults(func=command_github)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
