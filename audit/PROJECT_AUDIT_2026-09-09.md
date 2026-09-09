# Football prediction project audit — 9 September 2026

The project has useful foundations: substantial historical results, several working data adapters, rolling features, Elo, tree models, a Poisson score model, and a web interface. However, its current prediction accuracy is not established. The highest priorities are correcting target labels, removing future information from features, and making training and live prediction use the same feature calculation. Adding UCL data should follow that foundation work.

This is an assessment of the local checkout, not a certification of the deployed website. Application code, models and source data were not changed. Audit scripts and evidence were added under `audit/`.

## Scope and verification

- Inventoried and syntax-parsed 114 project Python files, approximately 29,675 lines; no syntax errors. Reviewed the main data, training, serving, evaluation and deployment paths and representative supporting modules and templates.
- Inspected all five season workbooks under `data/raw`, the processed football CSVs and preferred ZIP, the basketball/tennis/NFL CSVs, and model file presence/size/LFS-pointer status.
- Executed isolated methods from the actual source to reproduce inference-date, opponent-feature, probability, rest-day and future-referee-data defects. The methods were extracted with Python AST to avoid importing application startup and its unrelated dependencies; these are focused behavioral probes, not full-app tests.
- Consulted official provider documentation for the proposed UCL ingestion path.
- The local `.venv` points to a Python 3.11 interpreter that cannot be launched here. System Python lacks pandas, scikit-learn, Flask and other required packages. Bundled Python supplied pandas/openpyxl for read-only data analysis. Full application startup, deserialization/prediction with the saved estimators, pytest, retraining and an independent out-of-time model benchmark were therefore **not completed**. Artifact presence does not establish artifact compatibility or training provenance.
- Git status required a command-local ownership exception and disabling LFS clean filters for inspection. It reports two existing data artifacts as modified; with those filters disabled this is not a reliable content-diff assessment of LFS files. No Git configuration or application artifacts were edited by this audit.

Detailed machine-readable observations are in [evidence.json](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/audit/evidence.json>). No new estimate of model accuracy is asserted here.

## What actually runs

| Area | Current path | Assessment |
|---|---|---|
| Configured web deployment | `Procfile` / `railway.json` → `app.run:app` | Registers original football, multi-sport and advanced blueprints |
| Main football predictions | `app/routes.py` → `footy/predictor_utils.py` | Loads `models/football_models.joblib`; prefers the processed ZIP |
| Full football training | `main.py` → loaders → rolling features → feature engineering → `BayesianFootballPredictor` | Separate training pipeline with correctness issues described below |
| Weekly update | `run_weekly_update.ps1` → `update_data.py` | Reads an existing workbook; does not first download fresh results |
| Domestic downloads | `automated_football_scraper.py` | Separate script; incomplete/mislabelled competition registry |
| UCL live fixtures | `app/services/live_scores_service.py` | `CL: 2001` already present; no corresponding UCL training history found |
| Alternative football API | `api/unified_api.py` → `sports/football/football_predictor.py` | Different adapter; has a fixed-output fallback and interface mismatches |
| Alternative UI / training | `app/modern_routes.py`, `footy/fast_model_training.py`, `run_optimization.py` | Not the configured default web entry point; incompatible outcome encoding |
| Other sports | `app/multi_sport_routes.py` | Prefers advanced artifacts ahead of the artifacts named backtested |
| Advanced UI | AI chat, accumulator, live tracker, league table | Some state and estimates are generic or heuristic rather than validated model outputs |

There is no need to discard the entire application. Consolidating these paths would remove a large source of inconsistent behavior.

## Dataset findings

