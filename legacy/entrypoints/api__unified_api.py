"""
Unified Multi-Sport Prediction API

Single Flask application serving predictions for:
- Football (22 leagues)
- Basketball (NBA)
- NFL

Endpoints:
- GET  /api/sports - List available sports
- GET  /api/{sport}/teams - Get teams for a sport
- POST /api/{sport}/predict - Get prediction for a match
- GET  /api/{sport}/markets - Get prediction markets
- GET  /api/status - System status
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path
import sys
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.prediction_engine import UnifiedPredictionEngine
from sports.basketball.basketball_predictor import BasketballPredictor
from sports.nfl.nfl_predictor import NFLPredictor
from sports.football.football_predictor import FootballPredictor
from sports.tennis.tennis_predictor import TennisPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__,
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)  # Enable CORS for all routes

# Initialize prediction engine
engine = UnifiedPredictionEngine()

# Global flag to track initialization
models_loaded = False


def initialize_predictors():
    """Initialize and register all sport predictors."""
    global models_loaded

    if models_loaded:
        return

    logger.info("Initializing sport predictors...")

    try:
        # Initialize Basketball
        basketball_predictor = BasketballPredictor()
        engine.register_sport('basketball', basketball_predictor)

        # Initialize NFL
        nfl_predictor = NFLPredictor()
        engine.register_sport('nfl', nfl_predictor)

        # Initialize Football
        football_predictor = FootballPredictor()
        engine.register_sport('football', football_predictor)

        # Initialize Tennis
        tennis_predictor = TennisPredictor()
        engine.register_sport('tennis', tennis_predictor)

        # Try to load saved models
        models_dir = Path("models")
        if models_dir.exists():
            engine.load_all_models(models_dir)
            logger.info("Models loaded successfully")

        models_loaded = True
        logger.info("All predictors initialized")

    except Exception as e:
        logger.error(f"Error initializing predictors: {e}")
        raise


#==============================================================================
# WEB ROUTES (Frontend)
#==============================================================================

@app.route('/')
def index():
    """Homepage - sport selection."""
    return render_template('index.html')


@app.route('/<sport>')
def sport_page(sport):
    """Sport-specific prediction page."""
    if sport not in ['football', 'basketball', 'nfl']:
        return "Sport not found", 404

    return render_template(f'{sport}/predict.html')


#==============================================================================
# API ROUTES
#==============================================================================

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get API status and available sports."""
    try:
        initialize_predictors()

        status = {
            'status': 'online',
            'version': '1.0.0',
            'available_sports': engine.get_available_sports(),
            'models_loaded': models_loaded
        }

        return jsonify(status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sports', methods=['GET'])
def get_sports():
    """Get list of available sports with details."""
    try:
        initialize_predictors()

        sports_info = engine.get_all_sports_info()

        return jsonify({
            'sports': sports_info,
            'count': len(sports_info)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/<sport>/teams', methods=['GET'])
def get_teams(sport):
    """Get available teams for a sport."""
    try:
        initialize_predictors()

        predictor = engine.get_predictor(sport)

        if not predictor:
            return jsonify({'error': f'Sport not found: {sport}'}), 404

        if not predictor.is_trained:
            return jsonify({
                'error': f'{sport} models not trained yet',
                'teams': []
            }), 200

        teams = predictor.get_available_teams()

        return jsonify({
            'sport': sport,
            'teams': teams,
            'count': len(teams)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/<sport>/markets', methods=['GET'])
def get_markets(sport):
    """Get available prediction markets for a sport."""
    try:
        initialize_predictors()

        predictor = engine.get_predictor(sport)

        if not predictor:
            return jsonify({'error': f'Sport not found: {sport}'}), 404

        markets = predictor.get_prediction_markets()

        return jsonify({
            'sport': sport,
            'markets': markets,
            'count': len(markets)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/<sport>/predict', methods=['POST'])
def predict_match(sport):
    """Get prediction for a match."""
    try:
        initialize_predictors()

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields (handle tennis which uses player1/player2)
        if sport == 'tennis':
            if 'player1' not in data or 'player2' not in data:
                return jsonify({'error': 'Missing required fields: player1, player2'}), 400
            match_info = {
                'player1': data['player1'],
                'player2': data['player2'],
                'surface': data.get('surface'),
                'tournament': data.get('tournament'),
                'round': data.get('round')
            }
        else:
            if 'home' not in data or 'away' not in data:
                return jsonify({'error': 'Missing required fields: home, away'}), 400
            match_info = {
                'home': data['home'],
                'away': data['away'],
                'date': data.get('date'),
                'league': data.get('league')
            }

        # Get prediction
        prediction = engine.predict(sport, match_info)

        if not prediction:
            return jsonify({
                'error': f'Prediction failed for {sport}',
                'details': f'Models may not be trained yet'
            }), 500

        return jsonify(prediction), 200

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<sport>/predict/batch', methods=['POST'])
def predict_batch(sport):
    """Get predictions for multiple matches."""
    try:
        initialize_predictors()

        # Get request data
        data = request.get_json()

        if not data or 'matches' not in data:
            return jsonify({'error': 'No matches provided'}), 400

        matches = data['matches']

        if not isinstance(matches, list):
            return jsonify({'error': 'Matches must be a list'}), 400

        # Get predictions
        predictions = engine.predict_batch(sport, matches)

        return jsonify({
            'sport': sport,
            'predictions': predictions,
            'count': len(predictions)
        }), 200

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/<sport>/insights', methods=['GET'])
def get_insights(sport):
    """Get insights for a sport or team."""
    try:
        initialize_predictors()

        team = request.args.get('team')

        predictor = engine.get_predictor(sport)

        if not predictor:
            return jsonify({'error': f'Sport not found: {sport}'}), 404

        insights = predictor.get_insights(team)

        return jsonify(insights), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


#==============================================================================
# ERROR HANDLERS
#==============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


#==============================================================================
# MAIN
#==============================================================================

def create_app():
    """Factory function to create Flask app."""
    return app


if __name__ == '__main__':
    print("\n" + "="*80)
    print("MULTI-SPORT PREDICTION API - STARTING")
    print("="*80)
    print("\nAvailable Endpoints:")
    print("  GET  /                      - Homepage")
    print("  GET  /api/status            - API status")
    print("  GET  /api/sports            - List sports")
    print("  GET  /api/{sport}/teams     - Get teams")
    print("  GET  /api/{sport}/markets   - Get markets")
    print("  POST /api/{sport}/predict   - Get prediction")
    print("  GET  /api/{sport}/insights  - Get insights")
    print("\nSupported Sports:")
    print("  - basketball (NBA)")
    print("  - nfl (NFL)")
    print("  - football (22 leagues)")
    print("  - tennis (ATP/WTA)")
    print("\n" + "="*80)

    # Initialize predictors
    try:
        initialize_predictors()
        print("\nPredictors initialized successfully!")
    except Exception as e:
        print(f"\nWarning: Could not initialize predictors: {e}")
        print("API will still start, but predictions won't work until models are trained.")

    print("\nStarting server...")
    print("Access at: http://localhost:5000")
    print("="*80 + "\n")

    # Get port from environment variable (required for deployment)
    import os
    port = int(os.environ.get('PORT', 5000))

    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )
