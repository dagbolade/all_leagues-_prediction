# footy/feature_engineering.py

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from itertools import takewhile


class FootballFeatureEngineering:
    """Class for engineering football match features."""

    def __init__(self):
        self.team_encodings = {}
        self.scaler = StandardScaler()
        self.windows = [3, 5, 10]

    def encode_teams(self, df):
        """Convert team names to numerical encodings."""
        df = df.copy()
        if not self.team_encodings:
            all_teams = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
            self.team_encodings = {team: idx for idx, team in enumerate(sorted(all_teams))}

        df['HomeTeam_encoded'] = df['HomeTeam'].map(self.team_encodings)
        df['AwayTeam_encoded'] = df['AwayTeam'].map(self.team_encodings)
        return df

    def create_base_features(self, df):
        """Create fundamental match statistics features."""
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'])

        # Calculate total goals
        df['TotalGoals'] = df['FTHG'] + df['FTAG']

        # Calculate BTTS
        df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)

        # Calculate over/under
        for threshold in [1.5, 2.5, 3.5]:
            df[f'Over{threshold}'] = (df['TotalGoals'] > threshold).astype(int)

        return df

    def create_form_features(self, df, windows=[3, 5, 10]):
        """Create rolling window form-based features."""
        df = df.copy()
        for window in windows:
            for team_type in ['Home', 'Away']:
                team_col = f'{team_type}Team'
                goals_for = 'FTHG' if team_type == 'Home' else 'FTAG'
                goals_against = 'FTAG' if team_type == 'Home' else 'FTHG'

                # Goals scoring form
                df[f'{team_type}ScoringForm_{window}'] = df.groupby(team_col)[goals_for].transform(
                    lambda x: x.rolling(window, min_periods=1).mean())

                # Goals conceding form
                df[f'{team_type}ConcedingForm_{window}'] = df.groupby(team_col)[goals_against].transform(
                    lambda x: x.rolling(window, min_periods=1).mean())

                # Results form
                df[f'{team_type}Form_{window}'] = df.groupby(team_col)['FTR'].transform(
                    lambda x: x.map({'H' if team_type == 'Home' else 'A': 1,
                                     'D': 0.5,
                                     'A' if team_type == 'Home' else 'H': 0})
                    .rolling(window, min_periods=1).mean())

                # BTTS form
                df[f'{team_type}BTTSForm_{window}'] = df.groupby(team_col)['BTTS'].transform(
                    lambda x: x.rolling(window, min_periods=1).mean())

                # Over/Under form
                for threshold in [1.5, 2.5]:
                    df[f'{team_type}Over{threshold}Form_{window}'] = df.groupby(team_col)[f'Over{threshold}'].transform(
                        lambda x: x.rolling(window, min_periods=1).mean())

        return df

    def create_advanced_metrics(self, df):
        """Create advanced performance metrics."""
        df = df.copy()
        for team_type in ['Home', 'Away']:
            shots = 'HS' if team_type == 'Home' else 'AS'
            shots_target = 'HST' if team_type == 'Home' else 'AST'
            goals = 'FTHG' if team_type == 'Home' else 'FTAG'

            # Shot efficiency
            df[f'{team_type}ShotAccuracy'] = np.where(df[shots] > 0,
                                                      df[shots_target] / df[shots], 0)

            # Goal conversion
            df[f'{team_type}GoalConversion'] = np.where(df[shots_target] > 0,
                                                        df[goals] / df[shots_target], 0)

            # Expected goals (simple model)
            df[f'{team_type}xG'] = (df[shots] * 0.1 +
                                    df[shots_target] * 0.3)

        return df

    def create_team_strength_indicators(self, df):
        """Create relative team strength indicators."""
        df = df.copy()
        for team_type in ['Home', 'Away']:
            team_col = f'{team_type}Team'

            # Attack strength
            df[f'{team_type}AttackStrength'] = (
                    df[f'{team_type}ScoringForm_5'] /
                    df.groupby('League')[f'{team_type}ScoringForm_5'].transform('mean')
            )

            # Defense strength
            df[f'{team_type}DefenseStrength'] = (
                    df[f'{team_type}ConcedingForm_5'] /
                    df.groupby('League')[f'{team_type}ConcedingForm_5'].transform('mean')
            )

        return df

    def create_match_context(self, df):
        """Create contextual match features."""
        df = df.copy()
        # Season progress
        df['SeasonProgress'] = df.groupby(['League', 'Season'])['Date'].transform(
            lambda x: (x - x.min()) / (x.max() - x.min()))

        # Days rest
        df['HomeDaysRest'] = df.groupby('HomeTeam')['Date'].diff().dt.days
        df['AwayDaysRest'] = df.groupby('AwayTeam')['Date'].diff().dt.days

        # Head-to-head history
        h2h = df.groupby(['HomeTeam', 'AwayTeam']).agg({
            'FTR': lambda x: (x == 'H').mean(),
            'TotalGoals': 'mean',
            'BTTS': 'mean'
        }).reset_index()

        h2h.columns = ['HomeTeam', 'AwayTeam', 'H2H_HomeWinRate', 'H2H_AvgGoals', 'H2H_BTTSRate']
        df = df.merge(h2h, on=['HomeTeam', 'AwayTeam'], how='left')

        return df

    def create_goal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive goal-related features."""
        df = df.copy()

        # Base goal features
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['GoalDiff'] = df['FTHG'] - df['FTAG']
        df['Over1.5'] = (df['TotalGoals'] > 1.5).astype(int)
        df['Over2.5'] = (df['TotalGoals'] > 2.5).astype(int)

        # Create features for each team
        for team_type in ['Home', 'Away']:
            team_col = f'{team_type}Team'
            goals_for = 'FTHG' if team_type == 'Home' else 'FTAG'
            goals_against = 'FTAG' if team_type == 'Home' else 'FTHG'

            # Calculate for different window sizes
            for window in self.windows:
                # Scoring patterns
                df[f'{team_type}ScoringRate_{window}'] = (
                    df.groupby(team_col)[goals_for]
                    .transform(lambda x: x.rolling(window, min_periods=1).mean())
                )

                # Conceding patterns
                df[f'{team_type}ConcedingRate_{window}'] = (
                    df.groupby(team_col)[goals_against]
                    .transform(lambda x: x.rolling(window, min_periods=1).mean())
                )

                # Over rates
                for threshold in [1.5, 2.5]:
                    df[f'{team_type}OverRate{threshold}_{window}'] = (
                        df.groupby(team_col)[f'Over{threshold}']
                        .transform(lambda x: x.rolling(window, min_periods=1).mean())
                    )

                # Game intensity features
                df[f'{team_type}TotalGoalsRate_{window}'] = (
                    df.groupby(team_col)['TotalGoals']
                    .transform(lambda x: x.rolling(window, min_periods=1).mean())
                )

                # Consistency metrics
                df[f'{team_type}GoalVariance_{window}'] = (
                    df.groupby(team_col)['TotalGoals']
                    .transform(lambda x: x.rolling(window, min_periods=1).std())
                )

        # Add time-based features
        df['DayOfWeek'] = pd.to_datetime(df['Date']).dt.dayofweek
        df['Month'] = pd.to_datetime(df['Date']).dt.month

        # Add league average goals
        df['LeagueAvgGoals'] = df.groupby('League')['TotalGoals'].transform('mean')

        # Team goal-scoring potential
        df['CombinedGoalPotential'] = (
                                              df['HomeScoringRate_5'] +
                                              df['AwayScoringRate_5'] +
                                              df['HomeConcedingRate_5'] +
                                              df['AwayConcedingRate_5']
                                      ) / 4

        return df

    def add_h2h_goal_features(self, df):
        """Add head-to-head goal features."""
        df = df.copy()
        h2h = df.groupby(['HomeTeam', 'AwayTeam']).agg({
            'FTHG': 'mean',
            'FTAG': 'mean',
            'TotalGoals': 'mean'
        }).reset_index()

        h2h.columns = ['HomeTeam', 'AwayTeam', 'H2H_AvgHomeGoals', 'H2H_AvgAwayGoals', 'H2H_AvgGoals']
        df = df.merge(h2h, on=['HomeTeam', 'AwayTeam'], how='left')

        # H2H over/under rates
        for threshold in [1.5, 2.5]:
            h2h[f'H2H_Over{threshold}Rate'] = (h2h['H2H_AvgGoals'] > threshold).astype(int)

        h2h = h2h.drop('H2H_AvgGoals', axis=1)
        df = df.merge(h2h, on=['HomeTeam', 'AwayTeam'], how='left')

        return df

    def engineer_features(self, df):
        """Run complete feature engineering pipeline."""
        print("Starting feature engineering process...")
        df = df.copy()

        # Execute each step in sequence
        print("Creating base features...")
        df = self.create_base_features(df)

        print("Creating form features...")
        df = self.create_form_features(df)

        print("Creating advanced metrics...")
        df = self.create_advanced_metrics(df)

        print("Creating team strength indicators...")
        df = self.create_team_strength_indicators(df)

        print("Creating match context features...")
        df = self.create_match_context(df)

        print("Creating goal features...")
        df = self.create_goal_features(df)

        print("Adding H2H goal features...")
        df = self.add_h2h_goal_features(df)

        # Handle missing values and scale
        print("Handling missing values and scaling features...")
        df = df.fillna(0)
        numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
        df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])

        print("Feature engineering completed.")
        return df