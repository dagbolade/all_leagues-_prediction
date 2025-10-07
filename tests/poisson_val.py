from footy.poisson_predictor import PoissonScorelinePredictor
import pandas as pd
from typing import Dict, List, Tuple
from scipy.stats import poisson


def predict_scoreline_probabilities(home_team: str, away_team: str, max_goals: int = 5) -> Dict:
        """SAFE scoreline probability prediction."""
        predictor = PoissonScorelinePredictor()
        try:
            home_expected, away_expected = predictor.predict_match_goals(home_team, away_team)

            # Calculate probability matrix SAFELY
            scoreline_probs = {}
            total_prob = 0

            for home_goals in range(max_goals + 1):
                for away_goals in range(max_goals + 1):
                    try:
                        # Poisson probability for each team's goals
                        home_prob = poisson.pmf(home_goals, home_expected)
                        away_prob = poisson.pmf(away_goals, away_expected)

                        # Combined probability
                        scoreline_prob = float(home_prob * away_prob)

                        # Safety check
                        if pd.notna(scoreline_prob) and scoreline_prob >= 0:
                            scoreline_probs[f"{home_goals}-{away_goals}"] = scoreline_prob
                            total_prob += scoreline_prob
                        else:
                            scoreline_probs[f"{home_goals}-{away_goals}"] = 0.0

                    except Exception as e:
                        scoreline_probs[f"{home_goals}-{away_goals}"] = 0.0

            # Normalize probabilities SAFELY
            if total_prob > 0:
                for scoreline in scoreline_probs:
                    scoreline_probs[scoreline] = scoreline_probs[scoreline] / total_prob
            else:
                # Emergency fallback - equal probabilities
                uniform_prob = 1.0 / len(scoreline_probs)
                for scoreline in scoreline_probs:
                    scoreline_probs[scoreline] = uniform_prob

            return {
                'expected_goals': {
                    'home': home_expected,
                    'away': away_expected,
                    'total': home_expected + away_expected
                },
                'scoreline_probabilities': scoreline_probs,
                'top_scorelines': predictor._get_top_scorelines(scoreline_probs),
                'outcome_probabilities': predictor._calculate_outcome_probs(scoreline_probs),
                'goal_market_probs': predictor._calculate_goal_market_probs(scoreline_probs)
            }

        except Exception as e:
            print(f"   âš ï¸ Error in scoreline prediction: {e}")
            # Return safe defaults
            return predictor._get_default_predictions()


#First test case(Normal / General Execution)
"""
result = predict_scoreline_probabilities('Arsenal', 'Chelsea')

expected_goals_home = result['expected_goals']['home']
expected_goals_away = result['expected_goals']['away']
expected_goals_total = result['expected_goals']['total']

s_probab = result['scoreline_probabilities']
top_scoreline = result['top_scorelines']
outcome = result['outcome_probabilities']
goal_market = result['goal_market_probs']

print(f"Home goals {expected_goals_home}\n")
print(f"Away goals {expected_goals_away}\n")
print(f"Toal goals {expected_goals_total}\n")

print(f"scoreline proabab {s_probab}\n")
print(f'top_scoreline {top_scoreline}\n')
print(f"outcome probab {outcome}\n")

print(f"goal_market_probs {goal_market}\n")
"""

# 2nd test case (Giving values as inputs which are not present in the dictionary)
"""
result = predict_scoreline_probabilities('PSV', 'Ajax')

expected_goals_home = result['expected_goals']['home']
expected_goals_away = result['expected_goals']['away']
expected_goals_total = result['expected_goals']['total']

s_probab = result['scoreline_probabilities']
top_scoreline = result['top_scorelines']
outcome = result['outcome_probabilities']
goal_market = result['goal_market_probs']

print(f"Home goals {expected_goals_home}\n")
print(f"Away goals {expected_goals_away}\n")
print(f"Toal goals {expected_goals_total}\n")

print(f"scoreline proabab {s_probab}\n")
print(f'top_scoreline {top_scoreline}\n')
print(f"outcome probab {outcome}\n")

print(f"goal_market_probs {goal_market}\n")


# 3rd test case (Changing the data type of inputs)
"""




predictor = PoissonScorelinePredictor()
predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}
result = predictor.predict_scoreline_probabilities('Arsenal','Chelsea')

expected_goals_home = result['expected_goals']['home']
expected_goals_away = result['expected_goals']['away']
expected_goals_total = result['expected_goals']['total']

s_probab = result['scoreline_probabilities']
top_scoreline = result['top_scorelines']
outcome = result['outcome_probabilities']
goal_market = result['goal_market_probs']

print(f"Home goals {expected_goals_home}\n")
print(f"Away goals {expected_goals_away}\n")
print(f"Total goals {expected_goals_total}\n")

print(f"scoreline proabab {s_probab}\n")
print(f'top_scoreline {top_scoreline}\n')
print(f"outcome probab {outcome}\n")

print(f"goal_market_probs {goal_market}\n")