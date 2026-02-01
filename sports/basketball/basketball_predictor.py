"""
Basketball Predictor - NBA prediction system

Inherits from BaseSportPredictor and implements basketball-specific logic.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
sys.path.append('../..')

from core.base_predictor import BaseSportPredictor, PredictionResult
from sports.basketball.basketball_features import BasketballFeatureEngineer

# ML imports
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib


class BasketballPredictor(BaseSportPredictor):
    """NBA prediction system."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('basketball', config)
        self.feature_engineer = BasketballFeatureEngineer()
        self.scaler = StandardScaler()
        self.teams = []

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """
        Load basketball data from files.

        Args:
            data_path: Path to data directory or CSV file

        Returns:
            DataFrame with basketball data
        """
        print("Loading basketball data...")

        if data_path.is_file():
            # Single file
            if data_path.suffix == '.csv':
                df = pd.read_csv(data_path)
            elif data_path.suffix == '.xlsx':
                df = pd.read_excel(data_path)
            else:
                raise ValueError(f"Unsupported file format: {data_path.suffix}")

        elif data_path.is_dir():
            # Directory with multiple files
            all_files = list(data_path.glob('*.csv'))
            dfs = [pd.read_csv(f) for f in all_files]
            df = pd.concat(dfs, ignore_index=True)

        else:
            raise FileNotFoundError(f"Data path not found: {data_path}")

        # Standardize columns
        df = self._standardize_columns(df)

        # Get unique teams
        self.teams = sorted(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique()))

        print(f"Loaded {len(df)} basketball games")
        print(f"Found {len(self.teams)} teams")

        return df

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names."""
        # Ensure required columns exist
        required = ['Date', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore']

        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Add Result column if not exists
        if 'Result' not in df.columns:
            df['Result'] = 'H'
            df.loc[df['AwayScore'] > df['HomeScore'], 'Result'] = 'A'
            df.loc[df['AwayScore'] == df['HomeScore'], 'Result'] = 'D'

        # Ensure Date is datetime
        df['Date'] = pd.to_datetime(df['Date'])

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer basketball-specific features.

        Args:
            df: Raw data DataFrame

        Returns:
            DataFrame with engineered features
        """
        return self.feature_engineer.engineer_features(df)

    def train_models(self, df: pd.DataFrame, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train basketball prediction models.

        Args:
            df: DataFrame with engineered features
            targets: Optional list of targets (default: ['Result'])

        Returns:
            Dictionary with training results
        """
        print("Training basketball models...")

        targets = targets or ['Result']

        # Prepare features
        feature_cols = self.feature_engineer.get_feature_names()
        feature_cols = [col for col in feature_cols if col in df.columns]

        self.feature_columns = feature_cols

        # Remove rows with NaN in features
        df_clean = df.dropna(subset=feature_cols)

        X = df_clean[feature_cols]
        y = df_clean['Result']

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train models
        print("Training Random Forest...")
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_model.fit(X_train_scaled, y_train)

        print("Training Gradient Boosting...")
        gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        gb_model.fit(X_train_scaled, y_train)

        # Store models
        self.models['match_outcome_rf'] = rf_model
        self.models['match_outcome_gb'] = gb_model

        # Calculate accuracy
        rf_accuracy = rf_model.score(X_test_scaled, y_test)
        gb_accuracy = gb_model.score(X_test_scaled, y_test)

        print(f"Random Forest Accuracy: {rf_accuracy:.3f}")
        print(f"Gradient Boosting Accuracy: {gb_accuracy:.3f}")

        self.is_trained = True
        self.metadata['last_trained'] = datetime.now().isoformat()

        return {
            'rf_accuracy': rf_accuracy,
            'gb_accuracy': gb_accuracy,
            'num_features': len(feature_cols),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }

    def predict(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict basketball game outcome.

        Args:
            match_info: Dictionary with 'home' and 'away' team names

        Returns:
            Dictionary with predictions and probabilities
        """
        if not self.is_trained:
            raise ValueError("Models not trained yet")

        home_team = match_info['home']
        away_team = match_info['away']

        # TODO: Build feature vector for the match
        # For now, return placeholder

        prediction = {
            'match_info': match_info,
            'predictions': {
                'Winner': home_team,  # Placeholder
                'Spread': -5.5,
                'Total Points': 'Over 210.5'
            },
            'probabilities': {
                'Home Win': 0.65,
                'Away Win': 0.35
            },
            'confidence': 'Medium'
        }

        return prediction

    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict multiple basketball games.

        Args:
            matches: List of match info dictionaries

        Returns:
            List of prediction dictionaries
        """
        return [self.predict(match) for match in matches]

    def get_insights(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Get basketball insights.

        Args:
            team: Optional team name for team-specific insights

        Returns:
            Dictionary with insights
        """
        insights = {
            'sport': 'basketball',
            'teams_available': len(self.teams)
        }

        if team:
            insights['team'] = team
            insights['stats'] = 'Coming soon'

        return insights

    def validate_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Validate basketball prediction.

        Args:
            prediction: Prediction dictionary

        Returns:
            True if valid
        """
        # Basic validation
        required_keys = ['match_info', 'predictions', 'probabilities']

        return all(key in prediction for key in required_keys)

    def get_available_teams(self) -> List[str]:
        """Get list of NBA teams."""
        return self.teams

    def get_prediction_markets(self) -> List[str]:
        """Get available prediction markets for basketball."""
        return [
            'Winner (Moneyline)',
            'Point Spread',
            'Total Points (Over/Under)',
            'First Half Winner',
            'First Quarter Winner'
        ]
