# footy/model_training.py

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, precision_score, recall_score
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from imblearn.over_sampling import SMOTE
import warnings

warnings.filterwarnings('ignore')


class FootballPredictor:
    def __init__(self):
        self.models = {}
        self.metrics = {}

        # Enhanced feature list including goal-specific features
        self.base_features = [
            'HomeTeam_encoded', 'AwayTeam_encoded',
            'HomeTeamForm', 'AwayTeamForm',
            'HomeGoalsScoredAvg_5', 'AwayGoalsScoredAvg_5',
            'HomeGoalsConcededAvg_5', 'AwayGoalsConcededAvg_5',
            'HomeShotAccuracyRolling', 'AwayShotAccuracyRolling',
            'HomeFoulsAvg', 'AwayFoulsAvg'
        ]

        self.goal_features = [
            'HomeScoringRate_5', 'AwayScoringRate_5',
            'HomeConcedingRate_5', 'AwayConcedingRate_5',
            'HomeOverRate1.5_5', 'AwayOverRate1.5_5',
            'HomeOverRate2.5_5', 'AwayOverRate2.5_5',
            'HomeTotalGoalsRate_5', 'AwayTotalGoalsRate_5',
            'HomeGoalVariance_5', 'AwayGoalVariance_5',

        ]

    def prepare_data(self, df):
        """Prepare features and targets with enhanced goal predictions"""
        df = df.sort_values('Date').copy()

        # Combine base and goal-specific features
        self.features = self.base_features + self.goal_features
        X = df[self.features].fillna(0)

        # Prepare targets including over/under
        y = {}
        if 'FTR' in df.columns:
            y['match_outcome'] = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})
        if 'Over1.5' in df.columns:
            y['over_1_5'] = df['Over1.5']
        if 'Over2.5' in df.columns:
            y['over_2_5'] = df['Over2.5']
        if 'BTTS' in df.columns:
            y['btts'] = df['BTTS']

        return X, y

    def create_base_models(self, task):
        """Create base models with optimized parameters for each task"""
        common_params = {
            'random_state': 42,

        }

        if task == 'match_outcome':
            return [
                ('xgb', XGBClassifier(
                    n_estimators=300,
                    learning_rate=0.05,
                    max_depth=6,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective='multi:softprob',
                    num_class=3,
                    eval_metric='mlogloss',
                    use_label_encoder=False,
                    **common_params
                )),
                ('rf', RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_split=10,
                    min_samples_leaf=4,
                    **common_params
                )),
                ('cat', CatBoostClassifier(
                    iterations=300,
                    depth=6,
                    learning_rate=0.05,
                    loss_function='MultiClass',
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]
        else:
            return [
                ('xgb', XGBClassifier(
                    n_estimators=250,
                    learning_rate=0.05,
                    max_depth=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    scale_pos_weight=1.5,
                    use_label_encoder=False,
                    eval_metric='mlogloss',
                    **common_params
                )),
                ('rf', RandomForestClassifier(
                    n_estimators=250,
                    max_depth=5,
                    min_samples_split=8,
                    min_samples_leaf=4,
                    class_weight='balanced',
                    **common_params
                )),
                ('cat', CatBoostClassifier(
                    iterations=250,
                    depth=5,
                    learning_rate=0.05,
                    auto_class_weights='Balanced',
                    silent=True,
                    allow_writing_files=False,
                    **common_params
                ))
            ]

    def create_stacking_model(self, task, X_train, y_train):
        """Create and optimize stacking model for different prediction tasks."""

        # Create base models
        base_models = self.create_base_models(task)

        # Configure meta-classifier based on task
        if task == 'match_outcome':
            meta_clf = XGBClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=4,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                objective='multi:softprob',
                num_class=3,
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
        else:  # for over/under and BTTS
            meta_clf = XGBClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=3,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=1.5,
                random_state=42,
                eval_metric='mlogloss',
                use_label_encoder=False,
            )

        # Create stacking ensemble
        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=meta_clf,
            cv=5,
            n_jobs=-1,
            passthrough=True
        )

        return stacking_model

    def evaluate_model(self, model, X_val, y_val, task):
        """Enhanced model evaluation with additional metrics"""
        y_pred = model.predict(X_val)
        y_prob = model.predict_proba(X_val)

        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'f1': f1_score(y_val, y_pred, average='weighted'),
            'precision': precision_score(y_val, y_pred, average='weighted'),
            'recall': recall_score(y_val, y_pred, average='weighted')
        }

        if task != 'match_outcome':
            metrics['roc_auc'] = roc_auc_score(y_val, y_prob[:, 1])

        return metrics

    def train_models(self, df):
        """Train models with enhanced validation and metrics"""
        print("Preparing data...")
        X, y = self.prepare_data(df)

        tscv = TimeSeriesSplit(n_splits=5)

        for task, y_task in y.items():
            print(f"\nTraining models for {task}")
            cv_metrics = []
            best_metric = 0
            best_model = None

            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y_task.iloc[train_idx], y_task.iloc[val_idx]

                # Apply SMOTE for balanced training
                smote = SMOTE(random_state=42)
                X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

                # Create and train stacking model
                model = self.create_stacking_model(task, X_train_res, y_train_res)
                model.fit(X_train_res, y_train_res)

                # Evaluate
                fold_metrics = self.evaluate_model(model, X_val, y_val, task)
                cv_metrics.append(fold_metrics)

                # Track best model
                current_metric = fold_metrics['f1']
                if current_metric > best_metric:
                    best_metric = current_metric
                    best_model = model

            # Store best model and average metrics
            self.models[task] = best_model
            self.metrics[task] = {
                metric: np.mean([fold[metric] for fold in cv_metrics])
                for metric in cv_metrics[0].keys()
            }

            # Print detailed results
            print(f"\nResults for {task}:")
            for metric, value in self.metrics[task].items():
                print(f"{metric}: {value:.4f}")

    def predict(self, X_new):
        """Enhanced prediction with probabilities"""
        predictions = {}
        probabilities = {}

        for task, model in self.models.items():
            if task == 'match_outcome':
                pred_probs = model.predict_proba(X_new)
                pred_idx = np.argmax(pred_probs, axis=1)
                predictions[task] = pd.Series(pred_idx).map({0: 'H', 1: 'D', 2: 'A'})
                probabilities[task] = pred_probs
            else:
                pred_probs = model.predict_proba(X_new)
                predictions[task] = (pred_probs[:, 1] > 0.5).astype(int)
                probabilities[task] = pred_probs[:, 1]

        return predictions, probabilities

    def save_models(self, path):
        """Save trained models to disk"""
        try:
            import joblib
            joblib.dump(self.models, path)
            print(f"Models successfully saved to {path}")
        except Exception as e:
            print(f"Error saving models: {str(e)}")

    def load_models(self, path):
        """Load trained models from disk"""
        try:
            import joblib
            self.models = joblib.load(path)
            print(f"Models successfully loaded from {path}")
        except Exception as e:
            print(f"Error loading models: {str(e)}")