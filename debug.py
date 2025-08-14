import pandas as pd

from footy.predictor_utils import BayesianMatchPredictor

# Load your enhanced training data
df = pd.read_csv('data/processed/enhanced_bayesian_features.csv')  # Or whatever your file is called
# Create predictor (use local models or any dummy path)
predictor = BayesianMatchPredictor(df, 'models/football_models.joblib')

# Test feature extraction
features = predictor._get_bayesian_team_features('Mallorca', 'Barcelona')

# Check key features
print("🔍 Feature extraction test:")
print(f"HomeElo: {features.get('HomeElo', [0]).iloc[0]}")
print(f"AwayElo: {features.get('AwayElo', [0]).iloc[0]}")
print(f"EloAdvantage: {features.get('EloAdvantage', [0]).iloc[0]}")