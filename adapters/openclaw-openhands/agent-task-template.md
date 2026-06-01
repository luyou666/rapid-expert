# Agent Task Template

## Disclaimer

This project is for learning, research, source organization, and workflow assistance only. It is not professional advice. High-risk outputs require qualified professional confirmation.

## Objective

Generate a practical domain expert learning kit for the user's target domain. The kit must help a beginner participate in a real business task with AI / Agent assistance within 5-12 days.

## Mandatory Steps

1. Ask intake questions before generating the kit.
2. Determine learning duration: 5, 7, 9, or 12 days.
3. Search latest sources when current facts are needed.
4. Search reusable agents, skills, RAG projects, GitHub repos, courses, and datasets.
5. Generate domain knowledge package.
6. Generate practical exercises and final evaluation.
7. Apply safety rules for high-risk domains.
8. When running inside a repo, use the provided scripts under `scripts/` or `adapters/openclaw-openhands/scripts/`.

## Files To Produce

- domain-map.md
- industry-chain.md
- jargon.md
- business-model.md
- moat-analysis.md
- case-library.md
- source-library.md
- reusable-solutions.md
- learning-plan.md
- final-practical-task.md
- evaluation-report.md

## Minimal Script Chain

```bash
python scripts/collect_sources.py --domain "<domain>" --question "<question>" --output outputs/sources_raw.json
python scripts/rank_sources.py --input outputs/sources_raw.json --output outputs/sources_ranked.json
python scripts/build_report.py --domain "<domain>" --sources outputs/sources_ranked.json --duration "<5|7|9|12>" --output outputs/domain_kit_report.md
```

## Done Criteria

The task is done only when the generated package includes:

- a concrete learning duration with reason
- source strategy
- reusable solution search results
- risk boundaries
- final practical task
- evaluation criteria
