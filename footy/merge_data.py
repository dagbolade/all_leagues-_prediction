import pandas as pd

def merge_season_data(data_1, data_2):
    """
    Merge two dictionaries of DataFrames (representing two seasons) into one DataFrame.

    Args:
        data_1 (dict): Sheets and data for the first season.
        data_2 (dict): Sheets and data for the second season.

    Returns:
        pd.DataFrame: Combined data for both seasons with season and league columns.
    """
    merged_data = []
    sheet_names = list(data_1.keys())

    for sheet_name in sheet_names:
        # Process first season
        df_1 = data_1[sheet_name].copy()
        df_1['Season'] = '2024-2025'
        df_1['League'] = sheet_name

        # Process second season
        df_2 = data_2[sheet_name].copy()
        df_2['Season'] = '2023-2024'
        df_2['League'] = sheet_name

        # Concatenate both DataFrames
        merged_data.append(pd.concat([df_1, df_2], ignore_index=True))

    # Combine all sheets into a single DataFrame
    combined_df = pd.concat(merged_data, ignore_index=True)
    return combined_df