| Artifact | Matches | Columns | Latest match | Important observation |
|---|---:|---:|---|---|
| Preferred football ZIP | 58,304 | 376 | 2026-04-01 | 38 domestic competition codes; no UCL code |
| Football CSV fallback | 56,036 | 374 | 2026-04-01 | Different rows and xG values from ZIP |
| Older enhanced CSV | 31,202 | 246 | 2025-08-04 | Substantially older fallback |
| `complete_features.csv` | 1,000 | 267 | 2021-09-14 | 275 score/result disagreements; unsuitable silent fallback |
| Combined basketball | 9,149 | 20 | 2026-04-07 | NBA and EuroLeague |
| Tennis real-data CSV | 28,588 | 14 | 2026-04-05 | Does not by itself validate the claimed model scores |
| NFL sample CSV | 500 | 9 | 2024-04-05 | Sample data; 14 repeated date/home/away keys |

The preferred football ZIP is 161 days behind the audit date. Its EPL data stops on 22 March; 16 additional global leagues stop in August 2025. No 2026–27 raw season workbook is present. The ZIP and primary CSV each have no repeated date/home/away keys and no disagreement between their final scores and H/D/A result fields; those checks are encouraging, but do not resolve feature correctness.

The metadata matches the ZIP's 58,304 rows, not the CSV's 56,036. A fallback can therefore silently change the model's information base. Select data through a versioned manifest and validate its hash/schema against the model, instead of loading the first existing file.

## Findings in priority order

### 1. Critical: goals targets do not represent the real match result

[model_training.py:559](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/footy/model_training.py:559>) uses actual goals **OR** an expected-goals threshold to label over/under targets. A 0–0 match can become a positive over-2.5 example when `BayesianExpectedTotal > 2.8`. That same expected-total feature is available to the learner.

Applying the current expressions to the preferred ZIP gives:

| Market | Actual positive rate | Training-label positive rate | Actual unders relabelled as overs |
|---|---:|---:|---:|
| Over 1.5 | 74.67% | 97.67% | 13,409 |
| Over 2.5 | 50.40% | 79.40% | 16,910 |
| Over 3.5 | 28.23% | 42.14% | 8,107 |

These are measured label discrepancies, not a new evaluation of the stored models. An always-over classifier would score 97.67% against the altered over-1.5 labels. That illustrates why a high reported score can be meaningless.

**Fix:** derive settled-market targets strictly from completed-match scores. Keep forecasts only as inputs. Add tests covering 0–0, boundary totals, missing results and cup extra time. Rebuild features and retrain; changing inference alone cannot repair models trained on incorrect labels.

### 2. Critical: feature generation includes future outcomes

[rolling_features.py:33](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/footy/rolling_features.py:33>) calculates league/team Elo priors from the entire supplied dataset. Dynamic home advantage also examines all home results. Team-strength priors use full-dataset goal averages. The rolling generator's comments about `shift(1)` do not protect these aggregate calculations.

[feature_engineering.py:55](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/footy/feature_engineering.py:55>) computes referee summaries from all matches, then maps them back onto earlier rows. The main `engineer_features` sequence invokes this function. Other full-sample league and opening-week summaries need the same treatment.

**Reproduction:** the audit appends a later high-scoring match and observes the referee feature on an unchanged earlier match change. The old feature should remain invariant.

There is an additional indexing hazard: team history is selected with `df.index < idx` after sorting by season/date without resetting the index. Index order is not a guarantee of time order, especially with mixed calendar-year and cross-year competitions.

**Fix:** use a shared chronological feature builder with a strict information cutoff. Calculate each fixture's features before updating team/referee state. Initialize priors from earlier data only. Group simultaneous fixtures so results from the same prediction batch cannot enter one another's features. Test that modifying future results never changes past features.

### 3. Critical: live features are copied from old fixtures

[predictor_utils.py:146](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/footy/predictor_utils.py:146>) accepts `match_date` but never filters history by it. It copies a home team's previous home row and an away team's previous away row. Non-team-specific fields, including head-to-head/context features, are inherited from old opponents. Copying already-shifted rows also leaves team state behind the most recent result.

**Reproduction:** a request dated June 2025 receives a home-form value from January 2026; changing the request date to 2027 yields the identical vector. A requested A–B fixture inherits A–C's H2H average of 7 rather than A–B's 1.

