# app/routes.py - UPDATED VERSION WITH CACHING AND LIVE SCORES

# Fix for pkg_resources in Python 3.12+ (required for model deserialization)
import sys
try:
    import pkg_resources
except ImportError:
    # Python 3.12+ workaround: use importlib.metadata as pkg_resources replacement
    try:
        from importlib import metadata as importlib_metadata
        sys.modules['pkg_resources'] = type(sys)('pkg_resources')
        sys.modules['pkg_resources'].get_distribution = lambda name: type('obj', (object,), {'version': importlib_metadata.version(name)})()
    except Exception:
        # Fallback: create minimal mock
        sys.modules['pkg_resources'] = type(sys)('pkg_resources')

from datetime import datetime
import logging

from flask import Blueprint, render_template, request, jsonify
import joblib
import pandas as pd
import os
import numpy as np


# Enhanced import for predictor
from footy.predictor_utils import create_bayesian_predictor

# Import ALL the analyzers

from footy.opening_weekend_analyzer import OpeningWeekendAnalyzer
from footy.weekly_insights_analyzer import WeeklyInsightsAnalyzer
from footy.insights import FootballInsights
from footy.advanced_stats import DisciplineAnalyzer


# Import api service class
from app.services.football_service import FootballDataService

# Import caching and live scores
from app.caching import get_cache, POPULAR_MATCHUPS
from app.services.live_scores_service import get_live_scores_service
from app.services.team_resolver import resolve_team as _resolve_team

# Import betting tips generator
from app.betting_tips import get_betting_tips_generator

# Create blueprint
routes = Blueprint('routes', __name__)

# Global variables
predictor = None
teams = []
gw1_analyzer = None
weekly_analyzer = None
prediction_cache = None
live_scores_service = None
discipline_analyzer = None
league_teams = {}  # {league_code: [team_names]}

LEAGUE_NAMES = {
    'E0': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', 'E1': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship', 'E2': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 League One',
    'E3': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 League Two', 'SP1': '🇪🇸 La Liga', 'SP2': '🇪🇸 La Liga 2',
    'D1': '🇩🇪 Bundesliga', 'D2': '🇩🇪 Bundesliga 2', 'I1': '🇮🇹 Serie A',
    'I2': '🇮🇹 Serie B', 'F1': '🇫🇷 Ligue 1', 'F2': '🇫🇷 Ligue 2',
    'N1': '🇳🇱 Eredivisie', 'P1': '🇵🇹 Primeira Liga', 'B1': '🇧🇪 Pro League',
    'SC0': '🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scottish Prem', 'T1': '🇹🇷 Süper Lig', 'G1': '🇬🇷 Super League',
    'ARG1': '🇦🇷 Argentine Primera', 'BRA1': '🇧🇷 Brasileirão',
    'USA1': '🇺🇸 MLS', 'MX1': '🇲🇽 Liga MX',
}


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

