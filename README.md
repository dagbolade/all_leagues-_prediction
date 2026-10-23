# Matchday — sports intelligence

A rebuilt football, basketball and tennis analysis website. The active implementation is **`sportslab/`**. Football includes Champions League and 38 domestic/global competitions. The app uses SQLite, one chronological feature pipeline, versioned models and a private pre-match journal.

## Start on this computer

The isolated runtime, refreshed data and trained models are available locally.

```powershell
.\Start-Matchday.ps1
```

Open http://127.0.0.1:5000. The app has Overview, Match explorer, Prediction journal, Results, Model lab and Data coverage pages. It does not place bets.

## Refresh and retrain

```powershell
# Download available results, fixtures and observed xG; settle recorded forecasts
.\Refresh-Matchday.ps1
# Refresh, benchmark and train all three sport models
.\Refresh-Matchday.ps1 -Train
# Train without network access
.venv-revamp\Scripts\python.exe -m sportslab train
# Inspect coverage and provider outcomes
.venv-revamp\Scripts\python.exe -m sportslab status
```

Refresh is manual; no recurring task has been installed. **Refresh view** in the website reloads the database view, without scraping or retraining. An OS lock prevents overlapping CLI writers. Successful downloads remain available when another provider fails. Data coverage shows the latest outcome for each source plus recent attempt history. Partial provider failures are reported there; runtime or training failures return a nonzero exit code.

`FOOTBALL_DATA_API_KEY` (or the existing `API_KEY`) in `.env` enables football-data.org UCL history and verified fixtures. The current account returned seasons 2023 onward; the attempted 2022 season returned HTTP 403. No subscription was added. Raw responses are saved with URLs, hashes and retrieval timestamps; credentials are not logged.

## Recreate the environment

Python 3.12 is supported. The older `.venv` referenced a missing Python installation; the replacement is `.venv-revamp`.

```powershell
py -3.12 -m venv .venv-revamp
.venv-revamp\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv-revamp\Scripts\python.exe -m sportslab bootstrap
.venv-revamp\Scripts\python.exe -m sportslab pipeline
```

`requirements.txt` contains direct runtime dependencies; `requirements-lock.txt` records the tested Windows environment. Linux hosting additionally installs Gunicorn from `requirements.txt`. Original workbooks and basketball/tennis archives seed a new store. Generated data and model artifacts are ignored by Git and must be transferred or regenerated on another host.

## What the numbers mean

- Features use earlier UTC dates. Matches on the same date are processed as a batch, avoiding same-day leakage when kickoff times are missing.
- The same builder serves training and inference: head-to-head between the actual opponents, all-venue rest, scoring history, Elo, surface form and observed xG. Missing data remains missing.
- Outcome classes are explicit. Football goal totals, BTTS, clean sheets and outcome probabilities share one coherent score distribution. Predicted goals are model estimates, distinct from observed Understat xG.
- Training, calibration and test periods do not overlap. Model lab shows the untouched chronological **recipe benchmark**, with per-competition metrics, log loss, Brier score and a historical class-frequency baseline. The serving model is subsequently refit on newer results and calibrated on a recent held-back period. Its exact future accuracy is unknown.
- Historical accuracy does not establish profitability. Odds, lineups and injuries are not current model inputs. Half-time, cards, corners, NFL and unsupported legacy markets are not served.
- Both participants need five earlier appearances. Unknown or thinly covered participants receive an explicit unavailable response. League coverage does not mean complete coverage of every club or every field.

## Prediction journal

Only provider-verified future fixtures can be recorded. The server creates probabilities; the browser cannot supply them. Entries freeze the forecast and model/data versions. Duplicate saves retain the original record. Settlement uses exact identities, supports provider-confirmed postponements and records corrected final scores in an append-only event log. Custom scenarios cannot enter the journal.

The journal belongs to this browser session, using a signed cookie; it is not a cross-device account. Keep `data/sportslab/session.key` stable or configure `SECRET_KEY`. Clearing cookies loses access to an anonymous journal. Writes require CSRF tokens and have per-session rate limits. Provider text is rendered as text, not HTML. Old shared chat histories and accumulators are not imported into anonymous sessions.

## Storage and hosting

- `data/sportslab/sportslab.sqlite3`: matches, import reports, predictions and settlement events.
- `data/sportslab/raw/`: downloaded bodies and provenance metadata.
- `models/sportslab/<sport>/<version>/`: serving/benchmark artifacts and manifests containing evaluation, feature schema and checksums.
- `SPORTSLAB_DATA` and `SPORTSLAB_MODELS`: optional durable storage overrides, set before running the app or CLI.
- `app.run:app` and `api.unified_api:app`: the canonical Flask app; old blueprints are not registered.
- `/health`: liveness. `/ready`: checks for database records and all three model pointers.

Use Waitress locally, or `gunicorn app.run:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2` on Linux. Hosting needs durable data/model storage, a stable `SECRET_KEY` and `COOKIE_SECURE=1` behind HTTPS. Use SQLite's backup API for an active database, and back up the session key and model directories. Training writes a new version and switches the active pointer after its artifact and manifest are complete. No public deployment was performed.

## Tests and audit

```powershell
New-Item -ItemType Directory -Force .pytest-work
.venv-revamp\Scripts\python.exe -m pytest -q --basetemp=.pytest-work/run
```

Tests use an isolated store. They cover future-result invariance, same-day batching, training/inference parity, rest, real labels, coherent probabilities, aliases, missing half-time data, corrections, journal ownership/immutability, postponement, exact settlement and API validation/CSRF.

See `audit/PROJECT_AUDIT_2026-09-09.md` for the original audit and `audit/REVAMP_DELIVERY.md` for delivery evidence. Displaced entrypoints are retained in `legacy/entrypoints/`. Old `footy/`, route files, sport adapters and models remain as historical reference and are not used by the current application.

## Sources

[Football results](https://www.football-data.co.uk/data.php), [football-data.org](https://www.football-data.org/documentation/quickstart), [Understat](https://understat.com/), [tennis-data.co.uk](http://www.tennis-data.co.uk/alldata.php), [ESPN](https://www.espn.com/nba/scoreboard), [EuroLeague official API](https://api-live.euroleague.net/swagger/v2/swagger.json). The coverage page identifies imported results and freshness; provider availability can change.

## Railway deployment bundle

`deployment/` contains a compressed public-match seed and the active trained models. It deliberately excludes local journals, session keys, credentials and raw response archives. Railway runs `python -m sportslab.deploy` before Gunicorn and checks `/ready`. New instances are seeded; existing instances merge newer bundled match revisions while preserving newer live records and private journals. Each deployment activates the bundled model versions.

Attach a Railway volume to retain journals and refreshed data across deployments. The app automatically uses `RAILWAY_VOLUME_MOUNT_PATH/sportslab` when supplied, unless `SPORTSLAB_DATA` is explicitly set. Without a volume, Railway filesystem data is ephemeral. Set a stable `SECRET_KEY` and `COOKIE_SECURE=1` for the HTTPS site. Existing football API credentials remain Railway environment variables.

### Refresh verification — 23 October 2026

The data was refreshed and all three models retrained. Provider changes required published-link discovery for tennis and daily NBA feeds (with preseason games excluded). Run `python -m sportslab.package` after a validated refresh/training run to regenerate the public Railway bundle, including source update timestamps. See `audit/FRESHNESS_2026-10-23.json` for exact coverage, model dates and fixture checks. This report does not by itself confirm the live Railway installation is updated.