Training/inference definitions also differ: inference adds 35 to Elo advantage, and reconstructs selected probability/expected-goals features with different formulas. Unknown teams produce a zero-filled vector rather than an explicit unsupported result.

**Fix:** use the exact training feature builder for new fixtures, including match ID, UTC kickoff, competition, venue and an `as_of` timestamp. Persist team encodings with the model; the updater currently recreates encodings from sorted names, so adding a team can change IDs without retraining. Reject incompatible schemas and unknown teams or use an explicitly validated cold-start policy.

### 4. High: returned probabilities have inconsistent meanings

[predictor_utils.py:476](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/footy/predictor_utils.py:476>) returns `max(proba)` for binary tasks, then its constraint code interprets the scalar as the probability of the positive event.

**Reproduction:** a classifier returning `[0.8, 0.2]` produces `Over 2.5: No` and a scalar probability of `0.8`. That is the confidence in No, not P(over). Downstream hierarchy adjustments and estimated totals can consequently be wrong.

The separate numeric constraint validator also fails a direct hierarchy check: input `(0.1, 0.2, 0.3)` becomes `(0.2, 0.3, 0.3)`, still violating P(over 1.5) ≥ P(over 2.5).

Calibrated models are loaded and advertised, but prediction iterates `self.models`, not `self.calibrated_models`. The named “confidence intervals” are heuristic scalar transformations, not statistical intervals. The fallback expected-goals formula starts with a fixed 1 and omits the complete goal-distribution tail. A draw heuristic can replace the highest-probability outcome without evidence of out-of-time benefit.

**Fix:** return explicit class probabilities, using the artifact's class mapping. Separate event probability, chosen selection and selection probability. Evaluate the actual served/calibrated outputs. Derive related goal markets from a coherent score distribution where possible; test monotonicity, normalization and consistency after any adjustment.

### 5. High: reported validation is optimistic and does not measure the deployed pipeline

`model_training.py:1078` fits supervised feature selection before time-series folds. Hyperparameter search uses the outer validation labels, then reports on those same labels. The model kept for serving is the best fold's estimator, not a final fit on all eligible training history. Calibration uses ordinary `cv=3` on all rows. The fast trainer also uses ordinary cross-validation.

`footy/train_evaluate.py:79` evaluates on the data just supplied for fitting; it also imports `get_model_and_params`, which is absent from the current model-training module. The alternative fast trainer encodes H=2/A=0, while the main predictor assumes H=0/A=2. Feeding fast artifacts into that predictor can invert winner interpretation.

**Fix:** reserve a final untouched chronological test window. Use earlier development folds for feature selection, tuning and calibration. Then freeze the pipeline, test the exact serving implementation once, and report by market, competition and season. Save fold boundaries, dataset/code hashes, class labels, feature definitions, calibration method and all metrics with each artifact. Scikit-learn's [official leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) specifically recommends fitting preprocessing and feature selection only on training data.

### 6. High: real xG, estimated xG and missing data are mixed

In the primary CSV, every `HomexG` value matches the code's shot proxy `0.08*HS + 0.25*HST` after its missing-value convention. The ZIP also has `Home_xG`/`Away_xG`, but only 7,026 of 58,304 home entries are nonzero. The columns alone do not establish that all entries came from Understat.

`footy/xg_scraper.py` supports five domestic leagues and no UCL. `understatapi` is not listed in requirements; when absent, fetching quietly degrades to no client. Blanket `fillna(0)` means unknown xG becomes a real-looking zero, and subsequent missingness checks can conclude no backfill is needed. The xG merge lacks provider fixture IDs and a uniqueness validation. Existing league labels also need canonical mapping before joining.

**Fix:** retain source, provider, fetch time and a missingness flag. Store actual provider xG separately from shot-derived estimates and model-predicted goals. Track join coverage per competition/season. Use rolling xG for and against across all venues; add venue-specific splits separately. Verify coverage on returned data before selecting a UCL xG provider.

