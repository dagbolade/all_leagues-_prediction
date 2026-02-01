# app/modern_routes.py - MODERN PROFESSIONAL FLASK INTERFACE

from datetime import datetime
import logging
from flask import Blueprint, render_template, request, jsonify, flash
import joblib
import pandas as pd
import os
import numpy as np
from functools import lru_cache
import time

# Enhanced imports
from footy.predictor_utils import create_bayesian_predictor
from footy.intelligent_feature_selector import IntelligentFeatureSelector
from footy.fast_model_training import FastBayesianFootballPredictor

# Create blueprint
modern_routes = Blueprint('modern_routes', __name__)

# Global variables with caching
predictor = None
teams = []
performance_cache = {}
last_cache_update = 0

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModernPredictorManager:
    """Modern predictor with caching and performance optimization."""

    def __init__(self):
        self.predictor = None
        self.teams = []
        self.model_info = {}
        self.cache = {}
        self.last_update = 0

    @lru_cache(maxsize=100)
    def get_cached_prediction(self, home_team: str, away_team: str) -> dict:
        """Cache predictions to improve response time."""
        cache_key = f"{home_team}_vs_{away_team}"

        if cache_key in self.cache:
            cache_time = self.cache[cache_key].get('timestamp', 0)
            # Cache valid for 1 hour
            if time.time() - cache_time < 3600:
                return self.cache[cache_key]['data']

        # Generate new prediction
        if self.predictor:
            try:
                result = self.predictor.predict_with_full_bayesian_analysis(home_team, away_team)

                # Cache the result
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }

                return result
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                return {}

        return {}

    def initialize_fast_predictor(self):
        """Initialize with fast models for better performance."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # Try fast models first
            fast_models_path = os.path.join(base_dir, '..', 'models', 'fast_football_models.joblib')
            regular_models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')

            models_path = fast_models_path if os.path.exists(fast_models_path) else regular_models_path

            # Data file options
            data_options = [
                os.path.join(base_dir, '..', 'data', 'processed', 'optimized_features.csv'),
                os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_bayesian_features.csv'),
                os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_features.csv')
            ]

            data_path = None
            for option in data_options:
                if os.path.exists(option):
                    data_path = option
                    break

            if not data_path or not os.path.exists(models_path):
                logger.error("Required files not found")
                return False

            # Load data
            df = pd.read_csv(data_path, low_memory=False)

            # Create predictor
            self.predictor = create_bayesian_predictor(df, models_path)

            if self.predictor:
                # Extract teams
                self.teams = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))

                # Get model info
                try:
                    model_data = joblib.load(models_path)
                    self.model_info = {
                        'total_models': len(model_data.get('models', {})),
                        'fast_training': model_data.get('metadata', {}).get('fast_training', False),
                        'feature_count': len(model_data.get('feature_columns', [])),
                        'training_date': model_data.get('metadata', {}).get('training_date', 'Unknown')
                    }
                except:
                    self.model_info = {'total_models': 0, 'fast_training': False}

                logger.info(f"✅ Modern predictor initialized with {len(self.teams)} teams")
                return True
            else:
                logger.error("Failed to create predictor")
                return False

        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False


# Initialize the modern predictor manager
predictor_manager = ModernPredictorManager()
predictor_manager.initialize_fast_predictor()


@modern_routes.route('/')
def modern_home():
    """Modern home page with enhanced UI."""
    return render_template('modern/index.html',
                         teams=predictor_manager.teams,
                         model_info=predictor_manager.model_info)


@modern_routes.route('/predict')
def modern_predict():
    """Modern prediction interface."""
    return render_template('modern/predict.html',
                         teams=predictor_manager.teams,
                         model_info=predictor_manager.model_info)


@modern_routes.route('/api/predict', methods=['POST'])
def api_modern_predict():
    """Modern prediction API with caching and error handling."""
    try:
        data = request.get_json()
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not home_team or not away_team:
            return jsonify({
                'success': False,
                'error': 'Both teams must be selected'
            }), 400

        if not predictor_manager.predictor:
            return jsonify({
                'success': False,
                'error': 'Prediction system not available'
            }), 500

        start_time = time.time()

        # Get cached prediction
        result = predictor_manager.get_cached_prediction(home_team, away_team)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to generate prediction'
            }), 500

        prediction_time = time.time() - start_time

        # Format response
        response = {
            'success': True,
            'match': f"{home_team} vs {away_team}",
            'predictions': result.get('predictions', {}),
            'probabilities': result.get('probabilities', {}),
            'confidence_intervals': result.get('confidence_intervals', {}),
            'poisson_analysis': result.get('poisson_analysis', {}),
            'model_info': result.get('model_info', {}),
            'performance': {
                'prediction_time': round(prediction_time, 3),
                'cached': prediction_time < 0.1
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        # Convert numpy types for JSON serialization
        response = convert_numpy_types(response)

        return jsonify(response)

    except Exception as e:
        logger.error(f"Prediction API error: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@modern_routes.route('/analytics')
def modern_analytics():
    """Modern analytics dashboard."""
    return render_template('modern/analytics.html',
                         model_info=predictor_manager.model_info,
                         cache_stats=get_cache_stats())


@modern_routes.route('/api/analytics/performance')
def api_analytics_performance():
    """Performance analytics API."""
    try:
        cache_stats = get_cache_stats()

        performance_data = {
            'cache_hit_rate': cache_stats['hit_rate'],
            'total_predictions': cache_stats['total_predictions'],
            'average_response_time': cache_stats['avg_response_time'],
            'model_info': predictor_manager.model_info,
            'system_status': {
                'predictor_ready': predictor_manager.predictor is not None,
                'teams_loaded': len(predictor_manager.teams),
                'cache_size': len(predictor_manager.cache)
            }
        }

        return jsonify({
            'success': True,
            'data': performance_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@modern_routes.route('/api/teams/search')
def api_teams_search():
    """Team search API for autocomplete."""
    query = request.args.get('q', '').lower()

    if not query:
        return jsonify({'teams': predictor_manager.teams[:20]})

    # Filter teams based on query
    filtered_teams = [team for team in predictor_manager.teams
                     if query in team.lower()]

    return jsonify({'teams': filtered_teams[:10]})


@modern_routes.route('/optimize')
def optimize_page():
    """Model optimization interface."""
    return render_template('modern/optimize.html')


@modern_routes.route('/api/optimize/features', methods=['POST'])
def api_optimize_features():
    """Feature optimization API."""
    try:
        # Run feature optimization
        from footy.intelligent_feature_selector import optimize_features_for_speed

        # This could take a few minutes
        optimized_df, feature_data = optimize_features_for_speed()

        return jsonify({
            'success': True,
            'message': 'Feature optimization completed',
            'results': {
                'original_features': feature_data['metadata']['total_original_features'],
                'optimized_features': feature_data['metadata']['core_feature_count'],
                'reduction_percentage': round((1 - feature_data['metadata']['core_feature_count'] /
                                             feature_data['metadata']['total_original_features']) * 100, 1)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@modern_routes.route('/api/train/fast', methods=['POST'])
def api_train_fast():
    """Fast training API."""
    try:
        from footy.fast_model_training import run_fast_training_pipeline

        # Run fast training
        predictor, model_data, summary = run_fast_training_pipeline()

        # Reinitialize the predictor manager
        predictor_manager.initialize_fast_predictor()

        return jsonify({
            'success': True,
            'message': 'Fast training completed',
            'summary': summary
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def convert_numpy_types(obj):
    """Convert NumPy types to Python native types for JSON serialization."""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def get_cache_stats():
    """Get cache performance statistics."""
    cache = predictor_manager.cache

    if not cache:
        return {
            'hit_rate': 0,
            'total_predictions': 0,
            'avg_response_time': 0
        }

    total_predictions = len(cache)
    recent_predictions = [p for p in cache.values()
                         if time.time() - p['timestamp'] < 3600]  # Last hour

    return {
        'hit_rate': len(recent_predictions) / max(total_predictions, 1) * 100,
        'total_predictions': total_predictions,
        'avg_response_time': 0.1 if recent_predictions else 0  # Estimated
    }


@modern_routes.errorhandler(404)
def not_found(error):
    """Modern 404 page."""
    return render_template('modern/404.html'), 404


@modern_routes.errorhandler(500)
def internal_error(error):
    """Modern 500 page."""
    return render_template('modern/500.html'), 500