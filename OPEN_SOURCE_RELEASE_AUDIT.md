# Open Source Release Audit

This file records the final checks expected before publishing this project to GitHub.

## License

- Project license: MIT License.
- SPDX identifier: `MIT`.
- Canonical reference: https://spdx.org/licenses/MIT.html
- The complete license text is stored in `LICENSE`.

## Disclaimer Coverage

Disclaimer text is included in:

- `DISCLAIMER.md`
- `README.md`
- adapter README/runbook files
- generated report templates

The project is for learning, research, source organization, and workflow assistance only. It is not legal, investment, medical, psychological, cybersecurity, chemical, biosafety, tax, accounting, audit, compliance, regulatory, or other professional advice.

## Privacy and Secrets

The following local runtime files must never be committed:

- `.env`
- `.env.*`
- `.env.local`
- `.study-hacker.local.json`
- `sessions/`
- `outputs/`
- `queue/jobs/`
- `queue/locks/`
- `dist/`
- caches and logs

These paths are covered by `.gitignore`. If publishing by manually uploading a folder instead of using Git, delete these local files first.

## Third-Party Content

Reports may reference public websites, GitHub repositories, courses, datasets, APIs, or model providers. Third-party materials remain subject to their own copyrights, licenses, terms of use, rate limits, and privacy policies.

Do not copy third-party content into this repository unless its license permits redistribution and the required notices are preserved.

## Pre-Publish Commands

Run:

```bash
python scripts/run_tests.py
python scripts/validate_deploy.py
```

Then scan for accidental secrets:

```bash
rg -n "sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN .*PRIVATE KEY-----" .
```

Review matches manually because generic scanners may produce false positives in URLs or ordinary text.

## Limit

This audit reduces common open-source release risks, but it is not legal advice. For commercial, regulated, or high-risk use, ask qualified legal/security professionals to review the release.