### 7. High: missing half-time results become training negatives

The extra global-league workbook sheets often contain only ten basic columns and no half-time goals. Both feature pipelines end in blanket `fillna(0)`. Target preparation later checks `.notna()`, so an unknown half-time score that was converted to zero is considered observed. This also affects second-half targets derived by subtracting half-time goals.

The preferred ZIP contains **20,957 rows with zero half-time goals and an invalid half-time result code**, but no null half-time goal fields. This is direct evidence that missingness has been lost; it should not be interpreted as 20,957 observed 0–0 half-time scores.

**Fix:** preserve nullable result fields through the whole pipeline. Apply target-specific eligibility masks from source coverage, never imputed labels. Do not offer a market whose required data was unavailable in training.

### 8. High: scheduled updating does not guarantee fresh or complete data

`run_weekly_update.ps1` calls only `update_data.py`. That script loads the newest existing workbook; it does not run the domestic results downloader first. The downloader's registry advertises 22 leagues but contains 21 keys, mislabels football-data.co.uk's `EC` domestic competition, adds `WC`, and omits SC2/SC3. Its run method validates only one downloaded league and overwrites the season workbook with whichever downloads succeeded, potentially dropping other existing sheets.

The updater only identifies new match keys. It cannot reliably apply corrected scores or enrich an existing fixture after its first import. Model/data files are written separately; the running process and pair-only caches are not reloaded as one versioned unit.

**Fix:** one orchestrated download → validate → upsert → feature build → optional train → publish process. Preserve existing competitions on partial failures, use atomic outputs and row-count/freshness gates, and return failure exit codes for incomplete required updates. Add current-season and calendar-league handling to a provider-specific competition registry.

### 9. High: the accuracy dashboard can settle the wrong fixture

[routes.py:1284](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/app/routes.py:1284>) picks a finished match from one team's recent results using a ±1-day date check. It does not verify both teams or home/away orientation. Older pending predictions can also fall outside the last-five-matches lookup.

The save endpoint accepts client-supplied probabilities and predictions, defaults the date to today, and has no immutable pre-kickoff model snapshot. Deleting records can bias the displayed hit rate. There is no per-market settlement record for the complete prediction set.

**Fix:** store a provider fixture ID, both canonical team IDs, kickoff, prediction timestamp, model/data version and all probabilities server-side. Freeze entries before kickoff. Settle using fixture ID and the market's regulation-time rules. Keep corrections and exclusions auditable rather than silently editing history. This is necessary for the no-money prediction assessment you proposed.

### 10. High: the alternative football API can return invented fixed predictions

[football_predictor.py:391](<C:/Users/dagbo_b40tnyc/OneDrive/all_leagues _prediction/sports/football/football_predictor.py:391>) creates `SimplePredictor` when loading the existing raw model bundle. Every fixture receives 45% home, 30% draw, 25% away and a 2–1 score, regardless of the loaded estimators.

The adapter also calls a nonexistent `generate_all_features`, passes an unsupported `feature_columns` factory argument, and passes `league=` to a prediction signature that does not accept it. Its response field names differ from the main predictor.

This is the **alternative API path**, not proof that the default football page always returns fixed predictions. Consolidate the adapter with the default predictor, add interface tests, and fail explicitly if models cannot run.

### 11. High for a shared deployment: state and HTML handling need repair

Saved prediction history is one JSON file with read/modify/write operations and no concurrency control. The deployment specifies two Gunicorn workers. Accumulator and chat histories are process-global singletons, with no per-user isolation: different workers can disagree, and users sharing a worker can share state. History deletion endpoints have no application-level ownership checks.

`app/templates/accuracy.html:198` inserts client-supplied stored fields into `innerHTML`; `app/templates/chat.html:212` does the same with user/AI text without sanitization. These are concrete HTML-injection paths. No exploit was sent or executed.

