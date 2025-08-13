# footy/train_evaluate.py - ENHANCED VERSION

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, mean_squared_error, r2_score, accuracy_score,
    roc_auc_score, f1_score, precision_score, recall_score, log_loss,
    brier_score_loss, mean_absolute_error
)
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


def train_and_evaluate_model(X, y, model_name, task_type, preprocessor):
    """
    Enhanced model training and evaluation using GridSearchCV.

    Args:
        X (pd.DataFrame): Features.
        y (pd.Series): Target variable.
        model_name (str): Name of the model ('XGBoost', 'CatBoost', 'RandomForest').
        task_type (str): Task type ('classification', 'regression').
        preprocessor: Preprocessing pipeline.

    Returns:
        best_model: Trained best model.
        metrics: Comprehensive evaluation metrics.
        calibrated_model: Calibrated version (for classification).
    """
    print(f"\n🚀 Enhanced Training: {model_name} for {task_type}")
    print("=" * 60)

    from footy.model_training import get_model_and_params
    model, params = get_model_and_params(model_name, task_type)

    # Create enhanced pipeline
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    # Enhanced time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)

    # Enhanced scoring for different tasks
    if task_type == 'classification':
        scoring = 'roc_auc' if len(np.unique(y)) == 2 else 'accuracy'
    else:
        scoring = 'neg_mean_squared_error'

    # Grid search with enhanced parameters
    grid_search = GridSearchCV(
        pipeline,
        params,
        cv=tscv,
        scoring=scoring,
        n_jobs=-1,
        verbose=1,
        return_train_score=True
    )

    print(f"🔄 Training with {len(params)} parameter combinations...")
    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_
    print(f"✅ Best model trained with score: {grid_search.best_score_:.4f}")
    print(f"📊 Best parameters: {grid_search.best_params_}")

    # Enhanced evaluation
    metrics = evaluate_enhanced_model(best_model, X, y, task_type, model_name)

    # Model calibration for classification
    calibrated_model = None
    if task_type == 'classification':
        print(f"\n🎯 Calibrating {model_name} probabilities...")
        calibrated_model = CalibratedClassifierCV(best_model, method='isotonic', cv=3)
        calibrated_model.fit(X, y)

        # Evaluate calibration
        cal_metrics = evaluate_calibration(calibrated_model, X, y)
        metrics.update(cal_metrics)

    # Save enhanced model
    model_filename = f'models/enhanced_{task_type}_{model_name.lower()}.joblib'
    joblib.dump(best_model, model_filename)
    print(f"💾 Model saved: {model_filename}")

    if calibrated_model:
        cal_filename = f'models/calibrated_{task_type}_{model_name.lower()}.joblib'
        joblib.dump(calibrated_model, cal_filename)
        print(f"💾 Calibrated model saved: {cal_filename}")

    return best_model, metrics, calibrated_model


