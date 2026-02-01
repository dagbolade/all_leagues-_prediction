"""
Tennis Predictor - Player vs Player prediction system

Predicts tennis match outcomes using:
- Player rankings and ELO ratings
- Surface-specific performance
- Head-to-head records
- Recent form and momentum
- Fatigue factors
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.base_predictor import BaseSportPredictor, PredictionResult
from sports.tennis.tennis_features import TennisFeatureEngineer

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


class TennisPredictor(BaseSportPredictor):
    """
    Tennis prediction system for ATP/WTA matches.

    Predicts match winners, set scores, and provides insights on
    surface-specific performance and head-to-head records.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Tennis predictor."""
        super().__init__('tennis', config)

        self.feature_engineer = TennisFeatureEngineer()
        self.scaler = StandardScaler()

        # Available surfaces
        self.surfaces = ['Hard', 'Clay', 'Grass', 'Carpet']

        # Available tours
        self.tours = ['ATP', 'WTA', 'Challenger', 'ITF']

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """
        Load tennis match data.

        Args:
            data_path: Path to tennis data CSV file

        Returns:
            DataFrame with raw tennis data
        """
        print("[Tennis] Loading tennis data...")

        if data_path.is_file():
            df = pd.read_csv(data_path)
        else:
            # Look for CSV files in directory
            csv_files = list(data_path.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"No CSV files found in {data_path}")
            df = pd.read_csv(csv_files[0])

        # Ensure required columns
        required_cols = ['Date', 'Player1', 'Player2', 'Winner']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Convert date
        df['Date'] = pd.to_datetime(df['Date'])

        print(f"[Tennis] Loaded {len(df)} matches")

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer tennis-specific features.

        Args:
            df: Raw tennis data

        Returns:
            DataFrame with engineered features
        """
        print("[Tennis] Engineering tennis features...")

        df = self.feature_engineer.engineer_features(df)
        self.feature_columns = self.feature_engineer.get_feature_names()

        return df

    def train_models(self, df: pd.DataFrame, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train tennis prediction models.

        Args:
            df: DataFrame with engineered features
            targets: Optional list of targets (default: ['Winner'])

        Returns:
            Dictionary with training results
        """
        print("[Tennis] Training tennis models...")

        if targets is None:
            targets = ['Winner']

        # Prepare features
        X = df[self.feature_columns].fillna(0)

        # Prepare target (binary: Player1 wins = 1, Player2 wins = 0)
        y = (df['Winner'] == 'Player1').astype(int)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Random Forest
        print("[Tennis] Training Random Forest...")
        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train_scaled, y_train)
        rf_acc = rf_model.score(X_test_scaled, y_test)

        # Train Gradient Boosting
        print("[Tennis] Training Gradient Boosting...")
        gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        gb_model.fit(X_train_scaled, y_train)
        gb_acc = gb_model.score(X_test_scaled, y_test)

        # Store models
        self.models = {
            'match_outcome_rf': rf_model,
            'match_outcome_gb': gb_model,
            'scaler': self.scaler
        }

        self.is_trained = True
        self.metadata['last_trained'] = datetime.now().isoformat()

        results = {
            'rf_accuracy': rf_acc,
            'gb_accuracy': gb_acc,
            'features': len(self.feature_columns),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }

        print(f"[Tennis] Random Forest accuracy: {rf_acc:.2%}")
        print(f"[Tennis] Gradient Boosting accuracy: {gb_acc:.2%}")

        return results

    def predict(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction for a tennis match.

        Args:
            match_info: Dictionary with match details:
                - player1: Player 1 name
                - player2: Player 2 name
                - surface: Optional surface type
                - tournament: Optional tournament name
                - round: Optional tournament round

        Returns:
            Dictionary with predictions
        """
        if not self.is_trained:
            raise ValueError("Models not trained. Call train_models() first or load_models().")

        player1 = match_info.get('player1', match_info.get('home'))
        player2 = match_info.get('player2', match_info.get('away'))
        surface = match_info.get('surface', 'Hard')

        # Create feature vector (placeholder - would need actual player stats)
        features = self._extract_match_features(player1, player2, surface)

        # Get predictions from both models
        rf_model = self.models['match_outcome_rf']
        gb_model = self.models['match_outcome_gb']
        scaler = self.models['scaler']

        features_scaled = scaler.transform([features])

        # Get probabilities
        rf_proba = rf_model.predict_proba(features_scaled)[0]
        gb_proba = gb_model.predict_proba(features_scaled)[0]

        # Average probabilities
        avg_proba = (rf_proba + gb_proba) / 2

        player1_win_prob = avg_proba[1]  # Player1 wins
        player2_win_prob = avg_proba[0]  # Player2 wins

        # Determine winner
        predicted_winner = player1 if player1_win_prob > player2_win_prob else player2

        # Confidence based on probability margin
        prob_margin = abs(player1_win_prob - player2_win_prob)
        if prob_margin > 0.3:
            confidence = 'High'
        elif prob_margin > 0.15:
            confidence = 'Medium'
        else:
            confidence = 'Low'

        # Predict sets (simple heuristic)
        if player1_win_prob > 0.7:
            predicted_sets = '2-0'
        elif player1_win_prob > 0.55:
            predicted_sets = '2-1'
        elif player2_win_prob > 0.7:
            predicted_sets = '0-2'
        elif player2_win_prob > 0.55:
            predicted_sets = '1-2'
        else:
            predicted_sets = '2-1'

        return {
            'sport': 'tennis',
            'match_info': {
                'player1': player1,
                'player2': player2,
                'surface': surface
            },
            'predictions': {
                'Winner': predicted_winner,
                'Sets': predicted_sets,
                'Surface Advantage': player1 if player1_win_prob > 0.5 else player2
            },
            'probabilities': {
                f'{player1} Win': float(player1_win_prob),
                f'{player2} Win': float(player2_win_prob)
            },
            'confidence': confidence
        }

    def _extract_match_features(self, player1: str, player2: str, surface: str) -> List[float]:
        """Extract features for a match (placeholder - would use actual player stats)."""
        # This would normally query player stats, but for now return defaults
        num_features = len(self.feature_columns) if self.feature_columns else 30
        return [0.5] * num_features  # Neutral features

    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Make predictions for multiple matches."""
        predictions = []
        for match_info in matches:
            try:
                pred = self.predict(match_info)
                predictions.append(pred)
            except Exception as e:
                predictions.append({
                    'match_info': match_info,
                    'error': str(e)
                })

        return predictions

    def get_insights(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Get tennis insights (player parameter instead of team).

        Args:
            team: Player name for player-specific insights

        Returns:
            Dictionary with insights
        """
        insights = {
            'sport': 'tennis',
            'surfaces': self.surfaces,
            'tours': self.tours
        }

        if team:  # team parameter is actually player name
            insights['player'] = team
            insights['note'] = 'Player-specific insights require historical data'

        return insights

    def validate_prediction(self, prediction: Dict[str, Any]) -> bool:
        """Validate tennis prediction."""
        required = ['predictions', 'probabilities']
        if not all(field in prediction for field in required):
            return False

        # Validate probabilities sum to approximately 1
        probs = prediction['probabilities']
        prob_values = list(probs.values())
        if len(prob_values) >= 2:
            if not (0.95 <= sum(prob_values) <= 1.05):
                return False

        return True

    def get_available_teams(self) -> List[str]:
        """Get list of available players."""
        # Would return list of players from loaded data
        return [
            'Novak Djokovic', 'Carlos Alcaraz', 'Daniil Medvedev',
            'Jannik Sinner', 'Andrey Rublev', 'Stefanos Tsitsipas',
            'Iga Swiatek', 'Aryna Sabalenka', 'Coco Gauff',
            'Elena Rybakina', 'Jessica Pegula', 'Ons Jabeur'
        ]

    def get_prediction_markets(self) -> List[str]:
        """Get list of prediction markets for tennis."""
        return [
            "Match Winner",
            "Set Betting (Exact Score)",
            "Total Games Over/Under",
            "First Set Winner",
            "Handicap Betting",
            "Correct Score"
        ]
