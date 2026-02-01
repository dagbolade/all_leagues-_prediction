"""
Train Tennis models with ADVANCED methods
- XGBoost, CatBoost, LightGBM
- Bayesian Hyperparameter Optimization
- Stacking Ensembles
- Probability Calibration
"""

from pathlib import Path
import pandas as pd
from sports.tennis.tennis_features import TennisFeatureEngineer
from sports.tennis.advanced_tennis_training import AdvancedTennisPredictor

def main():
    print("=" * 80)
    print("ADVANCED TENNIS MODEL TRAINING - MATCHING FOOTBALL SOPHISTICATION")
    print("=" * 80)

    # Load data
    print("\n1. Loading REAL tennis data (27,784 matches)...")
    data_path = Path("data/tennis/raw/tennis_real_data.csv")
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])

    print(f"   Loaded {len(df)} matches")
    print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")

    # Engineer features
    print("\n2. Engineering tennis features...")
    feature_engineer = TennisFeatureEngineer()
    df_features = feature_engineer.engineer_features(df)
    feature_cols = feature_engineer.get_feature_names()
    print(f"   Created {len(feature_cols)} features")

    # Train advanced models
    print("\n3. Training ADVANCED models...")
    print("   - XGBoost with Bayesian optimization")
    print("   - CatBoost with Bayesian optimization")
    print("   - LightGBM with Bayesian optimization")
    print("   - Stacking ensemble with meta-learner")
    print("   - Probability calibration")

    predictor = AdvancedTennisPredictor()
    predictor.train_models(df_features, feature_cols)

    # Save models
    print("\n4. Saving advanced models...")
    models_dir = Path("models/tennis")
    models_dir.mkdir(parents=True, exist_ok=True)
    predictor.save_models(models_dir / "tennis_advanced_models.joblib")

    # Summary
    print("\n" + "=" * 80)
    print("ADVANCED TENNIS MODELS TRAINED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Models trained: {list(predictor.models.keys())}")
    print(f"Bayesian optimization trials: {len(predictor.hyperopt_trials)}")
    print("\nModel Performance:")
    for task, metrics in predictor.metrics.items():
        print(f"\n{task}:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.4f}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