def evaluate_enhanced_model(model, X, y, task_type, model_name):
    """
    Comprehensive model evaluation with enhanced metrics.

    Args:
        model: Trained model
        X: Features
        y: Target
        task_type: 'classification' or 'regression'
        model_name: Model name for reporting

    Returns:
        metrics: Dictionary of evaluation metrics
    """
    print(f"\n📊 Enhanced Evaluation: {model_name}")
    print("-" * 40)

    metrics = {
        'model_name': model_name,
        'task_type': task_type,
        'evaluation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Make predictions
    y_pred = model.predict(X)

    if task_type == 'classification':
        # Classification metrics
        accuracy = accuracy_score(y, y_pred)

        print(f"✅ Accuracy: {accuracy:.4f}")
        metrics['accuracy'] = accuracy

        # Detailed classification report
        class_report = classification_report(y, y_pred, output_dict=True)
        print(f"\n📋 Classification Report:")
        print(classification_report(y, y_pred))

        metrics['classification_report'] = class_report
        metrics['f1_macro'] = class_report['macro avg']['f1-score']
        metrics['precision_macro'] = class_report['macro avg']['precision']
        metrics['recall_macro'] = class_report['macro avg']['recall']

        # Probability-based metrics
        if hasattr(model, 'predict_proba'):
            y_proba = model.predict_proba(X)

            # ROC AUC (for binary classification)
            if len(np.unique(y)) == 2:
                roc_auc = roc_auc_score(y, y_proba[:, 1])
                print(f"🎯 ROC AUC: {roc_auc:.4f}")
                metrics['roc_auc'] = roc_auc

                # Brier Score (probability calibration quality)
                brier = brier_score_loss(y, y_proba[:, 1])
                print(f"📐 Brier Score: {brier:.4f} (lower is better)")
                metrics['brier_score'] = brier

            # Log Loss
            try:
                log_loss_score = log_loss(y, y_proba)
                print(f"📉 Log Loss: {log_loss_score:.4f}")
                metrics['log_loss'] = log_loss_score
            except:
                pass

        # Enhanced goal market analysis
        if 'over' in model_name.lower() or 'btts' in model_name.lower():
            analyze_goal_market_performance(y, y_pred, model_name, metrics)

    else:
        # Regression metrics
        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)

        print(f"📊 Regression Results:")
        print(f"   MSE: {mse:.4f}")
        print(f"   RMSE: {rmse:.4f}")
        print(f"   MAE: {mae:.4f}")
        print(f"   R² Score: {r2:.4f}")

        metrics.update({
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2_score': r2
        })

        # Enhanced goal prediction analysis
        if 'goal' in model_name.lower():
            analyze_goal_prediction_quality(y, y_pred, metrics)

    return metrics


def analyze_goal_market_performance(y_true, y_pred, market_name, metrics):
    """Analyze performance specifically for goal markets (Over/Under, BTTS)."""
    print(f"\n⚽ Enhanced Goal Market Analysis: {market_name}")

    # Convert to binary if needed
    y_true_bin = np.array(y_true)
    y_pred_bin = np.array(y_pred)

    # Market-specific analysis
    if 'over_2_5' in market_name.lower():
        print("🎯 Over 2.5 Goals Market Analysis:")

        # Calculate market-specific metrics
        correct_overs = np.sum((y_true_bin == 1) & (y_pred_bin == 1))
        correct_unders = np.sum((y_true_bin == 0) & (y_pred_bin == 0))
        total_overs = np.sum(y_true_bin == 1)
        total_unders = np.sum(y_true_bin == 0)

        over_accuracy = correct_overs / total_overs if total_overs > 0 else 0
        under_accuracy = correct_unders / total_unders if total_unders > 0 else 0

        print(f"   Over 2.5 Accuracy: {over_accuracy:.1%}")
        print(f"   Under 2.5 Accuracy: {under_accuracy:.1%}")

        metrics['over_2_5_accuracy'] = over_accuracy
        metrics['under_2_5_accuracy'] = under_accuracy

        # Betting profitability simulation
        if over_accuracy > 0.6:  # 60% threshold for profitability
            print(f"   🔥 STRONG MARKET: {over_accuracy:.1%} accuracy!")
            metrics['market_strength'] = 'Strong'
        elif over_accuracy > 0.55:
            print(f"   📊 Good market: {over_accuracy:.1%} accuracy")
            metrics['market_strength'] = 'Good'
        else:
            print(f"   ⚠️ Weak market: {over_accuracy:.1%} accuracy")
            metrics['market_strength'] = 'Weak'

    elif 'btts' in market_name.lower():
        print("🥅 Both Teams to Score Analysis:")

        btts_yes_accuracy = np.sum((y_true_bin == 1) & (y_pred_bin == 1)) / np.sum(y_true_bin == 1) if np.sum(
            y_true_bin == 1) > 0 else 0
        btts_no_accuracy = np.sum((y_true_bin == 0) & (y_pred_bin == 0)) / np.sum(y_true_bin == 0) if np.sum(
            y_true_bin == 0) > 0 else 0

        print(f"   BTTS Yes Accuracy: {btts_yes_accuracy:.1%}")
        print(f"   BTTS No Accuracy: {btts_no_accuracy:.1%}")

        metrics['btts_yes_accuracy'] = btts_yes_accuracy
        metrics['btts_no_accuracy'] = btts_no_accuracy


