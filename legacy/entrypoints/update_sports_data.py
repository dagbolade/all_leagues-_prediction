"""
Sports Data Updater — Tennis & Basketball

Incremental update script: checks what the latest date is in each dataset
and only fetches what's missing. Safe to run weekly.

Usage:
    python update_sports_data.py              # update both
    python update_sports_data.py --tennis     # tennis only
    python update_sports_data.py --basketball # basketball only
"""

import argparse
import time
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
TENNIS_FILE  = Path("data/tennis/raw/tennis_real_data.csv")
BBALL_FILE   = Path("data/basketball/raw/nba_real_data.csv")

CURRENT_YEAR   = datetime.utcnow().year
CURRENT_SEASON = f"{CURRENT_YEAR - 1}-{str(CURRENT_YEAR)[-2:]}"  # e.g. "2025-26"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def latest_date(filepath: Path, date_col: str = "Date") -> str | None:
    """Return the most recent date string in a CSV, or None if file missing."""
    if not filepath.exists():
        return None
    df = pd.read_csv(filepath, usecols=[date_col], parse_dates=[date_col])
    return df[date_col].max().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Tennis — Jeff Sackmann GitHub (ATP + WTA)
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_ATP = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
GITHUB_WTA = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fetch_sackmann_csv(base_url: str, year: int, tour: str) -> pd.DataFrame:
    """Download one year's CSV from Sackmann's GitHub and normalise it."""
    prefix = "atp" if tour == "ATP" else "wta"
    url = f"{base_url}/{prefix}_matches_{year}.csv"
    try:
        df = pd.read_csv(url)
        df["Year"] = year
        df["Tour"] = tour
        return df
    except Exception as e:
        print(f"  [{tour} {year}] fetch failed: {e}")
        return pd.DataFrame()


