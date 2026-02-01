"""
NBA Data Scraper using nba_api - Gets REAL data from NBA.com
2020-2021 through 2024-2025 seasons
"""

from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
from pathlib import Path
import time

def scrape_nba_games(seasons):
    """
    Scrape NBA games using official NBA API.

    Args:
        seasons: List of season strings like ['2020-21', '2021-22', ...]
    """
    print("=" * 80)
    print("NBA DATA SCRAPER - Using Official NBA API")
    print("=" * 80)

    all_games = []

    for season in seasons:
        print(f"\nFetching {season} season...")

        try:
            # Use LeagueGameFinder to get all games
            gamefinder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                league_id_nullable='00',  # NBA
                season_type_nullable='Regular Season'
            )

            games = gamefinder.get_data_frames()[0]

            if not games.empty:
                games['Season'] = season
                all_games.append(games)
                print(f"  Found {len(games)} game records")

            time.sleep(1)  # Rate limit

        except Exception as e:
            print(f"  Error: {e}")
            continue

    if all_games:
        combined = pd.concat(all_games, ignore_index=True)

        # Process to get one row per game (API returns 2 rows per game - one for each team)
        print("\n[Processing] Converting to game format...")

        # Group by GAME_ID and take home/away teams
        games_list = []

        for game_id in combined['GAME_ID'].unique():
            game_rows = combined[combined['GAME_ID'] == game_id]

            if len(game_rows) == 2:
                # One row is home, one is away
                row1 = game_rows.iloc[0]
                row2 = game_rows.iloc[1]

                # Determine home/away based on MATCHUP field
                if '@' in row1['MATCHUP']:
                    away = row1
                    home = row2
                else:
                    home = row1
                    away = row2

                game = {
                    'Date': pd.to_datetime(home['GAME_DATE']),
                    'HomeTeam': home['TEAM_NAME'],
                    'AwayTeam': away['TEAM_NAME'],
                    'HomeScore': home['PTS'],
                    'AwayScore': away['PTS'],
                    'HomeFG': home['FG_PCT'],
                    'AwayFG': away['FG_PCT'],
                    'HomeFG3': home['FG3_PCT'],
                    'AwayFG3': away['FG3_PCT'],
                    'HomeFT': home['FT_PCT'],
                    'AwayFT': away['FT_PCT'],
                    'HomeREB': home['REB'],
                    'AwayREB': away['REB'],
                    'HomeAST': home['AST'],
                    'AwayAST': away['AST'],
                    'HomeTO': home['TOV'],
                    'AwayTO': away['TOV'],
                    'Season': home['Season'],
                    'Winner': 'Home' if home['WL'] == 'W' else 'Away'
                }

                games_list.append(game)

        games_df = pd.DataFrame(games_list)
        games_df = games_df.sort_values('Date').reset_index(drop=True)

        print(f"\n[OK] Processed {len(games_df)} games")

        return games_df

    else:
        raise ValueError("No NBA data retrieved!")


def main():
    """Scrape NBA data from 2020-21 to 2024-25."""

    # Seasons to scrape
    seasons = [
        '2020-21',
        '2021-22',
        '2022-23',
        '2023-24',
        '2024-25'  # Current season (partial)
    ]

    # Scrape data
    nba_data = scrape_nba_games(seasons)

    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)
    print(f"Total games: {len(nba_data)}")
    print(f"Date range: {nba_data['Date'].min()} to {nba_data['Date'].max()}")
    print(f"Seasons: {nba_data['Season'].nunique()}")
    print("=" * 80)

    # Save
    output_dir = Path("data/basketball/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "nba_real_data.csv"
    nba_data.to_csv(output_file, index=False)

    print(f"\n[OK] Saved to {output_file}")
    print(f"[OK] Ready for training with {len(nba_data)} REAL NBA games!")


if __name__ == '__main__':
    main()
