# Security Policy

## Supported Scope

This project is a learning and workflow toolkit. It does not provide offensive security capabilities and must not be used for unauthorized access, exploitation, credential theft, stealth, evasion, or data exfiltration.

## Reporting Security Issues

If you find a vulnerability in this project, open a GitHub issue with:

- affected file or component
- reproduction steps
- expected behavior
- actual behavior
- potential impact

Do not include secrets, private data, exploit payloads, or instructions that enable unauthorized harm in public reports.

If the report requires sensitive reproduction details, credentials, private logs, or non-public customer data, do not post it publicly. Use a private reporting channel such as GitHub Security Advisories when available.

## Secrets and Local Files

Never commit:

- `.env`, `.env.*`, or `.env.local`
- `.study-hacker.local.json`
- API keys, bearer tokens, cookies, SSH keys, or private keys
- private prompts, private documents, customer data, or proprietary datasets
- generated `sessions/`, `outputs/`, `queue/`, `dist/`, caches, or logs

Rotate any secret that was pasted into chat, screenshots, logs, terminal history, or a public repository.

## Safety Boundary

Allowed:

- defensive security learning
- risk identification
- compliance checklists
- authorized audit planning
- safe remediation guidance

Not allowed:

- unauthorized exploitation
- bypassing detection or access controls
- credential theft
- malware, phishing, persistence, stealth, or evasion
- instructions for illegal data access
