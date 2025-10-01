# bayesian_football_pipeline.py
"""
Bayesian Football Prediction Pipeline
A beginner-friendly implementation following ML best practices
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Step 1: Data Collection
class DataCollector:
    """Handles data loading and initial validation"""
    
    def __init__(self, data_dir="data/raw"):
        self.data_dir = Path(data_dir)
        
    def load_season_data(self):
        """Load multiple seasons of football data"""
        print("📊 STEP 1: LOADING DATA")
        print("-" * 40)
        
        # Find all data files
        files = list(self.data_dir.glob("*.xlsx"))
        if not files:
            raise FileNotFoundError(f"No data files found in {self.data_dir}")
            
        print(f"Found {len(files)} data files")
        
        # Load each season
        seasons_data = {}
        for file_path in files:
            season_name = self._extract_season_name(file_path)
            try:
                df = pd.read_excel(file_path)
                seasons_data[season_name] = df
                print(f"✅ Loaded {season_name}: {len(df)} matches")
            except Exception as e:
                print(f"❌ Failed to load {file_path}: {e}")
                
        return seasons_data
    
    def _extract_season_name(self, file_path):
        """Extract season name from filename"""
        import re
        match = re.search(r"(\d{4}-\d{4})", file_path.name)
        return match.group(1) if match else "Unknown_Season"

# Step 2: Data Preprocessing
class DataPreprocessor:
    """Cleans and prepares data for modeling"""
    
    def __init__(self):
        self.required_columns = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    
    def preprocess_data(self, seasons_data):
        """Clean and merge all seasons data"""
        print("\n🧹 STEP 2: DATA PREPROCESSING")
        print("-" * 40)
        
        all_seasons = []
        
        for season_name, df in seasons_data.items():
            print(f"Processing {season_name}...")
            
            # Add season identifier
            df = df.copy()
            df['Season'] = season_name
            
            # Basic cleaning
            df_clean = self._clean_dataframe(df)
            
            # Validate data
            if self._validate_data(df_clean):
                all_seasons.append(df_clean)
                print(f"✅ {season_name}: Validated ({len(df_clean)} matches)")
            else:
                print(f"⚠️ {season_name}: Validation issues")
                
        # Merge all seasons
        merged_df = pd.concat(all_seasons, ignore_index=True)
        print(f"\n📈 Total merged data: {len(merged_df)} matches")
        
        return merged_df
    
    def _clean_dataframe(self, df):
        """Perform basic data cleaning"""
        df_clean = df.copy()
        
        # Handle missing values
        df_clean = df_clean.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
        
        # Ensure correct data types
        df_clean['FTHG'] = pd.to_numeric(df_clean['FTHG'], errors='coerce')
        df_clean['FTAG'] = pd.to_numeric(df_clean['FTAG'], errors='coerce')
        
        # Filter valid scores
        df_clean = df_clean[
            (df_clean['FTHG'] >= 0) & 
            (df_clean['FTAG'] >= 0)
        ]
        
        return df_clean
    
    def _validate_data(self, df):
        """Validate dataset has required columns and data"""
        # Check required columns
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            print(f"   Missing columns: {missing_cols}")
            return False
            
        # Check data quality
        if len(df) < 10:
            print("   Too few matches")
            return False
            
        return True

# Step 3: Feature Engineering
class FeatureEngineer:
    """Creates features for machine learning"""
    
    def __init__(self):
        self.feature_categories = {}
    
    def create_features(self, df):
        """Create comprehensive features for prediction"""
        print("\n🔧 STEP 3: FEATURE ENGINEERING")
        print("-" * 40)
        
        df_features = df.copy()
        
        # 3.1 Basic match features
        print("Creating basic match features...")
        df_features = self._create_basic_features(df_features)
        
        # 3.2 Team strength features
        print("Creating team strength features...")
        df_features = self._create_team_strength_features(df_features)
        
        # 3.3 Form features
        print("Creating form features...")
        df_features = self._create_form_features(df_features)
        
        # 3.4 Bayesian features
        print("Creating Bayesian features...")
        df_features = self._create_bayesian_features(df_features)
        
        # Track feature categories
        self._categorize_features(df_features)
        
        return df_features
    
    def _create_basic_features(self, df):
        """Create basic match-level features"""
        # Match outcome encoding
        df['HomeWin'] = (df['FTR'] == 'H').astype(int)
        df['AwayWin'] = (df['FTR'] == 'A').astype(int)
        df['Draw'] = (df['FTR'] == 'D').astype(int)
        
        # Goal-based features
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['GoalDifference'] = df['FTHG'] - df['FTAG']
        df['BothTeamsScored'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
        
        return df
    
    def _create_team_strength_features(self, df):
        """Create features representing team strengths"""
        # Simple Elo-like rating (beginner version)
        teams = pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']]))
        team_ratings = {team: 1500 for team in teams}
        
        home_strength = []
        away_strength = []
        
        for idx, match in df.iterrows():
            home_team = match['HomeTeam']
            away_team = match['AwayTeam']
            
            home_strength.append(team_ratings[home_team])
            away_strength.append(team_ratings[away_team])
            
            # Update ratings based on result
            self._update_team_ratings(team_ratings, home_team, away_team, 
                                    match['FTHG'], match['FTAG'])
        
        df['HomeTeamStrength'] = home_strength
        df['AwayTeamStrength'] = away_strength
        df['StrengthDifference'] = df['HomeTeamStrength'] - df['AwayTeamStrength']
        
        return df
    
    def _update_team_ratings(self, ratings, home_team, away_team, home_goals, away_goals):
        """Simple rating update based on match result"""
        K = 30  # Learning rate
        
        # Expected result (simplified)
        home_expected = 1 / (1 + 10 ** ((ratings[away_team] - ratings[home_team]) / 400))
        
        # Actual result
        if home_goals > away_goals:
            home_actual = 1.0
        elif home_goals < away_goals:
            home_actual = 0.0
        else:
            home_actual = 0.5
            
        # Update ratings
        ratings[home_team] += K * (home_actual - home_expected)
        ratings[away_team] += K * ((1 - home_actual) - (1 - home_expected))
    
    def _create_form_features(self, df):
        """Create recent form features for teams"""
        # Sort by date for rolling calculations
        if 'Date' in df.columns:
            df = df.sort_values('Date')
        
        # Calculate recent form (last 5 matches)
        all_teams = pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']]))
        
        for team in all_teams:
            team_matches = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].copy()
            team_matches['TeamPoints'] = team_matches.apply(
                lambda x: self._calculate_points(x, team), axis=1
            )
            
            # Rolling average of points
            team_matches['Form_5'] = team_matches['TeamPoints'].rolling(5, min_periods=1).mean()
            
            # Merge back to main dataframe
            form_mapping = team_matches.set_index(team_matches.index)['Form_5']
            # Simplified implementation - in practice you'd merge carefully
        
        return df
    
    def _calculate_points(self, match, team):
        """Calculate points for a team in a match"""
        if match['HomeTeam'] == team:
            if match['FTR'] == 'H':
                return 3
            elif match['FTR'] == 'D':
                return 1
            else:
                return 0
        else:  # Away team
            if match['FTR'] == 'A':
                return 3
            elif match['FTR'] == 'D':
                return 1
            else:
                return 0
    
    def _create_bayesian_features(self, df):
        """Create Bayesian-inspired features"""
        # Bayesian prior for goal scoring
        avg_home_goals = df['FTHG'].mean()
        avg_away_goals = df['FTAG'].mean()
        
        df['HomeGoalPrior'] = avg_home_goals
        df['AwayGoalPrior'] = avg_away_goals
        
        # Team-specific goal averages (Bayesian estimates with shrinkage)
        for team in pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']])):
            team_home_matches = df[df['HomeTeam'] == team]
            team_away_matches = df[df['AwayTeam'] == team]
            
            # Bayesian estimate: weighted average of team performance and league average
            if len(team_home_matches) > 0:
                team_home_avg = team_home_matches['FTHG'].mean()
                # Shrink towards league average
                df.loc[df['HomeTeam'] == team, 'HomeAttackStrength'] = (
                    0.7 * team_home_avg + 0.3 * avg_home_goals
                )
            
            if len(team_away_matches) > 0:
                team_away_avg = team_away_matches['FTAG'].mean()
                df.loc[df['AwayTeam'] == team, 'AwayAttackStrength'] = (
                    0.7 * team_away_avg + 0.3 * avg_away_goals
                )
        
        return df
    
    def _categorize_features(self, df):
        """Categorize features for better understanding"""
        basic_features = ['HomeWin', 'AwayWin', 'Draw', 'TotalGoals', 'GoalDifference']
        strength_features = [col for col in df.columns if 'Strength' in col]
        form_features = [col for col in df.columns if 'Form' in col]
        bayesian_features = [col for col in df.columns if any(x in col for x in ['Prior', 'Attack'])]
        
        self.feature_categories = {
            'basic': basic_features,
            'strength': strength_features,
            'form': form_features,
            'bayesian': bayesian_features
        }
        
        print(f"Feature breakdown:")
        for category, features in self.feature_categories.items():
            print(f"  {category}: {len(features)} features")

# Step 4: Model Training
class ModelTrainer:
    """Trains machine learning models for prediction"""
    
    def __init__(self):
        self.models = {}
        self.feature_columns = []
    
    def prepare_training_data(self, df):
        """Prepare features and target for training"""
        print("\n🤖 STEP 4: MODEL TRAINING PREPARATION")
        print("-" * 40)
        
        # Define feature columns (exclude identifiers and targets)
        exclude_columns = ['Date', 'HomeTeam', 'AwayTeam', 'Season', 'FTR', 'FTHG', 'FTAG']
        
        self.feature_columns = [col for col in df.columns 
                              if col not in exclude_columns 
                              and not col.startswith('HomeWin') 
                              and not col.startswith('AwayWin')
                              and not col.startswith('Draw')]
        
        print(f"Using {len(self.feature_columns)} features for training")
        print(f"Feature examples: {self.feature_columns[:5]}...")
        
        # Define targets
        X = df[self.feature_columns].fillna(0)
        y_home_win = df['HomeWin']
        y_total_goals = df['TotalGoals']
        
        return X, y_home_win, y_total_goals
    
    def train_models(self, X, y_home_win, y_total_goals):
        """Train multiple models for different prediction tasks"""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, mean_absolute_error
        
        print("\nTraining models...")
        
        # Split data
        X_train, X_test, y_home_train, y_home_test = train_test_split(
            X, y_home_win, test_size=0.2, random_state=42
        )
        
        _, _, y_goals_train, y_goals_test = train_test_split(
            X, y_total_goals, test_size=0.2, random_state=42
        )
        
        # Model 1: Match outcome prediction
        print("1. Training match outcome classifier...")
        outcome_model = RandomForestClassifier(n_estimators=100, random_state=42)
        outcome_model.fit(X_train, y_home_train)
        
        # Evaluate
        y_pred = outcome_model.predict(X_test)
        accuracy = accuracy_score(y_home_test, y_pred)
        print(f"   ✅ Outcome model accuracy: {accuracy:.3f}")
        
        # Model 2: Total goals prediction
        print("2. Training total goals regressor...")
        goals_model = RandomForestRegressor(n_estimators=100, random_state=42)
        goals_model.fit(X_train, y_goals_train)
        
        # Evaluate
        y_goals_pred = goals_model.predict(X_test)
        mae = mean_absolute_error(y_goals_test, y_goals_pred)
        print(f"   ✅ Goals model MAE: {mae:.3f}")
        
        # Store models
        self.models = {
            'outcome': outcome_model,
            'goals': goals_model
        }
        
        return self.models

# Step 5: Prediction System
class MatchPredictor:
    """Makes predictions for new matches"""
    
    def __init__(self, models, feature_columns):
        self.models = models
        self.feature_columns = feature_columns
        self.team_stats = {}
    
    def predict_match(self, home_team, away_team, historical_data):
        """Predict outcome for a specific match"""
        print(f"\n🎯 PREDICTING: {home_team} vs {away_team}")
        print("-" * 40)
        
        # Create feature vector for this match
        features = self._create_match_features(home_team, away_team, historical_data)
        
        if features is None:
            print("❌ Could not create features for prediction")
            return None
        
        # Make predictions
        outcome_proba = self.models['outcome'].predict_proba([features])[0]
        predicted_goals = self.models['goals'].predict([features])[0]
        
        # Interpret results
        home_win_prob = outcome_proba[1]  # Assuming class 1 is HomeWin
        away_win_prob = outcome_proba[0]  # Assuming class 0 is AwayWin
        draw_prob = 1 - (home_win_prob + away_win_prob)  # Simplified
        
        print("📊 PREDICTION RESULTS:")
        print(f"   🏆 {home_team} win: {home_win_prob:.1%}")
        print(f"   🤝 Draw: {draw_prob:.1%}")
        print(f"   🏆 {away_team} win: {away_win_prob:.1%}")
        print(f"   ⚽ Predicted total goals: {predicted_goals:.1f}")
        
        # Bayesian-inspired confidence
        confidence = self._calculate_confidence(outcome_proba, predicted_goals)
        print(f"   🎯 Confidence: {confidence}")
        
        return {
            'home_win_prob': home_win_prob,
            'draw_prob': draw_prob,
            'away_win_prob': away_win_prob,
            'predicted_goals': predicted_goals,
            'confidence': confidence
        }
    
    def _create_match_features(self, home_team, away_team, historical_data):
        """Create feature vector for a specific match"""
        # This is simplified - in practice you'd compute recent form, etc.
        features = {}
        
        # Get team strength features from historical data
        home_matches = historical_data[historical_data['HomeTeam'] == home_team]
        away_matches = historical_data[historical_data['AwayTeam'] == away_team]
        
        if len(home_matches) == 0 or len(away_matches) == 0:
            return None
        
        # Use average values as features
        for feature in self.feature_columns:
            if feature in historical_data.columns:
                # Simple approach: use league averages
                features[feature] = historical_data[feature].mean()
        
        # Ensure all features are present
        for feature in self.feature_columns:
            if feature not in features:
                features[feature] = 0
        
        return [features[feature] for feature in self.feature_columns]
    
    def _calculate_confidence(self, outcome_proba, predicted_goals):
        """Calculate prediction confidence (Bayesian inspired)"""
        # Confidence based on probability distribution
        max_prob = max(outcome_proba)
        
        if max_prob > 0.6:
            return "High"
        elif max_prob > 0.45:
            return "Medium"
        else:
            return "Low"

# Step 6: Main Pipeline
def run_bayesian_pipeline():
    """Complete machine learning pipeline for football prediction"""
    print("🚀 BAYESIAN FOOTBALL PREDICTION PIPELINE")
    print("=" * 50)
    
    try:
        # Step 1: Data Collection
        collector = DataCollector()
        seasons_data = collector.load_season_data()
        
        # Step 2: Data Preprocessing
        preprocessor = DataPreprocessor()
        cleaned_data = preprocessor.preprocess_data(seasons_data)
        
        # Step 3: Feature Engineering
        engineer = FeatureEngineer()
        featured_data = engineer.create_features(cleaned_data)
        
        # Step 4: Model Training
        trainer = ModelTrainer()
        X, y_home_win, y_total_goals = trainer.prepare_training_data(featured_data)
        models = trainer.train_models(X, y_home_win, y_total_goals)
        
        # Step 5: Predictions
        predictor = MatchPredictor(models, trainer.feature_columns)
        
        # Test predictions
        test_matches = [
            ('Arsenal', 'Chelsea'),
            ('Man City', 'Liverpool'),
            ('Tottenham', 'Brighton')
        ]
        
        print("\n" + "="*50)
        print("🧪 TEST PREDICTIONS")
        print("="*50)
        
        predictions = []
        for home, away in test_matches:
            prediction = predictor.predict_match(home, away, featured_data)
            if prediction:
                predictions.append({
                    'match': f"{home} vs {away}",
                    **prediction
                })
        
        # Summary
        print("\n📈 PIPELINE SUMMARY")
        print("-" * 30)
        print(f"✅ Data: {len(cleaned_data)} matches processed")
        print(f"✅ Features: {len(trainer.feature_columns)} features created")
        print(f"✅ Models: {len(models)} models trained")
        print(f"✅ Predictions: {len(predictions)} test predictions made")
        
        return {
            'data': featured_data,
            'models': models,
            'predictor': predictor,
            'predictions': predictions
        }
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = run_bayesian_pipeline()


    