def _normalise_sackmann(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Sackmann raw columns → our tennis schema."""
    import random
    random.seed(42)

    out = pd.DataFrame()
    out["Date"]       = pd.to_datetime(df["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    out["Tournament"] = df["tourney_name"]
    out["Surface"]    = df["surface"]
    out["Round"]      = df["round"]
    out["WinnerName"] = df["winner_name"]
    out["LoserName"]  = df["loser_name"]
    out["Tour"]       = df["Tour"]
    out["Year"]       = df["Year"]

    p1, p2, winner, r1, r2 = [], [], [], [], []
    for _, row in df.iterrows():
        if random.random() < 0.5:
            p1.append(row["winner_name"]); p2.append(row["loser_name"])
            winner.append("Player1")
            r1.append(row.get("winner_rank")); r2.append(row.get("loser_rank"))
        else:
            p1.append(row["loser_name"]); p2.append(row["winner_name"])
            winner.append("Player2")
            r1.append(row.get("loser_rank")); r2.append(row.get("winner_rank"))

    out["Player1"]     = p1
    out["Player2"]     = p2
    out["Winner"]      = winner
    out["Player1Rank"] = r1
    out["Player2Rank"] = r2
    out["Score"]       = df.get("score", None)

    return out.dropna(subset=["Date", "Player1", "Player2"])


# Sackmann GitHub only goes to 2024. For 2025+ use tennis-data.co.uk.
SACKMANN_MAX_YEAR   = 2024
TENNIS_DATA_UK_BASE = "http://www.tennis-data.co.uk"


def _fetch_tennis_data_uk(year: int) -> pd.DataFrame:
    """
    Download an Excel file from tennis-data.co.uk and normalise it.
    Format: http://www.tennis-data.co.uk/2026/2026.xlsx
    """
    url = f"{TENNIS_DATA_UK_BASE}/{year}/{year}.xlsx"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            print(f"  [tennis-data.co.uk {year}] HTTP {resp.status_code}")
            return pd.DataFrame()

        import io
        frames = []
        excel_bytes = io.BytesIO(resp.content)
        xl = pd.ExcelFile(excel_bytes)
        for sheet in xl.sheet_names:
            try:
                df = pd.read_excel(excel_bytes, sheet_name=sheet)
                df["Year"] = year
                df["Tour"] = "Mixed"
                frames.append(df)
            except Exception:
                pass
        xl.close()

        if not frames:
            return pd.DataFrame()

        raw = pd.concat(frames, ignore_index=True)

        # Normalise tennis-data.co.uk format → our schema
        import random
        random.seed(42)
        out = pd.DataFrame()
        out["Date"]       = pd.to_datetime(raw.get("Date"), errors="coerce")
        out["Tournament"] = raw.get("Tournament")
        out["Surface"]    = raw.get("Surface")
        out["Round"]      = raw.get("Round")
        out["WinnerName"] = raw.get("Winner")
        out["LoserName"]  = raw.get("Loser")
        out["Tour"]       = "Mixed"
        out["Year"]       = year

        p1, p2, winner, r1, r2 = [], [], [], [], []
        for _, row in raw.iterrows():
            w, l = row.get("Winner"), row.get("Loser")
            if pd.isna(w) or pd.isna(l):
                p1.append(None); p2.append(None); winner.append(None)
                r1.append(None); r2.append(None)
                continue
            if random.random() < 0.5:
                p1.append(w); p2.append(l); winner.append("Player1")
                r1.append(row.get("WRank")); r2.append(row.get("LRank"))
            else:
                p1.append(l); p2.append(w); winner.append("Player2")
                r1.append(row.get("LRank")); r2.append(row.get("WRank"))

        out["Player1"]     = p1
        out["Player2"]     = p2
        out["Winner"]      = winner
        out["Player1Rank"] = r1
        out["Player2Rank"] = r2
        out["Score"]       = raw.get("Score")

        out = out.dropna(subset=["Date", "Player1", "Player2"])
        print(f"  [tennis-data.co.uk {year}] {len(out):,} matches")
        return out

    except Exception as e:
        print(f"  [tennis-data.co.uk {year}] error: {e}")
        return pd.DataFrame()


def update_tennis(force: bool = False) -> int:
    """
    Incrementally update tennis data.

    Sources:
    - Sackmann GitHub   : historical data up to 2024
    - tennis-data.co.uk : 2025 and current year (updated throughout the season)

    Strategy:
    - Keep years < current year that are already in the file.
    - Always re-fetch the current year from tennis-data.co.uk (growing file).
    - On --force, re-download everything from 2020.

    Returns number of new rows added.
    """
    print("\n" + "=" * 60)
    print("TENNIS DATA UPDATE")
    print("=" * 60)

    existing = pd.DataFrame()
    if TENNIS_FILE.exists():
        existing = pd.read_csv(TENNIS_FILE, parse_dates=["Date"])
        print(f"  Existing: {len(existing):,} rows, latest: {existing['Date'].max().date()}")
    else:
        print("  No existing tennis data — full download.")
        force = True

    # Years to refresh
    if force:
        sackmann_years    = list(range(2020, SACKMANN_MAX_YEAR + 1))
        tennis_data_years = list(range(SACKMANN_MAX_YEAR + 1, CURRENT_YEAR + 1))
    else:
        sackmann_years    = []  # historical already in file
        tennis_data_years = [CURRENT_YEAR]
        # Also refresh previous year in January (year-end tournaments straddle)
        if datetime.utcnow().month == 1:
            tennis_data_years.append(CURRENT_YEAR - 1)

    new_frames = []

    # Sackmann GitHub (historical, only on force)
    for year in sackmann_years:
        for tour, base in [("ATP", GITHUB_ATP), ("WTA", GITHUB_WTA)]:
            print(f"  Fetching {tour} {year} (GitHub)...")
            raw = _fetch_sackmann_csv(base, year, tour)
            if not raw.empty:
                norm = _normalise_sackmann(raw)
                new_frames.append(norm)
                print(f"    {len(norm):,} matches")
            time.sleep(0.4)

    # tennis-data.co.uk (current year + recents)
    for year in tennis_data_years:
        print(f"  Fetching {year} (tennis-data.co.uk)...")
        df = _fetch_tennis_data_uk(year)
        if not df.empty:
            new_frames.append(df)

    if not new_frames:
        print("  Nothing fetched — no update made.")
        return 0

    new_data = pd.concat(new_frames, ignore_index=True)
    years_refreshed = sackmann_years + tennis_data_years

    if not existing.empty:
        existing["Date"] = pd.to_datetime(existing["Date"])
        keep = existing[~existing["Year"].isin(years_refreshed)]
        combined = pd.concat([keep, new_data], ignore_index=True)
    else:
        combined = new_data

    combined = combined.sort_values("Date").reset_index(drop=True)
    TENNIS_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(TENNIS_FILE, index=False)

    added = len(combined) - len(existing)
    print(f"\n  Done. Total: {len(combined):,} rows (+{added:,} new/refreshed)")
    print(f"  Latest match: {combined['Date'].max().date()}")
    return added


# ─────────────────────────────────────────────────────────────────────────────
# Basketball — NBA API (via nba_api package, falls back to raw HTTP)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from nba_api.stats.endpoints import leaguegamefinder as _lgf
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False

NBA_STATS_URL = "https://stats.nba.com/stats/leaguegamelog"
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}


def _fetch_nba_season(season: str) -> pd.DataFrame:
    """Fetch all games for one NBA season — tries nba_api first, falls back to raw HTTP."""

    # --- Method 1: nba_api package (most reliable) ---
    if NBA_API_AVAILABLE:
        try:
            gf = _lgf.LeagueGameFinder(
                season_nullable=season,
                league_id_nullable="00",
                season_type_nullable="Regular Season",
                timeout=60,
            )
            df = gf.get_data_frames()[0]
            if not df.empty:
                df["Season"] = season
                return df
        except Exception as e:
            print(f"  nba_api failed for {season}: {e} — trying raw HTTP...")

    # --- Method 2: raw HTTP request ---
    params = {
        "Season": season,
        "SeasonType": "Regular Season",
        "LeagueID": "00",
        "Direction": "ASC",
        "Sorter": "DATE",
    }
    try:
        session = requests.Session()
        session.headers.update(NBA_HEADERS)
        # Warm-up request (NBA API sometimes needs this)
        session.get("https://www.nba.com", timeout=10)
        time.sleep(1)
        resp = session.get(NBA_STATS_URL, params=params, timeout=60)
        if resp.status_code != 200:
            print(f"  API returned {resp.status_code} for {season}")
            return pd.DataFrame()
        data = resp.json()
        if "resultSets" not in data or not data["resultSets"]:
            return pd.DataFrame()
        cols = data["resultSets"][0]["headers"]
        rows = data["resultSets"][0]["rowSet"]
        df = pd.DataFrame(rows, columns=cols)
        df["Season"] = season
        return df
    except Exception as e:
        print(f"  Raw HTTP also failed for {season}: {e}")
        return pd.DataFrame()


def _build_game_rows(raw: pd.DataFrame, season: str) -> pd.DataFrame:
    """Convert per-team rows (2 per game) into one row per game."""
    raw["Season"] = season
    games = []

    for game_id in raw["GAME_ID"].unique():
        pair = raw[raw["GAME_ID"] == game_id]
        if len(pair) != 2:
            continue

        r1, r2 = pair.iloc[0], pair.iloc[1]
        home, away = (r2, r1) if "@" in r1["MATCHUP"] else (r1, r2)

        games.append({
            "Date":      pd.to_datetime(home["GAME_DATE"]),
            "HomeTeam":  home["TEAM_NAME"],
            "AwayTeam":  away["TEAM_NAME"],
            "HomeScore": home["PTS"],
            "AwayScore": away["PTS"],
            "HomeFG":    home["FG_PCT"],
            "AwayFG":    away["FG_PCT"],
            "HomeFG3":   home["FG3_PCT"],
            "AwayFG3":   away["FG3_PCT"],
            "HomeFT":    home["FT_PCT"],
            "AwayFT":    away["FT_PCT"],
            "HomeREB":   home["REB"],
            "AwayREB":   away["REB"],
            "HomeAST":   home["AST"],
            "AwayAST":   away["AST"],
            "HomeTO":    home["TOV"],
            "AwayTO":    away["TOV"],
            "Season":    season,
            "Winner":    "Home" if home["WL"] == "W" else "Away",
        })

    return pd.DataFrame(games)


def update_basketball(force: bool = False) -> int:
    """
    Incrementally update NBA data.

    Strategy:
    - Keep historical seasons intact.
    - Re-fetch the current season (in-progress) every run.
    - Optionally add playoffs (disabled by default to keep schema simple).

    Returns number of new rows added.
    """
    print("\n" + "=" * 60)
    print("BASKETBALL (NBA) DATA UPDATE")
    print("=" * 60)

    existing = pd.DataFrame()
    if BBALL_FILE.exists():
        existing = pd.read_csv(BBALL_FILE, parse_dates=["Date"])
        print(f"  Existing: {len(existing):,} rows, latest: {existing['Date'].max().date()}")
    else:
        print("  No existing NBA data — full download.")
        force = True

    # Always refresh current season; on force re-fetch all
    seasons_to_fetch = [CURRENT_SEASON]
    if force:
        seasons_to_fetch = [
            "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", CURRENT_SEASON
        ]
        # deduplicate
        seasons_to_fetch = list(dict.fromkeys(seasons_to_fetch))

    new_frames = []
    for season in seasons_to_fetch:
        print(f"  Fetching {season}...")
        raw = _fetch_nba_season(season)
        if raw.empty:
            print(f"    No data returned for {season}")
            time.sleep(2)
            continue
        games = _build_game_rows(raw, season)
        if not games.empty:
            new_frames.append(games)
            print(f"    {len(games):,} games")
        time.sleep(2)  # polite delay for NBA stats API

    if not new_frames:
        print("  Nothing fetched — no update made.")
        return 0

    new_data = pd.concat(new_frames, ignore_index=True)

    if not existing.empty:
        # Drop old rows for the re-fetched seasons and replace
        keep = existing[~existing["Season"].isin(seasons_to_fetch)]
        combined = pd.concat([keep, new_data], ignore_index=True)
    else:
        combined = new_data

    combined = combined.sort_values("Date").reset_index(drop=True)
    BBALL_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(BBALL_FILE, index=False)

    added = len(combined) - len(existing)
    print(f"\n  Done. Total: {len(combined):,} rows (+{added:,} new/refreshed)")
    print(f"  Latest game: {combined['Date'].max().date()}")
    return added


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Update tennis and basketball data")
    parser.add_argument("--tennis",     action="store_true", help="Update tennis only")
    parser.add_argument("--basketball", action="store_true", help="Update basketball only")
    parser.add_argument("--force",      action="store_true", help="Re-download all history")
    args = parser.parse_args()

    do_tennis = args.tennis or (not args.tennis and not args.basketball)
    do_bball  = args.basketball or (not args.tennis and not args.basketball)

    print(f"\n{'='*60}")
    print(f"SPORTS DATA UPDATER  —  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    results = {}

    if do_tennis:
        try:
            results["tennis"] = update_tennis(force=args.force)
        except Exception as e:
            print(f"\n[ERROR] Tennis update failed: {e}")
            results["tennis"] = -1

    if do_bball:
        try:
            results["basketball"] = update_basketball(force=args.force)
        except Exception as e:
            print(f"\n[ERROR] Basketball update failed: {e}")
            results["basketball"] = -1

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for sport, count in results.items():
        status = f"+{count} rows refreshed" if count >= 0 else "FAILED"
        print(f"  {sport.capitalize():12s}: {status}")
    print(f"{'='*60}\n")

    if any(v == -1 for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