def generate_comprehensive_insights(predictor_df, home_team, away_team, weekly_analyzer, gw1_analyzer):
    """Generate insights that actively GUIDE users toward smart predictions"""

    insights = []
    prediction_signals = []  # HIGH-CONFIDENCE prediction signals added at the end

    try:
        # 1. DETECT CURRENT GAMEWEEK FROM ACTUAL DATA
        if weekly_analyzer:
            current_gw = weekly_analyzer.detect_current_gameweek()
            insights.append(f"[GW] Gameweek {current_gw}")
    except:
        pass

    try:
        # 2. GET LATEST ACTUAL MATCH RESULTS with valid season filter
        all_seasons = predictor_df['Season'].dropna().unique()
        import re as _re
        valid_seasons = [s for s in all_seasons if _re.match(r'^\d{4}[-/]\d{4}$', str(s))]
        if not valid_seasons:
            valid_seasons = list(all_seasons)
        latest_season = sorted(valid_seasons)[-1]

        if not pd.api.types.is_datetime64_any_dtype(predictor_df['Date']):
            predictor_df = predictor_df.copy()
            predictor_df['Date'] = pd.to_datetime(predictor_df['Date'], errors='coerce')

        latest_season_matches = predictor_df[
            predictor_df['Season'] == latest_season
        ].sort_values('Date')

        if len(latest_season_matches) > 0:
            for team, label in [(home_team, 'Latest'), (away_team, 'Away')]:
                team_latest = latest_season_matches[
                    (latest_season_matches['HomeTeam'] == team) |
                    (latest_season_matches['AwayTeam'] == team)
                ].tail(1)
                if len(team_latest) > 0:
                    match = team_latest.iloc[0]
                    date = match['Date'].strftime('%b %d') if hasattr(match['Date'], 'strftime') else str(match['Date'])
                    if match['HomeTeam'] == team:
                        score = f"{match['FTHG']}-{match['FTAG']}"
                        opponent, venue = match['AwayTeam'], "H"
                        result_emoji = "[W]" if match['FTR'] == 'H' else "[D]" if match['FTR'] == 'D' else "[L]"
                    else:
                        score = f"{match['FTAG']}-{match['FTHG']}"
                        opponent, venue = match['HomeTeam'], "A"
                        result_emoji = "[W]" if match['FTR'] == 'A' else "[D]" if match['FTR'] == 'D' else "[L]"
                    insights.append(f"[{label}] {team}: {result_emoji} {score} vs {opponent} ({venue}) - {date}")
    except Exception as e:
        print(f"Latest season results error: {e}")

    # ==================== HELPER: ANALYZE FORM ====================
    def analyze_form(team, n=6):
        """Returns stats dict for a team's last n matches"""
        recent = predictor_df[
            (predictor_df['HomeTeam'] == team) | (predictor_df['AwayTeam'] == team)
        ].sort_values('Date', ascending=False).head(n)
        if len(recent) == 0:
            return None
        wins = draws = losses = 0
        gf = ga = cs = over25 = btts_count = 0
        letters = []
        for _, m in recent.iterrows():
            if m['HomeTeam'] == team:
                mgf, mga = m['FTHG'], m['FTAG']
                res = 'W' if m['FTR'] == 'H' else 'D' if m['FTR'] == 'D' else 'L'
            else:
                mgf, mga = m['FTAG'], m['FTHG']
                res = 'W' if m['FTR'] == 'A' else 'D' if m['FTR'] == 'D' else 'L'
            letters.append(res)
            if res == 'W': wins += 1
            elif res == 'D': draws += 1
            else: losses += 1
            gf += mgf
            ga += mga
            if mga == 0: cs += 1
            if mgf + mga > 2.5: over25 += 1
            if mgf > 0 and mga > 0: btts_count += 1
        n_actual = len(recent)
        return {
            'letters': ''.join(letters),
            'wins': wins, 'draws': draws, 'losses': losses,
            'avg_gf': round(gf / n_actual, 2), 'avg_ga': round(ga / n_actual, 2),
            'clean_sheets': cs, 'n': n_actual,
            'over25_rate': round(over25 / n_actual * 100, 0),
            'btts_rate': round(btts_count / n_actual * 100, 0),
            'last3': letters[:3],
        }

    home_form = analyze_form(home_team)
    away_form = analyze_form(away_team)

    # 3. HOME TEAM FORM + STREAK SIGNALS
    try:
        if home_form:
            insights.append(f"[Form] {home_team} last {home_form['n']}: {home_form['letters']} ({home_form['wins']}W-{home_form['draws']}D-{home_form['losses']}L)")
            insights.append(f"[Goals] {home_team} scoring: {home_form['avg_gf']:.1f}/game, conceding {home_form['avg_ga']:.1f}")
            if home_form['clean_sheets'] > 0:
                insights.append(f"[Clean] {home_team}: {home_form['clean_sheets']}/{home_form['n']} clean sheets")

            # HOT/COLD STREAKS
            last3 = home_form['last3']
            if last3.count('W') == 3:
                prediction_signals.append(f"🔥 {home_team} on 3-GAME WIN STREAK — back home confidence HIGH")
            elif last3.count('L') == 3:
                prediction_signals.append(f"❄️  {home_team} on 3-GAME LOSING STREAK — vulnerable, consider Away Win")
            elif last3.count('W') == 0:
                prediction_signals.append(f"⚠️  {home_team} winless in last 3 — home advantage may not be enough")

            # GOAL TREND SIGNALS
            if home_form['over25_rate'] >= 70:
                prediction_signals.append(f"⚽ {home_team} in Over 2.5 matches {home_form['over25_rate']:.0f}% of last {home_form['n']} games — lean OVER 2.5")
            if home_form['btts_rate'] >= 70:
                prediction_signals.append(f"🎯 {home_team} in BTTS matches {home_form['btts_rate']:.0f}% of last {home_form['n']} games — lean BTTS YES")
            if home_form['avg_ga'] > 2.0:
                prediction_signals.append(f"⚠️  {home_team} leaking {home_form['avg_ga']:.1f} goals/game — defensive fragility alert")
    except Exception as e:
        print(f"Home form error: {e}")

    # 4. AWAY TEAM FORM + STREAK SIGNALS
    try:
        if away_form:
            insights.append(f"[Form] {away_team} last {away_form['n']}: {away_form['letters']} ({away_form['wins']}W-{away_form['draws']}D-{away_form['losses']}L)")
            insights.append(f"[Goals] {away_team} scoring: {away_form['avg_gf']:.1f}/game, conceding {away_form['avg_ga']:.1f}")
            if away_form['clean_sheets'] > 0:
                insights.append(f"[Clean] {away_team}: {away_form['clean_sheets']}/{away_form['n']} clean sheets")

            # AWAY TEAM HOT/COLD
            last3 = away_form['last3']
            if last3.count('W') == 3:
                prediction_signals.append(f"🔥 {away_team} on 3-GAME WIN STREAK — strong form away is a danger sign for {home_team}")
            elif last3.count('L') == 3:
                prediction_signals.append(f"❄️  {away_team} on 3-GAME LOSING STREAK — {home_team} home win value likely STRONG")
    except Exception as e:
        print(f"Away form error: {e}")

    # 5. HEAD-TO-HEAD ANALYSIS WITH BETTING SIGNALS
    try:
        h2h = predictor_df[
            ((predictor_df['HomeTeam'] == home_team) & (predictor_df['AwayTeam'] == away_team)) |
            ((predictor_df['HomeTeam'] == away_team) & (predictor_df['AwayTeam'] == home_team))
        ].sort_values('Date', ascending=False).head(10)

        if len(h2h) > 0:
            h_wins = len(h2h[((h2h['HomeTeam'] == home_team) & (h2h['FTR'] == 'H')) |
                            ((h2h['AwayTeam'] == home_team) & (h2h['FTR'] == 'A'))])
            drws = len(h2h[h2h['FTR'] == 'D'])
            a_wins = len(h2h) - h_wins - drws
            avg_goals = (h2h['FTHG'] + h2h['FTAG']).mean()
            over25_h2h = len(h2h[(h2h['FTHG'] + h2h['FTAG']) > 2.5]) / len(h2h) * 100
            btts_h2h = len(h2h[(h2h['FTHG'] > 0) & (h2h['FTAG'] > 0)]) / len(h2h) * 100

            insights.append(f"[H2H] Last {len(h2h)} H2H: {home_team} {h_wins}W-{drws}D-{a_wins}L vs {away_team}")
            insights.append(f"[H2H] Avg {avg_goals:.1f} goals/game | Over 2.5: {over25_h2h:.0f}% | BTTS: {btts_h2h:.0f}%")

            # H2H BETTING SIGNALS
            if over25_h2h >= 70 and len(h2h) >= 5:
                prediction_signals.append(f"📊 Over 2.5 in {over25_h2h:.0f}% of last {len(h2h)} H2H — STRONG Over 2.5 signal")
            elif over25_h2h <= 30 and len(h2h) >= 5:
                prediction_signals.append(f"🔒 Only {over25_h2h:.0f}% Over 2.5 in H2H — lean Under 2.5 Goals")

            if btts_h2h >= 70 and len(h2h) >= 5:
                prediction_signals.append(f"🎯 BTTS in {btts_h2h:.0f}% of H2H — Both Teams Score very likely")
            elif btts_h2h <= 30 and len(h2h) >= 5:
                prediction_signals.append(f"🔒 Only {btts_h2h:.0f}% BTTS in H2H — Under or one team to keep clean sheet")

            if h_wins >= len(h2h) * 0.6:
                prediction_signals.append(f"📈 {home_team} wins {h_wins}/{len(h2h)} recent H2H — historical Home Win edge")
            elif a_wins >= len(h2h) * 0.6:
                prediction_signals.append(f"📈 {away_team} wins {a_wins}/{len(h2h)} recent H2H — historical Away Win edge")
    except Exception as e:
        print(f"H2H analysis error: {e}")

    # 6. VENUE-SPECIFIC PERFORMANCE
    try:
        home_at_home = predictor_df[predictor_df['HomeTeam'] == home_team].sort_values('Date').tail(10)
        if len(home_at_home) >= 5:
            hw = len(home_at_home[home_at_home['FTR'] == 'H'])
            hgf = home_at_home['FTHG'].mean()
            hga = home_at_home['FTAG'].mean()
            insights.append(f"[Home] {home_team} at home: {hw}/{len(home_at_home)} wins ({hw/len(home_at_home)*100:.0f}%)")
            insights.append(f"[Home] {home_team} home scoring: {hgf:.1f} for, {hga:.1f} against")
            if hw / len(home_at_home) >= 0.7:
                prediction_signals.append(f"🏟️  {home_team} wins {hw/len(home_at_home)*100:.0f}% at home — HOME WIN strong bet")
            if hga >= 1.8:
                prediction_signals.append(f"⚠️  {home_team} concedes {hga:.1f}/game at home — {away_team} can score here")

        away_away = predictor_df[predictor_df['AwayTeam'] == away_team].sort_values('Date').tail(10)
        if len(away_away) >= 5:
            aw = len(away_away[away_away['FTR'] == 'A'])
            agf = away_away['FTAG'].mean()
            aga = away_away['FTHG'].mean()
            insights.append(f"[Away] {away_team} away: {aw}/{len(away_away)} wins ({aw/len(away_away)*100:.0f}%)")
            insights.append(f"[Away] {away_team} away scoring: {agf:.1f} for, {aga:.1f} against")
            if aw == 0 and len(away_away) >= 5:
                prediction_signals.append(f"⚠️  {away_team} has ZERO away wins in last {len(away_away)} games — avoid Away Win bet")
            if aga >= 2.0:
                prediction_signals.append(f"⚽ {away_team} concedes {aga:.1f}/game away — {home_team} to score is HIGH probability")
    except Exception as e:
        print(f"Venue analysis error: {e}")

    # 7. xG UNDER/OVER-PERFORMANCE SIGNALS (if xG data available)
    try:
        for team, label in [(home_team, 'home'), (away_team, 'away')]:
            team_recent = predictor_df[
                (predictor_df['HomeTeam'] == team) | (predictor_df['AwayTeam'] == team)
            ].sort_values('Date', ascending=False).head(8)

            xg_col = 'HomexG' if label == 'home' else 'AwayxG'
            goals_col = 'FTHG' if label == 'home' else 'FTAG'
            if xg_col in team_recent.columns:
                home_rows = team_recent[team_recent['HomeTeam'] == team]
                away_rows = team_recent[team_recent['AwayTeam'] == team]
                xg_vals, goal_vals = [], []
                for _, m in home_rows.iterrows():
                    if pd.notnull(m.get('HomexG')):
                        xg_vals.append(m['HomexG']); goal_vals.append(m['FTHG'])
                for _, m in away_rows.iterrows():
                    if pd.notnull(m.get('AwayxG')):
                        xg_vals.append(m['AwayxG']); goal_vals.append(m['FTAG'])
                if xg_vals and goal_vals:
                    avg_xg = sum(xg_vals) / len(xg_vals)
                    avg_g = sum(goal_vals) / len(goal_vals)
                    diff = avg_xg - avg_g
                    if diff >= 0.6:
                        prediction_signals.append(f"📡 {team} xG ({avg_xg:.1f}) >> Actual Goals ({avg_g:.1f}) — UNDERPERFORMING, expect more goals soon")
                    elif diff <= -0.5:
                        prediction_signals.append(f"📡 {team} xG ({avg_xg:.1f}) << Actual Goals ({avg_g:.1f}) — OVERPERFORMING on finishing, may regress")
    except Exception as e:
        print(f"xG analysis error: {e}")

    # ---- COMBINE: put raw stats first, then ACTIONABLE SIGNALS at end ----
    if prediction_signals:
        insights.append("── PREDICTION SIGNALS ──")
        insights.extend(prediction_signals)

    return insights




