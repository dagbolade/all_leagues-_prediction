# Matchboard forecasts and live score view — 24 October 2026

Implemented locally:
- Pre-match probability cards for visible upcoming fixtures, using the existing validated sport models. Outcome probabilities, most likely football score with its probability, basketball point estimates, warnings and model/calculation timestamps are shown.
- Batch endpoint capped at 24 fixture IDs, CSRF protected, partial-unavailability responses, persistent model/data/fixture cache invalidation, and rejection at/after kickoff.
- Live / today navigation and legacy `/live-predictions` route; football provider scoreboard with status/search filters, manual refresh, one-minute visible-page refresh and shared SQLite rate limiting across workers.
- Source observation timestamps separate from HTTP fetch time, explicit provider delay warnings, unknown scores/clock retained as missing, phase labels for extra time, and 'awaiting provider status' for overdue scheduled fixtures.
- Exact-identity saved pre-match references can appear alongside live observations, but never become live probabilities or journal entries.

Validation:
- 28 pytest tests passed, including batch validation, cache invalidation by model, rejection after kickoff, unknown-clock/score handling, shared provider caching, failure retention without leaking exceptions, exact reference identity and timestamp checks, and current UTC day filtering.
- JavaScript syntax validation passed.
- Real local overview produced 24/24 forecasts. Browser reported no JavaScript errors during the core checks.
- Live provider returned 42 current-day matches, of which 36 belonged to connected competition mappings. Missing minute fields and stale scheduled statuses were observed and explicitly surfaced.
- Provider dateTo is exclusive; the adapter requests today through tomorrow and independently filters to today's UTC date.

Limits:
- In-play probabilities are NOT implemented or advertised. The existing models are pre-match only; no validated in-play model, reliable clock/event feed, or score-state calibration exists.
- football-data.org's free plan documents delayed scores. Some past-kickoff fixtures remained TIMED in the live verification. Refreshing HTTP cannot fix provider coverage or subscription delay.
- Basketball/tennis live feeds are not connected; the UI says so.
- Before Railway deployment, configure FOOTBALL_DATA_API_KEY there if it is absent. No credentials are committed and no provider subscription was purchased.
- Live cache and public forecast summaries are operational database tables, not part of the public deployment seed. No changes were made to training records or private journal settlement by this feature.

References:
- https://www.football-data.org/pricing
- https://docs.football-data.org/general/v4/overtime.html
- https://docs.football-data.org/general/v4/match.html
- https://docs.football-data.org/general/v4/index.html
