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

    @staticmethod
    def _parse_score(score_str):
        """Parse tennis score string into structured info.

        Returns dict with: num_sets, first_set_winner (1=P1, 0=P2, None=unknown)
        """
        if pd.isna(score_str):
            return {'num_sets': None, 'first_set_p1': None}
        parts = str(score_str).split()
        # Keep only parts that look like set scores (start with digit)
        sets = [p for p in parts if p and p[0].isdigit()]
        if not sets:
            return {'num_sets': None, 'first_set_p1': None}
        num_sets = len(sets)
        # Parse first set: "6-4" or "7-6(3)"
        try:
            first = sets[0].split('(')[0]  # strip tiebreak e.g. "7-6(3)" -> "7-6"
            a, b = first.split('-')
            first_set_p1 = 1 if int(a) > int(b) else 0
        except Exception:
            first_set_p1 = None
        return {'num_sets': num_sets, 'first_set_p1': first_set_p1}

    def prepare_data(self, df):
        """Prepare training data with multiple targets."""
        df = df.sort_values('Date').copy()

        targets = {}

        # Target 1: Match winner (Player1 wins = 1)
        targets['winner'] = (df['Winner'] == 'Player1').astype(int)
        player1_win_rate = targets['winner'].mean()
        self.bayesian_priors = {
            'player1_win_rate': player1_win_rate,
            'player2_win_rate': 1 - player1_win_rate
        }
        print(f"[Metrics] Player1 win rate: {player1_win_rate:.2%}")

        # Parse score for additional targets
        if 'Score' in df.columns:
            parsed = df['Score'].apply(self._parse_score)
            df['_num_sets']    = parsed.apply(lambda x: x['num_sets'])
            df['_first_set_p1'] = parsed.apply(lambda x: x['first_set_p1'])

            # Target 2: First set winner (Player1 wins first set = 1)
            mask_fs = df['_first_set_p1'].notna()
            if mask_fs.sum() > 1000:
                targets['first_set'] = df.loc[mask_fs, '_first_set_p1'].astype(int)
                print(f"[Metrics] First set P1 rate: {targets['first_set'].mean():.2%} ({mask_fs.sum()} matches)")

            # Target 3: Goes to distance (3+ sets for BO3, i.e. not straight sets)
            mask_sets = df['_num_sets'].notna()
            if mask_sets.sum() > 1000:
                goes_3 = (df.loc[mask_sets, '_num_sets'] >= 3).astype(int)
                targets['goes_distance'] = goes_3
                print(f"[Metrics] Goes distance (3+ sets) rate: {goes_3.mean():.2%} ({mask_sets.sum()} matches)")

        print(f"[Metrics] Training {len(targets)} tasks: {list(targets.keys())}")
        return df, targets

    def _train_single_task(self, task, X_full, y_task, feature_cols):
        """Train one task with CV, return best model and metrics."""
        tscv = TimeSeriesSplit(n_splits=3)

        # Align index between X and y
        common_idx = X_full.index.intersection(y_task.index)
        X = X_full.loc[common_idx].fillna(0)
        y = y_task.loc[common_idx]

        # Feature selection
        max_features = min(50, len(feature_cols))
        selected_features = feature_cols
        if X.shape[1] > max_features:
            selector = SelectKBest(f_classif, k=max_features)
            X_sel = selector.fit_transform(X, y)
            selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
            X = pd.DataFrame(X_sel, columns=selected_features, index=X.index)
            print(f"   [Selected] {len(selected_features)} best features")

        cv_metrics = []
        best_metric = float('-inf')
        best_model = None

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            print(f"   [Fold] Fold {fold + 1}/3…")
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            try:
                min_s = min(sum(y_train == 0), sum(y_train == 1))
                k = min(5, min_s - 1)
                if k > 0:
                    smote = SMOTE(random_state=42, k_neighbors=k)
                    X_train, y_train = smote.fit_resample(X_train, y_train)
            except Exception:
                pass

            model = self.create_stacking_model(X_train, y_train, X_val, y_val)
            model.fit(X_train, y_train)

            y_pred = model.predict(X_val)
            y_prob = model.predict_proba(X_val)
            acc = accuracy_score(y_val, y_pred)
            ll  = log_loss(y_val, y_prob)
            f1  = f1_score(y_val, y_pred)
            cv_metrics.append({'accuracy': acc, 'log_loss': ll, 'f1': f1})

            if acc > best_metric:
                best_metric = acc
                best_model  = model

        if best_model is None:
            return None, selected_features, {}

        self.models[task] = {'model': best_model, 'features': list(X.columns)}

        try:
            cal = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
            cal.fit(X, y)
            self.calibrated_models[task] = {'model': cal, 'features': list(X.columns)}
        except Exception as e:
            print(f"   [Warning] Calibration failed: {e}")

        metrics = {
            'accuracy': np.mean([m['accuracy'] for m in cv_metrics]),
            'log_loss': np.mean([m['log_loss'] for m in cv_metrics]),
            'f1':       np.mean([m['f1']       for m in cv_metrics]),
        }
        self.metrics[task] = metrics
        print(f"   [Metrics] Acc={metrics['accuracy']:.4f}  LL={metrics['log_loss']:.4f}  F1={metrics['f1']:.4f}")
        return best_model, list(X.columns), metrics

    def train_models(self, df, feature_cols):
        """Train advanced models for all targets."""
        print("[Training] Starting Advanced Tennis Model Training...")

        df_processed, targets = self.prepare_data(df)

        X_full = df_processed[feature_cols].fillna(0)

        for task, y_task in targets.items():
            print(f"\n[Tennis] Training: {task}…")
            self._train_single_task(task, X_full, y_task, feature_cols)

        print(f"\n[Complete] Training done — models: {list(self.models.keys())}")
        print(f"[Bayesian] Bayesian trials: {len(self.hyperopt_trials)}")

    def save_models(self, path):
        """Save all models."""
        all_features = []
        for task_data in self.models.values():
            for f in task_data.get('features', []):
                if f not in all_features:
                    all_features.append(f)

        save_data = {
            'models': self.models,
            'calibrated_models': self.calibrated_models,
            'metrics': self.metrics,
            'bayesian_priors': self.bayesian_priors,
            'hyperopt_trials': self.hyperopt_trials,
            'feature_cols': all_features,
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
