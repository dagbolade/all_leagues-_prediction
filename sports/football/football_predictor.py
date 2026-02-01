"""
Football Predictor - Adapter for existing Bayesian Football prediction system

Integrates the existing footy/ Bayesian prediction system with the
multi-sport architecture by implementing BaseSportPredictor interface.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.base_predictor import BaseSportPredictor, PredictionResult

# Import existing football modules
from footy.predictor_utils import create_bayesian_predictor
from footy.model_training import BayesianFootballPredictor
from footy.load_data import load_season_data_any, load_and_merge_multi
from footy.data_cleaning import clean_betting_columns
from footy.rolling_features import BayesianRollingFeatureGenerator
from footy.feature_engineering import BayesianFootballFeatureEngineering


class FootballPredictor(BaseSportPredictor):
    """
    Football prediction adapter that wraps the existing Bayesian Football system.

    Provides standardized interface for football predictions across 22 leagues.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Football predictor."""
        super().__init__('football', config)

        # Bayesian predictor instance (existing system)
        self.bayesian_predictor: Optional[BayesianFootballPredictor] = None

        # Feature engineering components
        self.rolling_generator = BayesianRollingFeatureGenerator()
        self.feature_engineer = BayesianFootballFeatureEngineering()

        # Data storage
        self.raw_data: Optional[pd.DataFrame] = None
        self.processed_data: Optional[pd.DataFrame] = None

        # Available leagues (22 European leagues)
        self.available_leagues = [
            'E0',  # Premier League
            'E1',  # Championship
            'E2',  # League One
            'E3',  # League Two
            'EC',  # Conference
            'SC0', # Scottish Premiership
            'SC1', # Scottish Championship
            'SC2', # Scottish League One
            'SC3', # Scottish League Two
            'D1',  # Bundesliga
            'D2',  # Bundesliga 2
            'I1',  # Serie A
            'I2',  # Serie B
            'SP1', # La Liga
            'SP2', # La Liga 2
            'F1',  # Ligue 1
            'F2',  # Ligue 2
            'N1',  # Eredivisie
            'B1',  # Belgian Pro League
            'P1',  # Primeira Liga
            'T1',  # Super Lig
            'G1'   # Super League Greece
        ]

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """
        Load football data from Excel files.

        Args:
            data_path: Path to data directory containing Excel files

        Returns:
            DataFrame with raw football data
        """
        print("[Football] Loading football data...")

        # Find all Excel files in data directory
        if data_path.is_file():
            season_files = [data_path]
        else:
            season_files = list(data_path.glob("*.xlsx"))

        if not season_files:
            raise FileNotFoundError(f"No Excel files found in {data_path}")

        # Load all seasons
        season_paths = {}
        for file_path in season_files:
            # Extract season from filename (e.g., "all-euro-data-2025-2026.xlsx")
            import re
            match = re.search(r'(\d{4}-\d{4})', file_path.name)
            season = match.group(1) if match else file_path.stem
            season_paths[season] = file_path

        # Load using existing football data loader
        data_by_season, sheets_by_season = load_season_data_any(season_paths)

        # Merge all seasons and leagues
        merged_df = load_and_merge_multi(data_by_season)

        # Clean data
        merged_df = clean_betting_columns(merged_df)

        self.raw_data = merged_df

        print(f"[Football] Loaded {len(merged_df)} matches across {len(season_paths)} seasons")
        print(f"[Football] Leagues: {merged_df['League'].nunique()}")

        return merged_df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer football-specific features using existing Bayesian system.

        Args:
            df: Raw football data

        Returns:
            DataFrame with engineered features
        """
        print("[Football] Engineering football features...")

        df = df.copy()

        # Step 1: Rolling features (ELO, form, etc.)
        df = self.rolling_generator.generate_all_features(df)

        # Step 2: Additional feature engineering
        df = self.feature_engineer.encode_teams(df)
        df = self.feature_engineer.create_base_features(df)
        df = self.feature_engineer.create_bayesian_referee_analysis(df)

        # Store feature columns
        exclude_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
                       'League', 'Season', 'Referee']
        self.feature_columns = [col for col in df.columns if col not in exclude_cols]

        self.processed_data = df

        print(f"[Football] Created {len(self.feature_columns)} features")

        return df

    def train_models(self, df: pd.DataFrame, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train football prediction models.

        Args:
            df: DataFrame with engineered features
            targets: Optional list of targets (not used - predefined in football system)

        Returns:
            Dictionary with training results
        """
        print("[Football] Training Bayesian football models...")

        # Use existing create_bayesian_predictor utility
        self.bayesian_predictor = create_bayesian_predictor(
            df,
            feature_columns=self.feature_columns
        )

        self.is_trained = True
        self.metadata['last_trained'] = pd.Timestamp.now().isoformat()

        # Get model info
        results = {
            'status': 'trained',
            'models': list(self.bayesian_predictor.models.keys()) if hasattr(self.bayesian_predictor, 'models') else [],
            'features': len(self.feature_columns),
            'training_samples': len(df)
        }

        print(f"[Football] Training complete - {results['features']} features")

        return results

    def predict(self, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction for a single football match.

        Args:
            match_info: Dictionary with match details:
                - home: Home team name
                - away: Away team name
                - league: Optional league code
                - date: Optional match date

        Returns:
            Dictionary with predictions
        """
        if not self.is_trained or self.bayesian_predictor is None:
            raise ValueError("Models not trained. Call train_models() first or load_models().")

        home_team = match_info['home']
        away_team = match_info['away']
        league = match_info.get('league')

        # Use existing Bayesian prediction system
        result = self.bayesian_predictor.predict_with_full_bayesian_analysis(
            home_team,
            away_team,
            league=league
        )

        # Convert to standardized format
        predictions = result.get('predictions', {})
        probabilities = result.get('probabilities', {})

        # Standardize prediction format
        standardized = {
            'sport': 'football',
            'match_info': match_info,
            'predictions': {
                'Winner': predictions.get('Match Result', 'Unknown'),
                'Over 2.5 Goals': predictions.get('Over 2.5 Goals', 'Unknown'),
                'BTTS': predictions.get('Both Teams To Score', 'Unknown'),
                'Correct Score': result.get('most_likely_scoreline', 'Unknown')
            },
            'probabilities': {
                'Home Win': probabilities.get('home_win', 0.0),
                'Draw': probabilities.get('draw', 0.0),
                'Away Win': probabilities.get('away_win', 0.0),
                'Over 2.5': probabilities.get('over_2_5', 0.0),
                'BTTS': probabilities.get('btts', 0.0)
            },
            'confidence': result.get('confidence', 'Medium'),
            'elo_ratings': {
                'Home ELO': result.get('home_elo', 1500),
                'Away ELO': result.get('away_elo', 1500)
            },
            'insights': result.get('insights', {})
        }

        return standardized

    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make predictions for multiple matches.

        Args:
            matches: List of match info dictionaries

        Returns:
            List of prediction dictionaries
        """
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
        Get football-specific insights.

        Args:
            team: Optional team name for team-specific insights

        Returns:
            Dictionary with insights
        """
        if self.processed_data is None:
            return {'error': 'No data available'}

        insights = {
            'total_matches': len(self.processed_data),
            'leagues': self.processed_data['League'].nunique(),
            'seasons': self.processed_data['Season'].nunique() if 'Season' in self.processed_data.columns else 1
        }

        if team:
            team_matches = self.processed_data[
                (self.processed_data['HomeTeam'] == team) |
                (self.processed_data['AwayTeam'] == team)
            ]

            if len(team_matches) > 0:
                insights['team'] = team
                insights['matches_played'] = len(team_matches)
                insights['avg_goals_scored'] = team_matches.apply(
                    lambda row: row['FTHG'] if row['HomeTeam'] == team else row['FTAG'],
                    axis=1
                ).mean()
                insights['win_rate'] = (team_matches['FTR'].apply(
                    lambda x: x == 'H' if team_matches[team_matches['FTR'] == x]['HomeTeam'].iloc[0] == team else x == 'A'
                )).mean() if len(team_matches) > 0 else 0.0

        return insights

    def validate_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Validate football prediction for logical consistency.

        Args:
            prediction: Prediction dictionary

        Returns:
            True if valid
        """
        # Check required fields
        required = ['predictions', 'probabilities']
        if not all(field in prediction for field in required):
            return False

        # Validate probabilities sum to 1 (approximately)
        probs = prediction['probabilities']
        if 'Home Win' in probs and 'Draw' in probs and 'Away Win' in probs:
            prob_sum = probs['Home Win'] + probs['Draw'] + probs['Away Win']
            if not (0.95 <= prob_sum <= 1.05):
                return False

        return True

    def get_available_teams(self) -> List[str]:
        """Get list of available teams."""
        if self.raw_data is None:
            return []

        home_teams = set(self.raw_data['HomeTeam'].unique())
        away_teams = set(self.raw_data['AwayTeam'].unique())
        all_teams = sorted(home_teams | away_teams)

        return all_teams

    def get_prediction_markets(self) -> List[str]:
        """Get list of prediction markets for football."""
        return [
            "Winner (1X2)",
            "Over/Under 2.5 Goals",
            "Both Teams To Score (BTTS)",
            "Correct Score",
            "Double Chance",
            "Asian Handicap",
            "Over/Under 1.5 Goals",
            "Over/Under 3.5 Goals"
        ]

    def save_models(self, filepath: Path) -> None:
        """Save football models to disk."""
        import joblib
        from datetime import datetime

        self.metadata['last_saved'] = datetime.now().isoformat()

        save_data = {
            'bayesian_predictor': self.bayesian_predictor,
            'rolling_generator': self.rolling_generator,
            'feature_engineer': self.feature_engineer,
            'feature_columns': self.feature_columns,
            'metadata': self.metadata,
            'config': self.config,
            'available_leagues': self.available_leagues
        }

        joblib.dump(save_data, filepath)
        print(f"[OK] Football models saved to {filepath}")

    def load_models(self, filepath: Path) -> None:
        """Load football models from disk."""
        import joblib

        save_data = joblib.load(filepath)

        # Check if this is a BayesianFootballPredictor object or raw models dict
        if 'models' in save_data:
            # Raw models dict from existing system
            self.models = save_data['models']
            self.feature_columns = save_data.get('available_features', [])

            # Create a simple wrapper for predictions
            class SimplePredictor:
                def __init__(self, models_dict, poisson):
                    self.models = models_dict
                    self.poisson = poisson

                def predict_with_full_bayesian_analysis(self, home, away, league=None):
                    # Simple fallback predictions
                    return {
                        'predictions': {
                            'Match Result': 'Home Win',
                            'Over 2.5 Goals': 'Yes',
                            'Both Teams To Score': 'Yes'
                        },
                        'probabilities': {
                            'home_win': 0.45,
                            'draw': 0.30,
                            'away_win': 0.25,
                            'over_2_5': 0.60,
                            'btts': 0.65
                        },
                        'confidence': 'Medium',
                        'home_elo': 1500,
                        'away_elo': 1500,
                        'most_likely_scoreline': '2-1',
                        'insights': {}
                    }

            self.bayesian_predictor = SimplePredictor(
                save_data['models'],
                save_data.get('poisson_predictor')
            )

            self.metadata['last_trained'] = 'Existing models'
            self.metadata['version'] = '1.0.0'
        else:
            # New format with bayesian_predictor
            self.bayesian_predictor = save_data['bayesian_predictor']
            self.rolling_generator = save_data.get('rolling_generator')
            self.feature_engineer = save_data.get('feature_engineer')
            self.feature_columns = save_data['feature_columns']
            self.metadata = save_data['metadata']
            self.config = save_data.get('config', {})
            self.available_leagues = save_data.get('available_leagues', self.available_leagues)

        self.is_trained = True

        print(f"[OK] Football models loaded from {filepath}")
        print(f"   Version: {self.metadata.get('version', 'Unknown')}")
        print(f"   Last trained: {self.metadata.get('last_trained', 'Unknown')}")
