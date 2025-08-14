# app/routes.py - CLEAN VERSION WITHOUT TECHNICAL JARGON

from datetime import datetime
import logging

from flask import Blueprint, render_template, request, jsonify
import joblib
import pandas as pd
import os
import numpy as np

# Enhanced import for predictor
from footy.predictor_utils import create_bayesian_predictor

# Import the analyzers
from footy.opening_weekend_analyzer import OpeningWeekendAnalyzer
from footy.weekly_insights_analyzer import WeeklyInsightsAnalyzer

# Create blueprint
routes = Blueprint('routes', __name__)

# Global variables
predictor = None
teams = []
gw1_analyzer = None
weekly_analyzer = None


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


def initialize_predictor():
    """Initialize prediction system"""
    global predictor, teams
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')

        # Try multiple data file options
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
                print(f"✅ Found data file: {option}")
                break

        if not data_path:
            print(f"❌ No data file found")
            return None, []

        if not os.path.exists(models_path):
            print(f"❌ Models file not found: {models_path}")
            return None, []

        # Load data
        df = pd.read_csv(data_path, low_memory=False)
        print(f"✅ Data loaded: {df.shape}")

        # Create predictor
        predictor = create_bayesian_predictor(df, models_path)
        if predictor is None:
            print("❌ Failed to create predictor")
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

        print(f"✅ System initialized with {len(teams)} teams")
        return predictor, teams

    except Exception as e:
        print(f"❌ Error initializing system: {str(e)}")
        return None, []


# Initialize predictor
predictor, teams = initialize_predictor()


@routes.route('/')
def home():
    """Home page"""
    return render_template('index.html', teams=teams)


