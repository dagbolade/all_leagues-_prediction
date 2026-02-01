"""
Basketball Model Backtesting - Test on Recent Unseen Games

This script properly validates the basketball model by:
1. Training on historical data (2020-2024)
2. Testing on recent unseen games (2024-2025 season)
3. Reporting realistic accuracy metrics
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import joblib

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sports.basketball.basketball_features import BasketballFeatureEngineer
from sports.basketball.advanced_basketball_training import AdvancedBasketballPredictor


def load_basketball_data():
    """Load real NBA data."""
    data_path = Path("data/basketball/raw/nba_real_data.csv")

    if not data_path.exists():
        raise FileNotFoundError(f"NBA data not found at {data_path}")

    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])

    print(f"[Data] Loaded {len(df)} games")
    print(f"[Data] Date range: {df['Date'].min()} to {df['Date'].max()}")

    return df


def temporal_train_test_split(df, split_date='2024-10-01'):
    """
    Split data temporally for proper backtesting.

    Train: Games before split_date
    Test: Games after split_date (recent unseen games)
    """
    split_date = pd.to_datetime(split_date)

    train_df = df[df['Date'] < split_date].copy()
    test_df = df[df['Date'] >= split_date].copy()

    print("\n" + "=" * 80)
    print("TEMPORAL TRAIN/TEST SPLIT")
    print("=" * 80)
    print(f"Split Date: {split_date.date()}")
    print(f"\nTraining Set:")
    print(f"  - Games: {len(train_df)}")
    print(f"  - Date Range: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")

    print(f"\nTest Set (UNSEEN RECENT GAMES):")
    print(f"  - Games: {len(test_df)}")
    print(f"  - Date Range: {test_df['Date'].min().date()} to {test_df['Date'].max().date()}")
    print("=" * 80 + "\n")

    return train_df, test_df


def train_model_on_historical_data(train_df):
    """Train model ONLY on historical data."""
    print("\n" + "=" * 80)
    print("TRAINING ON HISTORICAL DATA ONLY")
    print("=" * 80)

    # Standardize columns
    if 'Result' not in train_df.columns:
        train_df['Result'] = 'H'
        train_df.loc[train_df['AwayScore'] > train_df['HomeScore'], 'Result'] = 'A'

    if 'TotalPoints' not in train_df.columns:
        train_df['TotalPoints'] = train_df['HomeScore'] + train_df['AwayScore']

    if 'PointDiff' not in train_df.columns:
        train_df['PointDiff'] = train_df['HomeScore'] - train_df['AwayScore']

    # Engineer features
    print("\n[Features] Engineering basketball features...")
    feature_engineer = BasketballFeatureEngineer()
    train_df_features = feature_engineer.engineer_features(train_df)
    feature_cols = feature_engineer.get_feature_names()
    print(f"[Features] Created {len(feature_cols)} features")

    # Train models
    predictor = AdvancedBasketballPredictor()
    predictor.train_models(train_df_features, feature_cols)

    print("\n[Training] Models trained on historical data")

    return predictor, feature_cols, feature_engineer


def backtest_on_recent_games(predictor, test_df, feature_cols, feature_engineer):
    """Test model on recent unseen games."""
    print("\n" + "=" * 80)
    print("BACKTESTING ON RECENT UNSEEN GAMES")
    print("=" * 80)

    # Standardize columns
    if 'Result' not in test_df.columns:
        test_df['Result'] = 'H'
        test_df.loc[test_df['AwayScore'] > test_df['HomeScore'], 'Result'] = 'A'

    if 'TotalPoints' not in test_df.columns:
        test_df['TotalPoints'] = test_df['HomeScore'] + test_df['AwayScore']

    if 'PointDiff' not in test_df.columns:
        test_df['PointDiff'] = test_df['HomeScore'] - test_df['AwayScore']

    # Engineer features for test data
    print("\n[Features] Engineering features for test data...")
    test_df_features = feature_engineer.engineer_features(test_df)

    # Prepare test data
    test_df_processed, y_test = predictor.prepare_data(test_df_features)

    # Extract features
    X_test = test_df_processed[feature_cols].copy()

    # Handle missing values
    for col in X_test.columns:
        if X_test[col].isnull().any():
            X_test[col].fillna(X_test[col].median(), inplace=True)

    results = {}

    # Test each task
    for task, model_data in predictor.models.items():
        print(f"\n[Backtest] Testing {task}...")

        model = model_data['model']
        y_true = y_test[task]

        if task in ['match_outcome', 'over_220']:
            # Classification tasks
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)

            from sklearn.metrics import accuracy_score, log_loss, f1_score, classification_report

            accuracy = accuracy_score(y_true, y_pred)
            logloss = log_loss(y_true, y_pred_proba)
            f1 = f1_score(y_true, y_pred, average='weighted')

            results[task] = {
                'accuracy': accuracy,
                'log_loss': logloss,
                'f1': f1
            }

            print(f"  Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
            print(f"  Log Loss: {logloss:.4f}")
            print(f"  F1 Score: {f1:.4f}")

            print("\n  Classification Report:")
            print(classification_report(y_true, y_pred, target_names=['Away Win', 'Home Win'] if task == 'match_outcome' else ['Under 220', 'Over 220']))

        else:
            # Regression task (total_points)
            y_pred = model.predict(X_test)

            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

            mae = mean_absolute_error(y_true, y_pred)
            mse = mean_squared_error(y_true, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_true, y_pred)

            results[task] = {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'r2': r2
            }

            print(f"  MAE: {mae:.4f}")
            print(f"  RMSE: {rmse:.4f}")
            print(f"  R2 Score: {r2:.4f}")

    return results


def generate_backtest_report(results, train_df, test_df):
    """Generate comprehensive backtest report."""
    print("\n" + "=" * 80)
    print("BACKTEST REPORT - REALISTIC PERFORMANCE ON UNSEEN GAMES")
    print("=" * 80)

    print(f"\nTraining Period: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")
    print(f"Training Games: {len(train_df)}")

    print(f"\nTest Period (UNSEEN): {test_df['Date'].min().date()} to {test_df['Date'].max().date()}")
    print(f"Test Games: {len(test_df)}")

    print("\n" + "-" * 80)
    print("REALISTIC MODEL PERFORMANCE")
    print("-" * 80)

    for task, metrics in results.items():
        print(f"\n{task.upper()}:")
        for metric, value in metrics.items():
            if isinstance(value, float):
                if metric in ['accuracy', 'f1', 'r2']:
                    print(f"  {metric}: {value:.4f} ({value*100:.2f}%)")
                else:
                    print(f"  {metric}: {value:.4f}")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    match_accuracy = results.get('match_outcome', {}).get('accuracy', 0)

    if match_accuracy >= 0.65:
        print(f"\n[EXCELLENT] Match outcome accuracy of {match_accuracy*100:.2f}% is strong for sports prediction")
        print("This is realistic performance on unseen games (not overfitting).")
    elif match_accuracy >= 0.55:
        print(f"\n[GOOD] Match outcome accuracy of {match_accuracy*100:.2f}% is acceptable")
        print("Better than random (50%) and shows the model has learned patterns.")
    else:
        print(f"\n[POOR] Match outcome accuracy of {match_accuracy*100:.2f}% needs improvement")
        print("Model may need more features or better hyperparameter tuning.")

    print("\n" + "=" * 80)


def save_backtest_results(predictor, results, feature_cols):
    """Save backtested model and results."""
    output_dir = Path("models/basketball")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "basketball_backtested_models.joblib"

    # Save everything
    save_data = {
        'models': predictor.models,
        'calibrated_models': predictor.calibrated_models,
        'backtest_metrics': results,
        'feature_cols': feature_cols,
        'trained_on': 'historical_data',
        'tested_on': 'unseen_recent_games'
    }

    joblib.dump(save_data, output_path)
    print(f"\n[OK] Backtested models saved to {output_path}")


def main():
    """Run basketball backtesting."""
    print("=" * 80)
    print("BASKETBALL MODEL BACKTESTING")
    print("Testing on Recent Unseen Games")
    print("=" * 80)

    # Load data
    df = load_basketball_data()

    # Temporal split (train on pre-Oct 2024, test on 2024-25 season)
    train_df, test_df = temporal_train_test_split(df, split_date='2024-10-01')

    # Train on historical data only
    predictor, feature_cols, feature_engineer = train_model_on_historical_data(train_df)

    # Backtest on recent unseen games
    results = backtest_on_recent_games(predictor, test_df, feature_cols, feature_engineer)

    # Generate report
    generate_backtest_report(results, train_df, test_df)

    # Save backtested model
    save_backtest_results(predictor, results, feature_cols)

    print("\n" + "=" * 80)
    print("BACKTESTING COMPLETE!")
    print("=" * 80)
    print("\nThe model has been validated on recent unseen games.")
    print("This is realistic performance, not overfitting.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