def initialize_predictor():
    """Initialize prediction system with caching and live scores"""
    global predictor, teams, prediction_cache, live_scores_service
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load standard models
        models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')
        print(f"[Init] Loading standard models from {models_path}")

        # Try multiple data file options - PRIORITIZE ZIP TO BYPASS LFS
        data_options = [
            os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_bayesian_features.csv.zip'),
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
                print(f"[OK] Found data file: {option}")
                break

        if not data_path:
            print(f"[Error] No data file found")
            return None, []

        if not os.path.exists(models_path):
            print(f"[Error] Models file not found: {models_path}")
            return None, []

        # Load data with LFS pointer validation
        try:
            df = pd.read_csv(data_path, low_memory=False)
            
            # Check for LFS pointer file (small file size, few rows, missing columns)
            if len(df) < 100 or 'HomeTeam' not in df.columns:
                print(f"[Warning] Data file seems invalid (possible Git LFS pointer): {data_path}")
                print(f"   Rows: {len(df)}, Columns: {df.columns.tolist()}")
                
                # Check other options
                print("[Init] Attempting fallback to other data files...")
                found_fallback = False
                for option in data_options:
                     if option != data_path and os.path.exists(option):
                         try:
                             fallback_df = pd.read_csv(option, low_memory=False)
                             if len(fallback_df) > 100 and 'HomeTeam' in fallback_df.columns:
                                 df = fallback_df
                                 print(f"[OK] Fallback successful: {option}")
                                 found_fallback = True
                                 break
                         except:
                             continue
                
                if not found_fallback:
                    print("[Error] No valid data file found after fallback attempts")
                    return None, []

            print(f"[OK] Data loaded: {df.shape}")
        except Exception as e:
            print(f"[Error] Failed to load data: {e}")
            return None, []

        # Extract teams from data BEFORE predictor creation so teams always show
        # even when the model file is unavailable (e.g. Git LFS pointer on deploy)
        teams = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))
        print(f"[OK] Teams extracted from data: {len(teams)}")

        # Guard against LFS pointer files (< 1 KB = not the real model)
        if os.path.getsize(models_path) < 1024:
            print(f"[Warning] football_models.joblib is an LFS pointer "
                  f"({os.path.getsize(models_path)} bytes) — predictions unavailable but teams loaded")
            return None, teams

        # Create predictor
        predictor = create_bayesian_predictor(df, models_path)
        if predictor is None:
            print("[Error] Failed to create predictor")
            return None, teams

        # Initialize analyzers
        global gw1_analyzer, weekly_analyzer
        try:
            gw1_analyzer = OpeningWeekendAnalyzer(df)
            weekly_analyzer = WeeklyInsightsAnalyzer(df)
            print(f"[OK] All analyzers initialized")
        except Exception as e:
            print(f"[Warning] Analyzer initialization failed: {e}")

        # Initialize Discipline Analyzer
        global discipline_analyzer
        try:
            discipline_analyzer = DisciplineAnalyzer(df)
            print(f"[OK] Discipline Analyzer initialized")
        except Exception as e:
            print(f"[Warning] Discipline Analyzer initialization failed: {e}")

        # Build league -> teams mapping for the league filter UI
        global league_teams
        try:
            import re as _re
            all_s = df['Season'].dropna().unique()
            valid_s = [s for s in all_s if _re.match(r'^\d{4}[-/]\d{4}$', str(s))]
            latest_s = sorted(valid_s)[-1] if valid_s else None
            src = df[df['Season'] == latest_s] if latest_s else df
            lt = {}
            for lg in src['League'].dropna().unique():
                lg_df = src[src['League'] == lg]
                lg_t = sorted(set(lg_df['HomeTeam'].dropna().tolist()) | set(lg_df['AwayTeam'].dropna().tolist()))
                if lg_t:
                    lt[str(lg)] = lg_t
            league_teams = lt
            print(f"[OK] League teams map: {len(league_teams)} leagues")
        except Exception as e:
            print(f"[Warning] League teams map failed: {e}")

        # Initialize caching system
        try:
            prediction_cache = get_cache(use_redis=False, max_size=1000, ttl_hours=24)
            print(f"[OK] Prediction cache initialized")
            
            # Warm cache with popular matchups (async in background)
            # prediction_cache.warm_cache(predictor, POPULAR_MATCHUPS)
        except Exception as e:
            print(f"[Warning] Cache initialization failed: {e}")
            prediction_cache = None
        
        # Initialize live scores service
        try:
            live_scores_service = get_live_scores_service()
            print(f"[OK] Live scores service initialized")
        except Exception as e:
            print(f"[Warning] Live scores service failed: {e}")
            live_scores_service = None

        print(f"[OK] System initialized with {len(teams)} teams")
        return predictor, teams

    except Exception as e:
        print(f"[Error] Error initializing system: {str(e)}")
        return None, []


