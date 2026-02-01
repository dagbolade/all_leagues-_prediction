"""
Live Match Tracker

Tracks live matches and provides real-time updates with prediction comparisons.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from app.services.live_scores_service import get_live_scores_service

logger = logging.getLogger(__name__)


class LiveMatchTracker:
    """Track and analyze live matches"""
    
    def __init__(self):
        self.live_scores_service = get_live_scores_service()
        self.tracked_matches = {}
        self.predictions_cache = {}
    
    def get_live_matches_with_predictions(self) -> List[Dict[str, Any]]:
        """Get live matches with prediction comparisons"""
        try:
            # Get live matches
            live_matches = self.live_scores_service.get_live_matches()
            
            enriched_matches = []
            for match in live_matches:
                enriched = self._enrich_match_data(match)
                enriched_matches.append(enriched)
            
            return enriched_matches
            
        except Exception as e:
            logger.error(f"Error getting live matches: {e}")
            return []
    
    def _enrich_match_data(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich match data with additional analysis"""
        enriched = match.copy()
        
        # Add match status analysis
        enriched['analysis'] = self._analyze_match_status(match)
        
        # Add prediction comparison if available
        match_key = f"{match.get('home_team', '')}_{match.get('away_team', '')}"
        if match_key in self.predictions_cache:
            enriched['prediction_comparison'] = self._compare_with_prediction(
                match,
                self.predictions_cache[match_key]
            )
        
        return enriched
    
    def _analyze_match_status(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current match status"""
        home_score = match.get('home_score', 0)
        away_score = match.get('away_score', 0)
        minute = match.get('minute', 0)
        
        analysis = {
            'total_goals': home_score + away_score,
            'goal_difference': abs(home_score - away_score),
            'leading_team': None,
            'match_tempo': self._calculate_tempo(home_score + away_score, minute),
            'predictions': []
        }
        
        # Determine leading team
        if home_score > away_score:
            analysis['leading_team'] = 'home'
        elif away_score > home_score:
            analysis['leading_team'] = 'away'
        else:
            analysis['leading_team'] = 'draw'
        
        # Live predictions
        if minute > 0:
            analysis['predictions'] = self._generate_live_predictions(
                home_score, away_score, minute
            )
        
        return analysis
    
    def _calculate_tempo(self, total_goals: int, minute: int) -> str:
        """Calculate match tempo based on goals and time"""
        if minute == 0:
            return 'Not started'
        
        goals_per_minute = total_goals / minute if minute > 0 else 0
        
        if goals_per_minute > 0.05:  # More than 1 goal per 20 minutes
            return 'High'
        elif goals_per_minute > 0.025:  # More than 1 goal per 40 minutes
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_live_predictions(self,
                                   home_score: int,
                                   away_score: int,
                                   minute: int) -> List[str]:
        """Generate live match predictions"""
        predictions = []
        total_goals = home_score + away_score
        
        # Over/Under predictions
        if minute < 60:
            if total_goals >= 2:
                predictions.append("✅ Over 2.5 Goals looking likely")
            elif total_goals == 1:
                predictions.append("⚠️ Over 2.5 Goals still possible")
            else:
                predictions.append("❌ Over 2.5 Goals unlikely")
        
        # BTTS predictions
        if home_score > 0 and away_score > 0:
            predictions.append("✅ Both Teams to Score - YES")
        elif minute > 70:
            if home_score == 0 or away_score == 0:
                predictions.append("❌ Both Teams to Score - NO likely")
        
        # Match outcome
        if minute > 75:
            if home_score > away_score:
                predictions.append(f"🏠 Home Win likely (leading {home_score}-{away_score})")
            elif away_score > home_score:
                predictions.append(f"✈️ Away Win likely (leading {away_score}-{home_score})")
            else:
                predictions.append("🤝 Draw currently")
        
        return predictions
    
    def _compare_with_prediction(self,
                                match: Dict[str, Any],
                                prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Compare live match with pre-match prediction"""
        home_score = match.get('home_score', 0)
        away_score = match.get('away_score', 0)
        
        comparison = {
            'match_outcome': self._check_outcome_prediction(
                home_score, away_score, prediction
            ),
            'goals': self._check_goals_prediction(
                home_score + away_score, prediction
            ),
            'btts': self._check_btts_prediction(
                home_score, away_score, prediction
            )
        }
        
        return comparison
    
    def _check_outcome_prediction(self,
                                 home_score: int,
                                 away_score: int,
                                 prediction: Dict) -> str:
        """Check if match outcome matches prediction"""
        predicted_outcome = prediction.get('predictions', {}).get('Match Outcome', '')
        
        if home_score > away_score:
            actual = 'Home Win'
        elif away_score > home_score:
            actual = 'Away Win'
        else:
            actual = 'Draw'
        
        if predicted_outcome == actual:
            return f"✅ Correct - Predicted {predicted_outcome}"
        else:
            return f"❌ Incorrect - Predicted {predicted_outcome}, Actual {actual}"
    
    def _check_goals_prediction(self, total_goals: int, prediction: Dict) -> str:
        """Check if goals prediction is correct"""
        over_25 = prediction.get('predictions', {}).get('Over 2.5 Goals', '')
        
        if over_25 == 'Yes' and total_goals > 2.5:
            return "✅ Over 2.5 Goals - Correct"
        elif over_25 == 'No' and total_goals <= 2.5:
            return "✅ Under 2.5 Goals - Correct"
        elif over_25:
            return f"❌ Predicted {over_25}, Actual {total_goals} goals"
        else:
            return "No prediction available"
    
    def _check_btts_prediction(self,
                              home_score: int,
                              away_score: int,
                              prediction: Dict) -> str:
        """Check if BTTS prediction is correct"""
        btts_pred = prediction.get('predictions', {}).get('Both Teams to Score', '')
        
        both_scored = home_score > 0 and away_score > 0
        
        if btts_pred == 'Yes' and both_scored:
            return "✅ BTTS Yes - Correct"
        elif btts_pred == 'No' and not both_scored:
            return "✅ BTTS No - Correct"
        elif btts_pred:
            return f"❌ Predicted BTTS {btts_pred}"
        else:
            return "No prediction available"
    
    def add_prediction_for_tracking(self,
                                   home_team: str,
                                   away_team: str,
                                   prediction: Dict[str, Any]):
        """Add a prediction to track against live match"""
        match_key = f"{home_team}_{away_team}"
        self.predictions_cache[match_key] = prediction
        logger.info(f"Added prediction for tracking: {match_key}")
    
    def get_match_timeline(self, match_id: str) -> List[Dict[str, Any]]:
        """Get match timeline with key events"""
        # This would integrate with a detailed match API
        # For now, return placeholder
        return [
            {
                'minute': 0,
                'event': 'Kick-off',
                'description': 'Match started'
            }
        ]


# Global instance
_live_tracker = None


def get_live_tracker() -> LiveMatchTracker:
    """Get or create live match tracker (singleton)"""
    global _live_tracker
    
    if _live_tracker is None:
        _live_tracker = LiveMatchTracker()
        logger.info("Live match tracker initialized")
    
    return _live_tracker
