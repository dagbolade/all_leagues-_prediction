# Retired implementation

The entrypoints in this directory preserve the pre-revamp source for reference. Do not run them. They depend on the archived feature definitions and unreliable metrics documented in `audit/PROJECT_AUDIT_2026-09-09.md`.

The current app, CLI, feature pipeline, models and data store are all in `sportslab/`. Existing `footy/`, old `app` blueprints/templates, `core/`, and sport adapters are historical code and are not imported by the current server. NFL and old unsupported markets are not served. Old trained models are retained for reproducibility, never loaded by Matchday.
