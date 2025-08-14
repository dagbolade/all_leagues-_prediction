# footy/feature_engineering.py - ENHANCED WITH BAYESIAN INFERENCE

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


class BayesianFootballFeatureEngineering:
    """Enhanced football feature engineering with Bayesian inference for realistic predictions."""

    def __init__(self):
        self.team_encodings = {}
        self.scaler = StandardScaler()
        self.referee_stats = {}
        self.h2h_deep_stats = {}
        self.bayesian_priors = {}
        self.league_characteristics = {}

    def encode_teams(self, df):
        """Convert team names to numerical encodings with league context."""
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

        # Only create if not already exist (might come from rolling_features)
        if 'TotalGoals' not in df.columns:
            df['TotalGoals'] = df['FTHG'] + df['FTAG']

        if 'BTTS' not in df.columns:
            df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)

        # Create over/under if not exist
        for threshold in [1.5, 2.5, 3.5]:
            col_name = f'Over{threshold}'
            if col_name not in df.columns:
                df[col_name] = (df['TotalGoals'] > threshold).astype(int)

        return df

    def create_bayesian_referee_analysis(self, df):
        """
        🧠 BAYESIAN REFEREE: Use Bayesian updating for referee tendencies.
        """
        df = df.copy()

        if 'Referee' not in df.columns:
            print("⚠️ No referee data available")
            # Add default referee features
            df['RefAvgGoals'] = 2.5
            df['RefHomeBias'] = 0.45
            df['RefCardTendency'] = 4.0
            df['RefOver25Rate'] = 0.55
            return df

        print("🧠 Analyzing referee tendencies with Bayesian updating...")

        # Calculate league priors for referee behavior
        league_priors = self._calculate_referee_league_priors(df)

        # Calculate referee statistics with Bayesian updating
        ref_stats = {}
        for referee in df['Referee'].dropna().unique():
            ref_matches = df[df['Referee'] == referee]
            if len(ref_matches) < 3:  # Skip referees with very few matches
                continue

            # Get league context for this referee
            ref_leagues = ref_matches.get('League', ref_matches.get('Div', 'E0')).mode()
            primary_league = ref_leagues[0] if len(ref_leagues) > 0 else 'E0'

            # Bayesian updating: prior + evidence
            prior = league_priors.get(primary_league, league_priors.get('E0', {}))
            confidence = min(1.0, len(ref_matches) / 20)  # More matches = higher confidence

            # Calculate referee stats with Bayesian combination
            stats = {
                'matches': len(ref_matches),
                'avg_total_goals': self._bayesian_update(
                    prior.get('avg_goals', 2.5),
                    ref_matches['TotalGoals'].mean(),
                    confidence
                ),
                'home_win_rate': self._bayesian_update(
                    prior.get('home_win_rate', 0.45),
                    (ref_matches['FTR'] == 'H').mean(),
                    confidence
                ),
                'over_2_5_rate': self._bayesian_update(
                    prior.get('over_2_5_rate', 0.55),
                    (ref_matches['TotalGoals'] > 2.5).mean(),
                    confidence
                ),
                'btts_rate': self._bayesian_update(
                    prior.get('btts_rate', 0.55),
                    ref_matches['BTTS'].mean(),
                    confidence
                )
            }

            # Add card/foul stats if available
            if all(col in ref_matches.columns for col in ['HY', 'AY']):
                stats['avg_yellow_cards'] = self._bayesian_update(
                    prior.get('avg_cards', 4.0),
                    (ref_matches['HY'] + ref_matches['AY']).mean(),
                    confidence
                )
            else:
                stats['avg_yellow_cards'] = prior.get('avg_cards', 4.0)

            ref_stats[referee] = stats

        self.referee_stats = ref_stats

        # Add Bayesian referee features to dataframe
        df['RefAvgGoals'] = df['Referee'].map(
            lambda x: ref_stats.get(x, {}).get('avg_total_goals', 2.5)
        )
        df['RefHomeBias'] = df['Referee'].map(
            lambda x: ref_stats.get(x, {}).get('home_win_rate', 0.45)
        )
        df['RefCardTendency'] = df['Referee'].map(
            lambda x: ref_stats.get(x, {}).get('avg_yellow_cards', 4.0)
        )
        df['RefOver25Rate'] = df['Referee'].map(
            lambda x: ref_stats.get(x, {}).get('over_2_5_rate', 0.55)
        )

        print(f"✅ Analyzed {len(ref_stats)} referees with Bayesian updating")
        return df

    def _calculate_referee_league_priors(self, df: pd.DataFrame) -> Dict:
        """Calculate league-specific priors for referee behavior."""
        league_priors = {}

        for league in df.get('League', df.get('Div', ['E0'])).unique():
            league_matches = df[df.get('League', df.get('Div', 'E0')) == league]

            if len(league_matches) > 50:
                league_priors[league] = {
                    'avg_goals': league_matches['TotalGoals'].mean(),
                    'home_win_rate': (league_matches['FTR'] == 'H').mean(),
                    'over_2_5_rate': (league_matches['TotalGoals'] > 2.5).mean(),
                    'btts_rate': league_matches.get('BTTS', 0.55).mean() if 'BTTS' in league_matches.columns else 0.55,
                    'avg_cards': (league_matches.get('HY', 0) + league_matches.get('AY',
                                                                                   0)).mean() if 'HY' in league_matches.columns else 4.0
                }
            else:
                # Default priors
                league_priors[league] = {
                    'avg_goals': 2.5,
                    'home_win_rate': 0.45,
                    'over_2_5_rate': 0.55,
                    'btts_rate': 0.55,
                    'avg_cards': 4.0
                }

        return league_priors

    def _bayesian_update(self, prior: float, evidence: float, confidence: float) -> float:
        """Bayesian updating: combine prior belief with evidence."""
        return (1 - confidence) * prior + confidence * evidence

    def create_bayesian_h2h_analysis(self, df):
        """
        🧠 BAYESIAN H2H: Enhanced head-to-head with Bayesian priors.
        """
        df = df.copy()
        df = df.sort_values(['Season', 'Date'])

        print("🧠 Creating Bayesian H2H analysis...")

        # Calculate league-wide H2H priors
        league_h2h_priors = self._calculate_h2h_league_priors(df)

        # Initialize H2H columns with league priors
        df['H2H_HomeWinRate'] = 0.45  # Will be updated with Bayesian calculation
        df['H2H_AvgGoals'] = 2.5
        df['H2H_BTTSRate'] = 0.55
        df['H2H_RecentForm'] = 0.5
        df['H2H_GoalTrend'] = 0.0
        df['H2H_Confidence'] = 0.0  # NEW: Confidence in H2H prediction

        # Process each match efficiently
        unique_matchups = df[['HomeTeam', 'AwayTeam']].drop_duplicates()

        for _, matchup in unique_matchups.iterrows():
            home_team = matchup['HomeTeam']
            away_team = matchup['AwayTeam']

            # Get all matches for this H2H pairing
            matchup_matches = df[
                ((df['HomeTeam'] == home_team) & (df['AwayTeam'] == away_team)) |
                ((df['HomeTeam'] == away_team) & (df['AwayTeam'] == home_team))
                ].sort_values('Date')

            # Calculate Bayesian H2H stats for each match in this pairing
            for idx in matchup_matches.index:
                match_date = df.at[idx, 'Date']
                match_league = df.at[idx, 'League'] if 'League' in df.columns else 'E0'

                # Get PAST H2H matches only (no data leakage)
                past_h2h = matchup_matches[matchup_matches['Date'] < match_date]

                if len(past_h2h) >= 1:  # At least one previous meeting
                    # Get league prior for this matchup
                    league_prior = league_h2h_priors.get(match_league, league_h2h_priors.get('E0', {}))

                    # Calculate confidence based on number of H2H meetings
                    h2h_confidence = min(0.8, len(past_h2h) / 10)  # Max 80% confidence with 10+ meetings

                    # Bayesian updating for home win rate
                    home_wins = len(past_h2h[
                                        ((past_h2h['HomeTeam'] == home_team) & (past_h2h['FTR'] == 'H')) |
                                        ((past_h2h['AwayTeam'] == home_team) & (past_h2h['FTR'] == 'A'))
                                        ])
                    h2h_home_win_rate = home_wins / len(past_h2h)

                    bayesian_home_win_rate = self._bayesian_update(
                        league_prior.get('home_win_rate', 0.45),
                        h2h_home_win_rate,
                        h2h_confidence
                    )

                    # Bayesian updating for average goals
                    h2h_avg_goals = past_h2h['TotalGoals'].mean()
                    bayesian_avg_goals = self._bayesian_update(
                        league_prior.get('avg_goals', 2.5),
                        h2h_avg_goals,
                        h2h_confidence
                    )

                    # Bayesian updating for BTTS rate
                    h2h_btts_rate = past_h2h['BTTS'].mean()
                    bayesian_btts_rate = self._bayesian_update(
                        league_prior.get('btts_rate', 0.55),
                        h2h_btts_rate,
                        h2h_confidence
                    )

                    # Update dataframe with Bayesian H2H stats
                    df.at[idx, 'H2H_HomeWinRate'] = bayesian_home_win_rate
                    df.at[idx, 'H2H_AvgGoals'] = bayesian_avg_goals
                    df.at[idx, 'H2H_BTTSRate'] = bayesian_btts_rate
                    df.at[idx, 'H2H_Confidence'] = h2h_confidence

                    # Recent form (last 3 H2H with Bayesian smoothing)
                    if len(past_h2h) >= 3:
                        recent_h2h = past_h2h.tail(3)
                        recent_home_wins = len(recent_h2h[
                                                   ((recent_h2h['HomeTeam'] == home_team) & (
                                                               recent_h2h['FTR'] == 'H')) |
                                                   ((recent_h2h['AwayTeam'] == home_team) & (recent_h2h['FTR'] == 'A'))
                                                   ])
                        recent_form = recent_home_wins / len(recent_h2h)

                        # Smooth recent form with overall H2H
                        df.at[idx, 'H2H_RecentForm'] = self._bayesian_update(
                            bayesian_home_win_rate,
                            recent_form,
                            0.3  # Give some weight to recent form
                        )

                        # Goal trend with Bayesian smoothing
                        if len(past_h2h) >= 5:
                            recent_goals = recent_h2h['TotalGoals'].mean()
                            older_goals = past_h2h.head(-3)['TotalGoals'].mean()
                            raw_trend = recent_goals - older_goals

                            # Smooth extreme trends
                            df.at[idx, 'H2H_GoalTrend'] = np.clip(raw_trend, -1.0, 1.0)

        print("✅ Bayesian H2H analysis completed")
        return df

    def _calculate_h2h_league_priors(self, df: pd.DataFrame) -> Dict:
        """Calculate league-specific H2H priors."""
        league_priors = {}

        for league in df.get('League', df.get('Div', ['E0'])).unique():
            league_matches = df[df.get('League', df.get('Div', 'E0')) == league]

            if len(league_matches) > 50:
                league_priors[league] = {
                    'home_win_rate': (league_matches['FTR'] == 'H').mean(),
                    'avg_goals': league_matches['TotalGoals'].mean(),
                    'btts_rate': league_matches.get('BTTS', 0.55).mean() if 'BTTS' in league_matches.columns else 0.55
                }
            else:
                league_priors[league] = {
                    'home_win_rate': 0.45,
                    'avg_goals': 2.5,
                    'btts_rate': 0.55
                }

        return league_priors

    def create_bayesian_match_outcome_features(self, df):
        """
        🎯 BAYESIAN MATCH OUTCOMES: Core features for realistic match predictions.
        """
        df = df.copy()

        print("🎯 Creating Bayesian match outcome features...")

        # Use Bayesian Elo if available, otherwise create basic team strength
        if 'HomeElo' not in df.columns or 'AwayElo' not in df.columns:
            print("   ⚠️ Bayesian Elo not found, creating basic team strength")
            df = self._create_basic_team_strength(df)

        # Enhanced match outcome probabilities using multiple factors
        df['MatchOutcome_HomeProb'] = self._calculate_bayesian_home_win_prob(df)
        df['MatchOutcome_DrawProb'] = self._calculate_bayesian_draw_prob(df)
        df['MatchOutcome_AwayProb'] = 1 - df['MatchOutcome_HomeProb'] - df['MatchOutcome_DrawProb']

        # Ensure probabilities sum to 1 and are realistic
        total_prob = df['MatchOutcome_HomeProb'] + df['MatchOutcome_DrawProb'] + df['MatchOutcome_AwayProb']
        df['MatchOutcome_HomeProb'] = df['MatchOutcome_HomeProb'] / total_prob
        df['MatchOutcome_DrawProb'] = df['MatchOutcome_DrawProb'] / total_prob
        df['MatchOutcome_AwayProb'] = df['MatchOutcome_AwayProb'] / total_prob

        # Clip to realistic ranges
        df['MatchOutcome_DrawProb'] = df['MatchOutcome_DrawProb'].clip(0.15, 0.40)

        # Match competitiveness indicator
        df['MatchCompetitiveness'] = 1 - np.abs(df['MatchOutcome_HomeProb'] - df['MatchOutcome_AwayProb'])

        print("✅ Bayesian match outcome features created")
        return df

    def _calculate_bayesian_home_win_prob(self, df: pd.DataFrame) -> pd.Series:
        """Calculate realistic home win probabilities using multiple Bayesian factors."""

        # Base probability from Elo difference
        if 'EloAdvantage' in df.columns:
            elo_home_prob = 1 / (1 + 10 ** (-df['EloAdvantage'] / 400))
        else:
            elo_home_prob = 0.45  # Default

        # Adjust based on team form if available
        if 'HomeForm_5' in df.columns and 'AwayForm_5' in df.columns:
            form_diff = df['HomeForm_5'] - df['AwayForm_5']
            form_adjustment = form_diff * 0.1  # Max 10% adjustment
            elo_home_prob += form_adjustment

        # Adjust based on H2H if available
        if 'H2H_HomeWinRate' in df.columns and 'H2H_Confidence' in df.columns:
            h2h_adjustment = (df['H2H_HomeWinRate'] - 0.45) * df['H2H_Confidence'] * 0.1
            elo_home_prob += h2h_adjustment

        # Realistic bounds
        return elo_home_prob.clip(0.15, 0.70)

    def _calculate_bayesian_draw_prob(self, df: pd.DataFrame) -> pd.Series:
        """Calculate realistic draw probabilities."""

        # Base draw probability
        base_draw_prob = 0.25

        # Increase draw probability for closely matched teams
        if 'EloAdvantage' in df.columns:
            elo_diff = np.abs(df['EloAdvantage'])
            # Closer teams = higher draw probability
            draw_adjustment = (200 - np.minimum(elo_diff, 200)) / 200 * 0.15
            base_draw_prob += draw_adjustment

        # Adjust based on league characteristics
        if 'League' in df.columns:
            # Some leagues have higher draw rates
            league_draw_adjustment = df['League'].map({
                'I1': 0.05,  # Serie A historically higher draws
                'F1': 0.03,  # Ligue 1 slightly higher
                'E0': 0.00,  # Premier League baseline
                'SP1': -0.02,  # La Liga slightly lower
                'D1': -0.01  # Bundesliga slightly lower
            }).fillna(0)
            base_draw_prob += league_draw_adjustment

        return base_draw_prob.clip(0.15, 0.40)

    def _create_basic_team_strength(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create basic team strength if Bayesian Elo not available."""

        team_strength = {}

        for team in df['HomeTeam'].unique():
            team_matches = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)]

            if len(team_matches) > 5:
                home_matches = team_matches[team_matches['HomeTeam'] == team]
                away_matches = team_matches[team_matches['AwayTeam'] == team]

                home_wins = (home_matches['FTR'] == 'H').sum()
                away_wins = (away_matches['FTR'] == 'A').sum()
                total_games = len(team_matches)

                win_rate = (home_wins + away_wins) / total_games
                team_strength[team] = 1400 + (win_rate - 0.4) * 500  # Scale to Elo-like range
            else:
                team_strength[team] = 1500  # Default

        df['HomeElo'] = df['HomeTeam'].map(team_strength)
        df['AwayElo'] = df['AwayTeam'].map(team_strength)
        df['EloAdvantage'] = df['HomeElo'] - df['AwayElo']

        return df

    def create_bayesian_goal_prediction_features(self, df):
        """
        ⚽ BAYESIAN GOALS: Enhanced goal prediction features.
        """
        df = df.copy()

        print("⚽ Creating Bayesian goal prediction features...")

        # Enhanced expected goals using Bayesian team strengths
        if 'ExpectedHomeGoals' in df.columns and 'ExpectedAwayGoals' in df.columns:
            # Use Bayesian expected goals if available
            df['BayesianExpectedTotal'] = df['ExpectedHomeGoals'] + df['ExpectedAwayGoals']
        else:
            # Calculate basic expected goals
            df = self._calculate_basic_expected_goals(df)
            df['BayesianExpectedTotal'] = df['BasicExpectedHomeGoals'] + df['BasicExpectedAwayGoals']

        # Enhanced over/under probabilities with Bayesian smoothing
        df['BayesianOver15Prob'] = self._calculate_bayesian_over_prob(df, 1.5)
        df['BayesianOver25Prob'] = self._calculate_bayesian_over_prob(df, 2.5)
        df['BayesianOver35Prob'] = self._calculate_bayesian_over_prob(df, 3.5)

        # Enhanced BTTS probability
        df['BayesianBTTSProb'] = self._calculate_bayesian_btts_prob(df)

        # Goal scoring patterns
        df['GoalScoringConsistency'] = self._calculate_goal_consistency(df)
        df['GoalVarianceIndicator'] = self._calculate_goal_variance_indicator(df)

        print("✅ Bayesian goal prediction features created")
        return df

    def _calculate_basic_expected_goals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic expected goals if Bayesian not available."""

        team_attack = {}
        team_defense = {}

        # Calculate league averages
        league_avg_home = df['FTHG'].mean()
        league_avg_away = df['FTAG'].mean()

        for team in df['HomeTeam'].unique():
            # Home attack/defense
            home_matches = df[df['HomeTeam'] == team]
            if len(home_matches) > 3:
                team_attack[f"{team}_home"] = home_matches['FTHG'].mean()
                team_defense[f"{team}_home"] = home_matches['FTAG'].mean()
            else:
                team_attack[f"{team}_home"] = league_avg_home
                team_defense[f"{team}_home"] = league_avg_away

            # Away attack/defense
            away_matches = df[df['AwayTeam'] == team]
            if len(away_matches) > 3:
                team_attack[f"{team}_away"] = away_matches['FTAG'].mean()
                team_defense[f"{team}_away"] = away_matches['FTHG'].mean()
            else:
                team_attack[f"{team}_away"] = league_avg_away
                team_defense[f"{team}_away"] = league_avg_home

        # Calculate expected goals
        df['BasicExpectedHomeGoals'] = df.apply(lambda row:
                                                team_attack.get(f"{row['HomeTeam']}_home", league_avg_home) *
                                                team_defense.get(f"{row['AwayTeam']}_away",
                                                                 league_avg_home) / league_avg_home
                                                , axis=1)

        df['BasicExpectedAwayGoals'] = df.apply(lambda row:
                                                team_attack.get(f"{row['AwayTeam']}_away", league_avg_away) *
                                                team_defense.get(f"{row['HomeTeam']}_home",
                                                                 league_avg_away) / league_avg_away
                                                , axis=1)

        return df

    def _calculate_bayesian_over_prob(self, df: pd.DataFrame, threshold: float) -> pd.Series:
        """Calculate Bayesian over/under probabilities."""

        # Base probability from expected total goals
        expected_total = df.get('BayesianExpectedTotal', 2.5)

        # Convert expected goals to probability using Poisson-like distribution
        # Higher expected goals = higher probability of going over threshold
        base_prob = 1 / (1 + np.exp(-(expected_total - threshold) * 2))

        # Adjust based on team over/under history if available
        if f'HomeOverRate{threshold}_5' in df.columns and f'AwayOverRate{threshold}_5' in df.columns:
            team_over_tendency = (df[f'HomeOverRate{threshold}_5'] + df[f'AwayOverRate{threshold}_5']) / 2
            # Combine with base probability
            base_prob = base_prob * 0.7 + team_over_tendency * 0.3

        # Adjust based on referee tendency if available
        if 'RefOver25Rate' in df.columns and threshold == 2.5:
            ref_adjustment = (df['RefOver25Rate'] - 0.55) * 0.1
            base_prob += ref_adjustment

        return base_prob.clip(0.05, 0.95)

    def _calculate_bayesian_btts_prob(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Bayesian Both Teams To Score probability."""

        # Base BTTS probability from expected goals
        home_expected = df.get('ExpectedHomeGoals', 1.4)
        away_expected = df.get('ExpectedAwayGoals', 1.2)

        # Both teams score if both have decent expected goals
        base_btts_prob = (1 - np.exp(-home_expected)) * (1 - np.exp(-away_expected))

        # Adjust based on team BTTS history
        if 'HomeBTTSForm_5' in df.columns and 'AwayBTTSForm_5' in df.columns:
            team_btts_tendency = (df['HomeBTTSForm_5'] + df['AwayBTTSForm_5']) / 2
            base_btts_prob = base_btts_prob * 0.6 + team_btts_tendency * 0.4

        # Adjust based on H2H BTTS rate
        if 'H2H_BTTSRate' in df.columns and 'H2H_Confidence' in df.columns:
            h2h_adjustment = (df['H2H_BTTSRate'] - 0.55) * df['H2H_Confidence'] * 0.2
            base_btts_prob += h2h_adjustment

        return base_btts_prob.clip(0.15, 0.85)

    def _calculate_goal_consistency(self, df: pd.DataFrame) -> pd.Series:
        """Calculate how consistent teams are in their goal scoring."""

        # Use goal variance if available
        if 'HomeGoalVariance_5' in df.columns and 'AwayGoalVariance_5' in df.columns:
            home_consistency = 1 / (1 + df['HomeGoalVariance_5'])
            away_consistency = 1 / (1 + df['AwayGoalVariance_5'])
            return (home_consistency + away_consistency) / 2
        else:
            return pd.Series(0.5, index=df.index)  # Default medium consistency

    def _calculate_goal_variance_indicator(self, df: pd.DataFrame) -> pd.Series:
        """Calculate goal variance indicator for match unpredictability."""

        if 'HomeGoalVariance_5' in df.columns and 'AwayGoalVariance_5' in df.columns:
            combined_variance = df['HomeGoalVariance_5'] + df['AwayGoalVariance_5']
            return combined_variance.fillna(1.0)
        else:
            return pd.Series(1.0, index=df.index)

    def create_advanced_metrics(self, df):
        """Enhanced advanced performance metrics with Bayesian elements."""
        df = df.copy()

        # Shot efficiency with Bayesian smoothing
        if all(col in df.columns for col in ['HS', 'AS', 'HST', 'AST']):
            if 'HomeShotAccuracy' not in df.columns:
                df['HomeShotAccuracy'] = np.where(df['HS'] > 0, df['HST'] / df['HS'], 0)
                df['AwayShotAccuracy'] = np.where(df['AS'] > 0, df['AST'] / df['AS'], 0)

            if 'HomeGoalConversion' not in df.columns:
                df['HomeGoalConversion'] = np.where(df['HST'] > 0, df['FTHG'] / df['HST'], 0)
                df['AwayGoalConversion'] = np.where(df['AST'] > 0, df['FTAG'] / df['AST'], 0)

            # Enhanced xG model with Bayesian adjustment
            if 'HomexG' not in df.columns:
                league_shot_quality = (df['FTHG'] + df['FTAG']).sum() / (df['HST'] + df['AST']).sum()
                df['HomexG'] = df['HST'] * league_shot_quality
                df['AwayxG'] = df['AST'] * league_shot_quality

        return df

    def create_team_strength_indicators(self, df):
        """Enhanced team strength using Bayesian rolling features."""
        df = df.copy()

        # Use Bayesian rolling features if they exist, otherwise create basic ones
        for team_type in ['Home', 'Away']:
            scoring_col = f'{team_type}ScoringForm_5'
            conceding_col = f'{team_type}ConcedingForm_5'
            form_col = f'{team_type}Form_5'

            if scoring_col in df.columns and conceding_col in df.columns:
                # Attack strength (relative to league average) with Bayesian smoothing
                league_avg_scoring = df.groupby('League')[scoring_col].transform('mean')
                df[f'{team_type}AttackStrength'] = df[scoring_col] / (league_avg_scoring + 0.01)

                # Defense strength (lower is better for defense) with Bayesian smoothing
                league_avg_conceding = df.groupby('League')[conceding_col].transform('mean')
                df[f'{team_type}DefenseStrength'] = df[conceding_col] / (league_avg_conceding + 0.01)

                # Form momentum with Bayesian adjustment
                if f'{team_type}Form_3' in df.columns and f'{team_type}Form_10' in df.columns:
                    short_form = df[f'{team_type}Form_3']
                    long_form = df[f'{team_type}Form_10']

                    # Bayesian momentum: recent form vs long-term form
                    confidence = 0.7  # Weight for recent form
                    df[f'{team_type}FormMomentum'] = confidence * short_form + (1 - confidence) * long_form

        return df

    def create_match_context(self, df):
        """Enhanced contextual match features with Bayesian elements."""
        df = df.copy()

        # Season progress (if not already calculated)
        if 'SeasonProgress' not in df.columns:
            df['SeasonProgress'] = df.groupby(['League', 'Season'])['Date'].transform(
                lambda x: (x - x.min()) / (x.max() - x.min() + pd.Timedelta(days=1))
            )

        # Days rest with Bayesian smoothing
        if 'HomeDaysRest' not in df.columns:
            df['HomeDaysRest'] = df.groupby('HomeTeam')['Date'].diff().dt.days
            df['AwayDaysRest'] = df.groupby('AwayTeam')['Date'].diff().dt.days

        # Rest advantage with realistic bounds
        df['RestAdvantage'] = (df.get('HomeDaysRest', 7) - df.get('AwayDaysRest', 7)).clip(-14, 14)

        # Match timing features
        if 'DayOfWeek' not in df.columns:
            df['DayOfWeek'] = df['Date'].dt.dayofweek
            df['Month'] = df['Date'].dt.month
            df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)

        # Competition intensity with Bayesian adjustment
        if 'MatchDensity' not in df.columns:
            df['MatchDensity'] = df.groupby(['League', 'Season'])['Date'].transform(
                lambda x: x.dt.to_period('M').value_counts()[x.dt.to_period('M')].values
            )

        # Season phase indicators
        df['IsEarlySeasonBayesian'] = (df['SeasonProgress'] <= 0.2).astype(int)
        df['IsMidSeasonBayesian'] = ((df['SeasonProgress'] > 0.3) & (df['SeasonProgress'] <= 0.7)).astype(int)
        df['IsLateSeasonBayesian'] = (df['SeasonProgress'] > 0.8).astype(int)

        return df

    def create_enhanced_goal_potential(self, df):
        """
        ⚽ ENHANCED: Goal potential indicators using Bayesian features.
        """
        df = df.copy()

        # Combined goal potential using Bayesian strengths
        home_attack = df.get('HomeAttackStrengthRel', df.get('HomeAttackStrength', 1.0))
        away_attack = df.get('AwayAttackStrengthRel', df.get('AwayAttackStrength', 1.0))
        home_defense = df.get('HomeDefenseStrengthRel', df.get('HomeDefenseStrength', 1.0))
        away_defense = df.get('AwayDefenseStrengthRel', df.get('AwayDefenseStrength', 1.0))

        # Bayesian goal potential calculation
        df['BayesianGoalPotential'] = (home_attack * away_defense + away_attack * home_defense) / 2

        # Defensive vulnerability
        df['DefensiveVulnerability'] = (home_defense + away_defense) / 2

        # Attack vs Defense balance
        df['AttackDefenseBalance'] = (home_attack + away_attack) / (home_defense + away_defense + 0.01)

        # Over/Under tendency with Bayesian smoothing
        home_over_25 = df.get('HomeOverRate2.5_5', 0.5)
        away_over_25 = df.get('AwayOverRate2.5_5', 0.5)

        if isinstance(home_over_25, pd.Series) and isinstance(away_over_25, pd.Series):
            # Bayesian combination of team tendencies
            df['BayesianOver25Tendency'] = (home_over_25 + away_over_25) / 2

            # Add referee influence if available
            if 'RefOver25Rate' in df.columns:
                ref_weight = 0.2  # 20% weight for referee
                team_weight = 0.8  # 80% weight for teams
                df['BayesianOver25Tendency'] = (
                        team_weight * df['BayesianOver25Tendency'] +
                        ref_weight * df['RefOver25Rate']
                )
        else:
            df['BayesianOver25Tendency'] = 0.5

        return df

    def create_gw1_enhanced_features(self, df):
        """
        🏆 Enhanced GW1 features with Bayesian historical analysis.
        """
        df = df.copy()

        # Use IsEarlySeason if already calculated
        if 'IsEarlySeason' not in df.columns:
            if 'SeasonProgress' in df.columns:
                df['IsEarlySeason'] = (df['SeasonProgress'] <= 0.15).astype(int)
            else:
                df['IsEarlySeason'] = 0

        print("🏆 Creating enhanced GW1 features with Bayesian analysis...")

        # Calculate team's historical GW1 performance with Bayesian smoothing
        if df['IsEarlySeason'].sum() > 0:
            gw1_data = df[df['IsEarlySeason'] == 1]
            league_gw1_priors = self._calculate_gw1_league_priors(gw1_data)

            for team_type in ['Home', 'Away']:
                team_col = f'{team_type}Team'
                goals_col = 'FTHG' if team_type == 'Home' else 'FTAG'

                # Calculate team GW1 performance with Bayesian updating
                team_gw1_stats = {}
                for team in df[team_col].unique():
                    team_gw1_matches = gw1_data[gw1_data[team_col] == team]

                    if len(team_gw1_matches) > 0:
                        # Get league context
                        team_league = team_gw1_matches.get('League', 'E0').iloc[
                            0] if 'League' in team_gw1_matches.columns else 'E0'
                        league_prior = league_gw1_priors.get(team_league, league_gw1_priors.get('E0', {}))

                        # Bayesian updating for GW1 scoring
                        confidence = min(0.8, len(team_gw1_matches) / 5)  # Max 80% confidence with 5+ GW1 matches
                        team_gw1_scoring = team_gw1_matches[goals_col].mean()

                        bayesian_gw1_scoring = self._bayesian_update(
                            league_prior.get('avg_goals', 1.2),
                            team_gw1_scoring,
                            confidence
                        )

                        # Bayesian updating for GW1 form
                        if team_type == 'Home':
                            team_gw1_wins = (team_gw1_matches['FTR'] == 'H').mean()
                        else:
                            team_gw1_wins = (team_gw1_matches['FTR'] == 'A').mean()

                        bayesian_gw1_form = self._bayesian_update(
                            league_prior.get('win_rate', 0.4),
                            team_gw1_wins,
                            confidence
                        )

                        team_gw1_stats[team] = {
                            'scoring': bayesian_gw1_scoring,
                            'form': bayesian_gw1_form
                        }
                    else:
                        # Use league priors for teams with no GW1 history
                        default_league = 'E0'
                        if 'League' in df.columns:
                            team_matches = df[df[team_col] == team]
                            if len(team_matches) > 0:
                                default_league = team_matches['League'].iloc[0]

                        league_prior = league_gw1_priors.get(default_league, league_gw1_priors.get('E0', {}))
                        team_gw1_stats[team] = {
                            'scoring': league_prior.get('avg_goals', 1.2),
                            'form': league_prior.get('win_rate', 0.4)
                        }

                # Add to dataframe
                df[f'{team_type}GW1ScoringHistory'] = df[team_col].map(
                    lambda x: team_gw1_stats.get(x, {}).get('scoring', 1.2)
                )
                df[f'{team_type}GW1FormHistory'] = df[team_col].map(
                    lambda x: team_gw1_stats.get(x, {}).get('form', 0.4)
                )

        # Promoted team adjustments with Bayesian penalties
        if 'IsPromotedTeam' in df.columns:
            # Historical promoted team penalty
            promoted_penalty = self._calculate_promoted_team_penalty(df)

            df['PromotedTeamPenalty'] = df['IsPromotedTeam'] * promoted_penalty
            df['PromotedTeamEarlyBonus'] = (
                    df['IsPromotedTeam'] * df['IsEarlySeason'] * 0.05  # Small early season boost
            )
        else:
            df['PromotedTeamPenalty'] = 0
            df['PromotedTeamEarlyBonus'] = 0

        print("✅ Enhanced GW1 features with Bayesian analysis created")
        return df

    def _calculate_gw1_league_priors(self, gw1_data: pd.DataFrame) -> Dict:
        """Calculate league-specific GW1 priors."""
        league_priors = {}

        for league in gw1_data.get('League', gw1_data.get('Div', ['E0'])).unique():
            league_gw1 = gw1_data[gw1_data.get('League', gw1_data.get('Div', 'E0')) == league]

            if len(league_gw1) > 10:
                league_priors[league] = {
                    'avg_goals': league_gw1['FTHG'].mean(),  # Home goals in GW1
                    'win_rate': (league_gw1['FTR'] == 'H').mean(),  # Home win rate in GW1
                    'total_goals': league_gw1['TotalGoals'].mean() if 'TotalGoals' in league_gw1.columns else 2.5
                }
            else:
                # Default GW1 priors
                league_priors[league] = {
                    'avg_goals': 1.2,
                    'win_rate': 0.4,
                    'total_goals': 2.3
                }

        return league_priors

    def _calculate_promoted_team_penalty(self, df: pd.DataFrame) -> float:
        """Calculate historical penalty for promoted teams."""

        if 'IsPromotedTeam' not in df.columns:
            return 0.1  # Default penalty

        promoted_matches = df[df['IsPromotedTeam'] == 1]
        regular_matches = df[df['IsPromotedTeam'] == 0]

        if len(promoted_matches) > 20 and len(regular_matches) > 100:
            # Calculate performance difference
            promoted_goals = promoted_matches['TotalGoals'].mean()
            regular_goals = regular_matches['TotalGoals'].mean()

            # Return penalty as proportion
            penalty = max(0, (regular_goals - promoted_goals) / regular_goals)
            return min(0.2, penalty)  # Cap at 20% penalty

        return 0.1  # Default 10% penalty

    def engineer_features(self, df):
        """
        🚀 COMPLETE: Enhanced feature engineering pipeline with Bayesian inference.
        """
        print("🚀 Starting ENHANCED Bayesian feature engineering...")
        print("🧠 Integrates with Bayesian rolling features for realistic predictions")
        df = df.copy()

        # Check what we already have from rolling features
        existing_features = df.columns.tolist()
        elo_exists = 'HomeElo' in existing_features
        bayesian_exists = any('Bayesian' in col for col in existing_features)

        print(f"📊 Input features: {len(existing_features)}")
        if elo_exists:
            print("✅ Bayesian Elo ratings available")
        if bayesian_exists:
            print("✅ Bayesian rolling features available")

        # Execute each step in sequence
        print("🔧 Creating base features...")
        df = self.create_base_features(df)

        print("🔧 Encoding teams...")
        df = self.encode_teams(df)

        print("🧠 Creating Bayesian match outcome features...")
        df = self.create_bayesian_match_outcome_features(df)

        print("⚽ Creating Bayesian goal prediction features...")
        df = self.create_bayesian_goal_prediction_features(df)

        print("🔧 Creating advanced metrics...")
        df = self.create_advanced_metrics(df)

        print("🔧 Creating team strength indicators...")
        df = self.create_team_strength_indicators(df)

        print("🔧 Creating match context features...")
        df = self.create_match_context(df)

        print("🧠 Creating Bayesian referee analysis...")
        df = self.create_bayesian_referee_analysis(df)

        print("🧠 Creating Bayesian H2H analysis...")
        df = self.create_bayesian_h2h_analysis(df)

        print("⚽ Creating enhanced goal potential...")
        df = self.create_enhanced_goal_potential(df)

        print("🏆 Creating enhanced GW1 features...")
        df = self.create_gw1_enhanced_features(df)

        # Handle missing values
        print("🔧 Handling missing values...")
        df = df.fillna(0)

        # Count final features
        final_features = len(df.columns)
        new_features = final_features - len(existing_features)

        print("✅ ENHANCED Bayesian feature engineering completed!")
        print(f"📊 Added {new_features} new Bayesian features")
        print(f"📊 Total features: {final_features}")

        # Show sample of new Bayesian features
        bayesian_features = [col for col in df.columns if 'Bayesian' in col]
        h2h_features = [col for col in df.columns if 'H2H' in col]
        outcome_features = [col for col in df.columns if 'MatchOutcome' in col]

        print(f"   🧠 Bayesian features: {len(bayesian_features)}")
        print(f"   🤝 Enhanced H2H features: {len(h2h_features)}")
        print(f"   🎯 Match outcome features: {len(outcome_features)}")

        return df

    def get_referee_insights(self):
        """Return Bayesian referee analysis."""
        return self.referee_stats

    def get_team_encodings(self):
        """Return team encodings for reference."""
        return self.team_encodings

    def get_bayesian_priors(self):
        """Return calculated Bayesian priors."""
        return self.bayesian_priors

    def get_league_characteristics(self):
        """Return league-specific characteristics."""
        return self.league_characteristics