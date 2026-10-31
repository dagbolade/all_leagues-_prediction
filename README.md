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
## Matchboard forecasts and reported live scores

The overview now loads pre-match probabilities for the visible upcoming fixtures (up to 24 per request). Each card includes outcome probabilities, the most likely football scoreline, data limitations and calculation/model timestamps. These public forecast summaries are cached by fixture, model version and data version; they do not create private journal records. No new forecast is calculated after kickoff.

The **Live / today** view (also `/live-predictions`) connects football-data.org for today's covered football competitions. Set `FOOTBALL_DATA_API_KEY` in Railway variables; local development also reads `.env`. Credentials remain server-side. The feed is fetched on demand, at most once per minute per shared SQLite database, across visitors and Gunicorn workers. Browser refresh pauses when the page is hidden. A persistent Railway volume retains public pre-match references across releases.

Provider scores may be delayed; a fresh HTTP fetch is not proof of a fresh match observation. The UI displays both fetch time and the provider's match update time. Missing scores and clocks remain unavailable, failures retain the last successful observation with a warning, and extra-time phases are labelled. Scoreboard observations are separate from training results and private-journal settlement.

This is **not an in-play probability model**. Provider responses tested on 24 October 2026 omitted the match minute, and the current models were evaluated only pre-match. In-play forecasts require a reliable clock/event feed and a separately trained, calibrated, temporally evaluated model. When an exact fixture has a cached forecast generated before kickoff, the live view may show it as a **saved pre-match reference**, never as an updated in-play probability. Basketball and tennis live feeds are not connected.

Provider references: [score semantics](https://docs.football-data.org/general/v4/overtime.html), [match statuses](https://docs.football-data.org/general/v4/match.html), [coverage and delay plans](https://www.football-data.org/pricing).


## Prospective tracking and player data

`python -m sportslab track` records all stored fixtures inside the 24-hour or
1-hour lead-time window (15-minute tolerance). The first observation, including
a withheld forecast, is immutable for that fixture, kickoff and lead time.
Predictions with fewer than five appearances, 90-day-old participant history or
imprecise kickoff times are withheld. These thresholds apply to the tracking
ledger; they are not a blanket freshness guarantee for every source.
Result corrections append audit events; cancellations, awards and kickoff
changes void the original forecast. Each lead time and model version is reported
separately in Model lab. No historical predictions are fabricated or backfilled.

For ongoing collection run `python -m sportslab.worker` alongside the web process,
using the **same persistent SPORTSLAB_DATA directory**. It refreshes the connected
football fixture/result feed and captures/settles forecasts every ten minutes.
It does not retrain models or refresh every historical sport feed. Keep the
normal full refresh pipeline scheduled separately. The worker is not started by
this revision's Railway start command; Model lab flags missing/stale runs. Do not
run a separate Railway service with an isolated SQLite volume and expect the web
service to see it. The web process and worker must share the same database.

The optional player adapter uses the API-Sports direct API-Football service:
set `API_FOOTBALL_KEY` server-side, then run
`python -m sportslab player-import --provider-fixture <API-Football fixture ID>`.
This is a different ID namespace from football-data.org. The adapter imports a
completed regulation-time fixture's player appearances and original response,
retains null statistics, and replaces corrected imports transactionally. It
makes two provider calls per fixture; it does not launch a bulk paid backfill.
Reference: https://www.api-football.com/documentation_v3

No provider account or player history is bundled. Player market probabilities
remain unavailable until adequate historical coverage, reviewed fixture/team
mapping, pre-match lineup/expected-minutes inputs and chronological validation
are implemented. The current adapter does not fetch future lineups or estimate
player probabilities. Extra-time fixtures are excluded until regulation-only
statistics can be verified. Bookmaker definitions such as shots including
woodwork need their own matching data and settlement rules.


### Public player histories without an API

`scripts/collect_player_pages.mjs` exports `collectPlayer(tab, fs, source, output)`
for the Codex browser REPL. Supply a bound browser tab, Node `fs/promises`, an
observed public Understat player URL, and an absolute workspace output path.
It reads the rendered match-history table and follows normal page controls;
it makes no direct requests to data API endpoints and needs no API key.
Dynamic pages require the browser; this is an assisted collector, not an
unattended Railway scraping job. Rate-limit repeated visits and stop if the
source blocks access or changes its table structure.

Import saved histories with:
`python -m sportslab player-pages --input data/player-pages`
The initial 27 October 2026 collection contains 1,961 unique appearances across
ten selected players (full displayed histories, not all players or leagues).
Files preserve source URLs, extraction time, headers and page sequence.
`/api/players/public` and Model lab display the last ten appearances per player.
Total shots, goals, assists, minutes, xG and xA are available. Shots on target,
cards, team-at-appearance and UCL coverage are not inferred. Namespaces are
separate from API-Football. These statistics do not enter the existing team
models or generate betting probabilities. Current-scorer selection is biased;
a representative roster sample and chronological evaluation remain necessary
before training or publishing player probabilities. Data is stored in the local
SQLite database; these snapshots are not yet included in the Railway bundle.

Football fixture freshness: the web service checks the rolling provider window when the football fixture list is requested, at most once per ten minutes across workers. A SQLite lease prevents duplicate requests; failed checks retain saved data and retry after one minute. The UI displays the last successful check or an error, and polls while refreshing. This requires the existing FOOTBALL_DATA_API_KEY (or API_KEY) on the server. It does not refresh player history or retrain models. The Today button selects the current UTC date and clears other fixture filters.
