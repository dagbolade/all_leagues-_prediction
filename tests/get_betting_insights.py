# This file is here to fetch the values from calling the function in reality
from footy.poisson_predictor import PoissonScorelinePredictor
import pandas as pd
from typing import Dict, List, Tuple
from scipy.stats import poisson



predictor = PoissonScorelinePredictor()
predictor.home_attack_strength = {'Arsenal' : 1.3, 'Chelsea': 0.9}
predictor.home_defense_strength = {'Arsenal': 0.8, 'Chelsea': 1.1}
predictor.away_attack_strength = {'Arsenal' : 1.2, 'Chelsea': 0.85}
predictor.away_defense_strength = {'Arsenal': 0.9, 'Chelsea': 1.0}
predictor.league_averages = {'home_goals': 1.5, 'away_goals':1.2}

result = predictor.get_betting_insights('Arsenal', 'Chelsea')

print(result)