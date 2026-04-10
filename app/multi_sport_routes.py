"""
Multi-Sport Routes — Football, Basketball, Tennis
Each sport has its own prediction page integrated into the main platform.
"""

import sys
import logging
import pickle
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

multi_sport = Blueprint('multi_sport', __name__)

# ─── Model + historical data registry ───────────────────────────────────────
_basketball_data    = None
_tennis_data        = None
_basketball_hist    = None   # pre-loaded historical NBA data
_tennis_hist        = None   # pre-loaded historical tennis data
_tennis_hist_feats  = None   # pre-computed tennis features (avoids O(n²) on every request)


def _load_models():
    global _basketball_data, _tennis_data, _basketball_hist, _tennis_hist, _tennis_hist_feats

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

    # Basketball historical data — prefer combined NBA+EuroLeague file
    try:
        combined_csv = project_root / "data/basketball/raw/basketball_all_data.csv"
        nba_csv      = project_root / "data/basketball/raw/nba_real_data.csv"
        bball_csv    = combined_csv if combined_csv.exists() else nba_csv
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
            if 'IsEuroLeague' not in _basketball_hist.columns:
                _basketball_hist['IsEuroLeague'] = (_basketball_hist.get('League', 'NBA') == 'EuroLeague').astype(int)
            nba_n = (_basketball_hist.get('League', pd.Series(['NBA']*len(_basketball_hist))) == 'NBA').sum()
            eur_n = (_basketball_hist.get('League', pd.Series(['NBA']*len(_basketball_hist))) == 'EuroLeague').sum()
            logger.info(f"[Basketball] Loaded {len(_basketball_hist)} games (NBA:{nba_n} EuroLeague:{eur_n})")
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

    # Tennis historical data + pre-compute features ONCE at startup
    # Cache to disk so restarts after first run are instant
    try:
        tennis_csv   = project_root / "data/tennis/raw/tennis_real_data.csv"
        cache_pkl    = project_root / "data/tennis/raw/tennis_feats_cache.pkl"
        cache_sig    = project_root / "data/tennis/raw/tennis_feats_sig.txt"

        if tennis_csv.exists():
            _tennis_hist = pd.read_csv(tennis_csv)
            _tennis_hist['Date'] = pd.to_datetime(_tennis_hist['Date'])
            logger.info(f"[Tennis] Historical data loaded: {len(_tennis_hist)} matches")

            # Build a signature from the file mtime + size
            stat    = tennis_csv.stat()
            src_sig = f"{stat.st_mtime}_{stat.st_size}"

            loaded_from_cache = False
            if cache_pkl.exists() and cache_sig.exists():
                try:
                    if cache_sig.read_text().strip() == src_sig:
                        logger.info("[Tennis] Loading pre-computed features from cache...")
                        with open(cache_pkl, 'rb') as fh:
                            _tennis_hist_feats = pickle.load(fh)
                        loaded_from_cache = True
                        logger.info(f"[Tennis] Cache loaded: {len(_tennis_hist_feats)} rows")
                except Exception as ce:
                    logger.warning(f"[Tennis] Cache load failed, will recompute: {ce}")

            if not loaded_from_cache:
                logger.info("[Tennis] Computing features (first run, may take ~30s)…")
                try:
                    from sports.tennis.tennis_features import TennisFeatureEngineer
                    _fe = TennisFeatureEngineer()
                    _tennis_hist_feats = _fe.engineer_features(_tennis_hist.copy())
                    logger.info(f"[Tennis] Features computed: {len(_tennis_hist_feats)} rows — caching…")
                    with open(cache_pkl, 'wb') as fh:
                        pickle.dump(_tennis_hist_feats, fh)
                    cache_sig.write_text(src_sig)
                    logger.info("[Tennis] Features cached for future startups")
                except Exception as fe_err:
                    logger.error(f"[Tennis] Feature pre-computation failed: {fe_err}")
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
    teams_dict = _get_nba_teams()
    return render_template('multi_sport/basketball.html',
                           model_loaded=model_loaded,
                           teams=teams_dict)


