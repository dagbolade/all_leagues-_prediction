"""Train Basketball models with REAL NBA data (6,000 games)."""

from pathlib import Path
from sports.basketball.basketball_predictor import BasketballPredictor

def main():
    print("=" * 80)
    print("TRAINING BASKETBALL MODELS - REAL NBA DATA")
    print("=" * 80)

    predictor = BasketballPredictor()

    print("\n1. Loading REAL NBA data (6,000 games)...")
    data_path = Path("data/basketball/raw/nba_real_data.csv")
    raw_data = predictor.load_data(data_path)

    print("\n2. Engineering features...")
    processed_data = predictor.engineer_features(raw_data)

    print("\n3. Training models...")
    results = predictor.train_models(processed_data)

    print(f"\n[OK] Training Results:")
    print(f"   Random Forest: {results['rf_accuracy']:.2%}")
    print(f"   Gradient Boosting: {results['gb_accuracy']:.2%}")
    print(f"   Features: {results['features']}")

    print("\n4. Saving models...")
    models_dir = Path("models/basketball")
    models_dir.mkdir(parents=True, exist_ok=True)
    predictor.save_models(models_dir / "basketball_models.joblib")

    print("\n5. Testing predictions...")
    test_matches = [
        {'home': 'Los Angeles Lakers', 'away': 'Boston Celtics'},
        {'home': 'Golden State Warriors', 'away': 'Phoenix Suns'}
    ]

    for match in test_matches:
        result = predictor.predict(match)
        print(f"\n   {match['home']} vs {match['away']}")
        print(f"   Winner: {result['predictions']['Winner']}")
        print(f"   Spread: {result['predictions']['Spread']}")

    print("\n" + "=" * 80)
    print("BASKETBALL MODELS TRAINED WITH REAL DATA!")
    print("=" * 80)


if __name__ == '__main__':
    main()
