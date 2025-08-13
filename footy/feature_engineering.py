# footy/feature_engineering.py - ENHANCED & STREAMLINED VERSION

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from itertools import takewhile


class FootballFeatureEngineering:
    """Enhanced football feature engineering that integrates with rolling features."""

    def __init__(self):
        self.team_encodings = {}
        self.scaler = StandardScaler()
        self.referee_stats = {}
        self.h2h_deep_stats = {}

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

    def create_referee_analysis(self, df):
        """
        ✨ Enhanced referee analysis for betting insights.
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

        print("🔍 Analyzing referee tendencies...")

        # Calculate referee statistics
        ref_stats = {}
        for referee in df['Referee'].dropna().unique():
            ref_matches = df[df['Referee'] == referee]
            if len(ref_matches) < 5:  # Skip referees with few matches
                continue

            stats = {
                'matches': len(ref_matches),
                'avg_total_goals': ref_matches['TotalGoals'].mean(),
                'home_win_rate': (ref_matches['FTR'] == 'H').mean(),
                'over_2_5_rate': (ref_matches['TotalGoals'] > 2.5).mean(),
                'btts_rate': ref_matches['BTTS'].mean() if 'BTTS' in ref_matches.columns else 0.5
            }

            # Add card/foul stats if available
            if all(col in ref_matches.columns for col in ['HY', 'AY']):
                stats['avg_yellow_cards'] = (ref_matches['HY'] + ref_matches['AY']).mean()
            else:
                stats['avg_yellow_cards'] = 4.0

            if all(col in ref_matches.columns for col in ['HF', 'AF']):
                stats['avg_fouls'] = (ref_matches['HF'] + ref_matches['AF']).mean()
            else:
                stats['avg_fouls'] = 20.0

            ref_stats[referee] = stats

        self.referee_stats = ref_stats

        # Add referee features to dataframe
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

        print(f"✅ Analyzed {len(ref_stats)} referees")
        return df

    def create_advanced_h2h_analysis(self, df):
        """
        ✨ Enhanced H2H analysis with proper time-awareness.
        """
        df = df.copy()
        df = df.sort_values(['Season', 'Date'])

        print("🔍 Creating advanced H2H analysis...")

        # Initialize H2H columns
        df['H2H_HomeWinRate'] = 0.45  # Default slight home advantage
        df['H2H_AvgGoals'] = 2.5  # League average default
        df['H2H_BTTSRate'] = 0.55  # Default BTTS rate
        df['H2H_RecentForm'] = 0.5  # Default neutral
        df['H2H_GoalTrend'] = 0.0  # Default no trend

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

            # Calculate H2H stats for each match in this pairing
            for idx in matchup_matches.index:
                match_date = df.at[idx, 'Date']

                # Get PAST H2H matches only
                past_h2h = matchup_matches[matchup_matches['Date'] < match_date]

                if len(past_h2h) >= 2:
                    # Calculate home wins for the current home team
                    home_wins = len(past_h2h[
                                        ((past_h2h['HomeTeam'] == home_team) & (past_h2h['FTR'] == 'H')) |
                                        ((past_h2h['AwayTeam'] == home_team) & (past_h2h['FTR'] == 'A'))
                                        ])

                    df.at[idx, 'H2H_HomeWinRate'] = home_wins / len(past_h2h)
                    df.at[idx, 'H2H_AvgGoals'] = past_h2h['TotalGoals'].mean()
                    df.at[idx, 'H2H_BTTSRate'] = past_h2h['BTTS'].mean()

                    # Recent form (last 3 H2H)
                    if len(past_h2h) >= 3:
                        recent_h2h = past_h2h.tail(3)
                        recent_home_wins = len(recent_h2h[
                                                   ((recent_h2h['HomeTeam'] == home_team) & (
                                                               recent_h2h['FTR'] == 'H')) |
                                                   ((recent_h2h['AwayTeam'] == home_team) & (recent_h2h['FTR'] == 'A'))
                                                   ])
                        df.at[idx, 'H2H_RecentForm'] = recent_home_wins / len(recent_h2h)

                        # Goal trend
                        if len(past_h2h) >= 5:
                            recent_goals = recent_h2h['TotalGoals'].mean()
                            older_goals = past_h2h.head(-3)['TotalGoals'].mean()
                            df.at[idx, 'H2H_GoalTrend'] = recent_goals - older_goals

        print("✅ Advanced H2H analysis completed")
        return df

    def create_advanced_metrics(self, df):
        """Enhanced advanced performance metrics that work with rolling features."""
        df = df.copy()

        # Only create shot efficiency if data exists and not already calculated
        if all(col in df.columns for col in ['HS', 'AS', 'HST', 'AST']):
            if 'HomeShotAccuracy' not in df.columns:
                df['HomeShotAccuracy'] = np.where(df['HS'] > 0, df['HST'] / df['HS'], 0)
                df['AwayShotAccuracy'] = np.where(df['AS'] > 0, df['AST'] / df['AS'], 0)

            if 'HomeGoalConversion' not in df.columns:
                df['HomeGoalConversion'] = np.where(df['HST'] > 0, df['FTHG'] / df['HST'], 0)
                df['AwayGoalConversion'] = np.where(df['AST'] > 0, df['FTAG'] / df['AST'], 0)

            # Enhanced xG model if not exist
            if 'HomexG' not in df.columns:
                df['HomexG'] = df['HS'] * 0.08 + df['HST'] * 0.25
                df['AwayxG'] = df['AS'] * 0.08 + df['AST'] * 0.25

        return df

    def create_team_strength_indicators(self, df):
        """Enhanced team strength using rolling features."""
        df = df.copy()

        # Use rolling features if they exist, otherwise create basic ones
        for team_type in ['Home', 'Away']:
            scoring_col = f'{team_type}ScoringForm_5'
            conceding_col = f'{team_type}ConcedingForm_5'
            form_col = f'{team_type}Form_5'

            if scoring_col in df.columns and conceding_col in df.columns:
                # Attack strength (relative to league average)
                league_avg_scoring = df.groupby('League')[scoring_col].transform('mean')
                df[f'{team_type}AttackStrength'] = df[scoring_col] / (league_avg_scoring + 0.01)

                # Defense strength (lower is better for defense)
                league_avg_conceding = df.groupby('League')[conceding_col].transform('mean')
                df[f'{team_type}DefenseStrength'] = df[conceding_col] / (league_avg_conceding + 0.01)

                # Form momentum if we have multiple windows
                if f'{team_type}Form_3' in df.columns and f'{team_type}Form_10' in df.columns:
                    df[f'{team_type}FormMomentum'] = (
                            df[f'{team_type}Form_3'] - df[f'{team_type}Form_10']
                    )

        return df

    def create_match_context(self, df):
        """Enhanced contextual match features."""
        df = df.copy()

        # Season progress (if not already calculated)
        if 'SeasonProgress' not in df.columns:
            df['SeasonProgress'] = df.groupby(['League', 'Season'])['Date'].transform(
                lambda x: (x - x.min()) / (x.max() - x.min() + pd.Timedelta(days=1))
            )

        # Days rest if not already calculated
        if 'HomeDaysRest' not in df.columns:
            df['HomeDaysRest'] = df.groupby('HomeTeam')['Date'].diff().dt.days
            df['AwayDaysRest'] = df.groupby('AwayTeam')['Date'].diff().dt.days

        # Match timing features
        if 'DayOfWeek' not in df.columns:
            df['DayOfWeek'] = df['Date'].dt.dayofweek
            df['Month'] = df['Date'].dt.month
            df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)

        # Competition intensity
        if 'MatchDensity' not in df.columns:
            df['MatchDensity'] = df.groupby(['League', 'Season'])['Date'].transform(
                lambda x: x.dt.to_period('M').value_counts()[x.dt.to_period('M')].values
            )

        return df

    def create_enhanced_goal_potential(self, df):
        """
        ✨ NEW: Enhanced goal potential indicators using rolling features.
        """
        df = df.copy()

        # Combined goal potential (if rolling features exist)
        home_scoring = df.get('HomeScoringForm_5', df.get('FTHG', 0))
        away_scoring = df.get('AwayScoringForm_5', df.get('FTAG', 0))

        if isinstance(home_scoring, pd.Series) and isinstance(away_scoring, pd.Series):
            df['CombinedGoalPotential'] = (home_scoring + away_scoring) / 2
        else:
            df['CombinedGoalPotential'] = 1.25  # Default

        # Defensive struggle indicator
        home_conceding = df.get('HomeConcedingForm_5', 1.0)
        away_conceding = df.get('AwayConcedingForm_5', 1.0)

        if isinstance(home_conceding, pd.Series) and isinstance(away_conceding, pd.Series):
            df['DefensiveStruggle'] = (home_conceding + away_conceding) / 2
        else:
            df['DefensiveStruggle'] = 1.0  # Default

        # Over/Under tendency
        home_over_25 = df.get('HomeOverRate2.5_5', 0.5)
        away_over_25 = df.get('AwayOverRate2.5_5', 0.5)

        if isinstance(home_over_25, pd.Series) and isinstance(away_over_25, pd.Series):
            df['Over25Tendency'] = (home_over_25 + away_over_25) / 2
        else:
            df['Over25Tendency'] = 0.5  # Default

        return df

    def create_gw1_enhanced_features(self, df):
        """
        ✨ Enhanced GW1 features that work with rolling_features GW1 analysis.
        """
        df = df.copy()

        # Use IsEarlySeason if already calculated, otherwise create it
        if 'IsEarlySeason' not in df.columns:
            if 'SeasonProgress' in df.columns:
                df['IsEarlySeason'] = (df['SeasonProgress'] <= 0.15).astype(int)
            else:
                df['IsEarlySeason'] = 0

        print("🔍 Creating enhanced GW1 features...")

        # Calculate team's historical GW1 performance if we have the data
        if df['IsEarlySeason'].sum() > 0:
            gw1_data = df[df['IsEarlySeason'] == 1]

            for team_type in ['Home', 'Away']:
                team_col = f'{team_type}Team'
                goals_col = 'FTHG' if team_type == 'Home' else 'FTAG'

                # Historical GW1 goal scoring
                gw1_scoring = gw1_data.groupby(team_col)[goals_col].mean()
                df[f'{team_type}GW1ScoringHistory'] = df[team_col].map(gw1_scoring).fillna(1.2)

                # Historical GW1 form
                gw1_form = gw1_data.groupby(team_col)['FTR'].apply(
                    lambda x: (x == ('H' if team_type == 'Home' else 'A')).mean()
                )
                df[f'{team_type}GW1FormHistory'] = df[team_col].map(gw1_form).fillna(0.4)

        # Promoted team adjustments
        if 'IsPromotedTeam' in df.columns:
            df['PromotedTeamEarlyBonus'] = (
                    df['IsPromotedTeam'] * df['IsEarlySeason'] * 0.1
            )
        else:
            df['PromotedTeamEarlyBonus'] = 0

        print("✅ Enhanced GW1 features created")
        return df

    def engineer_features(self, df):
        """
        🚀 ENHANCED: Complete feature engineering pipeline that integrates with rolling features.
        """
        print("🚀 Starting ENHANCED feature engineering...")
        print("✅ Integrates with rolling features from previous step")
        df = df.copy()

        # Check what we already have from rolling features
        existing_features = df.columns.tolist()
        elo_exists = 'HomeElo' in existing_features
        form_exists = 'HomeForm_5' in existing_features

        print(f"📊 Input features: {len(existing_features)}")
        if elo_exists:
            print("✅ Elo ratings already calculated")
        if form_exists:
            print("✅ Rolling features already calculated")

        # Execute each step in sequence
        print("🔧 Creating base features...")
        df = self.create_base_features(df)

        print("🔧 Creating advanced metrics...")
        df = self.create_advanced_metrics(df)

        print("🔧 Creating team strength indicators...")
        df = self.create_team_strength_indicators(df)

        print("🔧 Creating match context features...")
        df = self.create_match_context(df)

        print("🔧 Creating referee analysis...")
        df = self.create_referee_analysis(df)

        print("🔧 Creating advanced H2H analysis...")
        df = self.create_advanced_h2h_analysis(df)

        print("🔧 Creating enhanced goal potential...")
        df = self.create_enhanced_goal_potential(df)

        print("🔧 Creating enhanced GW1 features...")
        df = self.create_gw1_enhanced_features(df)

        # Handle missing values
        print("🔧 Handling missing values...")
        df = df.fillna(0)

        # Count final features
        final_features = len(df.columns)
        new_features = final_features - len(existing_features)

        print("✅ ENHANCED feature engineering completed!")
        print(f"📊 Added {new_features} new features")
        print(f"📊 Total features: {final_features}")

        # Show sample of new features
        feature_types = {
            'Elo': [col for col in df.columns if 'Elo' in col],
            'H2H': [col for col in df.columns if 'H2H' in col],
            'Referee': [col for col in df.columns if 'Ref' in col],
            'GW1': [col for col in df.columns if 'GW1' in col],
            'Strength': [col for col in df.columns if 'Strength' in col or 'Potential' in col]
        }

        for feature_type, features in feature_types.items():
            if features:
                print(f"   {feature_type}: {len(features)} features")

        return df

    def get_referee_insights(self):
        """Return referee analysis for predictions."""
        return self.referee_stats

    def get_team_encodings(self):
        """Return team encodings for reference."""
        return self.team_encodings