"""
Basketball Feature Engineering

Features:
- ELO ratings (sequential, home court adjusted)
- Rolling form: win rate, avg points, avg points allowed (L5/L10/L20)
- Shooting efficiency: FG%, 3P%, FT% rolling averages
- Rebounding: avg REB, rebound differential
- Ball movement: avg AST, avg TO, AST/TO ratio
- Pace: avg total points, home/away pace
- Head-to-head record
- Rest/fatigue: days rest, back-to-back
- Situational: month, season phase
"""

import pandas as pd
import numpy as np
from typing import List


class BasketballFeatureEngineer:

    def __init__(self):
        self.feature_names = []
        self.elo_k_factor   = 20
        self.elo_initial    = 1500
        self.home_advantage = 100   # ELO points added for home court

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        print("[NBA] Engineering basketball features...")
        df = df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        df = self._add_basic_features(df)
        df = self._add_elo_ratings(df)
        df = self._add_rolling_performance(df)
        df = self._add_shooting_features(df)
        df = self._add_rebounding_features(df)
        df = self._add_ball_movement_features(df)
        df = self._add_pace_features(df)
        df = self._add_h2h_features(df)
        df = self._add_rest_features(df)
        df = self._add_situational_features(df)

        exclude = {
            'Date', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore',
            'Result', 'League', 'Season', 'Week', 'Winner',
            # raw per-game box stats — excluded to avoid data leakage
            # (rolling averages of these ARE kept as features)
            'HomeFG', 'AwayFG', 'HomeFG3', 'AwayFG3', 'HomeFT', 'AwayFT',
            'HomeREB', 'AwayREB', 'HomeAST', 'AwayAST', 'HomeTO', 'AwayTO',
            # targets
            'PointDiff', 'TotalPoints',
            'Over200', 'Over210', 'Over220', 'Over230',
            'CloseGame', 'Blowout',
        }

        self.feature_names = [
            c for c in df.columns
            if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
        ]

        print(f"[NBA] Created {len(self.feature_names)} basketball features")
        return df

    # ── Basic ─────────────────────────────────────────────────────────────────

    def _add_basic_features(self, df):
        df['PointDiff']   = df['HomeScore'] - df['AwayScore']
        df['TotalPoints'] = df['HomeScore'] + df['AwayScore']
        for t in [200, 210, 220, 230]:
            df[f'Over{t}'] = (df['TotalPoints'] > t).astype(int)
        df['CloseGame'] = (df['PointDiff'].abs() <= 5).astype(int)
        df['Blowout']   = (df['PointDiff'].abs() >= 20).astype(int)
        return df

    # ── ELO ───────────────────────────────────────────────────────────────────

    def _add_elo_ratings(self, df):
        elo = {}
        df['HomeElo'] = 0.0
        df['AwayElo'] = 0.0
        df['EloAdvantage'] = 0.0

        for idx, row in df.iterrows():
            h, a = row['HomeTeam'], row['AwayTeam']
            elo.setdefault(h, self.elo_initial)
            elo.setdefault(a, self.elo_initial)

            he, ae = elo[h], elo[a]
            df.at[idx, 'HomeElo']      = he
            df.at[idx, 'AwayElo']      = ae
            df.at[idx, 'EloAdvantage'] = he - ae

            exp_h = 1 / (1 + 10 ** ((ae - he - self.home_advantage) / 400))
            act_h = 1 if row['Result'] == 'H' else 0
            elo[h] += self.elo_k_factor * (act_h - exp_h)
            elo[a] += self.elo_k_factor * ((1 - act_h) - (1 - exp_h))

        return df

    # ── Rolling performance ───────────────────────────────────────────────────

    def _add_rolling_performance(self, df):
        """Win rate + avg points scored/allowed, computed per-team over all games."""
        for team in df['HomeTeam'].unique():
            mask = (df['HomeTeam'] == team) | (df['AwayTeam'] == team)
            tg   = df[mask].copy()

            tg['Win'] = 0
            tg.loc[(tg['HomeTeam'] == team) & (tg['Result'] == 'H'), 'Win'] = 1
            tg.loc[(tg['AwayTeam'] == team) & (tg['Result'] == 'A'), 'Win'] = 1

            tg['PtsFor']     = np.where(tg['HomeTeam'] == team, tg['HomeScore'], tg['AwayScore'])
            tg['PtsAgainst'] = np.where(tg['HomeTeam'] == team, tg['AwayScore'], tg['HomeScore'])

            for w in [5, 10, 20]:
                tg[f'WR_{w}']  = tg['Win'].shift(1).rolling(w, min_periods=1).mean()
                tg[f'PF_{w}']  = tg['PtsFor'].shift(1).rolling(w, min_periods=1).mean()
                tg[f'PA_{w}']  = tg['PtsAgainst'].shift(1).rolling(w, min_periods=1).mean()

            for idx in tg.index:
                prefix = 'Home' if df.at[idx, 'HomeTeam'] == team else 'Away'
                for w in [5, 10, 20]:
                    df.at[idx, f'{prefix}_WinRate_L{w}']   = tg.at[idx, f'WR_{w}']
                    df.at[idx, f'{prefix}_AvgPoints_L{w}'] = tg.at[idx, f'PF_{w}']
                    df.at[idx, f'{prefix}_AvgAllowed_L{w}']= tg.at[idx, f'PA_{w}']

        return df

    # ── Shooting efficiency ───────────────────────────────────────────────────

    def _add_shooting_features(self, df):
        """Rolling averages of FG%, 3P%, FT% per team."""
        if 'HomeFG' not in df.columns:
            return df

        for team in df['HomeTeam'].unique():
            # Home games
            hm = df[df['HomeTeam'] == team].copy()
            if len(hm) > 0:
                for stat, col in [('FG%', 'HomeFG'), ('FG3%', 'HomeFG3'), ('FT%', 'HomeFT')]:
                    rolled = hm[col].shift(1).rolling(5, min_periods=1).mean()
                    df.loc[df['HomeTeam'] == team, f'Home_{stat}_L5'] = rolled.values

            # Away games
            aw = df[df['AwayTeam'] == team].copy()
            if len(aw) > 0:
                for stat, col in [('FG%', 'AwayFG'), ('FG3%', 'AwayFG3'), ('FT%', 'AwayFT')]:
                    rolled = aw[col].shift(1).rolling(5, min_periods=1).mean()
                    df.loc[df['AwayTeam'] == team, f'Away_{stat}_L5'] = rolled.values

        return df

    # ── Rebounding ────────────────────────────────────────────────────────────

    def _add_rebounding_features(self, df):
        """Rolling avg rebounds and rebound differential."""
        if 'HomeREB' not in df.columns:
            return df

        for team in df['HomeTeam'].unique():
            mask_h = df['HomeTeam'] == team
            mask_a = df['AwayTeam'] == team

            hm = df[mask_h].copy()
            if len(hm) > 0:
                df.loc[mask_h, 'Home_AvgREB_L5'] = (
                    hm['HomeREB'].shift(1).rolling(5, min_periods=1).mean().values)
                df.loc[mask_h, 'Home_RebDiff_L5'] = (
                    (hm['HomeREB'] - hm['AwayREB']).shift(1).rolling(5, min_periods=1).mean().values)

            aw = df[mask_a].copy()
            if len(aw) > 0:
                df.loc[mask_a, 'Away_AvgREB_L5'] = (
                    aw['AwayREB'].shift(1).rolling(5, min_periods=1).mean().values)
                df.loc[mask_a, 'Away_RebDiff_L5'] = (
                    (aw['AwayREB'] - aw['HomeREB']).shift(1).rolling(5, min_periods=1).mean().values)

        return df

    # ── Ball movement ─────────────────────────────────────────────────────────

    def _add_ball_movement_features(self, df):
        """Rolling avg assists, turnovers, and AST/TO ratio."""
        if 'HomeAST' not in df.columns:
            return df

        for team in df['HomeTeam'].unique():
            mask_h = df['HomeTeam'] == team
            mask_a = df['AwayTeam'] == team

            hm = df[mask_h].copy()
            if len(hm) > 0:
                ast  = hm['HomeAST'].shift(1).rolling(5, min_periods=1).mean()
                to   = hm['HomeTO'].shift(1).rolling(5, min_periods=1).mean()
                df.loc[mask_h, 'Home_AvgAST_L5']   = ast.values
                df.loc[mask_h, 'Home_AvgTO_L5']    = to.values
                df.loc[mask_h, 'Home_ASTO_Ratio_L5'] = (ast / to.replace(0, np.nan)).values

            aw = df[mask_a].copy()
            if len(aw) > 0:
                ast  = aw['AwayAST'].shift(1).rolling(5, min_periods=1).mean()
                to   = aw['AwayTO'].shift(1).rolling(5, min_periods=1).mean()
                df.loc[mask_a, 'Away_AvgAST_L5']   = ast.values
                df.loc[mask_a, 'Away_AvgTO_L5']    = to.values
                df.loc[mask_a, 'Away_ASTO_Ratio_L5'] = (ast / to.replace(0, np.nan)).values

        return df

    # ── Pace ──────────────────────────────────────────────────────────────────

    def _add_pace_features(self, df):
        """Rolling avg total points (global pace proxy) + per-team offensive pace."""
        for w in [5, 10]:
            df[f'AvgTotalPoints_L{w}'] = (
                df['TotalPoints'].shift(1).rolling(w, min_periods=1).mean())

        # Per-team offensive pace (avg total in their games)
        for team in df['HomeTeam'].unique():
            mask = (df['HomeTeam'] == team) | (df['AwayTeam'] == team)
            tg   = df[mask].copy()
            pace = tg['TotalPoints'].shift(1).rolling(5, min_periods=1).mean()
            for idx in tg.index:
                prefix = 'Home' if df.at[idx, 'HomeTeam'] == team else 'Away'
                df.at[idx, f'{prefix}_PaceL5'] = pace.at[idx]

        return df

    # ── H2H ───────────────────────────────────────────────────────────────────

    def _add_h2h_features(self, df):
        df['H2H_HomeWins']   = 0
        df['H2H_AwayWins']   = 0
        df['H2H_TotalGames'] = 0
        df['H2H_AvgTotal']   = 0.0

        for idx, row in df.iterrows():
            h, a = row['HomeTeam'], row['AwayTeam']
            prev = df[
                (((df['HomeTeam'] == h) & (df['AwayTeam'] == a)) |
                 ((df['HomeTeam'] == a) & (df['AwayTeam'] == h))) &
                (df.index < idx)
            ]
            if len(prev) > 0:
                hw = len(prev[
                    ((prev['HomeTeam'] == h) & (prev['Result'] == 'H')) |
                    ((prev['AwayTeam'] == h) & (prev['Result'] == 'A'))
                ])
                df.at[idx, 'H2H_HomeWins']   = hw
                df.at[idx, 'H2H_AwayWins']   = len(prev) - hw
                df.at[idx, 'H2H_TotalGames'] = len(prev)
                df.at[idx, 'H2H_AvgTotal']   = prev['TotalPoints'].mean()

        return df

    # ── Rest ──────────────────────────────────────────────────────────────────

    def _add_rest_features(self, df):
        df['Home_DaysRest']   = 2
        df['Away_DaysRest']   = 2
        df['Home_BackToBack'] = 0
        df['Away_BackToBack'] = 0

        for team in df['HomeTeam'].unique():
            tg        = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].sort_values('Date')
            prev_date = None
            for idx in tg.index:
                cur = df.at[idx, 'Date']
                if prev_date is not None and pd.notna(cur) and pd.notna(prev_date):
                    rest = (cur - prev_date).days
                    col  = 'Home' if df.at[idx, 'HomeTeam'] == team else 'Away'
                    df.at[idx, f'{col}_DaysRest']   = rest
                    df.at[idx, f'{col}_BackToBack'] = 1 if rest == 1 else 0
                prev_date = cur

        return df

    # ── Situational ───────────────────────────────────────────────────────────

    def _add_situational_features(self, df):
        if 'Date' in df.columns:
            m = pd.to_datetime(df['Date']).dt.month
            df['Month']       = m
            df['EarlySeason'] = m.isin([10, 11]).astype(int)
            df['MidSeason']   = m.isin([12, 1, 2]).astype(int)
            df['LateSeason']  = m.isin([3, 4, 5]).astype(int)
        return df

    def get_feature_names(self) -> List[str]:
        return self.feature_names
