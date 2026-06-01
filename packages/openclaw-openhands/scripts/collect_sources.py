#!/usr/bin/env python3
"""Collect source candidates for a target domain.

This is a minimal, dependency-free collector intended for agent runtimes.
It uses DuckDuckGo HTML when network is available and falls back to an
auditable query plan when search fails.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


CURATED_SEED_SOURCES = [
    {
        "title": "NIST AI Risk Management Framework",
        "url": "https://www.nist.gov/itl/ai-risk-management-framework",
        "summary": "AI 风险管理、治理和可信系统的一线参考。",
    },
    {
        "title": "Atlassian Agile Product Management",
        "url": "https://www.atlassian.com/agile/product-management",
        "summary": "产品管理、敏捷协作和路线图实践参考。",
    },
    {
        "title": "ProductPlan Product Roadmap Glossary",
        "url": "https://www.productplan.com/glossary/product-roadmap/",
        "summary": "产品路线图和规划术语参考。",
    },
    {
        "title": "Y Combinator Startup Library",
        "url": "https://www.ycombinator.com/library",
        "summary": "创业、用户、增长和产品验证案例库。",
    },
    {
        "title": "Strategyzer Library",
        "url": "https://www.strategyzer.com/library",
        "summary": "商业模式、价值主张和创业实验方法参考。",
    },
    {
        "title": "GOV.UK Service Manual: Agile Delivery",
        "url": "https://www.gov.uk/service-manual/agile-delivery",
        "summary": "公共服务敏捷交付和团队协作参考。",
    },
    {
        "title": "GOV.UK Service Manual: Design",
        "url": "https://www.gov.uk/service-manual/design",
        "summary": "服务设计、用户研究和可用性实践参考。",
    },
    {
        "title": "Usability.gov User Research Methods",
        "url": "https://www.usability.gov/how-to-and-tools/methods/user-research/index.html",
        "summary": "用户研究方法和可用性测试参考。",
    },
    {
        "title": "Microsoft AI Agents for Beginners",
        "url": "https://github.com/microsoft/ai-agents-for-beginners",
        "summary": "AI Agent 入门课程和示例项目。",
    },
    {
        "title": "Microsoft Generative AI for Beginners",
        "url": "https://github.com/microsoft/generative-ai-for-beginners",
        "summary": "生成式 AI 入门课程和实战示例。",
    },
    {
        "title": "SVPG Articles",
        "url": "https://www.svpg.com/articles/",
        "summary": "产品发现、产品团队和产品战略文章库。",
    },
    {
        "title": "Open Product Management",
        "url": "https://github.com/ProductHired/open-product-management",
        "summary": "开源产品管理学习资源集合。",
    },
]


class DuckResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v or "" for k, v in attrs}
        if tag == "a" and "result__a" in attrs_dict.get("class", ""):
            self._in_result = True
            self._href = attrs_dict.get("href", "")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_result:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result:
            title = " ".join(part.strip() for part in self._text_parts if part.strip())
            url = normalize_duck_url(self._href)
            if title and url:
                self.results.append({"title": html.unescape(title), "url": url})
            self._in_result = False
            self._href = ""
            self._text_parts = []


def normalize_duck_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    if url.startswith("//"):
        return "https:" + url
    return url


def search_duckduckgo(query: str, max_results: int) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 source-collector/0.1",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8", errors="replace")
    parser = DuckResultParser()
    parser.feed(body)
    return parser.results[:max_results]


def url_reachable(url: str) -> bool:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 source-collector/0.1",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def curated_sources(query: str, accessed_at: str, limit: int) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for item in CURATED_SEED_SOURCES:
        if not url_reachable(item["url"]):
            continue
        sources.append(
            {
                "title": item["title"],
                "url": item["url"],
                "summary": item["summary"],
                "query": query,
                "accessed_at": accessed_at,
                "collector": "curated_reachable_seed",
            }
        )
        if len(sources) >= limit:
            break
    return sources


def build_queries(domain: str, question: str, region: str, time_range: str) -> list[str]:
    base = [domain, question, region, time_range]
    base_text = " ".join(item for item in base if item).strip()
    seeds = [
        base_text,
        f"{domain} industry report {region}",
        f"{domain} regulation policy {region}",
        f"{domain} github agent rag dataset",
        f"{domain} market competitors business model",
        f"{domain} failure case risk",
    ]
    clean = []
    seen = set()
    for seed in seeds:
        seed = re.sub(r"\s+", " ", seed).strip()
        if seed and seed not in seen:
            clean.append(seed)
            seen.add(seed)
    return clean


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--question", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--time-range", default="")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    accessed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    queries = build_queries(args.domain, args.question, args.region, args.time_range)
    sources: list[dict[str, str]] = []
    errors: list[str] = []

    if not args.no_network:
        for query in queries:
            try:
                for result in search_duckduckgo(query, args.max_results):
                    result.update(
                        {
                            "query": query,
                            "accessed_at": accessed_at,
                            "collector": "duckduckgo_html",
                        }
                    )
                    sources.append(result)
            except Exception as exc:  # noqa: BLE001 - preserve failure reason for audit.
                errors.append(f"{query}: {exc}")

    deduped = []
    seen_urls = set()
    for source in sources:
        url = source.get("url", "")
        if url and url not in seen_urls:
            deduped.append(source)
            seen_urls.add(url)

    status = "ok" if deduped else "query_plan_only"
    manual_fallback = len(deduped) == 0
    if not deduped and not args.no_network:
        fallback_query = queries[0] if queries else args.domain
        deduped = curated_sources(fallback_query, accessed_at, max(args.max_results, 8))
        if deduped:
            status = "curated_seed_sources"
            manual_fallback = False

    payload = {
        "domain": args.domain,
        "question": args.question,
        "region": args.region,
        "time_range": args.time_range,
        "accessed_at": accessed_at,
        "queries": queries,
        "sources": deduped,
        "errors": errors,
        "status": status,
        "manual_fallback": manual_fallback,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
