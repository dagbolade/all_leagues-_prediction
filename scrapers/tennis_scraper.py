"""
Real Tennis Data Scraper

Sources:
1. Tennis-Data.co.uk (Historical match data with odds)
2. Jeff Sackmann's Tennis Abstract GitHub (ATP/WTA match data)
3. ATP/WTA Official APIs

Downloads REAL historical tennis data for training models.
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from typing import List, Dict, Optional
import warnings

warnings.filterwarnings('ignore')


class TennisDataScraper:
    """Scraper for real tennis match data from multiple sources."""

    def __init__(self):
        self.base_urls = {
            'tennis_data': 'http://www.tennis-data.co.uk',
            'github_atp': 'https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master',
            'github_wta': 'https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master'
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_tennis_data_uk(self, years: List[int] = None) -> pd.DataFrame:
        """
        Scrape historical tennis data from tennis-data.co.uk

        Args:
            years: List of years to scrape (default: last 5 years)

        Returns:
            DataFrame with match data
        """
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 4, current_year + 1))

        print("[Tennis-Data.co.uk] Scraping tennis match data...")

        all_data = []

        for year in years:
            print(f"  Fetching {year} data...")

            # Tennis-Data.co.uk has Excel files for each year
            # Format: http://www.tennis-data.co.uk/2024/2024.xlsx
            url = f"{self.base_urls['tennis_data']}/{year}/{year}.xlsx"

            try:
                # Download the Excel file
                response = requests.get(url, headers=self.headers, timeout=30)

                if response.status_code == 200:
                    # Save temporarily
                    temp_file = Path(f"temp_tennis_{year}.xlsx")
                    with open(temp_file, 'wb') as f:
                        f.write(response.content)

                    # Read all sheets (different tournaments)
                    try:
                        excel_file = pd.ExcelFile(temp_file)

                        for sheet_name in excel_file.sheet_names:
                            df = pd.read_excel(temp_file, sheet_name=sheet_name)
                            df['Year'] = year
                            df['Tournament_Sheet'] = sheet_name
                            all_data.append(df)
                            print(f"    {sheet_name}: {len(df)} matches")

                        excel_file.close()
                    except Exception as e:
                        print(f"    Error reading Excel: {e}")

                    # Clean up temp file
                    if temp_file.exists():
                        temp_file.unlink()
                else:
                    print(f"    No data available for {year} (HTTP {response.status_code})")

                time.sleep(1)  # Be polite to server

            except Exception as e:
                print(f"    Error fetching {year}: {e}")
                continue

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n[OK] Scraped {len(combined):,} matches from Tennis-Data.co.uk")
            return combined
        else:
            print("\n[WARNING] No data scraped from Tennis-Data.co.uk")
            return pd.DataFrame()

    def scrape_github_atp(self, years: List[int] = None) -> pd.DataFrame:
        """
        Scrape ATP match data from Jeff Sackmann's GitHub repository.

        This is THE definitive source for historical ATP data.
        """
        if years is None:
            # Get 2020 to 2026 (current)
            years = list(range(2020, 2027))

        print("\n[GitHub ATP] Scraping ATP match data from Jeff Sackmann's repo...")

        all_data = []

        for year in years:
            print(f"  Fetching ATP {year}...")

            # Format: atp_matches_2024.csv
            url = f"{self.base_urls['github_atp']}/atp_matches_{year}.csv"

            try:
                df = pd.read_csv(url)
                df['Year'] = year
                df['Tour'] = 'ATP'
                all_data.append(df)
                print(f"    Found {len(df)} ATP matches")

                time.sleep(0.5)

            except Exception as e:
                print(f"    Error fetching ATP {year}: {e}")
                continue

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n[OK] Scraped {len(combined):,} ATP matches from GitHub")
            return combined
        else:
            print("\n[WARNING] No ATP data scraped")
            return pd.DataFrame()

    def scrape_github_wta(self, years: List[int] = None) -> pd.DataFrame:
        """
        Scrape WTA match data from Jeff Sackmann's GitHub repository.
        """
        if years is None:
            # Get 2020 to 2026 (current)
            years = list(range(2020, 2027))

        print("\n[GitHub WTA] Scraping WTA match data from Jeff Sackmann's repo...")

        all_data = []

        for year in years:
            print(f"  Fetching WTA {year}...")

            # Format: wta_matches_2024.csv
            url = f"{self.base_urls['github_wta']}/wta_matches_{year}.csv"

            try:
                df = pd.read_csv(url)
                df['Year'] = year
                df['Tour'] = 'WTA'
                all_data.append(df)
                print(f"    Found {len(df)} WTA matches")

                time.sleep(0.5)

            except Exception as e:
                print(f"    Error fetching WTA {year}: {e}")
                continue

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n[OK] Scraped {len(combined):,} WTA matches from GitHub")
            return combined
        else:
            print("\n[WARNING] No WTA data scraped")
            return pd.DataFrame()

    def normalize_github_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize GitHub tennis data to match our prediction format.

        GitHub columns include:
        - tourney_date, tourney_name, surface, round
        - winner_name, loser_name, score
        - winner_rank, loser_rank
        - winner_ht, winner_age, loser_ht, loser_age
        - And many more detailed stats
        """
        print("\n[Normalize] Processing GitHub tennis data...")

        normalized = pd.DataFrame()

        # Basic match info
        normalized['Date'] = pd.to_datetime(df['tourney_date'], format='%Y%m%d', errors='coerce')
        normalized['Tournament'] = df['tourney_name']
        normalized['Surface'] = df['surface']
        normalized['Round'] = df['round']

        # Players
        normalized['WinnerName'] = df['winner_name']
        normalized['LoserName'] = df['loser_name']

        # Randomize player positions to avoid bias
        # Randomly assign winner/loser to Player1/Player2
        import random
        random.seed(42)  # For reproducibility

        player1_list = []
        player2_list = []
        winner_list = []
        player1_rank_list = []
        player2_rank_list = []

        for idx, row in df.iterrows():
            # Random coin flip: 0 = winner is Player1, 1 = winner is Player2
            if random.random() < 0.5:
                # Winner is Player1
                player1_list.append(row['winner_name'])
                player2_list.append(row['loser_name'])
                winner_list.append('Player1')
                player1_rank_list.append(row.get('winner_rank'))
                player2_rank_list.append(row.get('loser_rank'))
            else:
                # Winner is Player2
                player1_list.append(row['loser_name'])
                player2_list.append(row['winner_name'])
                winner_list.append('Player2')
                player1_rank_list.append(row.get('loser_rank'))
                player2_rank_list.append(row.get('winner_rank'))

        normalized['Player1'] = player1_list
        normalized['Player2'] = player2_list
        normalized['Winner'] = winner_list

        # Rankings (now properly aligned with randomized positions)
        normalized['Player1Rank'] = player1_rank_list
        normalized['Player2Rank'] = player2_rank_list

        # Score
        normalized['Score'] = df['score']

        # Stats (if available) - align with randomized positions
        # We need to rebuild these lists based on whether winner is Player1 or Player2
        if 'winner_ace' in df.columns and 'loser_ace' in df.columns:
            p1_aces = []
            p2_aces = []
            for i, winner_pos in enumerate(winner_list):
                if winner_pos == 'Player1':
                    p1_aces.append(df.iloc[i].get('winner_ace'))
                    p2_aces.append(df.iloc[i].get('loser_ace'))
                else:
                    p1_aces.append(df.iloc[i].get('loser_ace'))
                    p2_aces.append(df.iloc[i].get('winner_ace'))
            normalized['Player1Aces'] = p1_aces
            normalized['Player2Aces'] = p2_aces

        if 'winner_df' in df.columns and 'loser_df' in df.columns:
            p1_df = []
            p2_df = []
            for i, winner_pos in enumerate(winner_list):
                if winner_pos == 'Player1':
                    p1_df.append(df.iloc[i].get('winner_df'))
                    p2_df.append(df.iloc[i].get('loser_df'))
                else:
                    p1_df.append(df.iloc[i].get('loser_df'))
                    p2_df.append(df.iloc[i].get('winner_df'))
            normalized['Player1DoubleFaults'] = p1_df
            normalized['Player2DoubleFaults'] = p2_df

        if 'winner_1stIn' in df.columns and 'loser_1stIn' in df.columns:
            p1_1stIn = []
            p2_1stIn = []
            for i, winner_pos in enumerate(winner_list):
                if winner_pos == 'Player1':
                    p1_1stIn.append(df.iloc[i].get('winner_1stIn'))
                    p2_1stIn.append(df.iloc[i].get('loser_1stIn'))
                else:
                    p1_1stIn.append(df.iloc[i].get('loser_1stIn'))
                    p2_1stIn.append(df.iloc[i].get('winner_1stIn'))
            normalized['Player1FirstServeIn'] = p1_1stIn
            normalized['Player2FirstServeIn'] = p2_1stIn

        if 'winner_1stWon' in df.columns and 'loser_1stWon' in df.columns:
            p1_1stWon = []
            p2_1stWon = []
            for i, winner_pos in enumerate(winner_list):
                if winner_pos == 'Player1':
                    p1_1stWon.append(df.iloc[i].get('winner_1stWon'))
                    p2_1stWon.append(df.iloc[i].get('loser_1stWon'))
                else:
                    p1_1stWon.append(df.iloc[i].get('loser_1stWon'))
                    p2_1stWon.append(df.iloc[i].get('winner_1stWon'))
            normalized['Player1FirstServeWon'] = p1_1stWon
            normalized['Player2FirstServeWon'] = p2_1stWon

        # Tour
        normalized['Tour'] = df['Tour']
        normalized['Year'] = df['Year']

        # Remove rows with missing critical data
        normalized = normalized.dropna(subset=['Date', 'Player1', 'Player2'])

        print(f"[OK] Normalized {len(normalized):,} matches")

        return normalized

    def normalize_tennis_data_uk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize tennis-data.co.uk data to match our format.
        """
        print("\n[Normalize] Processing Tennis-Data.co.uk data...")

        normalized = pd.DataFrame()

        # Basic match info - tennis-data.co.uk format
        if 'Date' in df.columns:
            normalized['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Players
        if 'Winner' in df.columns and 'Loser' in df.columns:
            normalized['WinnerName'] = df['Winner']
            normalized['LoserName'] = df['Loser']

            # Randomize player positions
            import random
            random.seed(42)

            player1_list = []
            player2_list = []
            winner_list = []

            for idx, row in df.iterrows():
                if pd.notna(row.get('Winner')) and pd.notna(row.get('Loser')):
                    if random.random() < 0.5:
                        player1_list.append(row['Winner'])
                        player2_list.append(row['Loser'])
                        winner_list.append('Player1')
                    else:
                        player1_list.append(row['Loser'])
                        player2_list.append(row['Winner'])
                        winner_list.append('Player2')
                else:
                    player1_list.append(None)
                    player2_list.append(None)
                    winner_list.append(None)

            normalized['Player1'] = player1_list
            normalized['Player2'] = player2_list
            normalized['Winner'] = winner_list

        # Surface and tournament info
        if 'Surface' in df.columns:
            normalized['Surface'] = df['Surface']
        if 'Tournament' in df.columns:
            normalized['Tournament'] = df['Tournament']
        if 'Round' in df.columns:
            normalized['Round'] = df['Round']

        # Rankings (if available)
        if 'WRank' in df.columns and 'LRank' in df.columns:
            # Align with randomized positions
            p1_rank = []
            p2_rank = []
            for i, w in enumerate(winner_list):
                if w == 'Player1':
                    p1_rank.append(df.iloc[i].get('WRank'))
                    p2_rank.append(df.iloc[i].get('LRank'))
                else:
                    p1_rank.append(df.iloc[i].get('LRank'))
                    p2_rank.append(df.iloc[i].get('WRank'))
            normalized['Player1Rank'] = p1_rank
            normalized['Player2Rank'] = p2_rank

        # Tour (assume ATP/WTA based on context)
        normalized['Tour'] = 'Mixed'
        if 'Year' in df.columns:
            normalized['Year'] = df['Year']

        # Remove rows with missing data
        normalized = normalized.dropna(subset=['Date', 'Player1', 'Player2'])

        print(f"[OK] Normalized {len(normalized):,} matches")

        return normalized

    def scrape_all_sources(self, years: List[int] = None, sources: List[str] = None) -> pd.DataFrame:
        """
        Scrape from all available sources and combine.

        Args:
            years: Years to scrape
            sources: List of sources ['github_atp', 'github_wta', 'tennis_data']

        Returns:
            Combined DataFrame with all tennis data
        """
        if sources is None:
            sources = ['github_atp', 'github_wta']  # Most reliable sources

        print("=" * 80)
        print("TENNIS DATA SCRAPER - REAL DATA COLLECTION")
        print("=" * 80)

        all_data = []

        # Scrape GitHub ATP (2020-2024)
        if 'github_atp' in sources:
            atp_data = self.scrape_github_atp(years)
            if not atp_data.empty:
                atp_normalized = self.normalize_github_data(atp_data)
                all_data.append(atp_normalized)

        # Scrape GitHub WTA (2020-2024)
        if 'github_wta' in sources:
            wta_data = self.scrape_github_wta(years)
            if not wta_data.empty:
                wta_normalized = self.normalize_github_data(wta_data)
                all_data.append(wta_normalized)

        # Scrape Tennis-Data.co.uk for 2025 data (latest)
        if 'tennis_data' in sources:
            tennis_years = [y for y in (years or [2025]) if y >= 2025]
            if tennis_years:
                tennis_data = self.scrape_tennis_data_uk(tennis_years)
                if not tennis_data.empty:
                    tennis_normalized = self.normalize_tennis_data_uk(tennis_data)
                    all_data.append(tennis_normalized)

        # Combine all sources
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            combined = combined.sort_values('Date').reset_index(drop=True)

            print("\n" + "=" * 80)
            print("SCRAPING COMPLETE")
            print("=" * 80)
            print(f"Total matches: {len(combined):,}")
            print(f"Date range: {combined['Date'].min()} to {combined['Date'].max()}")
            print(f"Surfaces: {combined['Surface'].value_counts().to_dict()}")
            print(f"Tours: {combined['Tour'].value_counts().to_dict()}")
            print("=" * 80)

            return combined
        else:
            raise ValueError("No data scraped from any source!")


def main():
    """Main scraping function."""
    scraper = TennisDataScraper()

    # Scrape 2020 to 2026 (current) - LATEST data
    years = list(range(2020, 2027))

    # Scrape from GitHub (2020-2024) + Tennis-Data.co.uk (2025+)
    tennis_data = scraper.scrape_all_sources(
        years=years,
        sources=['github_atp', 'github_wta', 'tennis_data']
    )

    # Save to CSV
    output_dir = Path("data/tennis/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "tennis_real_data.csv"
    tennis_data.to_csv(output_file, index=False)

    print(f"\n[OK] Saved to {output_file}")
    print(f"[OK] Ready for model training with {len(tennis_data):,} REAL matches!")


if __name__ == '__main__':
    main()
