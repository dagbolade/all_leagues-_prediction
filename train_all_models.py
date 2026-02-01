"""
Train all sport models - ACTUALLY TRAIN THEM

This trains basketball and NFL models with real feature engineering
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.prediction_engine import UnifiedPredictionEngine
from sports.basketball.basketball_predictor import BasketballPredictor
from sports.nfl.nfl_predictor import NFLPredictor


def train_basketball():
    """Train basketball models."""
    print("\n" + "="*80)
    print("TRAINING BASKETBALL (NBA) MODELS")
    print("="*80 + "\n")

    predictor = BasketballPredictor()

    # Load data
    data_path = Path("data/basketball/raw/nba_sample.csv")

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Run: python create_sample_data.py first")
        return None

    try:
        # Load data
        df = predictor.load_data(data_path)
        print(f"Loaded {len(df)} games\n")

        # Engineer features
        print("Engineering features...")
        df_features = predictor.engineer_features(df)
        print(f"Created {len(predictor.feature_engineer.get_feature_names())} features\n")

        # Train models
        print("Training models...")
        results = predictor.train_models(df_features)

        print("\nTraining Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")

        # Save models
        models_dir = Path("models/basketball")
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / "basketball_models.joblib"

        predictor.save_models(model_path)

        print(f"\n SUCCESS: Basketball models trained and saved!")
        return predictor

    except Exception as e:
        print(f"\n ERROR training basketball models: {e}")
        import traceback
        traceback.print_exc()
        return None


def train_nfl():
    """Train NFL models."""
    print("\n" + "="*80)
    print("TRAINING NFL MODELS")
    print("="*80 + "\n")

    predictor = NFLPredictor()

    # Load data
    data_path = Path("data/nfl/raw/nfl_sample.csv")

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Run: python create_sample_data.py first")
        return None

    try:
        # Load data
        df = predictor.load_data(data_path)
        print(f"Loaded {len(df)} games\n")

        # Engineer features
        print("Engineering features...")
        df_features = predictor.engineer_features(df)
        print(f"Created {len(predictor.feature_engineer.get_feature_names())} features\n")

        # Train models
        print("Training models...")
        results = predictor.train_models(df_features)

        print("\nTraining Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")

        # Save models
        models_dir = Path("models/nfl")
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / "nfl_models.joblib"

        predictor.save_models(model_path)

        print(f"\n SUCCESS: NFL models trained and saved!")
        return predictor

    except Exception as e:
        print(f"\n ERROR training NFL models: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_predictions(basketball_predictor, nfl_predictor):
    """Test predictions with the trained models."""
    print("\n" + "="*80)
    print("TESTING PREDICTIONS")
    print("="*80 + "\n")

    # Test basketball
    if basketball_predictor:
        print("BASKETBALL TEST:")
        print("-" * 40)
        try:
            result = basketball_predictor.predict({
                'home': 'Los Angeles Lakers',
                'away': 'Boston Celtics'
            })
            print(f"Match: Lakers vs Celtics")
            print(f"Prediction: {result}")
        except Exception as e:
            print(f"Basketball prediction error: {e}")

    print()

    # Test NFL
    if nfl_predictor:
        print("NFL TEST:")
        print("-" * 40)
        try:
            result = nfl_predictor.predict({
                'home': 'Kansas City Chiefs',
                'away': 'Buffalo Bills'
            })
            print(f"Match: Chiefs vs Bills")
            print(f"Prediction: {result}")
        except Exception as e:
            print(f"NFL prediction error: {e}")


def main():
    """Main training function."""
    print("\n" * 2)
    print("*" * 80)
    print("*" + "  TRAINING ALL SPORT MODELS".center(78) + "*")
    print("*" * 80)

    # Train Basketball
    basketball_predictor = train_basketball()

    # Train NFL
    nfl_predictor = train_nfl()

    # Test predictions
    test_predictions(basketball_predictor, nfl_predictor)

    # Summary
    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)

    if basketball_predictor:
        print(" Basketball: TRAINED")
    else:
        print(" Basketball: FAILED")

    if nfl_predictor:
        print(" NFL: TRAINED")
    else:
        print(" NFL: FAILED")

    print("\nModels saved in models/ directory")
    print("Ready to make predictions!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
