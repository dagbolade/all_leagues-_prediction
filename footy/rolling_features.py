# footy/rolling_features.py

import pandas as pd
import numpy as np


class RollingFeatureGenerator:
    """Handles creation of rolling window features."""

    @staticmethod
    def _calculate_team_form(df: pd.DataFrame, team: str, window: int = 5) -> pd.DataFrame:
        """
        Calculate form-based features for a specific team.

        Args:
            df: Input DataFrame
            team: Team name
            window: Rolling window size

        Returns:
            DataFrame with added form features
        """
        df = df.copy()

        # Home features
        home_mask = df['HomeTeam'] == team
        df.loc[home_mask, 'HomeTeamForm'] = (
            df[home_mask]['FTR']
            .map({'H': 1, 'D': 0.5, 'A': 0})
            .rolling(window, min_periods=1)
            .mean()
        )

        # Away features
        away_mask = df['AwayTeam'] == team
        df.loc[away_mask, 'AwayTeamForm'] = (
            df[away_mask]['FTR']
            .map({'A': 1, 'D': 0.5, 'H': 0})
            .rolling(window, min_periods=1)
            .mean()
        )

        return df

    @staticmethod
    def _calculate_goal_averages(df: pd.DataFrame, team: str, window: int = 5) -> pd.DataFrame:
        """Calculate rolling goal averages for a team."""
        df = df.copy()

        # Away goals
        away_mask = df['AwayTeam'] == team
        df.loc[away_mask, 'AwayGoalsScoredAvg_5'] = (
            df[away_mask]['FTAG'].rolling(window, min_periods=1).mean()
        )
        df.loc[away_mask, 'AwayGoalsConcededAvg_5'] = (
            df[away_mask]['FTHG'].rolling(window, min_periods=1).mean()
        )

        # Home goals
        home_mask = df['HomeTeam'] == team
        df.loc[home_mask, 'HomeGoalsScoredAvg_5'] = (
            df[home_mask]['FTHG'].rolling(window, min_periods=1).mean()
        )
        df.loc[home_mask, 'HomeGoalsConcededAvg_5'] = (
            df[home_mask]['FTAG'].rolling(window, min_periods=1).mean()
        )

        return df

    @staticmethod
    def _calculate_shot_accuracy(df: pd.DataFrame, team: str, window: int = 5) -> pd.DataFrame:
        """Calculate rolling shot accuracy metrics."""
        df = df.copy()

        # Home shot accuracy
        home_mask = df['HomeTeam'] == team
        df.loc[home_mask, 'HomeShotAccuracyRolling'] = (
            df[home_mask]['HST']
            .div(df[home_mask]['HS'])
            .rolling(window, min_periods=1)
            .mean()
        )

        # Away shot accuracy
        away_mask = df['AwayTeam'] == team
        df.loc[away_mask, 'AwayShotAccuracyRolling'] = (
            df[away_mask]['AST']
            .div(df[away_mask]['AS'])
            .rolling(window, min_periods=1)
            .mean()
        )

        return df

    @staticmethod
    def _calculate_foul_averages(df: pd.DataFrame, team: str, window: int = 5) -> pd.DataFrame:
        """Calculate rolling foul averages."""
        df = df.copy()

        # Home fouls
        home_mask = df['HomeTeam'] == team
        df.loc[home_mask, 'HomeFoulsAvg'] = (
            df[home_mask]['HF']
            .rolling(window, min_periods=1)
            .mean()
        )

        # Away fouls
        away_mask = df['AwayTeam'] == team
        df.loc[away_mask, 'AwayFoulsAvg'] = (
            df[away_mask]['AF']
            .rolling(window, min_periods=1)
            .mean()
        )

        return df

    def add_rolling_features(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Add all rolling features to the DataFrame.

        Args:
            df: Input DataFrame
            window: Size of rolling window (default: 5)

        Returns:
            DataFrame with added rolling features
        """
        df = df.copy()
        df = df.sort_values('Date')

        for team in df['HomeTeam'].unique():
            df = self._calculate_team_form(df, team, window)
            df = self._calculate_goal_averages(df, team, window)
            df = self._calculate_shot_accuracy(df, team, window)
            df = self._calculate_foul_averages(df, team, window)

        return df.fillna(0)

# Usage example:
# generator = RollingFeatureGenerator()
# df_with_features = generator.add_rolling_features(df)