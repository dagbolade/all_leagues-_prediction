# main.py - ENHANCED BAYESIAN PIPELINE

import pandas as pd
from pathlib import Path
from footy.load_data import load_season_data_any, load_and_merge_multi
from footy.data_cleaning import clean_betting_columns, explore_dataset

# ENHANCED IMPORTS - Using your Bayesian classes
from footy.rolling_features import BayesianRollingFeatureGenerator
from footy.feature_engineering import BayesianFootballFeatureEngineering
from footy.model_training import BayesianFootballPredictor
from footy.predictor_utils import create_bayesian_predictor

from footy.epl_analyzer import run_epl_analysis, AdvancedEPLAnalyzer
import re
import warnings

warnings.filterwarnings('ignore')

# Suppress specific warnings
import pandas as pd

pd.options.mode.chained_assignment = None

import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def _season_from_fname(p: Path) -> str:
    m = re.search(r"(\d{4}-\d{4})", p.name)
    return m.group(1) if m else "unknown"


def validate_bayesian_elo_ratings(df: pd.DataFrame) -> bool:
    """Validate that Bayesian Elo ratings are realistic."""
    if 'HomeElo' not in df.columns:
        return False

    avg_elo = df['HomeElo'].mean()
    min_elo = df['HomeElo'].min()
    max_elo = df['HomeElo'].max()

    print(f"🧠 Bayesian Elo Validation:")
    print(f"   Average: {avg_elo:.0f}")
    print(f"   Range: {min_elo:.0f} - {max_elo:.0f}")

    # Check if Bayesian Elo values are realistic
    if 1200 <= avg_elo <= 1800 and 1000 <= min_elo and max_elo <= 2000:
        print("✅ Bayesian Elo ratings look realistic!")
        return True
    else:
        print("⚠️ Bayesian Elo ratings may need adjustment!")
        return False


def validate_bayesian_predictions(predictions: dict) -> tuple:
    """Validate Bayesian predictions for logical consistency."""
    issues = []

    over_1_5 = predictions.get('Over 1.5 Goals', 'Unknown')
    over_2_5 = predictions.get('Over 2.5 Goals', 'Unknown')
    over_3_5 = predictions.get('Over 3.5 Goals', 'Unknown')

    # Check Bayesian logical consistency
    if over_1_5 == 'No' and over_2_5 == 'Yes':
        issues.append("Bayesian Logic Error: Over 1.5 No + Over 2.5 Yes")
    if over_2_5 == 'No' and over_3_5 == 'Yes':
        issues.append("Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes")
    if over_1_5 == 'No' and over_3_5 == 'Yes':
        issues.append("Bayesian Logic Error: Over 1.5 No + Over 3.5 Yes")

    is_valid = len(issues) == 0
    return is_valid, issues


