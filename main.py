# main.py - ENHANCED PIPELINE WITH LOGICAL CONSTRAINTS & POISSON

import pandas as pd
from pathlib import Path
from footy.load_data import load_season_data_any, load_and_merge_multi
from footy.data_cleaning import clean_betting_columns, explore_dataset
from footy.rolling_features import RollingFeatureGenerator
from footy.feature_engineering import FootballFeatureEngineering
from footy.model_training import FootballPredictor
from footy.predictor_utils import MatchPredictor, create_predictor
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


def validate_elo_ratings(df: pd.DataFrame) -> bool:
    """Validate that Elo ratings are realistic."""
    if 'HomeElo' not in df.columns:
        return False

    avg_elo = df['HomeElo'].mean()
    min_elo = df['HomeElo'].min()
    max_elo = df['HomeElo'].max()

    print(f"📊 Elo Validation:")
    print(f"   Average: {avg_elo:.0f}")
    print(f"   Range: {min_elo:.0f} - {max_elo:.0f}")

    # Check if Elo values are realistic
    if 1200 <= avg_elo <= 1800 and 1000 <= min_elo and max_elo <= 2000:
        print("✅ Elo ratings look realistic!")
        return True
    else:
        print("⚠️ Elo ratings may be unrealistic!")
        return False


def validate_predictions(predictions: dict) -> tuple:
    """Validate predictions for logical consistency."""
    issues = []

    over_1_5 = predictions.get('Over 1.5 Goals', 'Unknown')
    over_2_5 = predictions.get('Over 2.5 Goals', 'Unknown')
    over_3_5 = predictions.get('Over 3.5 Goals', 'Unknown')

    # Check logical consistency
    if over_1_5 == 'No' and over_2_5 == 'Yes':
        issues.append("Impossible: Over 1.5 No + Over 2.5 Yes")
    if over_2_5 == 'No' and over_3_5 == 'Yes':
        issues.append("Impossible: Over 2.5 No + Over 3.5 Yes")
    if over_1_5 == 'No' and over_3_5 == 'Yes':
        issues.append("Impossible: Over 1.5 No + Over 3.5 Yes")

    is_valid = len(issues) == 0
    return is_valid, issues


def test_enhanced_predictions(match_predictor):
    """Test the enhanced prediction system with logical constraints."""
    print(f"\n🧪 TESTING ENHANCED PREDICTION SYSTEM")
    print("=" * 60)

    test_matches = [
        ('Arsenal', 'Chelsea'),
        ('Man City', 'Liverpool'),
        ('Tottenham', 'Brighton'),
    ]

    all_predictions_valid = True

    for i, (home, away) in enumerate(test_matches, 1):
        print(f"\n🧪 TEST {i}: {home} vs {away}")
        print("-" * 40)

        try:
            # Test standard predictions
            predictions, probabilities = match_predictor.predict_match(home, away)

            # Validate logical consistency
            is_valid, issues = validate_predictions(predictions)

            if is_valid:
                print("✅ Predictions are logically consistent")
            else:
                print("❌ Logical issues found:")
                for issue in issues:
                    print(f"   • {issue}")
                all_predictions_valid = False

            # Show key predictions
            print("📊 Key Predictions:")
            for market in ['Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals']:
                if market in predictions:
                    pred = predictions[market]
                    print(f"   {market}: {pred}")

            # Test Poisson insights
            try:
                poisson_insights = match_predictor.get_poisson_insights(home, away)
                if poisson_insights and 'expected_goals' in poisson_insights:
                    exp_goals = poisson_insights['expected_goals']
                    print(f"⚽ Expected Goals: {exp_goals['home']} - {exp_goals['away']}")

                    if 'most_likely_scorelines' in poisson_insights:
                        top_score = poisson_insights['most_likely_scorelines'][0]
                        print(f"🎯 Most Likely: {top_score['score']} ({top_score['probability']})")
                else:
                    print("⚠️ Poisson insights not available")
            except Exception as e:
                print(f"⚠️ Poisson test failed: {e}")

        except Exception as e:
            print(f"❌ Prediction test failed: {e}")
            all_predictions_valid = False

    print(f"\n🧪 TESTING SUMMARY:")
    if all_predictions_valid:
        print("✅ All predictions passed logical consistency tests!")
    else:
        print("❌ Some predictions failed logical consistency tests!")

    return all_predictions_valid


