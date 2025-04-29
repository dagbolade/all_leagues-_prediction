# footy/load_data.py

import pandas as pd
import numpy as np
import openpyxl
from pathlib import Path


def load_season_data(season_paths):
    """
    Load Excel files containing season data.

    Args:
        season_paths (dict): Dictionary mapping season names to file paths

    Returns:
        tuple: Loaded DataFrames and their sheet names
    """
    data = {}
    sheets = {}

    for season, path in season_paths.items():
        # Load the Excel file
        data[season] = pd.read_excel(path, sheet_name=None)
        # Get sheet names
        sheets[season] = list(data[season].keys())

    return data, sheets


def load_and_merge_seasons(data_2024_2025, data_2023_2024):
    """
    Merge all sheets from both seasons into a single DataFrame.

    Args:
        data_2024_2025 (dict): Dictionary of DataFrames for 2024-2025 season
        data_2023_2024 (dict): Dictionary of DataFrames for 2023-2024 season

    Returns:
        pd.DataFrame: Combined DataFrame with all seasons and leagues
    """
    merged_data = []
    sheets_2024_2025 = list(data_2024_2025.keys())

    for sheet_name in sheets_2024_2025:
        # Load data for 2024-2025 and add season and league columns
        df_2024_2025 = data_2024_2025[sheet_name].copy()
        df_2024_2025['Season'] = '2024-2025'
        df_2024_2025['League'] = sheet_name

        # Load data for 2023-2024 and add season and league columns
        df_2023_2024 = data_2023_2024[sheet_name].copy()
        df_2023_2024['Season'] = '2023-2024'
        df_2023_2024['League'] = sheet_name

        # Append both dataframes to the list
        merged_data.append(pd.concat([df_2024_2025, df_2023_2024], ignore_index=True))

    # Combine all sheets into one DataFrame
    combined_df = pd.concat(merged_data, ignore_index=True)
    return combined_df