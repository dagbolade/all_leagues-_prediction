"""
Base Predictor - Abstract interface for all sports prediction systems
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path


class BaseSportPredictor(ABC):
    """
    Abstract base class for sport-specific prediction systems.

    All sport predictors (Football, Basketball, NFL) must inherit from this
    and implement all abstract methods.
    """

    def __init__(self, sport_name: str, config: Optional[Dict] = None):
        """
        Initialize base predictor.

        Args:
            sport_name: Name of the sport (e.g., 'football', 'basketball', 'nfl')
            config: Optional configuration dictionary
        """
        self.sport_name = sport_name
        self.config = config or {}
        self.models = {}
        self.feature_columns = []
        self.is_trained = False
        self.metadata = {
            'sport': sport_name,
            'version': '1.0.0',
            'created_at': None,
            'last_trained': None
        }

    @abstractmethod
    def load_data(self, data_path: Path) -> pd.DataFrame:
        """
        Load raw data from source.

        Args:
            data_path: Path to data directory or file

        Returns:
            DataFrame with raw sport data
        """
        pass

    @abstractmethod
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer sport-specific features.

        Args:
            df: Raw data DataFrame

        Returns:
            DataFrame with engineered features
        """
        pass

    @abstractmethod
    def train_models(self, df: pd.DataFrame, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train prediction models.

        Args:
            df: DataFrame with engineered features
            targets: Optional list of target variables to train for

        Returns:
            Dictionary with training results and metrics
        """
        pass

    @abstractmethod
    def predict(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make predictions for a single match/game.

        Args:
            match_info: Dictionary with match details (teams, date, etc.)

        Returns:
            Dictionary with predictions and probabilities
        """
        pass

    @abstractmethod
    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make predictions for multiple matches/games.

        Args:
            matches: List of match info dictionaries

        Returns:
            List of prediction dictionaries
        """
        pass

    @abstractmethod
    def get_insights(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sport-specific insights and analytics.

        Args:
            team: Optional team name for team-specific insights

        Returns:
            Dictionary with insights
        """
        pass

    @abstractmethod
    def validate_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Validate that prediction is logically consistent.

        Args:
            prediction: Prediction dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def save_models(self, filepath: Path) -> None:
        """
        Save trained models to disk.

        Args:
            filepath: Path to save models
        """
        import joblib
        from datetime import datetime

        self.metadata['last_saved'] = datetime.now().isoformat()

        save_data = {
            'models': self.models,
            'feature_columns': self.feature_columns,
            'metadata': self.metadata,
            'config': self.config
        }

        joblib.dump(save_data, filepath)
        print(f"[OK] {self.sport_name.title()} models saved to {filepath}")

    def load_models(self, filepath: Path) -> None:
        """
        Load trained models from disk.

        Args:
            filepath: Path to saved models
        """
        import joblib

        save_data = joblib.load(filepath)

        self.models = save_data['models']
        self.feature_columns = save_data['feature_columns']
        self.metadata = save_data['metadata']
        self.config = save_data.get('config', {})
        self.is_trained = True

        print(f"[OK] {self.sport_name.title()} models loaded from {filepath}")
        print(f"   Version: {self.metadata.get('version', 'Unknown')}")
        print(f"   Last trained: {self.metadata.get('last_trained', 'Unknown')}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            'sport': self.sport_name,
            'is_trained': self.is_trained,
            'num_models': len(self.models),
            'num_features': len(self.feature_columns),
            'metadata': self.metadata
        }

    def get_available_teams(self) -> List[str]:
        """
        Get list of available teams for this sport.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclass must implement get_available_teams()")

    def get_prediction_markets(self) -> List[str]:
        """
        Get list of prediction markets available for this sport.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclass must implement get_prediction_markets()")


class PredictionResult:
    """Standardized prediction result across all sports."""

    def __init__(self, sport: str, match_info: Dict, predictions: Dict, probabilities: Dict,
                 confidence: str, insights: Optional[Dict] = None):
        self.sport = sport
        self.match_info = match_info
        self.predictions = predictions
        self.probabilities = probabilities
        self.confidence = confidence
        self.insights = insights or {}
        self.timestamp = pd.Timestamp.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'sport': self.sport,
            'match_info': self.match_info,
            'predictions': self.predictions,
            'probabilities': self.probabilities,
            'confidence': self.confidence,
            'insights': self.insights,
            'timestamp': self.timestamp.isoformat()
        }

    def __repr__(self):
        teams = f"{self.match_info.get('home')} vs {self.match_info.get('away')}"
        return f"PredictionResult(sport={self.sport}, match={teams}, confidence={self.confidence})"
