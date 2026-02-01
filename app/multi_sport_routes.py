"""
Multi-Sport Routes - Extended from existing football routes

Supports: Football, Basketball, NFL, Tennis
"""

from flask import Blueprint, render_template, request, jsonify
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import predictors
from footy.predictor_utils import create_bayesian_predictor
from sports.basketball.basketball_predictor import BasketballPredictor
from sports.nfl.nfl_predictor import NFLPredictor
from sports.tennis.tennis_predictor import TennisPredictor

multi_sport = Blueprint('multi_sport', __name__)

# Global predictors
predictors = {
    'football': None,
    'basketball': None,
    'nfl': None,
    'tennis': None
}


def load_all_predictors():
    """Load all sport predictors with their trained models."""
    global predictors

    # Load Football (existing system)
    try:
        football_models_path = Path("models/football_models.joblib")
        if football_models_path.exists():
            # Load using existing method
            import joblib
            football_data = joblib.load(football_models_path)
            # Create predictor with loaded data
            # Note: This needs the processed data to work properly
            print("[Football] Models found but need data loader integration")
    except Exception as e:
        print(f"[Football] Error: {e}")

    # Load Basketball
    try:
        basketball = BasketballPredictor()
        basketball.load_models(Path("models/basketball/basketball_models.joblib"))
        predictors['basketball'] = basketball
        print("[Basketball] Loaded")
    except Exception as e:
        print(f"[Basketball] Error: {e}")

    # Load NFL
    try:
        nfl = NFLPredictor()
        nfl.load_models(Path("models/nfl/nfl_models.joblib"))
        predictors['nfl'] = nfl
        print("[NFL] Loaded")
    except Exception as e:
        print(f"[NFL] Error: {e}")

    # Load Tennis
    try:
        tennis = TennisPredictor()
        tennis.load_models(Path("models/tennis/tennis_models.joblib"))
        predictors['tennis'] = tennis
        print("[Tennis] Loaded")
    except Exception as e:
        print(f"[Tennis] Error: {e}")


@multi_sport.route('/')
def home():
    """Multi-sport home page."""
    return render_template('multi_sport/index.html')


@multi_sport.route('/sport/<sport_name>')
def sport_page(sport_name):
    """Sport-specific prediction page."""
    if sport_name not in ['football', 'basketball', 'nfl', 'tennis']:
        return "Sport not found", 404

    return render_template(f'multi_sport/{sport_name}.html', sport=sport_name)


@multi_sport.route('/api/<sport>/predict', methods=['POST'])
def predict(sport):
    """Make prediction for any sport."""
    try:
        data = request.json

        if sport not in predictors or predictors[sport] is None:
            return jsonify({'error': f'{sport} predictor not loaded'}), 500

        predictor = predictors[sport]

        # Make prediction
        if sport == 'tennis':
            match_info = {
                'player1': data.get('player1'),
                'player2': data.get('player2'),
                'surface': data.get('surface', 'Hard')
            }
        else:
            match_info = {
                'home': data.get('home'),
                'away': data.get('away')
            }

        result = predictor.predict(match_info)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@multi_sport.route('/api/<sport>/teams')
def get_teams(sport):
    """Get available teams/players for a sport."""
    try:
        if sport not in predictors or predictors[sport] is None:
            return jsonify({'teams': []}), 200

        teams = predictors[sport].get_available_teams()
        return jsonify({'teams': teams})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Initialize predictors when module loads
load_all_predictors()
