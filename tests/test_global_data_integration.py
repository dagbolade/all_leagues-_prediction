from global_data_integration import GlobalDataIntegrator
import pytest 
import sys
import os
from pathlib import Path

# Get the project root directory (parent of 'tests' folder)
current_dir = Path(__file__).resolve().parent  # tests/
project_root = current_dir.parent              # project root
sys.path.insert(0, str(project_root))
import pandas as pd


# We will first test the function standardize_dataframe

def test_standardize_dataframe():
    predictor = GlobalDataIntegrator()

    input_df = pd.DataFrame({
    'Date': ['2021-08-15', '2021-08-22', '2021-09-01'],
    'Home': ['Boca Juniors', 'River Plate', 'Racing Club'],
    'Away': ['River Plate', 'Independiente', 'Boca Juniors'],
    'HG': [2, 1, 0],
    'AG': [1, 1, 2],
    'Res': ['H', 'D', 'A'],
    'Season': ['2021/22', '2021/22', '2021/22'],
    'PSCH': [1.75, 2.10, 1.50],
    'PSCD': [3.40, 3.20, 3.80],
    'PSCA': [4.50, 3.60, 6.00]
    })

    result = predictor.standardize_dataframe(input_df)

    expected_output = pd.DataFrame({
    'Date': pd.to_datetime(['2021-08-15', '2021-08-22', '2021-09-01']),
    'HomeTeam': ['Boca Juniors', 'River Plate', 'Racing Club'],
    'AwayTeam': ['River Plate', 'Independiente', 'Boca Juniors'],
    'FTHG': [2, 1, 0],
    'FTAG': [1, 1, 2],
    'FTR': ['H', 'D', 'A'],
    'League': ['ARG1', 'ARG1', 'ARG1'],
    'Season': ['2021-2022', '2021-2022', '2021-2022'],
    'B365H': [1.75, 2.10, 1.50],
    'B365D': [3.40, 3.20, 3.80],
    'B365A': [4.50, 3.60, 6.00]
    })

    pd.testing.assert_frame_equal(result, expected_output)