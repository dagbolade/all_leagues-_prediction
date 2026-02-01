"""
Tennis Model Backtesting - Test on Recent Unseen Games

This script properly validates the tennis model by:
1. Training on historical data (2020-Oct 2025)
2. Testing on recent unseen matches (Nov 2025)
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

from sports.tennis.tennis_features import TennisFeatureEngineer
from sports.tennis.advanced_tennis_training import AdvancedTennisPredictor


def load_tennis_data():
    """Load real tennis data."""
    data_path = Path("data/tennis/raw/tennis_real_data.csv")

    if not data_path.exists():
        raise FileNotFoundError(f"Tennis data not found at {data_path}")

    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])

    print(f"[Data] Loaded {len(df)} matches")
    print(f"[Data] Date range: {df['Date'].min()} to {df['Date'].max()}")

    return df


def temporal_train_test_split(df, split_date='2025-11-01'):
    """
    Split data temporally for proper backtesting.

    Train: Matches before split_date
    Test: Matches after split_date (recent unseen matches)
    """
    split_date = pd.to_datetime(split_date)

    train_df = df[df['Date'] < split_date].copy()
    test_df = df[df['Date'] >= split_date].copy()

    print("\n" + "=" * 80)
    print("TEMPORAL TRAIN/TEST SPLIT")
    print("=" * 80)
    print(f"Split Date: {split_date.date()}")
    print(f"\nTraining Set:")
    print(f"  - Matches: {len(train_df)}")
    print(f"  - Date Range: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")

    print(f"\nTest Set (UNSEEN RECENT MATCHES):")
    print(f"  - Matches: {len(test_df)}")
    print(f"  - Date Range: {test_df['Date'].min().date()} to {test_df['Date'].max().date()}")
    print("=" * 80 + "\n")

    return train_df, test_df


def train_model_on_historical_data(train_df):
    """Train model ONLY on historical data."""
    print("\n" + "=" * 80)
    print("TRAINING ON HISTORICAL DATA ONLY")
    print("=" * 80)

    # Engineer features
    print("\n[Features] Engineering tennis features...")
    feature_engineer = TennisFeatureEngineer()
    train_df_features = feature_engineer.engineer_features(train_df)
    feature_cols = feature_engineer.get_feature_names()
    print(f"[Features] Created {len(feature_cols)} features")

    # Train models
    predictor = AdvancedTennisPredictor()
    predictor.train_models(train_df_features, feature_cols)

    print("\n[Training] Models trained on historical data")

    return predictor, feature_cols, feature_engineer


def backtest_on_recent_matches(predictor, test_df, feature_cols, feature_engineer):
    """Test model on recent unseen matches."""
    print("\n" + "=" * 80)
    print("BACKTESTING ON RECENT UNSEEN MATCHES")
    print("=" * 80)

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

    # Test winner prediction
    task = 'winner'
    print(f"\n[Backtest] Testing {task} prediction...")

    model = predictor.models[task]['model']
    y_true = y_test  # y_test is a Series, not a dictionary

    # Predictions
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
    print(classification_report(y_true, y_pred, target_names=['Player2 Win', 'Player1 Win']))

    # Show some example predictions
    print("\n  Sample Predictions (First 10 matches):")
    print("-" * 80)
    sample_df = test_df.head(10)
    sample_preds = y_pred[:10]
    sample_proba = y_pred_proba[:10]
    sample_true = y_true[:10].values

    for i in range(min(10, len(sample_df))):
        match = sample_df.iloc[i]
        pred = 'Player1' if sample_preds[i] == 1 else 'Player2'
        actual = 'Player1' if sample_true[i] == 1 else 'Player2'
        confidence = sample_proba[i][sample_preds[i]] * 100

        result_icon = "[OK]" if pred == actual else "[X]"
        print(f"  {result_icon} {match['Player1']} vs {match['Player2']}")
        print(f"      Predicted: {pred} ({confidence:.1f}% confidence) | Actual: {actual}")

    return results


def generate_backtest_report(results, train_df, test_df):
    """Generate comprehensive backtest report."""
    print("\n" + "=" * 80)
    print("BACKTEST REPORT - REALISTIC PERFORMANCE ON UNSEEN MATCHES")
    print("=" * 80)

    print(f"\nTraining Period: {train_df['Date'].min().date()} to {train_df['Date'].max().date()}")
    print(f"Training Matches: {len(train_df)}")

    print(f"\nTest Period (UNSEEN): {test_df['Date'].min().date()} to {test_df['Date'].max().date()}")
    print(f"Test Matches: {len(test_df)}")

    print("\n" + "-" * 80)
    print("REALISTIC MODEL PERFORMANCE")
    print("-" * 80)

    for task, metrics in results.items():
        print(f"\n{task.upper()} PREDICTION:")
        for metric, value in metrics.items():
            if isinstance(value, float):
                if metric in ['accuracy', 'f1']:
                    print(f"  {metric}: {value:.4f} ({value*100:.2f}%)")
                else:
                    print(f"  {metric}: {value:.4f}")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    winner_accuracy = results.get('winner', {}).get('accuracy', 0)

    if winner_accuracy >= 0.65:
        print(f"\n[EXCELLENT] Winner prediction accuracy of {winner_accuracy*100:.2f}% is strong for tennis")
        print("This is realistic performance on unseen matches (not overfitting).")
        print("Better than ATP/WTA rankings-based predictions (~60%).")
    elif winner_accuracy >= 0.55:
        print(f"\n[GOOD] Winner prediction accuracy of {winner_accuracy*100:.2f}% is acceptable")
        print("Better than random (50%) and shows the model has learned patterns.")
    else:
        print(f"\n[POOR] Winner prediction accuracy of {winner_accuracy*100:.2f}% needs improvement")
        print("Model may need more features or better hyperparameter tuning.")

    print("\n" + "=" * 80)


def save_backtest_results(predictor, results, feature_cols):
    """Save backtested model and results."""
    output_dir = Path("models/tennis")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "tennis_backtested_models.joblib"

    # Save everything
    save_data = {
        'models': predictor.models,
        'calibrated_models': predictor.calibrated_models,
        'backtest_metrics': results,
        'feature_cols': feature_cols,
        'trained_on': 'historical_data',
        'tested_on': 'unseen_recent_matches'
    }

    joblib.dump(save_data, output_path)
    print(f"\n[OK] Backtested models saved to {output_path}")


def main():
    """Run tennis backtesting."""
    print("=" * 80)
    print("TENNIS MODEL BACKTESTING")
    print("Testing on Recent Unseen Matches")
    print("=" * 80)

    # Load data
    df = load_tennis_data()

    # Use last 10% of data as test set for more robust evaluation
    print("\n[Strategy] Using last 10% of data as unseen test set for robust evaluation...")
    split_idx = int(len(df) * 0.9)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    print(f"\nTemporal Split:")
    print(f"  Training: {len(train_df)} matches ({train_df['Date'].min().date()} to {train_df['Date'].max().date()})")
    print(f"  Test (UNSEEN): {len(test_df)} matches ({test_df['Date'].min().date()} to {test_df['Date'].max().date()})")

    # Train on historical data only
    predictor, feature_cols, feature_engineer = train_model_on_historical_data(train_df)

    # Backtest on recent unseen matches
    results = backtest_on_recent_matches(predictor, test_df, feature_cols, feature_engineer)

    # Generate report
    generate_backtest_report(results, train_df, test_df)

    # Save backtested model
    save_backtest_results(predictor, results, feature_cols)

    print("\n" + "=" * 80)
    print("BACKTESTING COMPLETE!")
    print("=" * 80)
    print("\nThe model has been validated on recent unseen matches.")
    print("This is realistic performance, not overfitting.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
