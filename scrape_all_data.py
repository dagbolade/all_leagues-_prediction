"""
Data Collection Script - Scrape NBA and NFL historical data

This script collects data for:
- NBA: 2020-2026 seasons
- NFL: 2020-2025 seasons
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.basketball_scraper import BasketballScraper
from scrapers.nfl_scraper import NFLScraper
import time


def scrape_nba_data():
    """Scrape NBA historical data."""
    print("\n" + "="*80)
    print("SCRAPING NBA DATA")
    print("="*80 + "\n")

    scraper = BasketballScraper()
    output_dir = Path("data/basketball/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    # NBA seasons to scrape
    seasons = ['2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025']

    all_data = []

    for season in seasons:
        print(f"\nScraping NBA {season}...")
        try:
            df = scraper.scrape_season_data(season, league='NBA')

            if not df.empty:
                # Validate
                is_valid, issues = scraper.validate_data(df)

                if is_valid:
                    print(f"  SUCCESS: {len(df)} games scraped")
                    all_data.append(df)

                    # Save individual season
                    season_file = output_dir / f"nba_{season.replace('-', '_')}.csv"
                    scraper.save_data(df, season_file)
                else:
                    print(f"  WARNING: Data validation issues: {issues}")
                    # Still save it
                    all_data.append(df)
                    season_file = output_dir / f"nba_{season.replace('-', '_')}.csv"
                    scraper.save_data(df, season_file)

            else:
                print(f"  SKIPPED: No data returned")

            # Be nice to the server
            time.sleep(2)

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    # Combine all seasons
    if all_data:
        import pandas as pd
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = output_dir / "nba_all_seasons.csv"
        scraper.save_data(combined_df, combined_file)

        print(f"\n TOTAL: {len(combined_df)} NBA games collected")
        return combined_df

    return None


def scrape_nfl_data():
    """Scrape NFL historical data."""
    print("\n" + "="*80)
    print("SCRAPING NFL DATA")
    print("="*80 + "\n")

    scraper = NFLScraper()
    output_dir = Path("data/nfl/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    # NFL seasons to scrape
    seasons = ['2020', '2021', '2022', '2023', '2024']

    all_data = []

    for season in seasons:
        print(f"\nScraping NFL {season}...")
        try:
            df = scraper.scrape_season_data(season)

            if not df.empty:
                # Validate
                is_valid, issues = scraper.validate_data(df)

                if is_valid:
                    print(f"  SUCCESS: {len(df)} games scraped")
                    all_data.append(df)

                    # Save individual season
                    season_file = output_dir / f"nfl_{season}.csv"
                    scraper.save_data(df, season_file)
                else:
                    print(f"  WARNING: Data validation issues: {issues}")
                    # Still save it
                    all_data.append(df)
                    season_file = output_dir / f"nfl_{season}.csv"
                    scraper.save_data(df, season_file)

            else:
                print(f"  SKIPPED: No data returned")

            # Be nice to the server
            time.sleep(2)

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    # Combine all seasons
    if all_data:
        import pandas as pd
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = output_dir / "nfl_all_seasons.csv"
        scraper.save_data(combined_df, combined_file)

        print(f"\n TOTAL: {len(combined_df)} NFL games collected")
        return combined_df

    return None


def main():
    """Main data collection function."""
    print("\n" * 2)
    print("*" * 80)
    print("*" + "  MULTI-SPORT DATA COLLECTION".center(78) + "*")
    print("*" * 80)

    # Scrape NBA data
    nba_data = scrape_nba_data()

    # Scrape NFL data
    nfl_data = scrape_nfl_data()

    # Summary
    print("\n" + "="*80)
    print("DATA COLLECTION SUMMARY")
    print("="*80)

    if nba_data is not None:
        print(f"\n NBA: {len(nba_data)} games collected")
        print(f"   Seasons: {sorted(nba_data['Season'].unique())}")
        print(f"   Date range: {nba_data['Date'].min()} to {nba_data['Date'].max()}")
    else:
        print("\n NBA: No data collected")

    if nfl_data is not None:
        print(f"\n NFL: {len(nfl_data)} games collected")
        print(f"   Seasons: {sorted(nfl_data['Season'].unique())}")
        print(f"   Date range: {nfl_data['Date'].min()} to {nfl_data['Date'].max()}")
    else:
        print("\n NFL: No data collected")

    print("\n" + "="*80)
    print("Data collection complete!")
    print("Next step: Train models with collected data")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
