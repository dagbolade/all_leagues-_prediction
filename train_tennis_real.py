"""Train Tennis models with REAL ATP/WTA data (25,140 matches)."""

from pathlib import Path
from sports.tennis.tennis_predictor import TennisPredictor

def main():
    print("=" * 80)
    print("TRAINING TENNIS MODELS - REAL ATP/WTA DATA")
    print("=" * 80)

    predictor = TennisPredictor()

    print("\n1. Loading REAL tennis data (25,140 matches)...")
    data_path = Path("data/tennis/raw/tennis_real_data.csv")
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
    models_dir = Path("models/tennis")
    models_dir.mkdir(parents=True, exist_ok=True)
    predictor.save_models(models_dir / "tennis_models.joblib")

    print("\n5. Testing predictions...")
    test_matches = [
        {'player1': 'Novak Djokovic', 'player2': 'Carlos Alcaraz', 'surface': 'Hard'},
        {'player1': 'Iga Swiatek', 'player2': 'Aryna Sabalenka', 'surface': 'Clay'}
    ]

    for match in test_matches:
        result = predictor.predict(match)
        print(f"\n   {match['player1']} vs {match['player2']} ({match['surface']})")
        print(f"   Winner: {result['predictions']['Winner']}")
        print(f"   Sets: {result['predictions']['Sets']}")
        print(f"   Confidence: {result['confidence']}")

    print("\n" + "=" * 80)
    print("TENNIS MODELS TRAINED WITH REAL DATA!")
    print("=" * 80)


if __name__ == '__main__':
    main()
