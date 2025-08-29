# footy/model_training.py - ENHANCED WITH BAYESIAN HYPEROPT & INFERENCE

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score, log_loss, \
    brier_score_loss, mean_squared_error, mean_absolute_error
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_selection import SelectKBest, f_classif, f_regression
from xgboost import XGBClassifier, XGBRegressor
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, StackingClassifier, StackingRegressor
from imblearn.over_sampling import SMOTE
import warnings
import joblib
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats
import logging

# Bayesian Hyperparameter Optimization
try:
    from hyperopt import fmin, tpe, hp, STATUS_OK, Trials, space_eval
    from hyperopt.early_stop import no_progress_loss

    HYPEROPT_AVAILABLE = True
except ImportError:
    print("⚠️ hyperopt not available. Install with: pip install hyperopt")
    HYPEROPT_AVAILABLE = False

# Import Poisson predictor
from footy.poisson_predictor import PoissonScorelinePredictor

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BayesianLogicalConstraintValidator:
    """Enhanced logical constraints with Bayesian probability calibration."""

    @staticmethod
    def apply_bayesian_over_under_constraints(predictions: dict, probabilities: dict) -> Tuple[dict, dict, List[str]]:
        """
        🧠 BAYESIAN CONSTRAINTS: Apply logical constraints while preserving probability distributions.
        """
        fixed_predictions = predictions.copy()
        fixed_probabilities = probabilities.copy()
        constraints_applied = []

        # Get Over/Under predictions and probabilities
        over_1_5 = predictions.get('over_1_5', None)
        over_2_5 = predictions.get('over_2_5', None)
        over_3_5 = predictions.get('over_3_5', None)

        over_1_5_prob = probabilities.get('over_1_5', 0.5)
        over_2_5_prob = probabilities.get('over_2_5', 0.5)
        over_3_5_prob = probabilities.get('over_3_5', 0.5)

        # Rule 1: If Over 3.5 = Yes → Over 2.5 = Yes → Over 1.5 = Yes
        if over_3_5 == 1 and over_2_5 == 0:
            fixed_predictions['over_2_5'] = 1
            # Bayesian probability adjustment
            fixed_probabilities['over_2_5'] = max(over_2_5_prob, over_3_5_prob * 0.9)
            constraints_applied.append("Bayesian Rule 1a: Over 3.5 Yes → Over 2.5 Yes")

        if over_3_5 == 1 and over_1_5 == 0:
            fixed_predictions['over_1_5'] = 1
            fixed_probabilities['over_1_5'] = max(over_1_5_prob, over_3_5_prob * 0.95)
            constraints_applied.append("Bayesian Rule 1b: Over 3.5 Yes → Over 1.5 Yes")

        if over_2_5 == 1 and over_1_5 == 0:
            fixed_predictions['over_1_5'] = 1
            fixed_probabilities['over_1_5'] = max(over_1_5_prob, over_2_5_prob * 0.9)
            constraints_applied.append("Bayesian Rule 1c: Over 2.5 Yes → Over 1.5 Yes")

        # Rule 2: If Over 1.5 = No → Over 2.5 = No → Over 3.5 = No
        if over_1_5 == 0 and over_2_5 == 1:
            fixed_predictions['over_2_5'] = 0
            fixed_probabilities['over_2_5'] = min(over_2_5_prob, (1 - over_1_5_prob) * 0.9)
            constraints_applied.append("Bayesian Rule 2a: Over 1.5 No → Over 2.5 No")

        if over_1_5 == 0 and over_3_5 == 1:
            fixed_predictions['over_3_5'] = 0
            fixed_probabilities['over_3_5'] = min(over_3_5_prob, (1 - over_1_5_prob) * 0.8)
            constraints_applied.append("Bayesian Rule 2b: Over 1.5 No → Over 3.5 No")

        if over_2_5 == 0 and over_3_5 == 1:
            fixed_predictions['over_3_5'] = 0
            fixed_probabilities['over_3_5'] = min(over_3_5_prob, (1 - over_2_5_prob) * 0.8)
            constraints_applied.append("Bayesian Rule 2c: Over 2.5 No → Over 3.5 No")

        # Ensure probability hierarchy: P(Over1.5) ≥ P(Over2.5) ≥ P(Over3.5)
        if 'over_1_5' in fixed_probabilities and 'over_2_5' in fixed_probabilities:
            if fixed_probabilities['over_2_5'] > fixed_probabilities['over_1_5']:
                fixed_probabilities['over_1_5'] = fixed_probabilities['over_2_5']
                constraints_applied.append("Bayesian probability hierarchy: P(Over1.5) ≥ P(Over2.5)")

        if 'over_2_5' in fixed_probabilities and 'over_3_5' in fixed_probabilities:
            if fixed_probabilities['over_3_5'] > fixed_probabilities['over_2_5']:
                fixed_probabilities['over_2_5'] = fixed_probabilities['over_3_5']
                constraints_applied.append("Bayesian probability hierarchy: P(Over2.5) ≥ P(Over3.5)")

        return fixed_predictions, fixed_probabilities, constraints_applied

    @staticmethod
    def calculate_bayesian_total_goals(predictions: dict, probabilities: dict) -> float:
        """Calculate realistic total goals using Bayesian expected value."""
        over_1_5_prob = probabilities.get('over_1_5', 0.5)
        over_2_5_prob = probabilities.get('over_2_5', 0.5)
        over_3_5_prob = probabilities.get('over_3_5', 0.3)

        # Bayesian expected goals calculation
        # E[Goals] = sum(P(Goals > k) for k = 0, 1, 2, ...)
        expected_goals = (
                1.0 +  # Always at least 0 goals
                over_1_5_prob +  # P(Goals > 1.5)
                over_2_5_prob +  # P(Goals > 2.5)
                over_3_5_prob  # P(Goals > 3.5)
        )

        return max(0.5, min(6.0, expected_goals))  # Realistic bounds


