"""
Multi-Sport Routes — Football, Basketball, Tennis
Each sport has its own prediction page integrated into the main platform.
"""

import sys
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

multi_sport = Blueprint('multi_sport', __name__)

# ─── Model registry ──────────────────────────────────────────────────────────
_basketball_data = None
_tennis_data     = None


def _load_models():
    global _basketball_data, _tennis_data

    # Basketball – prefer advanced, fall back to backtested then basic
    for path in [
        "models/basketball/basketball_advanced_models.joblib",
        "models/basketball/basketball_backtested_models.joblib",
        "models/basketball/basketball_models.joblib",
    ]:
        p = project_root / path
        if p.exists() and p.stat().st_size > 1024:
            try:
                _basketball_data = joblib.load(p)
                logger.info(f"[Basketball] Loaded {p.name}")
                break
            except Exception as e:
                logger.error(f"[Basketball] Failed to load {p.name}: {e}")

    # Tennis – prefer advanced, fall back to backtested then basic
    for path in [
        "models/tennis/tennis_advanced_models.joblib",
        "models/tennis/tennis_backtested_models.joblib",
        "models/tennis/tennis_models.joblib",
    ]:
        p = project_root / path
        if p.exists() and p.stat().st_size > 1024:
            try:
                _tennis_data = joblib.load(p)
                logger.info(f"[Tennis] Loaded {p.name}")
                break
            except Exception as e:
                logger.error(f"[Tennis] Failed to load {p.name}: {e}")


_load_models()


# ─── Routes ──────────────────────────────────────────────────────────────────

@multi_sport.route('/')
def home():
    stats = {
        'basketball_loaded': _basketball_data is not None,
        'tennis_loaded':     _tennis_data is not None,
    }
    return render_template('multi_sport/index.html', stats=stats)


@multi_sport.route('/sport/football')
def football_page():
    """Football hub — links into the main football features."""
    return render_template('multi_sport/football.html')


@multi_sport.route('/sport/basketball')
def basketball_page():
    model_loaded = _basketball_data is not None
    # Pull NBA teams from training data if available
    teams = _get_nba_teams()
    return render_template('multi_sport/basketball.html',
                           model_loaded=model_loaded,
                           teams=teams)


@multi_sport.route('/sport/tennis')
def tennis_page():
    model_loaded = _tennis_data is not None
    surfaces = ['Hard', 'Clay', 'Grass', 'Carpet']
    return render_template('multi_sport/tennis.html',
                           model_loaded=model_loaded,
                           surfaces=surfaces)


# ─── Prediction APIs ─────────────────────────────────────────────────────────