@multi_sport.route('/sport/basketball/stats', methods=['GET', 'POST'])
def basketball_stats():
    teams_dict = _get_nba_teams()
    stats = None
    home_team = None
    away_team = None
    if request.method == 'POST':
        home_team = request.form.get('homeTeam', '').strip()
        away_team = request.form.get('awayTeam', '').strip()
        if home_team and away_team and _basketball_hist is not None:
            stats = _build_basketball_stats(home_team, away_team)
    return render_template('multi_sport/basketball_stats.html',
                           teams=teams_dict, stats=stats,
                           home_team=home_team, away_team=away_team)


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
            # League indicator
            eur_teams = set(_basketball_hist[_basketball_hist.get('League', pd.Series()) == 'EuroLeague']['HomeTeam'].unique()) if 'League' in _basketball_hist.columns else set()
            feat_row['IsEuroLeague'] = 1 if (home in eur_teams or away in eur_teams) else 0

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

            # Box score rolling averages — fill both old-model names (HomeFG etc.)
            # and new-model names (Home_FG%_L5 etc.) for compatibility
            for stat in ['FG', 'FG3', 'FT', 'REB', 'AST', 'TO']:
                hcol = f'Home{stat}'
                acol = f'Away{stat}'
                if hcol in _basketball_hist.columns:
                    val = _basketball_hist[_basketball_hist['HomeTeam'] == home][hcol].dropna().tail(5).mean()
                    feat_row[hcol] = val if pd.notna(val) else 0.0
                if acol in _basketball_hist.columns:
                    val = _basketball_hist[_basketball_hist['AwayTeam'] == away][acol].dropna().tail(5).mean()
                    feat_row[acol] = val if pd.notna(val) else 0.0

            # Also pull H2H_AvgTotal if present in hist_features
            if len(h2h) > 0 and 'H2H_AvgTotal' in hist_features.columns:
                feat_row['H2H_AvgTotal'] = h2h.iloc[-1].get('H2H_AvgTotal', 0)

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
        models = _tennis_data.get('models', {})
        hf     = _tennis_hist_feats  # pre-computed — avoids O(n²) recompute

        # ── Build feature row from pre-computed historical features ──────────
        feat_row = {}

        if hf is not None:
            # Player1's last match as Player1
            p1_as_p1 = hf[hf['Player1'] == player1]
            # Player1's last match as Player2
            p1_as_p2 = hf[hf['Player2'] == player1]
            # Player2's last match as Player2
            p2_as_p2 = hf[hf['Player2'] == player2]
            # Player2's last match as Player1
            p2_as_p1 = hf[hf['Player1'] == player2]

            # Extract Player1_* features from their most recent match
            for src_df, role in [(p1_as_p1, 'Player1'), (p1_as_p2, 'Player2')]:
                if len(src_df) > 0:
                    last = src_df.iloc[-1]
                    for col in hf.columns:
                        if col.startswith(f'{role}_'):
                            new_col = col.replace(f'{role}_', 'Player1_', 1)
                            val = last.get(col, 0)
                            if pd.notna(val):
                                feat_row[new_col] = float(val)
                    if role == 'Player1' and 'Player1_Elo' in hf.columns:
                        feat_row['Player1_Elo'] = float(last.get('Player1_Elo', 1500))
                    elif role == 'Player2' and 'Player2_Elo' in hf.columns:
                        feat_row['Player1_Elo'] = float(last.get('Player2_Elo', 1500))
                    break  # use most recent match regardless of role

            # Extract Player2_* features from their most recent match
            for src_df, role in [(p2_as_p2, 'Player2'), (p2_as_p1, 'Player1')]:
                if len(src_df) > 0:
                    last = src_df.iloc[-1]
                    for col in hf.columns:
                        if col.startswith(f'{role}_'):
                            new_col = col.replace(f'{role}_', 'Player2_', 1)
                            val = last.get(col, 0)
                            if pd.notna(val):
                                feat_row[new_col] = float(val)
                    if role == 'Player2' and 'Player2_Elo' in hf.columns:
                        feat_row['Player2_Elo'] = float(last.get('Player2_Elo', 1500))
                    elif role == 'Player1' and 'Player1_Elo' in hf.columns:
                        feat_row['Player2_Elo'] = float(last.get('Player1_Elo', 1500))
                    break

            # ELO difference
            feat_row['EloDiff'] = feat_row.get('Player1_Elo', 1500) - feat_row.get('Player2_Elo', 1500)

            # H2H — last meeting between these two
            h2h = hf[
                ((hf['Player1'] == player1) & (hf['Player2'] == player2)) |
                ((hf['Player1'] == player2) & (hf['Player2'] == player1))
            ]
            if len(h2h) > 0:
                last = h2h.iloc[-1]
                for col in ['H2H_Player1Wins', 'H2H_Player2Wins', 'H2H_TotalMatches']:
                    if col in hf.columns:
                        # Flip if the players were in opposite roles in the last H2H row
                        if last.get('Player1') == player2:
                            flip = {'H2H_Player1Wins': 'H2H_Player2Wins',
                                    'H2H_Player2Wins': 'H2H_Player1Wins',
                                    'H2H_TotalMatches': 'H2H_TotalMatches'}
                            feat_row[flip[col]] = float(last.get(col, 0))
                        else:
                            feat_row[col] = float(last.get(col, 0))

        # Surface encoding
        surface_map = {'Hard': 0, 'Clay': 1, 'Grass': 2, 'Carpet': 3}
        feat_row['Surface_encoded'] = surface_map.get(surface, 0)

        # Month / season context
        now = pd.Timestamp.now()
        feat_row['Month'] = now.month

        match_features = pd.DataFrame([feat_row])

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

        # Goes to distance / set handicap / correct score
        # Model biases toward predicting goes_distance — prob[0]/prob[1] swapped
        # to counter inversion. Treat as low-confidence market (~55% effective acc).
        if 'goes_distance' in models:
            X       = get_X('goes_distance')
            prob    = models['goes_distance']['model'].predict_proba(X)[0]
            p_dist  = round(float(prob[0]) * 100, 1)   # swapped
            p_str   = round(float(prob[1]) * 100, 1)   # swapped
            goes    = float(prob[0]) > float(prob[1])  # swapped
            result['match_length'] = {
                'correct_score':  '2-1' if goes else '2-0',
                'set_handicap':   'Does NOT cover -1.5' if goes else 'Covers -1.5 (straight sets)',
                'prob_distance':  p_dist,
                'prob_straight':  p_str,
                'low_confidence': True,
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_basketball_stats(home: str, away: str) -> dict:
    """Build comprehensive team stats for the stats page."""
    df = _basketball_hist.copy()

    def team_games(team):
        return df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].sort_values('Date')

    def last_n(team, n=10):
        tg = team_games(team).tail(n)
        results = []
        for _, row in tg.iterrows():
            if row['HomeTeam'] == team:
                won = row['HomeScore'] > row['AwayScore']
                pts_for, pts_ag = row['HomeScore'], row['AwayScore']
            else:
                won = row['AwayScore'] > row['HomeScore']
                pts_for, pts_ag = row['AwayScore'], row['HomeScore']
            results.append({'won': won, 'pts_for': pts_for, 'pts_ag': pts_ag,
                            'date': str(row['Date'])[:10]})
        return results

    def team_summary(team, n=10):
        results = last_n(team, n)
        if not results:
            return None
        wins   = sum(1 for r in results if r['won'])
        losses = len(results) - wins
        ppg    = round(sum(r['pts_for'] for r in results) / len(results), 1)
        papg   = round(sum(r['pts_ag']  for r in results) / len(results), 1)
        form   = ['W' if r['won'] else 'L' for r in results]
        streak = 0
        for r in reversed(results):
            if (r['won'] and form[-1] == 'W') or (not r['won'] and form[-1] == 'L'):
                streak += 1
            else:
                break
        streak_type = 'W' if results[-1]['won'] else 'L'

        # Shooting stats — last 10 home games
        hg = df[df['HomeTeam'] == team].tail(10)
        ag = df[df['AwayTeam'] == team].tail(10)
        fg_pct  = round(pd.concat([hg['HomeFG'] if 'HomeFG' in df.columns else pd.Series([]),
                                   ag['AwayFG'] if 'AwayFG' in df.columns else pd.Series([])]).mean() * 100, 1)
        fg3_pct = round(pd.concat([hg['HomeFG3'] if 'HomeFG3' in df.columns else pd.Series([]),
                                   ag['AwayFG3'] if 'AwayFG3' in df.columns else pd.Series([])]).mean() * 100, 1)
        ft_pct  = round(pd.concat([hg['HomeFT'] if 'HomeFT' in df.columns else pd.Series([]),
                                   ag['AwayFT'] if 'AwayFT' in df.columns else pd.Series([])]).mean() * 100, 1)
        reb     = round(pd.concat([hg['HomeREB'] if 'HomeREB' in df.columns else pd.Series([]),
                                   ag['AwayREB'] if 'AwayREB' in df.columns else pd.Series([])]).mean(), 1)
        ast     = round(pd.concat([hg['HomeAST'] if 'HomeAST' in df.columns else pd.Series([]),
                                   ag['AwayAST'] if 'AwayAST' in df.columns else pd.Series([])]).mean(), 1)
        to      = round(pd.concat([hg['HomeTO'] if 'HomeTO' in df.columns else pd.Series([]),
                                   ag['AwayTO'] if 'AwayTO' in df.columns else pd.Series([])]).mean(), 1)

        # Home record
        hgames = df[df['HomeTeam'] == team]
        home_w = (hgames['HomeScore'] > hgames['AwayScore']).sum()
        home_l = len(hgames) - home_w

        # Away record
        agames = df[df['AwayTeam'] == team]
        away_w = (agames['AwayScore'] > agames['HomeScore']).sum()
        away_l = len(agames) - away_w

        # Over/Under trends (last 10)
        totals = [r['pts_for'] + r['pts_ag'] for r in results]
        avg_total  = round(sum(totals) / len(totals), 1)
        over225    = sum(1 for t in totals if t > 225)

        return {
            'wins': wins, 'losses': losses,
            'ppg': ppg, 'papg': papg,
            'form': form,
            'streak': f"{streak_type}{streak}",
            'fg_pct': fg_pct, 'fg3_pct': fg3_pct, 'ft_pct': ft_pct,
            'reb': reb, 'ast': ast, 'to': to,
            'ast_to': round(ast / to, 2) if to else 0,
            'home_record': f"{home_w}-{home_l}",
            'away_record': f"{away_w}-{away_l}",
            'avg_total': avg_total,
            'over225_pct': round(over225 / len(results) * 100),
            'recent_games': results,
        }

    # H2H
    h2h_all = df[
        ((df['HomeTeam'] == home) & (df['AwayTeam'] == away)) |
        ((df['HomeTeam'] == away) & (df['AwayTeam'] == home))
    ].sort_values('Date').tail(10)

    h2h_games = []
    home_h2h_wins = 0
    for _, row in h2h_all.iterrows():
        if row['HomeTeam'] == home:
            hw = row['HomeScore'] > row['AwayScore']
            score = f"{int(row['HomeScore'])}-{int(row['AwayScore'])}"
        else:
            hw = row['AwayScore'] > row['HomeScore']
            score = f"{int(row['AwayScore'])}-{int(row['HomeScore'])}"
        if hw:
            home_h2h_wins += 1
        h2h_games.append({
            'date': str(row['Date'])[:10],
            'score': score,
            'winner': home if hw else away,
            'total': int(row['HomeScore'] + row['AwayScore']),
        })
    away_h2h_wins = len(h2h_games) - home_h2h_wins
    h2h_avg_total = round(sum(g['total'] for g in h2h_games) / len(h2h_games), 1) if h2h_games else 0
    h2h_over225   = sum(1 for g in h2h_games if g['total'] > 225)

    return {
        'home': team_summary(home),
        'away': team_summary(away),
        'h2h': {
            'games': list(reversed(h2h_games)),
            'home_wins': home_h2h_wins,
            'away_wins': away_h2h_wins,
            'total_games': len(h2h_games),
            'avg_total': h2h_avg_total,
            'over225_count': h2h_over225,
        },
        'league': 'NBA',
    }


def _get_nba_teams():
    """Return dict with 'NBA' and 'EuroLeague' team lists."""
    try:
        combined = project_root / "data/basketball/raw/basketball_all_data.csv"
        nba_csv  = project_root / "data/basketball/raw/nba_real_data.csv"
        if combined.exists():
            df = pd.read_csv(combined, usecols=['HomeTeam', 'League'])
            nba_teams = sorted(df[df['League']=='NBA']['HomeTeam'].dropna().unique().tolist())
            eur_teams = sorted(df[df['League']=='EuroLeague']['HomeTeam'].dropna().unique().tolist())
            return {'NBA': nba_teams, 'EuroLeague': eur_teams}
        elif nba_csv.exists():
            df = pd.read_csv(nba_csv, usecols=['HomeTeam'])
            return {'NBA': sorted(df['HomeTeam'].dropna().unique().tolist()), 'EuroLeague': []}
    except Exception:
        pass
    return {
        'NBA': [
            "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
            "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
            "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
            "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
            "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
            "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
            "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
            "Utah Jazz", "Washington Wizards",
        ],
        'EuroLeague': [],
    }
