"""
Accumulator Builder

Builds multi-match accumulator bets with combined odds and risk analysis.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AccumulatorBuilder:
    """Build and analyze accumulator bets"""
    
    def __init__(self):
        self.selections = []
        self.max_selections = 15
    
    def add_selection(self,
                     home_team: str,
                     away_team: str,
                     market: str,
                     selection: str,
                     odds: float,
                     confidence: float) -> Dict[str, Any]:
        """
        Add a selection to the accumulator
        
        Args:
            home_team: Home team name
            away_team: Away team name
            market: Betting market (e.g., "Match Winner", "Over 2.5 Goals")
            selection: Specific selection (e.g., "Home Win", "Yes")
            odds: Decimal odds
            confidence: Confidence level (0-1)
        
        Returns:
            Updated accumulator details
        """
        if len(self.selections) >= self.max_selections:
            return {
                'status': 'error',
                'message': f'Maximum {self.max_selections} selections allowed'
            }
        
        selection_data = {
            'id': len(self.selections) + 1,
            'match': f"{home_team} vs {away_team}",
            'home_team': home_team,
            'away_team': away_team,
            'market': market,
            'selection': selection,
            'odds': odds,
            'confidence': confidence,
            'added_at': datetime.utcnow().isoformat()
        }
        
        self.selections.append(selection_data)
        
        return {
            'status': 'success',
            'selection': selection_data,
            'accumulator': self.get_accumulator_details()
        }
    
    def remove_selection(self, selection_id: int) -> Dict[str, Any]:
        """Remove a selection from the accumulator"""
        self.selections = [s for s in self.selections if s['id'] != selection_id]
        
        # Re-number selections
        for i, selection in enumerate(self.selections):
            selection['id'] = i + 1
        
        return {
            'status': 'success',
            'accumulator': self.get_accumulator_details()
        }
    
    def clear_selections(self):
        """Clear all selections"""
        self.selections = []
    
    def get_accumulator_details(self) -> Dict[str, Any]:
        """Get detailed accumulator analysis"""
        if not self.selections:
            return {
                'num_selections': 0,
                'total_odds': 0,
                'combined_confidence': 0,
                'risk_level': 'N/A',
                'selections': []
            }
        
        # Calculate combined odds
        total_odds = 1.0
        for selection in self.selections:
            total_odds *= selection['odds']
        
        # Calculate combined confidence (probability all win)
        combined_confidence = 1.0
        for selection in self.selections:
            combined_confidence *= selection['confidence']
        
        # Calculate risk level
        risk_level = self._calculate_risk_level(
            len(self.selections),
            combined_confidence
        )
        
        # Calculate expected value
        stake = 10  # Default stake for calculation
        potential_return = stake * total_odds
        expected_value = potential_return * combined_confidence
        
        return {
            'num_selections': len(self.selections),
            'total_odds': round(total_odds, 2),
            'combined_confidence': round(combined_confidence * 100, 2),
            'risk_level': risk_level,
            'potential_return': round(potential_return, 2),
            'expected_value': round(expected_value, 2),
            'selections': self.selections,
            'recommendations': self._get_recommendations(
                len(self.selections),
                combined_confidence,
                total_odds
            )
        }
    
    def _calculate_risk_level(self, num_selections: int, confidence: float) -> str:
        """Calculate risk level based on selections and confidence"""
        if num_selections == 1:
            if confidence >= 0.7:
                return 'Low'
            elif confidence >= 0.5:
                return 'Medium'
            else:
                return 'High'
        elif num_selections <= 3:
            if confidence >= 0.5:
                return 'Medium'
            elif confidence >= 0.3:
                return 'Medium-High'
            else:
                return 'High'
        elif num_selections <= 5:
            if confidence >= 0.3:
                return 'Medium-High'
            elif confidence >= 0.15:
                return 'High'
            else:
                return 'Very High'
        else:
            if confidence >= 0.15:
                return 'High'
            else:
                return 'Very High'
    
    def _get_recommendations(self,
                           num_selections: int,
                           confidence: float,
                           odds: float) -> List[str]:
        """Get recommendations for the accumulator"""
        recommendations = []
        
        if num_selections == 0:
            recommendations.append("Add selections to build your accumulator")
            return recommendations
        
        if num_selections == 1:
            recommendations.append("Single bet - consider adding more selections for higher returns")
        
        if num_selections > 8:
            recommendations.append("⚠️ Large accumulator - very difficult to win")
            recommendations.append("Consider splitting into smaller accumulators")
        
        if confidence < 0.1:
            recommendations.append("⚠️ Very low probability of winning")
            recommendations.append("Reduce number of selections or choose higher confidence bets")
        elif confidence < 0.2:
            recommendations.append("⚠️ Low probability - high risk accumulator")
        elif confidence >= 0.4:
            recommendations.append("✅ Good confidence level for an accumulator")
        
        if odds > 100:
            recommendations.append("💰 Very high potential returns")
            recommendations.append("Consider reducing stake due to low probability")
        elif odds > 20:
            recommendations.append("💰 High potential returns")
        
        if num_selections >= 3 and num_selections <= 5:
            recommendations.append("✅ Good accumulator size - balanced risk/reward")
        
        # Value assessment
        expected_value_ratio = confidence * odds
        if expected_value_ratio > 1.5:
            recommendations.append("⭐ Good value accumulator")
        elif expected_value_ratio < 0.8:
            recommendations.append("⚠️ Poor value - odds don't justify the risk")
        
        return recommendations
    
    def get_suggested_stake(self, bankroll: float = 100) -> Dict[str, Any]:
        """Get suggested stake based on Kelly Criterion"""
        if not self.selections:
            return {'suggested_stake': 0, 'reasoning': 'No selections'}
        
        details = self.get_accumulator_details()
        confidence = details['combined_confidence'] / 100
        odds = details['total_odds']
        
        # Kelly Criterion: f = (bp - q) / b
        # where b = odds - 1, p = probability, q = 1 - p
        b = odds - 1
        p = confidence
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        
        # Use fractional Kelly (25% of full Kelly for safety)
        safe_kelly = kelly_fraction * 0.25
        
        # Ensure stake is between 1-10% of bankroll
        suggested_stake = max(0.01, min(0.10, safe_kelly)) * bankroll
        
        return {
            'suggested_stake': round(suggested_stake, 2),
            'percentage_of_bankroll': round((suggested_stake / bankroll) * 100, 2),
            'reasoning': self._get_stake_reasoning(safe_kelly, confidence, odds)
        }
    
    def _get_stake_reasoning(self, kelly: float, confidence: float, odds: float) -> str:
        """Get reasoning for stake suggestion"""
        if kelly <= 0:
            return "No value in this bet - not recommended"
        elif kelly < 0.02:
            return "Very small edge - minimal stake recommended"
        elif kelly < 0.05:
            return "Small edge - conservative stake recommended"
        elif kelly < 0.10:
            return "Moderate edge - reasonable stake recommended"
        else:
            return "Strong edge - higher stake justified (but capped for safety)"


# Global instance
_accumulator_builder = None


def get_accumulator_builder() -> AccumulatorBuilder:
    """Get or create accumulator builder (singleton)"""
    global _accumulator_builder
    
    if _accumulator_builder is None:
        _accumulator_builder = AccumulatorBuilder()
        logger.info("Accumulator builder initialized")
    
    return _accumulator_builder