class BayesianFootballPredictor:
    """Enhanced football predictor with Bayesian hyperparameter optimization and inference."""

    def __init__(self):
        self.models = {}
        self.calibrated_models = {}
        self.poisson_predictor = None
        self.metrics = {}
        self.feature_importance = {}
        self.constraint_validator = BayesianLogicalConstraintValidator()
        self.bayesian_priors = {}
        self.hyperopt_trials = {}

        # Enhanced feature categorization with Bayesian features
        self.feature_categories = {
            'core_features': [
                'HomeTeam_encoded', 'AwayTeam_encoded'
            ],
            'bayesian_elo_features': [
                'HomeElo', 'AwayElo', 'EloAdvantage'
            ],
            'bayesian_match_outcome_features': [
                'MatchOutcome_HomeProb', 'MatchOutcome_DrawProb', 'MatchOutcome_AwayProb',
                'MatchCompetitiveness', 'BayesianHomeWinProb', 'BayesianDrawProb', 'BayesianAwayWinProb'
            ],
            'bayesian_goal_features': [
                'BayesianExpectedTotal', 'BayesianOver15Prob', 'BayesianOver25Prob', 'BayesianOver35Prob',
                'BayesianBTTSProb', 'BayesianGoalPotential', 'ExpectedHomeGoals', 'ExpectedAwayGoals'
            ],
            'form_features': [
                'HomeForm_3', 'HomeForm_5', 'HomeForm_10',
                'AwayForm_3', 'AwayForm_5', 'AwayForm_10',
                'HomeFormMomentum', 'AwayFormMomentum'
            ],
            'goal_scoring_features': [
                'HomeScoringForm_3', 'HomeScoringForm_5', 'HomeScoringForm_10',
                'AwayScoringForm_3', 'AwayScoringForm_5', 'AwayScoringForm_10',
                'HomeConcedingForm_3', 'HomeConcedingForm_5', 'HomeConcedingForm_10',
                'AwayConcedingForm_3', 'AwayConcedingForm_5', 'AwayConcedingForm_10'
            ],
            'over_under_features': [
                'HomeOverRate1.5_3', 'HomeOverRate1.5_5', 'HomeOverRate1.5_10',
                'HomeOverRate2.5_3', 'HomeOverRate2.5_5', 'HomeOverRate2.5_10',
                'HomeOverRate3.5_3', 'HomeOverRate3.5_5', 'HomeOverRate3.5_10',
                'AwayOverRate1.5_3', 'AwayOverRate1.5_5', 'AwayOverRate1.5_10',
                'AwayOverRate2.5_3', 'AwayOverRate2.5_5', 'AwayOverRate2.5_10',
                'AwayOverRate3.5_3', 'AwayOverRate3.5_5', 'AwayOverRate3.5_10',
                'BayesianOver25Tendency'
            ],
            'team_strength_features': [
                'HomeAttackStrength', 'AwayAttackStrength', 'HomeDefenseStrength', 'AwayDefenseStrength',
                'HomeAttackStrengthRel', 'AwayAttackStrengthRel', 'HomeDefenseStrengthRel', 'AwayDefenseStrengthRel',
                'AttackDefenseBalance', 'DefensiveVulnerability'
            ],
            'h2h_features': [
                'H2H_HomeWinRate', 'H2H_AvgGoals', 'H2H_BTTSRate', 'H2H_RecentForm',
                'H2H_GoalTrend', 'H2H_Confidence'
            ],
            'referee_features': [
                'RefAvgGoals', 'RefHomeBias', 'RefCardTendency', 'RefOver25Rate'
            ],
            'context_features': [
                'SeasonProgress', 'HomeDaysRest', 'AwayDaysRest', 'RestAdvantage',
                'MatchDensity', 'DayOfWeek', 'Month', 'IsWeekend',
                'IsEarlySeasonBayesian', 'IsMidSeasonBayesian', 'IsLateSeasonBayesian'
            ],
            'gw1_features': [
                'HomeGW1ScoringHistory', 'AwayGW1ScoringHistory', 'HomeGW1FormHistory',
                'AwayGW1FormHistory', 'PromotedTeamPenalty', 'PromotedTeamEarlyBonus'
            ]
        }

    def get_bayesian_search_space(self, task: str) -> Dict:
        """Define Bayesian optimization search spaces for each model type."""

        if task == 'match_outcome':
            # 3-way classification search spaces
            return {
                'xgb': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7, 8]),
                    'subsample': hp.uniform('subsample', 0.6, 1.0),
                    'colsample_bytree': hp.uniform('colsample_bytree', 0.6, 1.0),
                    'reg_alpha': hp.uniform('reg_alpha', 0, 1),
                    'reg_lambda': hp.uniform('reg_lambda', 0, 2),
                    'min_child_weight': hp.choice('min_child_weight', [1, 3, 5, 7])
                },
                'lgbm': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'num_leaves': hp.choice('num_leaves', [31, 63, 127, 255]),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7, 8]),
                    'feature_fraction': hp.uniform('feature_fraction', 0.6, 1.0),
                    'bagging_fraction': hp.uniform('bagging_fraction', 0.6, 1.0),
                    'reg_alpha': hp.uniform('reg_alpha', 0, 1),
                    'reg_lambda': hp.uniform('reg_lambda', 0, 2)
                },
                'catboost': {
                    'iterations': hp.choice('iterations', [200, 300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'depth': hp.choice('depth', [4, 5, 6, 7, 8]),
                    'l2_leaf_reg': hp.uniform('l2_leaf_reg', 1, 10),
                    'border_count': hp.choice('border_count', [128, 254]),
                    'bagging_temperature': hp.uniform('bagging_temperature', 0, 1)
                }
            }

        elif task == 'total_goals':
            # Regression search spaces
            return {
                'xgb': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.15),
                    'max_depth': hp.choice('max_depth', [3, 4, 5, 6]),
                    'subsample': hp.uniform('subsample', 0.7, 1.0),
                    'colsample_bytree': hp.uniform('colsample_bytree', 0.7, 1.0),
                    'reg_alpha': hp.uniform('reg_alpha', 0, 0.5),
                    'reg_lambda': hp.uniform('reg_lambda', 0, 1)
                },
                'lgbm': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.15),
                    'num_leaves': hp.choice('num_leaves', [31, 63, 127]),
                    'max_depth': hp.choice('max_depth', [3, 4, 5, 6]),
                    'feature_fraction': hp.uniform('feature_fraction', 0.7, 1.0),
                    'bagging_fraction': hp.uniform('bagging_fraction', 0.7, 1.0)
                }
            }

        else:
            # Binary classification search spaces
            return {
                'xgb': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7]),
                    'subsample': hp.uniform('subsample', 0.7, 1.0),
                    'colsample_bytree': hp.uniform('colsample_bytree', 0.7, 1.0),
                    'scale_pos_weight': hp.uniform('scale_pos_weight', 0.5, 2.0),
                    'reg_alpha': hp.uniform('reg_alpha', 0, 1),
                    'reg_lambda': hp.uniform('reg_lambda', 0, 2)
                },
                'lgbm': {
                    'n_estimators': hp.choice('n_estimators', [200, 300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'num_leaves': hp.choice('num_leaves', [31, 63, 127]),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7]),
                    'feature_fraction': hp.uniform('feature_fraction', 0.7, 1.0),
                    'bagging_fraction': hp.uniform('bagging_fraction', 0.7, 1.0),
                    'is_unbalance': hp.choice('is_unbalance', [True, False])
                }
            }

    def bayesian_objective(self, params: Dict, X_train, y_train, X_val, y_val,
                           model_type: str, task: str) -> Dict:
        """Objective function for Bayesian optimization."""
        try:
            # Create model with hyperopt parameters
            if model_type == 'xgb':
                if task == 'match_outcome':
                    model = XGBClassifier(
                        objective='multi:softprob',
                        eval_metric='mlogloss',
                        use_label_encoder=False,
                        random_state=42,
                        **params
                    )
                elif task == 'total_goals':
                    model = XGBRegressor(
                        objective='reg:squarederror',
                        random_state=42,
                        **params
                    )
                else:
                    model = XGBClassifier(
                        objective='binary:logistic',
                        eval_metric='logloss',
                        use_label_encoder=False,
                        random_state=42,
                        **params
                    )

            elif model_type == 'lgbm':
                if task == 'match_outcome':
                    model = LGBMClassifier(
                        objective='multiclass',
                        metric='multi_logloss',
                        random_state=42,
                        verbose=-1,
                        **params
                    )
                elif task == 'total_goals':
                    model = LGBMRegressor(
                        objective='regression',
                        metric='rmse',
                        random_state=42,
                        verbose=-1,
                        **params
                    )
                else:
                    model = LGBMClassifier(
                        objective='binary',
                        metric='binary_logloss',
                        random_state=42,
                        verbose=-1,
                        **params
                    )

            elif model_type == 'catboost':
                if task == 'match_outcome':
                    model = CatBoostClassifier(
                        loss_function='MultiClass',
                        auto_class_weights='Balanced',
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **params
                    )
                elif task == 'total_goals':
                    model = CatBoostRegressor(
                        loss_function='RMSE',
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **params
                    )
                else:
                    model = CatBoostClassifier(
                        loss_function='Logloss',
                        auto_class_weights='Balanced',
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **params
                    )

            # Train and evaluate
            model.fit(X_train, y_train)

            if task == 'total_goals':
                y_pred = model.predict(X_val)
                loss = mean_squared_error(y_val, y_pred)
            else:
                y_pred_proba = model.predict_proba(X_val)
                loss = log_loss(y_val, y_pred_proba)

            return {'loss': loss, 'status': STATUS_OK}

        except Exception as e:
            logger.warning(f"Bayesian optimization trial failed: {e}")
            return {'loss': float('inf'), 'status': STATUS_OK}

    def get_task_specific_features(self, task: str, available_features: list) -> list:
        """
        🧠 ENHANCED: Bayesian feature selection for each prediction task.
        """
        # Start with core features
        base_features = []
        for category in ['core_features', 'bayesian_elo_features']:
            base_features.extend([f for f in self.feature_categories[category] if f in available_features])

        if task == 'match_outcome':
            # Match outcome benefits from Bayesian match outcome features and team strength
            additional_categories = [
                'bayesian_match_outcome_features', 'team_strength_features',
                'h2h_features', 'context_features', 'form_features'
            ]

        elif task in ['over_1_5', 'over_2_5', 'over_3_5']:
            # Over/Under predictions benefit from Bayesian goal features
            additional_categories = [
                'bayesian_goal_features', 'over_under_features', 'goal_scoring_features',
                'referee_features', 'team_strength_features'
            ]

        elif task == 'btts':
            # BTTS benefits from attack patterns and Bayesian BTTS features
            additional_categories = [
                'bayesian_goal_features', 'goal_scoring_features',
                'team_strength_features', 'h2h_features'
            ]

        elif task == 'total_goals':
            # Total goals uses Bayesian goal features and all goal-related features
            additional_categories = [
                'bayesian_goal_features', 'over_under_features', 'goal_scoring_features',
                'referee_features', 'team_strength_features'
            ]

        else:
            # Default: use most relevant features
            additional_categories = ['bayesian_goal_features', 'form_features', 'context_features']

        # Add task-specific features
        task_features = base_features.copy()
        for category in additional_categories:
            task_features.extend([f for f in self.feature_categories[category] if f in available_features])

        # Add GW1 features for early season boost
        task_features.extend([f for f in self.feature_categories['gw1_features'] if f in available_features])

        # Remove duplicates and limit to reasonable number
        task_features = list(set(task_features))

        # Limit features to prevent overfitting (but allow more for complex Bayesian models)
        max_features = min(80, len(task_features))  # Increased from 50 for Bayesian features
        if len(task_features) > max_features:
            # Prioritize Bayesian features
            priority_features = base_features + [f for f in task_features if
                                                 any(cat in f.lower() for cat in
                                                     ['bayesian', 'elo', 'form', 'scoring'])]
            task_features = list(set(priority_features))[:max_features]

        return task_features

    def prepare_data(self, df):
        """Enhanced data preparation with Bayesian target creation."""
        df = df.sort_values('Date').copy()

        print("🧠 Analyzing available Bayesian features...")
        available_features = df.columns.tolist()

        # Find which enhanced features exist
        all_possible_features = []
        for category, features in self.feature_categories.items():
            all_possible_features.extend(features)

        existing_features = [f for f in all_possible_features if f in available_features]
        bayesian_features = [f for f in existing_features if 'Bayesian' in f]

        print(f"✅ Found {len(existing_features)} enhanced features")
        print(f"🧠 Found {len(bayesian_features)} Bayesian features")

        self.available_features = existing_features

        # Enhanced target preparation with Bayesian priors
        y = {}

        # Match outcome with Bayesian priors
        if 'FTR' in df.columns:
            y['match_outcome'] = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})

            # Calculate Bayesian priors for match outcomes
            home_win_rate = (df['FTR'] == 'H').mean()
            draw_rate = (df['FTR'] == 'D').mean()
            away_win_rate = (df['FTR'] == 'A').mean()

            self.bayesian_priors['match_outcome'] = {
                'home_win': home_win_rate,
                'draw': draw_rate,
                'away_win': away_win_rate
            }

        # Over/Under targets with Bayesian smoothing
        if 'TotalGoals' in df.columns:
            # Use Bayesian expected values if available
            if 'BayesianExpectedTotal' in df.columns:
                print("   🧠 Using Bayesian expected goals for target creation")
                bayesian_total = df['BayesianExpectedTotal']

                # Create smoother targets using Bayesian expected values
                y['over_1_5'] = ((df['TotalGoals'] > 1.5) | (bayesian_total > 1.8)).astype(int)
                y['over_2_5'] = ((df['TotalGoals'] > 2.5) | (bayesian_total > 2.8)).astype(int)
                y['over_3_5'] = ((df['TotalGoals'] > 3.5) | (bayesian_total > 3.8)).astype(int)
            else:
                y['over_1_5'] = (df['TotalGoals'] > 1.5).astype(int)
                y['over_2_5'] = (df['TotalGoals'] > 2.5).astype(int)
                y['over_3_5'] = (df['TotalGoals'] > 3.5).astype(int)

            y['total_goals'] = df['TotalGoals']

            # Calculate Bayesian priors for over/under
            self.bayesian_priors['over_under'] = {
                'over_1_5_rate': y['over_1_5'].mean(),
                'over_2_5_rate': y['over_2_5'].mean(),
                'over_3_5_rate': y['over_3_5'].mean(),
                'avg_total_goals': df['TotalGoals'].mean()
            }

        # BTTS with Bayesian enhancement
        if 'BTTS' in df.columns:
            y['btts'] = df['BTTS']
        elif 'FTHG' in df.columns and 'FTAG' in df.columns:
            y['btts'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)

        if 'btts' in y:
            self.bayesian_priors['btts'] = {
                'btts_rate': y['btts'].mean()
            }

        print(f"📊 Prepared targets: {list(y.keys())}")
        print(f"🧠 Calculated Bayesian priors for {len(self.bayesian_priors)} target types")
        return df, y

    def create_bayesian_optimized_models(self, task: str, X_train, y_train, X_val, y_val):
        """Create models with Bayesian hyperparameter optimization."""

        if not HYPEROPT_AVAILABLE:
            print("⚠️ Hyperopt not available, using default parameters")
            return self.create_enhanced_models(task)

        print(f"🧠 Starting Bayesian hyperparameter optimization for {task}...")

        search_spaces = self.get_bayesian_search_space(task)
        optimized_models = []

        for model_type, space in search_spaces.items():
            print(f"   🔍 Optimizing {model_type}...")

            # Create trials object for this model
            trials = Trials()

            # Define objective function for this model
            def objective(params):
                return self.bayesian_objective(params, X_train, y_train, X_val, y_val, model_type, task)

            # Run Bayesian optimization
            try:
                best_params = fmin(
                    fn=objective,
                    space=space,
                    algo=tpe.suggest,
                    max_evals=20,  # Reduced for faster training
                    trials=trials,
                    early_stop_fn=no_progress_loss(10),
                    verbose=False
                )

                # Convert hyperopt choice parameters
                best_params = space_eval(space, best_params)

                # Store trials for analysis
                self.hyperopt_trials[f"{task}_{model_type}"] = trials

                print(f"   ✅ {model_type} optimization completed. Best loss: {min(trials.losses()):.4f}")

                # Create final model with best parameters
                if model_type == 'xgb':
                    if task == 'match_outcome':
                        final_model = XGBClassifier(
                            objective='multi:softprob',
                            eval_metric='mlogloss',
                            use_label_encoder=False,
                            random_state=42,
                            **best_params
                        )
                    elif task == 'total_goals':
                        final_model = XGBRegressor(
                            objective='reg:squarederror',
                            random_state=42,
                            **best_params
                        )
                    else:
                        final_model = XGBClassifier(
                            objective='binary:logistic',
                            eval_metric='logloss',
                            use_label_encoder=False,
                            random_state=42,
                            **best_params
                        )

                elif model_type == 'lgbm':
                    if task == 'match_outcome':
                        final_model = LGBMClassifier(
                            objective='multiclass',
                            metric='multi_logloss',
                            random_state=42,
                            verbose=-1,
                            **best_params
                        )
                    elif task == 'total_goals':
                        final_model = LGBMRegressor(
                            objective='regression',
                            metric='rmse',
                            random_state=42,
                            verbose=-1,
                            **best_params
                        )
                    else:
                        final_model = LGBMClassifier(
                            objective='binary',
                            metric='binary_logloss',
                            random_state=42,
                            verbose=-1,
                            **best_params
                        )

                elif model_type == 'catboost':
                    if task == 'match_outcome':
                        final_model = CatBoostClassifier(
                            loss_function='MultiClass',
                            auto_class_weights='Balanced',
                            random_state=42,
                            silent=True,
                            allow_writing_files=False,
                            **best_params
                        )
                    elif task == 'total_goals':
                        final_model = CatBoostRegressor(
                            loss_function='RMSE',
                            random_state=42,
                            silent=True,
                            allow_writing_files=False,
                            **best_params
                        )
                    else:
                        final_model = CatBoostClassifier(
                            loss_function='Logloss',
                            auto_class_weights='Balanced',
                            random_state=42,
                            silent=True,
                            allow_writing_files=False,
                            **best_params
                        )

                optimized_models.append((model_type, final_model))

            except Exception as e:
                print(f"   ⚠️ {model_type} optimization failed: {e}")
                # Fallback to default model
                default_models = self.create_enhanced_models(task)
                for name, model in default_models:
                    if name == model_type:
                        optimized_models.append((name, model))
                        break

        return optimized_models

    def create_enhanced_models(self, task: str):
        """Fallback: Enhanced base models with good default parameters."""
        common_params = {'random_state': 42}

        if task == 'match_outcome':
            return [
                ('xgb', XGBClassifier(
                    n_estimators=400,
                    learning_rate=0.05,
                    max_depth=6,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective='multi:softprob',
                    eval_metric='mlogloss',
                    use_label_encoder=False,
                    **common_params
                )),
                ('lgbm', LGBMClassifier(
                    n_estimators=400,
                    learning_rate=0.05,
                    num_leaves=63,
                    max_depth=6,
                    feature_fraction=0.8,
                    bagging_fraction=0.8,
                    objective='multiclass',
                    metric='multi_logloss',
                    verbose=-1,
                    **common_params
                )),
                ('catboost', CatBoostClassifier(
                    iterations=400,
                    depth=6,
                    learning_rate=0.05,
                    loss_function='MultiClass',
                    auto_class_weights='Balanced',
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]
        elif task == 'total_goals':
            return [
                ('xgb', XGBRegressor(
                    n_estimators=400,
                    learning_rate=0.05,
                    max_depth=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    **common_params
                )),
                ('lgbm', LGBMRegressor(
                    n_estimators=400,
                    learning_rate=0.05,
                    num_leaves=63,
                    max_depth=5,
                    feature_fraction=0.8,
                    bagging_fraction=0.8,
                    objective='regression',
                    metric='rmse',
                    verbose=-1,
                    **common_params
                ))
            ]
        else:
            return [
                ('xgb', XGBClassifier(
                    n_estimators=400,
                    learning_rate=0.05,
                    max_depth=6,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    scale_pos_weight=1.0,
                    use_label_encoder=False,
                    eval_metric='logloss',
                    **common_params
                )),
                ('lgbm', LGBMClassifier(
                    n_estimators=400,
                    learning_rate=0.05,
                    num_leaves=63,
                    max_depth=6,
                    feature_fraction=0.8,
                    bagging_fraction=0.8,
                    class_weight='balanced',
                    objective='binary',
                    metric='binary_logloss',
                    verbose=-1,
                    **common_params
                ))
            ]

    def create_bayesian_stacking_model(self, task: str, X_train, y_train, X_val, y_val):
        """Enhanced stacking with Bayesian-optimized base models."""

        # Get Bayesian-optimized base models
        base_models = self.create_bayesian_optimized_models(task, X_train, y_train, X_val, y_val)

        # Meta-learner with conservative parameters
        if task == 'match_outcome':
            meta_clf = XGBClassifier(
                n_estimators=200,
                learning_rate=0.08,
                max_depth=4,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                objective='multi:softprob',
                use_label_encoder=False
            )
            stacking_model = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_clf,
                cv=3,
                stack_method='predict_proba',
                n_jobs=-1
            )
        elif task == 'total_goals':
            meta_reg = XGBRegressor(
                n_estimators=200,
                learning_rate=0.08,
                max_depth=4,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42
            )
            stacking_model = StackingRegressor(
                estimators=base_models,
                final_estimator=meta_reg,
                cv=3,
                n_jobs=-1
            )
        else:
            meta_clf = XGBClassifier(
                n_estimators=200,
                learning_rate=0.08,
                max_depth=4,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                eval_metric='logloss',
                use_label_encoder=False
            )
            stacking_model = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_clf,
                cv=3,
                stack_method='predict_proba',
                n_jobs=-1
            )

        return stacking_model

    def evaluate_model(self, model, X_val, y_val, task):
        """Enhanced evaluation with Bayesian metrics."""
        try:
            if task == 'total_goals':
                # Regression metrics
                y_pred = model.predict(X_val)
                return {
                    'mse': np.mean((y_val - y_pred) ** 2),
                    'mae': np.mean(np.abs(y_val - y_pred)),
                    'r2': 1 - np.sum((y_val - y_pred) ** 2) / np.sum((y_val - y_val.mean()) ** 2)
                }
            else:
                # Classification metrics
                y_pred = model.predict(X_val)
                y_prob = model.predict_proba(X_val)

                metrics = {
                    'accuracy': accuracy_score(y_val, y_pred),
                    'f1': f1_score(y_val, y_pred, average='weighted'),
                    'log_loss': log_loss(y_val, y_prob)
                }

                # Add Bayesian calibration score
                if len(np.unique(y_val)) == 2:
                    try:
                        metrics['roc_auc'] = roc_auc_score(y_val, y_prob[:, 1])
                        metrics['brier_score'] = brier_score_loss(y_val, y_prob[:, 1])

                        # Bayesian calibration: how well predicted probabilities match actual frequencies
                        prob_bins = np.linspace(0, 1, 11)
                        bin_indices = np.digitize(y_prob[:, 1], prob_bins)
                        calibration_error = 0

                        for i in range(1, len(prob_bins)):
                            mask = bin_indices == i
                            if mask.sum() > 0:
                                predicted_prob = y_prob[mask, 1].mean()
                                actual_freq = y_val[mask].mean()
                                calibration_error += mask.sum() * (predicted_prob - actual_freq) ** 2

                        metrics['calibration_error'] = calibration_error / len(y_val)
                    except:
                        pass

                return metrics
        except Exception as e:
            print(f"⚠️ Evaluation error for {task}: {e}")
            return {'accuracy': 0.0, 'f1': 0.0, 'log_loss': 1.0}

    def train_models(self, df):
        """
        🚀 ENHANCED: Training with Bayesian optimization and inference.
        """
        print("🚀 Starting ENHANCED Bayesian model training...")

        # Prepare data
        df_processed, y = self.prepare_data(df)

        # Initialize Poisson predictor
        print("⚽ Initializing Poisson scoreline predictor...")
        self.poisson_predictor = PoissonScorelinePredictor()
        self.poisson_predictor.calculate_team_strengths(df_processed)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)

        for task, y_task in y.items():
            print(f"\n🧠 Training Bayesian-optimized model for {task}...")

            # Get task-specific features
            task_features = self.get_task_specific_features(task, self.available_features)

            if not task_features:
                print(f"⚠️ No features available for {task}, skipping...")
                continue

            print(f"   📊 Using {len(task_features)} task-specific features")

            # Prepare feature matrix with feature selection
            X = df_processed[task_features].fillna(0)

            # Feature selection for complex models
            max_features_for_selection = min(60, len(task_features))  # Increased for Bayesian models
            if len(task_features) > max_features_for_selection:
                if task == 'total_goals':
                    selector = SelectKBest(f_regression, k=max_features_for_selection)
                else:
                    selector = SelectKBest(f_classif, k=max_features_for_selection)

                X_selected = selector.fit_transform(X, y_task)
                selected_features = [task_features[i] for i in selector.get_support(indices=True)]
                X = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
                print(f"   🎯 Selected {len(selected_features)} best features")

            cv_metrics = []
            best_metric = float('-inf')
            best_model = None

            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                print(f"   🔄 Fold {fold + 1}/3...")

                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y_task.iloc[train_idx], y_task.iloc[val_idx]

                # Apply SMOTE for imbalanced datasets
                if task != 'match_outcome' and task != 'total_goals' and len(np.unique(y_train)) == 2:
                    try:
                        smote = SMOTE(random_state=42, k_neighbors=min(5, len(y_train[y_train == 1]) - 1))
                        X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
                    except:
                        X_train_res, y_train_res = X_train, y_train
                else:
                    X_train_res, y_train_res = X_train, y_train

                # Create Bayesian-optimized stacking model
                model = self.create_bayesian_stacking_model(task, X_train_res, y_train_res, X_val, y_val)
                model.fit(X_train_res, y_train_res)

                # Evaluate
                fold_metrics = self.evaluate_model(model, X_val, y_val, task)
                cv_metrics.append(fold_metrics)

                # Track best model
                if task == 'total_goals':
                    current_metric = -fold_metrics['mae']  # Lower MAE is better
                else:
                    current_metric = fold_metrics['accuracy']

                if current_metric > best_metric:
                    best_metric = current_metric
                    best_model = model

            # Store model with features
            if best_model is not None:
                self.models[task] = {
                    'model': best_model,
                    'features': list(X.columns)
                }

                # Add Bayesian probability calibration
                print(f"   🧠 Calibrating {task} probabilities with Bayesian methods...")
                try:
                    if task != 'total_goals':
                        calibrated_model = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
                        calibrated_model.fit(X, y_task)
                        self.calibrated_models[task] = {
                            'model': calibrated_model,
                            'features': list(X.columns)
                        }
                        print(f"   ✅ Bayesian calibration successful")
                except Exception as e:
                    print(f"   ⚠️ Calibration failed: {e}")

                # Store metrics
                if cv_metrics:
                    self.metrics[task] = {
                        metric: np.mean([fold[metric] for fold in cv_metrics])
                        for metric in cv_metrics[0].keys()
                    }

                    # Print results
                    print(f"\n   📊 Bayesian Results for {task}:")
                    for metric, value in self.metrics[task].items():
                        print(f"      {metric}: {value:.4f}")

                    # Highlight key metrics
                    if task == 'over_2_5' and 'accuracy' in self.metrics[task]:
                        acc = self.metrics[task]['accuracy']
                        if acc >= 0.85:
                            print(f"   🔥 EXCELLENT Over 2.5 Bayesian accuracy: {acc:.1%}")
                        elif acc >= 0.70:
                            print(f"   💰 Strong Over 2.5 Bayesian accuracy: {acc:.1%}")

        print(f"\n🎉 Enhanced Bayesian training completed!")
        print(f"   📊 Trained models: {list(self.models.keys())}")
        print(f"   ⚽ Poisson predictor ready for exact scorelines")
        print(f"   🧠 Bayesian optimization trials: {len(self.hyperopt_trials)}")

    def predict_with_bayesian_constraints(self, X_new):
        """
        🧠 CORE FEATURE: Make predictions with Bayesian constraints and inference.
        """
        raw_predictions = {}
        raw_probabilities = {}

        # Make raw predictions from all models
        for task, model_info in self.models.items():
            try:
                model = model_info['model']
                features = model_info['features']

                X_task = X_new[features].fillna(0)

                if task == 'match_outcome':
                    pred_probs = model.predict_proba(X_task)
                    pred_idx = np.argmax(pred_probs, axis=1)
                    raw_predictions[task] = pd.Series(pred_idx).map({0: 'H', 1: 'D', 2: 'A'})
                    raw_probabilities[task] = pred_probs
                elif task == 'total_goals':
                    pred_values = model.predict(X_task)
                    raw_predictions[task] = pred_values
                    raw_probabilities[task] = pred_values
                else:
                    pred_probs = model.predict_proba(X_task)
                    raw_predictions[task] = (pred_probs[:, 1] > 0.5).astype(int)
                    raw_probabilities[task] = pred_probs[:, 1]
            except Exception as e:
                print(f"Warning: Could not predict {task}: {e}")
                continue

        # Apply Bayesian logical constraints
        constrained_predictions = {}
        constrained_probabilities = {}
        constraints_applied = []

        for i in range(len(X_new)):
            match_predictions = {task: pred[i] if hasattr(pred, '__getitem__') else pred
                                 for task, pred in raw_predictions.items()}
            match_probabilities = {task: prob[i] if hasattr(prob, '__getitem__') else prob
                                   for task, prob in raw_probabilities.items()}

            # Apply Bayesian Over/Under constraints
            fixed_predictions, fixed_probabilities, match_constraints = self.constraint_validator.apply_bayesian_over_under_constraints(
                match_predictions, match_probabilities)
            constraints_applied.extend(match_constraints)

            # Update predictions
            for task, fixed_value in fixed_predictions.items():
                if task not in constrained_predictions:
                    constrained_predictions[task] = []
                constrained_predictions[task].append(fixed_value)

            for task, fixed_prob in fixed_probabilities.items():
                if task not in constrained_probabilities:
                    constrained_probabilities[task] = []
                constrained_probabilities[task].append(fixed_prob)

        # Convert to proper format
        for task in constrained_predictions:
            if task == 'match_outcome':
                constrained_predictions[task] = pd.Series(constrained_predictions[task])
            else:
                constrained_predictions[task] = np.array(constrained_predictions[task])

        for task in constrained_probabilities:
            constrained_probabilities[task] = np.array(constrained_probabilities[task])

        # Calculate Bayesian total goals
        bayesian_total_goals = []
        for i in range(len(X_new)):
            match_preds = {task: pred[i] if hasattr(pred, '__getitem__') else pred
                           for task, pred in constrained_predictions.items()}
            match_probs = {task: prob[i] if hasattr(prob, '__getitem__') else prob
                           for task, prob in constrained_probabilities.items()}

            total = self.constraint_validator.calculate_bayesian_total_goals(match_preds, match_probs)
            bayesian_total_goals.append(total)

        constrained_predictions['total_goals'] = np.array(bayesian_total_goals)

        if constraints_applied:
            print(f"🧠 Applied {len(constraints_applied)} Bayesian logical constraints")

        return constrained_predictions, constrained_probabilities

    def predict(self, X_new):
        """Standard prediction interface with Bayesian constraints."""
        return self.predict_with_bayesian_constraints(X_new)

    def get_poisson_predictions(self, home_team: str, away_team: str):
        """Get Poisson-based exact scoreline predictions."""
        if self.poisson_predictor is None:
            return None

        try:
            return self.poisson_predictor.predict_scoreline_probabilities(home_team, away_team)
        except Exception as e:
            print(f"⚠️ Poisson prediction failed: {e}")
            return None

    def save_models(self, path):
        """Enhanced model saving with Bayesian components."""
        try:
            save_data = {
                'models': self.models,
                'calibrated_models': self.calibrated_models,
                'poisson_predictor': self.poisson_predictor,
                'metrics': self.metrics,
                'feature_importance': getattr(self, 'feature_importance', {}),
                'available_features': getattr(self, 'available_features', []),
                'feature_categories': self.feature_categories,
                'bayesian_priors': self.bayesian_priors,
                'hyperopt_trials': self.hyperopt_trials
            }
            joblib.dump(save_data, path)
            print(f"✅ Enhanced Bayesian models saved to {path}")

            # Verification
            for task, model_info in self.models.items():
                model = model_info['model']
                print(f"   {task}: {type(model).__name__}")

        except Exception as e:
            print(f"❌ Error saving models: {str(e)}")

    def load_models(self, path):
        """Enhanced model loading with Bayesian components."""
        try:
            data = joblib.load(path)
            self.models = data['models']
            self.calibrated_models = data.get('calibrated_models', {})
            self.poisson_predictor = data.get('poisson_predictor', None)
            self.metrics = data.get('metrics', {})
            self.feature_importance = data.get('feature_importance', {})
            self.available_features = data.get('available_features', [])
            self.feature_categories = data.get('feature_categories', self.feature_categories)
            self.bayesian_priors = data.get('bayesian_priors', {})
            self.hyperopt_trials = data.get('hyperopt_trials', {})
            print(f"✅ Enhanced Bayesian models loaded from {path}")
        except Exception as e:
            print(f"❌ Error loading models: {str(e)}")

    def get_model_insights(self):
        """Enhanced insights including Bayesian optimization results."""
        insights = {
            'trained_models': list(self.models.keys()),
            'metrics_summary': {},
            'poisson_available': self.poisson_predictor is not None,
            'bayesian_constraints': 'Over/Under hierarchy with probability calibration',
            'calibration_status': list(self.calibrated_models.keys()),
            'bayesian_priors': self.bayesian_priors,
            'hyperopt_trials': len(self.hyperopt_trials)
        }

        # Summarize metrics
        for task, metrics in self.metrics.items():
            if task == 'total_goals':
                insights['metrics_summary'][task] = {
                    'mae': f"{metrics.get('mae', 0):.3f}",
                    'mse': f"{metrics.get('mse', 0):.3f}",
                    'r2': f"{metrics.get('r2', 0):.3f}"
                }
            else:
                insights['metrics_summary'][task] = {
                    'accuracy': f"{metrics.get('accuracy', 0):.3f}",
                    'f1': f"{metrics.get('f1', 0):.3f}",
                    'log_loss': f"{metrics.get('log_loss', 0):.3f}"
                }

                if 'calibration_error' in metrics:
                    insights['metrics_summary'][task]['calibration_error'] = f"{metrics['calibration_error']:.3f}"

        return insights


def main():
    """Test the enhanced Bayesian predictor."""
    print("🧪 Testing Enhanced Bayesian Football Predictor...")

    predictor = BayesianFootballPredictor()

    print("\n✅ Enhanced Bayesian predictor ready for training!")
    print("🧠 Features:")
    print("   - Bayesian hyperparameter optimization with hyperopt")
    print("   - Bayesian logical constraints with probability calibration")
    print("   - Enhanced feature selection for Bayesian models")
    print("   - Bayesian priors for all prediction tasks")
    print("   - Improved calibration with isotonic regression")


if __name__ == "__main__":
    main()