def analyze_goal_prediction_quality(y_true, y_pred, metrics):
    """Analyze quality of total goals predictions."""
    print(f"\n⚽ Goal Prediction Quality Analysis:")

    # Goal prediction accuracy within ranges
    exact_matches = np.sum(np.abs(y_true - y_pred) < 0.5)
    within_1_goal = np.sum(np.abs(y_true - y_pred) < 1.0)
    within_1_5_goals = np.sum(np.abs(y_true - y_pred) < 1.5)

    total_predictions = len(y_true)

    exact_accuracy = exact_matches / total_predictions
    within_1_accuracy = within_1_goal / total_predictions
    within_1_5_accuracy = within_1_5_goals / total_predictions

    print(f"   Exact predictions (±0.5): {exact_accuracy:.1%}")
    print(f"   Within 1 goal: {within_1_accuracy:.1%}")
    print(f"   Within 1.5 goals: {within_1_5_accuracy:.1%}")

    metrics.update({
        'exact_goal_accuracy': exact_accuracy,
        'within_1_goal_accuracy': within_1_accuracy,
        'within_1_5_goal_accuracy': within_1_5_accuracy
    })

    # Average prediction vs actual
    avg_predicted = np.mean(y_pred)
    avg_actual = np.mean(y_true)

    print(f"   Average predicted goals: {avg_predicted:.2f}")
    print(f"   Average actual goals: {avg_actual:.2f}")
    print(f"   Prediction bias: {avg_predicted - avg_actual:+.2f}")

    metrics['avg_predicted_goals'] = avg_predicted
    metrics['avg_actual_goals'] = avg_actual
    metrics['prediction_bias'] = avg_predicted - avg_actual


def evaluate_calibration(calibrated_model, X, y):
    """Evaluate probability calibration quality."""
    print(f"\n🎯 Probability Calibration Analysis:")

    cal_metrics = {}

    try:
        y_proba_cal = calibrated_model.predict_proba(X)[:, 1]

        # Calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y, y_proba_cal, n_bins=10
        )

        # Calibration error
        calibration_error = np.mean(np.abs(fraction_of_positives - mean_predicted_value))

        print(f"   Calibration Error: {calibration_error:.4f}")
        cal_metrics['calibration_error'] = calibration_error

        # Brier score for calibrated model
        brier_cal = brier_score_loss(y, y_proba_cal)
        print(f"   Calibrated Brier Score: {brier_cal:.4f}")
        cal_metrics['brier_score_calibrated'] = brier_cal

        if calibration_error < 0.05:
            print("   ✅ Excellent calibration!")
            cal_metrics['calibration_quality'] = 'Excellent'
        elif calibration_error < 0.1:
            print("   📊 Good calibration")
            cal_metrics['calibration_quality'] = 'Good'
        else:
            print("   ⚠️ Poor calibration")
            cal_metrics['calibration_quality'] = 'Poor'

    except Exception as e:
        print(f"   ❌ Calibration evaluation failed: {e}")
        cal_metrics['calibration_error'] = None

    return cal_metrics


