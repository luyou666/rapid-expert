# Release Checklist

## Required

- [ ] Read `DISCLAIMER.md`, `SECURITY.md`, `LICENSE`, and `NOTICE.md`.
- [ ] Read `PRIVACY.md` and `OPEN_SOURCE_RELEASE_AUDIT.md`.
- [ ] Confirm both `README.zh-CN.md` and `README.en.md` exist and are linked from `README.md`.
- [ ] Run `python scripts/harness_contract.py write`.
- [ ] Run `python scripts/run_tests.py`.
- [ ] Run `python scripts/validate_deploy.py`.
- [ ] Run `python scripts/harness_diag.py health`.
- [ ] Run `python scripts/harness_diag.py export --output dist/rapid-expert-harness.zip`.
- [ ] Confirm `HARNESS_API_TOKEN` is set before starting the HTTP server, including local `127.0.0.1` use.
- [ ] Confirm `HARNESS_ALLOW_UNAUTHENTICATED=1` is not used outside isolated local development.
- [ ] Confirm `sessions/`, `queue/jobs/`, `queue/locks/`, `outputs/`, `dist/`, caches, logs, and `.env*` are not committed.
- [ ] Confirm `.study-hacker.local.json` is not committed.
- [ ] Run a secret scan and manually review matches before pushing.
- [ ] If publishing by manual upload instead of Git, delete local runtime files before packaging.

## Optional Docker Smoke

```bash
docker compose up --build
curl -H "Authorization: Bearer <HARNESS_API_TOKEN>" http://127.0.0.1:8765/health
curl -H "Authorization: Bearer <HARNESS_API_TOKEN>" http://127.0.0.1:8765/openapi.json
```

## Notes

This project is for learning, research, source organization, and workflow assistance only. It is not professional advice.
