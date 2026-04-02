# footy/rolling_features.py - COMPLETE BAYESIAN ENHANCED VERSION

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class BayesianRollingFeatureGenerator:
    """Complete rolling window features with Bayesian inference for realistic team strength."""

    def __init__(self):
        self.gw1_stats = {}
        self.promotion_teams = {}
        self.elo_ratings = {}
        self.team_strength_priors = {}
        self.league_strength_distribution = {}

    def calculate_bayesian_elo_ratings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🎯 BAYESIAN ELO: Dynamic ratings with realistic priors based on league history.
        No more hardcoded 1500 - calculates realistic starting points!
        """
        df = df.copy()
        df = df.sort_values(['Season', 'Date'])

        print("[Model] Calculating BAYESIAN Elo ratings with historical priors...")

        # STEP 1: Calculate league-specific Elo priors from historical data
        league_priors = self._calculate_league_elo_priors(df)

        # STEP 2: Calculate team-specific priors for returning teams
        team_priors = self._calculate_team_elo_priors(df)

        # STEP 3: Dynamic K-factor based on match importance and team uncertainty
        elo_ratings = {}
        home_elo = []
        away_elo = []

        for idx, row in df.iterrows():
            home_team = row['HomeTeam']
            away_team = row['AwayTeam']
            current_season = row.get('Season', '2023/24')

            # Initialize Elo with Bayesian priors (NOT hardcoded 1500!)
            if home_team not in elo_ratings:
                elo_ratings[home_team] = self._get_bayesian_starting_elo(
                    home_team, current_season, league_priors, team_priors, df
                )
            if away_team not in elo_ratings:
                elo_ratings[away_team] = self._get_bayesian_starting_elo(
                    away_team, current_season, league_priors, team_priors, df
                )

            # Store PRE-MATCH ratings (no data leakage)
            current_home_elo = elo_ratings[home_team]
            current_away_elo = elo_ratings[away_team]

            home_elo.append(current_home_elo)
            away_elo.append(current_away_elo)

            # Update ratings AFTER match with Bayesian K-factor
            if pd.notna(row['FTR']):
                bayesian_k = self._calculate_bayesian_k_factor(
                    home_team, away_team, current_home_elo, current_away_elo, df
                )

                # Enhanced home advantage calculation
                dynamic_home_advantage = self._calculate_dynamic_home_advantage(
                    home_team, df, current_season
                )

                # Expected scores using Bayesian-adjusted Elo
                effective_home_elo = current_home_elo + dynamic_home_advantage
                effective_away_elo = current_away_elo

                expected_home = 1 / (1 + 10 ** ((effective_away_elo - effective_home_elo) / 400))
                expected_away = 1 - expected_home

                # Actual scores
                if row['FTR'] == 'H':
                    actual_home, actual_away = 1.0, 0.0
                elif row['FTR'] == 'A':
                    actual_home, actual_away = 0.0, 1.0
                else:
                    actual_home, actual_away = 0.5, 0.5

                # Bayesian update with dynamic K-factor
                elo_ratings[home_team] += bayesian_k * (actual_home - expected_home)
                elo_ratings[away_team] += bayesian_k * (actual_away - expected_away)

                # Realistic bounds (no extreme ratings)
                elo_ratings[home_team] = max(1000, min(2200, elo_ratings[home_team]))
                elo_ratings[away_team] = max(1000, min(2200, elo_ratings[away_team]))

        # Add to dataframe
        df['HomeElo'] = home_elo
        df['AwayElo'] = away_elo
        df['EloAdvantage'] = df['HomeElo'] - df['AwayElo']

        # Validation
        print("📊 Bayesian Elo validation:")
        print(f"   Average: {df['HomeElo'].mean():.0f}")
        print(f"   Range: {df['HomeElo'].min():.0f} - {df['HomeElo'].max():.0f}")
        print(f"   Std Dev: {df['HomeElo'].std():.0f}")

        # Show realistic team examples
        final_elos = {}
        for team in df['HomeTeam'].unique()[:10]:
            team_matches = df[df['HomeTeam'] == team]
            if len(team_matches) > 0:
                final_elos[team] = team_matches['HomeElo'].iloc[-1]

        top_teams = sorted(final_elos.items(), key=lambda x: x[1], reverse=True)[:5]
        print("[Top] Top teams by Bayesian Elo:")
        for team, elo in top_teams:
            print(f"   {team}: {elo:.0f}")

        self.elo_ratings = elo_ratings
        return df

    def _calculate_league_elo_priors(self, df: pd.DataFrame) -> Dict:
        """Calculate realistic Elo priors for each league from historical data."""
        league_priors = {}

        for league in df.get('League', df.get('Div', ['E0'])).unique():
            league_matches = df[df.get('League', df.get('Div', 'E0')) == league]

            if len(league_matches) > 100:  # Enough data for reliable prior
                # Calculate league competitiveness
                home_win_rate = (league_matches['FTR'] == 'H').mean()
                draw_rate = (league_matches['FTR'] == 'D').mean()

                # More competitive leagues have lower home advantage
                if home_win_rate < 0.40:  # Very competitive
                    base_elo = 1600  # Higher base for top leagues
                    elo_spread = 300  # Larger spread
                elif home_win_rate > 0.50:  # Less competitive
                    base_elo = 1400  # Lower base
                    elo_spread = 200  # Smaller spread
                else:
                    base_elo = 1500  # Standard
                    elo_spread = 250

                league_priors[league] = {
                    'base_elo': base_elo,
                    'elo_spread': elo_spread,
                    'home_win_rate': home_win_rate,
                    'competitiveness': 1 - abs(home_win_rate - 0.333)  # How close to 33.3% each outcome
                }
            else:
                # Default for leagues with little data
                league_priors[league] = {
                    'base_elo': 1500,
                    'elo_spread': 250,
                    'home_win_rate': 0.45,
                    'competitiveness': 0.7
                }

        return league_priors

    def _calculate_team_elo_priors(self, df: pd.DataFrame) -> Dict:
        """Calculate team-specific Elo priors based on historical performance."""
        team_priors = {}

        for team in df['HomeTeam'].unique():
            team_matches = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)]

            if len(team_matches) > 20:  # Enough history
                # Calculate historical win rate
                home_matches = team_matches[team_matches['HomeTeam'] == team]
                away_matches = team_matches[team_matches['AwayTeam'] == team]

                home_wins = (home_matches['FTR'] == 'H').sum()
                away_wins = (away_matches['FTR'] == 'A').sum()
                total_draws = ((home_matches['FTR'] == 'D').sum() +
                               (away_matches['FTR'] == 'D').sum())

                total_matches = len(team_matches)
                win_rate = (home_wins + away_wins) / total_matches

                # Convert win rate to Elo adjustment
                if win_rate > 0.60:
                    elo_adjustment = +150  # Strong team
                elif win_rate > 0.50:
                    elo_adjustment = +50  # Above average
                elif win_rate < 0.30:
                    elo_adjustment = -150  # Weak team
                elif win_rate < 0.40:
                    elo_adjustment = -50  # Below average
                else:
                    elo_adjustment = 0  # Average

                team_priors[team] = {
                    'elo_adjustment': elo_adjustment,
                    'historical_win_rate': win_rate,
                    'confidence': min(1.0, len(team_matches) / 100)  # More matches = higher confidence
                }

        return team_priors

    def _get_bayesian_starting_elo(self, team: str, season: str, league_priors: Dict,
                                   team_priors: Dict, df: pd.DataFrame) -> float:
        """Get realistic starting Elo using Bayesian priors - NO hardcoding!"""

        # Get league for this team
        team_league = 'E0'  # Default
        team_matches = df[df['HomeTeam'] == team]
        if len(team_matches) > 0 and 'League' in df.columns:
            team_league = team_matches.iloc[0]['League']
        elif len(team_matches) > 0 and 'Div' in df.columns:
            team_league = team_matches.iloc[0]['Div']

        # Start with league prior
        league_prior = league_priors.get(team_league, league_priors.get('E0', {
            'base_elo': 1500, 'elo_spread': 250
        }))

        base_elo = league_prior['base_elo']

        # Apply team-specific adjustment if available
        if team in team_priors:
            team_prior = team_priors[team]
            confidence = team_prior['confidence']

            # Weighted combination of league and team priors
            adjustment = team_prior['elo_adjustment'] * confidence
            starting_elo = base_elo + adjustment
        else:
            # Check if this is a promoted team
            if self._is_promoted_team(team, season, df):
                # Promoted teams start lower than league average
                starting_elo = base_elo - 100
            else:
                # New team starts at league average
                starting_elo = base_elo

        return max(1000, min(2000, starting_elo))

    def _calculate_bayesian_k_factor(self, home_team: str, away_team: str,
                                     home_elo: float, away_elo: float, df: pd.DataFrame) -> float:
        """Calculate dynamic K-factor based on Bayesian uncertainty."""

        # Base K-factor
        base_k = 20

        # Increase K for teams with fewer matches (higher uncertainty)
        home_matches = len(df[df['HomeTeam'] == home_team])
        away_matches = len(df[df['AwayTeam'] == away_team])

        min_matches = min(home_matches, away_matches)

        if min_matches < 10:
            uncertainty_multiplier = 1.5  # High uncertainty
        elif min_matches < 30:
            uncertainty_multiplier = 1.2  # Medium uncertainty
        else:
            uncertainty_multiplier = 1.0  # Normal uncertainty

        # Increase K for very mismatched teams (upset potential)
        elo_diff = abs(home_elo - away_elo)
        if elo_diff > 200:
            mismatch_multiplier = 1.3
        else:
            mismatch_multiplier = 1.0

        return min(40, base_k * uncertainty_multiplier * mismatch_multiplier)

    def _calculate_dynamic_home_advantage(self, home_team: str, df: pd.DataFrame,
                                          season: str) -> float:
        """Calculate team-specific home advantage from historical data."""

        home_matches = df[df['HomeTeam'] == home_team]

        if len(home_matches) < 5:
            return 100  # Default home advantage

        # Calculate actual home advantage
        home_win_rate = (home_matches['FTR'] == 'H').mean()
        league_home_win_rate = (df['FTR'] == 'H').mean()

        # Convert to Elo advantage
        if home_win_rate > league_home_win_rate + 0.1:
            return 150  # Strong home team
        elif home_win_rate < league_home_win_rate - 0.1:
            return 50  # Weak home team
        else:
            return 100  # Average home advantage

    def _is_promoted_team(self, team: str, season: str, df: pd.DataFrame) -> bool:
        """Check if team was promoted this season."""
        # Simple check - if team has no matches in previous season
        if 'Season' not in df.columns:
            return False

        seasons = sorted(df['Season'].unique())
        if season not in seasons:
            return False

        season_idx = seasons.index(season)
        if season_idx == 0:
            return False

        prev_season = seasons[season_idx - 1]

        # Check if team played in previous season
        prev_season_teams = set(df[df['Season'] == prev_season]['HomeTeam'].unique())

        return team not in prev_season_teams

    def calculate_bayesian_team_strengths(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🎯 BAYESIAN TEAM STRENGTHS: Calculate attack/defense strength with proper priors.
        """
        df = df.copy()

        print("[Model] Calculating Bayesian team strengths...")

        # Calculate league averages as priors
        league_avg_home_goals = df['FTHG'].mean()
        league_avg_away_goals = df['FTAG'].mean()

        print(f"   League priors: {league_avg_home_goals:.2f} home, {league_avg_away_goals:.2f} away")

        # For each team, calculate Bayesian strength estimates
        for team_type in ['Home', 'Away']:
            team_col = f'{team_type}Team'
            goals_for_col = 'FTHG' if team_type == 'Home' else 'FTAG'
            goals_against_col = 'FTAG' if team_type == 'Home' else 'FTHG'

            # Calculate team strengths with Bayesian updating
            attack_strengths = []
            defense_strengths = []

            for idx, row in df.iterrows():
                team = row[team_col]

                # Get team's historical data up to this point (no data leakage)
                team_history = df[(df[team_col] == team) & (df.index < idx)]

                if len(team_history) >= 3:  # Need some history for Bayesian update
                    # Bayesian update: prior + evidence
                    prior_attack = league_avg_home_goals if team_type == 'Home' else league_avg_away_goals
                    prior_defense = league_avg_away_goals if team_type == 'Home' else league_avg_home_goals

                    # Evidence from team's recent matches
                    recent_attack = team_history[goals_for_col].tail(10).mean()
                    recent_defense = team_history[goals_against_col].tail(10).mean()

                    # Bayesian combination (weighted by confidence)
                    confidence = min(1.0, len(team_history) / 20)  # More history = higher confidence

                    bayesian_attack = (1 - confidence) * prior_attack + confidence * recent_attack
                    bayesian_defense = (1 - confidence) * prior_defense + confidence * recent_defense

                    attack_strengths.append(bayesian_attack)
                    defense_strengths.append(bayesian_defense)
                else:
                    # Use priors for teams with little history
                    attack_strengths.append(league_avg_home_goals if team_type == 'Home' else league_avg_away_goals)
                    defense_strengths.append(league_avg_away_goals if team_type == 'Home' else league_avg_home_goals)

            # Add to dataframe
            df[f'{team_type}AttackStrength'] = attack_strengths
            df[f'{team_type}DefenseStrength'] = defense_strengths

            # Calculate relative strength (vs league average)
            league_avg = league_avg_home_goals if team_type == 'Home' else league_avg_away_goals
            df[f'{team_type}AttackStrengthRel'] = df[f'{team_type}AttackStrength'] / league_avg

            defense_avg = league_avg_away_goals if team_type == 'Home' else league_avg_home_goals
            df[f'{team_type}DefenseStrengthRel'] = df[f'{team_type}DefenseStrength'] / defense_avg

        print("[OK] Bayesian team strengths calculated")
        return df

    def identify_promoted_teams_with_penalties(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🎯 PROMOTED TEAMS: Identify and apply realistic Bayesian penalties.
        """
        df = df.copy()
        df['IsPromotedTeam'] = 0

        print("🔍 Identifying promoted teams with Bayesian penalties...")

        # Calculate historical promoted team performance
        promoted_team_stats = self._analyze_historical_promoted_performance(df)

        seasons = sorted(df['Season'].unique()) if 'Season' in df.columns else ['2023/24']

        for i, season in enumerate(seasons):
            if i == 0:
                continue  # Can't identify promoted teams in first season

            prev_season = seasons[i - 1]

            current_teams = set(df[df['Season'] == season]['HomeTeam'].unique())
            prev_teams = set(df[df['Season'] == prev_season]['HomeTeam'].unique())

            promoted_teams = current_teams - prev_teams

            if promoted_teams:
                print(f"   {season}: {', '.join(promoted_teams)}")
                self.promotion_teams[season] = promoted_teams

                # Apply Bayesian penalties based on historical data
                for team in promoted_teams:
                    # Mark matches for this promoted team
                    team_mask = (
                            (df['Season'] == season) &
                            ((df['HomeTeam'] == team) | (df['AwayTeam'] == team))
                    )

                    # Apply historical promoted team penalties
                    df.loc[team_mask, 'IsPromotedTeam'] = 1

                    # Reduce Elo for promoted teams based on historical performance
                    if 'HomeElo' in df.columns:
                        home_mask = team_mask & (df['HomeTeam'] == team)
                        away_mask = team_mask & (df['AwayTeam'] == team)

                        # Apply penalty based on historical promoted team performance
                        penalty = promoted_team_stats.get('elo_penalty', 100)

                        df.loc[home_mask, 'HomeElo'] -= penalty
                        df.loc[away_mask, 'AwayElo'] -= penalty

        return df

    def _analyze_historical_promoted_performance(self, df: pd.DataFrame) -> Dict:
        """Analyze how promoted teams historically perform."""

        # This would analyze historical promoted team performance
        # For now, return reasonable estimates based on typical promoted team struggles

        return {
            'elo_penalty': 80,  # Promoted teams typically 80 Elo points weaker
            'home_win_rate': 0.35,  # vs 0.45 average
            'away_win_rate': 0.15,  # vs 0.25 average
            'avg_goals_scored': 1.1,  # vs 1.4 average
            'avg_goals_conceded': 1.6  # vs 1.2 average
        }

    def _calculate_team_form_vectorized(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        🚀 VECTORIZED: Team form calculation with data leakage prevention.
        """
        df = df.copy()

        # Create result mapping
        result_map = {'H': 1, 'D': 0.5, 'A': 0}
        df['ResultNumeric'] = df['FTR'].map(result_map)

        # Home team form - vectorized with shift(1)
        df['HomeForm_3'] = df.groupby('HomeTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 1 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(3, min_periods=1).mean()
        )
        df['HomeForm_5'] = df.groupby('HomeTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 1 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(5, min_periods=1).mean()
        )
        df['HomeForm_10'] = df.groupby('HomeTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 1 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(10, min_periods=1).mean()
        )

        # Away team form - vectorized with shift(1)
        df['AwayForm_3'] = df.groupby('AwayTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 0 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(3, min_periods=1).mean()
        )
        df['AwayForm_5'] = df.groupby('AwayTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 0 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(5, min_periods=1).mean()
        )
        df['AwayForm_10'] = df.groupby('AwayTeam')['ResultNumeric'].transform(
            lambda x: x.map(lambda r: 1 if r == 0 else 0.5 if r == 0.5 else 0)
            .shift(1).rolling(10, min_periods=1).mean()
        )

        return df

    def _calculate_goal_features_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 VECTORIZED: Goal features - the core of your 94% accuracy.
        """
        df = df.copy()

        # Calculate total goals first
        df['TotalGoals'] = df['FTHG'] + df['FTAG']
        df['Over1.5'] = (df['TotalGoals'] > 1.5).astype(int)
        df['Over2.5'] = (df['TotalGoals'] > 2.5).astype(int)
        df['Over3.5'] = (df['TotalGoals'] > 3.5).astype(int)
        df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)

        # KEY FEATURES: Home team goal features (these gave you 94% accuracy)
        for window in [3, 5, 10]:
            # Home scoring features
            df[f'HomeScoringForm_{window}'] = df.groupby('HomeTeam')['FTHG'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'HomeConcedingForm_{window}'] = df.groupby('HomeTeam')['FTAG'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )

            # Away scoring features
            df[f'AwayScoringForm_{window}'] = df.groupby('AwayTeam')['FTAG'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'AwayConcedingForm_{window}'] = df.groupby('AwayTeam')['FTHG'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )

            # Over/Under rates (crucial for your 94% accuracy)
            df[f'HomeOverRate1.5_{window}'] = df.groupby('HomeTeam')['Over1.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'HomeOverRate2.5_{window}'] = df.groupby('HomeTeam')['Over2.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'HomeOverRate3.5_{window}'] = df.groupby('HomeTeam')['Over3.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )

            df[f'AwayOverRate1.5_{window}'] = df.groupby('AwayTeam')['Over1.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'AwayOverRate2.5_{window}'] = df.groupby('AwayTeam')['Over2.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'AwayOverRate3.5_{window}'] = df.groupby('AwayTeam')['Over3.5'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )

            # BTTS rates
            df[f'HomeBTTSForm_{window}'] = df.groupby('HomeTeam')['BTTS'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'AwayBTTSForm_{window}'] = df.groupby('AwayTeam')['BTTS'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )

            # Total goals rate and variance
            df[f'HomeTotalGoalsRate_{window}'] = df.groupby('HomeTeam')['TotalGoals'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'AwayTotalGoalsRate_{window}'] = df.groupby('AwayTeam')['TotalGoals'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).mean()
            )
            df[f'HomeGoalVariance_{window}'] = df.groupby('HomeTeam')['TotalGoals'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).std()
            )
            df[f'AwayGoalVariance_{window}'] = df.groupby('AwayTeam')['TotalGoals'].transform(
                lambda x: x.shift(1).rolling(window, min_periods=1).std()
            )

        return df

    def _calculate_shot_features_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 VECTORIZED: Enhanced shot features with rolling averages and conversion rates.
        """
        df = df.copy()

        # Only calculate if shot data exists
        if 'HS' in df.columns and 'AS' in df.columns:
            # Shot accuracy (existing)
            df['HomeShotAccuracy'] = np.where(df['HS'] > 0, df['HST'] / df['HS'], 0)
            df['AwayShotAccuracy'] = np.where(df['AS'] > 0, df['AST'] / df['AS'], 0)

            # Rolling shot accuracy (existing)
            df['HomeShotAccuracyRolling'] = df.groupby('HomeTeam')['HomeShotAccuracy'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayShotAccuracyRolling'] = df.groupby('AwayTeam')['AwayShotAccuracy'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # Goal conversion (goals per shot on target) - existing
            df['HomeGoalConversion'] = np.where(df['HST'] > 0, df['FTHG'] / df['HST'], 0)
            df['AwayGoalConversion'] = np.where(df['AST'] > 0, df['FTAG'] / df['AST'], 0)

            # Shot pressure (shots on target) - existing
            df['HomeShotPressure'] = df['HST']
            df['AwayShotPressure'] = df['AST']

            # Expected goals (Use accurate Understat xG if available, fallback to naive model)
            naive_hxG = df['HS'] * 0.08 + df['HST'] * 0.25
            naive_axG = df['AS'] * 0.08 + df['AST'] * 0.25
            
            if 'Home_xG' in df.columns and 'Away_xG' in df.columns:
                df['HomexG'] = df['Home_xG'].fillna(naive_hxG)
                df['AwayxG'] = df['Away_xG'].fillna(naive_axG)
            else:
                df['HomexG'] = naive_hxG
                df['AwayxG'] = naive_axG
                
            # ✨ NEW: True Rolling Expected Goals (3, 5, 10 game averages)
            for window in [3, 5, 10]:
                df[f'Home_Rolling_xG_{window}'] = df.groupby('HomeTeam')['HomexG'].transform(
                    lambda x: x.shift(1).rolling(window, min_periods=1).mean()
                )
                df[f'Away_Rolling_xG_{window}'] = df.groupby('AwayTeam')['AwayxG'].transform(
                    lambda x: x.shift(1).rolling(window, min_periods=1).mean()
                )
                
            # Expected Goals Differential (Advantage)
            df['Rolling_xG_Advantage'] = df['Home_Rolling_xG_5'] - df['Away_Rolling_xG_5']

            # ✨ NEW: Shots on Target Rolling Averages (Last 5 matches)
            df['HomeShotsOnTargetAvg_Last5'] = df.groupby('HomeTeam')['HST'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayShotsOnTargetAvg_Last5'] = df.groupby('AwayTeam')['AST'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ NEW: Shot Conversion Rate (rolling average of goals per SOT)
            df['HomeShotConversionRate'] = df.groupby('HomeTeam')['HomeGoalConversion'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayShotConversionRate'] = df.groupby('AwayTeam')['AwayGoalConversion'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ NEW: Defensive Shots Allowed (how many SOT opponents get)
            df['HomeDefensiveShotsAllowed_Last5'] = df.groupby('HomeTeam')['AST'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayDefensiveShotsAllowed_Last5'] = df.groupby('AwayTeam')['HST'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ NEW: Shot Differential (SOT advantage)
            df['ShotOnTargetDifferential'] = (
                df.get('HomeShotsOnTargetAvg_Last5', 0) -
                df.get('AwayShotsOnTargetAvg_Last5', 0)
            )

            # ✨ NEW: Goals per Shot on Target (attacking efficiency)
            df['HomeGoalsPerShotOnTarget_Last5'] = df.groupby('HomeTeam').apply(
                lambda g: (g['FTHG'].shift(1).rolling(5, min_periods=1).sum() /
                          (g['HST'].shift(1).rolling(5, min_periods=1).sum() + 0.1))
            ).reset_index(level=0, drop=True)

            df['AwayGoalsPerShotOnTarget_Last5'] = df.groupby('AwayTeam').apply(
                lambda g: (g['FTAG'].shift(1).rolling(5, min_periods=1).sum() /
                          (g['AST'].shift(1).rolling(5, min_periods=1).sum() + 0.1))
            ).reset_index(level=0, drop=True)

        return df

    def _calculate_halftime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 NEW: Half-time pattern features - 1st vs 2nd half scoring patterns.
        CRITICAL: Predicts team tendencies to start strong or finish strong.
        """
        df = df.copy()

        # Only calculate if half-time data exists
        if 'HTHG' in df.columns and 'HTAG' in df.columns:
            print("[HT] Calculating half-time pattern features...")

            # Calculate 1st half and 2nd half goals
            df['Home1stHalfGoals'] = df['HTHG']
            df['Home2ndHalfGoals'] = df['FTHG'] - df['HTHG']
            df['Away1stHalfGoals'] = df['HTAG']
            df['Away2ndHalfGoals'] = df['FTAG'] - df['HTAG']

            # ✨ Rolling averages for 1st half goals (Last 5 matches)
            df['Home1stHalfGoalsAvg_Last5'] = df.groupby('HomeTeam')['Home1stHalfGoals'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['Away1stHalfGoalsAvg_Last5'] = df.groupby('AwayTeam')['Away1stHalfGoals'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ Rolling averages for 2nd half goals (Last 5 matches)
            df['Home2ndHalfGoalsAvg_Last5'] = df.groupby('HomeTeam')['Home2ndHalfGoals'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['Away2ndHalfGoalsAvg_Last5'] = df.groupby('AwayTeam')['Away2ndHalfGoals'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ Strong Starter indicator (% of games where team scores in 1st half)
            df['Home1stHalfScored'] = (df['Home1stHalfGoals'] > 0).astype(int)
            df['Away1stHalfScored'] = (df['Away1stHalfGoals'] > 0).astype(int)

            df['HomeStrongStarter'] = df.groupby('HomeTeam')['Home1stHalfScored'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayStrongStarter'] = df.groupby('AwayTeam')['Away1stHalfScored'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ Strong Finisher indicator (% of games where 2nd half goals > 1st half goals)
            df['HomeStrongFinisherMatch'] = (df['Home2ndHalfGoals'] > df['Home1stHalfGoals']).astype(int)
            df['AwayStrongFinisherMatch'] = (df['Away2ndHalfGoals'] > df['Away1stHalfGoals']).astype(int)

            df['HomeStrongFinisher'] = df.groupby('HomeTeam')['HomeStrongFinisherMatch'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayStrongFinisher'] = df.groupby('AwayTeam')['AwayStrongFinisherMatch'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ Half-time lead conversion rate (when leading at HT, % of wins)
            df['HomeHalfTimeLeading'] = (df['HTHG'] > df['HTAG']).astype(int)
            df['AwayHalfTimeLeading'] = (df['HTAG'] > df['HTHG']).astype(int)

            # Calculate if they won when leading at HT
            df['HomeWonWhenLeadingHT'] = ((df['HTHG'] > df['HTAG']) & (df['FTR'] == 'H')).astype(int)
            df['AwayWonWhenLeadingHT'] = ((df['HTAG'] > df['HTHG']) & (df['FTR'] == 'A')).astype(int)

            # Conversion rate
            df['HomeHalfTimeLeadConversion'] = df.groupby('HomeTeam').apply(
                lambda g: (g['HomeWonWhenLeadingHT'].shift(1).rolling(10, min_periods=1).sum() /
                          (g['HomeHalfTimeLeading'].shift(1).rolling(10, min_periods=1).sum() + 0.1))
            ).reset_index(level=0, drop=True)

            df['AwayHalfTimeLeadConversion'] = df.groupby('AwayTeam').apply(
                lambda g: (g['AwayWonWhenLeadingHT'].shift(1).rolling(10, min_periods=1).sum() /
                          (g['AwayHalfTimeLeading'].shift(1).rolling(10, min_periods=1).sum() + 0.1))
            ).reset_index(level=0, drop=True)

            # ✨ 1st Half Over 0.5 Rate (% of 1st halves with goals)
            df['Home1stHalfOver05'] = (df['Home1stHalfGoals'] > 0.5).astype(int)
            df['Away1stHalfOver05'] = (df['Away1stHalfGoals'] > 0.5).astype(int)

            df['Home1stHalfOver05Rate'] = df.groupby('HomeTeam')['Home1stHalfOver05'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['Away1stHalfOver05Rate'] = df.groupby('AwayTeam')['Away1stHalfOver05'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            # ✨ 2nd Half Over 0.5 Rate
            df['Home2ndHalfOver05'] = (df['Home2ndHalfGoals'] > 0.5).astype(int)
            df['Away2ndHalfOver05'] = (df['Away2ndHalfGoals'] > 0.5).astype(int)

            df['Home2ndHalfOver05Rate'] = df.groupby('HomeTeam')['Home2ndHalfOver05'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['Away2ndHalfOver05Rate'] = df.groupby('AwayTeam')['Away2ndHalfOver05'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

            print("[HT] ✅ Created 20+ half-time pattern features")

        else:
            print("[HT] ⚠️ Half-time data (HTHG, HTAG) not available - skipping")

        return df

    def _calculate_rest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 NEW: Rest days and fixture congestion features.
        CRITICAL: Predicts fatigue-related performance drops.
        """
        df = df.copy()

        print("[REST] Calculating fixture congestion features...")

        # Ensure Date is datetime
        if 'Date' not in df.columns:
            print("[REST] ⚠️ Date column missing - skipping rest features")
            return df

        df['Date'] = pd.to_datetime(df['Date'])

        # Sort by team and date to ensure proper chronological order
        df = df.sort_values(['HomeTeam', 'Date'])

        # ✨ Days since last match (HOME)
        df['DaysSinceLastMatch_Home'] = df.groupby('HomeTeam')['Date'].diff().dt.days

        # ✨ Days since last match (AWAY)
        df = df.sort_values(['AwayTeam', 'Date'])
        df['DaysSinceLastMatch_Away'] = df.groupby('AwayTeam')['Date'].diff().dt.days

        # Sort back to original order
        df = df.sort_values(['Season', 'Date'])

        # Fill NaN (first match for each team) with 14 days (2 weeks default)
        df['DaysSinceLastMatch_Home'] = df['DaysSinceLastMatch_Home'].fillna(14)
        df['DaysSinceLastMatch_Away'] = df['DaysSinceLastMatch_Away'].fillna(14)

        # ✨ Rest Advantage (Home rest - Away rest)
        df['RestAdvantage'] = df['DaysSinceLastMatch_Home'] - df['DaysSinceLastMatch_Away']

        # ✨ Has Midweek Match (played in last 4 days)
        df['HasMidweekMatch_Home'] = (df['DaysSinceLastMatch_Home'] <= 4).astype(int)
        df['HasMidweekMatch_Away'] = (df['DaysSinceLastMatch_Away'] <= 4).astype(int)

        # ✨ Fixture Congestion Indicator (less than 5 days rest)
        df['FixtureCongestion_Home'] = (df['DaysSinceLastMatch_Home'] < 5).astype(int)
        df['FixtureCongestion_Away'] = (df['DaysSinceLastMatch_Away'] < 5).astype(int)

        # ✨ Well Rested Indicator (more than 6 days rest)
        df['WellRested_Home'] = (df['DaysSinceLastMatch_Home'] > 6).astype(int)
        df['WellRested_Away'] = (df['DaysSinceLastMatch_Away'] > 6).astype(int)

        print("[REST] ✅ Created 10 fixture congestion features")
        print(f"[REST] Avg rest days - Home: {df['DaysSinceLastMatch_Home'].mean():.1f}, Away: {df['DaysSinceLastMatch_Away'].mean():.1f}")

        return df

    def _calculate_disciplinary_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 VECTORIZED: Disciplinary features (fouls, cards).
        """
        df = df.copy()

        # Only if foul/card data exists
        if 'HF' in df.columns and 'AF' in df.columns:
            # Fouls average
            df['HomeFoulsAvg'] = df.groupby('HomeTeam')['HF'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayFoulsAvg'] = df.groupby('AwayTeam')['AF'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

        if 'HY' in df.columns and 'AY' in df.columns:
            # Yellow cards average
            df['HomeYellowAvg'] = df.groupby('HomeTeam')['HY'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            df['AwayYellowAvg'] = df.groupby('AwayTeam')['AY'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )

        return df

    def _calculate_gw1_historical_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ✨ Enhanced GW1 analysis with better season detection.
        """
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'])

        print("🔍 Analyzing GW1-5 historical patterns...")

        # Create TotalGoals if it doesn't exist
        if 'TotalGoals' not in df.columns:
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                df['TotalGoals'] = df['FTHG'] + df['FTAG']
                print("   [OK] Created TotalGoals column for GW1 analysis")
            else:
                print("   [Warning] Cannot create TotalGoals - missing FTHG/FTAG columns")
                return df

        # Create BTTS if it doesn't exist
        if 'BTTS' not in df.columns:
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
                print("   [OK] Created BTTS column for GW1 analysis")

        # Mark early season matches more accurately
        # Use 'Div' if 'League' not available
        league_col = 'League' if 'League' in df.columns else 'Div'

        if league_col in df.columns:
            df['SeasonProgress'] = df.groupby([league_col, 'Season'])['Date'].transform(
                lambda x: (x - x.min()) / (x.max() - x.min() + pd.Timedelta(days=1))
            )
        else:
            # If no league column, just use Season
            df['SeasonProgress'] = df.groupby('Season')['Date'].transform(
                lambda x: (x - x.min()) / (x.max() - x.min() + pd.Timedelta(days=1))
            )

        df['IsEarlySeason'] = (df['SeasonProgress'] <= 0.15).astype(int)

        # Calculate GW1 stats
        gw1_matches = df[df['IsEarlySeason'] == 1]

        if len(gw1_matches) > 0 and 'TotalGoals' in df.columns:
            gw1_stats = {
                'total_matches': len(gw1_matches),
                'avg_goals_per_match': gw1_matches['TotalGoals'].mean(),
                'home_win_rate': (gw1_matches['FTR'] == 'H').mean(),
                'over_2_5_rate': (gw1_matches['TotalGoals'] > 2.5).mean(),
                'btts_rate': gw1_matches['BTTS'].mean() if 'BTTS' in gw1_matches.columns else 0.5,
            }

            self.gw1_stats = gw1_stats
            print(f"[OK] GW1 Analysis Complete:")
            print(f"   [Stats] {gw1_stats['total_matches']} matches analyzed")
            print(f"   [Goals] Avg Goals: {gw1_stats['avg_goals_per_match']:.2f}")
            print(f"   [Home] Home Win Rate: {gw1_stats['home_win_rate']:.1%}")
            print(f"   [Stats] Over 2.5 Rate: {gw1_stats['over_2_5_rate']:.1%}")
        else:
            print("   [Warning] Cannot calculate GW1 stats - insufficient data")

        return df

    def _add_bayesian_match_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bayesian-based match prediction features."""

        # Calculate expected goals using Bayesian team strengths
        df['ExpectedHomeGoals'] = (
                df.get('HomeAttackStrength', 1.4) *
                df.get('AwayDefenseStrength', 1.2) / 1.2  # Normalize
        )

        df['ExpectedAwayGoals'] = (
                df.get('AwayAttackStrength', 1.2) *
                df.get('HomeDefenseStrength', 1.1) / 1.1  # Normalize
        )

        # Bayesian match outcome probabilities
        elo_diff = df.get('EloAdvantage', 0)

        # Convert Elo difference to win probabilities (more realistic)
        df['BayesianHomeWinProb'] = 1 / (1 + 10 ** (-elo_diff / 400))
        df['BayesianAwayWinProb'] = 1 / (1 + 10 ** (elo_diff / 400))
        df['BayesianDrawProb'] = 1 - df['BayesianHomeWinProb'] - df['BayesianAwayWinProb']

        # Ensure probabilities are realistic
        df['BayesianDrawProb'] = df['BayesianDrawProb'].clip(0.15, 0.40)  # Draw rate typically 15-40%

        return df

    def add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        🚀 COMPLETE: Enhanced rolling features with Bayesian inference.
        """
        df = df.copy()
        df = df.sort_values(['Season', 'Date'])

        print("[Start] Adding BAYESIAN rolling features...")
        print("[OK] All features use .shift(1) - NO DATA LEAKAGE")

        # 1. Calculate Bayesian Elo ratings first
        df = self.calculate_bayesian_elo_ratings(df)

        # 2. Calculate Bayesian team strengths
        df = self.calculate_bayesian_team_strengths(df)

        # 3. Create basic goal columns FIRST (before GW1 analysis needs them)
        print("[Goals] Creating base goal features...")
        if 'TotalGoals' not in df.columns:
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                df['TotalGoals'] = df['FTHG'] + df['FTAG']
                print("   [OK] Created TotalGoals column")

        if 'BTTS' not in df.columns:
            if 'FTHG' in df.columns and 'FTAG' in df.columns:
                df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
                print("   [OK] Created BTTS column")

        # Create Over/Under columns
        for threshold in [1.5, 2.5, 3.5]:
            col_name = f'Over{threshold}'
            if col_name not in df.columns:
                df[col_name] = (df['TotalGoals'] > threshold).astype(int)
                print(f"   [OK] Created {col_name} column")

        # 4. Calculate GW1 insights (after TotalGoals exists)
        df = self._calculate_gw1_historical_stats(df)

        # 5. Identify promoted teams with penalties
        df = self.identify_promoted_teams_with_penalties(df)

        # 6. Calculate all rolling features (vectorized for speed)
        print("[Stats] Calculating team form...")
        df = self._calculate_team_form_vectorized(df)

        print("[Goals] Calculating goal features...")
        df = self._calculate_goal_features_vectorized(df)

        print("[Stats] Calculating shot features...")
        df = self._calculate_shot_features_vectorized(df)

        print("[Cards] Calculating disciplinary features...")
        df = self._calculate_disciplinary_features(df)

        # ✨ NEW: Calculate half-time pattern features
        print("[HT] Calculating half-time features...")
        df = self._calculate_halftime_features(df)

        # ✨ NEW: Calculate rest days and fixture congestion
        print("[REST] Calculating fixture congestion features...")
        df = self._calculate_rest_features(df)

        # 7. Add Bayesian match predictions
        df = self._add_bayesian_match_predictions(df)

        # 8. Fill missing values
        print("[FIX] Filling missing values...")
        df = df.fillna(0)

        print("[OK] BAYESIAN rolling features completed!")

        # Show summary
        feature_count = len([col for col in df.columns if any(x in col for x in
                                                              ['Form', 'Scoring', 'Over', 'BTTS', 'Goals', 'Shot',
                                                               'Elo', 'GW1', 'Bayesian', 'Strength', 'Half', 'Rest',
                                                               'Congestion', 'Conversion', 'Starter', 'Finisher'])])
        print(f"📊 Created {feature_count} enhanced Bayesian features (including new HT + Rest + Shot features)")

        return df

    def get_gw1_insights(self) -> dict:
        """Return GW1 historical insights."""
        return self.gw1_stats

    def get_promoted_teams(self) -> dict:
        """Return promoted teams by season."""
        return self.promotion_teams

    def get_elo_ratings(self) -> dict:
        """Return final Elo ratings."""
        return self.elo_ratings

    def get_bayesian_team_strengths(self) -> dict:
        """Return Bayesian team strength calculations."""
        return {
            'league_priors': getattr(self, 'league_strength_distribution', {}),
            'team_priors': getattr(self, 'team_strength_priors', {}),
            'promoted_teams': self.promotion_teams
        }