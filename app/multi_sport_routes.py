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

# ─── Model + historical data registry ───────────────────────────────────────
_basketball_data = None
_tennis_data     = None
_basketball_hist = None   # pre-loaded historical NBA data
_tennis_hist     = None   # pre-loaded historical tennis data


def _load_models():
    global _basketball_data, _tennis_data, _basketball_hist, _tennis_hist

    # Basketball models
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

    # Basketball historical data — loaded once, used for feature engineering context
    try:
        bball_csv = project_root / "data/basketball/raw/nba_real_data.csv"
        if bball_csv.exists():
            _basketball_hist = pd.read_csv(bball_csv)
            _basketball_hist['Date'] = pd.to_datetime(_basketball_hist['Date'])
            if 'TotalPoints' not in _basketball_hist.columns:
                _basketball_hist['TotalPoints'] = _basketball_hist['HomeScore'] + _basketball_hist['AwayScore']
            if 'PointDiff' not in _basketball_hist.columns:
                _basketball_hist['PointDiff'] = _basketball_hist['HomeScore'] - _basketball_hist['AwayScore']
            if 'Result' not in _basketball_hist.columns:
                _basketball_hist['Result'] = 'H'
                _basketball_hist.loc[_basketball_hist['AwayScore'] > _basketball_hist['HomeScore'], 'Result'] = 'A'
            logger.info(f"[Basketball] Historical data loaded: {len(_basketball_hist)} games")
    except Exception as e:
        logger.error(f"[Basketball] Failed to load historical data: {e}")

    # Tennis models
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

    # Tennis historical data
    try:
        tennis_csv = project_root / "data/tennis/raw/tennis_real_data.csv"
        if tennis_csv.exists():
            _tennis_hist = pd.read_csv(tennis_csv)
            _tennis_hist['Date'] = pd.to_datetime(_tennis_hist['Date'])
            logger.info(f"[Tennis] Historical data loaded: {len(_tennis_hist)} matches")
    except Exception as e:
        logger.error(f"[Tennis] Failed to load historical data: {e}")


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

        models = _basketball_data.get('models', {})

        # Run feature engineering on historical data ONLY — no prediction row.
        # Then extract each team's most recent computed stats.
        # This avoids contaminating rolling averages with placeholder zeros.
        if _basketball_hist is not None:
            fe = BasketballFeatureEngineer()
            hist_features = fe.engineer_features(_basketball_hist.copy())

            # Most recent home game for home team → Home_* features + ELO
            home_rows = hist_features[hist_features['HomeTeam'] == home]
            # Most recent away game for away team → Away_* features
            away_rows = hist_features[hist_features['AwayTeam'] == away]
            # Most recent game involving either team for ELO
            any_home = hist_features[(hist_features['HomeTeam'] == home) | (hist_features['AwayTeam'] == home)]
            any_away = hist_features[(hist_features['HomeTeam'] == away) | (hist_features['AwayTeam'] == away)]

            # Build combined feature row
            feat_row = {}
            if len(home_rows) > 0:
                for col in hist_features.columns:
                    if col.startswith('Home_'):
                        feat_row[col] = home_rows.iloc[-1].get(col, 0)
            if len(away_rows) > 0:
                for col in hist_features.columns:
                    if col.startswith('Away_'):
                        feat_row[col] = away_rows.iloc[-1].get(col, 0)
            # ELO from most recent game for each team
            if len(any_home) > 0:
                last = any_home.iloc[-1]
                feat_row['HomeElo'] = last['HomeElo'] if last['HomeTeam'] == home else last['AwayElo']
            if len(any_away) > 0:
                last = any_away.iloc[-1]
                feat_row['AwayElo'] = last['AwayElo'] if last['AwayTeam'] == away else last['HomeElo']
            feat_row['EloAdvantage'] = feat_row.get('HomeElo', 1500) - feat_row.get('AwayElo', 1500)
            # H2H from last game between these two teams
            h2h = hist_features[
                ((hist_features['HomeTeam'] == home) & (hist_features['AwayTeam'] == away)) |
                ((hist_features['HomeTeam'] == away) & (hist_features['AwayTeam'] == home))
            ]
            if len(h2h) > 0:
                for col in ['H2H_HomeWins', 'H2H_AwayWins', 'H2H_TotalGames']:
                    feat_row[col] = h2h.iloc[-1].get(col, 0)
            # Season timing
            now = pd.Timestamp.now()
            feat_row['Month'] = now.month
            feat_row['EarlySeason'] = 1 if now.month in [10, 11] else 0
            feat_row['MidSeason']   = 1 if now.month in [12, 1, 2] else 0
            feat_row['LateSeason']  = 1 if now.month in [3, 4, 5] else 0
            # Rest days default
            feat_row.setdefault('Home_DaysRest', 2)
            feat_row.setdefault('Away_DaysRest', 2)
            feat_row.setdefault('Home_BackToBack', 0)
            feat_row.setdefault('Away_BackToBack', 0)
            # AvgTotalPoints from recent games globally
            if len(hist_features) >= 5:
                feat_row['AvgTotalPoints_L5']  = _basketball_hist['TotalPoints'].iloc[-5:].mean() if 'TotalPoints' in _basketball_hist else 227
                feat_row['AvgTotalPoints_L10'] = _basketball_hist['TotalPoints'].iloc[-10:].mean() if 'TotalPoints' in _basketball_hist else 227

            # Box score rolling averages — needed because HomeREB/AwayAST etc. are top-50 features
            for stat in ['FG', 'FG3', 'FT', 'REB', 'AST', 'TO']:
                hcol = f'Home{stat}'
                acol = f'Away{stat}'
                if hcol in _basketball_hist.columns:
                    val = _basketball_hist[_basketball_hist['HomeTeam'] == home][hcol].dropna().tail(5).mean()
                    feat_row[hcol] = val if pd.notna(val) else 0.0
                if acol in _basketball_hist.columns:
                    val = _basketball_hist[_basketball_hist['AwayTeam'] == away][acol].dropna().tail(5).mean()
                    feat_row[acol] = val if pd.notna(val) else 0.0

            game_features = pd.DataFrame([feat_row])
        else:
            game_features = pd.DataFrame([{}])

        def get_X(task):
            cols = models[task].get('features', [])
            row = {c: float(game_features[c].iloc[0])
                   if c in game_features.columns and pd.notna(game_features[c].iloc[0])
                   else 0.0
                   for c in cols}
            return pd.DataFrame([row])[cols]

        result = {}

        # Game winner
        if 'match_outcome' in models:
            X = get_X('match_outcome')
            prob      = models['match_outcome']['model'].predict_proba(X)[0]
            home_prob = float(prob[1])
            away_prob = float(prob[0])
            result['winner']        = home if home_prob > away_prob else away
            result['home_win_prob'] = round(home_prob * 100, 1)
            result['away_win_prob'] = round(away_prob * 100, 1)
            result['confidence']    = round(max(home_prob, away_prob) * 100, 1)

        # Total points (regression)
        if 'total_points' in models:
            X     = get_X('total_points')
            total = float(models['total_points']['model'].predict(X)[0])
            result['total_points']       = round(total, 1)
            result['total_points_range'] = f"{round(total - 10, 1)}–{round(total + 10, 1)}"

        # Point spread / handicap — predicted margin
        if 'point_diff' in models:
            X    = get_X('point_diff')
            diff = float(models['point_diff']['model'].predict(X)[0])
            result['point_diff'] = round(diff, 1)
            if diff > 0:
                result['spread_summary'] = f"{home} favoured by {abs(round(diff, 1))} pts"
            else:
                result['spread_summary'] = f"{away} favoured by {abs(round(diff, 1))} pts"

        # Over/Under lines — return both if available
        ou_markets = []
        for key, line in [('over_220', 220), ('over_225', 225)]:
            if key in models:
                X      = get_X(key)
                prob   = models[key]['model'].predict_proba(X)[0]
                over_p = round(float(prob[1]) * 100, 1)
                under_p = round(float(prob[0]) * 100, 1)
                ou_markets.append({
                    'line':       line,
                    'prediction': f"Over {line}" if prob[1] > prob[0] else f"Under {line}",
                    'over_prob':  over_p,
                    'under_prob': under_p,
                })
        if ou_markets:
            result['over_under_markets'] = ou_markets

        # Team totals
        team_totals = []
        if 'home_over_110' in models:
            X    = get_X('home_over_110')
            prob = models['home_over_110']['model'].predict_proba(X)[0]
            team_totals.append({
                'label': f'{home} over 110',
                'prediction': 'Over 110' if prob[1] > prob[0] else 'Under 110',
                'prob': round(float(max(prob)) * 100, 1),
            })
        if 'away_over_108' in models:
            X    = get_X('away_over_108')
            prob = models['away_over_108']['model'].predict_proba(X)[0]
            team_totals.append({
                'label': f'{away} over 108',
                'prediction': 'Over 108' if prob[1] > prob[0] else 'Under 108',
                'prob': round(float(max(prob)) * 100, 1),
            })
        if team_totals:
            result['team_totals'] = team_totals

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

        models = _tennis_data.get('models', {})

        future_date = pd.Timestamp.now() + pd.Timedelta(days=1)
        match_df = pd.DataFrame([{
            'Date':       future_date,
            'Player1':    player1,
            'Player2':    player2,
            'Winner':     'Player1',
            'Surface':    surface,
            'Tournament': 'Unknown',
            'Round':      'Final',
            'Score':      '0-0',
        }])

        # Append to historical data for proper feature context
        if _tennis_hist is not None:
            full_df = pd.concat([_tennis_hist, match_df], ignore_index=True)
        else:
            full_df = match_df

        fe             = TennisFeatureEngineer()
        match_features = fe.engineer_features(full_df).iloc[[-1]]

        def get_X(task):
            cols = models[task].get('features', [])
            row  = {c: float(match_features[c].iloc[0])
                    if c in match_features.columns and pd.notna(match_features[c].iloc[0])
                    else 0.0
                    for c in cols}
            return pd.DataFrame([row])[cols]

        result = {
            'player1': player1,
            'player2': player2,
        }

        # Match winner
        if 'winner' in models:
            X       = get_X('winner')
            prob    = models['winner']['model'].predict_proba(X)[0]
            p1_prob = float(prob[1])
            p2_prob = float(prob[0])
            result['winner']      = player1 if p1_prob > p2_prob else player2
            result['p1_win_prob'] = round(p1_prob * 100, 1)
            result['p2_win_prob'] = round(p2_prob * 100, 1)
            result['confidence']  = round(max(p1_prob, p2_prob) * 100, 1)

        # First set winner
        if 'first_set' in models:
            X       = get_X('first_set')
            prob    = models['first_set']['model'].predict_proba(X)[0]
            p1_prob = float(prob[1])
            p2_prob = float(prob[0])
            result['first_set'] = {
                'winner':     player1 if p1_prob > p2_prob else player2,
                'p1_prob':    round(p1_prob * 100, 1),
                'p2_prob':    round(p2_prob * 100, 1),
                'confidence': round(max(p1_prob, p2_prob) * 100, 1),
            }

        # Goes to distance / set handicap / correct score (same model, different framings)
        if 'goes_distance' in models:
            X       = get_X('goes_distance')
            prob    = models['goes_distance']['model'].predict_proba(X)[0]
            p_dist  = round(float(prob[1]) * 100, 1)   # prob of 3 sets
            p_str   = round(float(prob[0]) * 100, 1)   # prob of straight sets
            goes    = float(prob[1]) > float(prob[0])
            result['match_length'] = {
                # Correct score framing
                'correct_score': '2-1' if goes else '2-0',
                # Set handicap: winner covers -1.5 = straight sets win
                'set_handicap': 'Does NOT cover -1.5' if goes else 'Covers -1.5 (straight sets)',
                'prob_distance': p_dist,
                'prob_straight': p_str,
            }

        # Total games over/under 21.5
        if 'total_games_over_21' in models:
            X      = get_X('total_games_over_21')
            prob   = models['total_games_over_21']['model'].predict_proba(X)[0]
            over_p = round(float(prob[1]) * 100, 1)
            under_p = round(float(prob[0]) * 100, 1)
            result['total_games'] = {
                'line': 21.5,
                'prediction': 'Over 21.5' if prob[1] > prob[0] else 'Under 21.5',
                'over_prob':  over_p,
                'under_prob': under_p,
            }

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
