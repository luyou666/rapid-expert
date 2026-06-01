# Contributing

Contributions are welcome if they improve safety, reliability, documentation, tests, or platform compatibility.

## Requirements

- Preserve the MIT License header where applicable.
- Do not add secrets, private data, API keys, tokens, or proprietary datasets.
- Do not add instructions that enable illegal, harmful, deceptive, or unauthorized behavior.
- High-risk domain additions must include safety boundaries and professional-confirmation language.
- New CLI behavior should include a test or validation command where practical.

## Before Opening a Pull Request

Run:

```bash
python scripts/validate_deploy.py
```

Also check that generated cache files are not committed:

```bash
python -c "from pathlib import Path; print(list(Path('.').rglob('__pycache__')))"
```

## Legal Note

By contributing, you represent that you have the right to license your contribution under the MIT License used by this project.

