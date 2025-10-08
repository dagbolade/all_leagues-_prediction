# Right now, we are going to test only one of the functions
import pandas as pd
import pytest
from main import validate_bayesian_predictions
from main import validate_bayesian_elo_ratings
from main import _season_from_fname


"""
In the function below, we are testing the _season_from_fname function with various kinds of inputs

The first two inputs are checking how does it work in normal scenarios

The third input checks how does it perform in special scenarios like when there's no dates in the name
"""

@pytest.mark.parametrize("num, expected", [
    ("All-Euro-Data-2023-2024", "2023-2024"),
    ("All-American-Data-2000-2004", "2000-2004"),
    ("All-Oceanic-Data", "unknown")
])

def _season_from_fname_test(num, expected):
    assert _season_from_fname(num) == expected

"""
Below is the code for performing testing on the test_validate_bayesian_elo_ratings using

It tests the all edge case and the normal case as well. First input is to test a very general
scenario wherein the dataframe consists of values under the constraints

The second input is to test the maximum constraint.

The third input is to test the minimum constraint.

The fourth input is to test the constraints on keeping the average between 1200 and 1800

The fifth input is to test a scenario where the values are well spread out enough to fulfill the average limit.

"""
@pytest.mark.parametrize("num, expected", [
    (pd.DataFrame({'HomeElo': [1000, 1200, 1400, 1600]}), True),
    (pd.DataFrame({'HomeElo': [1000, 12000, 1400, 1600]}), False),
    (pd.DataFrame({'HomeElo': [1000, 1200, 900, 1600]}), False),
    (pd.DataFrame({'HomeElo': [1200, 1900, 2000, 1950, 1940, 1960, 1990]}), False),
    (pd.DataFrame({'HomeElo': [1000, 1200, 1400, 1600, 1650, 1450, 1350, 1880]}), True),
    (pd.DataFrame({'HomeElo': [1000, 1200, 1400, 1600, 1650, 1450, 1350, 1880, 1310, 1500, 1900, 2000, 1378, 1456, 1010, 1050, 1298, 1314, 1517, 1432, 1492]}), True)
])

def test_validate_bayesian_elo_ratings(num, expected):
    assert validate_bayesian_elo_ratings(num) == expected


"""
The code below is for testing the function test_validate_bayesian_predictions

The first three inputs are to check the behaviour when the inputs are correct

The next three (4,5,6) inputs consists of the cases where the inputs are wrong 

Inputs 7,8,9,10,11,12 are the inputs where we are trying to check what happens when we have all the three inputs and the different scenarios

Inputs 13 - 18 test the scenario when one of the inputs (1.5, 2.5 or 3.5) become unknown and the other two cases are correct and when the other two inputs are wrong (Acc to Bayesian Logic)

"""

@pytest.mark.parametrize("num, expected", [
    ({'Over 1.5 Goals': 'Yes', 'Over 2.5 Goals' : 'No'}, (True, [])),
    ({'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals' : 'No'}, (True, [])),
    ({'Over 1.5 Goals': 'Yes', 'Over 3.5 Goals' : 'No'}, (True, [])),
    ({'Over 1.5 Goals': 'No', 'Over 2.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 1.5 No + Over 2.5 Yes"])),
    ({'Over 2.5 Goals': 'No', 'Over 3.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': 'No', 'Over 3.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 1.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': 'Yes', 'Over 2.5 Goals': 'No', 'Over 3.5 Goals' : 'No'}, (True, [])),
    ({'Over 1.5 Goals': 'No', 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals' : 'No'}, (False, ["Bayesian Logic Error: Over 1.5 No + Over 2.5 Yes"])),
    ({'Over 1.5 Goals': 'Yes', 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals' : 'Yes'}, (True, [])),
    ({'Over 1.5 Goals': 'No', 'Over 2.5 Goals': 'No', 'Over 3.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes", "Bayesian Logic Error: Over 1.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': 'No', 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 1.5 No + Over 2.5 Yes", "Bayesian Logic Error: Over 1.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': 'Yes', 'Over 2.5 Goals': 'No', 'Over 3.5 Goals' : 'Yes'}, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes"])),

    ({'Over 1.5 Goals': '', 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals':'Yes' }, (True, [])),
    ({'Over 1.5 Goals': 123, 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals':'Yes' }, (True, [])),
    ({'Over 1.5 Goals': None, 'Over 2.5 Goals': 'Yes', 'Over 3.5 Goals':'Yes' }, (True, [])),
    ({'Over 1.5 Goals': '', 'Over 2.5 Goals': 'No', 'Over 3.5 Goals':'Yes' }, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': None, 'Over 2.5 Goals': 'No', 'Over 3.5 Goals':'Yes' }, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes"])),
    ({'Over 1.5 Goals': 123, 'Over 2.5 Goals': 'No', 'Over 3.5 Goals':'Yes' }, (False, ["Bayesian Logic Error: Over 2.5 No + Over 3.5 Yes"]))

])

def test_validate_bayesian_predictions(num, expected):
    assert validate_bayesian_predictions(num) == expected


"""
Below is the code for testing the test_enhanced_bayesian
"""
