# footy/model_training.py - ENHANCED WITH LOGICAL CONSTRAINTS & POISSON

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score, log_loss, \
    brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_selection import SelectKBest, f_classif, f_regression
from xgboost import XGBClassifier, XGBRegressor
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, StackingClassifier, StackingRegressor
from imblearn.over_sampling import SMOTE
import warnings
import joblib

# Import Poisson predictor
from footy.poisson_predictor import PoissonScorelinePredictor

warnings.filterwarnings('ignore')


class LogicalConstraintValidator:
    """Validates and fixes logical constraints in predictions."""

    @staticmethod
    def apply_over_under_constraints(predictions: dict) -> dict:
        """
        🎯 CORE FIX: Apply logical constraints to Over/Under predictions.
        Prevents impossible combinations like "Over 1.5 No, Over 2.5 Yes"
        """
        fixed_predictions = predictions.copy()

        # Get Over/Under predictions
        over_1_5 = predictions.get('over_1_5', None)
        over_2_5 = predictions.get('over_2_5', None)
        over_3_5 = predictions.get('over_3_5', None)

        constraints_applied = []

        # Rule 1: If Over 3.5 = Yes → Over 2.5 = Yes → Over 1.5 = Yes
        if over_3_5 == 1 and over_2_5 == 0:
            fixed_predictions['over_2_5'] = 1
            constraints_applied.append("Rule 1a: Over 3.5 Yes → Over 2.5 Yes")

        if over_3_5 == 1 and over_1_5 == 0:
            fixed_predictions['over_1_5'] = 1
            constraints_applied.append("Rule 1b: Over 3.5 Yes → Over 1.5 Yes")

        if over_2_5 == 1 and over_1_5 == 0:
            fixed_predictions['over_1_5'] = 1
            constraints_applied.append("Rule 1c: Over 2.5 Yes → Over 1.5 Yes")

        # Rule 2: If Over 1.5 = No → Over 2.5 = No → Over 3.5 = No
        if over_1_5 == 0 and over_2_5 == 1:
            fixed_predictions['over_2_5'] = 0
            constraints_applied.append("Rule 2a: Over 1.5 No → Over 2.5 No")

        if over_1_5 == 0 and over_3_5 == 1:
            fixed_predictions['over_3_5'] = 0
            constraints_applied.append("Rule 2b: Over 1.5 No → Over 3.5 No")

        if over_2_5 == 0 and over_3_5 == 1:
            fixed_predictions['over_3_5'] = 0
            constraints_applied.append("Rule 2c: Over 2.5 No → Over 3.5 No")

        return fixed_predictions, constraints_applied

    @staticmethod
    def calculate_logical_total_goals(predictions: dict) -> float:
        """
        Calculate realistic total goals from Over/Under predictions.
        """
        over_1_5 = predictions.get('over_1_5', 0)
        over_2_5 = predictions.get('over_2_5', 0)
        over_3_5 = predictions.get('over_3_5', 0)

        # Logic-based total goals calculation
        if over_3_5 == 1:
            return 4.2  # Likely 4+ goals
        elif over_2_5 == 1:
            return 3.1  # Likely 3 goals
        elif over_1_5 == 1:
            return 2.3  # Likely 2 goals
        else:
            return 1.1  # Likely 0-1 goals

    @staticmethod
    def validate_predictions(predictions: dict) -> tuple:
        """
        Validate all predictions for logical consistency.
        """
        issues = []

        # Check Over/Under logic
        over_1_5 = predictions.get('over_1_5', None)
        over_2_5 = predictions.get('over_2_5', None)
        over_3_5 = predictions.get('over_3_5', None)

        if over_1_5 == 0 and over_2_5 == 1:
            issues.append("Impossible: Over 1.5 No + Over 2.5 Yes")
        if over_2_5 == 0 and over_3_5 == 1:
            issues.append("Impossible: Over 2.5 No + Over 3.5 Yes")
        if over_1_5 == 0 and over_3_5 == 1:
            issues.append("Impossible: Over 1.5 No + Over 3.5 Yes")

        is_valid = len(issues) == 0
        return is_valid, issues