# Initialize predictor
predictor, teams = initialize_predictor()

@routes.route('/api/league-teams')
def api_league_teams():
    """Return teams grouped by league for the predict page league filter"""
    return jsonify({'league_teams': league_teams, 'league_names': LEAGUE_NAMES})

def check_initialization():
    """Ensure system is initialized before serving requests"""
    global predictor, teams
    if not teams or not predictor:
        print("[System] Lazy initialization triggered...")
        predictor, teams = initialize_predictor()
    return predictor, teams

@routes.route('/')
def home():
    """Home page"""
    check_initialization()
    return render_template('index.html', teams=teams)


@routes.route('/api/debug/status')
def debug_status():
    """Debug endpoint to check system status"""
    global predictor, teams
    return jsonify({
        'status': 'online',
        'teams_count': len(teams) if teams else 0,
        'predictor_loaded': predictor is not None,
        'teams_sample': teams[:5] if teams else []
    })


@routes.route('/predict', methods=['GET', 'POST'])
def predict():
    """Prediction page with caching"""
    current_predictor, current_teams = check_initialization()
    
    # Use explicitly returned teams to avoid global variable issues
    teams = current_teams
    predictor = current_predictor
    
    if request.method == 'POST':

        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')

        if not home_team or not away_team:
            return render_template('predict.html', teams=teams, error="Please select both teams")

        if not predictor:
            return render_template('predict.html', teams=teams, error="Prediction system not available")

        try:
            print(f"[Predict] Making prediction: {home_team} vs {away_team}")
            
            # Try to get from cache first
            result = None
            cache_hit = False
            if prediction_cache:
                result = prediction_cache.get(home_team, away_team)
                if result:
                    cache_hit = True
                    print(f"[Cache] HIT: Using cached prediction")
            
            # If not in cache, generate prediction
            if result is None:
                print(f"[Cache] MISS: Generating new prediction")
                result = predictor.predict_with_full_bayesian_analysis(home_team, away_team)
                
                # Cache the result
                if prediction_cache:
                    prediction_cache.set(home_team, away_team, result)

            # Convert numpy types
            predictions = convert_numpy_types(result.get('predictions', {}))
            probabilities = convert_numpy_types(result.get('probabilities', {}))
            confidence_intervals = convert_numpy_types(result.get('confidence_intervals', {}))
            poisson_analysis = convert_numpy_types(result.get('poisson_analysis', {}))

            # Format Match Outcome probabilities for display
            if 'Match Outcome' in probabilities and isinstance(probabilities['Match Outcome'], dict):
                for outcome, prob in probabilities['Match Outcome'].items():
                    try:
                        probabilities['Match Outcome'][outcome] = f"{float(prob) * 100:.1f}%"
                    except:
                        pass

            # 🚀 GENERATE COMPREHENSIVE DYNAMIC INSIGHTS
            try:
                match_insights = generate_comprehensive_insights(
                    predictor.df,
                    home_team,
                    away_team,
                    weekly_analyzer,
                    gw1_analyzer
                )

                # Add prediction-specific insights
                over_25_pred = predictions.get('Over 2.5 Goals', 'N/A')
                btts_pred = predictions.get('Both Teams to Score', 'N/A')
                total_goals = predictions.get('Total Goals', 'N/A')

                if over_25_pred != 'N/A':
                    match_insights.append(f"[Target] Over 2.5 Goals prediction: {over_25_pred}")

                if btts_pred != 'N/A':
                    match_insights.append(f"[Goals] Both teams to score: {btts_pred}")

                if total_goals != 'N/A':
                    match_insights.append(f"[Net] Expected total goals: {total_goals}")

                # ── DRAW DETECTION ENGINE ──────────────────────────────────
                draw_signals = []
                try:
                    df_copy = predictor.df.copy()
                    # Ensure FTR column exists (H/D/A)
                    if 'FTR' in df_copy.columns:
                        # 1. Team-level draw rate (last 20 home/away matches each)
                        home_matches = df_copy[
                            (df_copy['HomeTeam'] == home_team) | (df_copy['AwayTeam'] == home_team)
                        ].sort_values('Date', ascending=False).head(20) if 'Date' in df_copy.columns else \
                        df_copy[(df_copy['HomeTeam'] == home_team) | (df_copy['AwayTeam'] == home_team)].tail(20)

                        away_matches = df_copy[
                            (df_copy['HomeTeam'] == away_team) | (df_copy['AwayTeam'] == away_team)
                        ].sort_values('Date', ascending=False).head(20) if 'Date' in df_copy.columns else \
                        df_copy[(df_copy['HomeTeam'] == away_team) | (df_copy['AwayTeam'] == away_team)].tail(20)

                        # Draw = FTR == 'D'
                        if len(home_matches) >= 5:
                            home_draw_rate = (home_matches['FTR'] == 'D').mean()
                            if home_draw_rate >= 0.35:
                                draw_signals.append(f"⚖️ {home_team} draws {home_draw_rate*100:.0f}% of recent matches (draw-prone team)")

                        if len(away_matches) >= 5:
                            away_draw_rate = (away_matches['FTR'] == 'D').mean()
                            if away_draw_rate >= 0.35:
                                draw_signals.append(f"⚖️ {away_team} draws {away_draw_rate*100:.0f}% of recent matches (draw-prone team)")

                        # 2. H2H draw rate
                        h2h = df_copy[
                            ((df_copy['HomeTeam'] == home_team) & (df_copy['AwayTeam'] == away_team)) |
                            ((df_copy['HomeTeam'] == away_team) & (df_copy['AwayTeam'] == home_team))
                        ].tail(10)

                        if len(h2h) >= 4:
                            h2h_draw_rate = (h2h['FTR'] == 'D').mean()
                            if h2h_draw_rate >= 0.35:
                                draw_signals.append(f"⚖️ H2H: {h2h_draw_rate*100:.0f}% of head-to-head meetings ended as draws ({len(h2h)} matches)")

                        # 3. League-level draw rate (some leagues are structurally draw-heavy)
                        HIGH_DRAW_LEAGUES = {
                            'Championship': 0.28, 'Ligue 2': 0.28, 'Serie B': 0.28,
                            'Segunda Division': 0.27, 'Bundesliga 2': 0.27, '2. Bundesliga': 0.27,
                            'Eredivisie': 0.27, 'Scottish Premiership': 0.27,
                        }
                        team_league = None
                        if 'League' in df_copy.columns:
                            league_guess = df_copy[
                                (df_copy['HomeTeam'] == home_team) | (df_copy['AwayTeam'] == home_team)
                            ]['League'].mode()
                            team_league = str(league_guess.iloc[0]) if not league_guess.empty else None

                        if team_league:
                            # Check if it matches any known high-draw league (case-insensitive partial match)
                            for league_name, threshold in HIGH_DRAW_LEAGUES.items():
                                if league_name.lower() in team_league.lower():
                                    # Calculate actual league draw rate from data
                                    league_matches = df_copy[df_copy['League'] == team_league].tail(200)
                                    if len(league_matches) >= 30:
                                        actual_rate = (league_matches['FTR'] == 'D').mean()
                                        if actual_rate >= threshold:
                                            draw_signals.append(
                                                f"⚖️ {team_league} is a high-draw league ({actual_rate*100:.0f}% draw rate) — draw probability elevated"
                                            )
                                    else:
                                        draw_signals.append(
                                            f"⚖️ {team_league} is historically a high-draw league — consider draw as value bet"
                                        )
                                    break

                        # 4. Model draw probability signal (if probabilities dict has it)
                        raw_probs = result.get('probabilities', {})
                        outcome_probs = raw_probs.get('Match Outcome', {})
                        if isinstance(outcome_probs, dict):
                            for k, v in outcome_probs.items():
                                if 'draw' in k.lower():
                                    try:
                                        draw_p = float(str(v).replace('%', '')) / 100 if '%' in str(v) else float(v)
                                        if draw_p >= 0.28:
                                            draw_signals.append(
                                                f"⚖️ Model assigns {draw_p*100:.1f}% draw probability — strong value draw candidate"
                                            )
                                    except Exception:
                                        pass

                        # 5. Both teams in low-scoring form → low goal expectation = draw alert
                        if 'FTHG' in df_copy.columns and 'FTAG' in df_copy.columns:
                            home_goals_scored = home_matches['FTHG'].where(
                                home_matches['HomeTeam'] == home_team, home_matches['FTAG']
                            ).mean() if len(home_matches) >= 5 else None

                            away_goals_scored = away_matches['FTHG'].where(
                                away_matches['HomeTeam'] == away_team, away_matches['FTAG']
                            ).mean() if len(away_matches) >= 5 else None

                            if home_goals_scored and away_goals_scored:
                                if home_goals_scored < 1.2 and away_goals_scored < 1.2:
                                    draw_signals.append(
                                        f"⚖️ Both teams averaging low goals scored ({home_goals_scored:.1f} & {away_goals_scored:.1f}) — low-scoring game, draw possible"
                                    )

                except Exception as e:
                    print(f"[Draw Detection] Error: {e}")

                # Inject draw signals into PREDICTION SIGNALS section
                if draw_signals:
                    # Find or create the PREDICTION SIGNALS separator
                    has_signal_sep = any('PREDICTION SIGNALS' in i for i in match_insights)
                    if not has_signal_sep:
                        match_insights.append("── PREDICTION SIGNALS ──")
                    match_insights.extend(draw_signals)
                # ──────────────────────────────────────────────────────────

                # Add cache status
                if cache_hit:
                    match_insights.insert(0, "[⚡] Instant prediction from cache")

            except Exception as e:
                print(f"[Warning] Comprehensive insights error: {e}")
                match_insights = [f"[Goals] Basic prediction for {home_team} vs {away_team}"]

            # Format insights for display
            enhanced_insights = {
                'key_insights': match_insights[:30]  # Expanded to 30 to accommodate draw signals
            }

            # Format confidence levels with fallback
            formatted_confidence = {}
            # Ensure we have entries for all main predictions
            target_keys = ['Match Outcome', 'Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals', 'Both Teams to Score']
            
            for key in target_keys:
                if key in confidence_intervals and isinstance(confidence_intervals[key], dict):
                    formatted_confidence[key] = confidence_intervals[key].get('confidence_level', 'Medium')
                else:
                    # Fallback if calculation failed
                    formatted_confidence[key] = 'Medium'
            
            # Generate betting tips
            betting_tips = None
            try:
                tips_gen = get_betting_tips_generator()
                all_tips = tips_gen.generate_tips(
                    predictions,
                    probabilities,
                    home_team,
                    away_team
                )
                betting_tips = tips_gen.format_tips_for_display(all_tips)
                print(f"[Tips] Generated {len(all_tips)} betting tips")
            except Exception as e:
                print(f"[Warning] Betting tips generation failed: {e}")

            # Get Discipline & Corner Stats
            advanced_stats = None
            try:
                if discipline_analyzer:
                    advanced_stats = discipline_analyzer.project_match_stats(home_team, away_team)
            except Exception as e:
                print(f"[Warning] Advanced stats calculation failed: {e}")

            return render_template('predict.html',
                                   teams=teams,
                                   predictions=predictions,
                                   probabilities=probabilities,
                                   confidence_intervals=formatted_confidence,
                                   poisson_scorelines=poisson_analysis,
                                   match_insights=enhanced_insights,
                                   home_team=home_team,
                                   away_team=away_team,
                                   cache_hit=cache_hit,
                                   betting_tips=betting_tips,
                                   advanced_stats=advanced_stats)

        except Exception as e:
            print(f"[Error] Prediction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('predict.html', teams=teams,
                                   error=f"Prediction failed: {str(e)}")

    return render_template('predict.html', teams=teams,
                           league_teams=league_teams, league_names=LEAGUE_NAMES)


