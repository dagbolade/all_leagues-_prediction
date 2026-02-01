"""
League Table Predictor

Predicts final league standings based on remaining fixtures and team form.
"""

from typing import List, Dict, Any, Optional
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class LeagueTablePredictor:
    """Predict league table outcomes"""
    
    def __init__(self, predictor=None):
        """
        Initialize league table predictor
        
        Args:
            predictor: Football predictor instance for match predictions
        """
        self.predictor = predictor
        self.league_data = {}
    
    def predict_league_table(self,
                            league: str,
                            current_standings: List[Dict[str, Any]],
                            remaining_fixtures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict final league table
        
        Args:
            league: League name
            current_standings: Current league standings
            remaining_fixtures: List of remaining fixtures
        
        Returns:
            Predicted final table with probabilities
        """
        try:
            # Initialize table with current standings
            predicted_table = self._initialize_table(current_standings)
            
            # Simulate remaining fixtures
            simulations = self._run_simulations(
                predicted_table,
                remaining_fixtures,
                num_simulations=1000
            )
            
            # Calculate final predictions
            final_predictions = self._calculate_final_predictions(simulations)
            
            return {
                'status': 'success',
                'league': league,
                'current_standings': current_standings,
                'predicted_table': final_predictions['table'],
                'probabilities': final_predictions['probabilities'],
                'insights': self._generate_insights(
                    current_standings,
                    final_predictions['table']
                )
            }
            
        except Exception as e:
            logger.error(f"League prediction error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _initialize_table(self, standings: List[Dict[str, Any]]) -> pd.DataFrame:
        """Initialize table DataFrame from current standings"""
        df = pd.DataFrame(standings)
        
        # Ensure required columns
        required_cols = ['team', 'played', 'won', 'drawn', 'lost', 
                        'goals_for', 'goals_against', 'points']
        
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
        
        return df
    
    def _run_simulations(self,
                        table: pd.DataFrame,
                        fixtures: List[Dict[str, Any]],
                        num_simulations: int = 1000) -> List[pd.DataFrame]:
        """Run Monte Carlo simulations of remaining fixtures"""
        simulations = []
        
        for _ in range(num_simulations):
            sim_table = table.copy()
            
            for fixture in fixtures:
                home_team = fixture['home_team']
                away_team = fixture['away_team']
                
                # Get match prediction
                result = self._predict_match_outcome(home_team, away_team)
                
                # Update table based on result
                sim_table = self._update_table(sim_table, home_team, away_team, result)
            
            simulations.append(sim_table)
        
        return simulations
    
    def _predict_match_outcome(self, home_team: str, away_team: str) -> str:
        """Predict match outcome (Home/Draw/Away)"""
        if self.predictor:
            try:
                # Get prediction from main predictor
                prediction = self.predictor.predict_with_full_bayesian_analysis(
                    home_team, away_team
                )
                
                outcome = prediction.get('predictions', {}).get('Match Outcome', '')
                
                # Map to Home/Draw/Away
                if 'Home' in outcome:
                    return 'Home'
                elif 'Draw' in outcome:
                    return 'Draw'
                else:
                    return 'Away'
                    
            except:
                pass
        
        # Fallback to simple probability
        import random
        rand = random.random()
        
        if rand < 0.45:  # 45% home win
            return 'Home'
        elif rand < 0.75:  # 30% draw
            return 'Draw'
        else:  # 25% away win
            return 'Away'
    
    def _update_table(self,
                     table: pd.DataFrame,
                     home_team: str,
                     away_team: str,
                     result: str) -> pd.DataFrame:
        """Update table based on match result"""
        # Simulate scoreline based on result
        if result == 'Home':
            home_goals, away_goals = 2, 0
        elif result == 'Away':
            home_goals, away_goals = 0, 2
        else:  # Draw
            home_goals, away_goals = 1, 1
        
        # Update home team
        if home_team in table['team'].values:
            idx = table[table['team'] == home_team].index[0]
            table.at[idx, 'played'] += 1
            table.at[idx, 'goals_for'] += home_goals
            table.at[idx, 'goals_against'] += away_goals
            
            if result == 'Home':
                table.at[idx, 'won'] += 1
                table.at[idx, 'points'] += 3
            elif result == 'Draw':
                table.at[idx, 'drawn'] += 1
                table.at[idx, 'points'] += 1
            else:
                table.at[idx, 'lost'] += 1
        
        # Update away team
        if away_team in table['team'].values:
            idx = table[table['team'] == away_team].index[0]
            table.at[idx, 'played'] += 1
            table.at[idx, 'goals_for'] += away_goals
            table.at[idx, 'goals_against'] += home_goals
            
            if result == 'Away':
                table.at[idx, 'won'] += 1
                table.at[idx, 'points'] += 3
            elif result == 'Draw':
                table.at[idx, 'drawn'] += 1
                table.at[idx, 'points'] += 1
            else:
                table.at[idx, 'lost'] += 1
        
        return table
    
    def _calculate_final_predictions(self,
                                    simulations: List[pd.DataFrame]) -> Dict[str, Any]:
        """Calculate final predictions from simulations"""
        # Average points for each team
        all_teams = simulations[0]['team'].tolist()
        
        final_table = []
        probabilities = {}
        
        for team in all_teams:
            team_points = []
            team_positions = []
            
            for sim in simulations:
                # Get team's points in this simulation
                team_row = sim[sim['team'] == team]
                if not team_row.empty:
                    points = team_row.iloc[0]['points']
                    team_points.append(points)
                    
                    # Sort simulation table to get position
                    sorted_sim = sim.sort_values('points', ascending=False).reset_index(drop=True)
                    position = sorted_sim[sorted_sim['team'] == team].index[0] + 1
                    team_positions.append(position)
            
            avg_points = sum(team_points) / len(team_points) if team_points else 0
            avg_position = sum(team_positions) / len(team_positions) if team_positions else 0
            
            # Calculate position probabilities
            position_probs = {}
            for pos in range(1, len(all_teams) + 1):
                prob = sum(1 for p in team_positions if p == pos) / len(team_positions) if team_positions else 0
                position_probs[pos] = round(prob * 100, 1)
            
            final_table.append({
                'team': team,
                'predicted_points': round(avg_points, 1),
                'predicted_position': round(avg_position, 1),
                'current_points': simulations[0][simulations[0]['team'] == team].iloc[0]['points']
            })
            
            probabilities[team] = {
                'top_4': round(sum(1 for p in team_positions if p <= 4) / len(team_positions) * 100, 1) if team_positions else 0,
                'top_6': round(sum(1 for p in team_positions if p <= 6) / len(team_positions) * 100, 1) if team_positions else 0,
                'relegation': round(sum(1 for p in team_positions if p >= len(all_teams) - 2) / len(team_positions) * 100, 1) if team_positions else 0,
                'position_distribution': position_probs
            }
        
        # Sort by predicted points
        final_table.sort(key=lambda x: x['predicted_points'], reverse=True)
        
        return {
            'table': final_table,
            'probabilities': probabilities
        }
    
    def _generate_insights(self,
                          current: List[Dict[str, Any]],
                          predicted: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from predictions"""
        insights = []
        
        # Find biggest movers
        for pred_team in predicted[:5]:  # Top 5 predicted
            team_name = pred_team['team']
            
            # Find current position
            current_pos = next(
                (i + 1 for i, t in enumerate(current) if t.get('team') == team_name),
                None
            )
            
            if current_pos:
                pred_pos = predicted.index(pred_team) + 1
                movement = current_pos - pred_pos
                
                if movement > 2:
                    insights.append(f"📈 {team_name} predicted to climb {movement} positions")
                elif movement < -2:
                    insights.append(f"📉 {team_name} predicted to drop {abs(movement)} positions")
        
        # Championship/relegation battles
        top_team = predicted[0]['team']
        insights.append(f"🏆 {top_team} favorites for the title")
        
        bottom_teams = [t['team'] for t in predicted[-3:]]
        insights.append(f"⚠️ Relegation battle: {', '.join(bottom_teams)}")
        
        return insights


# Global instance
_league_predictor = None


def get_league_predictor(predictor=None) -> LeagueTablePredictor:
    """Get or create league table predictor"""
    global _league_predictor
    
    if _league_predictor is None:
        _league_predictor = LeagueTablePredictor(predictor)
        logger.info("League table predictor initialized")
    
    return _league_predictor