**Fix:** use transactional storage with per-user/session ownership, validated request schemas, and escaped text or sanitized Markdown. Restrict mutating/expensive endpoints as appropriate to the actual hosting setup. Add request timeouts consistently; the older football service has calls without them. Turn off debug mode for directly exposed development-server launches.

### 12. Medium: rest, competition strength and score forecasts need better definitions

The football rest calculation tracks last home appearance and last away appearance separately. The probe reports six days' rest when the team played away three days earlier. “Last five” venue-specific form is also not the same as overall last-five form. Promotion detection examines previous-season presence across all leagues, which can miss teams promoted from a covered lower division.

The Poisson model pools league averages and long-run team history without time decay or competition-specific calibration. Domestic ratings across countries are not automatically comparable for UCL fixtures. Current inference does not supply competition/round/neutral-venue information.

**Fix:** build a canonical team-match event stream across competitions, use all-venue rest and form plus separate home/away features, add opponent-strength adjustment and time decay, and evaluate transfer across leagues. Keep scoreline uncertainty visible: the most likely exact score is still usually a low-probability event.

### 13. Medium: several advanced features overstate their measurement

- The live-predictions route reads a top-level `confidence` field that the main predictor does not return, so its label defaults to LOW; it sets `logical_valid=True` without checking.
- Cache keys contain only home/away names, not fixture, competition, data version or prediction time.
- League-table prediction is requested without binding the main predictor, allowing generic 45/30/25 simulations. When a predictor is bound, it repeatedly uses its deterministic selected outcome instead of sampling its distribution. Fixed 2–0/0–2/1–1 scores further distort table uncertainty.
- Accumulator “combined confidence” multiplies submitted values without rejecting correlated same-match selections. Its `expected_value` is expected gross return, not net profit.
- AI explanations accept client context but do not establish verified form, injury, lineup or xG provenance. They should summarize the frozen prediction and cited data; fluent narrative is not additional predictive evidence.
- The service worker pre-caches `/static/css/style.css`, while the supplied stylesheet is `styles.css`; one failed `cache.addAll` asset can undermine offline initialization. Cached data needs an explicit stale/offline indicator.

### 14. Other sports need independent validation too

Basketball's current feature code explicitly excludes raw scores and box-score fields and maintains chronological rolling state, which is a useful foundation. However, its backtest rebuilds features on the test subset alone, resetting history at the split, and fills using test-set medians. The advanced trainer also selects features before validation folds. Old 87.89% claims are not a certification of the currently preferred advanced artifact.

Tennis still calculates whole-sample surface win rates and admits numeric match statistics through a denylist. `TotalSets` can reflect played sets when present, and raw per-match service statistics are not universally excluded. Its test-period features are rebuilt on the test period, so surface rates incorporate test outcomes. `backtest_tennis.py:119` treats the now-dictionary target return as a Series. The 95.57% claim is not reliable evidence for the current code.

`train_all_models.py` trains basketball and NFL from sample CSVs despite its general name. Keep demonstration artifacts clearly separate from validated production artifacts, and mark NFL unavailable for real forecasting until its real-data pipeline is verified.

### 15. Maintenance and runtime gaps

The README describes Python 3.8+, while the code uses newer syntax; it mentions a package.json and `.env.example` absent from the inspected root. The environment specification mixes application, notebooks and unrelated libraries, with both strict old pins and unpinned dependencies. The local venv is not portable. Requirements omit the optional xG dependency.

No CI workflow was found under `.github`; the `tests` directory contains scripts rather than a meaningful discovered regression suite. Root test scripts mostly require live services or print outputs. `.gitignore` broadly ignores `test_*.py`, making it easy to omit new tests. Several “complete/no leakage” documents contradict executable code, and claimed percentage-point improvements are not supported by controlled experiments.

**Fix:** one documented entry point, a reproducible application/ML environment, a separate development dependency group, an environment-variable example containing no secrets, meaningful offline tests and CI. Archive obsolete generated documentation and demo launchers after the canonical paths are established. Keep model artifacts with manifests and an explicit retrieval mechanism; current joblib files are real binary files locally, not LFS placeholders.

