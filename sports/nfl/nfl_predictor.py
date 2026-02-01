"""
NFL Predictor - American Football prediction system

Inherits from BaseSportPredictor and implements NFL-specific logic.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
sys.path.append('../..')

from core.base_predictor import BaseSportPredictor, PredictionResult
from sports.nfl.nfl_features import NFLFeatureEngineer

# ML imports
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib


class NFLPredictor(BaseSportPredictor):
    """NFL prediction system."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('nfl', config)
        self.feature_engineer = NFLFeatureEngineer()
        self.scaler = StandardScaler()
        self.teams = []

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """
        Load NFL data from files.

        Args:
            data_path: Path to data directory or CSV file

        Returns:
            DataFrame with NFL data
        """
        print("Loading NFL data...")

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

        print(f"Loaded {len(df)} NFL games")
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
            df.loc[df['AwayScore'] == df['HomeScore'], 'Result'] = 'D'  # Ties possible in NFL

        # Ensure Date is datetime
        df['Date'] = pd.to_datetime(df['Date'])

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer NFL-specific features.

        Args:
            df: Raw data DataFrame

        Returns:
            DataFrame with engineered features
        """
        return self.feature_engineer.engineer_features(df)

    def train_models(self, df: pd.DataFrame, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train NFL prediction models.

        Args:
            df: DataFrame with engineered features
            targets: Optional list of targets

        Returns:
            Dictionary with training results
        """
        print("Training NFL models...")

        # Prepare features
        feature_cols = self.feature_engineer.get_feature_names()
        feature_cols = [col for col in feature_cols if col in df.columns]

        self.feature_columns = feature_cols

        # Remove rows with NaN in features
        df_clean = df.dropna(subset=feature_cols)

        X = df_clean[feature_cols]
        y_outcome = df_clean['Result']
        y_points = df_clean['TotalPoints']

        # Train/test split
        X_train, X_test, y_train_outcome, y_test_outcome = train_test_split(
            X, y_outcome, test_size=0.2, random_state=42
        )
        _, _, y_train_points, y_test_points = train_test_split(
            X, y_points, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train outcome models
        print("Training Match Outcome models...")
        rf_outcome = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_outcome.fit(X_train_scaled, y_train_outcome)

        gb_outcome = GradientBoostingClassifier(n_estimators=100, random_state=42)
        gb_outcome.fit(X_train_scaled, y_train_outcome)

        # Train total points model
        print("Training Total Points model...")
        rf_points = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf_points.fit(X_train_scaled, y_train_points)

        # Store models
        self.models['match_outcome_rf'] = rf_outcome
        self.models['match_outcome_gb'] = gb_outcome
        self.models['total_points_rf'] = rf_points

        # Calculate accuracy
        outcome_accuracy_rf = rf_outcome.score(X_test_scaled, y_test_outcome)
        outcome_accuracy_gb = gb_outcome.score(X_test_scaled, y_test_outcome)
        points_r2 = rf_points.score(X_test_scaled, y_test_points)

        print(f"Match Outcome Accuracy (RF): {outcome_accuracy_rf:.3f}")
        print(f"Match Outcome Accuracy (GB): {outcome_accuracy_gb:.3f}")
        print(f"Total Points R²: {points_r2:.3f}")

        self.is_trained = True
        self.metadata['last_trained'] = datetime.now().isoformat()

        return {
            'outcome_accuracy_rf': outcome_accuracy_rf,
            'outcome_accuracy_gb': outcome_accuracy_gb,
            'points_r2': points_r2,
            'num_features': len(feature_cols),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }

    def predict(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict NFL game outcome.

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
                'Spread': -3.5,
                'Total Points': 'Over 47.5'
            },
            'probabilities': {
                'Home Win': 0.58,
                'Away Win': 0.40,
                'Tie': 0.02
            },
            'confidence': 'Medium'
        }

        return prediction

    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict multiple NFL games.

        Args:
            matches: List of match info dictionaries

        Returns:
            List of prediction dictionaries
        """
        return [self.predict(match) for match in matches]

    def get_insights(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Get NFL insights.

        Args:
            team: Optional team name for team-specific insights

        Returns:
            Dictionary with insights
        """
        insights = {
            'sport': 'nfl',
            'teams_available': len(self.teams)
        }

        if team:
            insights['team'] = team
            insights['stats'] = 'Coming soon'

        return insights

    def validate_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Validate NFL prediction.

        Args:
            prediction: Prediction dictionary

        Returns:
            True if valid
        """
        # Basic validation
        required_keys = ['match_info', 'predictions', 'probabilities']

        return all(key in prediction for key in required_keys)

    def get_available_teams(self) -> List[str]:
        """Get list of NFL teams."""
        return self.teams

    def get_prediction_markets(self) -> List[str]:
        """Get available prediction markets for NFL."""
        return [
            'Winner (Moneyline)',
            'Point Spread',
            'Total Points (Over/Under)',
            'First Half Winner',
            'First Team to Score'
        ]
