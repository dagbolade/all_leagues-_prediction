"""
Advanced Basketball Model Training - Matching Football Sophistication
Uses XGBoost, CatBoost, LightGBM with Bayesian Hyperparameter Optimization
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, log_loss, mean_squared_error
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_selection import SelectKBest, f_classif, f_regression
from xgboost import XGBClassifier, XGBRegressor
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import StackingClassifier, StackingRegressor
from imblearn.over_sampling import SMOTE
import warnings
import joblib
from typing import Dict, List, Tuple, Optional, Any

# Bayesian Hyperparameter Optimization
try:
    from hyperopt import fmin, tpe, hp, STATUS_OK, Trials, space_eval
    from hyperopt.early_stop import no_progress_loss
    HYPEROPT_AVAILABLE = True
except ImportError:
    print("⚠️ hyperopt not available. Install with: pip install hyperopt")
    HYPEROPT_AVAILABLE = False

warnings.filterwarnings('ignore')


class AdvancedBasketballPredictor:
    """Advanced NBA predictor with Bayesian optimization and ensemble methods."""

    def __init__(self):
        self.models = {}
        self.calibrated_models = {}
        self.metrics = {}
        self.feature_importance = {}
        self.hyperopt_trials = {}
        self.bayesian_priors = {}

    def get_bayesian_search_space(self, task: str) -> Dict:
        """Define Bayesian optimization search spaces."""

        if task == 'match_outcome':  # Winner prediction
            return {
                'xgb': {
                    'n_estimators': hp.choice('n_estimators', [300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7, 8]),
                    'subsample': hp.uniform('subsample', 0.6, 1.0),
                    'colsample_bytree': hp.uniform('colsample_bytree', 0.6, 1.0),
                    'reg_alpha': hp.uniform('reg_alpha', 0, 1),
                    'reg_lambda': hp.uniform('reg_lambda', 0, 2),
                },
                'lgbm': {
                    'n_estimators': hp.choice('n_estimators', [300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'num_leaves': hp.choice('num_leaves', [31, 63, 127, 255]),
                    'max_depth': hp.choice('max_depth', [4, 5, 6, 7, 8]),
                    'feature_fraction': hp.uniform('feature_fraction', 0.6, 1.0),
                    'bagging_fraction': hp.uniform('bagging_fraction', 0.6, 1.0),
                },
                'catboost': {
                    'iterations': hp.choice('iterations', [300, 500, 700]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                    'depth': hp.choice('depth', [4, 5, 6, 7, 8]),
                    'l2_leaf_reg': hp.uniform('l2_leaf_reg', 1, 10),
                }
            }
        else:  # Regression or binary tasks
            return {
                'xgb': {
                    'n_estimators': hp.choice('n_estimators', [300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.15),
                    'max_depth': hp.choice('max_depth', [3, 4, 5, 6]),
                    'subsample': hp.uniform('subsample', 0.7, 1.0),
                    'colsample_bytree': hp.uniform('colsample_bytree', 0.7, 1.0),
                },
                'lgbm': {
                    'n_estimators': hp.choice('n_estimators', [300, 500]),
                    'learning_rate': hp.uniform('learning_rate', 0.01, 0.15),
                    'num_leaves': hp.choice('num_leaves', [31, 63, 127]),
                    'max_depth': hp.choice('max_depth', [3, 4, 5, 6]),
                }
            }

    def bayesian_objective(self, params: Dict, X_train, y_train, X_val, y_val,
                           model_type: str, task: str) -> Dict:
        """Objective function for Bayesian optimization."""
        try:
            if model_type == 'xgb':
                if task == 'total_points':
                    model = XGBRegressor(random_state=42, **params)
                else:
                    model = XGBClassifier(
                        eval_metric='logloss',
                        use_label_encoder=False,
                        random_state=42,
                        **params
                    )
            elif model_type == 'lgbm':
                if task == 'total_points':
                    model = LGBMRegressor(random_state=42, verbose=-1, **params)
                else:
                    model = LGBMClassifier(random_state=42, verbose=-1, **params)
            elif model_type == 'catboost':
                if task == 'total_points':
                    model = CatBoostRegressor(
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **params
                    )
                else:
                    model = CatBoostClassifier(
                        auto_class_weights='Balanced',
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **params
                    )

            model.fit(X_train, y_train)

            if task == 'total_points':
                y_pred = model.predict(X_val)
                loss = mean_squared_error(y_val, y_pred)
            else:
                y_pred_proba = model.predict_proba(X_val)
                loss = log_loss(y_val, y_pred_proba)

            return {'loss': loss, 'status': STATUS_OK}

        except Exception as e:
            return {'loss': float('inf'), 'status': STATUS_OK}

    def create_bayesian_optimized_models(self, task: str, X_train, y_train, X_val, y_val):
        """Create models with Bayesian hyperparameter optimization."""

        if not HYPEROPT_AVAILABLE:
            print("⚠️ Using default parameters (hyperopt not available)")
            return self.create_default_models(task)

        print(f"🧠 Bayesian optimization for {task}...")

        search_spaces = self.get_bayesian_search_space(task)
        optimized_models = []

        for model_type, space in search_spaces.items():
            print(f"   🔍 Optimizing {model_type}...")

            trials = Trials()

            def objective(params):
                return self.bayesian_objective(params, X_train, y_train, X_val, y_val, model_type, task)

            try:
                best_params = fmin(
                    fn=objective,
                    space=space,
                    algo=tpe.suggest,
                    max_evals=15,  # Reduced for speed
                    trials=trials,
                    verbose=False
                )

                best_params = space_eval(space, best_params)
                self.hyperopt_trials[f"{task}_{model_type}"] = trials

                print(f"   ✅ {model_type} best loss: {min(trials.losses()):.4f}")

                # Create final model
                if model_type == 'xgb':
                    if task == 'total_points':
                        final_model = XGBRegressor(random_state=42, **best_params)
                    else:
                        final_model = XGBClassifier(
                            eval_metric='logloss',
                            use_label_encoder=False,
                            random_state=42,
                            **best_params
                        )
                elif model_type == 'lgbm':
                    if task == 'total_points':
                        final_model = LGBMRegressor(random_state=42, verbose=-1, **best_params)
                    else:
                        final_model = LGBMClassifier(random_state=42, verbose=-1, **best_params)
                elif model_type == 'catboost':
                    if task == 'total_points':
                        final_model = CatBoostRegressor(
                            random_state=42,
                            silent=True,
                            allow_writing_files=False,
                            **best_params
                        )
                    else:
                        final_model = CatBoostClassifier(
                            auto_class_weights='Balanced',
                            random_state=42,
                            silent=True,
                            allow_writing_files=False,
                            **best_params
                        )

                optimized_models.append((model_type, final_model))

            except Exception as e:
                print(f"   ⚠️ {model_type} failed: {e}")
                continue

        return optimized_models

    def create_default_models(self, task: str):
        """Fallback models with good default parameters."""
        if task == 'total_points':
            return [
                ('xgb', XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=5, random_state=42)),
                ('lgbm', LGBMRegressor(n_estimators=500, learning_rate=0.05, max_depth=5, random_state=42, verbose=-1)),
                ('catboost', CatBoostRegressor(iterations=500, depth=5, learning_rate=0.05, random_state=42, silent=True, allow_writing_files=False))
            ]
        else:
            return [
                ('xgb', XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42, eval_metric='logloss', use_label_encoder=False)),
                ('lgbm', LGBMClassifier(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42, verbose=-1)),
                ('catboost', CatBoostClassifier(iterations=500, depth=6, learning_rate=0.05, auto_class_weights='Balanced', random_state=42, silent=True, allow_writing_files=False))
            ]

    def create_stacking_model(self, task: str, X_train, y_train, X_val, y_val):
        """Create stacking ensemble with Bayesian-optimized base models."""

        base_models = self.create_bayesian_optimized_models(task, X_train, y_train, X_val, y_val)

        if task == 'total_points':
            meta_learner = XGBRegressor(n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42)
            stacking_model = StackingRegressor(
                estimators=base_models,
                final_estimator=meta_learner,
                cv=3,
                n_jobs=-1
            )
        else:
            meta_learner = XGBClassifier(n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42, eval_metric='logloss', use_label_encoder=False)
            stacking_model = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_learner,
                cv=3,
                stack_method='predict_proba',
                n_jobs=-1
            )

        return stacking_model

    def prepare_data(self, df):
        """Prepare training data with targets."""
        df = df.sort_values('Date').copy()

        y = {}

        # Match outcome (Winner)
        if 'Result' in df.columns:
            y['match_outcome'] = df['Result'].map({'H': 1, 'A': 0})

            home_win_rate = (df['Result'] == 'H').mean()
            self.bayesian_priors['match_outcome'] = {'home_win': home_win_rate}

        # Total points
        if 'TotalPoints' in df.columns:
            y['total_points'] = df['TotalPoints']
            self.bayesian_priors['total_points'] = {'avg_total': df['TotalPoints'].mean()}

        # Over/Under 200, 210, 220, 230
        if 'TotalPoints' in df.columns:
            for threshold in [200, 210, 220, 230]:
                y[f'over_{threshold}'] = (df['TotalPoints'] > threshold).astype(int)

        # Point spread
        if 'PointDiff' in df.columns:
            y['point_diff'] = df['PointDiff']

        print(f"📊 Prepared targets: {list(y.keys())}")
        return df, y

    def train_models(self, df, feature_cols):
        """Train advanced models with Bayesian optimization."""
        print("🚀 Starting Advanced Basketball Model Training...")

        df_processed, y = self.prepare_data(df)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)

        for task, y_task in y.items():
            print(f"\n🏀 Training {task}...")

            # Prepare features
            X = df_processed[feature_cols].fillna(0)

            # Feature selection
            max_features = min(50, len(feature_cols))
            if len(feature_cols) > max_features:
                if task in ['total_points', 'point_diff']:
                    selector = SelectKBest(f_regression, k=max_features)
                else:
                    selector = SelectKBest(f_classif, k=max_features)

                X_selected = selector.fit_transform(X, y_task)
                selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
                X = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
                print(f"   🎯 Selected {len(selected_features)} best features")

            cv_metrics = []
            best_metric = float('-inf')
            best_model = None

            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                print(f"   🔄 Fold {fold + 1}/3...")

                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y_task.iloc[train_idx], y_task.iloc[val_idx]

                # Create stacking model
                model = self.create_stacking_model(task, X_train, y_train, X_val, y_val)
                model.fit(X_train, y_train)

                # Evaluate
                if task in ['total_points', 'point_diff']:
                    y_pred = model.predict(X_val)
                    mae = np.mean(np.abs(y_val - y_pred))
                    mse = mean_squared_error(y_val, y_pred)
                    fold_metrics.append({'mae': mae, 'mse': mse})
                    current_metric = -mae
                else:
                    y_pred = model.predict(X_val)
                    y_prob = model.predict_proba(X_val)
                    acc = accuracy_score(y_val, y_pred)
                    ll = log_loss(y_val, y_prob)
                    fold_metrics.append({'accuracy': acc, 'log_loss': ll})
                    current_metric = acc

                if current_metric > best_metric:
                    best_metric = current_metric
                    best_model = model

            # Store best model
            if best_model is not None:
                self.models[task] = {
                    'model': best_model,
                    'features': list(X.columns)
                }

                # Calibrate classification models
                if task not in ['total_points', 'point_diff']:
                    print(f"   🧠 Calibrating {task} probabilities...")
                    try:
                        calibrated_model = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
                        calibrated_model.fit(X, y_task)
                        self.calibrated_models[task] = {
                            'model': calibrated_model,
                            'features': list(X.columns)
                        }
                    except Exception as e:
                        print(f"   ⚠️ Calibration failed: {e}")

                # Store metrics
                if cv_metrics:
                    self.metrics[task] = {
                        metric: np.mean([fold[metric] for fold in cv_metrics])
                        for metric in cv_metrics[0].keys()
                    }

                    print(f"\n   📊 Results for {task}:")
                    for metric, value in self.metrics[task].items():
                        print(f"      {metric}: {value:.4f}")

        print(f"\n🎉 Training completed!")
        print(f"   📊 Trained models: {list(self.models.keys())}")
        print(f"   🧠 Bayesian trials: {len(self.hyperopt_trials)}")

    def save_models(self, path):
        """Save all models."""
        save_data = {
            'models': self.models,
            'calibrated_models': self.calibrated_models,
            'metrics': self.metrics,
            'bayesian_priors': self.bayesian_priors,
            'hyperopt_trials': self.hyperopt_trials
        }
        joblib.dump(save_data, path)
        print(f"✅ Models saved to {path}")

    def load_models(self, path):
        """Load all models."""
        data = joblib.dump(path)
        self.models = data['models']
        self.calibrated_models = data.get('calibrated_models', {})
        self.metrics = data.get('metrics', {})
        self.bayesian_priors = data.get('bayesian_priors', {})
        self.hyperopt_trials = data.get('hyperopt_trials', {})
        print(f"✅ Models loaded from {path}")


def main():
    print("🧪 Testing Advanced Basketball Predictor...")
    predictor = AdvancedBasketballPredictor()
    print("\n✅ Ready for training with:")
    print("   - XGBoost, CatBoost, LightGBM")
    print("   - Bayesian hyperparameter optimization")
    print("   - Stacking ensembles")
    print("   - Probability calibration")


if __name__ == "__main__":
    main()