## UCL implementation plan

The existing `CL: 2001` mapping gives a starting point. Football-data.org lists Champions League coverage; its competition endpoint exposes historical seasons and its matches endpoint supports season filtering. Account-specific history entitlement remains unverified. Use the existing provider for fixture/result ingestion first, subject to the account's actual access. See [official coverage](https://www.football-data.org/coverage) and [competition API documentation](https://docs.football-data.org/general/v4/competition.html).

1. **Create canonical records.** Store provider and fixture IDs, canonical team IDs, competition, season, kickoff UTC, status, stage, round, leg/tie ID, neutral venue, separate regulation/extra-time/penalty scores, and fetch/update timestamps. Preserve raw responses for reproducibility.
2. **Backfill available completed UCL seasons.** Validate season completeness against returned fixtures; handle qualifiers separately from the main phase. Upsert corrections and postponements. Do not put UCL into the domestic CSV downloader by inventing a league code.
3. **Unify club identities and domestic context.** Link the same club across competitions. Bring domestic form, opponent-adjusted ratings, rest, travel and competition context to each UCL fixture. Avoid unsafe name-substring matches; unresolved teams should be visible.
4. **Add real xG only where verified.** The current Understat adapter will not provide UCL. Sample any candidate provider's UCL season and statistics responses, check historical depth, missingness and permitted access before adoption. API-Football lists UCL coverage, but league coverage alone does not prove complete xG coverage: [official coverage](https://www.api-football.com/coverage).
5. **Train and evaluate for transfer.** Compare a pooled model with competition features against a domestic-only baseline and a UCL-adjusted model. Reserve later UCL fixtures for evaluation. Distinguish regulation-time result/goal markets from qualification and extra-time outcomes.
6. **Expose coverage honestly.** Show last update, available team history, xG source/coverage and unsupported markets. Freeze predictions before kickoff and settle by fixture ID.

## Recommended sequence and acceptance criteria

| Phase | Work | Completion evidence |
|---|---|---|
| 1 — Correctness | Real targets; preserve missing labels; chronological shared feature builder; fixed probability contract; stable IDs | Future-mutation tests pass; historical dates respected; training/live vectors match; no synthetic fallback presented as prediction |
| 2 — Measurement | Chronological evaluation; fold-local tuning/selection; separate calibration; immutable prediction ledger | Reproducible metrics for the exact served model and dataset, by competition/market; no fitted/test overlap |
| 3 — Fresh data and UCL | Orchestrated upserts; current seasons; UCL history/fixtures; verified xG coverage | Completeness/freshness reports, no duplicate fixture IDs, correct regulation-time settlement, idempotent reruns |
| 4 — Measured model improvements | Time decay; opponent-adjusted xG/xGA; all-venue form/rest; league and cup context; score-distribution model | Each addition beats or usefully complements frozen baselines on untouched time periods |
| 5 — Application reliability | Transactional storage; state isolation; safe rendering; manifest-based loads; CI; clearer UI | Multi-worker consistency, correct ownership, deterministic model loading, offline regression suite and explicit stale-data behavior |

The first models to compare should be simple majority/league-prior baselines, Elo, a regularized Poisson score model, and a clean CatBoost model. Add a low-score dependence correction or other score model only after its held-out benefit is measured. A transformer or larger ensemble is a later experiment, not a substitute for valid data and evaluation.

For 1X2, report log loss, multiclass Brier score, accuracy, draw precision/recall and calibration. For goals/BTTS, report binary log loss, Brier score, class balance and calibration. Include sample counts and uncertainty by league and time window. If bookmaker prices are retained as a benchmark, use a timestamped, margin-adjusted probability baseline and distinguish models with odds inputs from those without. Do not claim a fixed accuracy improvement before these experiments.

The immediate next implementation should be Phase 1 followed by a trustworthy baseline evaluation. That will tell us which additional data and features actually improve the app.
