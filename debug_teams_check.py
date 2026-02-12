
import os
import sys
import pandas as pd
import joblib

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app.routes import initialize_predictor
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

print("\n--- Running initialize_predictor() ---")
predictor, teams = initialize_predictor()

print(f"\n--- Result ---")
print(f"Predictor object: {type(predictor)}")
print(f"Teams count: {len(teams)}")
if len(teams) > 0:
    print(f"First 10 teams: {teams[:10]}")
else:
    print("WARNING: No teams found!")

print("\n--- Checking Data File ---")
base_dir = os.path.dirname(os.path.abspath('app/routes.py'))
data_path = os.path.join(base_dir, '..', 'data', 'processed', 'enhanced_bayesian_features.csv')
if os.path.exists(data_path):
    print(f"Data file exists at: {data_path}")
    try:
        df = pd.read_csv(data_path, nrows=100)
        print(f"Columns: {df.columns.tolist()[:10]}...")
        if 'HomeTeam' in df.columns:
            print(f"Unique HomeTeams in first 100 rows: {df['HomeTeam'].unique()}")
    except Exception as e:
        print(f"Error reading data file: {e}")
else:
    print(f"Data file NOT found at: {data_path}")
