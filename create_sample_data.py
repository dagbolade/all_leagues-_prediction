"""
Create sample data for testing - so we can train models NOW

This generates realistic sample data for NBA and NFL
We'll replace with real scraped data later
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)


def create_nba_sample_data(num_games=1000):
    """Create realistic NBA sample data."""
    print("Creating NBA sample data...")

    teams = [
        'Los Angeles Lakers', 'Boston Celtics', 'Golden State Warriors',
        'Milwaukee Bucks', 'Phoenix Suns', 'Miami Heat', 'Denver Nuggets',
        'Philadelphia 76ers', 'Dallas Mavericks', 'Brooklyn Nets',
        'Memphis Grizzlies', 'Cleveland Cavaliers', 'New York Knicks',
        'Sacramento Kings', 'LA Clippers', 'New Orleans Pelicans'
    ]

    games = []
    start_date = datetime(2023, 10, 1)

    for i in range(num_games):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # Realistic NBA scores (avg ~110 points per team)
        home_score = int(np.random.normal(110, 12))
        away_score = int(np.random.normal(108, 12))  # Away teams score slightly less

        # Ensure scores are positive
        home_score = max(70, min(150, home_score))
        away_score = max(70, min(150, away_score))

        game_date = start_date + timedelta(days=i // 10)

        games.append({
            'Date': game_date,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'HomeScore': home_score,
            'AwayScore': away_score,
            'Result': 'H' if home_score > away_score else 'A',
            'League': 'NBA',
            'Season': '2023-2024'
        })

    df = pd.DataFrame(games)
    print(f"Created {len(df)} NBA games")
    return df


def create_nfl_sample_data(num_games=500):
    """Create realistic NFL sample data."""
    print("Creating NFL sample data...")

    teams = [
        'Kansas City Chiefs', 'Buffalo Bills', 'San Francisco 49ers',
        'Philadelphia Eagles', 'Dallas Cowboys', 'Miami Dolphins',
        'Baltimore Ravens', 'Detroit Lions', 'Cleveland Browns',
        'Green Bay Packers', 'Cincinnati Bengals', 'Jacksonville Jaguars',
        'Seattle Seahawks', 'Los Angeles Rams', 'Tampa Bay Buccaneers',
        'New England Patriots'
    ]

    games = []
    start_date = datetime(2023, 9, 1)
    week = 1

    for i in range(num_games):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # Realistic NFL scores (avg ~24 points per team)
        home_score = int(np.random.normal(24, 8))
        away_score = int(np.random.normal(21, 8))  # Away teams score less

        # Ensure scores are realistic
        home_score = max(0, min(60, home_score))
        away_score = max(0, min(60, away_score))

        game_date = start_date + timedelta(days=(i // 16) * 7)  # Games weekly

        games.append({
            'Date': game_date,
            'Week': (i // 16) + 1,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'HomeScore': home_score,
            'AwayScore': away_score,
            'Result': 'H' if home_score > away_score else ('A' if away_score > home_score else 'D'),
            'League': 'NFL',
            'Season': '2023'
        })

    df = pd.DataFrame(games)
    print(f"Created {len(df)} NFL games")
    return df


def main():
    """Create sample data for both sports."""
    print("\n" + "="*60)
    print("CREATING SAMPLE DATA FOR TESTING")
    print("="*60 + "\n")

    # Create directories
    Path("data/basketball/raw").mkdir(parents=True, exist_ok=True)
    Path("data/nfl/raw").mkdir(parents=True, exist_ok=True)

    # Create NBA data
    nba_df = create_nba_sample_data(1000)
    nba_file = Path("data/basketball/raw/nba_sample.csv")
    nba_df.to_csv(nba_file, index=False)
    print(f"Saved: {nba_file}\n")

    # Create NFL data
    nfl_df = create_nfl_sample_data(500)
    nfl_file = Path("data/nfl/raw/nfl_sample.csv")
    nfl_df.to_csv(nfl_file, index=False)
    print(f"Saved: {nfl_file}\n")

    print("="*60)
    print("SAMPLE DATA CREATED!")
    print("="*60)
    print("\nNBA Sample:")
    print(nba_df.head())
    print(f"\nNFL Sample:")
    print(nfl_df.head())
    print("\n" + "="*60)
    print("Ready to train models!")
    print("="*60)


if __name__ == "__main__":
    main()
