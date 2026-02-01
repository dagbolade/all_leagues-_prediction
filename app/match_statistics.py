"""
Match Statistics Generator

Generates comprehensive match statistics including:
- Team form analysis
- Head-to-head history
- League position and trends
- Goal statistics
- Home/away performance
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MatchStatistics:
    """Generate comprehensive match statistics"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize statistics generator
        
        Args:
            df: Historical match data
        """
        self.df = df
        
        # Ensure Date column is datetime
        if 'Date' in self.df.columns:
            self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
    
    def generate_full_statistics(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Generate complete statistics for a match
        
        Args:
            home_team: Home team name
            away_team: Away team name
        
        Returns:
            Dictionary with all statistics
        """
        stats = {
            'home_team': home_team,
            'away_team': away_team,
            'generated_at': datetime.now().isoformat(),
            'team_form': self._get_team_form(home_team, away_team),
            'head_to_head': self._get_h2h_stats(home_team, away_team),
            'goal_statistics': self._get_goal_stats(home_team, away_team),
            'home_away_performance': self._get_venue_stats(home_team, away_team),
            'recent_results': self._get_recent_results(home_team, away_team),
            'league_position': self._get_league_position(home_team, away_team)
        }
        
        return stats
    
    def _get_team_form(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get recent form for both teams"""
        home_form = self._calculate_form(home_team, last_n=10)
        away_form = self._calculate_form(away_team, last_n=10)
        
        return {
            'home': home_form,
            'away': away_form,
            'comparison': {
                'home_points': home_form['points'],
                'away_points': away_form['points'],
                'advantage': 'Home' if home_form['points'] > away_form['points'] else 'Away' if away_form['points'] > home_form['points'] else 'Equal'
            }
        }
    
    def _calculate_form(self, team: str, last_n: int = 10) -> Dict[str, Any]:
        """Calculate form for a team"""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
        ].sort_values('Date', ascending=False).head(last_n)
        
        if len(team_matches) == 0:
            return {
                'matches_played': 0,
                'form_string': '',
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'points': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0
            }
        
        form_letters = []
        wins = draws = losses = 0
        goals_for = goals_against = 0
        
        for _, match in team_matches.iterrows():
            if match['HomeTeam'] == team:
                gf, ga = match['FTHG'], match['FTAG']
                result = match['FTR']
                if result == 'H':
                    form_letters.append('W')
                    wins += 1
                elif result == 'D':
                    form_letters.append('D')
                    draws += 1
                else:
                    form_letters.append('L')
                    losses += 1
            else:
                gf, ga = match['FTAG'], match['FTHG']
                result = match['FTR']
                if result == 'A':
                    form_letters.append('W')
                    wins += 1
                elif result == 'D':
                    form_letters.append('D')
                    draws += 1
                else:
                    form_letters.append('L')
                    losses += 1
            
            goals_for += gf
            goals_against += ga
        
        points = wins * 3 + draws
        
        return {
            'matches_played': len(team_matches),
            'form_string': ''.join(form_letters),
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'points': points,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'ppg': round(points / len(team_matches), 2) if len(team_matches) > 0 else 0,
            'win_percentage': round(wins / len(team_matches) * 100, 1) if len(team_matches) > 0 else 0
        }
    
    def _get_h2h_stats(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get head-to-head statistics"""
        h2h_matches = self.df[
            ((self.df['HomeTeam'] == home_team) & (self.df['AwayTeam'] == away_team)) |
            ((self.df['HomeTeam'] == away_team) & (self.df['AwayTeam'] == home_team))
        ].sort_values('Date', ascending=False).head(10)
        
        if len(h2h_matches) == 0:
            return {
                'total_matches': 0,
                'home_wins': 0,
                'draws': 0,
                'away_wins': 0,
                'recent_results': []
            }
        
        home_wins = len(h2h_matches[
            ((h2h_matches['HomeTeam'] == home_team) & (h2h_matches['FTR'] == 'H')) |
            ((h2h_matches['AwayTeam'] == home_team) & (h2h_matches['FTR'] == 'A'))
        ])
        
        draws = len(h2h_matches[h2h_matches['FTR'] == 'D'])
        away_wins = len(h2h_matches) - home_wins - draws
        
        # Recent results
        recent_results = []
        for _, match in h2h_matches.head(5).iterrows():
            result = {
                'date': match['Date'].strftime('%Y-%m-%d') if pd.notna(match['Date']) else 'N/A',
                'home': match['HomeTeam'],
                'away': match['AwayTeam'],
                'score': f"{int(match['FTHG'])}-{int(match['FTAG'])}",
                'result': match['FTR']
            }
            recent_results.append(result)
        
        # Goal statistics
        total_goals = (h2h_matches['FTHG'] + h2h_matches['FTAG']).sum()
        avg_goals = total_goals / len(h2h_matches)
        over_25 = len(h2h_matches[(h2h_matches['FTHG'] + h2h_matches['FTAG']) > 2.5])
        btts = len(h2h_matches[(h2h_matches['FTHG'] > 0) & (h2h_matches['FTAG'] > 0)])
        
        return {
            'total_matches': len(h2h_matches),
            'home_wins': home_wins,
            'draws': draws,
            'away_wins': away_wins,
            'recent_results': recent_results,
            'goal_stats': {
                'avg_goals': round(avg_goals, 2),
                'over_25_percentage': round(over_25 / len(h2h_matches) * 100, 1),
                'btts_percentage': round(btts / len(h2h_matches) * 100, 1)
            }
        }
    
    def _get_goal_stats(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get goal statistics for both teams"""
        home_stats = self._calculate_goal_stats(home_team)
        away_stats = self._calculate_goal_stats(away_team)
        
        return {
            'home': home_stats,
            'away': away_stats
        }
    
    def _calculate_goal_stats(self, team: str, last_n: int = 10) -> Dict[str, Any]:
        """Calculate goal statistics for a team"""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
        ].sort_values('Date', ascending=False).head(last_n)
        
        if len(team_matches) == 0:
            return {}
        
        goals_for = []
        goals_against = []
        clean_sheets = 0
        failed_to_score = 0
        
        for _, match in team_matches.iterrows():
            if match['HomeTeam'] == team:
                gf, ga = match['FTHG'], match['FTAG']
            else:
                gf, ga = match['FTAG'], match['FTHG']
            
            goals_for.append(gf)
            goals_against.append(ga)
            
            if ga == 0:
                clean_sheets += 1
            if gf == 0:
                failed_to_score += 1
        
        return {
            'avg_goals_scored': round(sum(goals_for) / len(goals_for), 2),
            'avg_goals_conceded': round(sum(goals_against) / len(goals_against), 2),
            'clean_sheets': clean_sheets,
            'failed_to_score': failed_to_score,
            'clean_sheet_percentage': round(clean_sheets / len(team_matches) * 100, 1),
            'scoring_percentage': round((len(team_matches) - failed_to_score) / len(team_matches) * 100, 1)
        }
    
    def _get_venue_stats(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get home/away performance statistics"""
        home_at_home = self._calculate_venue_stats(home_team, 'home')
        away_away = self._calculate_venue_stats(away_team, 'away')
        
        return {
            'home_at_home': home_at_home,
            'away_away': away_away
        }
    
    def _calculate_venue_stats(self, team: str, venue: str, last_n: int = 10) -> Dict[str, Any]:
        """Calculate venue-specific statistics"""
        if venue == 'home':
            matches = self.df[self.df['HomeTeam'] == team].sort_values('Date', ascending=False).head(last_n)
            wins = len(matches[matches['FTR'] == 'H'])
        else:
            matches = self.df[self.df['AwayTeam'] == team].sort_values('Date', ascending=False).head(last_n)
            wins = len(matches[matches['FTR'] == 'A'])
        
        if len(matches) == 0:
            return {}
        
        draws = len(matches[matches['FTR'] == 'D'])
        losses = len(matches) - wins - draws
        
        return {
            'matches': len(matches),
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'win_percentage': round(wins / len(matches) * 100, 1),
            'points': wins * 3 + draws,
            'ppg': round((wins * 3 + draws) / len(matches), 2)
        }
    
    def _get_recent_results(self, home_team: str, away_team: str) -> Dict[str, List[Dict]]:
        """Get recent match results for both teams"""
        home_recent = self._get_team_recent_results(home_team, 5)
        away_recent = self._get_team_recent_results(away_team, 5)
        
        return {
            'home': home_recent,
            'away': away_recent
        }
    
    def _get_team_recent_results(self, team: str, n: int = 5) -> List[Dict]:
        """Get recent results for a team"""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
        ].sort_values('Date', ascending=False).head(n)
        
        results = []
        for _, match in team_matches.iterrows():
            is_home = match['HomeTeam'] == team
            opponent = match['AwayTeam'] if is_home else match['HomeTeam']
            
            if is_home:
                score = f"{int(match['FTHG'])}-{int(match['FTAG'])}"
                result = 'W' if match['FTR'] == 'H' else 'D' if match['FTR'] == 'D' else 'L'
            else:
                score = f"{int(match['FTAG'])}-{int(match['FTHG'])}"
                result = 'W' if match['FTR'] == 'A' else 'D' if match['FTR'] == 'D' else 'L'
            
            results.append({
                'date': match['Date'].strftime('%Y-%m-%d') if pd.notna(match['Date']) else 'N/A',
                'opponent': opponent,
                'venue': 'H' if is_home else 'A',
                'score': score,
                'result': result
            })
        
        return results
    
    def _get_league_position(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get current league position (simplified - based on recent form)"""
        # This is a simplified version - in production, you'd calculate actual league table
        home_form = self._calculate_form(home_team, last_n=38)
        away_form = self._calculate_form(away_team, last_n=38)
        
        return {
            'home': {
                'team': home_team,
                'points': home_form['points'],
                'goal_difference': home_form['goal_difference']
            },
            'away': {
                'team': away_team,
                'points': away_form['points'],
                'goal_difference': away_form['goal_difference']
            }
        }


# Global instance
_stats_generator = None


def get_statistics_generator(df: pd.DataFrame) -> MatchStatistics:
    """Get or create statistics generator"""
    global _stats_generator
    
    if _stats_generator is None or _stats_generator.df is not df:
        _stats_generator = MatchStatistics(df)
        logger.info("Statistics generator initialized")
    
    return _stats_generator