def compare_models_enhanced(X, y, task_type, models_to_compare=['XGBoost', 'CatBoost', 'RandomForest']):
    """
    Compare multiple models side by side with enhanced metrics.

    Args:
        X: Features
        y: Target
        task_type: 'classification' or 'regression'
        models_to_compare: List of model names to compare

    Returns:
        comparison_results: DataFrame with model comparison
    """
    print(f"\n🏆 Enhanced Model Comparison for {task_type}")
    print("=" * 60)

    results = []

    for model_name in models_to_compare:
        print(f"\n🔄 Evaluating {model_name}...")

        try:
            # Use a simple preprocessor for comparison
            from sklearn.preprocessing import StandardScaler
            preprocessor = StandardScaler()

            model, metrics, cal_model = train_and_evaluate_model(
                X, y, model_name, task_type, preprocessor
            )

            # Extract key metrics for comparison
            if task_type == 'classification':
                comparison_metrics = {
                    'Model': model_name,
                    'Accuracy': metrics.get('accuracy', 0),
                    'F1_Score': metrics.get('f1_macro', 0),
                    'ROC_AUC': metrics.get('roc_auc', 0),
                    'Brier_Score': metrics.get('brier_score', np.inf),
                    'Log_Loss': metrics.get('log_loss', np.inf)
                }
            else:
                comparison_metrics = {
                    'Model': model_name,
                    'R2_Score': metrics.get('r2_score', -np.inf),
                    'RMSE': metrics.get('rmse', np.inf),
                    'MAE': metrics.get('mae', np.inf),
                    'MSE': metrics.get('mse', np.inf)
                }

            results.append(comparison_metrics)

        except Exception as e:
            print(f"❌ {model_name} evaluation failed: {e}")

    # Create comparison DataFrame
    comparison_df = pd.DataFrame(results)

    if len(comparison_df) > 0:
        print(f"\n📊 Model Comparison Results:")
        print("=" * 60)
        print(comparison_df.round(4).to_string(index=False))

        # Identify best model
        if task_type == 'classification':
            best_model = comparison_df.loc[comparison_df['Accuracy'].idxmax(), 'Model']
            best_score = comparison_df['Accuracy'].max()
            print(f"\n🏆 Best Model: {best_model} (Accuracy: {best_score:.4f})")
        else:
            best_model = comparison_df.loc[comparison_df['R2_Score'].idxmax(), 'Model']
            best_score = comparison_df['R2_Score'].max()
            print(f"\n🏆 Best Model: {best_model} (R² Score: {best_score:.4f})")

    return comparison_df


def evaluate_model_portfolio(models_dict, X, y):
    """
    Evaluate a portfolio of trained models for different tasks.

    Args:
        models_dict: Dictionary of {task: model} pairs
        X: Features
        y_dict: Dictionary of {task: target} pairs for each task

    Returns:
        portfolio_metrics: Comprehensive evaluation of the model portfolio
    """
    print(f"\n🎯 Enhanced Model Portfolio Evaluation")
    print("=" * 60)

    portfolio_metrics = {
        'evaluation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_models': len(models_dict),
        'model_performance': {}
    }

    for task, model in models_dict.items():
        print(f"\n📊 Evaluating {task} model...")

        try:
            if hasattr(model, 'predict'):
                y_pred = model.predict(X)

                # Task-specific evaluation
                if 'classification' in str(type(model)).lower():
                    accuracy = accuracy_score(y, y_pred)
                    portfolio_metrics['model_performance'][task] = {
                        'accuracy': accuracy,
                        'type': 'classification'
                    }
                    print(f"   ✅ {task} Accuracy: {accuracy:.4f}")
                else:
                    mse = mean_squared_error(y, y_pred)
                    r2 = r2_score(y, y_pred)
                    portfolio_metrics['model_performance'][task] = {
                        'mse': mse,
                        'r2_score': r2,
                        'type': 'regression'
                    }
                    print(f"   ✅ {task} R² Score: {r2:.4f}")

        except Exception as e:
            print(f"   ❌ {task} evaluation failed: {e}")
            portfolio_metrics['model_performance'][task] = {'error': str(e)}

    return portfolio_metrics


# Enhanced utility functions
def save_evaluation_report(metrics_dict, filename=None):
    """Save comprehensive evaluation report."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/enhanced_evaluation_{timestamp}.json"

    import json
    import os

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as f:
        json.dump(metrics_dict, f, indent=2, default=str)

    print(f"💾 Enhanced evaluation report saved: {filename}")


def load_and_evaluate_saved_model(model_path, X, y, task_type):
    """Load and evaluate a previously saved model."""
    print(f"\n📂 Loading and evaluating model: {model_path}")

    try:
        model = joblib.load(model_path)
        metrics = evaluate_enhanced_model(model, X, y, task_type, model_path)
        return model, metrics
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return None, None