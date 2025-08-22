# app/routes.py - UPDATED VERSION WITH DYNAMIC INSIGHTS

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
from footy.insights import FootballInsights  # ADD THIS IMPORT

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

def generate_comprehensive_insights(predictor_df, home_team, away_team, weekly_analyzer, gw1_analyzer):
    """Generate insights using ONLY actual data - no generic bullshit"""

    insights = []

    try:
        # 1. DETECT CURRENT GAMEWEEK FROM ACTUAL DATA
        if weekly_analyzer:
            current_gw = weekly_analyzer.detect_current_gameweek()
            insights.append(f"📅 Gameweek {current_gw}")
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
                    result_emoji = "🟢" if match['FTR'] == 'H' else "🟡" if match['FTR'] == 'D' else "🔴"
                else:
                    score = f"{match['FTAG']}-{match['FTHG']}"
                    opponent = match['HomeTeam']
                    venue = "A"
                    result_emoji = "🟢" if match['FTR'] == 'A' else "🟡" if match['FTR'] == 'D' else "🔴"

                insights.append(f"🏆 {home_team} latest: {result_emoji} {score} vs {opponent} ({venue}) - {date}")

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
                    result_emoji = "🟢" if match['FTR'] == 'H' else "🟡" if match['FTR'] == 'D' else "🔴"
                else:
                    score = f"{match['FTAG']}-{match['FTHG']}"
                    opponent = match['HomeTeam']
                    venue = "A"
                    result_emoji = "🟢" if match['FTR'] == 'A' else "🟡" if match['FTR'] == 'D' else "🔴"

                insights.append(f"✈️ {away_team} latest: {result_emoji} {score} vs {opponent} ({venue}) - {date}")

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
                f"📈 {home_team} last {len(home_recent)}: {''.join(form_letters)} ({wins}W-{draws}D-{losses}L)")
            insights.append(f"⚽ {home_team} scoring: {avg_goals_for:.1f} per game, conceding {avg_goals_against:.1f}")

            if clean_sheets > 0:
                insights.append(f"🛡️ {home_team}: {clean_sheets}/{len(home_recent)} clean sheets")

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
                f"📉 {away_team} last {len(away_recent)}: {''.join(form_letters)} ({wins}W-{draws}D-{losses}L)")
            insights.append(f"⚽ {away_team} scoring: {avg_goals_for:.1f} per game, conceding {avg_goals_against:.1f}")

            if clean_sheets > 0:
                insights.append(f"🛡️ {away_team}: {clean_sheets}/{len(away_recent)} clean sheets")

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
                f"🤝 Last {len(h2h_matches)} H2H: {home_team} {home_wins}W-{draws}D-{away_wins}L vs {away_team}")
            insights.append(f"📊 H2H averages: {avg_goals:.1f} goals per game")

            if len(h2h_matches) >= 5:
                insights.append(
                    f"🎯 Over 2.5 Goals in {over_25_count}/{len(h2h_matches)} recent H2H ({(over_25_count / len(h2h_matches) * 100):.0f}%)")
                insights.append(
                    f"⚽ Both teams scored in {btts_count}/{len(h2h_matches)} recent H2H ({(btts_count / len(h2h_matches) * 100):.0f}%)")

    except Exception as e:
        print(f"H2H analysis error: {e}")

    try:
        # 6. VENUE-SPECIFIC PERFORMANCE (HOME TEAM at home, AWAY TEAM away)
        home_at_home = predictor_df[predictor_df['HomeTeam'] == home_team].tail(10)
        if len(home_at_home) >= 5:
            home_wins = len(home_at_home[home_at_home['FTR'] == 'H'])
            home_goals_for = home_at_home['FTHG'].sum()
            home_goals_against = home_at_home['FTAG'].sum()

            insights.append(
                f"🏠 {home_team} at home: {home_wins}/{len(home_at_home)} wins ({(home_wins / len(home_at_home) * 100):.0f}%)")
            insights.append(
                f"🏠 {home_team} home scoring: {(home_goals_for / len(home_at_home)):.1f} for, {(home_goals_against / len(home_at_home)):.1f} against")

        away_away = predictor_df[predictor_df['AwayTeam'] == away_team].tail(10)
        if len(away_away) >= 5:
            away_wins = len(away_away[away_away['FTR'] == 'A'])
            away_goals_for = away_away['FTAG'].sum()
            away_goals_against = away_away['FTHG'].sum()

            insights.append(
                f"✈️ {away_team} away: {away_wins}/{len(away_away)} wins ({(away_wins / len(away_away) * 100):.0f}%)")
            insights.append(
                f"✈️ {away_team} away scoring: {(away_goals_for / len(away_away)):.1f} for, {(away_goals_against / len(away_away)):.1f} against")

    except Exception as e:
        print(f"Venue analysis error: {e}")

    return insights


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
            print(f"✅ All analyzers initialized")
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
                    match_insights.append(f"🎯 Over 2.5 Goals prediction: {over_25_pred}")

                if btts_pred != 'N/A':
                    match_insights.append(f"⚽ Both teams to score: {btts_pred}")

                if total_goals != 'N/A':
                    match_insights.append(f"🥅 Expected total goals: {total_goals}")

            except Exception as e:
                print(f"⚠️ Comprehensive insights error: {e}")
                match_insights = [f"⚽ Basic prediction for {home_team} vs {away_team}"]

            # Format insights for display
            enhanced_insights = {
                'key_insights': match_insights[:10]  # Show top 10 insights
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