"""
Train Basketball models with ADVANCED methods
- XGBoost, CatBoost, LightGBM
- Bayesian Hyperparameter Optimization
- Stacking Ensembles
- Probability Calibration
"""

from pathlib import Path
import pandas as pd
from sports.basketball.basketball_features import BasketballFeatureEngineer
from sports.basketball.advanced_basketball_training import AdvancedBasketballPredictor

def main():
    print("=" * 80)
    print("ADVANCED BASKETBALL MODEL TRAINING - MATCHING FOOTBALL SOPHISTICATION")
    print("=" * 80)

    # Load data — combined NBA + EuroLeague
    combined_path = Path("data/basketball/raw/basketball_all_data.csv")
    nba_path      = Path("data/basketball/raw/nba_real_data.csv")
    data_path     = combined_path if combined_path.exists() else nba_path

    league_label = "NBA + EuroLeague" if combined_path.exists() else "NBA"
    print(f"\n1. Loading {league_label} data...")
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])

    # League indicator feature (1 = EuroLeague, 0 = NBA)
    if 'League' in df.columns:
        df['IsEuroLeague'] = (df['League'] == 'EuroLeague').astype(int)
    else:
        df['IsEuroLeague'] = 0

    # Standardize columns
    if 'Result' not in df.columns:
        df['Result'] = 'H'
        df.loc[df['AwayScore'] > df['HomeScore'], 'Result'] = 'A'

    if 'TotalPoints' not in df.columns:
        df['TotalPoints'] = df['HomeScore'] + df['AwayScore']

    if 'PointDiff' not in df.columns:
        df['PointDiff'] = df['HomeScore'] - df['AwayScore']

    nba_games = (df['League'] == 'NBA').sum() if 'League' in df.columns else len(df)
    eur_games = (df['League'] == 'EuroLeague').sum() if 'League' in df.columns else 0
    print(f"   Loaded {len(df)} games (NBA: {nba_games} | EuroLeague: {eur_games})")

    # Engineer features
    print("\n2. Engineering basketball features...")
    feature_engineer = BasketballFeatureEngineer()
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

    predictor = AdvancedBasketballPredictor()
    predictor.train_models(df_features, feature_cols)

    # Save models
    print("\n4. Saving advanced models...")
    models_dir = Path("models/basketball")
    models_dir.mkdir(parents=True, exist_ok=True)
    predictor.save_models(models_dir / "basketball_advanced_models.joblib")

    # Summary
    print("\n" + "=" * 80)
    print("ADVANCED BASKETBALL MODELS TRAINED SUCCESSFULLY!")
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
