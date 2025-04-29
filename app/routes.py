# app/routes.py
from datetime import datetime
import logging

from flask import Blueprint, render_template, request
from footy.predictor_utils import MatchPredictor
from flask import jsonify

from services.football_service import FootballDataService
import joblib

# Create blueprint
routes = Blueprint('routes', __name__)

# Load the models
import os


def initialize_predictor():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')
        data_path = os.path.join(base_dir, '..', 'data', 'processed', 'processed_data.pkl')

        models = joblib.load(models_path)

        # HOTFIX: Clean models properly
        cleaned_models = {}
        for name, model in models.items():
            try:
                if hasattr(model, 'use_label_encoder'):
                    delattr(model, 'use_label_encoder')
                cleaned_models[name] = model
            except Exception as e:
                print(f"Warning cleaning model {name}: {str(e)}")
                cleaned_models[name] = model

        df_engineered = joblib.load(data_path)

        predictor = MatchPredictor(df_engineered, cleaned_models)
        teams = sorted(list(set(df_engineered['HomeTeam'].unique()) | set(df_engineered['AwayTeam'].unique())))

        print(f"✅ Successfully loaded {len(teams)} teams.")
        return predictor, teams

    except Exception as e:
        print(f"❌ Error loading models or data: {str(e)}")
        return None, []


predictor, teams = initialize_predictor()
football_service = FootballDataService()


@routes.route('/api/live-scores')
def live_scores():
    try:
        matches = football_service.get_live_matches()
        if matches:
            # Print what we're sending back
            print("Sending matches data:", matches)
            return jsonify(matches)

        return jsonify({
            'error': 'No matches found',
            'matches': []
        })
    except Exception as e:
        print(f"Route error: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch matches',
            'message': str(e)
        }), 500

@routes.route('/api/competition/<competition_id>/matches')
def competition_matches(competition_id):
    matches = football_service.get_matches_by_competition(competition_id)
    if matches:
        return jsonify(matches)
    return jsonify({'error': 'Unable to fetch competition matches'}), 500

@routes.route('/api/team/<int:team_id>/matches')
def team_matches(team_id):
    status = request.args.get('status', 'SCHEDULED')
    matches = football_service.get_matches_by_team(team_id, status)
    if matches:
        return jsonify(matches)
    return jsonify({'error': 'Unable to fetch team matches'}), 500

@routes.route('/')
def home():
    """Home page with prediction form."""
    return render_template('index.html', teams=teams)


@routes.route('/predict', methods=['GET', 'POST'])
def predict():
    """Handle prediction requests."""
    print("Teams available:", teams)  # Debug print
    print("Number of teams:", len(teams) if teams else 0)  # Debug print

    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')

        if predictor and home_team and away_team:
            predictions, probabilities = predictor.predict_match(home_team, away_team)
            return render_template('predict.html',
                                   teams=teams,
                                   predictions=predictions,
                                   probabilities=probabilities,
                                   home_team=home_team,
                                   away_team=away_team)

    return render_template('predict.html', teams=teams)

@routes.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """Save prediction to database."""
    try:
        prediction_data = request.json
        # Here you would typically save to a database
        # For now, we'll just return success
        return jsonify({
            'status': 'success',
            'message': 'Prediction saved successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@routes.route('/results')
def results():
    """Display prediction results."""
    return render_template('results.html')


@routes.route('/live-predictions')
def live_predictions_page():
    return render_template('live_predictions.html')


from footy.utils import smart_team_match


@routes.route('/api/live-predictions')
def live_predictions():
    try:
        today_matches = football_service.get_live_matches().get('matches', [])  # This should be a LIST []  # now it is a LIST []
        #print("Today's Matches:", today_matches)  # Debug print
        #print("Number of matches:", len(today_matches) if today_matches else 0)  # Debug print

        if not today_matches:
            print("[ERROR🚨] No live matches today.")
            return jsonify({
                'status': 'error',
                'message': 'No live matches available today.'
            })

        predictions = []

        print("\n[Today's Matched Live Matches 📋]")
        for match in today_matches:
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']

            matched_home = smart_team_match(home_team, teams)
            matched_away = smart_team_match(away_team, teams)

            print(f" - {home_team} ➔ {matched_home} | {away_team} ➔ {matched_away}")

            if matched_home and matched_away:
                preds, probs = predictor.predict_match(matched_home, matched_away)
                if preds and probs:
                    predictions.append({
                        'home_team': matched_home,
                        'away_team': matched_away,
                        'predictions': preds,
                        'probabilities': probs
                    })
            else:
                print(f"[SKIPPED❗] Cannot predict {home_team} vs {away_team} (No match found)")

        print(f"\n✅ Number of predictions generated: {len(predictions)}")

        return jsonify({
            'predictions': predictions,
            'status': 'success',
            'timestamp': str(datetime.utcnow())
        })

    except Exception as e:
        print(f"[ERROR🚨] Live prediction error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
