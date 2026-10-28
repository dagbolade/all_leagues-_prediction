# Public player coverage

Snapshot observed 27 October 2026. Collected from rendered Understat league, team and match pages without API calls or credentials.

## Scope and validation

All six available 2026/27 league inventories: EPL, La Liga, Bundesliga, Serie A, Ligue 1 and RFPL. 112 teams; 2,613 distinct players (2,634 league-player entries); 490 completed matches discovered; 489 validated rosters; 15,318 current-season appearances. Together with previously imported career histories there are 17,205 unique player-match records. Older history is not complete for every player.

Match 30804 is quarantined: repeated player rows have conflicting statistics. Do not deduplicate it arbitrarily. The coverage denominator deliberately remains 490. Every inventory player has at least one valid appearance elsewhere.

Available: minutes, starts/substitute status, shots, goals, assists, key passes, xG, xA and reported yellow/red timeline events. Card events are not bookmaker settlements. Shots on target and UCL player data are absent. Player forecast probabilities remain disabled pending fixture mapping, expected minutes and separate chronological validation.

## Refresh and import

Use the Codex browser runtime with a bound public-page tab. `scripts/collect_league_inventory.mjs` supplies DOM readers for league player pages and completed team match links; visit every player-table pagination page and retain its page number and last-page flag. Save league snapshots as `<league>-roster.json`, and deduplicated match links plus team reports as `match-index.json` under `data/public-coverage`.

`scripts/collect_match_rosters.mjs` exports `collectBatch(tabs, fs, outRoot, matches, cursor, budgetMs)`. It navigates public match pages, reads both rendered team tables and card timelines, and saves source snapshots under `matches/`. Resume from the returned cursor; retry returned failures. This is a browser-assisted refresh, not a scheduled production scraper.

Import with:

```powershell
.venv-revamp/Scripts/python.exe -m sportslab player-rosters --input data/public-coverage
```

The importer validates identifiers, dates, columns, unique players and exactly eleven starters per team. Invalid matches are reported and excluded; a nonzero exit code signals exclusions. Newer snapshots replace complete rosters. Older career imports cannot overwrite enriched roster records.

The local endpoint `/api/players/public` accepts `league`, `q`, `offset`, `limit` (maximum 50). Model lab displays inventory coverage, searchable player histories and pagination. The public-only deployment/players.json.gz bundle is imported by sportslab.deploy on startup. Repeat imports are idempotent and preserve newer player records, roster corrections and inventories. No private journal, session, credential or tracking tables are bundled. Changes have not been pushed to Railway.

Audit: `audit/player-coverage-2026-10-27.json`. Preview verification: player search, expanded Palmer history, API pagination and 50 passing sportslab tests, including a clean database seed, repeat import, newer-record preservation and corrected-roster removal protection.
