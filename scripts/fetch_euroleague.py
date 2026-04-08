"""
Fetch EuroLeague game results from basketball-reference.com
Outputs: data/basketball/raw/euroleague_data.csv  (same schema as nba_real_data.csv)

Seasons scraped: 2020-21 through 2024-25
Run: python scripts/fetch_euroleague.py
"""

import time
import re
import sys
from pathlib import Path
from io import StringIO

import pandas as pd
import cloudscraper

ROOT = Path(__file__).parent.parent
OUT_DIR  = ROOT / "data/basketball/raw"
OUT_FILE = OUT_DIR / "euroleague_data.csv"

BASE = "https://www.basketball-reference.com"

# Seasons: bbref uses the END year, e.g. 2025 = 2024-25 season
SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]

# ── Team name normalisation ────────────────────────────────────────────────────
# bbref uses long sponsor-heavy names; we strip to the club core
_NAME_MAP = {
    "Panathinaikos AKTOR":            "Panathinaikos",
    "Panathinaikos BC":                "Panathinaikos",
    "ALBA Berlin":                     "ALBA Berlin",
    "Real Madrid":                     "Real Madrid",
    "Bayern München":                  "Bayern Munich",
    "FC Bayern Munich":                "Bayern Munich",
    "Bayern Munich":                   "Bayern Munich",
    "LDLC ASVEL":                      "ASVEL",
    "ASVEL":                           "ASVEL",
    "Maccabi Playtika Tel Aviv":       "Maccabi Tel Aviv",
    "Maccabi Tel Aviv":                "Maccabi Tel Aviv",
    "EA7 Emporio Armani Milano":       "Olimpia Milano",
    "AX Armani Exchange Milan":        "Olimpia Milano",
    "Olimpia Milano":                  "Olimpia Milano",
    "AS Monaco":                       "Monaco",
    "Monaco":                          "Monaco",
    "Partizan Mozzart Bet":            "Partizan",
    "Partizan":                        "Partizan",
    "Baskonia":                        "Baskonia",
    "Td Systems Baskonia":             "Baskonia",
    "Saski Baskonia":                  "Baskonia",
    "Barcelona":                       "Barcelona",
    "FC Barcelona":                    "Barcelona",
    "Žalgiris":                        "Zalgiris",
    "Zalgiris Kaunas":                 "Zalgiris",
    "Zalgiris":                        "Zalgiris",
    "Crvena zvezda Meridianbet":       "Red Star Belgrade",
    "Crvena Zvezda":                   "Red Star Belgrade",
    "Red Star Belgrade":               "Red Star Belgrade",
    "Paris Basketball":                "Paris Basketball",
    "Olympiacos":                      "Olympiacos",
    "Olympiakos Piraeus":              "Olympiacos",
    "Fenerbahçe Beko":                 "Fenerbahce",
    "Fenerbahce Beko":                 "Fenerbahce",
    "Fenerbahce":                      "Fenerbahce",
    "Anadolu Efes":                    "Efes",
    "Anadolu Efes SK":                 "Efes",
    "Virtus Segafredo Bologna":        "Virtus Bologna",
    "Virtus Bologna":                  "Virtus Bologna",
    "Valencia Basket":                 "Valencia",
    "Valencia":                        "Valencia",
    "Villeurbanne":                    "ASVEL",
    "Buducnost VOLI":                  "Buducnost",
    "CSKA Moscow":                     "CSKA Moscow",
    "Khimki":                          "Khimki",
    "Zenit St Petersburg":             "Zenit",
    "Zenit Saint Petersburg":         "Zenit",
    "Unics Kazan":                     "UNICS Kazan",
    "UNICS Kazan":                     "UNICS Kazan",
    "Kirolbet Baskonia":               "Baskonia",
    "Bitci Baskonia":                  "Baskonia",
    "Vitoria":                         "Baskonia",
    "Vitoria-Gasteiz":                 "Baskonia",
    "Hapoel Bank Yahav Jerusalem":     "Hapoel Jerusalem",
    "Hapoel Jerusalem":                "Hapoel Jerusalem",
    "Cazoo Baskonia":                  "Baskonia",
    "Zalgiris Kaunas":                 "Zalgiris",
    "Germani Brescia":                 "Brescia",
    "EA7 Milano":                      "Olimpia Milano",
    "Euroleague Basketball":           None,  # header row
}

def clean_name(name):
    if pd.isna(name):
        return None
    name = str(name).strip()
    if name in _NAME_MAP:
        return _NAME_MAP[name]
    # partial match
    for k, v in _NAME_MAP.items():
        if k.lower() in name.lower() or name.lower() in k.lower():
            return v
    return name  # return as-is if not found


