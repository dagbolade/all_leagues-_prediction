# main.py

import pandas as pd
from pathlib import Path
from footy.load_data import load_season_data, load_and_merge_seasons
from footy.data_cleaning import clean_betting_columns, explore_dataset
from footy.feature_engineering import FootballFeatureEngineering
from footy.model_training import FootballPredictor
from footy.predictor_utils import MatchPredictor
from footy.epl_analyzer import run_epl_analysis
from footy.rolling_features import RollingFeatureGenerator


def main():
    # 1. Set up paths
    data_dir = Path("data/raw")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    season_paths = {
        "2024-2025": data_dir / "all-euro-data-2024-2025.xlsx",
        "2023-2024": data_dir / "all-euro-data-2023-2024.xlsx"
    }

    try:
        # 2. Load and merge data
        print("Loading data...")
        data, sheets = load_season_data(season_paths)
        merged_df = load_and_merge_seasons(data["2024-2025"], data["2023-2024"])

        # 3. Clean data
        print("\nCleaning data...")
        merged_df_cleaned = clean_betting_columns(merged_df)
        dataset_info = explore_dataset(merged_df_cleaned)

        # 4. Feature engineering with all features
        print("\nStarting feature engineering...")

        # First encode teams
        feature_engineering = FootballFeatureEngineering()
        df_encoded = feature_engineering.encode_teams(merged_df_cleaned)

        # Then add rolling features (these create the features the model expects)
        print("\nAdding rolling features...")
        rolling_generator = RollingFeatureGenerator()
        df_with_rolling = rolling_generator.add_rolling_features(df_encoded)

        # Then do the rest of feature engineering
        print("\nCompleting feature engineering...")
        df_engineered = feature_engineering.engineer_features(df_with_rolling)

        # 5. Train models with enhanced predictions
        print("\nTraining prediction models...")
        predictor = FootballPredictor()
        predictor.train_models(df_engineered)

        # Save trained models
        predictor.save_models(models_dir / "football_models.joblib")

        # 6. Run EPL analysis
        print("\nAnalyzing EPL statistics...")
        team_stats, percentage_stats, fig = run_epl_analysis(df_engineered)
        fig.show()

        # 7. Set up match predictor
        match_predictor = MatchPredictor(df_engineered, predictor.models)

        # 8. Make predictions for upcoming matches
        print("\nPredicting upcoming matches...")
        upcoming_matches = [
            ('Fulham', 'Southampton'),
            ('Leicester', 'Wolves'),
            ('Man United', 'Bournemouth'),
            ('Everton', 'Chelsea'),
            ('Tottenham', 'Liverpool'),
            ('Real Madrid', 'Sevilla')
        ]

        match_predictor.predict_matches(upcoming_matches)

        # 9. Save processed data
        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True)

        print("\nSaving processed data...")
        df_engineered.to_pickle(output_dir / "processed_data.pkl")

        print("\nProcess completed successfully!")
        return {
            'data': df_engineered,
            'predictor': predictor,
            'match_predictor': match_predictor,
            'team_stats': team_stats,
            'percentage_stats': percentage_stats
        }

    except Exception as e:
        print(f"\nError in main process: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()