"""
Live Scores Service - Enhanced

Integrates with football-data.org API to provide real-time match data,
live scores, and upcoming fixtures.

Features:
- Live match scores
- Upcoming fixtures
- Match statistics
- Team standings
- Historical results
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


from app.services.team_ids_mapping import TEAM_IDS

class LiveScoresService:
    """Enhanced live scores and match data service"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize live scores service
        
        Args:
            api_key: football-data.org API key (get from .env or environment)
        """
        # Try to get API key from environment or .env file
        if api_key is None:
            api_key = os.getenv('FOOTBALL_DATA_API_KEY')
            
            # Try loading from .env file
            if api_key is None:
                env_file = Path('.env')
                if env_file.exists():
                    with open(env_file) as f:
                        for line in f:
                            if line.startswith('FOOTBALL_DATA_API_KEY='):
                                api_key = line.split('=')[1].strip()
                                break
                            elif line.startswith('API_KEY='):
                                api_key = line.split('=')[1].strip()
                                break
        
        self.api_key = api_key
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {
            'X-Auth-Token': self.api_key if self.api_key else ''
        }
        
        # Competition IDs for major leagues
        self.competitions = {
            'PL': 2021,   # Premier League
            'ELC': 2016,  # Championship
            'PD': 2014,   # La Liga
            'BL1': 2002,  # Bundesliga
            'SA': 2019,   # Serie A
            'FL1': 2015,  # Ligue 1
            'DED': 2003,  # Eredivisie
            'PPL': 2017,  # Primeira Liga
            'CL': 2001,   # Champions League
            'EC': 2018,   # European Championship
            'WC': 2000,   # World Cup
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        if not self.api_key:
            logger.debug("No API key - skipping live scores request")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 403:
                logger.warning("API key invalid or rate limit exceeded")
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("API rate limit exceeded. Consider upgrading your plan.")
            elif e.response.status_code == 403:
                logger.error("API access forbidden. Check your API key.")
            else:
                logger.error(f"HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def get_live_matches(self, competition: str = None) -> List[Dict[str, Any]]:
        """
        Get currently live matches
        
        Args:
            competition: Optional competition code (e.g., 'PL' for Premier League)
        
        Returns:
            List of live match dictionaries
        """
        if not self.api_key:
            return []  # Return empty list if no API key
            
        params = {
            'status': 'LIVE,IN_PLAY,PAUSED'
        }
        
        if competition and competition in self.competitions:
            endpoint = f"competitions/{self.competitions[competition]}/matches"
        else:
            endpoint = "matches"
        
        data = self._make_request(endpoint, params)
        
        if data and 'matches' in data:
            matches = []
            for match in data['matches']:
                matches.append({
                    'id': match['id'],
                    'competition': match['competition']['name'],
                    'home_team': match['homeTeam']['name'],
                    'away_team': match['awayTeam']['name'],
                    'score': {
                        'home': match['score']['fullTime']['home'] or match['score']['halfTime']['home'] or 0,
                        'away': match['score']['fullTime']['away'] or match['score']['halfTime']['away'] or 0
                    },
                    'status': match['status'],
                    'minute': match.get('minute', 0),
                    'utc_date': match['utcDate']
                })
            
            logger.info(f"Retrieved {len(matches)} live matches")
            return matches
        
        return []
        date_from = datetime.now().strftime('%Y-%m-%d')
        date_to = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        params = {
            'status': 'SCHEDULED',
            'dateFrom': date_from,
            'dateTo': date_to
        }
        
        if competition and competition in self.competitions:
            endpoint = f"competitions/{self.competitions[competition]}/matches"
        else:
            endpoint = "matches"
        
        data = self._make_request(endpoint, params)
        
        if data and 'matches' in data:
            matches = []
            for match in data['matches']:
                matches.append({
                    'id': match['id'],
                    'competition': match['competition']['name'],
                    'home_team': match['homeTeam']['name'],
                    'away_team': match['awayTeam']['name'],
                    'utc_date': match['utcDate'],
                    'matchday': match.get('matchday'),
                    'venue': match.get('venue')
                })
            
            logger.info(f"Retrieved {len(matches)} upcoming matches")
            return matches
        
        return []
    
    def get_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific match
        
        Args:
            match_id: Match ID from football-data.org
        
        Returns:
            Match details dictionary
        """
        data = self._make_request(f"matches/{match_id}")
        
        if data:
            match = data
            return {
                'id': match['id'],
                'competition': match['competition']['name'],
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'score': match['score'],
                'status': match['status'],
                'utc_date': match['utcDate'],
                'venue': match.get('venue'),
                'referee': match.get('referees', [{}])[0].get('name') if match.get('referees') else None,
                'odds': match.get('odds'),
                'head2head': match.get('head2head')
            }
        
        return None
    
    def get_team_standings(self, competition: str = 'PL') -> List[Dict[str, Any]]:
        """
        Get league standings
        
        Args:
            competition: Competition code
        
        Returns:
            List of team standings
        """
        if competition not in self.competitions:
            logger.error(f"Unknown competition: {competition}")
            return []
        
        comp_id = self.competitions[competition]
        data = self._make_request(f"competitions/{comp_id}/standings")
        
        if data and 'standings' in data:
            standings = data['standings'][0]['table']  # Get main table
            
            teams = []
            for team in standings:
                teams.append({
                    'position': team['position'],
                    'team': team['team']['name'],
                    'played': team['playedGames'],
                    'won': team['won'],
                    'draw': team['draw'],
                    'lost': team['lost'],
                    'points': team['points'],
                    'goals_for': team['goalsFor'],
                    'goals_against': team['goalsAgainst'],
                    'goal_difference': team['goalDifference'],
                    'form': team.get('form')
                })
            
            logger.info(f"Retrieved standings for {competition}")
            return teams
        
        return []
    
    def get_team_matches(self, team_id: int, limit: int = 10, status: str = None) -> List[Dict[str, Any]]:
        """
        Get recent matches for a team
        
        Args:
            team_id: Team ID from football-data.org
            limit: Number of matches to retrieve
            status: Optional status to filter by (e.g. 'FINISHED', 'SCHEDULED')
        
        Returns:
            List of recent matches
        """
        params = {'limit': limit}
        if status:
            params['status'] = status
            
        data = self._make_request(f"teams/{team_id}/matches", params)
        
        if data and 'matches' in data:
            matches = []
            for match in data['matches']:
                matches.append({
                    'date': match['utcDate'],
                    'competition': match['competition']['name'],
                    'home_team': match['homeTeam']['name'],
                    'away_team': match['awayTeam']['name'],
                    'score': match['score'],
                    'status': match['status']
                })
            
            return matches
        
        return []
    
    def search_team(self, team_name: str) -> Optional[int]:
        """
        Search for a team and get its ID
        
        Args:
            team_name: Team name to search for
        
        Returns:
            Team ID or None if not found
        """
        # Use the auto-generated comprehensive mapping
        return TEAM_IDS.get(team_name.lower())


# Global service instance
_service_instance = None


def get_live_scores_service(api_key: Optional[str] = None) -> LiveScoresService:
    """
    Get or create live scores service instance (singleton)
    
    Args:
        api_key: Optional API key
    
    Returns:
        LiveScoresService instance
    """
    global _service_instance
    
    if _service_instance is None:
        _service_instance = LiveScoresService(api_key)
        logger.info("Live scores service initialized")
    
    return _service_instance
