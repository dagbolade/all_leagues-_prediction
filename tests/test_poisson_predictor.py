from footy.poisson_predictor import PoissonScorelinePredictor
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# In all the test cases, Arsenal is the Home Team and Chelsea is the Away team

def test_poission_predictor_first():
    # This test case is more of a general scenario
    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}

    predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}
    home_exp, away_exp = predictor.predict_match_goals('Arsenal', 'Chelsea')
    assert abs(home_exp - 1.95) < 0.01
    assert abs(away_exp - 0.816) < 0.01


def test_poisson_predictor_second():
    # This test case if for when it's a high scoring match
    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 2.3, 'Chelsea': 1.9}
    predictor.home_defense_strength = {'Arsenal': 1.1, 'Chelsea': 1.2}
    predictor.away_attack_strength = {'Arsenal' : 2.3, 'Chelsea': 1.8}
    predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}

    predictor.league_averages = {'home_goals': 2, 'away_goals':1.85}
    home_exp, away_exp = predictor.predict_match_goals('Arsenal', 'Chelsea')

    assert abs(home_exp - 4.6) < 0.01
    assert abs(away_exp - 3.663) < 0.01

def test_poission_predictor_third():
    # This test case if for when it's a low scoring match
    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 2.0, 'Chelsea': 1.9}
    predictor.home_defense_strength = {'Arsenal': 0.2, 'Chelsea': 1.2}
    predictor.away_attack_strength = {'Arsenal' : 2.3, 'Chelsea': 1.8}
    predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 0.3}

    predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}
    home_exp, away_exp = predictor.predict_match_goals('Arsenal', 'Chelsea')

    assert abs(home_exp - 0.9) < 0.01
    assert abs(away_exp - 0.432) < 0.01


def test_poission_predictor_fourth():
    # Testing the case when home_expected becomes lesser than 0.1 and so, the new home_exp value becomes 0.1

    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 0.1, 'Chelsea': 0.1}
    predictor.home_defense_strength = {'Arsenal': 0.1, 'Chelsea': 0.1}
    predictor.away_attack_strength = {'Arsenal' : 0.1, 'Chelsea': 0.1}
    predictor.away_defense_strength = {'Arsenal': 0.1, 'Chelsea': 0.1}

    predictor.league_averages = {'home_goals': 0.5, 'away_goals': 0.5}
    home_exp, away_exp = predictor.predict_match_goals('Arsenal', 'Chelsea')

    assert abs(home_exp - 0.1) < 0.01
    assert abs(away_exp - 0.1) < 0.01

def test_poission_predictor_fifth():
    # Testing the case when there is an error in the entries and the outputs get hardcoded to 1.4 and 1.1 for home_expected and away_expected respectively

    predictor = PoissonScorelinePredictor()
    home_exp, away_exp = predictor.predict_match_goals('Arsenal', 'Chelsea')

    predictor.home_attack_strength = {'Arsenal' : 'Random', 'Chelsea': 0.1}
    predictor.home_defense_strength = {'Arsenal': 0.1, 'Chelsea': 0.1}
    predictor.away_attack_strength = {'Arsenal' : 0.1, 'Chelsea': 0.1}
    predictor.away_defense_strength = {'Arsenal': 0.1, 'Chelsea': 0.1}

    predictor.league_averages = {'home_goals': 0.5, 'away_goals': 0.5}
    

    assert (home_exp, away_exp) == (1.4, 1.1)  


"""
The next three functions below to test test_predict_scoreline_probabilities are being written while assuming that inside the function predict_match_goals, we have the required input dictionaries defined with the two test teams being Arsenal and Chelsea. Home Team - Arsenal and Away Team - Chelsea

""" 




