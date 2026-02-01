"""
Multi-Sport Routes - Extended from existing football routes

Supports: Football, Basketball, Tennis
Uses Advanced Models: XGBoost + CatBoost + LightGBM with Bayesian Optimization
"""

from flask import Blueprint, render_template, request, jsonify
from pathlib import Path
import sys
import joblib
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

multi_sport = Blueprint('multi_sport', __name__)

# Global predictors
predictors = {
    'football': None,
    'basketball': None,
    'tennis': None
}


def load_all_predictors():
    """Load all sport predictors with advanced trained models."""
    global predictors

    # Load Football (your existing advanced system)
    try:
        football_models_path = Path("models/enhanced_processed_data.pkl")
        if football_models_path.exists():
            predictors['football'] = joblib.load(football_models_path)
            logger.info("[Football] Advanced model loaded")
        else:
            logger.warning("[Football] Models not found")
    except Exception as e:
        logger.error(f"[Football] Error: {e}")

    # Load Basketball Advanced Models (XGBoost + CatBoost + LightGBM)
    try:
        basketball_advanced_path = Path("models/basketball/basketball_advanced_models.joblib")
        if basketball_advanced_path.exists():
            predictors['basketball'] = joblib.load(basketball_advanced_path)
            logger.info("[Basketball] Advanced models loaded (XGBoost + CatBoost + LightGBM)")
        else:
            # Fallback to basic model
            basketball_basic_path = Path("models/basketball/basketball_models.joblib")
            if basketball_basic_path.exists():
                predictors['basketball'] = joblib.load(basketball_basic_path)
                logger.info("[Basketball] Basic model loaded")
            else:
                logger.warning("[Basketball] No models found")
    except Exception as e:
        logger.error(f"[Basketball] Error: {e}")

    # Load Tennis Advanced Models (XGBoost + CatBoost + LightGBM)
    try:
        tennis_advanced_path = Path("models/tennis/tennis_advanced_models.joblib")
        if tennis_advanced_path.exists():
            predictors['tennis'] = joblib.load(tennis_advanced_path)
            logger.info("[Tennis] Advanced models loaded (XGBoost + CatBoost + LightGBM)")
            # Log metrics
            if 'metrics' in predictors['tennis']:
                metrics = predictors['tennis']['metrics']
                logger.info(f"[Tennis] Accuracy: {metrics.get('winner', {}).get('accuracy', 0):.2%}")
        else:
            # Fallback to basic model
            tennis_basic_path = Path("models/tennis/tennis_models.joblib")
            if tennis_basic_path.exists():
                predictors['tennis'] = joblib.load(tennis_basic_path)
                logger.info("[Tennis] Basic model loaded")
            else:
                logger.warning("[Tennis] No models found")
    except Exception as e:
        logger.error(f"[Tennis] Error: {e}")


@multi_sport.route('/')
def home():
    """Multi-sport home page."""
    return render_template('multi_sport/index.html')


@multi_sport.route('/sport/<sport_name>')
def sport_page(sport_name):
    """Sport-specific prediction page."""
    if sport_name not in ['football', 'basketball', 'tennis']:
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