@routes.route('/weekend-predictions')
def weekend_predictions():
    """Auto-generate predictions for all Fri/Sat/Sun games this weekend"""
    current_predictor, current_teams = check_initialization()
    svc = get_live_scores_service()

    # --- Get fixtures from API ---
    try:
        raw_grouped = svc.get_weekend_fixtures()
    except Exception as e:
        print(f"[Weekend] Fixture fetch failed: {e}")
        raw_grouped = {}

    def resolve_team(api_name: str):
        return _resolve_team(api_name, current_teams or [])

    # --- Run predictions for each fixture ---
    weekend_days = {}
    total_predicted = 0

    for date_str, fixtures in sorted(raw_grouped.items()):
        day_dt = datetime.strptime(date_str, '%Y-%m-%d')
        day_label = day_dt.strftime('%A, %d %B')  # e.g. "Saturday, 05 April"

        day_results = []
        for fix in fixtures:
            home_local = resolve_team(fix['home_team'])
            away_local = resolve_team(fix['away_team'])

            pred_data = None
            error_msg = None

            if home_local and away_local and current_predictor:
                try:
                    # Use cache if available
                    result = None
                    if prediction_cache:
                        result = prediction_cache.get(home_local, away_local)
                    if result is None:
                        result = current_predictor.predict_with_full_bayesian_analysis(
                            home_local, away_local)
                        if prediction_cache:
                            prediction_cache.set(home_local, away_local, result)

                    preds = convert_numpy_types(result.get('predictions', {}))
                    probs = convert_numpy_types(result.get('probabilities', {}))

                    # Simplify outcome probabilities
                    outcome_probs = {}
                    if 'Match Outcome' in probs and isinstance(probs['Match Outcome'], dict):
                        for k, v in probs['Match Outcome'].items():
                            try:
                                outcome_probs[k] = f"{float(v)*100:.0f}%"
                            except Exception:
                                outcome_probs[k] = str(v)

                    pred_data = {
                        'outcome': preds.get('Match Outcome', 'Unknown'),
                        'outcome_probs': outcome_probs,
                        'over25': preds.get('Over 2.5 Goals', 'Unknown'),
                        'btts': preds.get('Both Teams to Score', 'Unknown'),
                        'draw_risk': result.get('draw_risk', False),
                        'draw_probability': result.get('draw_probability', 0),
                    }
                    total_predicted += 1
                except Exception as e:
                    error_msg = str(e)
                    print(f"[Weekend] Prediction failed for {home_local} vs {away_local}: {e}")
            elif not (home_local and away_local):
                error_msg = "Teams not in local dataset"

            day_results.append({
                'api_home': fix['home_team'],
                'api_away': fix['away_team'],
                'home_team': home_local or fix['home_team'],
                'away_team': away_local or fix['away_team'],
                'competition': fix['competition'],
                'kick_off': fix['kick_off'],
                'prediction': pred_data,
                'error': error_msg,
                'matched': bool(home_local and away_local),
            })

        if day_results:
            weekend_days[date_str] = {
                'label': day_label,
                'fixtures': day_results
            }

    no_api_key = not svc.api_key
    return render_template(
        'weekend.html',
        weekend_days=weekend_days,
        total_predicted=total_predicted,
        no_api_key=no_api_key,
    )


