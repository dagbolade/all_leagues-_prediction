import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder

def prepare_data(df, target_columns):
    """
    Prepare features and targets from the dataset.

    Args:
        df (pd.DataFrame): Input DataFrame.
        target_columns (list): Target columns for the model.

    Returns:
        X (pd.DataFrame): Features.
        y (pd.DataFrame): Target variables.
    """
    df = df.sort_values('Date')

    features = [
        'HomeTeam', 'AwayTeam', 'HomeTeam_encoded', 'AwayTeam_encoded',
        'HomeTeamForm', 'AwayTeamForm', 'HomeGoalsScoredAvg_5', 'AwayGoalsScoredAvg_5',
        'HomeGoalsConcededAvg_5', 'AwayGoalsConcededAvg_5', 'HomeShotAccuracyRolling',
        'AwayShotAccuracyRolling', 'HomeFoulsAvg', 'AwayFoulsAvg', 'HomeShotAccuracy', 'AwayShotAccuracy'
    ]

    X = df[features]
    y = df[target_columns]

    le = LabelEncoder()
    for col in ['FTR', 'Over_1.5_Goals', 'Over_2.5_Goals']:
        y[col] = le.fit_transform(y[col])

    return X, y


def create_preprocessor():
    """
    Create a preprocessing pipeline for numeric and categorical data.

    Returns:
        preprocessor: A ColumnTransformer object for preprocessing.
    """
    numeric_features = ['HomeTeam_encoded', 'AwayTeam_encoded', 'HomeTeamForm', 'AwayTeamForm',
                        'HomeGoalsScoredAvg_5', 'AwayGoalsScoredAvg_5', 'HomeGoalsConcededAvg_5',
                        'AwayGoalsConcededAvg_5', 'HomeShotAccuracyRolling', 'AwayShotAccuracyRolling',
                        'HomeFoulsAvg', 'AwayFoulsAvg', 'HomeShotAccuracy', 'AwayShotAccuracy']
    categorical_features = ['HomeTeam', 'AwayTeam']

    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])

    return preprocessor