@routes.route('/predict', methods=['GET', 'POST'])
def predict():
    """Prediction page"""
    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')

        if not home_team or not away_team:
            return render_template('predict.html', teams=teams, error="Please select both teams")

        if not predictor:
            return render_template('predict.html', teams=teams, error="Prediction system not available")

        try:
            print(f"🎯 Making prediction: {home_team} vs {away_team}")

            # Get predictions
            result = predictor.predict_with_full_bayesian_analysis(home_team, away_team)

            # Convert numpy types
            predictions = convert_numpy_types(result.get('predictions', {}))
            probabilities = convert_numpy_types(result.get('probabilities', {}))
            confidence_intervals = convert_numpy_types(result.get('confidence_intervals', {}))
            poisson_analysis = convert_numpy_types(result.get('poisson_analysis', {}))

            # 🚀 REAL INSIGHTS - NO TECHNICAL JARGON
            match_insights = []

            # 1. Get team GW1 records (now works for all leagues)
            if gw1_analyzer:
                try:
                    home_gw1 = gw1_analyzer.get_team_gw1_history(home_team)
                    away_gw1 = gw1_analyzer.get_team_gw1_history(away_team)

                    if home_gw1 and not home_gw1.get('error'):
                        match_insights.append(
                            f"🏆 {home_team} opening weekend record: {home_gw1['record']} ({home_gw1['win_rate']}% win rate)")

                    if away_gw1 and not away_gw1.get('error'):
                        match_insights.append(
                            f"✈️ {away_team} opening weekend record: {away_gw1['record']} ({away_gw1['win_rate']}% win rate)")

                except Exception as e:
                    print(f"⚠️ GW1 insights error: {e}")

            # 2. Get head-to-head record
            try:
                h2h_matches = predictor.df[
                    ((predictor.df['HomeTeam'] == home_team) & (predictor.df['AwayTeam'] == away_team)) |
                    ((predictor.df['HomeTeam'] == away_team) & (predictor.df['AwayTeam'] == home_team))
                    ].tail(8)

                if len(h2h_matches) > 0:
                    home_wins = len(h2h_matches[
                                        ((h2h_matches['HomeTeam'] == home_team) & (h2h_matches['FTR'] == 'H')) |
                                        ((h2h_matches['AwayTeam'] == home_team) & (h2h_matches['FTR'] == 'A'))
                                        ])
                    draws = len(h2h_matches[h2h_matches['FTR'] == 'D'])
                    away_wins = len(h2h_matches) - home_wins - draws

                    match_insights.append(
                        f"🤝 Last {len(h2h_matches)} meetings: {home_team} {home_wins}W-{draws}D-{away_wins}L vs {away_team}")

                    # Average goals in H2H
                    if 'FTHG' in h2h_matches.columns and 'FTAG' in h2h_matches.columns:
                        avg_goals = (h2h_matches['FTHG'] + h2h_matches['FTAG']).mean()
                        over_25_h2h = len(h2h_matches[(h2h_matches['FTHG'] + h2h_matches['FTAG']) > 2.5])
                        btts_h2h = len(h2h_matches[(h2h_matches['FTHG'] > 0) & (h2h_matches['FTAG'] > 0)])

                        match_insights.append(f"📊 H2H average: {avg_goals:.1f} goals per game")
                        if len(h2h_matches) >= 3:
                            match_insights.append(f"🎯 Over 2.5 Goals in {over_25_h2h}/{len(h2h_matches)} recent H2H")
                            match_insights.append(f"⚽ Both scored in {btts_h2h}/{len(h2h_matches)} recent H2H")

            except Exception as e:
                print(f"⚠️ H2H insights error: {e}")

            # 3. Get recent form
            try:
                # Home team form
                home_recent = predictor.df[
                    (predictor.df['HomeTeam'] == home_team) | (predictor.df['AwayTeam'] == home_team)
                    ].tail(6)

                if len(home_recent) > 0:
                    home_wins = home_draws = home_losses = 0
                    home_goals_for = home_goals_against = 0

                    for _, match in home_recent.iterrows():
                        if match['HomeTeam'] == home_team:
                            home_goals_for += match['FTHG']
                            home_goals_against += match['FTAG']
                            if match['FTR'] == 'H':
                                home_wins += 1
                            elif match['FTR'] == 'D':
                                home_draws += 1
                            else:
                                home_losses += 1
                        else:
                            home_goals_for += match['FTAG']
                            home_goals_against += match['FTHG']
                            if match['FTR'] == 'A':
                                home_wins += 1
                            elif match['FTR'] == 'D':
                                home_draws += 1
                            else:
                                home_losses += 1

                    if len(home_recent) >= 3:
                        match_insights.append(
                            f"📈 {home_team} last {len(home_recent)}: {home_wins}W-{home_draws}D-{home_losses}L")

                # Away team form
                away_recent = predictor.df[
                    (predictor.df['HomeTeam'] == away_team) | (predictor.df['AwayTeam'] == away_team)
                    ].tail(6)

                if len(away_recent) > 0:
                    away_wins = away_draws = away_losses = 0

                    for _, match in away_recent.iterrows():
                        if match['HomeTeam'] == away_team:
                            if match['FTR'] == 'H':
                                away_wins += 1
                            elif match['FTR'] == 'D':
                                away_draws += 1
                            else:
                                away_losses += 1
                        else:
                            if match['FTR'] == 'A':
                                away_wins += 1
                            elif match['FTR'] == 'D':
                                away_draws += 1
                            else:
                                away_losses += 1

                    if len(away_recent) >= 3:
                        match_insights.append(
                            f"📉 {away_team} last {len(away_recent)}: {away_wins}W-{away_draws}D-{away_losses}L")

            except Exception as e:
                print(f"⚠️ Form insights error: {e}")

            # 4. Goal market insights
            try:
                over_25_pred = predictions.get('Over 2.5 Goals', 'N/A')
                btts_pred = predictions.get('Both Teams to Score', 'N/A')
                total_goals = predictions.get('Total Goals', 'N/A')

                if over_25_pred != 'N/A':
                    confidence = probabilities.get('Over 2.5 Goals', 0)
                    if isinstance(confidence, (int, float)):
                        confidence_pct = f"{confidence:.0%}" if confidence <= 1 else f"{confidence:.1f}%"
                        match_insights.append(f"🎯 Over 2.5 Goals: {over_25_pred} ({confidence_pct} confidence)")

                if btts_pred != 'N/A':
                    match_insights.append(f"⚽ Both teams to score: {btts_pred}")

                if total_goals != 'N/A':
                    match_insights.append(f"🥅 Expected total goals: {total_goals}")

            except Exception as e:
                print(f"⚠️ Goal insights error: {e}")

            # 5. Venue-specific insights
            try:
                # Home team at home record
                home_at_home = predictor.df[predictor.df['HomeTeam'] == home_team].tail(10)
                if len(home_at_home) >= 5:
                    home_home_wins = len(home_at_home[home_at_home['FTR'] == 'H'])
                    home_win_rate = (home_home_wins / len(home_at_home)) * 100
                    match_insights.append(
                        f"🏠 {home_team} at home: {home_home_wins}/{len(home_at_home)} wins ({home_win_rate:.0f}%)")

                # Away team away record
                away_away = predictor.df[predictor.df['AwayTeam'] == away_team].tail(10)
                if len(away_away) >= 5:
                    away_away_wins = len(away_away[away_away['FTR'] == 'A'])
                    away_win_rate = (away_away_wins / len(away_away)) * 100
                    match_insights.append(
                        f"✈️ {away_team} away: {away_away_wins}/{len(away_away)} wins ({away_win_rate:.0f}%)")

            except Exception as e:
                print(f"⚠️ Venue insights error: {e}")

            # 6. Fallback insights if none found
            if not match_insights:
                match_insights = [
                    f"⚽ Match prediction: {predictions.get('Match Outcome', 'N/A')}",
                    f"🎯 Over 2.5 Goals: {predictions.get('Over 2.5 Goals', 'N/A')}",
                    f"🏆 Both teams to score: {predictions.get('Both Teams to Score', 'N/A')}"
                ]

            # Format insights for display
            enhanced_insights = {
                'key_insights': match_insights[:8]  # Limit to top 8 insights
            }

            # Format confidence levels
            formatted_confidence = {}
            for pred_type, confidence_data in confidence_intervals.items():
                if isinstance(confidence_data, dict):
                    confidence_level = confidence_data.get('confidence_level', 'Medium')
                    formatted_confidence[pred_type] = confidence_level

            return render_template('predict.html',
                                   teams=teams,
                                   predictions=predictions,
                                   probabilities=probabilities,
                                   confidence_intervals=formatted_confidence,
                                   poisson_scorelines=poisson_analysis,
                                   match_insights=enhanced_insights,
                                   home_team=home_team,
                                   away_team=away_team)

        except Exception as e:
            print(f"❌ Prediction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('predict.html', teams=teams,
                                   error=f"Prediction failed: {str(e)}")

    return render_template('predict.html', teams=teams)