class FootballPredictor:
    """Enhanced Football Predictor with logical constraints and Poisson integration."""

    def __init__(self):
        self.models = {}
        self.calibrated_models = {}
        self.poisson_predictor = None
        self.metrics = {}
        self.feature_importance = {}
        self.constraint_validator = LogicalConstraintValidator()

        # 🎯 ENHANCED: Better feature categorization
        self.feature_categories = {
            'core_features': [
                'HomeTeam_encoded', 'AwayTeam_encoded'
            ],
            'elo_features': [
                'HomeElo', 'AwayElo', 'EloAdvantage'
            ],
            'form_features': [
                'HomeForm_3', 'HomeForm_5', 'HomeForm_10',
                'AwayForm_3', 'AwayForm_5', 'AwayForm_10'
            ],
            'goal_features': [
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
                'AwayOverRate3.5_3', 'AwayOverRate3.5_5', 'AwayOverRate3.5_10'
            ],
            'shot_features': [
                'HomeShotAccuracy', 'AwayShotAccuracy', 'HomeGoalConversion', 'AwayGoalConversion',
                'HomexG', 'AwayxG', 'HomeShotPressure', 'AwayShotPressure'
            ],
            'h2h_features': [
                'H2H_HomeWinRate', 'H2H_AvgGoals', 'H2H_BTTSRate', 'H2H_RecentForm', 'H2H_GoalTrend'
            ],
            'referee_features': [
                'RefAvgGoals', 'RefHomeBias', 'RefCardTendency', 'RefOver25Rate'
            ],
            'context_features': [
                'SeasonProgress', 'HomeDaysRest', 'AwayDaysRest', 'IsEarlySeason',
                'MatchDensity', 'DayOfWeek', 'Month', 'IsWeekend'
            ],
            'strength_features': [
                'HomeAttackStrength', 'AwayAttackStrength', 'HomeDefenseStrength', 'AwayDefenseStrength',
                'HomeFormMomentum', 'AwayFormMomentum', 'CombinedGoalPotential', 'DefensiveStruggle'
            ],
            'gw1_features': [
                'HomeGW1ScoringHistory', 'AwayGW1ScoringHistory', 'HomeGW1FormHistory',
                'AwayGW1FormHistory', 'PromotedTeamEarlyBonus'
            ]
        }

    def get_task_specific_features(self, task: str, available_features: list) -> list:
        """
        🎯 ENHANCED: Optimized feature selection for each prediction task.
        """
        # Start with core features that should always be included
        base_features = []
        for category in ['core_features', 'elo_features', 'form_features']:
            base_features.extend([f for f in self.feature_categories[category] if f in available_features])

        if task == 'match_outcome':
            # Match outcome benefits from team strength and form
            additional_categories = ['h2h_features', 'context_features', 'strength_features']

        elif task in ['over_1_5', 'over_2_5', 'over_3_5']:
            # Over/Under predictions benefit from goal-specific features
            additional_categories = ['goal_features', 'over_under_features', 'referee_features', 'shot_features']

        elif task == 'btts':
            # BTTS benefits from attack patterns and H2H
            additional_categories = ['goal_features', 'shot_features', 'h2h_features']

        elif task == 'total_goals':
            # Total goals uses all goal-related features
            additional_categories = ['goal_features', 'over_under_features', 'shot_features', 'referee_features']

        else:
            # Default: use most relevant features
            additional_categories = ['goal_features', 'context_features']

        # Add task-specific features
        task_features = base_features.copy()
        for category in additional_categories:
            task_features.extend([f for f in self.feature_categories[category] if f in available_features])

        # Add GW1 features for early season boost
        task_features.extend([f for f in self.feature_categories['gw1_features'] if f in available_features])

        # Remove duplicates and limit to reasonable number
        task_features = list(set(task_features))

        # 🔧 IMPORTANT: Limit features to prevent overfitting
        max_features = min(50, len(task_features))  # Max 50 features per task
        if len(task_features) > max_features:
            # Keep most important feature categories
            priority_features = base_features + [f for f in task_features if
                                                 any(cat in f.lower() for cat in ['elo', 'form', 'scoring', 'over'])]
            task_features = list(set(priority_features))[:max_features]

        return task_features

    def prepare_data(self, df):
        """Enhanced data preparation with better target creation."""
        df = df.sort_values('Date').copy()

        print("🔍 Analyzing available features...")
        available_features = df.columns.tolist()

        # Find which enhanced features exist
        all_possible_features = []
        for category, features in self.feature_categories.items():
            all_possible_features.extend(features)

        existing_features = [f for f in all_possible_features if f in available_features]
        print(f"✅ Found {len(existing_features)} enhanced features")

        self.available_features = existing_features

        # 🎯 ENHANCED: Better target preparation
        y = {}

        # Match outcome
        if 'FTR' in df.columns:
            y['match_outcome'] = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})

        # Over/Under targets with consistent naming
        if 'TotalGoals' in df.columns:
            y['over_1_5'] = (df['TotalGoals'] > 1.5).astype(int)
            y['over_2_5'] = (df['TotalGoals'] > 2.5).astype(int)
            y['over_3_5'] = (df['TotalGoals'] > 3.5).astype(int)  # 🎯 Key for your accuracy
            y['total_goals'] = df['TotalGoals']
        elif 'Over1.5' in df.columns:
            y['over_1_5'] = df['Over1.5']
            y['over_2_5'] = df['Over2.5'] if 'Over2.5' in df.columns else (df['TotalGoals'] > 2.5).astype(int)
            y['over_3_5'] = df['Over3.5'] if 'Over3.5' in df.columns else (df['TotalGoals'] > 3.5).astype(int)

        # BTTS
        if 'BTTS' in df.columns:
            y['btts'] = df['BTTS']
        elif 'FTHG' in df.columns and 'FTAG' in df.columns:
            y['btts'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)

        print(f"📊 Prepared targets: {list(y.keys())}")
        return df, y

    def create_enhanced_models(self, task: str):
        """Enhanced base models with better parameters."""
        common_params = {'random_state': 42}

        if task == 'match_outcome':
            # 3-way classification
            return [
                ('xgb', XGBClassifier(
                    n_estimators=300,  # 🔧 Reduced to prevent overfitting
                    learning_rate=0.05,
                    max_depth=5,  # 🔧 Shallower trees
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective='multi:softprob',
                    eval_metric='mlogloss',
                    use_label_encoder=False,
                    **common_params
                )),
                ('rf', RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,  # 🔧 Controlled depth
                    min_samples_split=10,  # 🔧 More conservative
                    min_samples_leaf=5,
                    class_weight='balanced',
                    **common_params
                )),
                ('cat', CatBoostClassifier(
                    iterations=300,
                    depth=5,  # 🔧 Shallower
                    learning_rate=0.05,
                    loss_function='MultiClass',
                    auto_class_weights='Balanced',
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]
        elif task == 'total_goals':
            # Regression
            return [
                ('xgb', XGBRegressor(
                    n_estimators=300,
                    learning_rate=0.05,
                    max_depth=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    **common_params
                )),
                ('rf', RandomForestRegressor(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    **common_params
                )),
                ('cat', CatBoostRegressor(
                    iterations=300,
                    depth=5,
                    learning_rate=0.05,
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]
        else:
            # Binary classification
            return [
                ('xgb', XGBClassifier(
                    n_estimators=300,
                    learning_rate=0.05,
                    max_depth=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    scale_pos_weight=1.0,  # 🔧 Balanced
                    use_label_encoder=False,
                    eval_metric='logloss',
                    **common_params
                )),
                ('rf', RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    class_weight='balanced',
                    **common_params
                )),
                ('cat', CatBoostClassifier(
                    iterations=300,
                    depth=5,
                    learning_rate=0.05,
                    auto_class_weights='Balanced',
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]

    def create_stacking_model(self, task: str, X_train, y_train):
        """Enhanced stacking with logical constraints consideration."""
        base_models = self.create_enhanced_models(task)

        # Meta-learner with conservative parameters
        if task == 'match_outcome':
            meta_clf = XGBClassifier(
                n_estimators=150,  # 🔧 Reduced
                learning_rate=0.08,
                max_depth=3,  # 🔧 Shallow meta-learner
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                objective='multi:softprob',
                use_label_encoder=False
            )
            stacking_model = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_clf,
                cv=3,  # 🔧 Reduced CV folds
                stack_method='predict_proba',
                n_jobs=-1
            )
        elif task == 'total_goals':
            meta_reg = XGBRegressor(
                n_estimators=150,
                learning_rate=0.08,
                max_depth=3,
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
                n_estimators=150,
                learning_rate=0.08,
                max_depth=3,
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
        """Enhanced evaluation with logical constraint checking."""
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

                # Binary classification specific metrics
                if task != 'match_outcome' and len(np.unique(y_val)) == 2:
                    try:
                        metrics['roc_auc'] = roc_auc_score(y_val, y_prob[:, 1])
                        metrics['brier_score'] = brier_score_loss(y_val, y_prob[:, 1])
                    except:
                        pass

                return metrics
        except Exception as e:
            print(f"⚠️ Evaluation error for {task}: {e}")
            return {'accuracy': 0.0, 'f1': 0.0, 'log_loss': 1.0}

    def train_models(self, df):
        """🚀 ENHANCED: Training with logical constraints and Poisson integration."""
        print("🚀 Starting ENHANCED model training with logical constraints...")

        # Prepare data
        df_processed, y = self.prepare_data(df)

        # 🎯 NEW: Initialize Poisson predictor
        print("⚽ Initializing Poisson scoreline predictor...")
        self.poisson_predictor = PoissonScorelinePredictor()
        self.poisson_predictor.calculate_team_strengths(df_processed)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)  # 🔧 Reduced for faster training

        for task, y_task in y.items():
            print(f"\n📈 Training enhanced model for {task}...")

            # Get task-specific features
            task_features = self.get_task_specific_features(task, self.available_features)

            if not task_features:
                print(f"⚠️ No features available for {task}, skipping...")
                continue

            print(f"   📊 Using {len(task_features)} task-specific features")

            # Prepare feature matrix with feature selection
            X = df_processed[task_features].fillna(0)

            # 🔧 Feature selection to prevent overfitting
            max_features_for_selection = min(30, len(task_features))
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
                print(f"   📄 Fold {fold + 1}/3...")

                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y_task.iloc[train_idx], y_task.iloc[val_idx]

                # Apply SMOTE only for imbalanced binary classification
                if task != 'match_outcome' and task != 'total_goals' and len(np.unique(y_train)) == 2:
                    try:
                        smote = SMOTE(random_state=42, k_neighbors=min(5, len(y_train[y_train == 1]) - 1))
                        X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
                    except:
                        X_train_res, y_train_res = X_train, y_train
                else:
                    X_train_res, y_train_res = X_train, y_train

                # Create and train model
                model = self.create_stacking_model(task, X_train_res, y_train_res)
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

                # 🎯 Add probability calibration
                print(f"   🔧 Calibrating {task} probabilities...")
                try:
                    if task != 'total_goals':
                        calibrated_model = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
                        calibrated_model.fit(X, y_task)
                        self.calibrated_models[task] = {
                            'model': calibrated_model,
                            'features': list(X.columns)
                        }
                        print(f"   ✅ Calibration successful")
                except Exception as e:
                    print(f"   ⚠️ Calibration failed: {e}")

                # Store metrics
                if cv_metrics:
                    self.metrics[task] = {
                        metric: np.mean([fold[metric] for fold in cv_metrics])
                        for metric in cv_metrics[0].keys()
                    }

                    # Print results
                    print(f"\n   📊 Results for {task}:")
                    for metric, value in self.metrics[task].items():
                        print(f"      {metric}: {value:.4f}")

                    # 🎯 Highlight key metrics
                    if task == 'over_2_5' and 'accuracy' in self.metrics[task]:
                        acc = self.metrics[task]['accuracy']
                        if acc >= 0.90:
                            print(f"   🔥 EXCELLENT Over 2.5 accuracy: {acc:.1%}")
                        elif acc >= 0.75:
                            print(f"   💰 Strong Over 2.5 accuracy: {acc:.1%}")

        print(f"\n🎉 Enhanced training completed!")
        print(f"   📊 Trained models: {list(self.models.keys())}")
        print(f"   ⚽ Poisson predictor ready for exact scorelines")

    def predict_with_logical_constraints(self, X_new):
        """
        🎯 CORE FEATURE: Make predictions with logical constraints applied.
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
                    raw_probabilities[task] = pred_values  # No probabilities for regression
                else:
                    pred_probs = model.predict_proba(X_task)
                    raw_predictions[task] = (pred_probs[:, 1] > 0.5).astype(int)
                    raw_probabilities[task] = pred_probs[:, 1]
            except Exception as e:
                print(f"Warning: Could not predict {task}: {e}")
                continue

        # 🎯 Apply logical constraints
        constrained_predictions = {}
        constraints_applied = []

        for i in range(len(X_new)):
            match_predictions = {task: pred[i] if hasattr(pred, '__getitem__') else pred
                                 for task, pred in raw_predictions.items()}

            # Apply Over/Under constraints
            fixed_predictions, match_constraints = self.constraint_validator.apply_over_under_constraints(
                match_predictions)
            constraints_applied.extend(match_constraints)

            # Update predictions
            for task, fixed_value in fixed_predictions.items():
                if task not in constrained_predictions:
                    constrained_predictions[task] = []
                constrained_predictions[task].append(fixed_value)

        # Convert to proper format
        for task in constrained_predictions:
            if task == 'match_outcome':
                constrained_predictions[task] = pd.Series(constrained_predictions[task])
            else:
                constrained_predictions[task] = np.array(constrained_predictions[task])

        # Calculate logical total goals
        logical_total_goals = []
        for i in range(len(X_new)):
            match_preds = {task: pred[i] if hasattr(pred, '__getitem__') else pred
                           for task, pred in constrained_predictions.items()}
            total = self.constraint_validator.calculate_logical_total_goals(match_preds)
            logical_total_goals.append(total)

        constrained_predictions['total_goals'] = np.array(logical_total_goals)

        if constraints_applied:
            print(f"🔧 Applied {len(constraints_applied)} logical constraints")

        return constrained_predictions, raw_probabilities

    def predict(self, X_new):
        """Standard prediction interface with logical constraints."""
        return self.predict_with_logical_constraints(X_new)

    def get_poisson_predictions(self, home_team: str, away_team: str):
        """
        🎯 NEW: Get Poisson-based exact scoreline predictions.
        """
        if self.poisson_predictor is None:
            return None

        try:
            return self.poisson_predictor.predict_scoreline_probabilities(home_team, away_team)
        except Exception as e:
            print(f"⚠️ Poisson prediction failed: {e}")
            return None

    def save_models(self, path):
        """Enhanced model saving with Poisson predictor."""
        try:
            save_data = {
                'models': self.models,
                'calibrated_models': self.calibrated_models,
                'poisson_predictor': self.poisson_predictor,
                'metrics': self.metrics,
                'feature_importance': getattr(self, 'feature_importance', {}),
                'available_features': getattr(self, 'available_features', []),
                'feature_categories': self.feature_categories
            }
            joblib.dump(save_data, path)
            print(f"✅ Enhanced models with Poisson predictor saved to {path}")

            # Verification
            for task, model_info in self.models.items():
                model = model_info['model']
                print(f"   {task}: {type(model).__name__}")

        except Exception as e:
            print(f"❌ Error saving models: {str(e)}")

    def load_models(self, path):
        """Enhanced model loading with Poisson predictor."""
        try:
            data = joblib.load(path)
            self.models = data['models']
            self.calibrated_models = data.get('calibrated_models', {})
            self.poisson_predictor = data.get('poisson_predictor', None)
            self.metrics = data.get('metrics', {})
            self.feature_importance = data.get('feature_importance', {})
            self.available_features = data.get('available_features', [])
            self.feature_categories = data.get('feature_categories', self.feature_categories)
            print(f"✅ Enhanced models with Poisson predictor loaded from {path}")
        except Exception as e:
            print(f"❌ Error loading models: {str(e)}")

    def validate_predictions_batch(self, predictions_dict):
        """
        🎯 Validate a batch of predictions for logical consistency.
        """
        validation_results = []

        for i in range(len(list(predictions_dict.values())[0])):
            match_preds = {task: pred[i] if hasattr(pred, '__getitem__') else pred
                           for task, pred in predictions_dict.items()}

            is_valid, issues = self.constraint_validator.validate_predictions(match_preds)
            validation_results.append({
                'valid': is_valid,
                'issues': issues,
                'predictions': match_preds
            })

        return validation_results

    def get_model_insights(self):
        """Enhanced insights including Poisson and constraint info."""
        insights = {
            'trained_models': list(self.models.keys()),
            'metrics_summary': {},
            'poisson_available': self.poisson_predictor is not None,
            'logical_constraints': 'Over/Under hierarchy enforced',
            'calibration_status': list(self.calibrated_models.keys())
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

        return insights

    def test_logical_constraints(self):
        """
        🧪 Test the logical constraint system.
        """
        print("🧪 Testing logical constraint system...")

        # Test cases
        test_cases = [
            {'over_1_5': 0, 'over_2_5': 1, 'over_3_5': 0},  # Should fix over_2_5 to 0
            {'over_1_5': 1, 'over_2_5': 0, 'over_3_5': 1},  # Should fix over_3_5 to 0
            {'over_1_5': 1, 'over_2_5': 1, 'over_3_5': 1},  # Should remain unchanged
            {'over_1_5': 0, 'over_2_5': 0, 'over_3_5': 0},  # Should remain unchanged
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {test_case}")
            fixed, constraints = self.constraint_validator.apply_over_under_constraints(test_case)
            print(f"   Fixed: {fixed}")
            if constraints:
                print(f"   Applied: {constraints}")

            is_valid, issues = self.constraint_validator.validate_predictions(fixed)
            print(f"   Valid: {is_valid}")
            if not is_valid:
                print(f"   Issues: {issues}")

        print("✅ Constraint testing completed")


def main():
    """Test the enhanced predictor."""
    print("🧪 Testing Enhanced Football Predictor...")

    predictor = FootballPredictor()

    # Test constraint system
    predictor.test_logical_constraints()

    print("\n✅ Enhanced predictor ready for training!")


if __name__ == "__main__":
    main()