"""
NFL Data Scraper - Pro Football Reference + ESPN API

Sources:
1. Pro-Football-Reference.com - Historical NFL data
2. ESPN NFL API - Live scores and schedules
3. nfl_data_py - Python package for NFL data
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


class NFLScraper(BaseScraper):
    """Scraper for NFL data from multiple sources."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('nfl', config)

        # Pro-Football-Reference base URL
        self.pfr_base = "https://www.pro-football-reference.com"

        # ESPN NFL API
        self.espn_api_base = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

        # Current NFL season
        current_year = datetime.now().year
        current_month = datetime.now().month
        if current_month >= 9:  # NFL season starts in September
            self.current_season = current_year
        else:
            self.current_season = current_year - 1

    def scrape_season_data(self, season: str, league: Optional[str] = None) -> pd.DataFrame:
        """
        Scrape complete NFL season data.

        Args:
            season: Season year (e.g., '2023', '2024')
            league: Not used for NFL (only one league)

        Returns:
            DataFrame with all games for the season
        """
        print(f"🏈 Scraping NFL season data for {season}...")

        return self._scrape_nfl_season(int(season))

    def _scrape_nfl_season(self, year: int) -> pd.DataFrame:
        """Scrape NFL season from Pro-Football-Reference."""
        all_games = []

        # Pro-Football-Reference games URL
        url = f"{self.pfr_base}/years/{year}/games.htm"

        print(f"📥 Fetching: {url}")
        response = self.fetch_url(url)

        if not response:
            print(f"❌ Failed to fetch NFL schedule for {year}")
            return pd.DataFrame()

        soup = self.parse_html(response.text)

        # Find games table
        games_table = soup.find('table', {'id': 'games'})

        if not games_table:
            print("❌ Could not find games table")
            return pd.DataFrame()

        # Parse games
        rows = games_table.find('tbody').find_all('tr')

        current_week = None

        for row in rows:
            # Check if this is a week header
            if row.find('th', {'data-stat': 'week_num'}):
                week_cell = row.find('th', {'data-stat': 'week_num'})
                if week_cell:
                    week_text = week_cell.text.strip()
                    if week_text.isdigit():
                        current_week = int(week_text)
                    elif 'Wild' in week_text:
                        current_week = 'WildCard'
                    elif 'Division' in week_text:
                        current_week = 'Divisional'
                    elif 'Conf' in week_text:
                        current_week = 'Conference'
                    elif 'Super' in week_text:
                        current_week = 'SuperBowl'

            # Skip playoff week headers
            if row.get('class') and 'thead' in row.get('class', []):
                continue

            cells = row.find_all(['th', 'td'])

            if len(cells) < 8:
                continue

            try:
                # Extract game data
                week_num = current_week
                day = cells[1].text.strip() if len(cells) > 1 else ''
                date_str = cells[2].text.strip() if len(cells) > 2 else ''
                time_str = cells[3].text.strip() if len(cells) > 3 else ''
                winner = cells[4].text.strip() if len(cells) > 4 else ''
                loser = cells[6].text.strip() if len(cells) > 6 else ''

                # Check for @ symbol to determine home/away
                winner_loc = cells[4].find('a')
                loser_loc = cells[6].find('a')

                # Extract scores
                pts_win_cell = cells[5] if len(cells) > 5 else None
                pts_lose_cell = cells[7] if len(cells) > 7 else None

                pts_win = pts_win_cell.text.strip() if pts_win_cell else ''
                pts_lose = pts_lose_cell.text.strip() if pts_lose_cell else ''

                # Skip games not yet played
                if not pts_win or not pts_lose or not winner or not loser:
                    continue

                # Determine home/away
                # In PFR, the loser has @ if they were away
                is_winner_home = '@' not in str(cells[4])

                if is_winner_home:
                    home_team = winner
                    away_team = loser
                    home_score = int(pts_win)
                    away_score = int(pts_lose)
                else:
                    home_team = loser
                    away_team = winner
                    home_score = int(pts_lose)
                    away_score = int(pts_win)

                # Parse date
                try:
                    game_date = pd.to_datetime(f"{date_str} {year}")
                except:
                    game_date = None

                game_data = {
                    'Date': game_date,
                    'Week': week_num,
                    'HomeTeam': home_team,
                    'AwayTeam': away_team,
                    'HomeScore': home_score,
                    'AwayScore': away_score,
                    'League': 'NFL',
                    'Season': str(year)
                }

                # Determine result
                if home_score > away_score:
                    game_data['Result'] = 'H'
                elif away_score > home_score:
                    game_data['Result'] = 'A'
                else:
                    game_data['Result'] = 'D'  # Ties are possible in NFL (rare)

                # Calculate point differential
                game_data['PointDifferential'] = abs(home_score - away_score)
                game_data['TotalPoints'] = home_score + away_score

                all_games.append(game_data)

            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue

        df = pd.DataFrame(all_games)
        print(f"✅ Scraped {len(df)} NFL games for {year}")

        return df

    def scrape_live_scores(self) -> pd.DataFrame:
        """
        Scrape current live NFL scores using ESPN API.

        Returns:
            DataFrame with today's games and scores
        """
        print("🏈 Scraping live NFL scores...")

        url = f"{self.espn_api_base}/scoreboard"

        response = self.fetch_url(url)

        if not response:
            print("❌ Failed to fetch live scores")
            return pd.DataFrame()

        try:
            data = response.json()
        except:
            print("❌ Failed to parse JSON response")
            return pd.DataFrame()

        games = []

        for event in data.get('events', []):
            try:
                competition = event['competitions'][0]

                # Extract teams
                competitors = competition['competitors']

                home_team = None
                away_team = None
                home_score = None
                away_score = None

                for competitor in competitors:
                    team_name = competitor['team']['displayName']
                    score = int(competitor['score'])

                    if competitor['homeAway'] == 'home':
                        home_team = team_name
                        home_score = score
                    else:
                        away_team = team_name
                        away_score = score

                # Get game status
                status = competition['status']['type']['name']
                state = competition['status']['type']['state']

                # Get date
                date_str = event['date']
                game_date = pd.to_datetime(date_str)

                game_data = {
                    'Date': game_date.date(),
                    'HomeTeam': home_team,
                    'AwayTeam': away_team,
                    'HomeScore': home_score,
                    'AwayScore': away_score,
                    'Status': status,
                    'State': state,
                    'League': 'NFL'
                }

                games.append(game_data)

            except Exception as e:
                print(f"⚠️ Error parsing live game: {e}")
                continue

        df = pd.DataFrame(games)
        print(f"✅ Found {len(df)} NFL games")

        return df

    def scrape_team_stats(self, team: str, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape statistics for a specific NFL team.

        Args:
            team: Team name or abbreviation
            season: Season year (default: current season)

        Returns:
            Dictionary with team statistics
        """
        season = season or str(self.current_season)
        year = int(season)

        # Convert team name to abbreviation
        team_abbr = self._get_team_abbreviation(team)

        url = f"{self.pfr_base}/teams/{team_abbr}/{year}.htm"

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

        # Parse team stats
        team_stats_table = soup.find('table', {'id': 'team_stats'})

        if team_stats_table:
            rows = team_stats_table.find('tbody').find_all('tr')

            for row in rows:
                try:
                    stat_name = row.find('th').text.strip()
                    stat_value = row.find('td').text.strip()
                    stats[stat_name] = stat_value
                except:
                    continue

        return stats

    def scrape_schedule(self, date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Scrape upcoming NFL schedule.

        Args:
            date: Date to get schedule for (default: today)

        Returns:
            DataFrame with scheduled games
        """
        date = date or datetime.now()

        print(f"📅 Scraping NFL schedule")

        # Use ESPN API for schedule
        url = f"{self.espn_api_base}/scoreboard"

        response = self.fetch_url(url)

        if not response:
            return pd.DataFrame()

        # Parse similar to live scores
        return self.scrape_live_scores()

    def validate_data(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        Validate scraped NFL data.

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
            # NFL scores typically between 0-60
            invalid_home = ((df['HomeScore'] < 0) | (df['HomeScore'] > 80)).sum()
            invalid_away = ((df['AwayScore'] < 0) | (df['AwayScore'] > 80)).sum()

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
        """Convert team name to Pro-Football-Reference abbreviation."""
        team_abbr_map = {
            'Arizona Cardinals': 'crd',
            'Atlanta Falcons': 'atl',
            'Baltimore Ravens': 'rav',
            'Buffalo Bills': 'buf',
            'Carolina Panthers': 'car',
            'Chicago Bears': 'chi',
            'Cincinnati Bengals': 'cin',
            'Cleveland Browns': 'cle',
            'Dallas Cowboys': 'dal',
            'Denver Broncos': 'den',
            'Detroit Lions': 'det',
            'Green Bay Packers': 'gnb',
            'Houston Texans': 'htx',
            'Indianapolis Colts': 'clt',
            'Jacksonville Jaguars': 'jax',
            'Kansas City Chiefs': 'kan',
            'Las Vegas Raiders': 'rai',
            'Los Angeles Chargers': 'sdg',
            'Los Angeles Rams': 'ram',
            'Miami Dolphins': 'mia',
            'Minnesota Vikings': 'min',
            'New England Patriots': 'nwe',
            'New Orleans Saints': 'nor',
            'New York Giants': 'nyg',
            'New York Jets': 'nyj',
            'Philadelphia Eagles': 'phi',
            'Pittsburgh Steelers': 'pit',
            'San Francisco 49ers': 'sfo',
            'Seattle Seahawks': 'sea',
            'Tampa Bay Buccaneers': 'tam',
            'Tennessee Titans': 'oti',
            'Washington Commanders': 'was'
        }

        return team_abbr_map.get(team_name, team_name[:3].lower())

    def standardize_team_name(self, team_name: str) -> str:
        """Standardize NFL team names."""
        team_name = team_name.strip()

        # Handle common variations
        replacements = {
            'Washington Football Team': 'Washington Commanders',
            'Washington Redskins': 'Washington Commanders',
            'Oakland Raiders': 'Las Vegas Raiders',
            'San Diego Chargers': 'Los Angeles Chargers',
            'St. Louis Rams': 'Los Angeles Rams'
        }

        return replacements.get(team_name, team_name)


def test_nfl_scraper():
    """Test the NFL scraper."""
    print("=" * 60)
    print("TESTING NFL SCRAPER")
    print("=" * 60)

    scraper = NFLScraper()

    # Test scraping NFL season
    print("\n1. Testing NFL season scraping...")
    nfl_data = scraper.scrape_season_data('2023')

    if not nfl_data.empty:
        print(f"✅ Scraped {len(nfl_data)} NFL games")
        print("\nSample data:")
        print(nfl_data.head())

        # Validate data
        is_valid, issues = scraper.validate_data(nfl_data)
        if is_valid:
            print("\n✅ Data validation PASSED")
        else:
            print(f"\n⚠️ Data validation issues: {issues}")

        # Save data
        output_dir = Path("data/nfl/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        scraper.save_data(nfl_data, output_dir / "nfl_2023.csv")

    # Test live scores
    print("\n2. Testing live scores...")
    live_data = scraper.scrape_live_scores()

    if not live_data.empty:
        print(f"✅ Found {len(live_data)} NFL games")
        print(live_data)

    print("\n" + "=" * 60)
    print("NFL SCRAPER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_nfl_scraper()
