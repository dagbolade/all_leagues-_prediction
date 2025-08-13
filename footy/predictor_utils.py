# footy/predictor_utils.py - ENHANCED WITH LOGICAL CONSTRAINTS & POISSON

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List, Union
import warnings
import joblib

warnings.filterwarnings('ignore')


class TeamMapper:
    """Handles team name mappings and standardization."""

    TEAM_MAPPINGS = {
        'Manchester City': 'Man City',
        'Manchester United': 'Man United',
        'Tottenham Hotspur': 'Tottenham',
        'Brighton & Hove Albion': 'Brighton',
        'West Ham United': 'West Ham',
        'Newcastle United': 'Newcastle',
        'Wolverhampton Wanderers': 'Wolves',
        'Sheffield United': 'Sheffield Utd',
        'Norwich City': 'Norwich',
        'Leicester City': 'Leicester'
    }

    @classmethod
    def standardize_team_name(cls, team_name: str) -> str:
        """Standardize team names for consistency."""
        return cls.TEAM_MAPPINGS.get(team_name, team_name)


class MatchPredictor:
    """Enhanced match predictor with logical constraints and Poisson integration."""

    def __init__(self, df: pd.DataFrame, models_path: str = 'models/football_models.joblib'):
        print(f"🔮 Initializing Enhanced MatchPredictor with logical constraints...")
        self.df = df.copy()
        self.models = {}
        self.calibrated_models = {}
        self.poisson_predictor = None
        self.feature_columns = []

        # Enhanced prediction tasks with logical hierarchy
        self.PREDICTION_TASKS = {
            'match_outcome': 'Match Outcome',
            'over_1_5': 'Over 1.5 Goals',
            'over_2_5': 'Over 2.5 Goals',
            'over_3_5': 'Over 3.5 Goals',
            'total_goals': 'Total Goals',
            'btts': 'Both Teams to Score'
        }

        # Load enhanced models
        self._load_enhanced_models(models_path)

        # Prepare enhanced features
        self._prepare_enhanced_features()

    def _load_enhanced_models(self, models_path: str):
        """Load enhanced trained models with logical constraints."""
        try:
            model_data = joblib.load(models_path)
            print(f"✅ Loaded models, type: {type(model_data)}")

            if isinstance(model_data, dict) and 'models' in model_data:
                print("✅ Detected enhanced model format")
                self.models = model_data['models']
                self.calibrated_models = model_data.get('calibrated_models', {})
                self.poisson_predictor = model_data.get('poisson_predictor', None)

                # Verify enhanced models loaded
                loaded_tasks = []
                for task, model_info in self.models.items():
                    if isinstance(model_info, dict) and 'model' in model_info:
                        actual_model = model_info['model']
                        if actual_model is not None:
                            loaded_tasks.append(task)
                            print(f"✅ Enhanced {task}: {type(actual_model).__name__}")

                print(f"✅ Enhanced models loaded: {loaded_tasks}")

                if self.poisson_predictor:
                    print("✅ Poisson predictor loaded for exact scorelines")

            else:
                print("❌ Enhanced model format not detected")

        except Exception as e:
            print(f"❌ Error loading enhanced models: {e}")
            raise

    def _prepare_enhanced_features(self):
        """Prepare enhanced feature columns using all engineered features."""
        # Get all enhanced feature columns from the dataframe
        exclude_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'League', 'Season', 'Div',
            'FTR', 'FTHG', 'FTAG', 'HTHG', 'HTAG', 'HTR',
            'Referee', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF',
            'HC', 'AC', 'HY', 'AY', 'HR', 'AR', 'TotalGoals',
            'Over1.5', 'Over2.5', 'Over3.5', 'BTTS'
        ]

        # Also exclude betting odds columns to prevent data leakage
        betting_cols = [col for col in self.df.columns if any(bookie in col for bookie in
                                                              ['B365', 'BW', 'IW', 'PS', 'WH', 'SJ', 'VC', 'GB', 'BS',
                                                               'LB'])]
        exclude_cols.extend(betting_cols)

        # Use all engineered features
        all_columns = self.df.columns.tolist()
        self.feature_columns = [col for col in all_columns if col not in exclude_cols]

        print(f"✅ Enhanced features prepared: {len(self.feature_columns)} features")
        print(f"📊 Excluded {len(exclude_cols)} non-predictive columns")

    def _get_enhanced_team_features(self, team: str, date: pd.Timestamp = None) -> pd.Series:
        """Get enhanced features for a team using all engineered features."""

        # Standardize team name
        team = TeamMapper.standardize_team_name(team)

        # Get team matches (both home and away)
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
            ].copy()

        if date is not None:
            # Only use matches before the prediction date (no data leakage)
            team_matches = team_matches[team_matches['Date'] < date]

        if len(team_matches) == 0:
            print(f"⚠️ No enhanced data found for {team}")
            # Return zeros for all features
            return pd.Series(0, index=self.feature_columns)

        # Get the most recent match for this team
        latest_match = team_matches.sort_values('Date').iloc[-1]

        print(f"✅ Found {len(team_matches)} enhanced matches for {team}")

        # Extract enhanced features for this team
        enhanced_features = {}

        for feature in self.feature_columns:
            if feature in latest_match.index:
                enhanced_features[feature] = latest_match[feature]
            else:
                enhanced_features[feature] = 0

        return pd.Series(enhanced_features)

    def _apply_logical_constraints(self, predictions: Dict) -> Tuple[Dict, List[str]]:
        """
        🎯 CORE FIX: Apply logical constraints to prevent impossible predictions.
        """
        fixed_predictions = predictions.copy()
        constraints_applied = []

        # Get Over/Under predictions
        over_1_5 = predictions.get('Over 1.5 Goals', 'Unknown')
        over_2_5 = predictions.get('Over 2.5 Goals', 'Unknown')
        over_3_5 = predictions.get('Over 3.5 Goals', 'Unknown')

        # Convert to binary for logic checking
        over_1_5_bin = 1 if over_1_5 == 'Yes' else 0 if over_1_5 == 'No' else -1
        over_2_5_bin = 1 if over_2_5 == 'Yes' else 0 if over_2_5 == 'No' else -1
        over_3_5_bin = 1 if over_3_5 == 'Yes' else 0 if over_3_5 == 'No' else -1

        # Rule 1: If Over 3.5 = Yes → Over 2.5 = Yes → Over 1.5 = Yes
        if over_3_5_bin == 1 and over_2_5_bin == 0:
            fixed_predictions['Over 2.5 Goals'] = 'Yes'
            constraints_applied.append("Rule 1a: Over 3.5 Yes → Over 2.5 Yes")

        if over_3_5_bin == 1 and over_1_5_bin == 0:
            fixed_predictions['Over 1.5 Goals'] = 'Yes'
            constraints_applied.append("Rule 1b: Over 3.5 Yes → Over 1.5 Yes")

        if over_2_5_bin == 1 and over_1_5_bin == 0:
            fixed_predictions['Over 1.5 Goals'] = 'Yes'
            constraints_applied.append("Rule 1c: Over 2.5 Yes → Over 1.5 Yes")

        # Rule 2: If Over 1.5 = No → Over 2.5 = No → Over 3.5 = No
        if over_1_5_bin == 0 and over_2_5_bin == 1:
            fixed_predictions['Over 2.5 Goals'] = 'No'
            constraints_applied.append("Rule 2a: Over 1.5 No → Over 2.5 No")

        if over_1_5_bin == 0 and over_3_5_bin == 1:
            fixed_predictions['Over 3.5 Goals'] = 'No'
            constraints_applied.append("Rule 2b: Over 1.5 No → Over 3.5 No")

        if over_2_5_bin == 0 and over_3_5_bin == 1:
            fixed_predictions['Over 3.5 Goals'] = 'No'
            constraints_applied.append("Rule 2c: Over 2.5 No → Over 3.5 No")

        # Update total goals based on Over/Under logic
        if 'Total Goals' in predictions:
            logical_total = self._calculate_logical_total_goals(fixed_predictions)
            fixed_predictions['Total Goals'] = f"{logical_total:.1f}"

        return fixed_predictions, constraints_applied

    def _calculate_logical_total_goals(self, predictions: Dict) -> float:
        """Calculate realistic total goals from Over/Under predictions."""
        over_1_5 = predictions.get('Over 1.5 Goals', 'No')
        over_2_5 = predictions.get('Over 2.5 Goals', 'No')
        over_3_5 = predictions.get('Over 3.5 Goals', 'No')

        # Logic-based total goals calculation
        if over_3_5 == 'Yes':
            return 4.2  # Likely 4+ goals
        elif over_2_5 == 'Yes':
            return 3.1  # Likely 3 goals
        elif over_1_5 == 'Yes':
            return 2.3  # Likely 2 goals
        else:
            return 1.1  # Likely 0-1 goals

    def _get_confidence_level(self, probability: float) -> str:
        """Determine confidence level for betting guidance."""
        if probability >= 0.75:
            return "🔥 HIGH"
        elif probability >= 0.60:
            return "📊 MEDIUM"
        else:
            return "⚡ LOW"

    def _extract_team_strength_insights(self, home_features: pd.Series, away_features: pd.Series) -> Dict:
        """Extract team strength insights from enhanced features."""
        insights = {}

        # Elo ratings
        home_elo = home_features.get('HomeElo', 1500)
        away_elo = home_features.get('AwayElo', 1500)  # Away team's elo when they're away

        insights['team_strength'] = {
            'home_elo': f"{home_elo:.0f}",
            'away_elo': f"{away_elo:.0f}",
            'elo_advantage': f"{home_elo - away_elo:+.0f}"
        }

        # Form analysis
        home_form = home_features.get('HomeForm_5', 0.5)
        away_form = away_features.get('AwayForm_5', 0.5)

        key_factors = []
        if home_form > away_form + 0.2:
            key_factors.append("Home team in better form")
        elif away_form > home_form + 0.2:
            key_factors.append("Away team in better form")

        # Goal potential
        home_scoring = home_features.get('HomeScoringForm_5', 1.0)
        away_scoring = away_features.get('AwayScoringForm_5', 1.0)

        if (home_scoring + away_scoring) > 2.5:
            key_factors.append("Both teams scoring regularly")
        elif (home_scoring + away_scoring) < 1.5:
            key_factors.append("Both teams struggling for goals")

        insights['key_factors'] = key_factors[:3]  # Top 3 factors

        return insights

    def predict_match(self, home_team: str, away_team: str) -> Tuple[Dict, Dict]:
        """Make enhanced predictions with logical constraints and Poisson integration."""

        print(f"🔮 ENHANCED Prediction: {home_team} vs {away_team}")

        # Get enhanced features for both teams
        home_features = self._get_enhanced_team_features(home_team)
        away_features = self._get_enhanced_team_features(away_team)

        # Create enhanced feature matrix
        feature_matrix = pd.DataFrame([home_features.values], columns=self.feature_columns)

        print(f"✅ Enhanced feature matrix created: {feature_matrix.shape}")

        predictions = {}
        probabilities = {}

        # Make predictions with all enhanced models
        for task, display_name in self.PREDICTION_TASKS.items():
            if task in self.models:
                try:
                    print(f"🔄 Enhanced prediction for {display_name}...")

                    model_info = self.models[task]
                    if isinstance(model_info, dict) and 'model' in model_info:
                        model = model_info['model']
                        task_features = model_info.get('features', self.feature_columns)

                        # Use task-specific features if available
                        available_features = [f for f in task_features if f in feature_matrix.columns]
                        if available_features:
                            task_matrix = feature_matrix[available_features]
                            print(f"   Using {len(available_features)} enhanced features")
                        else:
                            task_matrix = feature_matrix
                            print(f"   Using all {len(self.feature_columns)} features")

                        # Make enhanced prediction
                        if hasattr(model, 'predict_proba'):
                            # Classification with probabilities
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
                                # Ensure realistic goal predictions
                                pred_value = max(0, min(10, pred_value))
                                predictions[display_name] = f"{pred_value:.1f}"
                                probabilities[display_name] = 0.8  # Default confidence
                            else:
                                predictions[display_name] = pred_value
                                probabilities[display_name] = 0.8

                        print(f"✅ {display_name}: {predictions.get(display_name, 'N/A')}")

                except Exception as e:
                    print(f"❌ Enhanced prediction failed for {display_name}: {e}")
                    predictions[display_name] = "Error"
                    probabilities[display_name] = 0.0

        # 🎯 Apply logical constraints
        print("🔧 Applying logical constraints...")
        constrained_predictions, constraints_applied = self._apply_logical_constraints(predictions)

        if constraints_applied:
            for constraint in constraints_applied:
                print(f"   ✅ Applied {constraint}")
        else:
            print("   ✅ No constraints needed - predictions already logical")

        print(f"✅ Enhanced predictions generated: {len(constrained_predictions)}")
        return constrained_predictions, probabilities

    def get_poisson_insights(self, home_team: str, away_team: str) -> Dict:
        """
        🎯 NEW: Get Poisson-based exact scoreline predictions and insights.
        """
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

    def get_comprehensive_insights(self, home_team: str, away_team: str) -> Dict:
        """Get comprehensive match insights using all enhanced features."""

        print(f"📊 Getting comprehensive insights for {home_team} vs {away_team}")

        # Get team features
        home_features = self._get_enhanced_team_features(home_team)
        away_features = self._get_enhanced_team_features(away_team)

        # Extract team strength insights
        strength_insights = self._extract_team_strength_insights(home_features, away_features)

        # Get Poisson insights
        poisson_insights = self.get_poisson_insights(home_team, away_team)

        # Combine all insights
        comprehensive_insights = {
            **strength_insights,
            'poisson_analysis': poisson_insights,
            'betting_focus': self._get_betting_recommendations(home_features, away_features),
            'confidence_assessment': self._assess_prediction_confidence(home_features, away_features)
        }

        return comprehensive_insights

    def _get_betting_recommendations(self, home_features: pd.Series, away_features: pd.Series) -> Dict:
        """Get betting market recommendations based on features."""
        recommendations = {}

        # Goal market analysis
        home_over_25 = home_features.get('HomeOverRate2.5_5', 0.5)
        away_over_25 = away_features.get('AwayOverRate2.5_5', 0.5)
        combined_over_25 = (home_over_25 + away_over_25) / 2

        if combined_over_25 > 0.7:
            recommendations['primary_market'] = 'Over 2.5 Goals'
            recommendations['confidence'] = 'High'
        elif combined_over_25 < 0.3:
            recommendations['primary_market'] = 'Under 2.5 Goals'
            recommendations['confidence'] = 'High'
        else:
            recommendations['primary_market'] = 'Over/Under 2.5 Goals'
            recommendations['confidence'] = 'Medium'

        # BTTS analysis
        home_btts = home_features.get('HomeBTTSForm_5', 0.5)
        away_btts = away_features.get('AwayBTTSForm_5', 0.5)
        combined_btts = (home_btts + away_btts) / 2

        if combined_btts > 0.6:
            recommendations['secondary_market'] = 'Both Teams to Score - Yes'
        else:
            recommendations['secondary_market'] = 'Both Teams to Score - No'

        return recommendations

    def _assess_prediction_confidence(self, home_features: pd.Series, away_features: pd.Series) -> str:
        """Assess overall prediction confidence based on data quality."""
        confidence_factors = []

        # Elo difference factor
        home_elo = home_features.get('HomeElo', 1500)
        away_elo = away_features.get('AwayElo', 1500)
        elo_diff = abs(home_elo - away_elo)

        if elo_diff > 200:
            confidence_factors.append("Large Elo difference")
        elif elo_diff < 50:
            confidence_factors.append("Very close teams")

        # Form consistency
        home_form_variance = abs(home_features.get('HomeForm_3', 0.5) - home_features.get('HomeForm_10', 0.5))
        away_form_variance = abs(away_features.get('AwayForm_3', 0.5) - away_features.get('AwayForm_10', 0.5))

        if home_form_variance < 0.2 and away_form_variance < 0.2:
            confidence_factors.append("Consistent recent form")

        # Determine overall confidence
        if len(confidence_factors) >= 2:
            return "High"
        elif len(confidence_factors) == 1:
            return "Medium"
        else:
            return "Low"

    def predict_with_full_insights(self, home_team: str, away_team: str) -> Dict:
        """
        🎯 COMPLETE: Make predictions with full insights, constraints, and Poisson analysis.
        """
        # Get core predictions
        predictions, probabilities = self.predict_match(home_team, away_team)

        # Get comprehensive insights
        insights = self.get_comprehensive_insights(home_team, away_team)

        # Format enhanced output
        enhanced_output = {
            'predictions': predictions,
            'probabilities': probabilities,
            'insights': insights,
            'poisson_scorelines': insights.get('poisson_analysis', {}),
            'betting_guidance': insights.get('betting_focus', {}),
            'confidence_level': insights.get('confidence_assessment', 'Medium')
        }

        return enhanced_output


def create_predictor(df: pd.DataFrame, models_path: str = 'models/football_models.joblib') -> MatchPredictor:
    """Factory function to create enhanced predictor with logical constraints."""
    return MatchPredictor(df, models_path)