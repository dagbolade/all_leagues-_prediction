"""
Unified Prediction Engine - Manages all sport predictors
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from core.base_predictor import BaseSportPredictor, PredictionResult


logger = logging.getLogger(__name__)


class UnifiedPredictionEngine:
    """
    Unified prediction engine that manages all sport-specific predictors.

    This is the main entry point for making predictions across all sports.
    """

    def __init__(self):
        """Initialize the unified prediction engine."""
        self.predictors: Dict[str, BaseSportPredictor] = {}
        self.loaded_sports: List[str] = []
        logger.info("Unified Prediction Engine initialized")

    def register_sport(self, sport_name: str, predictor: BaseSportPredictor) -> None:
        """
        Register a sport predictor.

        Args:
            sport_name: Name of the sport (e.g., 'football', 'basketball', 'nfl')
            predictor: Sport-specific predictor instance
        """
        self.predictors[sport_name.lower()] = predictor
        self.loaded_sports.append(sport_name.lower())
        logger.info(f"✅ Registered {sport_name} predictor")

    def get_predictor(self, sport: str) -> Optional[BaseSportPredictor]:
        """
        Get predictor for a specific sport.

        Args:
            sport: Sport name

        Returns:
            Predictor instance or None if not found
        """
        return self.predictors.get(sport.lower())

    def predict(self, sport: str, match_info: Dict[str, Any]) -> Optional[PredictionResult]:
        """
        Make a prediction for a specific sport.

        Args:
            sport: Sport name
            match_info: Match information dictionary

        Returns:
            PredictionResult or None if sport not available
        """
        predictor = self.get_predictor(sport)

        if not predictor:
            logger.error(f"❌ No predictor found for sport: {sport}")
            logger.info(f"Available sports: {self.get_available_sports()}")
            return None

        if not predictor.is_trained:
            logger.error(f"❌ {sport} predictor not trained yet")
            return None

        try:
            prediction = predictor.predict(match_info)

            # Validate prediction
            is_valid = predictor.validate_prediction(prediction)
            if not is_valid:
                logger.warning(f"⚠️ Invalid prediction for {sport}")

            return prediction

        except Exception as e:
            logger.error(f"❌ Prediction failed for {sport}: {e}")
            return None

    def predict_batch(self, sport: str, matches: List[Dict[str, Any]]) -> List[Optional[PredictionResult]]:
        """
        Make predictions for multiple matches in one sport.

        Args:
            sport: Sport name
            matches: List of match info dictionaries

        Returns:
            List of prediction results
        """
        predictor = self.get_predictor(sport)

        if not predictor:
            logger.error(f"❌ No predictor found for sport: {sport}")
            return [None] * len(matches)

        if not predictor.is_trained:
            logger.error(f"❌ {sport} predictor not trained yet")
            return [None] * len(matches)

        try:
            predictions = predictor.predict_batch(matches)
            return predictions

        except Exception as e:
            logger.error(f"❌ Batch prediction failed for {sport}: {e}")
            return [None] * len(matches)

    def get_available_sports(self) -> List[str]:
        """Get list of available sports."""
        return self.loaded_sports

    def get_sport_info(self, sport: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific sport.

        Args:
            sport: Sport name

        Returns:
            Dictionary with sport info or None
        """
        predictor = self.get_predictor(sport)

        if not predictor:
            return None

        return {
            'sport': sport,
            'is_trained': predictor.is_trained,
            'available_teams': predictor.get_available_teams() if predictor.is_trained else [],
            'prediction_markets': predictor.get_prediction_markets(),
            'model_info': predictor.get_model_info()
        }

    def get_all_sports_info(self) -> Dict[str, Any]:
        """Get information about all registered sports."""
        return {
            sport: self.get_sport_info(sport)
            for sport in self.loaded_sports
        }

    def train_sport(self, sport: str, data_path: Path) -> bool:
        """
        Train a specific sport predictor.

        Args:
            sport: Sport name
            data_path: Path to training data

        Returns:
            True if successful, False otherwise
        """
        predictor = self.get_predictor(sport)

        if not predictor:
            logger.error(f"❌ No predictor found for sport: {sport}")
            return False

        try:
            logger.info(f"🚀 Training {sport} predictor...")

            # Load data
            df = predictor.load_data(data_path)
            logger.info(f"✅ Loaded {len(df)} records for {sport}")

            # Engineer features
            df_features = predictor.engineer_features(df)
            logger.info(f"✅ Engineered features for {sport}")

            # Train models
            results = predictor.train_models(df_features)
            logger.info(f"✅ Trained {sport} models: {results}")

            predictor.is_trained = True
            return True

        except Exception as e:
            logger.error(f"❌ Training failed for {sport}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_all_models(self, base_dir: Path) -> None:
        """
        Save all trained models.

        Args:
            base_dir: Base directory for models
        """
        base_dir.mkdir(parents=True, exist_ok=True)

        for sport, predictor in self.predictors.items():
            if predictor.is_trained:
                model_path = base_dir / sport / f"{sport}_models.joblib"
                model_path.parent.mkdir(parents=True, exist_ok=True)
                predictor.save_models(model_path)

    def load_all_models(self, base_dir: Path) -> None:
        """
        Load all available models.

        Args:
            base_dir: Base directory for models
        """
        for sport, predictor in self.predictors.items():
            model_path = base_dir / sport / f"{sport}_models.joblib"

            if model_path.exists():
                predictor.load_models(model_path)
            else:
                logger.warning(f"⚠️ No saved models found for {sport} at {model_path}")

    def __repr__(self):
        return f"UnifiedPredictionEngine(sports={self.loaded_sports})"