def test_predict_scoreline_probabilities_first():
    new_predictor = PoissonScorelinePredictor()

    new_predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    new_predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    new_predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    new_predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
    new_predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}

    result = new_predictor.predict_scoreline_probabilities('Arsenal', 'Chelsea')
    expected_goals_home = result['expected_goals']['home']
    expected_goals_away = result['expected_goals']['away']
    expected_goals_total = result['expected_goals']['total']

    s_probab = result['scoreline_probabilities']
    top_scoreline = result['top_scorelines']
    outcome = result['outcome_probabilities']
    goal_market = result['goal_market_probs']

    # The values below were calculated in a different file called poisson_val.py for testing purposes. For reference, you can check that file under the tests folder

    assert abs(expected_goals_home - 1.95) < 0.01
    assert abs(expected_goals_away- 0.816) < 0.01
    assert abs(expected_goals_total - 2.766) < 0.01

    assert 'scoreline_probabilities' in result
    assert 'top_scorelines' in result
    assert 'outcome_probabilities' in result
    assert 'goal_market_probs' in result

    

    



    
def test_predict_scoreline_probabilities_two():
    new_predictor2 = PoissonScorelinePredictor()
    new_predictor2.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    new_predictor2.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    new_predictor2.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    new_predictor2.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
    new_predictor2.league_averages = {'home_goals': 1.5, 'away_goals':1.2}

    result = new_predictor2.predict_scoreline_probabilities('PSV', 'Ajax')

    expected_goals_home = result['expected_goals']['home']
    expected_goals_away = result['expected_goals']['away']
    expected_goals_total = result['expected_goals']['total']

    s_probab = result['scoreline_probabilities']
    top_scoreline = result['top_scorelines']
    outcome = result['outcome_probabilities']
    goal_market = result['goal_market_probs']

    assert abs(expected_goals_home - 1.5) < 0.01
    assert abs(expected_goals_away - 1.2) < 0.01
    assert abs(expected_goals_total - 2.7) < 0.01


    assert 'scoreline_probabilities' in result
    assert 'top_scorelines' in result
    assert 'outcome_probabilities' in result
    assert 'goal_market_probs' in result

    
    

def test_predict_scoreline_probabilities_three():
    new_predictor3 = PoissonScorelinePredictor()

    new_predictor3.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    new_predictor3.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    new_predictor3.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    new_predictor3.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
    new_predictor3.league_averages = {'home_goals': 1.5, 'away_goals':1.2}

    result = new_predictor3.predict_scoreline_probabilities(2,3)
    # The outputs here are going to be the same as in the case above where we gave wrong teams as inputs

    expected_goals_home = result['expected_goals']['home']
    expected_goals_away = result['expected_goals']['away']
    expected_goals_total = result['expected_goals']['total']

    s_probab = result['scoreline_probabilities']
    top_scoreline = result['top_scorelines']
    outcome = result['outcome_probabilities']
    goal_market = result['goal_market_probs']


    assert abs(expected_goals_home - 1.5) < 0.01
    assert abs(expected_goals_away - 1.2) < 0.01
    assert abs(expected_goals_total - 2.7) < 0.01

    assert 'scoreline_probabilities' in result
    assert 'top_scorelines' in result
    assert 'outcome_probabilities' in result
    assert 'goal_market_probs' in result





def test_predict_scoreline_probabilities_fourth():
    new_predictor4 = PoissonScorelinePredictor()

    new_predictor4.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    new_predictor4.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    new_predictor4.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    new_predictor4.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}

    result = new_predictor4.predict_scoreline_probabilities('Arsenal', 'Chelsea')

    # The outputs here are going to be the same as in the case above where we gave wrong teams as inputs

    expected_goals_home = result['expected_goals']['home']
    expected_goals_away = result['expected_goals']['away']
    expected_goals_total = result['expected_goals']['total']

    s_probab = result['scoreline_probabilities']
    top_scoreline = result['top_scorelines']
    outcome = result['outcome_probabilities']
    goal_market = result['goal_market_probs']

    assert abs(expected_goals_home - 1.4) < 0.01
    assert abs(expected_goals_away - 1.1) < 0.01
    assert abs(expected_goals_total - 2.5) < 0.01

    assert 'scoreline_probabilities' in result
    assert 'top_scorelines' in result
    assert 'outcome_probabilities' in result
    assert 'goal_market_probs' in result



