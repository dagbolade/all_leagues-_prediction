"""
Advanced Tennis Model Training - Matching Football Sophistication
Uses XGBoost, CatBoost, LightGBM with Bayesian Hyperparameter Optimization
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, log_loss
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_selection import SelectKBest, f_classif
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import StackingClassifier
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
    print("[Warning]️ hyperopt not available. Install with: pip install hyperopt")
    HYPEROPT_AVAILABLE = False

warnings.filterwarnings('ignore')


class AdvancedTennisPredictor:
    """Advanced tennis predictor with Bayesian optimization and ensemble methods."""

    def __init__(self):
        self.models = {}
        self.calibrated_models = {}
        self.metrics = {}
        self.feature_importance = {}
        self.hyperopt_trials = {}
        self.bayesian_priors = {}

    def get_bayesian_search_space(self) -> Dict:
        """Define Bayesian optimization search spaces for tennis."""
        return {
            'xgb': {
                'n_estimators': hp.choice('n_estimators', [300, 500, 700]),
                'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                'max_depth': hp.choice('max_depth', [4, 5, 6, 7]),
                'subsample': hp.uniform('subsample', 0.7, 1.0),
                'colsample_bytree': hp.uniform('colsample_bytree', 0.7, 1.0),
                'scale_pos_weight': hp.uniform('scale_pos_weight', 0.8, 1.2),
            },
            'lgbm': {
                'n_estimators': hp.choice('n_estimators', [300, 500, 700]),
                'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                'num_leaves': hp.choice('num_leaves', [31, 63, 127]),
                'max_depth': hp.choice('max_depth', [4, 5, 6, 7]),
                'feature_fraction': hp.uniform('feature_fraction', 0.7, 1.0),
            },
            'catboost': {
                'iterations': hp.choice('iterations', [300, 500, 700]),
                'learning_rate': hp.uniform('learning_rate', 0.01, 0.2),
                'depth': hp.choice('depth', [4, 5, 6, 7]),
                'l2_leaf_reg': hp.uniform('l2_leaf_reg', 1, 10),
            }
        }

    def bayesian_objective(self, params: Dict, X_train, y_train, X_val, y_val, model_type: str) -> Dict:
        """Objective function for Bayesian optimization."""
        try:
            if model_type == 'xgb':
                model = XGBClassifier(
                    eval_metric='logloss',
                    use_label_encoder=False,
                    random_state=42,
                    **params
                )
            elif model_type == 'lgbm':
                model = LGBMClassifier(
                    random_state=42,
                    verbose=-1,
                    **params
                )
            elif model_type == 'catboost':
                model = CatBoostClassifier(
                    auto_class_weights='Balanced',
                    random_state=42,
                    silent=True,
                    allow_writing_files=False,
                    **params
                )

            model.fit(X_train, y_train)
            y_pred_proba = model.predict_proba(X_val)
            loss = log_loss(y_val, y_pred_proba)

            return {'loss': loss, 'status': STATUS_OK}

        except Exception as e:
            return {'loss': float('inf'), 'status': STATUS_OK}

    def create_bayesian_optimized_models(self, X_train, y_train, X_val, y_val):
        """Create models with Bayesian hyperparameter optimization."""

        if not HYPEROPT_AVAILABLE:
            print("[Warning]️ Using default parameters (hyperopt not available)")
            return self.create_default_models()

        print(f"[Bayesian] Bayesian optimization for tennis winner prediction...")

        search_spaces = self.get_bayesian_search_space()
        optimized_models = []

        for model_type, space in search_spaces.items():
            print(f"   [Optimizing] Optimizing {model_type}...")

            trials = Trials()

            def objective(params):
                return self.bayesian_objective(params, X_train, y_train, X_val, y_val, model_type)

            try:
                best_params = fmin(
                    fn=objective,
                    space=space,
                    algo=tpe.suggest,
                    max_evals=15,
                    trials=trials,
                    verbose=False
                )

                best_params = space_eval(space, best_params)
                self.hyperopt_trials[model_type] = trials

                print(f"   [OK] {model_type} best loss: {min(trials.losses()):.4f}")

                # Create final model
                if model_type == 'xgb':
                    final_model = XGBClassifier(
                        eval_metric='logloss',
                        use_label_encoder=False,
                        random_state=42,
                        **best_params
                    )
                elif model_type == 'lgbm':
                    final_model = LGBMClassifier(
                        random_state=42,
                        verbose=-1,
                        **best_params
                    )
                elif model_type == 'catboost':
                    final_model = CatBoostClassifier(
                        auto_class_weights='Balanced',
                        random_state=42,
                        silent=True,
                        allow_writing_files=False,
                        **best_params
                    )

                optimized_models.append((model_type, final_model))

            except Exception as e:
                print(f"   [Warning]️ {model_type} failed: {e}")
                continue

        return optimized_models

    def create_default_models(self):
        """Fallback models with good default parameters."""
        return [
            ('xgb', XGBClassifier(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=6,
                random_state=42,
                eval_metric='logloss',
                use_label_encoder=False
            )),
            ('lgbm', LGBMClassifier(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=6,
                random_state=42,
                verbose=-1
            )),
            ('catboost', CatBoostClassifier(
                iterations=500,
                depth=6,
                learning_rate=0.05,
                auto_class_weights='Balanced',
                random_state=42,
                silent=True,
                allow_writing_files=False
            ))
        ]

    def create_stacking_model(self, X_train, y_train, X_val, y_val):
        """Create stacking ensemble with Bayesian-optimized base models."""

        base_models = self.create_bayesian_optimized_models(X_train, y_train, X_val, y_val)

        meta_learner = XGBClassifier(
            n_estimators=200,
            learning_rate=0.08,
            max_depth=4,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )

        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=meta_learner,
            cv=3,
            stack_method='predict_proba',
            n_jobs=-1
        )

        return stacking_model

    def prepare_data(self, df):
        """Prepare training data."""
        df = df.sort_values('Date').copy()

        # Target: Player1 wins = 1, Player2 wins = 0
        y = (df['Winner'] == 'Player1').astype(int)

        # Calculate Bayesian priors
        player1_win_rate = y.mean()
        self.bayesian_priors = {
            'player1_win_rate': player1_win_rate,
            'player2_win_rate': 1 - player1_win_rate
        }

        print(f"[Metrics] Player1 win rate: {player1_win_rate:.2%}")
        return df, y

    def train_models(self, df, feature_cols):
        """Train advanced models with Bayesian optimization."""
        print("[Training] Starting Advanced Tennis Model Training...")

        df_processed, y = self.prepare_data(df)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)

        print(f"\n[Tennis] Training match winner prediction...")

        # Prepare features
        X = df_processed[feature_cols].fillna(0)

        # Feature selection
        max_features = min(50, len(feature_cols))
        if len(feature_cols) > max_features:
            selector = SelectKBest(f_classif, k=max_features)
            X_selected = selector.fit_transform(X, y)
            selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
            X = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
            print(f"   [Selected] Selected {len(selected_features)} best features")

        cv_metrics = []
        best_metric = float('-inf')
        best_model = None

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            print(f"   [Fold] Fold {fold + 1}/3...")

            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # SMOTE for balance
            try:
                min_samples = min(sum(y_train == 0), sum(y_train == 1))
                k_neighbors = min(5, min_samples - 1)
                if k_neighbors > 0:
                    smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
                    X_train, y_train = smote.fit_resample(X_train, y_train)
            except:
                pass

            # Create stacking model
            model = self.create_stacking_model(X_train, y_train, X_val, y_val)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_val)
            y_prob = model.predict_proba(X_val)
            acc = accuracy_score(y_val, y_pred)
            ll = log_loss(y_val, y_prob)
            f1 = f1_score(y_val, y_pred)

            cv_metrics.append({'accuracy': acc, 'log_loss': ll, 'f1': f1})

            if acc > best_metric:
                best_metric = acc
                best_model = model

        # Store best model
        if best_model is not None:
            self.models['winner'] = {
                'model': best_model,
                'features': list(X.columns)
            }

            # Calibrate probabilities
            print(f"   [Bayesian] Calibrating probabilities...")
            try:
                calibrated_model = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
                calibrated_model.fit(X, y)
                self.calibrated_models['winner'] = {
                    'model': calibrated_model,
                    'features': list(X.columns)
                }
            except Exception as e:
                print(f"   [Warning]️ Calibration failed: {e}")

            # Store metrics
            self.metrics['winner'] = {
                'accuracy': np.mean([m['accuracy'] for m in cv_metrics]),
                'log_loss': np.mean([m['log_loss'] for m in cv_metrics]),
                'f1': np.mean([m['f1'] for m in cv_metrics])
            }

            print(f"\n   [Metrics] Results:")
            print(f"      Accuracy: {self.metrics['winner']['accuracy']:.4f}")
            print(f"      Log Loss: {self.metrics['winner']['log_loss']:.4f}")
            print(f"      F1 Score: {self.metrics['winner']['f1']:.4f}")

        print(f"\n[Complete] Training completed!")
        print(f"   [Bayesian] Bayesian trials: {len(self.hyperopt_trials)}")

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
        print(f"[OK] Models saved to {path}")

    def load_models(self, path):
        """Load all models."""
        data = joblib.load(path)
        self.models = data['models']
        self.calibrated_models = data.get('calibrated_models', {})
        self.metrics = data.get('metrics', {})
        self.bayesian_priors = data.get('bayesian_priors', {})
        self.hyperopt_trials = data.get('hyperopt_trials', {})
        print(f"[OK] Models loaded from {path}")


def main():
    print("[Test] Testing Advanced Tennis Predictor...")
    predictor = AdvancedTennisPredictor()
    print("\n[OK] Ready for training with:")
    print("   - XGBoost, CatBoost, LightGBM")
    print("   - Bayesian hyperparameter optimization")
    print("   - Stacking ensembles")
    print("   - Probability calibration")


if __name__ == "__main__":
    main()
