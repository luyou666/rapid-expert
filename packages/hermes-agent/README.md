# Rapid Expert MVP for Hermes Agent

## Disclaimer

This package is for learning, research, source organization, and workflow assistance only. It is not professional advice. High-risk decisions require qualified professional confirmation.

## Files

- `../../adapters/hermes-agent/config.yaml`
- `../../adapters/hermes-agent/system-prompt.md`
- `../../adapters/hermes-agent/workflow.md`
- `../../adapters/hermes-agent/rag-config.md`
- `../../adapters/hermes-agent/memory-policy.md`

## Install Pattern

1. Register `system-prompt.md` as the system prompt.
2. Register workflow commands from `config.yaml`.
3. Bind tools to `python ../../scripts/rapid_expert.py`.
4. Use `state/schemas/session-state.schema.json` for state validation.
5. Use `tests/final-practical-evaluation.md` for final acceptance.

## Tool Commands

```bash
python ../../scripts/rapid_expert.py risk --domain "<domain>" --question "<question>"
python ../../scripts/rapid_expert.py plan --domain "<domain>" --user-level "<level>" --daily-time "<time>" --goal "<goal>"
python ../../scripts/rapid_expert.py scan --domain "<domain>" --question "<question>" --output outputs/sources_raw.json
python ../../scripts/rapid_expert.py rank --input outputs/sources_raw.json --output outputs/sources_ranked.json
python ../../scripts/rapid_expert.py build --domain "<domain>" --sources outputs/sources_ranked.json --duration 7 --output outputs/domain_kit_report.md
python ../../scripts/rapid_expert.py evaluate --report outputs/domain_kit_report.md --sources outputs/sources_ranked.json --output outputs/evaluation.json
```
