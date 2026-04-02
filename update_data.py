#!/usr/bin/env python3
"""
INCREMENTAL DATA UPDATE - Fast weekly updates without full retraining

This script:
1. Loads existing processed features
2. Adds ONLY new matches from latest 2025/2026 data
3. Updates rolling features for affected teams
4. Saves updated dataset
5. Optionally fine-tunes models (or skips if not needed)

USAGE:
    python update_data.py                    # Quick update (no retraining)
    python update_data.py --retrain          # Update + retrain models
    python update_data.py --file path.xlsx   # Specify new data file

SPEED: ~30 seconds vs 10+ minutes for full training
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime
import sys

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from footy.data_cleaning import clean_betting_columns
from footy.load_data import load_season_data_any, load_and_merge_multi
from footy.rolling_features import BayesianRollingFeatureGenerator
from footy.feature_engineering import BayesianFootballFeatureEngineering


class IncrementalDataUpdater:
    """Fast incremental updates for new match data"""

    def __init__(self, existing_data_path='data/processed/enhanced_bayesian_features.csv.zip'):
        self.existing_data_path = existing_data_path
        self.output_dir = Path('data/processed')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_existing_data(self):
        """Load existing processed features"""
        print(f"\n📊 Loading existing data from {self.existing_data_path}")

        if not Path(self.existing_data_path).exists():
            print("❌ No existing data found. Run main.py first for full training.")
            return None

        df = pd.read_csv(self.existing_data_path, low_memory=False)
        df['Date'] = pd.to_datetime(df['Date'])
        print(f"✅ Loaded {len(df)} existing matches")
        print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")

        return df

    def load_new_matches(self, new_data_file=None):
        """Load only NEW matches from latest file"""
        print(f"\n📥 Loading new match data...")

        if new_data_file is None:
            # Auto-detect latest file
            raw_files = list(Path('data/raw').glob('all-euro-data-*.xlsx'))
            if not raw_files:
                print("❌ No data files found in data/raw/")
                return None
            new_data_file = sorted(raw_files)[-1]  # Most recent

        print(f"   Source: {new_data_file}")

        # Extract season name from filename (e.g. all-euro-data-2025-2026.xlsx -> 2025-2026)
        fname = Path(new_data_file).stem  # e.g. all-euro-data-2025-2026
        parts = fname.split('-')
        season = f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else "2025-2026"

        # Load and clean using correct functions
        season_paths = {season: str(new_data_file)}
        data_by_season, _ = load_season_data_any(season_paths)
        new_df = load_and_merge_multi(data_by_season)
        new_df = clean_betting_columns(new_df)
        new_df['Date'] = pd.to_datetime(new_df['Date'])

        print(f"✅ Loaded {len(new_df)} total matches from file")
        print(f"   Date range: {new_df['Date'].min()} to {new_df['Date'].max()}")

        return new_df

    def find_new_matches(self, existing_df, new_df):
        """Find matches that are NEW (not in existing data)"""
        print(f"\n🔍 Identifying new matches...")

        # Create unique match ID
        def create_match_id(df):
            return (df['Date'].dt.strftime('%Y-%m-%d') + '_' +
                   df['HomeTeam'] + '_' + df['AwayTeam'])

        existing_ids = set(create_match_id(existing_df))
        new_df['match_id'] = create_match_id(new_df)

        # Filter to only NEW matches
        new_matches = new_df[~new_df['match_id'].isin(existing_ids)].copy()
        new_matches = new_matches.drop('match_id', axis=1)

        print(f"✅ Found {len(new_matches)} NEW matches")

        if len(new_matches) > 0:
            print(f"   Newest match: {new_matches['Date'].max()}")
            print(f"   Leagues: {new_matches['League'].nunique()} leagues")
            print(f"   Teams involved: {len(set(new_matches['HomeTeam']) | set(new_matches['AwayTeam']))} teams")
        else:
            print("ℹ️  No new matches found. Data is already up to date!")

        return new_matches

    def merge_and_update_features(self, existing_df, new_matches):
        """Merge new matches and update features incrementally"""
        print(f"\n🔧 Updating features...")

        # Combine datasets
        combined_df = pd.concat([existing_df, new_matches], ignore_index=True)
        combined_df = combined_df.sort_values('Date').reset_index(drop=True)

        print(f"✅ Combined dataset: {len(combined_df)} total matches")

        # --- NEW: EXPECTED GOALS (xG) INTEGRATION ---
        # Backfill or fetch latest xG if it's missing or largely NaN
        if 'Home_xG' not in combined_df.columns or combined_df['Home_xG'].isna().mean() > 0.3:
            print("\n🌍 Fetching Expected Goals (xG) data from Understat for the dataset...")
            try:
                from footy.xg_scraper import ExpectedGoalsScraper
                scraper = ExpectedGoalsScraper()
                combined_df = scraper.merge_xg_to_matches(combined_df)
                print(f"✅ Successfully integrated Expected Goals mapping!")
            except Exception as e:
                print(f"⚠️ Could not fetch xG data: {e}")
                if 'Home_xG' not in combined_df.columns:
                    combined_df['Home_xG'] = float('nan')
                    combined_df['Away_xG'] = float('nan')
        # --------------------------------------------

        # Get list of affected teams (teams with new matches)
        affected_teams = set(new_matches['HomeTeam']) | set(new_matches['AwayTeam'])
        print(f"   Affected teams: {len(affected_teams)} teams need feature updates")

        # OPTIMIZATION: Only recalculate rolling features for affected teams
        # For teams NOT in new matches, keep existing features
        print(f"\n🧠 Updating Bayesian rolling features (incremental)...")

        # Option 1: Full recalc (slower but accurate) - ~2-3 min
        # Option 2: Incremental update (faster) - ~30 sec
        # For simplicity, we'll do full recalc on combined data (still faster than full retrain)

        rolling_generator = BayesianRollingFeatureGenerator()
        df_with_rolling = rolling_generator.add_rolling_features(combined_df)

        print(f"\n🎯 Updating advanced Bayesian features...")
        feature_engineer = BayesianFootballFeatureEngineering()
        df_fully_engineered = feature_engineer.engineer_features(df_with_rolling)

        print(f"✅ Feature engineering complete!")
        print(f"   Total features: {len(df_fully_engineered.columns)}")

        return df_fully_engineered

    def save_updated_data(self, df):
        """Save updated dataset"""
        print(f"\n💾 Saving updated data...")

        # Save as ZIP (for deployment)
        csv_zip_path = self.output_dir / 'enhanced_bayesian_features.csv.zip'
        df.to_csv(csv_zip_path, index=False, compression='zip')
        print(f"✅ Saved to {csv_zip_path}")
        print(f"   Size: {csv_zip_path.stat().st_size / 1024 / 1024:.2f} MB")

        # Also save as regular CSV (for local use)
        csv_path = self.output_dir / 'enhanced_bayesian_features.csv'
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved to {csv_path}")

        # Save metadata
        metadata = {
            'last_update': datetime.now().isoformat(),
            'total_matches': len(df),
            'latest_match_date': df['Date'].max().isoformat(),
            'total_features': len(df.columns),
            'leagues': df['League'].nunique()
        }

        import json
        metadata_path = self.output_dir / 'data_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Metadata saved to {metadata_path}")

    def run(self, new_data_file=None, retrain_models=False):
        """Run incremental update"""
        print("="*80)
        print("🚀 INCREMENTAL DATA UPDATE - Fast Weekly Updates")
        print("="*80)

        # Step 1: Load existing data
        existing_df = self.load_existing_data()
        if existing_df is None:
            return False

        # Step 2: Load new matches
        new_df = self.load_new_matches(new_data_file)
        if new_df is None:
            return False

        # Step 3: Find what's NEW
        new_matches = self.find_new_matches(existing_df, new_df)

        if len(new_matches) == 0:
            print("\n✅ Data is already up to date. BUT forcing xG backfill update...")
            # return True

        # Step 4: Merge and update features
        updated_df = self.merge_and_update_features(existing_df, new_matches)

        # Step 5: Save
        self.save_updated_data(updated_df)

        # Step 6: Optionally retrain models
        if retrain_models:
            print("\n🤖 Retraining models...")
            print("   (This will take 5-10 minutes)")
            # Import and run model training
            from footy.model_training import BayesianFootballPredictor
            predictor = BayesianFootballPredictor()
            models, metrics = predictor.train_models(updated_df)

            # Save models
            import joblib
            models_path = Path('models/football_models.joblib')
            joblib.dump(models, models_path)
            print(f"✅ Models retrained and saved to {models_path}")
        else:
            print("\n⏭️  Skipping model retraining (use --retrain to retrain)")
            print("   Existing models will work fine with updated data!")

        print("\n" + "="*80)
        print("✅ INCREMENTAL UPDATE COMPLETE!")
        print("="*80)
        print(f"📊 Added {len(new_matches)} new matches")
        print(f"📊 Total dataset: {len(updated_df)} matches")
        print(f"⚡ Time saved vs full retrain: ~90%")
        print("="*80)

        return True


def main():
    parser = argparse.ArgumentParser(description='Incremental data update (fast)')
    parser.add_argument('--file', type=str, help='Path to new data file (auto-detect if not provided)')
    parser.add_argument('--retrain', action='store_true', help='Retrain models after update')
    parser.add_argument('--existing', type=str, default='data/processed/enhanced_bayesian_features.csv.zip',
                       help='Path to existing processed data')

    args = parser.parse_args()

    updater = IncrementalDataUpdater(existing_data_path=args.existing)
    success = updater.run(new_data_file=args.file, retrain_models=args.retrain)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
