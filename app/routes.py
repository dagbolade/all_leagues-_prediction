# app/routes.py - UPDATED VERSION WITH CACHING AND LIVE SCORES

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
prediction_cache = None
live_scores_service = None
discipline_analyzer = None


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
    """Generate insights using ONLY actual data - no generic bullshit"""

    insights = []

    try:
        # 1. DETECT CURRENT GAMEWEEK FROM ACTUAL DATA
        if weekly_analyzer:
            current_gw = weekly_analyzer.detect_current_gameweek()
            insights.append(f"[GW] Gameweek {current_gw}")
    except:
        pass

    try:
        # 2. GET LATEST ACTUAL MATCH RESULTS (whatever season format exists)
        # Find what seasons actually exist in the data
        available_seasons = predictor_df['Season'].unique()
        latest_season = sorted(available_seasons)[-1]  # Most recent season

        # Get latest season matches
        latest_season_matches = predictor_df[
            predictor_df['Season'] == latest_season
            ].sort_values('Date')

        if len(latest_season_matches) > 0:
            # Get HOME TEAM's latest match from current season
            home_latest_season = latest_season_matches[
                (latest_season_matches['HomeTeam'] == home_team) |
                (latest_season_matches['AwayTeam'] == home_team)
                ].tail(1)

            if len(home_latest_season) > 0:
                match = home_latest_season.iloc[0]
                date = match['Date'].strftime('%b %d') if hasattr(match['Date'], 'strftime') else str(match['Date'])

                if match['HomeTeam'] == home_team:
                    score = f"{match['FTHG']}-{match['FTAG']}"
                    opponent = match['AwayTeam']
                    venue = "H"
                    result_emoji = "[W]" if match['FTR'] == 'H' else "[D]" if match['FTR'] == 'D' else "[L]"
                else:
                    score = f"{match['FTAG']}-{match['FTHG']}"
                    opponent = match['HomeTeam']
                    venue = "A"
                    result_emoji = "[W]" if match['FTR'] == 'A' else "[D]" if match['FTR'] == 'D' else "[L]"

                insights.append(f"[Latest] {home_team} latest: {result_emoji} {score} vs {opponent} ({venue}) - {date}")

            # Get AWAY TEAM's latest match from current season
            away_latest_season = latest_season_matches[
                (latest_season_matches['HomeTeam'] == away_team) |
                (latest_season_matches['AwayTeam'] == away_team)
                ].tail(1)

            if len(away_latest_season) > 0:
                match = away_latest_season.iloc[0]
                date = match['Date'].strftime('%b %d') if hasattr(match['Date'], 'strftime') else str(match['Date'])

                if match['HomeTeam'] == away_team:
                    score = f"{match['FTHG']}-{match['FTAG']}"
                    opponent = match['AwayTeam']
                    venue = "H"
                    result_emoji = "[W]" if match['FTR'] == 'H' else "[D]" if match['FTR'] == 'D' else "[L]"
                else:
                    score = f"{match['FTAG']}-{match['FTHG']}"
                    opponent = match['HomeTeam']
                    venue = "A"
                    result_emoji = "[W]" if match['FTR'] == 'A' else "[D]" if match['FTR'] == 'D' else "[L]"

                insights.append(f"[Away] {away_team} latest: {result_emoji} {score} vs {opponent} ({venue}) - {date}")

    except Exception as e:
        print(f"Latest season results error: {e}")

    try:
        # 3. HOME TEAM RECENT FORM (last 6 matches across all time)
        home_recent = predictor_df[
            (predictor_df['HomeTeam'] == home_team) | (predictor_df['AwayTeam'] == home_team)
            ].sort_values('Date', ascending=False).head(6)

        if len(home_recent) > 0:
            form_letters = []
            wins = draws = losses = 0
            goals_for = goals_against = 0
            clean_sheets = 0

            for _, match in home_recent.iterrows():
                if match['HomeTeam'] == home_team:
                    gf, ga = match['FTHG'], match['FTAG']
                    result = match['FTR']
                    if result == 'H':
                        form_letters.append('W')
                        wins += 1
                    elif result == 'D':
                        form_letters.append('D')
                        draws += 1
                    else:
                        form_letters.append('L')
                        losses += 1
                else:
                    gf, ga = match['FTAG'], match['FTHG']
                    result = match['FTR']
                    if result == 'A':
                        form_letters.append('W')
                        wins += 1
                    elif result == 'D':
                        form_letters.append('D')
                        draws += 1
                    else:
                        form_letters.append('L')
                        losses += 1

                goals_for += gf
                goals_against += ga
                if ga == 0:
                    clean_sheets += 1

            avg_goals_for = goals_for / len(home_recent)
            avg_goals_against = goals_against / len(home_recent)

            insights.append(
                f"[Form] {home_team} last {len(home_recent)}: {''.join(form_letters)} ({wins}W-{draws}D-{losses}L)")
            insights.append(f"[Goals] {home_team} scoring: {avg_goals_for:.1f} per game, conceding {avg_goals_against:.1f}")

            if clean_sheets > 0:
                insights.append(f"[Clean] {home_team}: {clean_sheets}/{len(home_recent)} clean sheets")

    except Exception as e:
        print(f"Home team form error: {e}")

    try:
        # 4. AWAY TEAM RECENT FORM (last 6 matches across all time)
        away_recent = predictor_df[
            (predictor_df['HomeTeam'] == away_team) | (predictor_df['AwayTeam'] == away_team)
            ].sort_values('Date', ascending=False).head(6)

        if len(away_recent) > 0:
            form_letters = []
            wins = draws = losses = 0
            goals_for = goals_against = 0
            clean_sheets = 0

            for _, match in away_recent.iterrows():
                if match['HomeTeam'] == away_team:
                    gf, ga = match['FTHG'], match['FTAG']
                    result = match['FTR']
                    if result == 'H':
                        form_letters.append('W')
                        wins += 1
                    elif result == 'D':
                        form_letters.append('D')
                        draws += 1
                    else:
                        form_letters.append('L')
                        losses += 1
                else:
                    gf, ga = match['FTAG'], match['FTHG']
                    result = match['FTR']
                    if result == 'A':
                        form_letters.append('W')
                        wins += 1
                    elif result == 'D':
                        form_letters.append('D')
                        draws += 1
                    else:
                        form_letters.append('L')
                        losses += 1

                goals_for += gf
                goals_against += ga
                if ga == 0:
                    clean_sheets += 1

            avg_goals_for = goals_for / len(away_recent)
            avg_goals_against = goals_against / len(away_recent)

            insights.append(
                f"[Form] {away_team} last {len(away_recent)}: {''.join(form_letters)} ({wins}W-{draws}D-{losses}L)")
            insights.append(f"[Goals] {away_team} scoring: {avg_goals_for:.1f} per game, conceding {avg_goals_against:.1f}")

            if clean_sheets > 0:
                insights.append(f"[Clean] {away_team}: {clean_sheets}/{len(away_recent)} clean sheets")

    except Exception as e:
        print(f"Away team form error: {e}")

    try:
        # 5. HEAD-TO-HEAD ANALYSIS (BOTH TEAMS)
        h2h_matches = predictor_df[
            ((predictor_df['HomeTeam'] == home_team) & (predictor_df['AwayTeam'] == away_team)) |
            ((predictor_df['HomeTeam'] == away_team) & (predictor_df['AwayTeam'] == home_team))
            ].sort_values('Date', ascending=False).head(10)

        if len(h2h_matches) > 0:
            home_wins = len(h2h_matches[
                                ((h2h_matches['HomeTeam'] == home_team) & (h2h_matches['FTR'] == 'H')) |
                                ((h2h_matches['AwayTeam'] == home_team) & (h2h_matches['FTR'] == 'A'))
                                ])
            draws = len(h2h_matches[h2h_matches['FTR'] == 'D'])
            away_wins = len(h2h_matches) - home_wins - draws

            # Goal analysis
            total_goals = (h2h_matches['FTHG'] + h2h_matches['FTAG']).sum()
            avg_goals = total_goals / len(h2h_matches)
            over_25_count = len(h2h_matches[(h2h_matches['FTHG'] + h2h_matches['FTAG']) > 2.5])
            btts_count = len(h2h_matches[(h2h_matches['FTHG'] > 0) & (h2h_matches['FTAG'] > 0)])

            insights.append(
                f"[H2H] Last {len(h2h_matches)} H2H: {home_team} {home_wins}W-{draws}D-{away_wins}L vs {away_team}")
            insights.append(f"[Stats] H2H averages: {avg_goals:.1f} goals per game")

            if len(h2h_matches) >= 5:
                insights.append(
                    f"[Target] Over 2.5 Goals in {over_25_count}/{len(h2h_matches)} recent H2H ({(over_25_count / len(h2h_matches) * 100):.0f}%)")
                insights.append(
                    f"[Goals] Both teams scored in {btts_count}/{len(h2h_matches)} recent H2H ({(btts_count / len(h2h_matches) * 100):.0f}%)")

    except Exception as e:
        print(f"H2H analysis error: {e}")

    try:
        # 6. VENUE-SPECIFIC PERFORMANCE (HOME TEAM at home, AWAY TEAM away)
        home_at_home = predictor_df[predictor_df['HomeTeam'] == home_team].sort_values('Date').tail(10)
        if len(home_at_home) >= 5:
            home_wins = len(home_at_home[home_at_home['FTR'] == 'H'])
            home_goals_for = home_at_home['FTHG'].sum()
            home_goals_against = home_at_home['FTAG'].sum()

            insights.append(
                f"[Home] {home_team} at home: {home_wins}/{len(home_at_home)} wins ({(home_wins / len(home_at_home) * 100):.0f}%)")
            insights.append(
                f"[Home] {home_team} home scoring: {(home_goals_for / len(home_at_home)):.1f} for, {(home_goals_against / len(home_at_home)):.1f} against")

        away_away = predictor_df[predictor_df['AwayTeam'] == away_team].sort_values('Date').tail(10)
        if len(away_away) >= 5:
            away_wins = len(away_away[away_away['FTR'] == 'A'])
            away_goals_for = away_away['FTAG'].sum()
            away_goals_against = away_away['FTHG'].sum()

            insights.append(
                f"[Away] {away_team} away: {away_wins}/{len(away_away)} wins ({(away_wins / len(away_away) * 100):.0f}%)")
            insights.append(
                f"[Away] {away_team} away scoring: {(away_goals_for / len(away_away)):.1f} for, {(away_goals_against / len(away_away)):.1f} against")

    except Exception as e:
        print(f"Venue analysis error: {e}")

    return insights


