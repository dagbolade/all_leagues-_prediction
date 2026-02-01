# footy/fast_model_training.py - LIGHTNING FAST MODEL TRAINING

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, log_loss
from sklearn.calibration import CalibratedClassifierCV
import joblib
from typing import Dict, List, Tuple, Optional, Any
import warnings
from datetime import datetime
import os

# Fast ML models
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import RandomForestClassifier

# Import Poisson predictor
from footy.poisson_predictor import PoissonScorelinePredictor

warnings.filterwarnings('ignore')


class FastBayesianFootballPredictor:
    """Lightning fast model training - from 2 days to 30 minutes!"""

    def __init__(self):
        self.models = {}
        self.calibrated_models = {}
        self.poisson_predictor = None
        self.feature_columns = []
        self.scaler = StandardScaler()
        self.training_time = {}

    def train_fast_models(self, df: pd.DataFrame, selected_features: List[str] = None):
        """Train models with optimized features - MUCH faster than before."""

        print("⚡ FAST BAYESIAN MODEL TRAINING STARTING...")
        print("🎯 Goal: Train accurate models in 30 minutes instead of 2 days")
        print("=" * 60)

        start_time = datetime.now()

        # Use selected features or get core features
        if selected_features is None:
            selected_features = self._get_essential_features(df)

        print(f"🚀 Using {len(selected_features)} optimized features (vs 273 before)")

        # Prepare fast training data
        X, targets = self._prepare_fast_training_data(df, selected_features)

        if X.empty:
            print("❌ No valid training data prepared")
            return

        print(f"📊 Training data: {X.shape[0]:,} matches, {X.shape[1]} features")

        # Fast model configurations (optimized for speed + accuracy)
        fast_model_configs = {
            'match_outcome': {
                'model': XGBClassifier(
                    n_estimators=100,  # Reduced from 500+
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='logloss'
                ),
                'target': 'match_outcome',
                'type': 'classification'
            },
            'over_2_5': {
                'model': LGBMClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                ),
                'target': 'over_2_5',
                'type': 'classification'
            },
            'btts': {
                'model': XGBClassifier(
                    n_estimators=80,
                    max_depth=5,
                    learning_rate=0.15,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='logloss'
                ),
                'target': 'btts',
                'type': 'classification'
            },
            'total_goals': {
                'model': XGBRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1
                ),
                'target': 'total_goals',
                'type': 'regression'
            }
        }

        # Train each model FAST
        for task_name, config in fast_model_configs.items():
            task_start = datetime.now()

            if config['target'] not in targets:
                print(f"⚠️ Skipping {task_name} - target not available")
                continue

            print(f"\n⚡ Training {task_name}...")

            y = targets[config['target']]
            valid_idx = y.notna()

            if valid_idx.sum() < 100:
                print(f"❌ Insufficient data for {task_name}")
                continue

            X_valid = X[valid_idx]
            y_valid = y[valid_idx]

            try:
                # Fast training
                model = config['model']
                model.fit(X_valid, y_valid)

                # Quick validation
                score = self._quick_validation(model, X_valid, y_valid, config['type'])

                # Fast calibration for classification
                calibrated_model = None
                if config['type'] == 'classification':
                    calibrated_model = CalibratedClassifierCV(model, cv=3)
                    calibrated_model.fit(X_valid, y_valid)

                # Store models
                self.models[task_name] = {
                    'model': model,
                    'features': selected_features,
                    'score': score,
                    'type': config['type']
                }

                if calibrated_model:
                    self.calibrated_models[task_name] = calibrated_model

                task_time = datetime.now() - task_start
                self.training_time[task_name] = task_time.total_seconds()

                print(f"✅ {task_name}: Score={score:.3f}, Time={task_time.total_seconds():.1f}s")

            except Exception as e:
                print(f"❌ {task_name} training failed: {e}")

        # Train fast Poisson predictor
        print(f"\n⚽ Training fast Poisson predictor...")
        try:
            self.poisson_predictor = PoissonScorelinePredictor()
            self.poisson_predictor.calculate_team_strengths(df)
            print("✅ Poisson predictor trained")
        except Exception as e:
            print(f"⚠️ Poisson training failed: {e}")

        # Store feature columns
        self.feature_columns = selected_features

        total_time = datetime.now() - start_time
        print(f"\n🎉 FAST TRAINING COMPLETE!")
        print(f"⏰ Total time: {total_time.total_seconds()/60:.1f} minutes")
        print(f"🚀 Speedup: ~{(2*24*60)/(total_time.total_seconds()/60):.0f}x faster than before!")

    def _get_essential_features(self, df: pd.DataFrame) -> List[str]:
        """Get the most essential features if none provided."""

        essential_features = [
            'HomeElo', 'AwayElo', 'EloAdvantage',
            'HomeForm_5', 'AwayForm_5',
            'HomeScoringForm_5', 'AwayScoringForm_5',
            'ExpectedHomeGoals', 'ExpectedAwayGoals',
            'BayesianHomeWinProb', 'BayesianAwayWinProb', 'BayesianDrawProb',
            'BayesianOver25Prob', 'BayesianBTTSProb',
            'H2H_HomeWinRate', 'H2H_AvgGoals',
            'SeasonProgress', 'HomeTeam_encoded', 'AwayTeam_encoded',
            'HomeTotalGoalsRate_5', 'AwayTotalGoalsRate_5',
            'HomeOverRate2.5_5', 'AwayOverRate2.5_5',
            'HomeBTTSForm_5', 'AwayBTTSForm_5'
        ]

        # Only include features that exist in the dataframe
        available_features = [f for f in essential_features if f in df.columns]

        print(f"🎯 Using {len(available_features)} essential features")
        return available_features

    def _prepare_fast_training_data(self, df: pd.DataFrame, feature_cols: List[str]) -> Tuple[pd.DataFrame, Dict]:
        """Prepare training data quickly."""

        # Get clean completed matches only
        mask = (
            df['FTR'].notna() &
            df['FTHG'].notna() &
            df['FTAG'].notna() &
            (df['FTHG'] >= 0) &
            (df['FTAG'] >= 0)
        )

        clean_df = df[mask].copy()

        if len(clean_df) == 0:
            print("❌ No valid matches found")
            return pd.DataFrame(), {}

        # Prepare features
        available_features = [f for f in feature_cols if f in clean_df.columns]
        X = clean_df[available_features].fillna(0)

        # Replace infinite values
        X = X.replace([np.inf, -np.inf], 0)

        # Prepare targets
        targets = {}

        # Match outcome
        if 'FTR' in clean_df.columns:
            targets['match_outcome'] = clean_df['FTR'].map({'H': 2, 'D': 1, 'A': 0})

        # Over 2.5 goals
        if 'TotalGoals' in clean_df.columns:
            targets['over_2_5'] = (clean_df['TotalGoals'] > 2.5).astype(int)
        elif 'Over2.5' in clean_df.columns:
            targets['over_2_5'] = clean_df['Over2.5']

        # BTTS
        if 'BTTS' in clean_df.columns:
            targets['btts'] = clean_df['BTTS']
        elif all(col in clean_df.columns for col in ['FTHG', 'FTAG']):
            targets['btts'] = ((clean_df['FTHG'] > 0) & (clean_df['FTAG'] > 0)).astype(int)

        # Total goals
        if 'TotalGoals' in clean_df.columns:
            targets['total_goals'] = clean_df['TotalGoals']
        elif all(col in clean_df.columns for col in ['FTHG', 'FTAG']):
            targets['total_goals'] = clean_df['FTHG'] + clean_df['FTAG']

        print(f"🎯 Prepared targets: {list(targets.keys())}")

        return X, targets

    def _quick_validation(self, model, X, y, model_type: str) -> float:
        """Quick 3-fold validation for speed."""

        try:
            if model_type == 'classification':
                scores = cross_val_score(model, X, y, cv=3, scoring='accuracy', n_jobs=-1)
            else:
                scores = cross_val_score(model, X, y, cv=3, scoring='neg_mean_squared_error', n_jobs=-1)
                scores = -scores  # Convert to positive

            return scores.mean()
        except:
            return 0.0

    def save_fast_models(self, filepath: str = 'models/fast_football_models.joblib'):
        """Save the fast-trained models."""

        model_data = {
            'models': self.models,
            'calibrated_models': self.calibrated_models,
            'poisson_predictor': self.poisson_predictor,
            'feature_columns': self.feature_columns,
            'scaler': self.scaler,
            'training_time': self.training_time,
            'metadata': {
                'training_date': datetime.now(),
                'total_features': len(self.feature_columns),
                'total_models': len(self.models),
                'fast_training': True
            }
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model_data, filepath)

        print(f"💾 Fast models saved to: {filepath}")
        return model_data

    def get_model_performance_summary(self) -> Dict:
        """Get performance summary of fast models."""

        summary = {
            'total_models': len(self.models),
            'total_training_time': sum(self.training_time.values()),
            'average_time_per_model': np.mean(list(self.training_time.values())),
            'model_scores': {name: info['score'] for name, info in self.models.items()},
            'feature_count': len(self.feature_columns),
            'models_trained': list(self.models.keys())
        }

        return summary


