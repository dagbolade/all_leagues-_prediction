"""
Base Scraper - Abstract interface for all sports data scrapers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time


class BaseScraper(ABC):
    """
    Abstract base class for sport-specific data scrapers.

    All sport scrapers must inherit from this and implement all abstract methods.
    """

    def __init__(self, sport_name: str, config: Optional[Dict] = None):
        """
        Initialize base scraper.

        Args:
            sport_name: Name of the sport
            config: Optional configuration dictionary
        """
        self.sport_name = sport_name
        self.config = config or {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limit_delay = self.config.get('rate_limit_delay', 1.0)  # seconds between requests
        self.last_request_time = 0

    @abstractmethod
    def scrape_season_data(self, season: str, league: Optional[str] = None) -> pd.DataFrame:
        """
        Scrape complete season data.

        Args:
            season: Season identifier (e.g., '2024-2025', '2024')
            league: Optional league identifier

        Returns:
            DataFrame with season data
        """
        pass

    @abstractmethod
    def scrape_live_scores(self) -> pd.DataFrame:
        """
        Scrape current live scores/results.

        Returns:
            DataFrame with live match data
        """
        pass

    @abstractmethod
    def scrape_team_stats(self, team: str, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape statistics for a specific team.

        Args:
            team: Team name/identifier
            season: Optional season identifier

        Returns:
            Dictionary with team statistics
        """
        pass

    @abstractmethod
    def scrape_schedule(self, date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Scrape upcoming match schedule.

        Args:
            date: Optional date to get schedule for (default: today)

        Returns:
            DataFrame with scheduled matches
        """
        pass

    @abstractmethod
    def validate_data(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        Validate scraped data quality.

        Args:
            df: DataFrame to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        pass

    def save_data(self, df: pd.DataFrame, filepath: Path, format: str = 'csv') -> None:
        """
        Save scraped data to file.

        Args:
            df: DataFrame to save
            filepath: Path to save to
            format: File format ('csv', 'excel', 'pickle')
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if format == 'csv':
            df.to_csv(filepath, index=False)
        elif format == 'excel':
            df.to_excel(filepath, index=False)
        elif format == 'pickle':
            df.to_pickle(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

        print(f"✅ {self.sport_name.title()} data saved to {filepath}")

    def rate_limit(self) -> None:
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch_url(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Fetch URL with rate limiting and retries.

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None if failed
        """
        self.rate_limit()

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"❌ Failed to fetch {url} after {max_retries} attempts")
                    return None

        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content.

        Args:
            html: HTML string to parse

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'html.parser')

    def standardize_team_name(self, team_name: str) -> str:
        """
        Standardize team names for consistency.

        Args:
            team_name: Raw team name

        Returns:
            Standardized team name
        """
        # Basic standardization - subclasses should override for sport-specific logic
        return team_name.strip()

    def get_scraper_info(self) -> Dict[str, Any]:
        """Get information about this scraper."""
        return {
            'sport': self.sport_name,
            'rate_limit_delay': self.rate_limit_delay,
            'config': self.config
        }


class ScraperResult:
    """Standardized scraper result."""

    def __init__(self, sport: str, data: pd.DataFrame, metadata: Dict[str, Any]):
        self.sport = sport
        self.data = data
        self.metadata = metadata
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sport': self.sport,
            'num_records': len(self.data),
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

    def __repr__(self):
        return f"ScraperResult(sport={self.sport}, records={len(self.data)})"
