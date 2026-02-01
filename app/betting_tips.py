"""
Betting Tips Generator

Generates actionable betting tips based on Bayesian predictions and probabilities.
Provides value bets, confidence ratings, and risk assessments.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BettingTipsGenerator:
    """Generate intelligent betting tips from predictions"""
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.70
    MEDIUM_CONFIDENCE = 0.60
    LOW_CONFIDENCE = 0.50
    
    # Value bet thresholds
    VALUE_THRESHOLD = 0.15  # 15% edge
    
    def __init__(self):
        self.tips = []
    
    def generate_tips(self, 
                     predictions: Dict[str, Any],
                     probabilities: Dict[str, Any],
                     home_team: str,
                     away_team: str) -> List[Dict[str, Any]]:
        """
        Generate betting tips from predictions
        
        Args:
            predictions: Prediction results
            probabilities: Probability estimates
            home_team: Home team name
            away_team: Away team name
        
        Returns:
            List of betting tip dictionaries
        """
        tips = []
        
        # Match Winner Tips
        match_tips = self._analyze_match_winner(predictions, probabilities, home_team, away_team)
        tips.extend(match_tips)
        
        # Over/Under Tips
        goals_tips = self._analyze_goals_markets(predictions, probabilities)
        tips.extend(goals_tips)
        
        # Both Teams to Score
        btts_tips = self._analyze_btts(predictions, probabilities)
        tips.extend(btts_tips)
        
        # Poisson Scorelines
        if 'poisson_analysis' in probabilities:
            scoreline_tips = self._analyze_scorelines(probabilities['poisson_analysis'])
            tips.extend(scoreline_tips)
        
        # Sort by confidence
        tips.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return tips
    
    def _analyze_match_winner(self, predictions, probabilities, home_team, away_team) -> List[Dict]:
        """Analyze match winner market"""
        tips = []
        
        match_outcome = predictions.get('Match Outcome')
        match_probs = probabilities.get('Match Outcome', {})
        
        if isinstance(match_probs, dict):
            home_prob = match_probs.get('Home Win', 0)
            draw_prob = match_probs.get('Draw', 0)
            away_prob = match_probs.get('Away Win', 0)
            
            # High confidence home win
            if home_prob >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Match Winner',
                    'tip': f'{home_team} to Win',
                    'confidence': 'High',
                    'confidence_score': home_prob,
                    'probability': f'{home_prob:.1%}',
                    'reasoning': f'{home_team} has a {home_prob:.0%} chance of winning based on Bayesian analysis',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(home_prob, 1.0 / home_prob)
                })
            
            # High confidence away win
            elif away_prob >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Match Winner',
                    'tip': f'{away_team} to Win',
                    'confidence': 'High',
                    'confidence_score': away_prob,
                    'probability': f'{away_prob:.1%}',
                    'reasoning': f'{away_team} has a {away_prob:.0%} chance of winning',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(away_prob, 1.0 / away_prob)
                })
            
            # Medium confidence predictions
            elif home_prob >= self.MEDIUM_CONFIDENCE:
                tips.append({
                    'market': 'Match Winner',
                    'tip': f'{home_team} to Win',
                    'confidence': 'Medium',
                    'confidence_score': home_prob,
                    'probability': f'{home_prob:.1%}',
                    'reasoning': f'Moderate confidence in {home_team} victory',
                    'risk': 'Medium',
                    'value_rating': self._calculate_value_rating(home_prob, 1.0 / home_prob)
                })
            
            # Draw value bet
            if draw_prob >= 0.30 and draw_prob < 0.40:
                tips.append({
                    'market': 'Match Winner',
                    'tip': 'Draw',
                    'confidence': 'Medium',
                    'confidence_score': draw_prob,
                    'probability': f'{draw_prob:.1%}',
                    'reasoning': 'Evenly matched teams suggest draw potential',
                    'risk': 'Medium',
                    'value_rating': self._calculate_value_rating(draw_prob, 1.0 / draw_prob)
                })
        
        return tips
    
    def _analyze_goals_markets(self, predictions, probabilities) -> List[Dict]:
        """Analyze over/under goals markets"""
        tips = []
        
        # Over 2.5 Goals
        over_25_pred = predictions.get('Over 2.5 Goals')
        over_25_prob = probabilities.get('Over 2.5 Goals', 0)
        
        if isinstance(over_25_prob, (int, float)):
            if over_25_pred == 'Yes' and over_25_prob >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Total Goals',
                    'tip': 'Over 2.5 Goals',
                    'confidence': 'High',
                    'confidence_score': over_25_prob,
                    'probability': f'{over_25_prob:.1%}',
                    'reasoning': f'High-scoring match expected ({over_25_prob:.0%} probability)',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(over_25_prob, 1.0 / over_25_prob)
                })
            elif over_25_pred == 'No' and (1 - over_25_prob) >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Total Goals',
                    'tip': 'Under 2.5 Goals',
                    'confidence': 'High',
                    'confidence_score': 1 - over_25_prob,
                    'probability': f'{(1 - over_25_prob):.1%}',
                    'reasoning': f'Low-scoring match expected ({(1 - over_25_prob):.0%} probability)',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(1 - over_25_prob, 1.0 / (1 - over_25_prob))
                })
        
        # Over 1.5 Goals
        over_15_pred = predictions.get('Over 1.5 Goals')
        over_15_prob = probabilities.get('Over 1.5 Goals', 0)
        
        if isinstance(over_15_prob, (int, float)):
            if over_15_pred == 'Yes' and over_15_prob >= 0.80:
                tips.append({
                    'market': 'Total Goals',
                    'tip': 'Over 1.5 Goals',
                    'confidence': 'Very High',
                    'confidence_score': over_15_prob,
                    'probability': f'{over_15_prob:.1%}',
                    'reasoning': f'Very likely to see at least 2 goals ({over_15_prob:.0%})',
                    'risk': 'Very Low',
                    'value_rating': self._calculate_value_rating(over_15_prob, 1.0 / over_15_prob)
                })
        
        # Over 3.5 Goals
        over_35_pred = predictions.get('Over 3.5 Goals')
        over_35_prob = probabilities.get('Over 3.5 Goals', 0)
        
        if isinstance(over_35_prob, (int, float)):
            if over_35_pred == 'Yes' and over_35_prob >= self.MEDIUM_CONFIDENCE:
                tips.append({
                    'market': 'Total Goals',
                    'tip': 'Over 3.5 Goals',
                    'confidence': 'Medium',
                    'confidence_score': over_35_prob,
                    'probability': f'{over_35_prob:.1%}',
                    'reasoning': 'Goal-fest potential in this matchup',
                    'risk': 'Medium-High',
                    'value_rating': self._calculate_value_rating(over_35_prob, 1.0 / over_35_prob)
                })
        
        return tips
    
    def _analyze_btts(self, predictions, probabilities) -> List[Dict]:
        """Analyze Both Teams to Score market"""
        tips = []
        
        btts_pred = predictions.get('Both Teams to Score')
        btts_prob = probabilities.get('Both Teams to Score', 0)
        
        if isinstance(btts_prob, (int, float)):
            if btts_pred == 'Yes' and btts_prob >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Both Teams to Score',
                    'tip': 'Yes',
                    'confidence': 'High',
                    'confidence_score': btts_prob,
                    'probability': f'{btts_prob:.1%}',
                    'reasoning': f'Both teams likely to score ({btts_prob:.0%} probability)',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(btts_prob, 1.0 / btts_prob)
                })
            elif btts_pred == 'No' and (1 - btts_prob) >= self.HIGH_CONFIDENCE:
                tips.append({
                    'market': 'Both Teams to Score',
                    'tip': 'No',
                    'confidence': 'High',
                    'confidence_score': 1 - btts_prob,
                    'probability': f'{(1 - btts_prob):.1%}',
                    'reasoning': f'Clean sheet likely ({(1 - btts_prob):.0%} probability)',
                    'risk': 'Low',
                    'value_rating': self._calculate_value_rating(1 - btts_prob, 1.0 / (1 - btts_prob))
                })
        
        return tips
    
    def _analyze_scorelines(self, poisson_analysis) -> List[Dict]:
        """Analyze exact scoreline predictions"""
        tips = []
        
        if not poisson_analysis or 'top_scorelines' not in poisson_analysis:
            return tips
        
        top_scorelines = poisson_analysis['top_scorelines']
        
        if top_scorelines and len(top_scorelines) > 0:
            # Most likely scoreline
            top_score = top_scorelines[0]
            if top_score['probability'] >= 10:  # At least 10% probability
                tips.append({
                    'market': 'Correct Score',
                    'tip': top_score['score'],
                    'confidence': 'Medium',
                    'confidence_score': top_score['probability'] / 100,
                    'probability': f"{top_score['probability']}%",
                    'reasoning': f"Most likely scoreline based on Poisson distribution",
                    'risk': 'High',
                    'value_rating': '⭐⭐⭐'
                })
        
        return tips
    
    def _calculate_value_rating(self, probability: float, implied_odds: float) -> str:
        """Calculate value rating (stars)"""
        # This is simplified - in production, compare with actual bookmaker odds
        if probability >= 0.75:
            return '⭐⭐⭐⭐⭐'
        elif probability >= 0.65:
            return '⭐⭐⭐⭐'
        elif probability >= 0.55:
            return '⭐⭐⭐'
        elif probability >= 0.45:
            return '⭐⭐'
        else:
            return '⭐'
    
    def format_tips_for_display(self, tips: List[Dict]) -> Dict[str, List[Dict]]:
        """Format tips grouped by confidence level"""
        formatted = {
            'high_confidence': [],
            'medium_confidence': [],
            'value_bets': []
        }
        
        for tip in tips:
            if tip['confidence'] in ['High', 'Very High']:
                formatted['high_confidence'].append(tip)
            elif tip['confidence'] == 'Medium':
                formatted['medium_confidence'].append(tip)
            
            # Value bets are those with good probability but higher odds
            if tip['value_rating'] in ['⭐⭐⭐⭐⭐', '⭐⭐⭐⭐']:
                formatted['value_bets'].append(tip)
        
        return formatted


# Global instance
_betting_tips_generator = None


def get_betting_tips_generator() -> BettingTipsGenerator:
    """Get or create betting tips generator (singleton)"""
    global _betting_tips_generator
    
    if _betting_tips_generator is None:
        _betting_tips_generator = BettingTipsGenerator()
        logger.info("Betting tips generator initialized")
    
    return _betting_tips_generator