def run_fast_training_pipeline(
    data_path: str = 'data/processed/enhanced_bayesian_features.csv',
    feature_selection_path: str = 'models/optimized_features.joblib'
):
    """Complete fast training pipeline."""

    print("⚡ FAST TRAINING PIPELINE STARTING")
    print("🎯 Goal: Complete training in 30 minutes")
    print("=" * 50)

    # Load data
    print("📊 Loading data...")
    df = pd.read_csv(data_path, low_memory=False)
    print(f"✅ Data loaded: {df.shape}")

    # Load feature selection if available
    selected_features = None
    if os.path.exists(feature_selection_path):
        try:
            feature_data = joblib.load(feature_selection_path)
            selected_features = feature_data.get('core_features', None)
            print(f"✅ Using optimized features: {len(selected_features)}")
        except:
            print("⚠️ Could not load feature selection, using defaults")

    # Initialize fast predictor
    predictor = FastBayesianFootballPredictor()

    # Train models
    predictor.train_fast_models(df, selected_features)

    # Save models
    model_data = predictor.save_fast_models()

    # Get performance summary
    summary = predictor.get_model_performance_summary()

    print(f"\n🎉 FAST TRAINING PIPELINE COMPLETE!")
    print(f"⏰ Total time: {summary['total_training_time']/60:.1f} minutes")
    print(f"🎯 Models trained: {summary['total_models']}")
    print(f"📊 Features used: {summary['feature_count']}")
    print(f"📈 Average model score: {np.mean(list(summary['model_scores'].values())):.3f}")

    return predictor, model_data, summary


if __name__ == "__main__":
    run_fast_training_pipeline()