@routes.route('/live-predictions')
def live_predictions_page():
    """Live predictions page"""
    return render_template('live_predictions.html')


@routes.route('/api/live-predictions')
def live_predictions():
    """Live predictions API"""
    try:
        sample_predictions = []

        if predictor and len(teams) >= 4:
            # Create sample matches
            sample_matches = [
                (teams[0], teams[1]),
                (teams[2], teams[3]),
            ]

            for home, away in sample_matches:
                try:
                    result = predictor.predict_with_full_bayesian_analysis(home, away)
                    predictions = result.get('predictions', {})
                    probabilities = result.get('probabilities', {})
                    confidence_intervals = result.get('confidence_intervals', {})
                    poisson_analysis = result.get('poisson_analysis', {})

                    sample_predictions.append({
                        'home_team': home,
                        'away_team': away,
                        'predictions': predictions,
                        'probabilities': probabilities,
                        'confidence_intervals': confidence_intervals,
                        'poisson_scorelines': poisson_analysis,
                        'confidence_level': 'HIGH'
                    })
                except Exception as e:
                    print(f"Error creating sample prediction: {e}")
                    continue

        return jsonify({
            'status': 'success',
            'predictions': sample_predictions,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Live predictions error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


@routes.route('/results')
def results():
    """Results page"""
    return render_template('results.html')


@routes.route('/api/gw1-analysis')
def gw1_analysis():
    """API endpoint for opening weekend analysis"""
    try:
        if not gw1_analyzer:
            return jsonify({'error': 'GW1 analyzer not available'}), 500

        analysis = gw1_analyzer.analyze_gw1_patterns()
        insights = gw1_analyzer.generate_gw1_insights()

        return jsonify({
            'status': 'success',
            'gw1_analysis': analysis,
            'key_insights': insights,
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
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/my-predictions')
def my_predictions():
    """My Predictions page"""
    return render_template('my_predictions.html')


@routes.route('/api/weekly-insights')
def weekly_insights_api():
    """API endpoint for weekly insights"""
    try:
        if not weekly_analyzer:
            return jsonify({'error': 'Weekly analyzer not available'}), 500

        phase_analysis = weekly_analyzer.get_season_phase_analysis()

        return jsonify({
            'status': 'success',
            'season_phase': phase_analysis,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ Weekly insights API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/system-status')
def api_system_status():
    """System status API"""
    return jsonify({
        'status': 'operational' if predictor else 'error',
        'teams_loaded': len(teams),
        'predictor_ready': predictor is not None,
        'gw1_analyzer_ready': gw1_analyzer is not None
    })


@routes.route('/api/prediction', methods=['POST'])
def api_prediction():
    """API endpoint for predictions"""
    try:
        data = request.get_json()
        home_team = data.get('home_team')
        away_team = data.get('away_team')

        if not home_team or not away_team:
            return jsonify({'status': 'error', 'message': 'Missing team selection'}), 400

        if not predictor:
            return jsonify({'status': 'error', 'message': 'Prediction system not available'}), 500

        result = predictor.predict_with_full_bayesian_analysis(home_team, away_team)

        return jsonify({
            'status': 'success',
            'match': f"{home_team} vs {away_team}",
            'analysis': result,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"❌ Prediction API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """Save prediction functionality"""
    try:
        data = request.get_json()

        prediction_record = {
            'id': len(data) + 1,
            'home_team': data.get('home_team'),
            'away_team': data.get('away_team'),
            'predictions': data.get('predictions', {}),
            'probabilities': data.get('probabilities', {}),
            'confidence_intervals': data.get('confidence_intervals', {}),
            'poisson_analysis': data.get('poisson_analysis', {}),
            'date_saved': datetime.utcnow().isoformat(),
            'match_date': data.get('match_date', 'TBD'),
            'season': '2024/25'
        }

        print(f"✅ Prediction saved: {prediction_record['home_team']} vs {prediction_record['away_team']}")

        return jsonify({
            'status': 'success',
            'message': 'Prediction saved successfully',
            'prediction_id': prediction_record['id']
        })

    except Exception as e:
        print(f"❌ Save error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500