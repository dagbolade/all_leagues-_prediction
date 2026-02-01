"""
NFL Feature Engineering - American Football specific features

Features include:
- Offensive metrics (yards, points, turnovers)
- Defensive metrics (yards allowed, sacks, interceptions)
- Special teams performance
- QB performance metrics
- Home field advantage
- ELO ratings
- Rolling form (L3, L5, L8 games)
- Head-to-head analysis
- Division/conference performance
- Weather impact (when available)
- Rest days between games
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class NFLFeatureEngineer:
    """Feature engineering for NFL predictions."""

    def __init__(self):
        self.feature_names = []
        self.elo_k_factor = 20  # K-factor for ELO ratings
        self.elo_initial = 1500  # Initial ELO rating
        self.home_field_advantage = 65  # Points added to home team ELO

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all NFL features.

        Args:
            df: Raw NFL data

        Returns:
            DataFrame with engineered features
        """
        print("[NFL] Engineering NFL features...")

        df = df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        # Basic features
        df = self._add_basic_features(df)

        # ELO ratings
        df = self._add_elo_ratings(df)

        # Rolling team performance
        df = self._add_rolling_performance(df)

        # Offensive features
        df = self._add_offensive_features(df)

        # Defensive features
        df = self._add_defensive_features(df)

        # Point differential trends
        df = self._add_point_differential_features(df)

        # Head-to-head features
        df = self._add_h2h_features(df)

        # Rest/schedule features
        df = self._add_rest_features(df)

        # Situational features (division, playoff implications)
        df = self._add_situational_features(df)

        # Week-based features
        df = self._add_week_features(df)

        self.feature_names = [col for col in df.columns if col not in [
            'Date', 'Week', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore', 'Result',
            'League', 'Season'
        ]]

        print(f"[NFL] Created {len(self.feature_names)} NFL features")

        return df

    def _add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic calculated features."""
        # Point differential
        df['PointDiff'] = df['HomeScore'] - df['AwayScore']

        # Total points
        df['TotalPoints'] = df['HomeScore'] + df['AwayScore']

        # Over/under thresholds
        for threshold in [37.5, 40.5, 43.5, 47.5, 50.5]:
            df[f'Over{threshold}'] = (df['TotalPoints'] > threshold).astype(int)

        # Close game indicator (within 3 points - one possession)
        df['CloseGame'] = (df['PointDiff'].abs() <= 3).astype(int)

        # One-score game (within 7-8 points)
        df['OneScoreGame'] = (df['PointDiff'].abs() <= 8).astype(int)

        # Blowout indicator (>= 17 points)
        df['Blowout'] = (df['PointDiff'].abs() >= 17).astype(int)

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
            expected_home = 1 / (1 + 10 ** ((away_elo - home_elo - self.home_field_advantage) / 400))
            expected_away = 1 - expected_home

            # Actual scores
            actual_home = 1 if row['Result'] == 'H' else (0.5 if row['Result'] == 'D' else 0)
            actual_away = 1 if row['Result'] == 'A' else (0.5 if row['Result'] == 'D' else 0)

            # Margin of victory multiplier (NFL-specific)
            mov_multiplier = np.log(abs(row['PointDiff']) + 1)

            # Update ELO
            elo_ratings[home_team] += self.elo_k_factor * mov_multiplier * (actual_home - expected_home)
            elo_ratings[away_team] += self.elo_k_factor * mov_multiplier * (actual_away - expected_away)

        return df

    def _add_rolling_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling performance metrics."""
        for window in [3, 5, 8]:
            df[f'Home_WinRate_L{window}'] = 0.0
            df[f'Away_WinRate_L{window}'] = 0.0

            for team in df['HomeTeam'].unique():
                team_games = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].copy()

                # Calculate wins
                team_games['Win'] = 0.0
                team_games.loc[(team_games['HomeTeam'] == team) & (team_games['Result'] == 'H'), 'Win'] = 1.0
                team_games.loc[(team_games['AwayTeam'] == team) & (team_games['Result'] == 'A'), 'Win'] = 1.0
                team_games.loc[team_games['Result'] == 'D', 'Win'] = 0.5  # Ties count as 0.5

                # Rolling win rate
                team_games[f'WinRate_L{window}'] = team_games['Win'].rolling(window, min_periods=1).mean()

                # Map back to main df
                for idx in team_games.index:
                    if df.at[idx, 'HomeTeam'] == team:
                        df.at[idx, f'Home_WinRate_L{window}'] = team_games.at[idx, f'WinRate_L{window}']
                    elif df.at[idx, 'AwayTeam'] == team:
                        df.at[idx, f'Away_WinRate_L{window}'] = team_games.at[idx, f'WinRate_L{window}']

        return df

    def _add_offensive_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add offensive performance features."""
        for window in [3, 5]:
            df[f'Home_AvgPointsScored_L{window}'] = 0.0
            df[f'Away_AvgPointsScored_L{window}'] = 0.0

            for team in df['HomeTeam'].unique():
                # Home games
                team_home = df[df['HomeTeam'] == team].copy()
                if len(team_home) > 0:
                    team_home[f'AvgPointsScored_L{window}'] = team_home['HomeScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['HomeTeam'] == team, f'Home_AvgPointsScored_L{window}'] = team_home[f'AvgPointsScored_L{window}'].values

                # Away games
                team_away = df[df['AwayTeam'] == team].copy()
                if len(team_away) > 0:
                    team_away[f'AvgPointsScored_L{window}'] = team_away['AwayScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['AwayTeam'] == team, f'Away_AvgPointsScored_L{window}'] = team_away[f'AvgPointsScored_L{window}'].values

        return df

    def _add_defensive_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add defensive performance features."""
        for window in [3, 5]:
            df[f'Home_AvgPointsAllowed_L{window}'] = 0.0
            df[f'Away_AvgPointsAllowed_L{window}'] = 0.0

            for team in df['HomeTeam'].unique():
                # Points allowed when playing at home
                team_home = df[df['HomeTeam'] == team].copy()
                if len(team_home) > 0:
                    team_home[f'AvgPointsAllowed_L{window}'] = team_home['AwayScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['HomeTeam'] == team, f'Home_AvgPointsAllowed_L{window}'] = team_home[f'AvgPointsAllowed_L{window}'].values

                # Points allowed when playing away
                team_away = df[df['AwayTeam'] == team].copy()
                if len(team_away) > 0:
                    team_away[f'AvgPointsAllowed_L{window}'] = team_away['HomeScore'].rolling(window, min_periods=1).mean()
                    df.loc[df['AwayTeam'] == team, f'Away_AvgPointsAllowed_L{window}'] = team_away[f'AvgPointsAllowed_L{window}'].values

        return df

    def _add_point_differential_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add point differential trends."""
        for window in [3, 5, 8]:
            df[f'Home_AvgPointDiff_L{window}'] = 0.0
            df[f'Away_AvgPointDiff_L{window}'] = 0.0

            for team in df['HomeTeam'].unique():
                team_games = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].copy()

                # Calculate point differential for each game
                team_games['TeamPointDiff'] = 0.0
                team_games.loc[team_games['HomeTeam'] == team, 'TeamPointDiff'] = team_games['PointDiff']
                team_games.loc[team_games['AwayTeam'] == team, 'TeamPointDiff'] = -team_games['PointDiff']

                # Rolling average
                team_games[f'AvgPointDiff_L{window}'] = team_games['TeamPointDiff'].rolling(window, min_periods=1).mean()

                # Map back
                for idx in team_games.index:
                    if df.at[idx, 'HomeTeam'] == team:
                        df.at[idx, f'Home_AvgPointDiff_L{window}'] = team_games.at[idx, f'AvgPointDiff_L{window}']
                    elif df.at[idx, 'AwayTeam'] == team:
                        df.at[idx, f'Away_AvgPointDiff_L{window}'] = team_games.at[idx, f'AvgPointDiff_L{window}']

        return df

    def _add_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head matchup features."""
        df['H2H_HomeWins'] = 0
        df['H2H_AwayWins'] = 0
        df['H2H_Ties'] = 0
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
                ties = len(h2h[h2h['Result'] == 'D'])
                away_wins = len(h2h) - home_wins - ties

                df.at[idx, 'H2H_HomeWins'] = home_wins
                df.at[idx, 'H2H_AwayWins'] = away_wins
                df.at[idx, 'H2H_Ties'] = ties
                df.at[idx, 'H2H_TotalGames'] = len(h2h)

        return df

    def _add_rest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rest/schedule features."""
        df['Home_DaysRest'] = 0
        df['Away_DaysRest'] = 0
        df['Home_ShortWeek'] = 0  # Thursday game
        df['Away_ShortWeek'] = 0

        for team in df['HomeTeam'].unique():
            team_games = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].sort_values('Date')

            prev_date = None
            for idx in team_games.index:
                current_date = df.at[idx, 'Date']

                if prev_date is not None and pd.notna(current_date) and pd.notna(prev_date):
                    days_rest = (current_date - prev_date).days

                    if df.at[idx, 'HomeTeam'] == team:
                        df.at[idx, 'Home_DaysRest'] = days_rest
                        df.at[idx, 'Home_ShortWeek'] = 1 if days_rest <= 4 else 0
                    else:
                        df.at[idx, 'Away_DaysRest'] = days_rest
                        df.at[idx, 'Away_ShortWeek'] = 1 if days_rest <= 4 else 0

                prev_date = current_date

        return df

    def _add_situational_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add situational features."""
        # Prime time indicator (if time data available)
        # Division game indicator (would need division data)

        # Month indicators
        if 'Date' in df.columns:
            df['Month'] = pd.to_datetime(df['Date']).dt.month

            # Season phases
            df['EarlySeason'] = (df['Month'].isin([9, 10])).astype(int)
            df['MidSeason'] = (df['Month'].isin([11, 12])).astype(int)
            df['LateSeason'] = (df['Month'].isin([1])).astype(int)

        return df

    def _add_week_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add week-based features."""
        if 'Week' in df.columns:
            # Normalize week number for regular season
            df['WeekNum'] = pd.to_numeric(df['Week'], errors='coerce')
            df['WeekNum'] = df['WeekNum'].fillna(18)  # Playoffs = week 18+

            # Week indicators
            df['Week1'] = (df['WeekNum'] == 1).astype(int)
            df['Playoffs'] = (df['Week'].astype(str).str.contains('Wild|Division|Conference|SuperBowl', na=False)).astype(int)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of all engineered feature names."""
        return self.feature_names
