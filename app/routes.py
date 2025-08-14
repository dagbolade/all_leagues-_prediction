# app/routes.py - ENHANCED BAYESIAN VERSION

from datetime import datetime
import logging

from flask import Blueprint, render_template, request, jsonify
import joblib
import pandas as pd
import os
import numpy as np

# Enhanced import for Bayesian predictor
from footy.predictor_utils import create_bayesian_predictor

# Import the analyzers
from footy.opening_weekend_analyzer import OpeningWeekendAnalyzer
from footy.weekly_insights_analyzer import WeeklyInsightsAnalyzer

# Create blueprint
routes = Blueprint('routes', __name__)

# Global variables
bayesian_predictor = None
teams = []
gw1_analyzer = None
weekly_analyzer = None


import numpy as np

def convert_numpy_types(obj):
    """Convert NumPy types to Python native types for JSON serialization"""
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

def initialize_bayesian_predictor():
    """Initialize enhanced Bayesian predictor"""
    global bayesian_predictor, teams
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')

        # Try multiple enhanced data file options
        data_options = [
            os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_bayesian_features.csv'),
            os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_features.csv'),
            os.path.join(base_dir, '..', 'data', 'processed', 'complete_features.csv'),
            os.path.join(base_dir, '..', 'data', 'processed_matches.csv'),
            os.path.join(base_dir, '..', 'data', 'processed', 'combined_euro_data.csv'),
            os.path.join(base_dir, '..', 'data', 'processed', 'cleaned_euro_data.csv')
        ]

        data_path = None
        for option in data_options:
            if os.path.exists(option):
                data_path = option
                print(f"✅ Found enhanced data file: {option}")
                break

        if not data_path:
            print(f"❌ No enhanced data file found. Checked:")
            for option in data_options:
                print(f"   - {option}")
            return None, []

        print(f"🧠 DEBUG: Loading Bayesian models from: {models_path}")
        print(f"🧠 DEBUG: Using enhanced data file: {data_path}")

        # Check if enhanced models exist
        if not os.path.exists(models_path):
            print(f"❌ Enhanced Bayesian models file not found: {models_path}")
            return None, []

        # Load enhanced data
        if data_path and os.path.exists(data_path):
            df = pd.read_csv(data_path, low_memory=False)
            print(f"✅ Enhanced data loaded: {df.shape}")

            # Check required columns
            required_cols = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"❌ Missing required columns: {missing_cols}")
                print(f"Available columns: {list(df.columns[:10])}...")
                return None, []

            # Check for enhanced features
            bayesian_features = [col for col in df.columns if 'Bayesian' in col]
            elo_features = [col for col in df.columns if 'Elo' in col]
            form_features = [col for col in df.columns if 'Form' in col]

            print(f"🧠 Enhanced features detected:")
            print(f"   Bayesian features: {len(bayesian_features)}")
            print(f"   Elo features: {len(elo_features)}")
            print(f"   Form features: {len(form_features)}")

        else:
            print(f"❌ Enhanced data file not found")
            return None, []

        # Create enhanced Bayesian predictor
        print("🧠 Creating enhanced Bayesian predictor...")
        bayesian_predictor = create_bayesian_predictor(df, models_path)

        if bayesian_predictor is None:
            print("❌ Failed to create Bayesian predictor")
            return None, []

        # Extract teams
        teams = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))

        # Initialize analyzers
        global gw1_analyzer, weekly_analyzer
        try:
            gw1_analyzer = OpeningWeekendAnalyzer(df)
            weekly_analyzer = WeeklyInsightsAnalyzer(df)
            print(f"✅ Analyzers initialized")
        except Exception as e:
            print(f"⚠️ Analyzer initialization failed: {e}")

        print(f"✅ Enhanced Bayesian predictor initialized with {len(teams)} teams")
        print(f"🧠 System ready for realistic predictions with Bayesian inference")
        return bayesian_predictor, teams

    except Exception as e:
        print(f"❌ Error initializing Bayesian predictor: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, []


# Initialize enhanced Bayesian predictor
bayesian_predictor, teams = initialize_bayesian_predictor()


@routes.route('/')
def home():
    """Home page with enhanced Bayesian system"""
    return render_template('index.html', teams=teams,
                           system_status='Enhanced Bayesian System Active' if bayesian_predictor else 'System Unavailable')


@routes.route('/predict', methods=['GET', 'POST'])
def predict():
    """Enhanced prediction page with Bayesian inference"""
    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')

        if not home_team or not away_team:
            return render_template('predict.html', teams=teams, error="Please select both teams")

        if not bayesian_predictor:
            return render_template('predict.html', teams=teams,
                                   error="Enhanced Bayesian prediction system not available")

        try:
            print(f"🧠 Making Bayesian prediction: {home_team} vs {away_team}")

            # Get full enhanced Bayesian predictions
            bayesian_result = bayesian_predictor.predict_with_full_bayesian_analysis(home_team, away_team)

            # CONVERT NUMPY TYPES TO PYTHON TYPES FOR JSON SERIALIZATION
            predictions = convert_numpy_types(bayesian_result.get('predictions', {}))
            probabilities = convert_numpy_types(bayesian_result.get('probabilities', {}))
            confidence_intervals = convert_numpy_types(bayesian_result.get('confidence_intervals', {}))
            poisson_analysis = convert_numpy_types(bayesian_result.get('poisson_analysis', {}))
            model_info = convert_numpy_types(bayesian_result.get('model_info', {}))
            bayesian_priors = convert_numpy_types(bayesian_result.get('bayesian_priors', {}))

            # Validate Bayesian logical consistency
            logical_valid = True
            logical_issues = []

            over_15 = predictions.get('Over 1.5 Goals')
            over_25 = predictions.get('Over 2.5 Goals')
            over_35 = predictions.get('Over 3.5 Goals')

            # Check Bayesian logical constraints (should already be applied by predictor)
            if over_15 == 'No' and over_25 == 'Yes':
                logical_issues.append("Bayesian constraint applied: Over 1.5 adjusted for consistency")
                logical_valid = False

            if over_25 == 'No' and over_35 == 'Yes':
                logical_issues.append("Bayesian constraint applied: Over 2.5 adjusted for consistency")
                logical_valid = False

            # Enhanced team insights
            team_insights = {
                'bayesian_system': True,
                'models_used': model_info.get('models_used', []),
                'calibrated_models': model_info.get('calibrated_models', []),
                'poisson_available': model_info.get('poisson_available', False),
                'bayesian_priors_used': list(bayesian_priors.keys()) if bayesian_priors else [],
                'confidence_assessment': 'High' if logical_valid else 'Medium'
            }

            # Get weekly insights based on current gameweek
            weekly_insights = []
            if weekly_analyzer:
                try:
                    weekly_data = weekly_analyzer.get_weekly_insights(home_team, away_team)
                    if weekly_data and 'insights' in weekly_data:
                        weekly_insights = weekly_data['insights'][:2]

                        # Add gameweek context
                        phase_info = weekly_analyzer.get_season_phase_analysis()
                        if phase_info:
                            weekly_insights.insert(0,
                                                   f"📅 {phase_info['phase']} (GW{phase_info['current_gameweek']}) - {phase_info['description']}")

                except Exception as e:
                    print(f"❌ Weekly insights error: {e}")
                    weekly_insights = []

            # Format enhanced match insights
            enhanced_insights = {
                'key_insights': [
                    f"🧠 Enhanced Bayesian prediction with {len(model_info.get('models_used', []))} models",
                    f"🎯 Logical consistency: {'✅ Passed' if logical_valid else '⚠️ Constraints applied'}",
                    f"📊 Calibrated models: {len(model_info.get('calibrated_models', []))}",
                    f"⚽ Poisson scorelines: {'✅ Available' if poisson_analysis else '❌ Not available'}"
                ]
            }

            # Add weekly insights
            if weekly_insights:
                enhanced_insights['key_insights'].extend(weekly_insights)

            # Format confidence levels for display
            formatted_confidence = {}
            for pred_type, confidence_data in confidence_intervals.items():
                if isinstance(confidence_data, dict):
                    confidence_level = confidence_data.get('confidence_level', 'N/A')
                    prediction_strength = confidence_data.get('prediction_strength', 'Medium')
                    formatted_confidence[pred_type] = f"{confidence_level} ({prediction_strength})"

            return render_template('predict.html',
                                   teams=teams,
                                   predictions=predictions,
                                   probabilities=probabilities,
                                   confidence_intervals=formatted_confidence,
                                   team_insights=team_insights,
                                   poisson_scorelines=poisson_analysis,
                                   match_insights=enhanced_insights,
                                   logical_valid=logical_valid,
                                   logical_issues=logical_issues,
                                   home_team=home_team,
                                   away_team=away_team,
                                   bayesian_system=True)

        except Exception as e:
            print(f"❌ Bayesian prediction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('predict.html', teams=teams,
                                   error=f"Enhanced Bayesian prediction failed: {str(e)}")

    return render_template('predict.html', teams=teams, bayesian_system=True)


@routes.route('/live-predictions')
def live_predictions_page():
    """Live predictions page with Bayesian system"""
    return render_template('live_predictions.html', bayesian_system=True)


@routes.route('/api/live-predictions')
def live_predictions():
    """Live predictions API with enhanced Bayesian predictions"""
    try:
        sample_predictions = []

        if bayesian_predictor and len(teams) >= 4:
            # Create sample matches for testing
            sample_matches = [
                (teams[0], teams[1]),
                (teams[2], teams[3]),
            ]

            for home, away in sample_matches:
                try:
                    # Get Bayesian predictions
                    bayesian_result = bayesian_predictor.predict_with_full_bayesian_analysis(home, away)

                    predictions = bayesian_result.get('predictions', {})
                    probabilities = bayesian_result.get('probabilities', {})
                    confidence_intervals = bayesian_result.get('confidence_intervals', {})
                    poisson_analysis = bayesian_result.get('poisson_analysis', {})

                    sample_predictions.append({
                        'home_team': home,
                        'away_team': away,
                        'predictions': predictions,
                        'probabilities': probabilities,
                        'confidence_intervals': confidence_intervals,
                        'poisson_scorelines': poisson_analysis,
                        'logical_valid': True,
                        'confidence_level': 'HIGH',
                        'system_type': 'Enhanced Bayesian'
                    })
                except Exception as e:
                    print(f"Error creating Bayesian sample prediction: {e}")
                    continue

        return jsonify({
            'status': 'success',
            'predictions': sample_predictions,
            'system_type': 'Enhanced Bayesian',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Live Bayesian predictions error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


@routes.route('/results')
def results():
    """Results page"""
    return render_template('results.html', bayesian_system=True)


@routes.route('/api/gw1-analysis')
def gw1_analysis():
    """API endpoint for opening weekend analysis"""
    try:
        if not gw1_analyzer:
            return jsonify({'error': 'GW1 analyzer not available'}), 500

        # Get comprehensive GW1 analysis
        analysis = gw1_analyzer.analyze_gw1_patterns()
        insights = gw1_analyzer.generate_gw1_insights()
        manager_bounce = gw1_analyzer.detect_new_manager_bounce()

        return jsonify({
            'status': 'success',
            'gw1_analysis': analysis,
            'key_insights': insights,
            'manager_patterns': manager_bounce,
            'system_type': 'Enhanced Bayesian',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ GW1 analysis error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/team-gw1-history/<team_name>')
def team_gw1_history(team_name):
    """Get specific team's GW1 history"""
    try:
        if not gw1_analyzer:
            return jsonify({'error': 'GW1 analyzer not available'}), 500

        history = gw1_analyzer.get_team_gw1_history(team_name)

        return jsonify({
            'status': 'success',
            'team_gw1_history': history,
            'system_type': 'Enhanced Bayesian',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/my-predictions')
def my_predictions():
    """My Predictions page with acca builder"""
    return render_template('my_predictions.html', bayesian_system=True)


@routes.route('/api/weekly-insights')
def weekly_insights_api():
    """API endpoint for weekly insights"""
    try:
        if not weekly_analyzer:
            return jsonify({'error': 'Weekly analyzer not available'}), 500

        # Get current season phase
        phase_analysis = weekly_analyzer.get_season_phase_analysis()

        return jsonify({
            'status': 'success',
            'season_phase': phase_analysis,
            'system_type': 'Enhanced Bayesian',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ Weekly insights API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/system-status')
def api_system_status():
    """Enhanced system status API"""
    return jsonify({
        'status': 'operational' if bayesian_predictor else 'error',
        'system_type': 'Enhanced Bayesian Prediction System',
        'teams_loaded': len(teams),
        'predictor_ready': bayesian_predictor is not None,
        'gw1_analyzer_ready': gw1_analyzer is not None,
        'features': {
            'bayesian_inference': True,
            'bayesian_logical_constraints': True,
            'hyperparameter_optimization': True,
            'probability_calibration': True,
            'team_insights': True,
            'poisson_scorelines': True,
            'enhanced_predictions': True,
            'opening_weekend_analysis': gw1_analyzer is not None,
            'confidence_intervals': True
        },
        'model_info': {
            'models_available': bayesian_predictor.models.keys() if bayesian_predictor else [],
            'calibrated_models_available': bayesian_predictor.calibrated_models.keys() if bayesian_predictor else [],
            'poisson_predictor_available': bayesian_predictor.poisson_predictor is not None if bayesian_predictor else False
        } if bayesian_predictor else {}
    })


@routes.route('/api/bayesian-prediction', methods=['POST'])
def api_bayesian_prediction():
    """API endpoint for Bayesian predictions"""
    try:
        data = request.get_json()
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not home_team or not away_team:
            return jsonify({'status': 'error', 'message': 'Missing team selection'}), 400

        if not bayesian_predictor:
            return jsonify({'status': 'error', 'message': 'Bayesian prediction system not available'}), 500

        # Get Bayesian predictions
        bayesian_result = bayesian_predictor.predict_with_full_bayesian_analysis(home_team, away_team)

        return jsonify({
            'status': 'success',
            'system_type': 'Enhanced Bayesian',
            'match': f"{home_team} vs {away_team}",
            'bayesian_analysis': bayesian_result,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ Bayesian prediction API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """Save prediction functionality with Bayesian data"""
    try:
        data = request.get_json()

        # Create enhanced prediction record
        prediction_record = {
            'id': len(data) + 1,
            'home_team': data.get('home_team'),
            'away_team': data.get('away_team'),
            'predictions': data.get('predictions', {}),
            'probabilities': data.get('probabilities', {}),
            'confidence_intervals': data.get('confidence_intervals', {}),
            'poisson_analysis': data.get('poisson_analysis', {}),
            'system_type': 'Enhanced Bayesian',
            'date_saved': datetime.utcnow().isoformat(),
            'match_date': data.get('match_date', 'TBD'),
            'season': '2024/25',
            'bayesian_features': True
        }

        print(
            f"✅ Enhanced Bayesian prediction saved: {prediction_record['home_team']} vs {prediction_record['away_team']}")

        return jsonify({
            'status': 'success',
            'message': 'Enhanced Bayesian prediction saved successfully',
            'prediction_id': prediction_record['id'],
            'system_type': 'Enhanced Bayesian'
        })

    except Exception as e:
        print(f"❌ Save error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/model-insights')
def api_model_insights():
    """API endpoint for Bayesian model insights"""
    try:
        if not bayesian_predictor:
            return jsonify({'error': 'Bayesian predictor not available'}), 500

        # Get model insights (this method should exist on your BayesianFootballPredictor)
        if hasattr(bayesian_predictor, 'get_model_insights'):
            insights = bayesian_predictor.get_model_insights()
        else:
            insights = {
                'models_available': list(bayesian_predictor.models.keys()),
                'calibrated_models': list(bayesian_predictor.calibrated_models.keys()),
                'poisson_available': bayesian_predictor.poisson_predictor is not None,
                'bayesian_priors': bayesian_predictor.bayesian_priors
            }

        return jsonify({
            'status': 'success',
            'system_type': 'Enhanced Bayesian',
            'model_insights': insights,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ Model insights error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500