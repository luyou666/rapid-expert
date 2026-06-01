# Privacy and Data Handling

This project is designed to run locally first. It does not intentionally collect telemetry, analytics, user tracking identifiers, or usage statistics.

## Local Data

The CLI and harness may create local runtime files while you use the project:

- `.env.local`
- `.study-hacker.local.json`
- `sessions/`
- `outputs/`
- `queue/jobs/`
- `queue/locks/`
- `dist/`

These paths may contain prompts, generated reports, API configuration metadata, logs, or local execution state. They are excluded by `.gitignore` and should not be committed or uploaded to public repositories.

## Secrets

Do not commit API keys, provider tokens, bearer tokens, cookies, SSH keys, private keys, customer data, private documents, or proprietary datasets.

Use `.env.example` as a template and create `.env` or `.env.local` only for local execution. Rotate any secret that was ever pasted into chat, logs, screenshots, terminal history, or a public repository.

## Third-Party Services

If you configure an external model provider, search API, GitHub token, proxy, or custom API base URL, prompts and task data may be sent to that provider according to its own terms and privacy policy.

Before using third-party APIs, review their terms, data retention settings, logging behavior, and allowed use policies.

## User Responsibility

Users are responsible for:

- removing private data before publishing outputs
- verifying that they have rights to use uploaded documents or datasets
- complying with privacy, data protection, employment, financial, healthcare, and other applicable laws
- avoiding sensitive personal data unless there is a lawful basis and a clear need

## Public Issue Reports

Do not include secrets, personal data, private prompts, private logs, exploit payloads, or customer information in public GitHub issues.

If a security report requires sensitive detail, use a private reporting channel such as GitHub Security Advisories when available.
