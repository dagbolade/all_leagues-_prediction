"""
Real Basketball (NBA) Data Scraper - 2020 to 2026

Downloads actual NBA game data from basketball-reference.com
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from bs4 import BeautifulSoup
import re

class NBADataScraper:
    """Scraper for real NBA data from basketball-reference.com"""

    def __init__(self):
        self.base_url = 'https://www.basketball-reference.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_season_schedule(self, season_year: int) -> pd.DataFrame:
        """
        Scrape full season schedule and results.

        Args:
            season_year: End year of season (e.g., 2024 for 2023-24 season)
        """
        print(f"  Scraping NBA {season_year-1}-{season_year} season...")

        # basketball-reference uses months for schedule
        months = ['october', 'november', 'december', 'january', 'february',
                 'march', 'april', 'may', 'june']

        all_games = []

        for month in months:
            url = f"{self.base_url}/leagues/NBA_{season_year}_games-{month}.html"

            try:
                response = requests.get(url, headers=self.headers, timeout=30)

                if response.status_code == 200:
                    # Parse with pandas
                    tables = pd.read_html(response.content)

                    if tables:
                        df = tables[0]

                        # Clean data
                        if 'Date' in df.columns:
                            # Remove header rows that repeat
                            df = df[df['Date'] != 'Date']

                            # Add season info
                            df['Season'] = f"{season_year-1}-{season_year}"
                            df['Month'] = month.capitalize()

                            all_games.append(df)
                            print(f"    {month}: {len(df)} games")

                time.sleep(1)  # Be respectful to server

            except Exception as e:
                print(f"    {month}: {e}")
                continue

        if all_games:
            combined = pd.concat(all_games, ignore_index=True)
            print(f"    Total: {len(combined)} games")
            return combined
        else:
            print(f"    No data found for {season_year}")
            return pd.DataFrame()

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize scraped data to standard format."""
        print("\n[Normalize] Processing NBA data...")

        normalized = pd.DataFrame()

        # Date
        if 'Date' in df.columns:
            normalized['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Teams - basketball-reference format
        if 'Visitor/Neutral' in df.columns:
            normalized['AwayTeam'] = df['Visitor/Neutral']
        elif 'Away' in df.columns:
            normalized['AwayTeam'] = df['Away']

        if 'Home/Neutral' in df.columns:
            normalized['HomeTeam'] = df['Home/Neutral']
        elif 'Home' in df.columns:
            normalized['HomeTeam'] = df['Home']

        # Scores
        if 'PTS' in df.columns:
            normalized['AwayScore'] = pd.to_numeric(df['PTS'], errors='coerce')
        if 'PTS.1' in df.columns:
            normalized['HomeScore'] = pd.to_numeric(df['PTS.1'], errors='coerce')

        # Overtime
        if 'OT' in df.columns or 'Notes' in df.columns:
            ot_col = 'OT' if 'OT' in df.columns else 'Notes'
            normalized['Overtime'] = df[ot_col].notna()

        # Attendance
        if 'Attend.' in df.columns:
            normalized['Attendance'] = pd.to_numeric(
                df['Attend.'].str.replace(',', ''),
                errors='coerce'
            )

        # Season and Month
        if 'Season' in df.columns:
            normalized['Season'] = df['Season']
        if 'Month' in df.columns:
            normalized['Month'] = df['Month']

        # Calculate winner
        if 'HomeScore' in normalized.columns and 'AwayScore' in normalized.columns:
            normalized['Winner'] = normalized.apply(
                lambda row: 'Home' if row['HomeScore'] > row['AwayScore']
                else 'Away' if row['AwayScore'] > row['HomeScore']
                else 'Tie',
                axis=1
            )

        # Remove rows with missing critical data
        normalized = normalized.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])

        print(f"[OK] Normalized {len(normalized)} games")

        return normalized

    def scrape_all_seasons(self, start_year: int = 2020, end_year: int = 2025) -> pd.DataFrame:
        """
        Scrape multiple NBA seasons.

        Args:
            start_year: First season start year (e.g., 2020 for 2020-21)
            end_year: Last season end year (e.g., 2025 for 2024-25)
        """
        print("=" * 80)
        print("NBA DATA SCRAPER - BASKETBALL-REFERENCE.COM")
        print("=" * 80)

        all_seasons = []

        # Season years (end year of season)
        for year in range(start_year + 1, end_year + 1):
            season_data = self.scrape_season_schedule(year)

            if not season_data.empty:
                all_seasons.append(season_data)

            time.sleep(2)  # Be respectful between seasons

        if all_seasons:
            combined = pd.concat(all_seasons, ignore_index=True)
            normalized = self.normalize_data(combined)

            print("\n" + "=" * 80)
            print("SCRAPING COMPLETE")
            print("=" * 80)
            print(f"Total games: {len(normalized)}")
            print(f"Date range: {normalized['Date'].min()} to {normalized['Date'].max()}")
            print(f"Seasons: {normalized['Season'].nunique()}")
            print("=" * 80)

            return normalized
        else:
            raise ValueError("No NBA data scraped!")


def main():
    """Scrape NBA data from 2020 to current."""
    scraper = NBADataScraper()

    # Scrape 2020-21 through 2024-25 seasons (up to current)
    nba_data = scraper.scrape_all_seasons(
        start_year=2020,
        end_year=2025  # Will get 2024-25 season
    )

    # Save
    output_dir = Path("data/basketball/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "nba_real_data.csv"
    nba_data.to_csv(output_file, index=False)

    print(f"\n[OK] Saved to {output_file}")
    print(f"[OK] Ready for training with {len(nba_data)} REAL NBA games!")


if __name__ == '__main__':
    main()