def test_enhanced_bayesian_predictions(match_predictor):
    """Test the enhanced Bayesian prediction system."""
    print(f"\n🧠 TESTING ENHANCED BAYESIAN PREDICTION SYSTEM")
    print("=" * 60)

    test_matches = [
        ('Arsenal', 'Chelsea'),
        ('Man City', 'Liverpool'),
        ('Tottenham', 'Brighton'),
        ('Newcastle', 'West Ham'),
        ('Wolves', 'Fulham')
    ]

    all_predictions_valid = True

    for i, (home, away) in enumerate(test_matches, 1):
        print(f"\n🧠 BAYESIAN TEST {i}: {home} vs {away}")
        print("-" * 40)

        try:
            # Test Bayesian predictions with full analysis
            bayesian_result = match_predictor.predict_with_full_bayesian_analysis(home, away)

            predictions = bayesian_result['predictions']
            probabilities = bayesian_result['probabilities']
            confidence_intervals = bayesian_result['confidence_intervals']

            # Validate Bayesian logical consistency
            is_valid, issues = validate_bayesian_predictions(predictions)

            if is_valid:
                print("✅ Bayesian predictions are logically consistent")
            else:
                print("❌ Bayesian logical issues found:")
                for issue in issues:
                    print(f"   • {issue}")
                all_predictions_valid = False

            # Show key Bayesian predictions
            print("🧠 Key Bayesian Predictions:")
            for market in ['Match Outcome', 'Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals']:
                if market in predictions:
                    pred = predictions[market]

                    # Get confidence if available
                    confidence = "N/A"
                    if market in confidence_intervals:
                        confidence = confidence_intervals[market].get('confidence_level', 'N/A')

                    print(f"   {market}: {pred} (Confidence: {confidence})")

            # Show Bayesian probability details for match outcome
            if 'Match Outcome' in probabilities and isinstance(probabilities['Match Outcome'], dict):
                print(f"   Match Outcome Probabilities:")
                for outcome, prob in probabilities['Match Outcome'].items():
                    print(f"     {outcome}: {prob}")

            # Test Poisson insights
            poisson_insights = bayesian_result.get('poisson_analysis', {})
            if poisson_insights and 'expected_goals' in poisson_insights:
                exp_goals = poisson_insights['expected_goals']
                print(f"⚽ Bayesian Expected Goals: {exp_goals['home']} - {exp_goals['away']}")

                if 'most_likely_scorelines' in poisson_insights:
                    top_score = poisson_insights['most_likely_scorelines'][0]
                    print(f"🎯 Most Likely Score: {top_score['score']} ({top_score['probability']})")
            else:
                print("⚠️ Poisson insights not available")

            # Show model info
            model_info = bayesian_result.get('model_info', {})
            if model_info:
                models_used = model_info.get('models_used', [])
                print(f"🤖 Models Used: {', '.join(models_used)}")

        except Exception as e:
            print(f"❌ Bayesian prediction test failed: {e}")
            import traceback
            traceback.print_exc()
            all_predictions_valid = False

    print(f"\n🧠 BAYESIAN TESTING SUMMARY:")
    if all_predictions_valid:
        print("✅ All Bayesian predictions passed logical consistency tests!")
    else:
        print("❌ Some Bayesian predictions failed logical consistency tests!")

    return all_predictions_valid


