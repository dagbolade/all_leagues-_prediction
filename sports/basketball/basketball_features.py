"""
Basketball Feature Engineering - NBA specific features

Features include:
- Shooting efficiency (FG%, 3P%, FT%, TS%)
- Rebounding metrics
- Ball movement (assists, turnovers)
- Pace and tempo
- Home court advantage
- ELO ratings adapted for basketball
- Rolling form (L5, L10, L20 games)
- Head-to-head analysis
- Back-to-back game fatigue
- Player impact (when available)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class BasketballFeatureEngineer:
    """Feature engineering for basketball predictions."""

    def __init__(self):
        self.feature_names = []
        self.elo_k_factor = 20  # K-factor for ELO ratings
        self.elo_initial = 1500  # Initial ELO rating
        self.home_court_advantage = 100  # Points added to home team ELO

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all basketball features.

        Args:
            df: Raw basketball data

        Returns:
            DataFrame with engineered features
        """
        print("[NBA] Engineering basketball features...")

        df = df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        # Basic features
        df = self._add_basic_features(df)

        # ELO ratings
        df = self._add_elo_ratings(df)

        # Rolling team performance
        df = self._add_rolling_performance(df)

        # Shooting efficiency features
        df = self._add_shooting_features(df)

        # Rebounding features
        df = self._add_rebounding_features(df)

        # Ball movement features
        df = self._add_ball_movement_features(df)

        # Pace features
        df = self._add_pace_features(df)

        # Head-to-head features
        df = self._add_h2h_features(df)

        # Rest/fatigue features
        df = self._add_rest_features(df)

        # Situational features
        df = self._add_situational_features(df)

        # Exclude non-numeric and target columns + DATA LEAKAGE columns
        exclude_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore', 'Result',
            'League', 'Season', 'Week', 'Winner', 'HomeFG', 'AwayFG', 'HomeFG3',
            'AwayFG3', 'HomeFT', 'AwayFT',  # May be float but from raw data
            # DATA LEAKAGE - these contain the game result!
            'PointDiff', 'TotalPoints', 'Over200', 'Over210', 'Over220', 'Over230',
            'CloseGame', 'Blowout'
        ]

        # Only keep numeric columns
        self.feature_names = [col for col in df.columns
                             if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]

        print(f"[NBA] Created {len(self.feature_names)} basketball features")

        return df

    def _add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic calculated features."""
        # Point differential
        df['PointDiff'] = df['HomeScore'] - df['AwayScore']

        # Total points
        df['TotalPoints'] = df['HomeScore'] + df['AwayScore']

        # Over/under thresholds
        for threshold in [200, 210, 220, 230]:
            df[f'Over{threshold}'] = (df['TotalPoints'] > threshold).astype(int)

        # Close game indicator (within 5 points)
        df['CloseGame'] = (df['PointDiff'].abs() <= 5).astype(int)

        # Blowout indicator (>= 20 points)
        df['Blowout'] = (df['PointDiff'].abs() >= 20).astype(int)

        return df

    def _add_elo_ratings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ELO ratings for teams."""
        elo_ratings = {}

        df['HomeElo'] = 0.0
        df['AwayElo'] = 0.0
        df['EloAdvantage'] = 0.0

        for idx, row in df.iterrows():
            home_team = row['HomeTeam']
            away_team = row['AwayTeam']

            # Initialize ELO if new team
            if home_team not in elo_ratings:
                elo_ratings[home_team] = self.elo_initial
            if away_team not in elo_ratings:
                elo_ratings[away_team] = self.elo_initial

            # Get current ELO
            home_elo = elo_ratings[home_team]
            away_elo = elo_ratings[away_team]

            df.at[idx, 'HomeElo'] = home_elo
            df.at[idx, 'AwayElo'] = away_elo
            df.at[idx, 'EloAdvantage'] = home_elo - away_elo

            # Calculate expected scores
            expected_home = 1 / (1 + 10 ** ((away_elo - home_elo - self.home_court_advantage) / 400))
            expected_away = 1 - expected_home

            # Actual scores
            actual_home = 1 if row['Result'] == 'H' else 0
            actual_away = 1 if row['Result'] == 'A' else 0

            # Update ELO
            elo_ratings[home_team] += self.elo_k_factor * (actual_home - expected_home)
            elo_ratings[away_team] += self.elo_k_factor * (actual_away - expected_away)

        return df

    def _add_rolling_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling performance metrics."""
        for window in [5, 10, 20]:
            # Win rate
            for team in df['HomeTeam'].unique():
                team_games = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].copy()

                # Calculate wins
                team_games['Win'] = 0
                team_games.loc[(team_games['HomeTeam'] == team) & (team_games['Result'] == 'H'), 'Win'] = 1
                team_games.loc[(team_games['AwayTeam'] == team) & (team_games['Result'] == 'A'), 'Win'] = 1

                # Rolling win rate
                team_games[f'WinRate_L{window}'] = team_games['Win'].rolling(window, min_periods=1).mean()

                # Map back to main df
                for idx in team_games.index:
                    if df.at[idx, 'HomeTeam'] == team:
                        df.at[idx, f'Home_WinRate_L{window}'] = team_games.at[idx, f'WinRate_L{window}']
                    elif df.at[idx, 'AwayTeam'] == team:
                        df.at[idx, f'Away_WinRate_L{window}'] = team_games.at[idx, f'WinRate_L{window}']

        return df

    def _add_shooting_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add shooting efficiency features (requires detailed stats)."""
        # Placeholder - would need shot data from API
        # For now, use points scored as proxy

        for window in [5, 10]:
            df[f'Home_AvgPoints_L{window}'] = 0.0
            df[f'Away_AvgPoints_L{window}'] = 0.0

            for team in df['HomeTeam'].unique():
                team_home = df[df['HomeTeam'] == team].copy()
                team_away = df[df['AwayTeam'] == team].copy()

                if len(team_home) > 0:
                    team_home[f'AvgPoints_L{window}'] = team_home['HomeScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['HomeTeam'] == team, f'Home_AvgPoints_L{window}'] = team_home[f'AvgPoints_L{window}'].values

                if len(team_away) > 0:
                    team_away[f'AvgPoints_L{window}'] = team_away['AwayScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['AwayTeam'] == team, f'Away_AvgPoints_L{window}'] = team_away[f'AvgPoints_L{window}'].values

        return df

    def _add_rebounding_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rebounding features (requires detailed stats)."""
        # Placeholder - would need rebounding data
        return df

    def _add_ball_movement_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ball movement features (requires detailed stats)."""
        # Placeholder - would need assist/turnover data
        return df

    def _add_pace_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add pace/tempo features."""
        # Use total points as proxy for pace
        for window in [5, 10]:
            df[f'AvgTotalPoints_L{window}'] = df['TotalPoints'].rolling(window, min_periods=1).mean()

        return df

    def _add_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head matchup features."""
        df['H2H_HomeWins'] = 0
        df['H2H_AwayWins'] = 0
        df['H2H_TotalGames'] = 0

        for idx, row in df.iterrows():
            home = row['HomeTeam']
            away = row['AwayTeam']

            # Get all previous meetings
            h2h = df[(((df['HomeTeam'] == home) & (df['AwayTeam'] == away)) |
                      ((df['HomeTeam'] == away) & (df['AwayTeam'] == home))) &
                     (df.index < idx)]

            if len(h2h) > 0:
                home_wins = len(h2h[((h2h['HomeTeam'] == home) & (h2h['Result'] == 'H')) |
                                    ((h2h['AwayTeam'] == home) & (h2h['Result'] == 'A'))])
                away_wins = len(h2h) - home_wins

                df.at[idx, 'H2H_HomeWins'] = home_wins
                df.at[idx, 'H2H_AwayWins'] = away_wins
                df.at[idx, 'H2H_TotalGames'] = len(h2h)

        return df

    def _add_rest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rest/fatigue features."""
        df['Home_DaysRest'] = 0
        df['Away_DaysRest'] = 0
        df['Home_BackToBack'] = 0
        df['Away_BackToBack'] = 0

        for team in df['HomeTeam'].unique():
            team_games = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].sort_values('Date')

            prev_date = None
            for idx in team_games.index:
                current_date = df.at[idx, 'Date']

                if prev_date is not None and pd.notna(current_date) and pd.notna(prev_date):
                    days_rest = (current_date - prev_date).days

                    if df.at[idx, 'HomeTeam'] == team:
                        df.at[idx, 'Home_DaysRest'] = days_rest
                        df.at[idx, 'Home_BackToBack'] = 1 if days_rest == 1 else 0
                    else:
                        df.at[idx, 'Away_DaysRest'] = days_rest
                        df.at[idx, 'Away_BackToBack'] = 1 if days_rest == 1 else 0

                prev_date = current_date

        return df

    def _add_situational_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add situational features."""
        # Month (NBA season dynamics change throughout year)
        if 'Date' in df.columns:
            df['Month'] = pd.to_datetime(df['Date']).dt.month

            # Season phases
            df['EarlySeason'] = (df['Month'].isin([10, 11])).astype(int)
            df['MidSeason'] = (df['Month'].isin([12, 1, 2])).astype(int)
            df['LateSeason'] = (df['Month'].isin([3, 4])).astype(int)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of all engineered feature names."""
        return self.feature_names
