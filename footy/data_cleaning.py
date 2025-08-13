# footy/data_cleaning.py

import pandas as pd
import numpy as np


def explore_dataset(df):
    """
    Explore the dataset and return basic statistics.

    Args:
        df (pd.DataFrame): Input DataFrame

    Returns:
        dict: Dictionary containing exploration results
    """
    exploration = {
        'missing_values': df.isnull().sum(),
        'basic_stats': df.describe(),
        'unique_leagues': df['League'].unique(),
        'unique_seasons': df['Season'].unique(),
        'unique_home_teams': df['HomeTeam'].unique(),
        'unique_away_teams': df['AwayTeam'].unique()
    }

    return exploration


def clean_betting_columns(df):
    """
    Remove betting-related columns from the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame

    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    betting_columns = [col for col in df.columns
                       if any(x in col for x in ['VC', 'VCH', 'IW', 'B365'])]
    return df.drop(columns=betting_columns)