"""
Basketball Data Scraper - NBA, EuroLeague, NCAA

Sources:
1. Basketball-Reference.com - Historical and current NBA data
2. NBA Stats API - Official NBA statistics
3. EuroLeague API - European basketball
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import time
from bs4 import BeautifulSoup
import sys
sys.path.append('..')

from core.base_scraper import BaseScraper, ScraperResult


class BasketballScraper(BaseScraper):
    """Scraper for basketball data from multiple sources."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('basketball', config)

        # Basketball-Reference.com base URLs
        self.bbref_base = "https://www.basketball-reference.com"

        # NBA Stats API endpoints
        self.nba_api_base = "https://stats.nba.com/stats"

        # Current NBA season (adjust based on date)
        current_year = datetime.now().year
        current_month = datetime.now().month
        if current_month >= 10:  # NBA season starts in October
            self.current_season = f"{current_year}-{current_year + 1}"
        else:
            self.current_season = f"{current_year - 1}-{current_year}"

    def scrape_season_data(self, season: str, league: str = 'NBA') -> pd.DataFrame:
        """
        Scrape complete season data.

        Args:
            season: Season (e.g., '2024-2025' or '2024' for college)
            league: 'NBA', 'NCAA', 'EUROLEAGUE'

        Returns:
            DataFrame with all games for the season
        """
        print(f"🏀 Scraping {league} season data for {season}...")

        if league == 'NBA':
            return self._scrape_nba_season(season)
        elif league == 'NCAA':
            return self._scrape_ncaa_season(season)
        elif league == 'EUROLEAGUE':
            return self._scrape_euroleague_season(season)
        else:
            raise ValueError(f"Unsupported league: {league}")

    def _scrape_nba_season(self, season: str) -> pd.DataFrame:
        """Scrape NBA season from Basketball-Reference."""
        all_games = []

        # Convert season format: '2024-2025' -> '2025'
        year = int(season.split('-')[1]) if '-' in season else int(season)

        # Basketball-Reference uses the end year
        url = f"{self.bbref_base}/leagues/NBA_{year}_games.html"

        print(f"📥 Fetching: {url}")
        response = self.fetch_url(url)

        if not response:
            print(f"❌ Failed to fetch NBA schedule for {season}")
            return pd.DataFrame()

        soup = self.parse_html(response.text)

        # Find schedule table
        schedule_table = soup.find('table', {'id': 'schedule'})

        if not schedule_table:
            print("❌ Could not find schedule table")
            return pd.DataFrame()

        # Parse games
        rows = schedule_table.find('tbody').find_all('tr')

        for row in rows:
            # Skip month headers
            if 'thead' in row.get('class', []):
                continue

            cells = row.find_all(['th', 'td'])

            if len(cells) < 7:
                continue

            try:
                date_str = cells[0].text.strip()
                visitor_team = cells[2].text.strip()
                visitor_pts = cells[3].text.strip()
                home_team = cells[4].text.strip()
                home_pts = cells[5].text.strip()

                # Skip games not yet played
                if not visitor_pts or not home_pts:
                    continue

                game_data = {
                    'Date': pd.to_datetime(date_str),
                    'HomeTeam': home_team,
                    'AwayTeam': visitor_team,
                    'HomeScore': int(home_pts),
                    'AwayScore': int(visitor_pts),
                    'League': 'NBA',
                    'Season': season
                }

                # Determine winner
                if int(home_pts) > int(visitor_pts):
                    game_data['Result'] = 'H'
                elif int(visitor_pts) > int(home_pts):
                    game_data['Result'] = 'A'
                else:
                    game_data['Result'] = 'D'  # Extremely rare in basketball

                # Calculate total points
                game_data['TotalPoints'] = int(home_pts) + int(visitor_pts)

                # Point differential
                game_data['PointDifferential'] = abs(int(home_pts) - int(visitor_pts))

                all_games.append(game_data)

            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue

        df = pd.DataFrame(all_games)
        print(f"✅ Scraped {len(df)} NBA games for {season}")

        return df

    def _scrape_ncaa_season(self, season: str) -> pd.DataFrame:
        """Scrape NCAA basketball season data."""
        print("⚠️ NCAA scraping not yet implemented")
        # TODO: Implement NCAA scraping
        return pd.DataFrame()

    def _scrape_euroleague_season(self, season: str) -> pd.DataFrame:
        """Scrape EuroLeague basketball season data."""
        print("⚠️ EuroLeague scraping not yet implemented")
        # TODO: Implement EuroLeague scraping
        return pd.DataFrame()

    def scrape_live_scores(self) -> pd.DataFrame:
        """
        Scrape current live NBA scores.

        Returns:
            DataFrame with today's games and scores
        """
        print("🏀 Scraping live NBA scores...")

        url = f"{self.bbref_base}/boxscores/"

        response = self.fetch_url(url)

        if not response:
            print("❌ Failed to fetch live scores")
            return pd.DataFrame()

        soup = self.parse_html(response.text)

        games = []

        # Find all game summaries
        game_summaries = soup.find_all('div', class_='game_summary')

        for game in game_summaries:
            try:
                # Extract teams
                teams = game.find_all('tr')

                if len(teams) < 2:
                    continue

                visitor = teams[0]
                home = teams[1]

                visitor_team = visitor.find('a').text.strip()
                home_team = home.find('a').text.strip()

                visitor_score = visitor.find('td', class_='right').text.strip()
                home_score = home.find('td', class_='right').text.strip()

                # Check if game is final
                status_div = game.find('div', class_='game_summary')
                is_final = 'Final' in game.text

                game_data = {
                    'Date': datetime.now().date(),
                    'HomeTeam': home_team,
                    'AwayTeam': visitor_team,
                    'HomeScore': int(visitor_score) if visitor_score else None,
                    'AwayScore': int(home_score) if home_score else None,
                    'Status': 'Final' if is_final else 'In Progress',
                    'League': 'NBA'
                }

                games.append(game_data)

            except Exception as e:
                print(f"⚠️ Error parsing live game: {e}")
                continue

        df = pd.DataFrame(games)
        print(f"✅ Found {len(df)} games today")

        return df

    def scrape_team_stats(self, team: str, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape statistics for a specific NBA team.

        Args:
            team: Team name or abbreviation
            season: Season (default: current season)

        Returns:
            Dictionary with team statistics
        """
        season = season or self.current_season
        year = int(season.split('-')[1]) if '-' in season else int(season)

        # Convert team name to abbreviation
        team_abbr = self._get_team_abbreviation(team)

        url = f"{self.bbref_base}/teams/{team_abbr}/{year}.html"

        print(f"📥 Fetching stats for {team} ({season})")
        response = self.fetch_url(url)

        if not response:
            print(f"❌ Failed to fetch stats for {team}")
            return {}

        soup = self.parse_html(response.text)

        stats = {
            'team': team,
            'season': season
        }

        # Parse team stats table
        team_misc = soup.find('table', {'id': 'team_misc'})

        if team_misc:
            rows = team_misc.find('tbody').find_all('tr')

            for row in rows:
                cells = row.find_all('td')

                if len(cells) > 1:
                    stat_name = row.find('th').text.strip()
                    stat_value = cells[0].text.strip()
                    stats[stat_name] = stat_value

        return stats

    def scrape_schedule(self, date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Scrape upcoming NBA schedule.

        Args:
            date: Date to get schedule for (default: today)

        Returns:
            DataFrame with scheduled games
        """
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')

        print(f"📅 Scraping NBA schedule for {date_str}")

        url = f"{self.bbref_base}/boxscores/"

        response = self.fetch_url(url)

        if not response:
            return pd.DataFrame()

        # Parse similar to live scores
        # For simplicity, reusing live_scores logic
        return self.scrape_live_scores()

    def validate_data(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        Validate scraped basketball data.

        Args:
            df: DataFrame to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Required columns
        required_cols = ['Date', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")

        # Check for null values
        if 'HomeScore' in df.columns:
            null_scores = df['HomeScore'].isna().sum() + df['AwayScore'].isna().sum()
            if null_scores > 0:
                issues.append(f"{null_scores} games with missing scores")

        # Check for unrealistic scores
        if 'HomeScore' in df.columns and 'AwayScore' in df.columns:
            # NBA scores typically between 70-150
            invalid_home = ((df['HomeScore'] < 50) | (df['HomeScore'] > 180)).sum()
            invalid_away = ((df['AwayScore'] < 50) | (df['AwayScore'] > 180)).sum()

            if invalid_home > 0 or invalid_away > 0:
                issues.append(f"{invalid_home + invalid_away} games with unrealistic scores")

        # Check for duplicate games
        if all(col in df.columns for col in ['Date', 'HomeTeam', 'AwayTeam']):
            duplicates = df.duplicated(subset=['Date', 'HomeTeam', 'AwayTeam']).sum()
            if duplicates > 0:
                issues.append(f"{duplicates} duplicate games found")

        is_valid = len(issues) == 0

        return is_valid, issues

    def _get_team_abbreviation(self, team_name: str) -> str:
        """Convert team name to Basketball-Reference abbreviation."""
        team_abbr_map = {
            'Atlanta Hawks': 'ATL',
            'Boston Celtics': 'BOS',
            'Brooklyn Nets': 'BRK',
            'Charlotte Hornets': 'CHO',
            'Chicago Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL',
            'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW',
            'Houston Rockets': 'HOU',
            'Indiana Pacers': 'IND',
            'Los Angeles Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM',
            'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC',
            'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI',
            'Phoenix Suns': 'PHO',
            'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC',
            'San Antonio Spurs': 'SAS',
            'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA',
            'Washington Wizards': 'WAS'
        }

        return team_abbr_map.get(team_name, team_name[:3].upper())

    def standardize_team_name(self, team_name: str) -> str:
        """Standardize NBA team names."""
        # Remove common variations
        team_name = team_name.strip()

        # Handle abbreviations
        abbr_to_full = {abbr: full for full, abbr in self._get_all_team_abbreviations().items()}

        if team_name.upper() in abbr_to_full:
            return abbr_to_full[team_name.upper()]

        return team_name

    def _get_all_team_abbreviations(self) -> Dict[str, str]:
        """Get all NBA team abbreviations."""
        return {
            'Atlanta Hawks': 'ATL',
            'Boston Celtics': 'BOS',
            'Brooklyn Nets': 'BRK',
            'Charlotte Hornets': 'CHO',
            'Chicago Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL',
            'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW',
            'Houston Rockets': 'HOU',
            'Indiana Pacers': 'IND',
            'Los Angeles Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM',
            'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC',
            'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI',
            'Phoenix Suns': 'PHO',
            'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC',
            'San Antonio Spurs': 'SAS',
            'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA',
            'Washington Wizards': 'WAS'
        }


def test_basketball_scraper():
    """Test the basketball scraper."""
    print("=" * 60)
    print("TESTING BASKETBALL SCRAPER")
    print("=" * 60)

    scraper = BasketballScraper()

    # Test scraping NBA season
    print("\n1. Testing NBA season scraping...")
    nba_data = scraper.scrape_season_data('2023-2024', league='NBA')

    if not nba_data.empty:
        print(f"✅ Scraped {len(nba_data)} NBA games")
        print("\nSample data:")
        print(nba_data.head())

        # Validate data
        is_valid, issues = scraper.validate_data(nba_data)
        if is_valid:
            print("\n✅ Data validation PASSED")
        else:
            print(f"\n⚠️ Data validation issues: {issues}")

        # Save data
        output_dir = Path("data/basketball/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        scraper.save_data(nba_data, output_dir / "nba_2023_2024.csv")

    # Test live scores
    print("\n2. Testing live scores...")
    live_data = scraper.scrape_live_scores()

    if not live_data.empty:
        print(f"✅ Found {len(live_data)} games today")
        print(live_data)

    print("\n" + "=" * 60)
    print("BASKETBALL SCRAPER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_basketball_scraper()
