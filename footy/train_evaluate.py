from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import joblib
import pandas as pd

def train_and_evaluate_model(X, y, model_name, task_type, preprocessor):
    """
    Train and evaluate a model using GridSearchCV.

    Args:
        X (pd.DataFrame): Features.
        y (pd.Series): Target variable.
        model_name (str): Name of the model ('XGBoost', 'CatBoost').
        task_type (str): Task type ('classification', 'regression').
        preprocessor: Preprocessing pipeline.

    Returns:
        best_model: Trained best model.
    """
    from footy.model_training import get_model_and_params

    model, params = get_model_and_params(model_name, task_type)

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    tscv = TimeSeriesSplit(n_splits=5)
    grid_search = GridSearchCV(pipeline, params, cv=tscv,
                               scoring='neg_mean_squared_error' if task_type == 'regression' else 'accuracy', n_jobs=-1)
    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_

    # Evaluation
    if task_type == 'classification':
        y_pred = best_model.predict(X)
        print(f"\nClassification Report for {model_name}:")
        print(classification_report(y, y_pred))
    else:
        mse = mean_squared_error(y, best_model.predict(X))
        r2 = r2_score(y, best_model.predict(X))
        print(f"\nRegression Results for {model_name}:")
        print(f"Mean Squared Error: {mse}")
        print(f"R2 Score: {r2}")

    # Save the model
    joblib.dump(best_model, f'models/best_{task_type}_{model_name.lower()}.joblib')
    return best_model
