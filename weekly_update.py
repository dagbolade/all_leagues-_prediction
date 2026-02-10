
import os
import sys
import subprocess
import argparse
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our new incremental updater and fast trainer
from footy.incremental_features import update_features_incrementally
from footy.fast_model_training import run_fast_training_pipeline

def run_scraper():
    """Run the automated football scraper."""
    print("\n🌍 STEP 1: RUNNING DATA SCRAPER")
    print("=" * 50)
    try:
        # We run this as a subprocess to ensure clean state
        subprocess.run(["python", "automated_football_scraper.py"], check=True)
        print("✅ Scraper completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Scraper failed with error code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Scraper failed: {e}")
        return False

def update_features():
    """Run incremental feature engineering."""
    print("\n⚙️ STEP 2: INCREMENTAL FEATURE UPDATE")
    print("=" * 50)
    try:
        success = update_features_incrementally()
        if success:
            print("✅ Features updated successfully")
        else:
            print("⚠️ Feature update reported failure (or no new data)")
        return success
    except Exception as e:
        print(f"❌ Feature update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def train_models():
    """Run fast model training."""
    print("\n🤖 STEP 3: FAST MODEL RETRAINING")
    print("=" * 50)
    try:
        run_fast_training_pipeline()
        print("✅ Models retrained successfully")
        return True
    except Exception as e:
        print(f"❌ Model training failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Weekly Football Prediction Update Script")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip the scraping step")
    parser.add_argument("--skip-features", action="store_true", help="Skip the feature update step")
    parser.add_argument("--skip-train", action="store_true", help="Skip the training step")
    
    args = parser.parse_args()
    
    start_time = time.time()
    print(f"🚀 STARTING WEEKLY UPDATE PIPELINE at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Scrape
    if not args.skip_scrape:
        if not run_scraper():
            print("⛔ Pipeline stopped due to scraper failure.")
            return
    else:
        print("\n⏩ Skipping Scraper (User requested)")
        
    # Step 2: Update Features
    if not args.skip_features:
        if not update_features():
            # If features failed, we might still want to train if data exists?
            # But usually we define failure as "something broke", not "no new data".
            # update_features_incrementally returns True if no new data.
            # So if it returns False, it really broke.
            print("⛔ Pipeline stopped due to feature update failure.")
            return
    else:
        print("\n⏩ Skipping Feature Update (User requested)")
        
    # Step 3: Train
    if not args.skip_train:
        if not train_models():
            print("⛔ Pipeline stopped due to training failure.")
            return
    else:
        print("\n⏩ Skipping Training (User requested)")
        
    duration = time.time() - start_time
    print(f"\n✨ WEEKLY UPDATE COMPLETED in {duration/60:.1f} minutes!")
    print(f"📅 Next update recommended: Next Tuesday morning.")

if __name__ == "__main__":
    main()
