import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DisciplineAnalyzer:
    """
    Analyzer for match discipline statistics (Cards, Fouls) and Corners.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Ensure date column is datetime
        if 'Date' in self.df.columns and not pd.api.types.is_datetime64_any_dtype(self.df['Date']):
            self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
            
    def get_team_stats(self, team_name: str, last_n: int = 10) -> Dict:
        """
        Get average discipline and corner stats for a team (last N matches).
        """
        try:
            # Filter matches involving the team
            team_matches = self.df[
                (self.df['HomeTeam'] == team_name) | 
                (self.df['AwayTeam'] == team_name)
            ].sort_values('Date', ascending=False).head(last_n)
            
            if len(team_matches) == 0:
                return self._get_empty_stats()

            stats = {
                'matches': len(team_matches),
                'yellow_cards': 0,
                'red_cards': 0,
                'fouls': 0,
                'corners': 0
            }
            
            for _, match in team_matches.iterrows():
                if match['HomeTeam'] == team_name:
                    stats['yellow_cards'] += match.get('HY', 0)
                    stats['red_cards'] += match.get('HR', 0)
                    stats['fouls'] += match.get('HF', 0)
                    stats['corners'] += match.get('HC', 0)
                else:
                    stats['yellow_cards'] += match.get('AY', 0)
                    stats['red_cards'] += match.get('AR', 0)
                    stats['fouls'] += match.get('AF', 0)
                    stats['corners'] += match.get('AC', 0)
            
            # Calculate averages
            return {
                'matches': stats['matches'],
                'avg_yellow_cards': round(stats['yellow_cards'] / stats['matches'], 2),
                'avg_red_cards': round(stats['red_cards'] / stats['matches'], 2),
                'avg_fouls': round(stats['fouls'] / stats['matches'], 1),
                'avg_corners': round(stats['corners'] / stats['matches'], 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating team stats for {team_name}: {e}")
            return self._get_empty_stats()

    def get_h2h_intensity(self, home_team: str, away_team: str, last_n: int = 5) -> Dict:
        """
        Get intensity stats from Head-to-Head matches.
        """
        try:
            h2h_matches = self.df[
                ((self.df['HomeTeam'] == home_team) & (self.df['AwayTeam'] == away_team)) |
                ((self.df['HomeTeam'] == away_team) & (self.df['AwayTeam'] == home_team))
            ].sort_values('Date', ascending=False).head(last_n)
            
            if len(h2h_matches) == 0:
                return self._get_empty_stats()

            total_yellow = 0
            total_red = 0
            total_fouls = 0
            total_corners = 0
            
            for _, match in h2h_matches.iterrows():
                total_yellow += (match.get('HY', 0) + match.get('AY', 0))
                total_red += (match.get('HR', 0) + match.get('AR', 0))
                total_fouls += (match.get('HF', 0) + match.get('AF', 0))
                total_corners += (match.get('HC', 0) + match.get('AC', 0))
                
            return {
                'matches': len(h2h_matches),
                'avg_total_yellow': round(total_yellow / len(h2h_matches), 2),
                'avg_total_red': round(total_red / len(h2h_matches), 2),
                'avg_total_fouls': round(total_fouls / len(h2h_matches), 1),
                'avg_total_corners': round(total_corners / len(h2h_matches), 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating H2H intensity for {home_team} vs {away_team}: {e}")
            return self._get_empty_stats()

    def project_match_stats(self, home_team: str, away_team: str) -> Dict:
        """
        Project stats for an upcoming match based on recent form and H2H.
        """
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        h2h_stats = self.get_h2h_intensity(home_team, away_team)
        
        # Weighted projection: 40% Home Recent + 40% Away Recent + 20% H2H
        # If H2H is empty, 50% Home + 50% Away
        
        has_h2h = h2h_stats.get('matches', 0) > 0
        
        if has_h2h:
            proj_corners = (home_stats['avg_corners'] * 0.4) + (away_stats['avg_corners'] * 0.4) + (h2h_stats['avg_total_corners'] * 0.2)
            proj_cards = (home_stats['avg_yellow_cards'] * 0.4) + (away_stats['avg_yellow_cards'] * 0.4) + ((h2h_stats['avg_total_yellow']/2) * 0.2 * 2) # avg_total_yellow is for both teams combined
            # Better approximation for total cards:
            # We want projected TOTAL cards in the match.
            # Home avg + Away avg is a baseline. H2H avg total is another baseline.
            
            proj_total_cards = (home_stats['avg_yellow_cards'] + away_stats['avg_yellow_cards']) * 0.7 + (h2h_stats['avg_total_yellow']) * 0.3
            proj_total_corners = (home_stats['avg_corners'] + away_stats['avg_corners']) * 0.7 + (h2h_stats['avg_total_corners']) * 0.3
            
        else:
            proj_total_cards = home_stats['avg_yellow_cards'] + away_stats['avg_yellow_cards']
            proj_total_corners = home_stats['avg_corners'] + away_stats['avg_corners']

        # Determine intensity level
        if proj_total_cards >= 5.5:
            intensity = "High"
            intensity_color = "danger"
        elif proj_total_cards >= 3.5:
            intensity = "Medium"
            intensity_color = "warning"
        else:
            intensity = "Low"
            intensity_color = "success"

        return {
            'home_stats': home_stats,
            'away_stats': away_stats,
            'h2h_stats': h2h_stats,
            'projected_total_cards': round(proj_total_cards, 1),
            'projected_total_corners': round(proj_total_corners, 1),
            'intensity': intensity,
            'intensity_color': intensity_color
        }

    def _get_empty_stats(self) -> Dict:
        return {
            'matches': 0,
            'avg_yellow_cards': 0,
            'avg_red_cards': 0,
            'avg_fouls': 0,
            'avg_corners': 0,
            'avg_total_yellow': 0, # For H2H
            'avg_total_red': 0,
            'avg_total_fouls': 0,
            'avg_total_corners': 0
        }
