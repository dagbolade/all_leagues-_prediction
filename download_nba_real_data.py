"""
Download REAL NBA Data

Sources:
1. NBA.com Stats API (official NBA data)
2. basketball-reference.com
3. Kaggle datasets (as backup)

Gets REAL historical NBA game data like the football data approach.
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timedelta
import time

def download_nba_seasons_csv():
    """
    Download NBA game data from multiple sources.

    Kaggle has comprehensive NBA datasets with real historical data.
    """
    print("=" * 80)
    print("DOWNLOADING REAL NBA DATA")
    print("=" * 80)

    # Try to download from basketball-reference or use NBA stats API
    # For now, let's use a known good source

    # basketball-reference has game logs we can download
    # But the best source is actually downloading CSVs from Kaggle or similar

    print("\n[INFO] For REAL NBA data, download from:")
    print("1. Kaggle: 'wyattowalsh/basketball' dataset")
    print("   https://www.kaggle.com/datasets/wyattowalsh/basketball")
    print("2. basketball-reference.com - Schedule & Results pages")
    print("3. NBA.com Stats API")

    print("\n[ACTION REQUIRED]")
    print("Please download NBA game data CSV and place in:")
    print("  data/basketball/raw/nba_games_[season].csv")

    print("\nFor now, using NBA Stats API to get some real data...")

    # Use NBA Stats API (undocumented but public)
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.nba.com/',
    }

    all_games = []

    # Get last 3 seasons
    for year in [2022, 2023, 2024]:
        season = f"{year}-{str(year+1)[-2:]}"
        print(f"\nFetching {season} season...")

        # NBA Stats API endpoint for game log
        url = f'https://stats.nba.com/stats/leaguegamelog'
        params = {
            'Season': season,
            'SeasonType': 'Regular Season',
            'LeagueID': '00',
            'Direction': 'ASC',
            'Sorter': 'DATE'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if 'resultSets' in data and len(data['resultSets']) > 0:
                    headers_list = data['resultSets'][0]['headers']
                    rows = data['resultSets'][0]['rowSet']

                    df = pd.DataFrame(rows, columns=headers_list)
                    df['Season'] = season
                    all_games.append(df)

                    print(f"  Got {len(df)} game records")
                else:
                    print(f"  No data found for {season}")
            else:
                print(f"  API returned {response.status_code}")

            time.sleep(2)  # Be polite to NBA servers

        except Exception as e:
            print(f"  Error: {e}")

    if all_games:
        combined = pd.concat(all_games, ignore_index=True)

        # Save
        output_dir = Path("data/basketball/raw")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "nba_real_api_data.csv"
        combined.to_csv(output_file, index=False)

        print(f"\n[OK] Saved {len(combined)} records to {output_file}")
        return combined
    else:
        print("\n[ERROR] Could not download NBA data from API")
        print("Please download manually from basketball-reference.com or Kaggle")
        return None


if __name__ == '__main__':
    download_nba_seasons_csv()