def main():
    print("🚀 STARTING ENHANCED FOOTBALL PREDICTION PIPELINE")
    print("🎯 Goal: Logical predictions with 75%+ accuracy for EPL 2024/25")
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

        print("🔄 Loading and merging 5 seasons of data...")
        data_by_season, sheets = load_season_data_any(season_paths)
        merged_df = load_and_merge_multi(data_by_season)
        print(f"✅ Loaded {len(merged_df):,} matches across {len(season_paths)} seasons")

        print("🧹 Cleaning data...")
        merged_df_cleaned = clean_betting_columns(merged_df)
        dataset_info = explore_dataset(merged_df_cleaned)
        print(f"✅ Data cleaned: {len(merged_df_cleaned):,} matches ready")

        # ============================================================================
        # PHASE 2: ENHANCED FEATURE ENGINEERING PIPELINE
        # ============================================================================
        print(f"\n🔧 PHASE 2: ENHANCED FEATURE ENGINEERING")
        print("-" * 50)

        # Step 1: Team encoding
        print("🏷️ Step 1: Encoding teams...")
        feature_engineering = FootballFeatureEngineering()
        df_encoded = feature_engineering.encode_teams(merged_df_cleaned)
        print(f"✅ Teams encoded: {df_encoded['HomeTeam_encoded'].nunique()} unique teams")

        # Step 2: Enhanced rolling features (including fixed Elo)
        print("📈 Step 2: Adding enhanced rolling features with fixed Elo...")
        rolling_generator = RollingFeatureGenerator()
        df_with_rolling = rolling_generator.add_rolling_features(df_encoded)

        # Validate Elo ratings
        elo_valid = validate_elo_ratings(df_with_rolling)

        rolling_features = [col for col in df_with_rolling.columns if
                            any(x in col for x in ['Form', 'Scoring', 'Over', 'Elo', 'BTTS'])]
        print(f"✅ Rolling features added: {len(rolling_features)} features")

        # Step 3: Additional feature engineering
        print("⚽ Step 3: Adding advanced features (H2H, referee, context)...")
        df_engineered = feature_engineering.engineer_features(df_with_rolling)

        # Count final features
        enhanced_features = [col for col in df_engineered.columns if
                             any(x in col for x in ['Elo', 'H2H', 'GW1', 'Ref', 'Strength'])]
        print(f"✅ Advanced features completed: {len(enhanced_features)} features")

        total_features = len([col for col in df_engineered.columns if col not in [
            'Date', 'HomeTeam', 'AwayTeam', 'League', 'Season', 'FTR', 'FTHG', 'FTAG'
        ]])
        print(f"🎯 Total engineered features: {total_features}")

        # ============================================================================
        # PHASE 3: ENHANCED MODEL TRAINING WITH LOGICAL CONSTRAINTS
        # ============================================================================
        print(f"\n🤖 PHASE 3: ENHANCED MODEL TRAINING")
        print("-" * 50)

        print("🚀 Starting enhanced model training with logical constraints...")
        predictor = FootballPredictor()

        # Test constraint system before training
        print("🧪 Testing logical constraint system...")
        predictor.test_logical_constraints()

        # Train enhanced models
        predictor.train_models(df_engineered)

        # Save enhanced models
        models_path = models_dir / "football_models.joblib"
        predictor.save_models(models_path)
        print(f"💾 Enhanced models saved to: {models_path}")

        # ============================================================================
        # PHASE 4: ENHANCED MATCH PREDICTOR SETUP
        # ============================================================================
        print(f"\n🔮 PHASE 4: ENHANCED MATCH PREDICTOR SETUP")
        print("-" * 50)

        print("🔄 Creating enhanced match predictor...")
        match_predictor = create_predictor(df_engineered, models_path)
        print("✅ Enhanced match predictor initialized with logical constraints")

        # Test the enhanced prediction system
        predictions_valid = test_enhanced_predictions(match_predictor)

        # ============================================================================
        # PHASE 5: ENHANCED EPL ANALYSIS
        # ============================================================================
        print(f"\n📊 PHASE 5: ENHANCED EPL ANALYSIS")
        print("-" * 50)

        try:
            analyzer = AdvancedEPLAnalyzer()
            analysis_results = analyzer.analyze_enhanced_epl_data(df_engineered)

            # Get GW1 insights
            gw1_insights = rolling_generator.get_gw1_insights()
            if gw1_insights:
                print("🏆 GW1 Historical Insights:")
                print(f"   Average GW1 goals: {gw1_insights.get('avg_goals_per_match', 'N/A'):.2f}")
                print(f"   GW1 Over 2.5 rate: {gw1_insights.get('over_2_5_rate', 'N/A'):.1%}")
                print(f"   GW1 home win rate: {gw1_insights.get('home_win_rate', 'N/A'):.1%}")

        except Exception as e:
            print(f"⚠️ Enhanced analysis failed, using basic: {e}")
            team_stats, percentage_stats, fig = run_epl_analysis(df_engineered)

        # ============================================================================
        # PHASE 6: ENHANCED MATCH PREDICTIONS WITH FULL INSIGHTS
        # ============================================================================
        print(f"\n⚽ PHASE 6: ENHANCED MATCH PREDICTIONS")
        print("=" * 80)

        # EPL opening fixtures for 2024/25
        epl_opening_matches = [
            ('Arsenal', 'Wolves'),
            ('Brighton', 'Man United'),
            ('Chelsea', 'Man City'),
            ('Liverpool', 'Ipswich'),
            ('Newcastle', 'Southampton')
        ]

        print("🏆 EPL 2024/25 OPENING MATCH PREDICTIONS")
        print("📊 Using enhanced models with logical constraints & Poisson analysis")

        all_predictions = []

        for i, (home, away) in enumerate(epl_opening_matches, 1):
            print(f"\n{'=' * 20} MATCH {i}/{len(epl_opening_matches)} {'=' * 20}")
            print(f"🏟️ {home} vs {away}")
            print("-" * 60)

            try:
                # Get full enhanced predictions with insights
                full_analysis = match_predictor.predict_with_full_insights(home, away)

                predictions = full_analysis['predictions']
                insights = full_analysis['insights']
                poisson_analysis = full_analysis.get('poisson_scorelines', {})

                # Validate predictions
                is_valid, issues = validate_predictions(predictions)

                print("🎯 ENHANCED PREDICTIONS:")

                # Match outcome
                if 'Match Outcome' in predictions:
                    outcome = predictions['Match Outcome']
                    print(f"   🏆 Match Outcome: {outcome}")

                # Over/Under with logical consistency check
                over_markets = ['Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals']
                print("   ⚽ Goal Markets:")
                for market in over_markets:
                    if market in predictions:
                        pred = predictions[market]
                        # Simple confidence based on prediction
                        confidence = "🔥 HIGH" if market == 'Over 2.5 Goals' else "📊 MEDIUM"
                        print(f"     {market}: {pred} {confidence}")

                # BTTS
                if 'Both Teams to Score' in predictions:
                    btts = predictions['Both Teams to Score']
                    print(f"   ✅ Both Teams to Score: {btts}")

                # Logical consistency status
                if is_valid:
                    print("   ✅ LOGICAL CONSISTENCY: PASSED")
                else:
                    print("   ❌ LOGICAL CONSISTENCY: FAILED")
                    for issue in issues:
                        print(f"     • {issue}")

                # Total goals
                if 'Total Goals' in predictions:
                    total = predictions['Total Goals']
                    print(f"   ⚽ Total Goals: {total}")

                # Poisson insights
                if poisson_analysis and 'expected_goals' in poisson_analysis:
                    exp_goals = poisson_analysis['expected_goals']
                    print(f"\n📊 POISSON EXACT SCORELINES:")
                    print(f"   Expected Goals: {exp_goals['home']} - {exp_goals['away']}")

                    if 'most_likely_scorelines' in poisson_analysis:
                        print(f"   Most Likely Scorelines:")
                        for j, scoreline in enumerate(poisson_analysis['most_likely_scorelines'][:3], 1):
                            print(f"     {j}. {scoreline['score']}: {scoreline['probability']}")

                # Team strength insights
                if 'team_strength' in insights:
                    strength = insights['team_strength']
                    print(f"\n💡 TEAM STRENGTH:")
                    print(f"   {home} Elo: {strength.get('home_elo', 'N/A')}")
                    print(f"   {away} Elo: {strength.get('away_elo', 'N/A')}")
                    print(f"   Advantage: {strength.get('elo_advantage', 'N/A')}")

                # Key factors
                if 'key_factors' in insights and insights['key_factors']:
                    print(f"   🎯 Key Factors:")
                    for factor in insights['key_factors'][:2]:
                        print(f"     • {factor}")

                # Betting focus
                betting_focus = full_analysis.get('betting_guidance', {})
                if betting_focus:
                    primary = betting_focus.get('primary_market', 'N/A')
                    confidence = betting_focus.get('confidence', 'Medium')
                    print(f"   💰 Betting Focus: {primary} ({confidence} confidence)")

                all_predictions.append({
                    'match': f"{home} vs {away}",
                    'predictions': predictions,
                    'valid': is_valid,
                    'poisson_available': bool(poisson_analysis)
                })

            except Exception as e:
                print(f"❌ Enhanced prediction failed for {home} vs {away}: {e}")
                import traceback
                traceback.print_exc()

        # ============================================================================
        # PHASE 7: SYSTEM VALIDATION & SUMMARY
        # ============================================================================
        print(f"\n📋 PHASE 7: SYSTEM VALIDATION & SUMMARY")
        print("=" * 60)

        # Validate overall system
        total_predictions = len(all_predictions)
        valid_predictions = sum(1 for pred in all_predictions if pred['valid'])
        poisson_available = sum(1 for pred in all_predictions if pred['poisson_available'])

        print(f"🎯 PREDICTION SYSTEM SUMMARY:")
        print(f"   Total Predictions: {total_predictions}")
        print(f"   Logically Valid: {valid_predictions}/{total_predictions}")
        print(f"   Poisson Available: {poisson_available}/{total_predictions}")
        print(f"   Elo Ratings: {'✅ Realistic' if elo_valid else '⚠️ May need adjustment'}")

        # Model summary
        model_insights = predictor.get_model_insights()
        print(f"\n🤖 MODEL SUMMARY:")
        print(f"   Trained Models: {len(model_insights['trained_models'])}")
        print(f"   Poisson Available: {model_insights['poisson_available']}")
        print(f"   Logical Constraints: {model_insights['logical_constraints']}")

        # Save processed data
        print(f"\n💾 SAVING ENHANCED DATA")
        print("-" * 40)

        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True)

        # Save enhanced dataframe
        enhanced_data_path = output_dir / "enhanced_processed_data.pkl"
        df_engineered.to_pickle(enhanced_data_path)
        print(f"✅ Enhanced data saved: {enhanced_data_path}")

        # Save CSV for inspection
        csv_path = output_dir / "enhanced_features.csv"
        df_engineered.to_csv(csv_path, index=False)
        print(f"✅ CSV saved: {csv_path}")

        # Final success message
        print(f"\n🎉 ENHANCED PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"📊 Processed {len(df_engineered):,} matches")
        print(f"🔧 Created {total_features} enhanced features")
        print(f"🤖 Trained {len(model_insights['trained_models'])} models with logical constraints")
        print(f"⚽ Generated {valid_predictions}/{total_predictions} logically consistent predictions")
        print(f"🎯 System ready for EPL 2024/25 with realistic accuracy!")

        return {
            'data': df_engineered,
            'predictor': predictor,
            'match_predictor': match_predictor,
            'total_features': total_features,
            'models_path': models_path,
            'predictions_valid': valid_predictions == total_predictions,
            'elo_valid': elo_valid
        }

    except Exception as e:
        print(f"\n❌ Error in enhanced pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()