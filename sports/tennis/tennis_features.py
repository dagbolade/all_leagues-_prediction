"""
Tennis Feature Engineering

Features include:
- Player rankings (ATP/WTA)
- Surface-specific performance (hard, clay, grass, carpet)
- Head-to-head records
- Recent form and momentum
- Serve statistics (aces, double faults, first serve %)
- Return statistics
- Break point conversion
- Match duration trends
- Fatigue factors
- Tournament round importance
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class TennisFeatureEngineer:
    """Feature engineering for tennis predictions."""

    def __init__(self):
        self.feature_names = []
        self.elo_initial = 1500
        self.elo_k_factor = 32

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all tennis features.

        Args:
            df: Raw tennis match data

        Returns:
            DataFrame with engineered features
        """
        print("[Tennis] Engineering tennis features...")

        df = df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        # Basic features
        df = self._add_basic_features(df)

        # Ranking features
        df = self._add_ranking_features(df)

        # ELO ratings (surface-specific)
        df = self._add_elo_ratings(df)

        # Form features
        df = self._add_form_features(df)

        # Head-to-head features
        df = self._add_h2h_features(df)

        # Surface-specific features
        df = self._add_surface_features(df)

        # Serve/return features
        df = self._add_serve_return_features(df)

        # Fatigue features
        df = self._add_fatigue_features(df)

        # Tournament context
        df = self._add_tournament_features(df)

        # Exclude non-numeric and target columns + DATA LEAKAGE columns
        exclude_cols = [
            'Date', 'Player1', 'Player2', 'Winner', 'Score',
            'Tournament', 'Round', 'Surface', 'Sets', 'Tour',
            # DATA LEAKAGE - these contain the match result!
            'Upset'  # Calculated from Winner column
        ]

        # Only keep numeric columns
        self.feature_names = [col for col in df.columns
                             if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]

        print(f"[Tennis] Created {len(self.feature_names)} tennis features")

        return df

    def _add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic calculated features."""
        # Match duration proxy (sets played)
        if 'Sets' in df.columns:
            df['TotalSets'] = df['Sets']
        else:
            df['TotalSets'] = 3  # Default best of 3

        # Upset indicator (lower ranked player wins)
        if 'Player1Rank' in df.columns and 'Player2Rank' in df.columns:
            df['Upset'] = ((df['Winner'] == 'Player1') & (df['Player1Rank'] > df['Player2Rank'])) | \
                         ((df['Winner'] == 'Player2') & (df['Player2Rank'] > df['Player1Rank']))
            df['Upset'] = df['Upset'].astype(int)

        return df

    def _add_ranking_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add player ranking features."""
        if 'Player1Rank' in df.columns and 'Player2Rank' in df.columns:
            df['RankDiff'] = df['Player1Rank'] - df['Player2Rank']
            df['RankAvg'] = (df['Player1Rank'] + df['Player2Rank']) / 2
            df['TopRank'] = df[['Player1Rank', 'Player2Rank']].min(axis=1)

            # Ranking categories
            df['Player1Top10'] = (df['Player1Rank'] <= 10).astype(int)
            df['Player2Top10'] = (df['Player2Rank'] <= 10).astype(int)
            df['Player1Top50'] = (df['Player1Rank'] <= 50).astype(int)
            df['Player2Top50'] = (df['Player2Rank'] <= 50).astype(int)

        return df

    def _add_elo_ratings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ELO ratings for players (surface-specific)."""
        # Overall ELO
        elo_overall = {}

        df['Player1Elo'] = 0.0
        df['Player2Elo'] = 0.0
        df['EloAdvantage'] = 0.0

        for idx, row in df.iterrows():
            player1 = row['Player1']
            player2 = row['Player2']

            # Initialize ELO
            if player1 not in elo_overall:
                elo_overall[player1] = self.elo_initial
            if player2 not in elo_overall:
                elo_overall[player2] = self.elo_initial

            # Get current ELO
            p1_elo = elo_overall[player1]
            p2_elo = elo_overall[player2]

            df.at[idx, 'Player1Elo'] = p1_elo
            df.at[idx, 'Player2Elo'] = p2_elo
            df.at[idx, 'EloAdvantage'] = p1_elo - p2_elo

            # Calculate expected scores
            expected_p1 = 1 / (1 + 10 ** ((p2_elo - p1_elo) / 400))
            expected_p2 = 1 - expected_p1

            # Actual scores
            actual_p1 = 1 if row['Winner'] == 'Player1' else 0
            actual_p2 = 1 if row['Winner'] == 'Player2' else 0

            # Update ELO
            elo_overall[player1] += self.elo_k_factor * (actual_p1 - expected_p1)
            elo_overall[player2] += self.elo_k_factor * (actual_p2 - expected_p2)

        return df

    def _add_form_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add recent form features."""
        for window in [5, 10, 20]:
            df[f'Player1_WinRate_L{window}'] = 0.0
            df[f'Player2_WinRate_L{window}'] = 0.0

            for player in pd.concat([df['Player1'], df['Player2']]).unique():
                player_matches = df[(df['Player1'] == player) | (df['Player2'] == player)].copy()

                # Calculate wins
                player_matches['Win'] = 0
                player_matches.loc[(player_matches['Player1'] == player) & (player_matches['Winner'] == 'Player1'), 'Win'] = 1
                player_matches.loc[(player_matches['Player2'] == player) & (player_matches['Winner'] == 'Player2'), 'Win'] = 1

                # Rolling win rate
                player_matches[f'WinRate_L{window}'] = player_matches['Win'].rolling(window, min_periods=1).mean()

                # Map back
                for idx in player_matches.index:
                    if df.at[idx, 'Player1'] == player:
                        df.at[idx, f'Player1_WinRate_L{window}'] = player_matches.at[idx, f'WinRate_L{window}']
                    elif df.at[idx, 'Player2'] == player:
                        df.at[idx, f'Player2_WinRate_L{window}'] = player_matches.at[idx, f'WinRate_L{window}']

        return df

    def _add_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head matchup features — O(n log n) via groupby cumsum."""
        df = df.reset_index(drop=True)
        df['H2H_Player1Wins']  = 0
        df['H2H_Player2Wins']  = 0
        df['H2H_TotalMatches'] = 0

        # Canonical pair key: sort names so A||B == B||A regardless of who is P1/P2
        p1_vals = df['Player1'].values
        p2_vals = df['Player2'].values
        df['_pair'] = [f"{min(a, b)}||{max(a, b)}" for a, b in zip(p1_vals, p2_vals)]

        # For each row, is Player1 the "canonical-first" player (i.e. alphabetically smaller)?
        p1_is_canon = df['Player1'] <= df['Player2']

        # 1 = canonical-first-player won this match
        df['_canon_win'] = (
            (p1_is_canon & (df['Winner'] == 'Player1')) |
            (~p1_is_canon & (df['Winner'] == 'Player2'))
        ).astype(int)

        # Cumulative totals BEFORE the current row (shift by group)
        df['_cum_total']   = df.groupby('_pair').cumcount()           # 0-based = matches before this
        df['_cum_canon_w'] = (df.groupby('_pair')['_canon_win'].cumsum() - df['_canon_win'])

        df['H2H_TotalMatches'] = df['_cum_total'].values

        mask_canon = p1_is_canon.values
        df.loc[mask_canon,  'H2H_Player1Wins'] = df.loc[mask_canon,  '_cum_canon_w'].values
        df.loc[mask_canon,  'H2H_Player2Wins'] = (df.loc[mask_canon,  '_cum_total'] - df.loc[mask_canon,  '_cum_canon_w']).values
        df.loc[~mask_canon, 'H2H_Player2Wins'] = df.loc[~mask_canon, '_cum_canon_w'].values
        df.loc[~mask_canon, 'H2H_Player1Wins'] = (df.loc[~mask_canon, '_cum_total'] - df.loc[~mask_canon, '_cum_canon_w']).values

        df.drop(columns=['_pair', '_canon_win', '_cum_total', '_cum_canon_w'], inplace=True)
        return df

    def _add_surface_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add surface-specific performance features."""
        if 'Surface' not in df.columns:
            df['Surface'] = 'Hard'  # Default

        # Surface encoding
        surface_map = {'Hard': 0, 'Clay': 1, 'Grass': 2, 'Carpet': 3}
        df['Surface_encoded'] = df['Surface'].map(surface_map).fillna(0)

        # Calculate surface-specific win rates
        for surface in ['Hard', 'Clay', 'Grass']:
            df[f'Player1_{surface}WinRate'] = 0.0
            df[f'Player2_{surface}WinRate'] = 0.0

            for player in pd.concat([df['Player1'], df['Player2']]).unique():
                player_surface = df[((df['Player1'] == player) | (df['Player2'] == player)) &
                                   (df['Surface'] == surface)]

                if len(player_surface) > 0:
                    wins = len(player_surface[((player_surface['Player1'] == player) & (player_surface['Winner'] == 'Player1')) |
                                              ((player_surface['Player2'] == player) & (player_surface['Winner'] == 'Player2'))])
                    win_rate = wins / len(player_surface)

                    df.loc[(df['Player1'] == player) & (df['Surface'] == surface), f'Player1_{surface}WinRate'] = win_rate
                    df.loc[(df['Player2'] == player) & (df['Surface'] == surface), f'Player2_{surface}WinRate'] = win_rate

        return df

    def _add_serve_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add serve/return statistics features."""
        # Placeholders for when detailed stats are available
        for stat in ['AceRate', 'DoubleFaultRate', 'FirstServeIn', 'BreakPointsSaved']:
            if f'Player1{stat}' not in df.columns:
                df[f'Player1{stat}'] = 0.5  # Default neutral value
                df[f'Player2{stat}'] = 0.5

        return df

    def _add_fatigue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add fatigue/schedule features."""
        df['Player1_DaysSinceLastMatch'] = 0
        df['Player2_DaysSinceLastMatch'] = 0
        df['Player1_MatchesLast7Days'] = 0
        df['Player2_MatchesLast7Days'] = 0

        for player in pd.concat([df['Player1'], df['Player2']]).unique():
            player_matches = df[(df['Player1'] == player) | (df['Player2'] == player)].sort_values('Date')

            prev_date = None
            for idx in player_matches.index:
                current_date = df.at[idx, 'Date']

                if prev_date is not None and pd.notna(current_date) and pd.notna(prev_date):
                    days_rest = (current_date - prev_date).days

                    if df.at[idx, 'Player1'] == player:
                        df.at[idx, 'Player1_DaysSinceLastMatch'] = days_rest
                    else:
                        df.at[idx, 'Player2_DaysSinceLastMatch'] = days_rest

                    # Count matches in last 7 days
                    recent_matches = player_matches[(player_matches['Date'] < current_date) &
                                                   (player_matches['Date'] >= current_date - timedelta(days=7))]

                    if df.at[idx, 'Player1'] == player:
                        df.at[idx, 'Player1_MatchesLast7Days'] = len(recent_matches)
                    else:
                        df.at[idx, 'Player2_MatchesLast7Days'] = len(recent_matches)

                prev_date = current_date

        return df

    def _add_tournament_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add tournament context features."""
        if 'Round' in df.columns:
            # Tournament round encoding
            round_map = {
                'Final': 7,
                'Semi-Final': 6,
                'Quarter-Final': 5,
                'Round of 16': 4,
                'Round of 32': 3,
                'Round of 64': 2,
                'Qualifying': 1
            }
            df['Round_encoded'] = df['Round'].map(round_map).fillna(3)

        if 'Tournament' in df.columns:
            # Grand Slam indicator
            grand_slams = ['Australian Open', 'French Open', 'Wimbledon', 'US Open']
            df['GrandSlam'] = df['Tournament'].isin(grand_slams).astype(int)

            # Masters/WTA 1000 indicator
            masters = ['Indian Wells', 'Miami', 'Monte Carlo', 'Madrid', 'Rome',
                      'Canada', 'Cincinnati', 'Shanghai', 'Paris']
            df['Masters1000'] = df['Tournament'].str.contains('|'.join(masters), case=False, na=False).astype(int)

        return df

    def get_feature_names(self) -> List[str]:
        """Get list of all engineered feature names."""
        return self.feature_names
