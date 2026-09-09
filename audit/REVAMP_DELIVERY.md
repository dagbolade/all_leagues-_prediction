# Matchday revamp delivery

Verified 2026-09-09T13:36:05.965340+00:00.

## Delivered

The active application has been replaced with the `sportslab` package. Existing `app.run:app`, unified API and convenience launchers point to the same implementation. The original source datasets and models remain available; retired entrypoints are preserved under `legacy/entrypoints`.

- Responsive dashboard, match explorer, factual form/xG analysis, results, model lab and source coverage pages.
- Refreshed football results, Champions League history/fixtures, ATP/WTA results, NBA results and official EuroLeague results plus upcoming fixtures.
- Transactional SQLite imports, explicit club identity reconciliation, immutable raw downloads, source error reporting and CLI writer lock.
- Shared chronological features, real outcomes, explicit class mappings, calibrated outcome probabilities and coherent football goal markets.
- Per-sport untouched chronological benchmarks and versioned artifacts with checksums. Serving models are separately refit, with a recent calibration holdout. Benchmark failure against the class-frequency baseline prevents promotion.
- Browser-session prediction journal with immutable probabilities, CSRF protection, exact-fixture settlement, postponed-fixture reconciliation, cancellation voids and correction history.
- Lean Python 3.12 environment, dependency lock, start/refresh scripts, regression suite and CI workflow.

## Measured coverage

| Sport | Records | Completed | Latest result |
|---|---:|---:|---|
| Football | 103,415 | 103,174 | 2026-09-08 |
| Basketball | 9,721 | 9,341 | 2026-06-13 |
| Tennis | 31,630 | 31,630 | 2026-08-30 |

Champions League: 647 records, including 509 finished matches. Observed xG is attached to 8,186 football matches, from Understat. Coverage is partial, concentrated in five major European leagues; no xG was fabricated for uncovered competitions.

NBA results extend to 13 June 2026, EuroLeague results to 24 May 2026, and tennis to 30 August 2026. The app also contains 380 upcoming EuroLeague fixtures. These dates describe downloaded coverage, not a claim of live or exhaustive feeds.

## Final chronological benchmarks

| Sport | Test matches | Accuracy | Log loss | Baseline log loss |
|---|---:|---:|---:|---:|
| Football | 21,053 | 48.5% | 1.025 | 1.074 |
| Basketball | 1,072 | 65.3% | 0.634 | 0.689 |
| Tennis | 1,369 | 62.0% | 0.643 | 0.693 |

These are held-out results for the evaluated training recipe, not a backtest of the subsequently refit serving artifact. Football is a three-way outcome task; basketball and tennis are binary, so raw accuracies are not directly comparable. All beat their class-frequency log-loss baseline. This does not establish betting profitability or superiority over bookmaker prices.

## Verification

- 18 regression tests passed, including future-score invariance, same-day batching, shared inference features, labels, missing values, Unicode aliases, coherent markets, idempotent imports, ownership, CSRF, postponement and cancellation handling.
- Eight running HTTP routes passed smoke checks. Real UCL and EuroLeague fixtures and a tennis scenario generated valid forecasts. Outcome probabilities summed to one.
- Desktop and 390-pixel mobile layouts inspected in the browser; no horizontal overflow. Scenario date display verified after fixing a UTC-to-local rollover. Final browser logs contained no warnings or errors.
- `pip check` passed; active Python source compiled successfully. Exact API checks, data counts and model versions are in `revamp-verification.json`.

## Original audit findings addressed

| Audit issues | Active implementation resolution |
|---|---|
| 1–3: false labels, future leakage, copied live rows | Actual result labels and one causal feature builder; current fixtures rebuilt from earlier results. |
| 4–5: ambiguous probabilities, misleading validation | Explicit classes, temporal calibration and separate benchmark/serving manifests. |
| 6–7: fake xG and missing half-time labels | Observed xG has a source and coverage; missing values stay missing. Unsupported half-time markets retired. |
| 8–9: stale data and incorrect settlement | Provider refreshes, visible failures, exact IDs, postponements and score-correction events. |
| 10–11: fixed predictions, shared state and unsafe HTML | Alternate serving paths replaced, no fallback probability constants, per-session journal and safe DOM rendering. |
| 12–14: rest/scoring definitions, unsupported advanced claims, other sports | All-venue rest, coherent score distribution, independently tested sport models; unmeasured legacy features removed from the active UI. |
| 15: runtime and maintenance | Isolated working environment, lean dependencies, lock file, tests, CI and canonical launchers. |

## Explicit remaining limits

- No public deployment or recurring refresh was created. Start locally with `Start-Matchday.ps1`; refresh with `Refresh-Matchday.ps1`, optionally `-Train`. Hosting requires durable data/model storage.
- The API rejected UCL season 2022 with HTTP 403. More history requires a provider/account that supplies it. Provider gaps are visible and retained data is not replaced by synthetic results.
- No current lineups, injury feed, player-level availability, bookmaker odds or closing-line comparison. Half-time, cards, corners, NFL and old accumulator/LLM chat paths are retired, not claimed as measured features.
- Legacy tennis names can differ between full-name historical feeds and abbreviated modern feeds. The system does not fuzzy-merge people. New or insufficiently covered participants return unavailable until there are five earlier records.
- The journal is private to a signed browser session, not an authenticated account with cross-device recovery. Old shared chat/journal files are not migrated into a public user session.
- Existing older code under `footy`, legacy blueprints and sport adapters remains reference material and is not imported by the current app. The audit defects were removed from the active execution paths; archived implementations were not represented as repaired production code.
- Historical accuracy is insufficient to establish a profitable betting strategy. Next useful measurement is a growing frozen prospective journal; meaningful model additions should beat the same chronological baseline before promotion.

Original tracked processed-data files were not intentionally changed by this implementation; Git LFS filter differences can report them as modified. The new data and models are in separate ignored directories.