def main():
    print("🧠 STARTING ENHANCED BAYESIAN FOOTBALL PREDICTION PIPELINE")
    print("🎯 Goal: Realistic predictions with Bayesian inference for EPL 2024/25")
    print("=" * 80)

    data_dir = Path("data/raw")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # Auto-discover all season files
    files = sorted(data_dir.glob("all-euro-data-*.xlsx"))
    if not files:
        raise FileNotFoundError("No season files found in data/raw")

    season_paths = {_season_from_fname(f): f for f in files}
    print(f"📂 Found {len(season_paths)} season files: {list(season_paths.keys())}")

    try:
        # ============================================================================
        # PHASE 1: ENHANCED DATA LOADING & CLEANING
        # ============================================================================
        print(f"\n📊 PHASE 1: ENHANCED DATA LOADING")
        print("-" * 50)

        print("📄 Loading and merging 5 seasons of data...")
        data_by_season, sheets = load_season_data_any(season_paths)
        merged_df = load_and_merge_multi(data_by_season)
        print(f"✅ Loaded {len(merged_df):,} matches across {len(season_paths)} seasons")

        print("🧹 Cleaning data...")
        merged_df_cleaned = clean_betting_columns(merged_df)
        dataset_info = explore_dataset(merged_df_cleaned)
        print(f"✅ Data cleaned: {len(merged_df_cleaned):,} matches ready")

        # ============================================================================
        # PHASE 2: ENHANCED BAYESIAN FEATURE ENGINEERING PIPELINE
        # ============================================================================
        print(f"\n🧠 PHASE 2: ENHANCED BAYESIAN FEATURE ENGINEERING")
        print("-" * 50)

        # Step 1: Enhanced Bayesian rolling features
        print("🧠 Step 1: Adding Bayesian rolling features...")
        bayesian_rolling_generator = BayesianRollingFeatureGenerator()
        df_with_bayesian_rolling = bayesian_rolling_generator.add_rolling_features(merged_df_cleaned)

        # Validate Bayesian Elo ratings
        bayesian_elo_valid = validate_bayesian_elo_ratings(df_with_bayesian_rolling)

        bayesian_rolling_features = [col for col in df_with_bayesian_rolling.columns if
                                     any(x in col for x in
                                         ['Bayesian', 'Elo', 'Form', 'Scoring', 'Over', 'BTTS', 'Expected'])]
        print(f"✅ Bayesian rolling features added: {len(bayesian_rolling_features)} features")

        # Step 2: Enhanced Bayesian feature engineering
        print("🧠 Step 2: Adding Bayesian feature engineering...")
        bayesian_feature_engineering = BayesianFootballFeatureEngineering()
        df_bayesian_engineered = bayesian_feature_engineering.engineer_features(df_with_bayesian_rolling)

        # Count final Bayesian features
        enhanced_bayesian_features = [col for col in df_bayesian_engineered.columns if
                                      any(x in col for x in ['Bayesian', 'MatchOutcome', 'H2H', 'Ref', 'GW1'])]
        print(f"✅ Bayesian feature engineering completed: {len(enhanced_bayesian_features)} features")

        total_features = len([col for col in df_bayesian_engineered.columns if col not in [
            'Date', 'HomeTeam', 'AwayTeam', 'League', 'Season', 'FTR', 'FTHG', 'FTAG'
        ]])
        print(f"🧠 Total Bayesian engineered features: {total_features}")

        # ============================================================================
        # PHASE 3: ENHANCED BAYESIAN MODEL TRAINING
        # ============================================================================
        print(f"\n🤖 PHASE 3: ENHANCED BAYESIAN MODEL TRAINING")
        print("-" * 50)

        print("🧠 Starting Bayesian model training with hyperparameter optimization...")
        bayesian_predictor = BayesianFootballPredictor()

        # Train enhanced Bayesian models
        bayesian_predictor.train_models(df_bayesian_engineered)

        # Save enhanced Bayesian models
        models_path = models_dir / "football_models.joblib"
        bayesian_predictor.save_models(models_path)
        print(f"💾 Enhanced Bayesian models saved to: {models_path}")

        # ============================================================================
        # PHASE 4: ENHANCED BAYESIAN MATCH PREDICTOR SETUP
        # ============================================================================
        print(f"\n🧠 PHASE 4: ENHANCED BAYESIAN MATCH PREDICTOR SETUP")
        print("-" * 50)

        print("🔄 Creating enhanced Bayesian match predictor...")
        bayesian_match_predictor = create_bayesian_predictor(df_bayesian_engineered, models_path)
        print("✅ Enhanced Bayesian match predictor initialized")

        # Test the enhanced Bayesian prediction system
        bayesian_predictions_valid = test_enhanced_bayesian_predictions(bayesian_match_predictor)

        # ============================================================================
        # PHASE 5: ENHANCED EPL ANALYSIS
        # ============================================================================
        print(f"\n📊 PHASE 5: ENHANCED EPL ANALYSIS")
        print("-" * 50)

        try:
            analyzer = AdvancedEPLAnalyzer()
            analysis_results = analyzer.analyze_enhanced_epl_data(df_bayesian_engineered)

            # Get Bayesian insights
            bayesian_insights = bayesian_rolling_generator.get_bayesian_team_strengths()
            if bayesian_insights:
                print("🧠 Bayesian Team Strength Insights:")
                print(f"   League priors calculated: {len(bayesian_insights.get('league_priors', {}))}")
                print(f"   Team priors calculated: {len(bayesian_insights.get('team_priors', {}))}")

        except Exception as e:
            print(f"⚠️ Enhanced analysis failed, using basic: {e}")
            team_stats, percentage_stats, fig = run_epl_analysis(df_bayesian_engineered)

        # ============================================================================
        # PHASE 6: ENHANCED BAYESIAN MATCH PREDICTIONS
        # ============================================================================
        print(f"\n⚽ PHASE 6: ENHANCED BAYESIAN MATCH PREDICTIONS")
        print("=" * 80)

        # EPL opening fixtures for 2024/25
        epl_opening_matches = [
            ('Arsenal', 'Wolves'),
            ('Brighton', 'Man United'),
            ('Chelsea', 'Man City'),
            ('Liverpool', 'Ipswich'),
            ('Newcastle', 'Southampton')
        ]

        print("🧠 EPL 2024/25 OPENING MATCH PREDICTIONS")
        print("📊 Using enhanced Bayesian models with hyperparameter optimization")

        all_bayesian_predictions = []

        for i, (home, away) in enumerate(epl_opening_matches, 1):
            print(f"\n{'=' * 20} BAYESIAN MATCH {i}/{len(epl_opening_matches)} {'=' * 20}")
            print(f"🏟️ {home} vs {away}")
            print("-" * 60)

            try:
                # Get full enhanced Bayesian predictions with analysis
                bayesian_analysis = bayesian_match_predictor.predict_with_full_bayesian_analysis(home, away)

                predictions = bayesian_analysis['predictions']
                probabilities = bayesian_analysis['probabilities']
                confidence_intervals = bayesian_analysis['confidence_intervals']
                poisson_analysis = bayesian_analysis.get('poisson_analysis', {})
                model_info = bayesian_analysis.get('model_info', {})

                # Validate Bayesian predictions
                is_valid, issues = validate_bayesian_predictions(predictions)

                print("🧠 ENHANCED BAYESIAN PREDICTIONS:")

                # Match outcome with confidence
                if 'Match Outcome' in predictions:
                    outcome = predictions['Match Outcome']
                    confidence = confidence_intervals.get('Match Outcome', {}).get('confidence_level', 'N/A')
                    print(f"   🏆 Match Outcome: {outcome} (Confidence: {confidence})")

                    # Show probabilities
                    if isinstance(probabilities.get('Match Outcome'), dict):
                        print(f"   Probabilities:")
                        for outcome_type, prob in probabilities['Match Outcome'].items():
                            print(f"     {outcome_type}: {prob}")

                # Over/Under with Bayesian logical consistency check
                over_markets = ['Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals']
                print("   ⚽ Bayesian Goal Markets:")
                for market in over_markets:
                    if market in predictions:
                        pred = predictions[market]
                        confidence = confidence_intervals.get(market, {}).get('confidence_level', 'N/A')
                        print(f"     {market}: {pred} (Confidence: {confidence})")

                # BTTS with Bayesian confidence
                if 'Both Teams to Score' in predictions:
                    btts = predictions['Both Teams to Score']
                    btts_confidence = confidence_intervals.get('Both Teams to Score', {}).get('confidence_level', 'N/A')
                    print(f"   ✅ Both Teams to Score: {btts} (Confidence: {btts_confidence})")

                # Bayesian logical consistency status
                if is_valid:
                    print("   ✅ BAYESIAN LOGICAL CONSISTENCY: PASSED")
                else:
                    print("   ❌ BAYESIAN LOGICAL CONSISTENCY: FAILED")
                    for issue in issues:
                        print(f"     • {issue}")

                # Total goals
                if 'Total Goals' in predictions:
                    total = predictions['Total Goals']
                    print(f"   ⚽ Bayesian Total Goals: {total}")

                # Poisson insights
                if poisson_analysis and 'expected_goals' in poisson_analysis:
                    exp_goals = poisson_analysis['expected_goals']
                    print(f"\n📊 BAYESIAN POISSON EXACT SCORELINES:")
                    print(f"   Expected Goals: {exp_goals['home']} - {exp_goals['away']}")

                    if 'most_likely_scorelines' in poisson_analysis:
                        print(f"   Most Likely Scorelines:")
                        for j, scoreline in enumerate(poisson_analysis['most_likely_scorelines'][:3], 1):
                            print(f"     {j}. {scoreline['score']}: {scoreline['probability']}")

                # Model information
                if model_info:
                    models_used = model_info.get('models_used', [])
                    calibrated_models = model_info.get('calibrated_models', [])
                    print(f"\n🤖 BAYESIAN MODEL INFO:")
                    print(f"   Models Used: {', '.join(models_used)}")
                    if calibrated_models:
                        print(f"   Calibrated Models: {', '.join(calibrated_models)}")

                # Bayesian priors used
                bayesian_priors = bayesian_analysis.get('bayesian_priors', {})
                if bayesian_priors:
                    print(f"   Bayesian Priors Available: {list(bayesian_priors.keys())}")

                all_bayesian_predictions.append({
                    'match': f"{home} vs {away}",
                    'predictions': predictions,
                    'valid': is_valid,
                    'bayesian_models': len(models_used),
                    'poisson_available': bool(poisson_analysis)
                })

            except Exception as e:
                print(f"❌ Enhanced Bayesian prediction failed for {home} vs {away}: {e}")
                import traceback
                traceback.print_exc()

        # ============================================================================
        # PHASE 7: BAYESIAN SYSTEM VALIDATION & SUMMARY
        # ============================================================================
        print(f"\n🧠 PHASE 7: BAYESIAN SYSTEM VALIDATION & SUMMARY")
        print("=" * 60)

        # Validate overall Bayesian system
        total_predictions = len(all_bayesian_predictions)
        valid_predictions = sum(1 for pred in all_bayesian_predictions if pred['valid'])
        poisson_available = sum(1 for pred in all_bayesian_predictions if pred['poisson_available'])

        print(f"🧠 BAYESIAN PREDICTION SYSTEM SUMMARY:")
        print(f"   Total Bayesian Predictions: {total_predictions}")
        print(f"   Logically Valid: {valid_predictions}/{total_predictions}")
        print(f"   Poisson Available: {poisson_available}/{total_predictions}")
        print(f"   Bayesian Elo Ratings: {'✅ Realistic' if bayesian_elo_valid else '⚠️ May need adjustment'}")

        # Bayesian model summary
        model_insights = bayesian_predictor.get_model_insights()
        print(f"\n🤖 BAYESIAN MODEL SUMMARY:")
        print(f"   Trained Models: {len(model_insights['trained_models'])}")
        print(f"   Calibrated Models: {len(model_insights['calibration_status'])}")
        print(f"   Poisson Available: {model_insights['poisson_available']}")
        print(f"   Bayesian Constraints: {model_insights['bayesian_constraints']}")
        print(f"   Hyperopt Trials: {model_insights['hyperopt_trials']}")

        # Save processed data
        print(f"\n💾 SAVING ENHANCED BAYESIAN DATA")
        print("-" * 40)

        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True)

        # Save enhanced Bayesian dataframe
        bayesian_data_path = output_dir / "enhanced_bayesian_data.pkl"
        df_bayesian_engineered.to_pickle(bayesian_data_path)
        print(f"✅ Enhanced Bayesian data saved: {bayesian_data_path}")

        # Save CSV for inspection
        csv_path = output_dir / "enhanced_bayesian_features.csv"
        df_bayesian_engineered.to_csv(csv_path, index=False)
        print(f"✅ Bayesian CSV saved: {csv_path}")

        # Final success message
        print(f"\n🎉 ENHANCED BAYESIAN PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"📊 Processed {len(df_bayesian_engineered):,} matches")
        print(f"🧠 Created {total_features} enhanced Bayesian features")
        print(f"🤖 Trained {len(model_insights['trained_models'])} Bayesian models with hyperopt")
        print(f"⚽ Generated {valid_predictions}/{total_predictions} logically consistent Bayesian predictions")
        print(f"🎯 System ready for EPL 2024/25 with realistic Bayesian inference!")

        return {
            'data': df_bayesian_engineered,
            'predictor': bayesian_predictor,
            'match_predictor': bayesian_match_predictor,
            'total_features': total_features,
            'models_path': models_path,
            'predictions_valid': valid_predictions == total_predictions,
            'bayesian_elo_valid': bayesian_elo_valid
        }

    except Exception as e:
        print(f"\n❌ Error in enhanced Bayesian pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()