def fetch_season(scraper, year):
    """Fetch results for one season (year = end year, e.g. 2025 = 2024-25)."""
    season_label = f"{year-1}-{str(year)[-2:]}"
    url = f"{BASE}/international/euroleague/{year}-schedule.html"
    print(f"  Fetching {season_label} -> {url}")

    try:
        r = scraper.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  [SKIP] HTTP {r.status_code}")
            return pd.DataFrame()
        tables = pd.read_html(StringIO(r.text))
    except Exception as e:
        print(f"  [ERROR] {e}")
        return pd.DataFrame()

    rows = []
    for df in tables:
        if 'Date' not in df.columns or 'PTS' not in df.columns:
            continue
        df = df.copy()
        # Rename columns: Team=home, PTS=home_pts, Opp=away, PTS.1=away_pts
        df.columns = [str(c) for c in df.columns]
        df = df.rename(columns={
            'Team':  'raw_home',
            'PTS':   'HomeScore',
            'Opp':   'raw_away',
            'PTS.1': 'AwayScore',
        })
        # Drop header rows, future games (no score)
        df = df[df['Date'].notna() & ~df['Date'].str.startswith('Date', na=True)]
        df = df[df['HomeScore'].notna()]
        df['HomeScore'] = pd.to_numeric(df['HomeScore'], errors='coerce')
        df['AwayScore'] = pd.to_numeric(df['AwayScore'], errors='coerce')
        df = df.dropna(subset=['HomeScore', 'AwayScore'])

        # Parse date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        df['HomeTeam'] = df['raw_home'].apply(clean_name)
        df['AwayTeam'] = df['raw_away'].apply(clean_name)
        df = df[df['HomeTeam'].notna() & df['AwayTeam'].notna()]
        df = df[df['HomeTeam'] != df['AwayTeam']]

        df['Season'] = season_label
        rows.append(df[['Date', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore', 'Season']])

    if not rows:
        return pd.DataFrame()

    season_df = pd.concat(rows).drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'])
    print(f"  [OK] {len(season_df)} games for {season_label}")
    return season_df


def fetch_team_stats(scraper, year):
    """
    Fetch per-team season averages (FG%, 3P%, FT%, REB, AST, TO) from the season page.
    These are used as proxies for box-score features across all games that season.
    """
    url = f"{BASE}/international/euroleague/{year}.html"
    try:
        r = scraper.get(url, timeout=30)
        tables = pd.read_html(StringIO(r.text))
    except Exception as e:
        print(f"  [WARN] Could not fetch team stats for {year}: {e}")
        return {}

    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        # Look for table with FG% column
        if 'fg%' in cols or 'fg' in cols:
            t.columns = [str(c) for c in t.columns]
            stats = {}
            for _, row in t.iterrows():
                team = clean_name(str(row.get('Team', row.get('Squad', ''))))
                if not team or team == 'None':
                    continue
                s = {}
                for src, dst in [('FG%','FG'), ('3P%','FG3'), ('FT%','FT'),
                                  ('TRB','REB'), ('AST','AST'), ('TOV','TO')]:
                    if src in row.index:
                        try: s[dst] = float(row[src])
                        except: pass
                if s:
                    stats[team] = s
            if stats:
                print(f"  [Stats] {len(stats)} teams' averages loaded for {year}")
                return stats
    return {}


def main():
    print("=" * 70)
    print("EuroLeague Scraper — basketball-reference.com")
    print("=" * 70)

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        delay=5
    )

    all_games = []
    all_team_stats = {}   # { season: { team: {FG, FG3, FT, REB, AST, TO} } }

    for year in SEASONS:
        season_label = f"{year-1}-{str(year)[-2:]}"
        print(f"\n[Season {season_label}]")
        df = fetch_season(scraper, year)
        if len(df):
            all_games.append(df)

        # Fetch team season averages
        stats = fetch_team_stats(scraper, year)
        if stats:
            all_team_stats[season_label] = stats

        time.sleep(4)  # polite crawl delay

    if not all_games:
        print("\n[ERROR] No games fetched. Exiting.")
        sys.exit(1)

    combined = pd.concat(all_games, ignore_index=True)
    combined = combined.sort_values('Date').reset_index(drop=True)

    # ── Add box-score proxy columns from season averages ──────────────────────
    # For each game, look up the season's avg stats for each team
    for col in ['HomeFG', 'AwayFG', 'HomeFG3', 'AwayFG3',
                'HomeFT', 'AwayFT', 'HomeREB', 'AwayREB',
                'HomeAST', 'AwayAST', 'HomeTO', 'AwayTO']:
        combined[col] = float('nan')

    for i, row in combined.iterrows():
        season = row['Season']
        stats  = all_team_stats.get(season, {})
        h_stats = stats.get(row['HomeTeam'], {})
        a_stats = stats.get(row['AwayTeam'], {})
        for k, col in [('FG','HomeFG'),('FG3','HomeFG3'),('FT','HomeFT'),
                       ('REB','HomeREB'),('AST','HomeAST'),('TO','HomeTO')]:
            if k in h_stats:
                combined.at[i, col] = h_stats[k]
        for k, col in [('FG','AwayFG'),('FG3','AwayFG3'),('FT','AwayFT'),
                       ('REB','AwayREB'),('AST','AwayAST'),('TO','AwayTO')]:
            if k in a_stats:
                combined.at[i, col] = a_stats[k]

    # ── Winner column ─────────────────────────────────────────────────────────
    combined['Winner'] = combined.apply(
        lambda r: 'Home' if r['HomeScore'] > r['AwayScore'] else 'Away', axis=1
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_FILE, index=False)

    print(f"\n{'='*70}")
    print(f"[DONE] {len(combined)} games saved -> {OUT_FILE}")
    print(f"Seasons: {sorted(combined['Season'].unique())}")
    print(f"Teams:   {sorted(combined['HomeTeam'].unique())}")
    print(f"Date range: {combined['Date'].min().date()} -> {combined['Date'].max().date()}")

    # Quick sanity check
    print(f"\nSample output:")
    print(combined.head(5)[['Date','HomeTeam','AwayTeam','HomeScore','AwayScore','Season']].to_string())


if __name__ == "__main__":
    main()