@multi_sport.route('/api/basketball/predict', methods=['POST'])
def basketball_predict():
    if _basketball_data is None:
        return jsonify({'error': 'Basketball model not loaded'}), 503

    data = request.json or {}
    home = data.get('home', '').strip()
    away = data.get('away', '').strip()
    if not home or not away:
        return jsonify({'error': 'home and away team names required'}), 400

    try:
        from sports.basketball.basketball_features import BasketballFeatureEngineer

        models      = _basketball_data.get('models', {})
        feature_cols = _basketball_data.get('feature_cols', [])

        game_df = pd.DataFrame([{
            'Date':      pd.Timestamp.now(),
            'HomeTeam':  home,
            'AwayTeam':  away,
            'HomeScore': 0,
            'AwayScore': 0,
            'Result':    'H',
        }])

        fe = BasketballFeatureEngineer()
        game_features = fe.engineer_features(game_df)

        # Keep only columns the model was trained on
        available = [c for c in feature_cols if c in game_features.columns]
        X = game_features[available].fillna(0)
        if len(available) < len(feature_cols):
            # Pad missing columns with zeros
            for col in feature_cols:
                if col not in X.columns:
                    X[col] = 0
            X = X[feature_cols]

        result = {}

        # Winner
        if 'match_outcome' in models:
            model = models['match_outcome']['model']
            prob  = model.predict_proba(X)[0]
            # prob[0]=Away wins, prob[1]=Home wins
            home_prob = float(prob[1])
            away_prob = float(prob[0])
            result['winner']        = home if home_prob > away_prob else away
            result['home_win_prob'] = round(home_prob * 100, 1)
            result['away_win_prob'] = round(away_prob * 100, 1)
            result['confidence']    = round(max(home_prob, away_prob) * 100, 1)

        # Total Points prediction
        if 'total_points' in models:
            tp_model = models['total_points']['model']
            total    = float(tp_model.predict(X)[0])
            result['total_points']       = round(total, 1)
            result['total_points_range'] = f"{round(total - 10, 1)}–{round(total + 10, 1)}"

        # Over/Under (various thresholds)
        for key in ['over_220', 'over_215', 'over_225']:
            if key in models:
                ou_model  = models[key]['model']
                ou_prob   = ou_model.predict_proba(X)[0]
                threshold = key.split('_')[1]
                result['over_under'] = {
                    'line':       int(threshold),
                    'prediction': f"Over {threshold}" if ou_prob[1] > ou_prob[0] else f"Under {threshold}",
                    'over_prob':  round(float(ou_prob[1]) * 100, 1),
                    'under_prob': round(float(ou_prob[0]) * 100, 1),
                }
                break  # only need one

        return jsonify(result)

    except Exception as e:
        logger.exception("[Basketball] Prediction error")
        return jsonify({'error': str(e)}), 500


@multi_sport.route('/api/tennis/predict', methods=['POST'])
def tennis_predict():
    if _tennis_data is None:
        return jsonify({'error': 'Tennis model not loaded'}), 503

    data    = request.json or {}
    player1 = data.get('player1', '').strip()
    player2 = data.get('player2', '').strip()
    surface = data.get('surface', 'Hard')
    if not player1 or not player2:
        return jsonify({'error': 'player1 and player2 names required'}), 400

    try:
        from sports.tennis.tennis_features import TennisFeatureEngineer

        models       = _tennis_data.get('models', {})
        feature_cols = _tennis_data.get('feature_cols', [])

        match_df = pd.DataFrame([{
            'Date':       pd.Timestamp.now(),
            'Player1':    player1,
            'Player2':    player2,
            'Winner':     'Player1',
            'Surface':    surface,
            'Tournament': 'Unknown',
            'Round':      'Final',
            'Score':      '0-0',
        }])

        fe             = TennisFeatureEngineer()
        match_features = fe.engineer_features(match_df)

        available = [c for c in feature_cols if c in match_features.columns]
        X = match_features[available].fillna(0)
        for col in feature_cols:
            if col not in X.columns:
                X[col] = 0
        X = X[feature_cols]

        result = {}

        if 'winner' in models:
            model = models['winner']['model']
            prob  = model.predict_proba(X)[0]
            # prob[0]=Player2 wins, prob[1]=Player1 wins
            p1_prob = float(prob[1])
            p2_prob = float(prob[0])
            result['winner']       = player1 if p1_prob > p2_prob else player2
            result['p1_win_prob']  = round(p1_prob * 100, 1)
            result['p2_win_prob']  = round(p2_prob * 100, 1)
            result['confidence']   = round(max(p1_prob, p2_prob) * 100, 1)
            result['player1']      = player1
            result['player2']      = player2

        return jsonify(result)

    except Exception as e:
        logger.exception("[Tennis] Prediction error")
        return jsonify({'error': str(e)}), 500


# ─── Helper ──────────────────────────────────────────────────────────────────

def _get_nba_teams():
    """Return sorted list of NBA team names from training data."""
    try:
        csv = project_root / "data/basketball/raw/nba_real_data.csv"
        if csv.exists():
            df    = pd.read_csv(csv, usecols=['HomeTeam'])
            teams = sorted(df['HomeTeam'].dropna().unique().tolist())
            return teams
    except Exception:
        pass
    return [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
        "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
        "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
        "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
        "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
        "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
        "Utah Jazz", "Washington Wizards",
    ]
