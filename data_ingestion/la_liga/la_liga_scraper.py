import pandas as pd
import os

def load_la_liga(file_path):
    df = pd.read_csv(file_path)

    # Standardize columns
    df.rename(columns={
        'HomeTeamName': 'HomeTeam',
        'AwayTeamName': 'AwayTeam',
        'FTHG': 'FTHG',
        'FTAG': 'FTAG',
        'FTR': 'FTR'
    }, inplace=True)

    # Add league column
    df['League'] = 'La Liga'

    # Fill missing values
    df.fillna(0, inplace=True)

    # Save cleaned data
    output_folder = "../../data/cleaned"
    os.makedirs(output_folder, exist_ok=True)
    df.to_csv(os.path.join(output_folder, "la_liga_cleaned.csv"), index=False)
    print("La Liga data cleaned and saved.")
    return df
