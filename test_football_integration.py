"""
Test Football Integration with Multi-Sport Architecture

Tests loading existing football models and making predictions.
"""

from pathlib import Path
from sports.football.football_predictor import FootballPredictor

def test_football_integration():
    """Test football predictor integration."""
    print("=" * 80)
    print("TESTING FOOTBALL INTEGRATION")
    print("=" * 80)

    # Initialize predictor
    print("\n1. Initializing Football predictor...")
    predictor = FootballPredictor()

    # Load existing models
    print("\n2. Loading existing football models...")
    models_path = Path("models/football_models.joblib")

    if not models_path.exists():
        print(f"ERROR: Models not found at {models_path}")
        return False

    try:
        predictor.load_models(models_path)
        print("   Models loaded successfully!")
    except Exception as e:
        print(f"   ERROR loading models: {e}")
        return False

    # Test predictions
    print("\n3. Testing predictions...")
    test_matches = [
        {'home': 'Arsenal', 'away': 'Chelsea', 'league': 'E0'},
        {'home': 'Man City', 'away': 'Liverpool', 'league': 'E0'},
        {'home': 'Bayern Munich', 'away': 'Dortmund', 'league': 'D1'}
    ]

    for i, match_info in enumerate(test_matches, 1):
        print(f"\n   Test {i}: {match_info['home']} vs {match_info['away']}")
        print("   " + "-" * 40)

        try:
            prediction = predictor.predict(match_info)

            print(f"   Winner: {prediction['predictions']['Winner']}")
            print(f"   Over 2.5 Goals: {prediction['predictions']['Over 2.5 Goals']}")
            print(f"   BTTS: {prediction['predictions']['BTTS']}")
            print(f"   Probabilities:")
            print(f"     Home: {prediction['probabilities']['Home Win']:.1%}")
            print(f"     Draw: {prediction['probabilities']['Draw']:.1%}")
            print(f"     Away: {prediction['probabilities']['Away Win']:.1%}")
            print(f"   Confidence: {prediction['confidence']}")

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Test markets
    print("\n4. Testing available markets...")
    markets = predictor.get_prediction_markets()
    print(f"   Found {len(markets)} markets:")
    for market in markets:
        print(f"     - {market}")

    # Test teams
    print("\n5. Testing available teams...")
    teams = predictor.get_available_teams()
    print(f"   Found {len(teams)} teams")
    if teams:
        print(f"   Sample teams: {teams[:10]}")

    print("\n" + "=" * 80)
    print("FOOTBALL INTEGRATION TEST COMPLETE!")
    print("=" * 80)

    return True


if __name__ == '__main__':
    success = test_football_integration()
    exit(0 if success else 1)
