# footy/predictor_utils.py - ENHANCED BAYESIAN INTEGRATION

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import joblib
import logging
from scipy import stats
from sklearn.isotonic import IsotonicRegression
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class BayesianMatchPredictor:
    """Enhanced predictor with full Bayesian integration from your enhanced pipeline"""

    def __init__(self, df: pd.DataFrame, models_path: str = 'models/football_models.joblib'):
        print(f"🎯 Initializing BAYESIAN MatchPredictor...")

        self.df = df.copy()
        self.models = {}
        self.calibrated_models = {}
        self.poisson_predictor = None
        self.feature_columns = []
        self.bayesian_priors = {}
        self.confidence_adjuster = None

        # Enhanced prediction tasks matching your model training
        self.PREDICTION_TASKS = {
            'match_outcome': 'Match Outcome',
            'over_1_5': 'Over 1.5 Goals',
            'over_2_5': 'Over 2.5 Goals',
            'over_3_5': 'Over 3.5 Goals',
            'total_goals': 'Total Goals',
            'btts': 'Both Teams to Score'
        }

        # Load enhanced Bayesian models
        self._load_bayesian_models(models_path)

        # Prepare enhanced features from your pipeline
        self._prepare_bayesian_features()

    def _load_bayesian_models(self, models_path: str):
        """Load your enhanced Bayesian models with all components"""
        try:
            model_data = joblib.load(models_path)
            print(f"✅ Loaded Bayesian model data, type: {type(model_data)}")

            if isinstance(model_data, dict):
                # Load all Bayesian components
                self.models = model_data.get('models', {})
                self.calibrated_models = model_data.get('calibrated_models', {})
                self.poisson_predictor = model_data.get('poisson_predictor', None)
                self.bayesian_priors = model_data.get('bayesian_priors', {})
                self.confidence_adjuster = model_data.get('confidence_adjuster', None)
                self.feature_categories = model_data.get('feature_categories', {})
                self.available_features = model_data.get('available_features', [])

                # Verify Bayesian models loaded
                loaded_tasks = []
                for task, model_info in self.models.items():
                    if isinstance(model_info, dict) and 'model' in model_info:
                        actual_model = model_info['model']
                        if actual_model is not None:
                            loaded_tasks.append(task)
                            print(f"✅ Bayesian {task}: {type(actual_model).__name__}")

                print(f"🧠 Bayesian models loaded: {loaded_tasks}")
                print(f"🧠 Bayesian priors available: {list(self.bayesian_priors.keys())}")

                if self.poisson_predictor:
                    print("⚽ Poisson predictor loaded for exact scorelines")

                if self.calibrated_models:
                    print(f"📊 Calibrated models available: {list(self.calibrated_models.keys())}")

            else:
                print("❌ Bayesian model format not detected")
                raise ValueError("Expected enhanced Bayesian model format")

        except Exception as e:
            print(f"❌ Error loading Bayesian models: {e}")
            raise

    def _prepare_bayesian_features(self):
        """Prepare enhanced feature columns from your Bayesian pipeline"""
        # Exclude target variables and non-predictive columns
        exclude_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'League', 'Season', 'Div',
            'FTR', 'FTHG', 'FTAG', 'HTHG', 'HTAG', 'HTR',
            'Referee', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF',
            'HC', 'AC', 'HY', 'AY', 'HR', 'AR', 'TotalGoals',
            'Over1.5', 'Over2.5', 'Over3.5', 'BTTS'
        ]

        # Also exclude betting odds to prevent data leakage
        betting_cols = [col for col in self.df.columns if any(bookie in col for bookie in
                                                              ['B365', 'BW', 'IW', 'PS', 'WH', 'SJ', 'VC', 'GB', 'BS',
                                                               'LB'])]
        exclude_cols.extend(betting_cols)

        # Use all enhanced features from your Bayesian pipeline
        all_columns = self.df.columns.tolist()
        self.feature_columns = [col for col in all_columns if col not in exclude_cols]

        # Prioritize Bayesian features
        bayesian_features = [col for col in self.feature_columns if 'Bayesian' in col]
        elo_features = [col for col in self.feature_columns if 'Elo' in col]
        form_features = [col for col in self.feature_columns if 'Form' in col]
        h2h_features = [col for col in self.feature_columns if 'H2H' in col]

        print(f"🧠 Bayesian features prepared: {len(self.feature_columns)} total features")
        print(f"   🎯 Bayesian features: {len(bayesian_features)}")
        print(f"   🏆 Elo features: {len(elo_features)}")
        print(f"   📈 Form features: {len(form_features)}")
        print(f"   🤝 H2H features: {len(h2h_features)}")

    def _get_bayesian_team_features(self, home_team: str, away_team: str,
                                    match_date: pd.Timestamp = None) -> pd.DataFrame:
        """Get Bayesian features for a match using your enhanced pipeline"""

        # Create a mock match for feature generation
        if match_date is None:
            match_date = pd.Timestamp.now()

        # Get recent data for both teams
        home_matches = self.df[
            (self.df['HomeTeam'] == home_team) | (self.df['AwayTeam'] == home_team)
            ].copy()

        away_matches = self.df[
            (self.df['HomeTeam'] == away_team) | (self.df['AwayTeam'] == away_team)
            ].copy()

        if len(home_matches) == 0 or len(away_matches) == 0:
            print(f"⚠️ Limited data for {home_team} vs {away_team}")
            # Return zeros for all features
            return pd.DataFrame(0, index=[0], columns=self.feature_columns)

        # Find the most recent match features for prediction
        # This uses the latest available Bayesian features for each team
        combined_matches = self.df[
            ((self.df['HomeTeam'] == home_team) | (self.df['AwayTeam'] == home_team) |
             (self.df['HomeTeam'] == away_team) | (self.df['AwayTeam'] == away_team))
        ].copy()

        if len(combined_matches) == 0:
            return pd.DataFrame(0, index=[0], columns=self.feature_columns)

        # Get the latest match and use its features as a template
        latest_match = combined_matches.sort_values('Date').iloc[-1]

        # Create feature vector by extracting team-specific features
        features = {}

        # Get home team features (when they were playing at home)
        home_home_matches = self.df[self.df['HomeTeam'] == home_team]
        if len(home_home_matches) > 0:
            latest_home_home = home_home_matches.sort_values('Date').iloc[-1]

            # Extract home team features
            for col in self.feature_columns:
                if col.startswith('Home') and col in latest_home_home.index:
                    features[col] = latest_home_home[col]
                elif col in latest_home_home.index:
                    # Skip EloAdvantage here - we'll calculate it properly later
                    if col != 'EloAdvantage':
                        features[col] = latest_home_home[col]

        # Get away team features (when they were playing away)
        away_away_matches = self.df[self.df['AwayTeam'] == away_team]
        if len(away_away_matches) > 0:
            latest_away_away = away_away_matches.sort_values('Date').iloc[-1]

            # Extract away team features
            for col in self.feature_columns:
                if col.startswith('Away') and col in latest_away_away.index:
                    features[col] = latest_away_away[col]
                elif col not in features and col in latest_away_away.index:
                    # Skip EloAdvantage here - we'll calculate it properly later
                    if col != 'EloAdvantage':
                        features[col] = latest_away_away[col]

        # Fill missing features with zeros or defaults
        for col in self.feature_columns:
            if col not in features:
                if 'Elo' in col and col != 'EloAdvantage':
                    features[col] = 1500  # Default Elo
                elif 'Prob' in col:
                    features[col] = 0.5  # Default probability
                elif 'Rate' in col:
                    features[col] = 0.5  # Default rate
                elif col != 'EloAdvantage':  # Skip EloAdvantage
                    features[col] = 0  # Default zero

        # 🔧 CRITICAL FIX: Properly calculate EloAdvantage
        if 'HomeElo' in features and 'AwayElo' in features:
            features['EloAdvantage'] = features['HomeElo'] - features['AwayElo']
            print(
                f"🔧 Fixed EloAdvantage: {features['HomeElo']:.1f} - {features['AwayElo']:.1f} = {features['EloAdvantage']:.1f}")
        else:
            features['EloAdvantage'] = 0  # Default if Elo values missing

        # 🔧 ADDITIONAL FIXES: Recalculate other derived features properly

        # Fix Bayesian match outcome probabilities if they exist
        if 'HomeElo' in features and 'AwayElo' in features and 'EloAdvantage' in features:
            elo_diff = features['EloAdvantage']

            # Recalculate Bayesian home win probability
            if 'MatchOutcome_HomeProb' in self.feature_columns:
                features['MatchOutcome_HomeProb'] = 1 / (1 + 10 ** (-elo_diff / 400))
                features['MatchOutcome_AwayProb'] = 1 / (1 + 10 ** (elo_diff / 400))
                features['MatchOutcome_DrawProb'] = max(0.15, min(0.40,
                                                                  1 - features['MatchOutcome_HomeProb'] - features[
                                                                      'MatchOutcome_AwayProb']))

                # Normalize probabilities
                total_prob = (features['MatchOutcome_HomeProb'] +
                              features['MatchOutcome_DrawProb'] +
                              features['MatchOutcome_AwayProb'])
                if total_prob > 0:
                    features['MatchOutcome_HomeProb'] /= total_prob
                    features['MatchOutcome_DrawProb'] /= total_prob
                    features['MatchOutcome_AwayProb'] /= total_prob

            # Recalculate Bayesian win probabilities if they exist
            if 'BayesianHomeWinProb' in self.feature_columns:
                features['BayesianHomeWinProb'] = features['MatchOutcome_HomeProb']
                features['BayesianDrawProb'] = features['MatchOutcome_DrawProb']
                features['BayesianAwayWinProb'] = features['MatchOutcome_AwayProb']

        # Fix team strength comparisons
        if 'HomeAttackStrength' in features and 'AwayDefenseStrength' in features:
            if 'ExpectedHomeGoals' in self.feature_columns:
                features['ExpectedHomeGoals'] = features['HomeAttackStrength'] * features['AwayDefenseStrength']

        if 'AwayAttackStrength' in features and 'HomeDefenseStrength' in features:
            if 'ExpectedAwayGoals' in self.feature_columns:
                features['ExpectedAwayGoals'] = features['AwayAttackStrength'] * features['HomeDefenseStrength']

        # Fix Bayesian expected total
        if ('ExpectedHomeGoals' in features and 'ExpectedAwayGoals' in features and
                'BayesianExpectedTotal' in self.feature_columns):
            features['BayesianExpectedTotal'] = features['ExpectedHomeGoals'] + features['ExpectedAwayGoals']

        # Create DataFrame
        feature_df = pd.DataFrame([features], columns=self.feature_columns)

        print(f"✅ Bayesian features extracted for {home_team} vs {away_team}")
        print(f"   📊 Feature vector shape: {feature_df.shape}")

        # Debug output for key features
        if 'EloAdvantage' in features:
            advantage = features['EloAdvantage']
            if advantage < -100:
                print(f"   🎯 Strong away advantage: {advantage:.1f} (favors {away_team})")
            elif advantage > 100:
                print(f"   🎯 Strong home advantage: {advantage:.1f} (favors {home_team})")
            else:
                print(f"   ⚖️ Close match: {advantage:.1f} Elo difference")

        return feature_df

    def apply_bayesian_logical_constraints(self, predictions: Dict, probabilities: Dict) -> Tuple[
        Dict, Dict, List[str]]:
        """Apply Bayesian logical constraints with probability calibration"""
        fixed_predictions = predictions.copy()
        fixed_probabilities = probabilities.copy()
        constraints_applied = []

        # Get Over/Under predictions and probabilities
        over_1_5 = predictions.get('Over 1.5 Goals', 'Unknown')
        over_2_5 = predictions.get('Over 2.5 Goals', 'Unknown')
        over_3_5 = predictions.get('Over 3.5 Goals', 'Unknown')

        over_1_5_prob = probabilities.get('Over 1.5 Goals', 0.5)
        over_2_5_prob = probabilities.get('Over 2.5 Goals', 0.5)
        over_3_5_prob = probabilities.get('Over 3.5 Goals', 0.5)

        # Convert to binary for logic checking
        over_1_5_bin = 1 if over_1_5 == 'Yes' else 0 if over_1_5 == 'No' else -1
        over_2_5_bin = 1 if over_2_5 == 'Yes' else 0 if over_2_5 == 'No' else -1
        over_3_5_bin = 1 if over_3_5 == 'Yes' else 0 if over_3_5 == 'No' else -1

        # Bayesian Rule 1: If Over 3.5 = Yes → Over 2.5 = Yes → Over 1.5 = Yes
        if over_3_5_bin == 1 and over_2_5_bin == 0:
            fixed_predictions['Over 2.5 Goals'] = 'Yes'
            # Bayesian probability adjustment
            fixed_probabilities['Over 2.5 Goals'] = max(over_2_5_prob, over_3_5_prob * 0.9)
            constraints_applied.append("Bayesian Rule 1a: Over 3.5 Yes → Over 2.5 Yes")

        if over_3_5_bin == 1 and over_1_5_bin == 0:
            fixed_predictions['Over 1.5 Goals'] = 'Yes'
            fixed_probabilities['Over 1.5 Goals'] = max(over_1_5_prob, over_3_5_prob * 0.95)
            constraints_applied.append("Bayesian Rule 1b: Over 3.5 Yes → Over 1.5 Yes")

        if over_2_5_bin == 1 and over_1_5_bin == 0:
            fixed_predictions['Over 1.5 Goals'] = 'Yes'
            fixed_probabilities['Over 1.5 Goals'] = max(over_1_5_prob, over_2_5_prob * 0.9)
            constraints_applied.append("Bayesian Rule 1c: Over 2.5 Yes → Over 1.5 Yes")

        # Bayesian Rule 2: If Over 1.5 = No → Over 2.5 = No → Over 3.5 = No
        if over_1_5_bin == 0 and over_2_5_bin == 1:
            fixed_predictions['Over 2.5 Goals'] = 'No'
            fixed_probabilities['Over 2.5 Goals'] = min(over_2_5_prob, (1 - over_1_5_prob) * 0.9)
            constraints_applied.append("Bayesian Rule 2a: Over 1.5 No → Over 2.5 No")

        if over_1_5_bin == 0 and over_3_5_bin == 1:
            fixed_predictions['Over 3.5 Goals'] = 'No'
            fixed_probabilities['Over 3.5 Goals'] = min(over_3_5_prob, (1 - over_1_5_prob) * 0.8)
            constraints_applied.append("Bayesian Rule 2b: Over 1.5 No → Over 3.5 No")

        if over_2_5_bin == 0 and over_3_5_bin == 1:
            fixed_predictions['Over 3.5 Goals'] = 'No'
            fixed_probabilities['Over 3.5 Goals'] = min(over_3_5_prob, (1 - over_2_5_prob) * 0.8)
            constraints_applied.append("Bayesian Rule 2c: Over 2.5 No → Over 3.5 No")

        # Ensure Bayesian probability hierarchy: P(Over1.5) ≥ P(Over2.5) ≥ P(Over3.5)
        if 'Over 1.5 Goals' in fixed_probabilities and 'Over 2.5 Goals' in fixed_probabilities:
            if fixed_probabilities['Over 2.5 Goals'] > fixed_probabilities['Over 1.5 Goals']:
                fixed_probabilities['Over 1.5 Goals'] = fixed_probabilities['Over 2.5 Goals']
                constraints_applied.append("Bayesian probability hierarchy: P(Over1.5) ≥ P(Over2.5)")

        if 'Over 2.5 Goals' in fixed_probabilities and 'Over 3.5 Goals' in fixed_probabilities:
            if fixed_probabilities['Over 3.5 Goals'] > fixed_probabilities['Over 2.5 Goals']:
                fixed_probabilities['Over 2.5 Goals'] = fixed_probabilities['Over 3.5 Goals']
                constraints_applied.append("Bayesian probability hierarchy: P(Over2.5) ≥ P(Over3.5)")

        return fixed_predictions, fixed_probabilities, constraints_applied

    def calculate_bayesian_total_goals(self, predictions: Dict, probabilities: Dict) -> float:
        """Calculate realistic total goals using Bayesian expected value"""
        over_1_5_prob = probabilities.get('Over 1.5 Goals', 0.5)
        over_2_5_prob = probabilities.get('Over 2.5 Goals', 0.5)
        over_3_5_prob = probabilities.get('Over 3.5 Goals', 0.3)

        # Bayesian expected goals calculation
        # E[Goals] = sum(P(Goals > k) for k = 0, 1, 2, ...)
        expected_goals = (
                1.0 +  # Always at least 0 goals
                over_1_5_prob +  # P(Goals > 1.5)
                over_2_5_prob +  # P(Goals > 2.5)
                over_3_5_prob  # P(Goals > 3.5)
        )

        return max(0.5, min(6.0, expected_goals))  # Realistic bounds

    def predict_match_bayesian(self, home_team: str, away_team: str) -> Tuple[Dict, Dict]:
        """Make Bayesian predictions using your enhanced models"""

        print(f"🧠 BAYESIAN Prediction: {home_team} vs {away_team}")

        # Get Bayesian features
        feature_matrix = self._get_bayesian_team_features(home_team, away_team)

        if feature_matrix.empty:
            print("❌ Could not generate Bayesian features")
            return {}, {}

        print(f"✅ Bayesian feature matrix ready: {feature_matrix.shape}")

        predictions = {}
        probabilities = {}

        # Make predictions with all Bayesian models
        for task, display_name in self.PREDICTION_TASKS.items():
            if task in self.models:
                try:
                    print(f"🔄 Bayesian prediction for {display_name}...")

                    model_info = self.models[task]
                    if isinstance(model_info, dict) and 'model' in model_info:
                        model = model_info['model']
                        task_features = model_info.get('features', self.feature_columns)

                        # Use task-specific Bayesian features
                        available_features = [f for f in task_features if f in feature_matrix.columns]
                        if available_features:
                            task_matrix = feature_matrix[available_features]
                            print(f"   Using {len(available_features)} Bayesian features for {task}")
                        else:
                            task_matrix = feature_matrix
                            print(f"   Using all {len(self.feature_columns)} features for {task}")

                        # Make Bayesian prediction
                        if hasattr(model, 'predict_proba'):
                            # Classification with Bayesian probabilities
                            proba = model.predict_proba(task_matrix)[0]
                            pred_class = np.argmax(proba)

                            if task == 'match_outcome':
                                outcomes = ['Home Win', 'Draw', 'Away Win']
                                predictions[display_name] = outcomes[pred_class]
                                probabilities[display_name] = {
                                    outcomes[i]: proba[i] for i in range(len(outcomes))
                                }
                            else:
                                # Binary classification
                                predictions[display_name] = 'Yes' if pred_class == 1 else 'No'
                                confidence = max(proba)
                                probabilities[display_name] = confidence

                        elif hasattr(model, 'predict'):
                            # Regression or simple prediction
                            pred_value = model.predict(task_matrix)[0]

                            if task == 'total_goals':
                                # Ensure realistic goal predictions with Bayesian bounds
                                pred_value = max(0, min(10, pred_value))
                                predictions[display_name] = f"{pred_value:.1f}"
                                probabilities[display_name] = 0.8  # Default confidence
                            else:
                                predictions[display_name] = pred_value
                                probabilities[display_name] = 0.8

                        print(f"✅ {display_name}: {predictions.get(display_name, 'N/A')}")

                except Exception as e:
                    print(f"❌ Bayesian prediction failed for {display_name}: {e}")
                    predictions[display_name] = "Error"
                    probabilities[display_name] = 0.0

        # Apply Bayesian logical constraints
        print("🧠 Applying Bayesian logical constraints...")
        constrained_predictions, constrained_probabilities, constraints_applied = self.apply_bayesian_logical_constraints(
            predictions, probabilities
        )

        if constraints_applied:
            for constraint in constraints_applied:
                print(f"   ✅ Applied {constraint}")
        else:
            print("   ✅ No Bayesian constraints needed - predictions already logical")

        # Calculate Bayesian total goals
        if 'Total Goals' not in constrained_predictions:
            bayesian_total = self.calculate_bayesian_total_goals(constrained_predictions, constrained_probabilities)
            constrained_predictions['Total Goals'] = f"{bayesian_total:.1f}"
            constrained_probabilities['Total Goals'] = 0.8

        print(f"✅ Bayesian predictions completed: {len(constrained_predictions)}")
        return constrained_predictions, constrained_probabilities

    def get_bayesian_confidence_intervals(self, probabilities: Dict) -> Dict:
        """Calculate Bayesian confidence intervals for predictions"""
        confidence_intervals = {}

        for pred_type, prob_data in probabilities.items():
            try:
                if pred_type == 'Match Outcome' and isinstance(prob_data, dict):
                    # Match outcome confidence based on probability spread
                    probs = list(prob_data.values())
                    max_prob = max(probs)
                    confidence = 0.6 + (max_prob - 0.33) * 0.8  # Scale from 0.6 to 1.0

                    confidence_intervals[pred_type] = {
                        'confidence_level': f"{confidence:.1%}",
                        'prediction_strength': 'High' if max_prob > 0.6 else 'Medium' if max_prob > 0.45 else 'Low'
                    }

                elif isinstance(prob_data, (int, float)):
                    # Binary prediction confidence
                    confidence = abs(prob_data - 0.5) * 2  # Convert to 0-1 scale

                    confidence_intervals[pred_type] = {
                        'confidence_level': f"{confidence:.1%}",
                        'prediction_strength': 'High' if confidence > 0.7 else 'Medium' if confidence > 0.5 else 'Low'
                    }

            except Exception as e:
                logger.warning(f"Could not calculate confidence for {pred_type}: {e}")

        return confidence_intervals

    def get_poisson_insights(self, home_team: str, away_team: str) -> Dict:
        """Get Poisson-based exact scoreline predictions"""
        if not self.poisson_predictor:
            print("⚠️ Poisson predictor not available")
            return {}

        try:
            print(f"⚽ Getting Poisson scoreline analysis for {home_team} vs {away_team}")

            # Get Poisson predictions
            poisson_result = self.poisson_predictor.predict_scoreline_probabilities(home_team, away_team)

            if not poisson_result:
                return {}

            # Format for display
            insights = {
                'expected_goals': {
                    'home': f"{poisson_result['expected_goals']['home']:.1f}",
                    'away': f"{poisson_result['expected_goals']['away']:.1f}",
                    'total': f"{poisson_result['expected_goals']['total']:.1f}"
                },
                'most_likely_scorelines': [],
                'outcome_probabilities': poisson_result['outcome_probabilities'],
                'goal_market_probs': poisson_result['goal_market_probs']
            }

            # Top 5 most likely scorelines
            for scoreline, prob in poisson_result['top_scorelines'][:5]:
                insights['most_likely_scorelines'].append({
                    'score': scoreline,
                    'probability': f"{prob:.1%}"
                })

            return insights

        except Exception as e:
            print(f"❌ Poisson analysis failed: {e}")
            return {}

    def predict_with_full_bayesian_analysis(self, home_team: str, away_team: str) -> Dict:
        """
        🎯 COMPLETE: Make predictions with full Bayesian analysis and insights
        """
        # Get core Bayesian predictions
        predictions, probabilities = self.predict_match_bayesian(home_team, away_team)

        # Get Bayesian confidence intervals
        confidence_intervals = self.get_bayesian_confidence_intervals(probabilities)

        # Get Poisson insights
        poisson_insights = self.get_poisson_insights(home_team, away_team)

        # Format enhanced output
        bayesian_output = {
            'predictions': predictions,
            'probabilities': probabilities,
            'confidence_intervals': confidence_intervals,
            'poisson_analysis': poisson_insights,
            'bayesian_priors': self.bayesian_priors,
            'model_info': {
                'models_used': list(self.models.keys()),
                'calibrated_models': list(self.calibrated_models.keys()),
                'poisson_available': self.poisson_predictor is not None
            }
        }

        return bayesian_output


def create_bayesian_predictor(df: pd.DataFrame,
                              models_path: str = 'models/football_models.joblib') -> BayesianMatchPredictor:
    """Factory function to create enhanced Bayesian predictor"""
    return BayesianMatchPredictor(df, models_path)