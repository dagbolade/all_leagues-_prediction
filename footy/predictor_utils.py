# footy/predictor_utils.py

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List, Union


class TeamMapper:
    """Handles team name mappings and standardization."""

    TEAM_MAPPINGS = {
        'Manchester City': 'Man City',
        'Manchester United': 'Man United',
        'Newcastle United': 'Newcastle',
        'Nottingham Forest': "Nott'm Forest",
        'West Ham United': 'West Ham',
        'Wolverhampton Wanderers': 'Wolves',
        'Tottenham Hotspur': 'Tottenham',
        'Brighton & Hove Albion': 'Brighton'
    }

    @classmethod
    def standardize_name(cls, team: str) -> str:
        """Convert team name to standard format."""
        return cls.TEAM_MAPPINGS.get(team, team)


class MatchPredictor:
    """Handles match prediction and stat retrieval."""

    def __init__(self, df: pd.DataFrame, models: Dict):
        self.df = df
        self.models = models
        self.team_mapper = TeamMapper()

        # Updated with goal-specific features
        self.features = [
            # Base features
            'HomeTeam_encoded', 'AwayTeam_encoded',
            'HomeTeamForm', 'AwayTeamForm',
            'HomeGoalsScoredAvg_5', 'AwayGoalsScoredAvg_5',
            'HomeGoalsConcededAvg_5', 'AwayGoalsConcededAvg_5',
            'HomeShotAccuracyRolling', 'AwayShotAccuracyRolling',
            'HomeFoulsAvg', 'AwayFoulsAvg',
            # Goal-specific features
            'HomeScoringRate_5', 'AwayScoringRate_5',
            'HomeConcedingRate_5', 'AwayConcedingRate_5',
            'HomeOverRate1.5_5', 'AwayOverRate1.5_5',
            'HomeOverRate2.5_5', 'AwayOverRate2.5_5',
            'HomeTotalGoalsRate_5', 'AwayTotalGoalsRate_5',
            'HomeGoalVariance_5', 'AwayGoalVariance_5',
        ]

        self.task_mapping = {
            'match_outcome': 'Match Outcome',
            'over_1_5': 'Over 1.5 Goals',
            'over_2_5': 'Over 2.5 Goals',
            'btts': 'Both Teams to Score'
        }

    def get_team_stats(self, team: str, is_home: bool = True) -> Optional[Dict]:
        """Get latest statistics for a team."""
        team = self.team_mapper.standardize_name(team)

        try:
            team_col = 'HomeTeam' if is_home else 'AwayTeam'
            team_data = self.df[self.df[team_col] == team].sort_values('Date').iloc[-1]

            prefix = 'Home' if is_home else 'Away'
            stats = {}

            # Get all relevant features for the team
            for feature in self.features:
                if feature.startswith(prefix):
                    stats[feature] = float(team_data[feature])

            return stats

        except Exception as e:
            print(f"Error getting stats for {team}: {str(e)}")
            return None

    def predict_match(self, home_team: str, away_team: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Make predictions for a match."""
        try:
            home_stats = self.get_team_stats(home_team, is_home=True)
            away_stats = self.get_team_stats(away_team, is_home=False)

            if home_stats is None or away_stats is None:
                return None, None

            match_data = pd.DataFrame([{**home_stats, **away_stats}])[self.features]

            predictions = {}
            probabilities = {}

            for task_name, model in self.models.items():
                display_name = self.task_mapping.get(task_name, task_name)

                # HOTFIX: Remove `use_label_encoder` right before predict
                if hasattr(model, 'use_label_encoder'):
                    try:
                        delattr(model, 'use_label_encoder')
                    except Exception as e:
                        print(f"Warning deleting use_label_encoder from {task_name}: {str(e)}")

                probs = model.predict_proba(match_data)[0]

                if task_name == 'match_outcome':
                    pred_idx = np.argmax(probs)
                    predictions[display_name] = ['Home Win', 'Draw', 'Away Win'][pred_idx]
                    probabilities[display_name] = {
                        'Home Win': f"{probs[0]:.2%}",
                        'Draw': f"{probs[1]:.2%}",
                        'Away Win': f"{probs[2]:.2%}"
                    }
                else:
                    predictions[display_name] = 'Yes' if probs[1] > 0.5 else 'No'
                    probabilities[display_name] = f"{probs[1]:.2%}"

            return predictions, probabilities

        except Exception as e:
            print(f"Error predicting {home_team} vs {away_team}: {str(e)}")
            return None, None

    def predict_matches(self, matches: List[Tuple[str, str]]) -> None:
        """Predict multiple matches and print results."""
        print("\nMatch Predictions:")
        for home_team, away_team in matches:
            print(f"\n{home_team} vs {away_team}")

            predictions, probabilities = self.predict_match(home_team, away_team)

            if predictions and probabilities:
                print("\nPredictions:")
                for task, pred in predictions.items():
                    print(f"{task}: {pred}")

                print("\nProbabilities:")
                for task, prob in probabilities.items():
                    if isinstance(prob, dict):
                        print(f"\n{task}:")
                        for outcome, probability in prob.items():
                            print(f"  {outcome}: {probability}")
                    else:
                        print(f"{task}: {prob}")
            print("-" * 50)