@routes.route('/live-predictions')
def live_predictions_page():
    """Live predictions page"""
    return render_template('live_predictions.html')



@routes.route('/api/live-predictions')
def live_predictions():
    """Live predictions API - fetches today's scheduled fixtures and runs predictions"""
    try:
        current_predictor, current_teams = check_initialization()
        svc = get_live_scores_service()

        # Fetch today's fixtures from the API
        today = datetime.utcnow().strftime('%Y-%m-%d')
        fixtures = []
        try:
            data = svc._make_request("matches", params={
                'status': 'SCHEDULED,TIMED',
                'dateFrom': today,
                'dateTo': today
            })
            if data and 'matches' in data:
                for match in data['matches']:
                    fixtures.append({
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'competition': match['competition']['name'],
                        'utc_date': match['utcDate'],
                    })
        except Exception as e:
            print(f"[Live Predictions] Fixture fetch error: {e}")

        if not fixtures:
            return jsonify({
                'status': 'success',
                'predictions': [],
                'message': 'No fixtures found for today' if svc.api_key else 'No API key configured',
                'timestamp': datetime.utcnow().isoformat()
            })

        # Run predictions on matched fixtures
        live_predictions_list = []
        for fix in fixtures:
            home_local = _resolve_team(fix['home_team'], current_teams or [])
            away_local = _resolve_team(fix['away_team'], current_teams or [])

            if not (home_local and away_local and current_predictor):
                continue

            try:
                result = None
                if prediction_cache:
                    result = prediction_cache.get(home_local, away_local)
                if result is None:
                    result = current_predictor.predict_with_full_bayesian_analysis(home_local, away_local)
                    if prediction_cache:
                        prediction_cache.set(home_local, away_local, result)

                predictions_raw = convert_numpy_types(result.get('predictions', {}))
                probabilities_raw = convert_numpy_types(result.get('probabilities', {}))
                poisson_analysis = convert_numpy_types(result.get('poisson_analysis', {}))
                match_insights = convert_numpy_types(result.get('match_insights', {}))

                # Format outcome probabilities as percentages
                outcome_probs = {}
                if 'Match Outcome' in probabilities_raw and isinstance(probabilities_raw['Match Outcome'], dict):
                    for k, v in probabilities_raw['Match Outcome'].items():
                        try:
                            outcome_probs[k] = f"{float(v)*100:.0f}%"
                        except Exception:
                            outcome_probs[k] = str(v)
                    probabilities_raw['Match Outcome'] = outcome_probs

                # Derive confidence level from model confidence if available
                confidence = result.get('confidence', 0)
                confidence_level = 'HIGH' if confidence >= 0.65 else ('MEDIUM' if confidence >= 0.45 else 'LOW')

                live_predictions_list.append({
                    'home_team': home_local,
                    'away_team': away_local,
                    'api_home': fix['home_team'],
                    'api_away': fix['away_team'],
                    'competition': fix['competition'],
                    'kick_off': fix['utc_date'][11:16],
                    'predictions': predictions_raw,
                    'probabilities': probabilities_raw,
                    'poisson_scorelines': poisson_analysis,
                    'match_insights': match_insights,
                    'confidence_level': confidence_level,
                    'logical_valid': True,
                    'draw_risk': result.get('draw_risk', False),
                    'draw_probability': result.get('draw_probability', 0),
                })
            except Exception as e:
                print(f"[Live Predictions] Prediction failed for {home_local} vs {away_local}: {e}")
                continue

        return jsonify({
            'status': 'success',
            'predictions': live_predictions_list,
            'total_fixtures': len(fixtures),
            'predicted': len(live_predictions_list),
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
        print(f"[Error] GW1 analysis error: {e}")
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
        print(f"[Error] Weekly insights API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/system-status')
def api_system_status():
    """System status API"""
    return jsonify({
        'status': 'operational' if predictor else 'error',
        'teams_loaded': len(teams),
        'predictor_ready': predictor is not None,
        'gw1_analyzer_ready': gw1_analyzer is not None,
        'weekly_analyzer_ready': weekly_analyzer is not None
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
        print(f"[Error] Prediction API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """Save prediction functionality with persistence"""
    try:
        data = request.get_json()
        
        # Define storage path
        storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions_history.json')
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Load existing history
        history = []
        if os.path.exists(storage_path):
            try:
                import json
                with open(storage_path, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                print(f"[Warning] Could not load history: {e}")

        # Generate unique ID
        new_id = 1
        if history:
            new_id = max(item.get('id', 0) for item in history) + 1

        prediction_record = {
            'id': new_id,
            'home_team': data.get('home_team'),
            'away_team': data.get('away_team'),
            'predictions': data.get('predictions', {}),
            'probabilities': data.get('probabilities', {}),
            'confidence_intervals': data.get('confidence_intervals', {}),
            'poisson_analysis': data.get('poisson_analysis', {}),
            'advanced_stats': data.get('advanced_stats', {}), # Include Phase 3 stats
            'date_saved': datetime.utcnow().isoformat(),
            'match_date': data.get('match_date', datetime.now().strftime('%Y-%m-%d')),
            'status': 'Pending', # Pending, Correct, Incorrect
            'result_verified': False,
            'actual_score': None
        }
        
        history.append(prediction_record)
        
        # Save back to file
        import json
        with open(storage_path, 'w') as f:
            json.dump(history, f, indent=4)

        print(f"[OK] Prediction saved to disk: {prediction_record['home_team']} vs {prediction_record['away_team']}")

        return jsonify({
            'status': 'success',
            'message': 'Prediction saved successfully',
            'prediction_id': prediction_record['id']
        })

    except Exception as e:
        print(f"[Error] Save error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@routes.route('/accuracy')
def accuracy_dashboard():
    """Render accuracy dashboard"""
    return render_template('accuracy.html')

@routes.route('/api/get-history')
def get_prediction_history():
    """Get all saved predictions"""
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions_history.json')
    if not os.path.exists(storage_path):
        return jsonify([])
    
    try:
        import json
        with open(storage_path, 'r') as f:
            history = json.load(f)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes.route('/api/prediction/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    """Delete a specific prediction"""
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions_history.json')
    if not os.path.exists(storage_path):
        return jsonify({'status': 'error', 'message': 'No history found'}), 404
        
    try:
        import json
        with open(storage_path, 'r') as f:
            history = json.load(f)
            
        # Filter out the item to delete
        new_history = [item for item in history if item.get('id') != prediction_id]
        
        if len(new_history) == len(history):
            return jsonify({'status': 'error', 'message': 'Prediction not found'}), 404
            
        with open(storage_path, 'w') as f:
            json.dump(new_history, f, indent=4)
            
        return jsonify({'status': 'success', 'message': f'Prediction {prediction_id} deleted'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@routes.route('/api/history', methods=['DELETE'])
def clear_history():
    """Clear all prediction history"""
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions_history.json')
    
    try:
        import json
        # Write empty list
        with open(storage_path, 'w') as f:
            json.dump([], f, indent=4)
            
        return jsonify({'status': 'success', 'message': 'History cleared'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@routes.route('/api/verify-predictions', methods=['POST'])
def verify_predictions():
    """Check pending predictions against actual results"""
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions_history.json')
    if not os.path.exists(storage_path):
        return jsonify({'status': 'error', 'message': 'No history found'})
    
    try:
        import json
        with open(storage_path, 'r') as f:
            history = json.load(f)
        
        updated_count = 0
        service = get_live_scores_service()
        
        for record in history:
            if record.get('status') == 'Pending':
                # Attempt to verify
                home_team = record['home_team']
                
                # 1. Get Team ID (Try Home, then Away)
                team_id = service.search_team(record['home_team'])
                if not team_id:
                    # Try away team
                    team_id = service.search_team(record['away_team'])
                    
                if not team_id:
                    print(f"[Verify] Could not find ID for matching: {record['home_team']} vs {record['away_team']}")
                    continue
                    
                # 2. Get Recent Matches (FINISHED)
                matches_finished = service.get_team_matches(team_id, limit=5, status='FINISHED')
                
                # Also get Scheduled to checking if it's just not played yet? 
                # For verification, we strictly look for FINISHED matches matching the date.
                
                # 3. Find matching game
                target_date = record['match_date'] # YYYY-MM-DD
                found_match = None
                
                for m in matches_finished:
                    # Date parsing with tolerance
                    try:
                        match_dt = datetime.fromisoformat(m['date'].replace('Z', '+00:00'))
                        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
                        # Make target_dt offset-aware (assuming UTC for simplicity or naive comparison)
                        # Best to compare dates only
                        match_date_str = match_dt.strftime('%Y-%m-%d')
                        
                        # Check strict match OR +/- 1 day
                        delta = abs((match_dt.date() - target_dt.date()).days)
                        if delta <= 1:
                            found_match = m
                            break
                    except Exception as e:
                        # Fallback to string match
                        if m['date'].startswith(target_date):
                            found_match = m
                            break
                
                if found_match and found_match['status'] == 'FINISHED':
                    score = found_match['score']['fullTime']
                    home_score = score['home']
                    away_score = score['away']
                    
                    record['actual_score'] = f"{home_score}-{away_score}"
                    record['result_verified'] = True
                    
                    # Determine Result
                    if home_score > away_score:
                        result = "Home Win"
                    elif away_score > home_score:
                        result = "Away Win"
                    else:
                        result = "Draw"
                    
                    # Check against prediction
                    predicted_outcome = record['predictions'].get('Match Outcome')
                    if predicted_outcome:
                        # Normalize string comparison
                        if "Home Win" in predicted_outcome and result == "Home Win":
                            record['status'] = 'Correct'
                        elif "Away Win" in predicted_outcome and result == "Away Win":
                            record['status'] = 'Correct'
                        elif "Draw" in predicted_outcome and result == "Draw":
                            record['status'] = 'Correct'
                        else:
                            record['status'] = 'Incorrect'
                    
                    # Check Exact Score
                    predicted_cs = None
                    if record.get('poisson_analysis') and record['poisson_analysis'].get('most_likely_scorelines'):
                        predicted_cs = record['poisson_analysis']['most_likely_scorelines'][0]['score'] # e.g. "2-1"
                    
                    if predicted_cs == f"{home_score}-{away_score}":
                        record['exact_score_correct'] = True
                    else:
                        record['exact_score_correct'] = False
                        
                    updated_count += 1
        
        # Save updates
        if updated_count > 0:
            with open(storage_path, 'w') as f:
                json.dump(history, f, indent=4)
                
        return jsonify({
            'status': 'success', 
            'message': f'Verified {updated_count} predictions',
            'updated_count': updated_count
        })

    except Exception as e:
        print(f"[Error] Verify error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/live-scores', methods=['GET'])
def live_scores():
    """
    Fetch live scores using enhanced live scores service
    """
    try:
        if not live_scores_service:
            return jsonify({
                'status': 'error',
                'message': 'Live scores service not available',
                'timestamp': datetime.utcnow().isoformat()
            }), 500

        # Get live matches
        matches = live_scores_service.get_live_matches()

        return jsonify({
            'status': 'success',
            'matches': matches,
            'count': len(matches),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"[Error] Live scores error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@routes.route('/api/upcoming-matches', methods=['GET'])
def upcoming_matches():
    """Get upcoming matches"""
    try:
        if not live_scores_service:
            return jsonify({'status': 'error', 'message': 'Service not available'}), 500
        
        days = request.args.get('days', 7, type=int)
        competition = request.args.get('competition', None)
        
        matches = live_scores_service.get_upcoming_matches(competition, days)
        
        return jsonify({
            'status': 'success',
            'matches': matches,
            'count': len(matches),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/api/cache-stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    try:
        if not prediction_cache:
            return jsonify({'status': 'error', 'message': 'Cache not available'}), 500
        
        stats = prediction_cache.get_stats()
        
        return jsonify({
            'status': 'success',
            'cache_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes.route('/statistics', methods=['GET', 'POST'])
def statistics():
    """Match statistics dashboard"""
    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')
        
        if not home_team or not away_team:
            return render_template('statistics.html', teams=teams, error="Please select both teams")
        
        if not predictor:
            return render_template('statistics.html', teams=teams, error="System not available")
        
        try:
            # Import statistics generator
            from app.match_statistics import get_statistics_generator
            
            stats_gen = get_statistics_generator(predictor.df)
            stats = stats_gen.generate_full_statistics(home_team, away_team)
            
            # Add Advanced Stats (Discipline & Corners)
            advanced_stats = None
            if discipline_analyzer:
                try:
                    advanced_stats = discipline_analyzer.project_match_stats(home_team, away_team)
                except Exception as e:
                    print(f"[Warning] Statistics advanced stats failed: {e}")

            return render_template('statistics.html',
                                 teams=teams,
                                 stats=stats,
                                 home_team=home_team,
                                 away_team=away_team,
                                 advanced_stats=advanced_stats)
        
        except Exception as e:
            print(f"[Error] Statistics error: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('statistics.html', teams=teams,
                                 error=f"Statistics generation failed: {str(e)}")
    
    return render_template('statistics.html', teams=teams, stats=None)


@routes.route('/api/betting-tips', methods=['POST'])
def api_betting_tips():
    """API endpoint for betting tips"""
    try:
        data = request.get_json()
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        
        if not home_team or not away_team or not predictor:
            return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
        
        # Get prediction
        result = predictor.predict_with_full_bayesian_analysis(home_team, away_team)
        
        # Generate betting tips
        tips_gen = get_betting_tips_generator()
        tips = tips_gen.generate_tips(
            result.get('predictions', {}),
            result.get('probabilities', {}),
            home_team,
            away_team
        )
        
        formatted_tips = tips_gen.format_tips_for_display(tips)
        
        return jsonify({
            'status': 'success',
            'tips': formatted_tips,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
