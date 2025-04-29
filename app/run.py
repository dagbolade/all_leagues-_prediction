# run.py

from flask import Flask, render_template, request, redirect, url_for, jsonify
from footy.predictor_utils import MatchPredictor
from app.routes import routes  # Import the blueprint
from app.services.football_service import FootballDataService
import joblib
import os

# Initialize Flask app
app = Flask(__name__)
app.register_blueprint(routes)  # Register the blueprint with the API routes

# Initialize football service
football_service = FootballDataService()

# Load models and data
try:
    print("Loading models and data...")
    models = joblib.load('models/football_models.joblib')
    df_engineered = joblib.load('data/processed/processed_data.pkl')
    predictor = MatchPredictor(df_engineered, models)
    teams = sorted(list(set(df_engineered['HomeTeam'].unique()) | set(df_engineered['AwayTeam'].unique())))
    print("Models and data loaded successfully!")
except Exception as e:
    print(f"Error loading models or data: {str(e)}")
    models, df_engineered, predictor, teams = None, None, None, []

football_service.predictor = predictor

# Page routes
@app.route('/')
def index():
    """Home page route."""
    return render_template('index.html')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Prediction page route with lazy model loading."""
    global predictor, teams, football_service

    if predictor is None:
        try:
            print("🔄 Lazy-loading models and data...")
            models = joblib.load('models/football_models.joblib')
            df_engineered = joblib.load('data/processed/processed_data.pkl')
            predictor = MatchPredictor(df_engineered, models)
            teams = sorted(list(set(df_engineered['HomeTeam'].unique()) | set(df_engineered['AwayTeam'].unique())))
            football_service.predictor = predictor
            print("✅ Models loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Lazy-loading failed: {str(e)}")
            return render_template('predict.html', error="Error loading model/data", teams=[])

    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')

        if predictor and home_team and away_team:
            try:
                predictions, probabilities = predictor.predict_match(home_team, away_team)
                return render_template('predict.html',
                                       teams=teams,
                                       predictions=predictions,
                                       probabilities=probabilities,
                                       home_team=home_team,
                                       away_team=away_team)
            except Exception as e:
                print(f"[ERROR] Prediction failed: {str(e)}")
                return render_template('predict.html', error="Prediction failed", teams=teams)

    return render_template('predict.html', teams=teams)

@app.route('/results')
def results():
    """Results page route."""
    return render_template('results.html')

# API routes
@app.route('/api/live-scores')
def live_scores():
    """Get live scores endpoint."""
    matches = football_service.get_live_matches()
    if matches:
        return jsonify(matches)
    return jsonify({
        'error': 'Unable to fetch live scores',
        'matches': []
    }), 500

if __name__ == '__main__':
    app.run(debug=True)