def initialize_predictor():
    """Initialize prediction system with caching and live scores"""
    global predictor, teams, prediction_cache, live_scores_service
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try to load fast models first (from weekly updates)
        fast_models_path = os.path.join(base_dir, '..', 'models', 'fast_football_models.joblib')
        original_models_path = os.path.join(base_dir, '..', 'models', 'football_models.joblib')
        
        # [FIX] Temporarily disable fast models due to XGBoost version mismatch on server
        # if os.path.exists(fast_models_path):
        #     models_path = fast_models_path
        #     print(f"[Init] Loading OPTIMIZED fast models from {models_path}")
        # else:
        models_path = original_models_path
        print(f"[Init] Loading standard models from {models_path}")

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

        # Create predictor
        predictor = create_bayesian_predictor(df, models_path)
        if predictor is None:
            print("[Error] Failed to create predictor")
            return None, []

        # Extract teams
        teams = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))

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
                
                # Add cache status
                if cache_hit:
                    match_insights.insert(0, "[⚡] Instant prediction from cache")

            except Exception as e:
                print(f"[Warning] Comprehensive insights error: {e}")
                match_insights = [f"[Goals] Basic prediction for {home_team} vs {away_team}"]

            # Format insights for display
            enhanced_insights = {
                'key_insights': match_insights[:10]  # Show top 10 insights
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
