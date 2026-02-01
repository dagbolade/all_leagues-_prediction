"""Train tennis prediction models."""

from pathlib import Path
from sports.tennis.tennis_predictor import TennisPredictor

def main():
    """Train and test tennis models."""
    print("=" * 80)
    print("TRAINING TENNIS MODELS")
    print("=" * 80)

    # Initialize predictor
    print("\n1. Initializing Tennis predictor...")
    predictor = TennisPredictor()

    # Load REAL data
    print("\n2. Loading REAL tennis data...")
    data_path = Path("data/tennis/raw/tennis_real_data.csv")
    raw_data = predictor.load_data(data_path)

    # Engineer features
    print("\n3. Engineering features...")
    processed_data = predictor.engineer_features(raw_data)

    # Train models
    print("\n4. Training models...")
    results = predictor.train_models(processed_data)

    print(f"\n[OK] Training Results:")
    print(f"   Random Forest: {results['rf_accuracy']:.2%}")
    print(f"   Gradient Boosting: {results['gb_accuracy']:.2%}")
    print(f"   Features: {results['features']}")
    print(f"   Training samples: {results['training_samples']}")

    # Save models
    print("\n5. Saving models...")
    models_dir = Path("models/tennis")
    models_dir.mkdir(parents=True, exist_ok=True)
    predictor.save_models(models_dir / "tennis_models.joblib")

    # Test predictions
    print("\n6. Testing predictions...")
    test_matches = [
        {'player1': 'Novak Djokovic', 'player2': 'Carlos Alcaraz', 'surface': 'Hard'},
        {'player1': 'Iga Swiatek', 'player2': 'Aryna Sabalenka', 'surface': 'Clay'},
        {'player1': 'Daniil Medvedev', 'player2': 'Jannik Sinner', 'surface': 'Grass'}
    ]

    for i, match_info in enumerate(test_matches, 1):
        print(f"\n   Test {i}: {match_info['player1']} vs {match_info['player2']} ({match_info['surface']})")
        result = predictor.predict(match_info)

        print(f"   Winner: {result['predictions']['Winner']}")
        print(f"   Sets: {result['predictions']['Sets']}")

        p1_prob = result['probabilities'][f"{match_info['player1']} Win"]
        p2_prob = result['probabilities'][f"{match_info['player2']} Win"]
        print(f"   Probabilities: {p1_prob:.1%} / {p2_prob:.1%}")
        print(f"   Confidence: {result['confidence']}")

    print("\n" + "=" * 80)
    print("TENNIS MODELS TRAINED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == '__main__':
    main()
