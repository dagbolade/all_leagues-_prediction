
# footy/incremental_features.py

import pandas as pd
import numpy as np
from pathlib import Path
import os
import joblib
from datetime import datetime

# Import existing feature generators
from footy.rolling_features import BayesianRollingFeatureGenerator
from footy.feature_engineering import BayesianFootballFeatureEngineering
from footy.load_data import load_season_data_any, load_and_merge_multi
from footy.data_cleaning import clean_betting_columns

def update_features_incrementally(
    raw_data_dir="data/raw",
    features_path="data/processed/enhanced_bayesian_features.csv",
    history_window=50
):
    """
    Update feature file incrementally by processing only new matches.
    
    Args:
        raw_data_dir: Directory containing raw season Excel files
        features_path: Path to the existing CSV with engineered features
        history_window: Number of past matches per team to keep for rolling stats calculation
    """
    print(f"\n🔄 STARTING INCREMENTAL FEATURE UPDATE")
    print("=" * 60)
    
    # 1. Load Existing Features (The Master Cache)
    if not os.path.exists(features_path):
        print(f"⚠️ Features file not found at {features_path}. Running FULL process...")
        # Fallback to main.py logic or raise error
        return False
        
    print(f"📂 Loading existing features from {features_path}...")
    existing_df = pd.read_csv(features_path, low_memory=False)
    existing_df['Date'] = pd.to_datetime(existing_df['Date'])
    print(f"   Matches in cache: {len(existing_df):,} (Up to {existing_df['Date'].max().date()})")
    
    # 2. Load Raw Data (The Source)
    print(f"📂 Scanning raw data in {raw_data_dir}...")
    files = sorted(Path(raw_data_dir).glob("all-euro-data-*.xlsx"))
    season_paths = {f.name: f for f in files}
    
    # Check specifically for the current/latest season file
    # We assume '2024-2025' or similar is the latest.
    # Just load ALL raw data? It takes a few seconds to load Excel, but we only need latest.
    # Optimization: Loading 5 years of Excel is slow (~30s). 
    # We can assume updates only happen in the CHANGED files (latest season).
    # But for safety, let's load all to ensure we don't miss anything, 
    # unless we want to be super fast. 
    # Let's load ONLY the file with the latest modification time + the current season file?
    # For now, load all - 30s is fine compared to 2 hours of training.
    
    data_by_season, _ = load_season_data_any(season_paths)
    raw_df = load_and_merge_multi(data_by_season)
    raw_df['Date'] = pd.to_datetime(raw_df['Date'])
    raw_df = clean_betting_columns(raw_df)
    
    print(f"   Total raw matches: {len(raw_df):,} (Up to {raw_df['Date'].max().date()})")
    
    # 3. Identify New Matches
    # Identify by Date + HomeTeam + AwayTeam
    # Create a unique ID for comparison
    def create_match_id(df):
        return df['Date'].astype(str) + "_" + df['HomeTeam'] + "_" + df['AwayTeam']
        
    existing_ids = set(create_match_id(existing_df))
    raw_df['match_id'] = create_match_id(raw_df)
    
    new_matches_mask = ~raw_df['match_id'].isin(existing_ids)
    new_matches = raw_df[new_matches_mask].copy()
    
    if len(new_matches) == 0:
        print("✅ No new matches found. Features are up to date.")
        return True
        
    print(f"🆕 Found {len(new_matches)} NEW matches to process.")
    print(f"   Dates: {new_matches['Date'].min().date()} to {new_matches['Date'].max().date()}")
    
    # 4. Create Calculation Window
    # We need history to calculate rolling features for these new matches.
    # Taking the last N matches for every team involved in new matches?
    # Simpler: unique teams in new_matches
    teams_involved = set(new_matches['HomeTeam'].unique()) | set(new_matches['AwayTeam'].unique())
    
    print(f"   Loading history for {len(teams_involved)} teams...")
    
    # Filter existing_df for these teams and take last 50 matches each
    history_dfs = []
    
    # This loop might be slow if existing_df is huge.
    # Optimization: sort by date, group by team (Home/Away logic is tricky).
    # Easier: Just take the last 5000 matches from existing_df?
    # 50 matches * 20 teams = 1000 matches. 
    # 50 matches * 500 teams = 25000.
    # Let's just take the last 30% of the dataframe or last 1 year.
    
    one_year_ago = new_matches['Date'].min() - pd.Timedelta(days=365)
    history_window_df = existing_df[existing_df['Date'] > one_year_ago].copy()
    
    # We typically only need raw columns for feature engineering input
    # But feature engineering might expect certain columns.
    # existing_df has ENGINEERED columns. 
    # If we pass engineered columns to `add_rolling_features`, does it break?
    # `add_rolling_features` takes `merged_df_cleaned` (raw).
    
    # So we need RAW data for history. 
    # existing_df has raw columns? Yes.
    # But it also has `BayesianRolling...` columns.
    # Does `add_rolling_features` overwrite or crash if columns exist?
    # It usually calculates generic rolling features.
    
    # Safest: Use `raw_df` for history as well!
    # We already loaded `raw_df`.
    # So `window_df` should be built from `raw_df`, NOT `existing_df`.
    
    # Get match_ids of new matches
    new_match_ids = set(new_matches['match_id'])
    
    # Get indices of new matches in raw_df
    # We want rows that are EITHER new OR within the history window (relative to new matches)
    # But simpler: Just use raw_df directly?
    # If we run feature engineering on the WHOLE raw_df, it takes time (years of data).
    # We want to run it on (History + New).
    
    # Select History Matches: matches in raw_df that are NOT new, but recent.
    # Latest date in existing_df?
    last_processed_date = existing_df['Date'].max()
    
    # Get data from (last_processed_date - 365 days) up to (last_processed_date)
    # Plus the new matches.
    
    start_history_date = new_matches['Date'].min() - pd.Timedelta(days=365)
    
    # Filter raw_df
    processing_window = raw_df[raw_df['Date'] >= start_history_date].copy()
    
    print(f"   Processing window: {len(processing_window)} matches (History + New)")
    
    # 5. Run Feature Engineering on Window
    print("⚙️ Running incremental feature engineering...")
    
    # Step A: Rolling Features
    bayesian_rolling = BayesianRollingFeatureGenerator()
    df_window_rolling = bayesian_rolling.add_rolling_features(processing_window)
    
    # Step B: Feature Engineering
    bayesian_engine = BayesianFootballFeatureEngineering()
    df_window_engineered = bayesian_engine.engineer_features(df_window_rolling)
    
    # 6. Extract Computed Features for New Matches ONLY
    # Re-calculate match_id for the engineered window
    df_window_engineered['match_id'] = create_match_id(df_window_engineered)
    
    # Filter for the new matches we identified earlier
    df_new_engineered = df_window_engineered[df_window_engineered['match_id'].isin(new_match_ids)].copy()
    
    print(f"   Extracted {len(df_new_engineered)} new engineered records")
    
    # Drop temp match_id column
    df_new_engineered = df_new_engineered.drop(columns=['match_id'])
    
    # 7. Append and Save
    # Align columns (ensure order matches existing)
    common_cols = [c for c in existing_df.columns if c in df_new_engineered.columns]
    
    # If new columns were added (unlikely), they will be ignored.
    # If columns match, append.
    
    final_df = pd.concat([existing_df, df_new_engineered[common_cols]], ignore_index=True)
    
    # Remove duplicates just in case (based on match_id logic equivalent)
    # De-duplicate by Date, HomeTeam, AwayTeam
    final_df = final_df.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'], keep='last')
    
    print(f"💾 Saving updated features to {features_path}...")
    final_df.to_csv(features_path, index=False)
    
    print(f"✅ Success! Total matches: {len(final_df):,}")
    return True

if __name__ == "__main__":
    update_features_incrementally()