# Now we need to test the private helper functions

def test_get_top_scorelines_one():
    # We need a custom made dictionary for this
    predictor = PoissonScorelinePredictor()
    test_scoreline_probs = {
    '0-3': 0.02,
    '2-2': 0.04,
    '1-0': 0.10,
    '3-1': 0.04,
    '0-0': 0.06,
    '1-1': 0.15,
    '0-2': 0.05,
    '2-0': 0.07,
    '1-2': 0.06,
    '2-1': 0.12,
    '3-0': 0.03,
    '0-1': 0.08
    }

    ans = predictor._get_top_scorelines(test_scoreline_probs, 12)

    expected_result = [
    ('1-1', 0.15),
    ('2-1', 0.12),
    ('1-0', 0.10),
    ('0-1', 0.08),
    ('2-0', 0.07),
    ('0-0', 0.06),
    ('1-2', 0.06),
    ('0-2', 0.05),
    ('2-2', 0.04),
    ('3-1', 0.04),
    ('3-0', 0.03),
    ('0-3', 0.02)
    ]


    assert ans == expected_result

    
    

def test_get_top_scorelines_two():
    # Here we try getting the exception by sending in some wrong data
    predictor = PoissonScorelinePredictor()
    test_scoreline_probs = None

    ans = predictor._get_top_scorelines(test_scoreline_probs,12)

    expected_result = [('1-1', 0.15), ('2-1', 0.12), ('1-0', 0.10), ('0-1', 0.08), ('2-0', 0.07)]


    assert ans == expected_result

def test_calculate_outcome_probs_one():
    predictor = PoissonScorelinePredictor()
    test_scoreline_probs = {
    '2-1': 0.12,
    '1-1': 0.15,
    '1-0': 0.10,
    '0-1': 0.08,
    '2-0': 0.07,
    '0-0': 0.06,
    '1-2': 0.06,
    '0-2': 0.05,
    '3-1': 0.04,
    '2-2': 0.04,
    '3-0': 0.03,
    '0-3': 0.02
    }
    expected_outcome_probs = {
        'home_win': 0.36,  
        'draw': 0.25,      
        'away_win': 0.21   
    }

    result = predictor._calculate_outcome_probs(test_scoreline_probs)

    assert result == expected_outcome_probs

def test_calculate_outcome_probs_two():
    predictor = PoissonScorelinePredictor()
    test_scoreline_probs = None

    expected_outcome_probs = {'home_win': 0.45, 'draw': 0.30, 'away_win': 0.25}

    result = predictor._calculate_outcome_probs(test_scoreline_probs)

    assert result == expected_outcome_probs


def get_betting_insights_one():
    # 1st Test case to check the get_beting_insights function's general working when the inputs is correct
    
    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
    predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}

    result = predictor.get_betting_insights('Arsenal', 'Chelsea')

    assert abs(result['match_summary']['expected_total_goals'] - 2.766) < 0.01
    assert result['match_summary']['most_likely_score'] == '1-0'
    assert result['match_summary']['most_likely_outcome'] == 'home_win'
    assert result['high_confidence_bets'] == []
    assert abs(result['goal_markets']['over_2_5'] - 0.5151157058716723) < 0.01
    assert abs(result['goal_markets']['btts_yes'] - 0.47717035335823055) < 0.01
    assert result['exact_scores'][0][0] == '1-0'
    assert abs(result['exact_scores'][0][1] - 0.12455240320666928) < 0.01


def get_betting_insights_two():
    # 2nd test case for get_betting_insight to raise an exception

    predictor = PoissonScorelinePredictor()
    predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
    predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
    predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
    predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}

    result = predictor.get_betting_insights('Arsenal', 'Chelsea')
    assert result['match_summary']['expected_total_goals'] == 2.5
    assert result['match_summary']['most_likely_score'] == '1-1'
    assert result['match_summary']['most_likely_outcome'] == 'home_win'
    assert result['high_confidence_bets'] == ['Over 2.5 Goals (50%)']


