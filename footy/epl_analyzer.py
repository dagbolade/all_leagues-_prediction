# footy/epl_analyzer.py - ENHANCED VERSION

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta


class AdvancedEPLAnalyzer:
    """Enhanced EPL analyzer with GW1 insights and advanced analytics."""

    def __init__(self):
        self.gw1_insights = {}
        self.team_strength_matrix = {}
        self.referee_insights = {}
        self.prediction_confidence = {}

    def analyze_gw1_historical_patterns(self, df):
        """
        ✨ NEW: Analyze first 5 gameweeks patterns across all seasons.
        Critical for early season predictions.
        """
        print("🔍 Analyzing GW1-5 historical patterns...")

        # Filter for EPL and early season matches
        epl_df = df[df['League'] == 'E0'].copy()
        if 'IsEarlySeason' in df.columns:
            gw1_df = epl_df[epl_df['IsEarlySeason'] == 1].copy()
        else:
            # Fallback: use season progress
            epl_df['SeasonProgress'] = epl_df.groupby('Season')['Date'].transform(
                lambda x: (x - x.min()) / (x.max() - x.min() + pd.Timedelta(days=1))
            )
            gw1_df = epl_df[epl_df['SeasonProgress'] <= 0.15].copy()

        if len(gw1_df) == 0:
            print("⚠️ No GW1 data found")
            return {}

        # Calculate GW1 statistics
        gw1_stats = {
            'total_matches': len(gw1_df),
            'avg_goals_per_match': (gw1_df['FTHG'] + gw1_df['FTAG']).mean(),
            'home_win_rate': (gw1_df['FTR'] == 'H').mean(),
            'away_win_rate': (gw1_df['FTR'] == 'A').mean(),
            'draw_rate': (gw1_df['FTR'] == 'D').mean(),
            'over_1_5_rate': ((gw1_df['FTHG'] + gw1_df['FTAG']) > 1.5).mean(),
            'over_2_5_rate': ((gw1_df['FTHG'] + gw1_df['FTAG']) > 2.5).mean(),
            'over_3_5_rate': ((gw1_df['FTHG'] + gw1_df['FTAG']) > 3.5).mean(),
            'btts_rate': ((gw1_df['FTHG'] > 0) & (gw1_df['FTAG'] > 0)).mean(),
            'clean_sheet_rate': ((gw1_df['FTHG'] == 0) | (gw1_df['FTAG'] == 0)).mean(),
            'high_scoring_rate': ((gw1_df['FTHG'] + gw1_df['FTAG']) >= 4).mean()
        }

        # Team-specific GW1 patterns
        team_gw1_stats = {}
        for team in gw1_df['HomeTeam'].unique():
            team_home = gw1_df[gw1_df['HomeTeam'] == team]
            team_away = gw1_df[gw1_df['AwayTeam'] == team]

            if len(team_home) + len(team_away) >= 3:  # Minimum sample
                team_stats = {
                    'matches': len(team_home) + len(team_away),
                    'home_goals_avg': team_home['FTHG'].mean() if len(team_home) > 0 else 0,
                    'away_goals_avg': team_away['FTAG'].mean() if len(team_away) > 0 else 0,
                    'home_conceded_avg': team_home['FTAG'].mean() if len(team_home) > 0 else 0,
                    'away_conceded_avg': team_away['FTHG'].mean() if len(team_away) > 0 else 0,
                    'gw1_form': (len(team_home[team_home['FTR'] == 'H']) +
                                 len(team_away[team_away['FTR'] == 'A'])) / (len(team_home) + len(team_away)),
                    'gw1_over_2_5': ((team_home['FTHG'] + team_home['FTAG'] > 2.5).sum() +
                                     (team_away['FTHG'] + team_away['FTAG'] > 2.5).sum()) / (
                                                len(team_home) + len(team_away))
                }
                team_gw1_stats[team] = team_stats

        self.gw1_insights = {
            'overall': gw1_stats,
            'teams': team_gw1_stats
        }

        print(f"✅ GW1 Analysis Complete:")
        print(f"   📊 {gw1_stats['total_matches']} early season matches analyzed")
        print(f"   ⚽ Avg Goals: {gw1_stats['avg_goals_per_match']:.2f}")
        print(f"   🏠 Home Win Rate: {gw1_stats['home_win_rate']:.1%}")
        print(f"   📈 Over 2.5 Rate: {gw1_stats['over_2_5_rate']:.1%}")

        return self.gw1_insights

    def analyze_team_strength_matrix(self, df):
        """
        ✨ NEW: Create comprehensive team strength analysis.
        """
        print("🔍 Creating team strength matrix...")

        # Focus on current season EPL
        current_season = df['Season'].max()
        epl_current = df[(df['League'] == 'E0') & (df['Season'] == current_season)].copy()

        if len(epl_current) == 0:
            print("⚠️ No current season EPL data found")
            return {}

        team_matrix = {}

        for team in epl_current['HomeTeam'].unique():
            home_matches = epl_current[epl_current['HomeTeam'] == team]
            away_matches = epl_current[epl_current['AwayTeam'] == team]

            # Basic stats
            total_matches = len(home_matches) + len(away_matches)

            if total_matches >= 5:  # Minimum sample
                # Goals
                goals_scored = home_matches['FTHG'].sum() + away_matches['FTAG'].sum()
                goals_conceded = home_matches['FTAG'].sum() + away_matches['FTHG'].sum()

                # Results
                wins = len(home_matches[home_matches['FTR'] == 'H']) + len(away_matches[away_matches['FTR'] == 'A'])
                draws = len(home_matches[home_matches['FTR'] == 'D']) + len(away_matches[away_matches['FTR'] == 'D'])
                losses = total_matches - wins - draws

                # Advanced metrics
                over_2_5 = (len(home_matches[home_matches['FTHG'] + home_matches['FTAG'] > 2.5]) +
                            len(away_matches[away_matches['FTHG'] + away_matches['FTAG'] > 2.5]))

                btts = (len(home_matches[(home_matches['FTHG'] > 0) & (home_matches['FTAG'] > 0)]) +
                        len(away_matches[(away_matches['FTHG'] > 0) & (away_matches['FTAG'] > 0)]))

                # Elo rating if available
                elo_rating = home_matches['HomeElo'].iloc[-1] if 'HomeElo' in home_matches.columns and len(
                    home_matches) > 0 else 1500

                team_matrix[team] = {
                    'matches': total_matches,
                    'wins': wins,
                    'draws': draws,
                    'losses': losses,
                    'win_rate': wins / total_matches,
                    'goals_scored': goals_scored,
                    'goals_conceded': goals_conceded,
                    'goal_difference': goals_scored - goals_conceded,
                    'goals_per_match': goals_scored / total_matches,
                    'goals_conceded_per_match': goals_conceded / total_matches,
                    'over_2_5_rate': over_2_5 / total_matches,
                    'btts_rate': btts / total_matches,
                    'elo_rating': elo_rating,
                    'attack_strength': (goals_scored / total_matches) / 2.5,  # Relative to league avg
                    'defense_strength': 1 - ((goals_conceded / total_matches) / 2.5),  # Higher = better defense
                    'form_recent': wins / max(total_matches, 1) if total_matches <= 5 else wins / 5  # Recent form
                }

        self.team_strength_matrix = team_matrix
        print(f"✅ Team strength matrix created for {len(team_matrix)} teams")
        return team_matrix

    def analyze_epl_current_season(self, df):
        """Enhanced current season analysis with advanced metrics."""
        # Get current season EPL data
        current_season = df['Season'].max()
        epl_df = df[(df['League'] == 'E0') & (df['Season'] == current_season)].copy()

        if len(epl_df) == 0:
            print("⚠️ No current season EPL data found")
            return pd.DataFrame()

        # Calculate enhanced match statistics
        epl_df['TotalGoals'] = epl_df['FTHG'] + epl_df['FTAG']
        epl_df['TotalFouls'] = epl_df['HF'] + epl_df['AF'] if 'HF' in epl_df.columns else 0
        epl_df['BTTS'] = ((epl_df['FTHG'] > 0) & (epl_df['FTAG'] > 0)).astype(int)
        epl_df['Over1.5'] = (epl_df['TotalGoals'] > 1.5).astype(int)
        epl_df['Over2.5'] = (epl_df['TotalGoals'] > 2.5).astype(int)
        epl_df['Over3.5'] = (epl_df['TotalGoals'] > 3.5).astype(int)

        # Create enhanced team statistics
        team_stats = []
        for team in epl_df['HomeTeam'].unique():
            home_games = epl_df[epl_df['HomeTeam'] == team]
            away_games = epl_df[epl_df['AwayTeam'] == team]
            all_games = len(home_games) + len(away_games)

            if all_games == 0:
                continue

            # Basic stats
            stats = {
                'Team': team,
                'Games': all_games,
                'Wins': len(home_games[home_games['FTR'] == 'H']) + len(away_games[away_games['FTR'] == 'A']),
                'Draws': len(home_games[home_games['FTR'] == 'D']) + len(away_games[away_games['FTR'] == 'D']),
                'Losses': all_games - (
                            len(home_games[home_games['FTR'] == 'H']) + len(away_games[away_games['FTR'] == 'A']) +
                            len(home_games[home_games['FTR'] == 'D']) + len(away_games[away_games['FTR'] == 'D'])),
                'GoalsScored': home_games['FTHG'].sum() + away_games['FTAG'].sum(),
                'GoalsConceded': home_games['FTAG'].sum() + away_games['FTHG'].sum(),
                'Over1.5_Games': len(home_games[home_games['Over1.5'] == 1]) + len(
                    away_games[away_games['Over1.5'] == 1]),
                'Over2.5_Games': len(home_games[home_games['Over2.5'] == 1]) + len(
                    away_games[away_games['Over2.5'] == 1]),
                'Over3.5_Games': len(home_games[home_games['Over3.5'] == 1]) + len(
                    away_games[away_games['Over3.5'] == 1]),
                'BTTS_Games': len(home_games[home_games['BTTS'] == 1]) + len(away_games[away_games['BTTS'] == 1]),
                'CleanSheets': len(home_games[home_games['FTAG'] == 0]) + len(away_games[away_games['FTHG'] == 0]),
            }

            # Enhanced metrics
            if 'TotalFouls' in epl_df.columns:
                stats['TotalFouls'] = home_games['TotalFouls'].sum() + away_games['TotalFouls'].sum()
                stats['AvgFouls'] = stats['TotalFouls'] / all_games if all_games > 0 else 0

            # Elo rating if available
            if 'HomeElo' in home_games.columns and len(home_games) > 0:
                stats['EloRating'] = home_games['HomeElo'].iloc[-1]
            elif 'AwayElo' in away_games.columns and len(away_games) > 0:
                stats['EloRating'] = away_games['AwayElo'].iloc[-1]
            else:
                stats['EloRating'] = 1500  # Default

            # Performance ratios
            stats['WinRate'] = stats['Wins'] / all_games if all_games > 0 else 0
            stats['GoalsPerGame'] = stats['GoalsScored'] / all_games if all_games > 0 else 0
            stats['GoalsConcededPerGame'] = stats['GoalsConceded'] / all_games if all_games > 0 else 0
            stats['GoalDifference'] = stats['GoalsScored'] - stats['GoalsConceded']

            team_stats.append(stats)

        return pd.DataFrame(team_stats)

    def create_gw1_insights_dashboard(self, gw1_insights):
        """
        ✨ NEW: Create GW1 insights visualization dashboard.
        """
        if not gw1_insights or 'overall' not in gw1_insights:
            return go.Figure()

        print("📊 Creating GW1 insights dashboard...")

        overall_stats = gw1_insights['overall']

        # Create dashboard
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                'GW1-5 Goal Statistics',
                'Result Distribution',
                'Over/Under Patterns',
                'BTTS vs Clean Sheets',
                'Home Advantage in Early Season',
                'Key GW1 Metrics'
            ),
            specs=[[{"type": "bar"}, {"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}, {"type": "indicator"}]]
        )

        # 1. Goal statistics
        fig.add_trace(
            go.Bar(
                name='Goals Stats',
                x=['Avg Goals/Match', 'Over 1.5 Rate', 'Over 2.5 Rate', 'Over 3.5 Rate'],
                y=[overall_stats['avg_goals_per_match'],
                   overall_stats['over_1_5_rate'] * 4,  # Scale for visibility
                   overall_stats['over_2_5_rate'] * 4,
                   overall_stats['over_3_5_rate'] * 4],
                text=[f"{overall_stats['avg_goals_per_match']:.2f}",
                      f"{overall_stats['over_1_5_rate']:.1%}",
                      f"{overall_stats['over_2_5_rate']:.1%}",
                      f"{overall_stats['over_3_5_rate']:.1%}"],
                textposition='auto',
            ),
            row=1, col=1
        )

        # 2. Result distribution
        fig.add_trace(
            go.Pie(
                labels=['Home Wins', 'Draws', 'Away Wins'],
                values=[overall_stats['home_win_rate'],
                        overall_stats['draw_rate'],
                        overall_stats['away_win_rate']],
                textinfo='label+percent',
            ),
            row=1, col=2
        )

        # 3. Over/Under patterns
        fig.add_trace(
            go.Bar(
                name='O/U Patterns',
                x=['Over 1.5', 'Over 2.5', 'Over 3.5', 'High Scoring (4+)'],
                y=[overall_stats['over_1_5_rate'],
                   overall_stats['over_2_5_rate'],
                   overall_stats['over_3_5_rate'],
                   overall_stats.get('high_scoring_rate', 0)],
                text=[f"{overall_stats['over_1_5_rate']:.1%}",
                      f"{overall_stats['over_2_5_rate']:.1%}",
                      f"{overall_stats['over_3_5_rate']:.1%}",
                      f"{overall_stats.get('high_scoring_rate', 0):.1%}"],
                textposition='auto',
            ),
            row=1, col=3
        )

        # 4. BTTS vs Clean Sheets
        fig.add_trace(
            go.Bar(
                name='BTTS vs CS',
                x=['Both Teams Score', 'Clean Sheets'],
                y=[overall_stats['btts_rate'], overall_stats['clean_sheet_rate']],
                text=[f"{overall_stats['btts_rate']:.1%}",
                      f"{overall_stats['clean_sheet_rate']:.1%}"],
                textposition='auto',
            ),
            row=2, col=1
        )

        # 5. Home advantage
        home_advantage = overall_stats['home_win_rate'] - overall_stats['away_win_rate']
        fig.add_trace(
            go.Bar(
                name='Home Advantage',
                x=['Home Win Rate', 'Away Win Rate', 'Home Advantage'],
                y=[overall_stats['home_win_rate'],
                   overall_stats['away_win_rate'],
                   home_advantage],
                text=[f"{overall_stats['home_win_rate']:.1%}",
                      f"{overall_stats['away_win_rate']:.1%}",
                      f"+{home_advantage:.1%}" if home_advantage > 0 else f"{home_advantage:.1%}"],
                textposition='auto',
            ),
            row=2, col=2
        )

        # 6. Key metrics indicator
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=overall_stats['avg_goals_per_match'],
                delta={"reference": 2.5, "relative": True},
                title={"text": "Avg Goals vs League Avg"},
                domain={'x': [0, 1], 'y': [0, 1]}
            ),
            row=2, col=3
        )

        fig.update_layout(
            height=800,
            width=1400,
            title_text="GW1-5 Historical Insights Dashboard (5 Season Analysis)",
            showlegend=False
        )

        return fig

    def create_enhanced_epl_visualizations(self, team_stats):
        """Enhanced EPL visualizations with advanced metrics."""
        if len(team_stats) == 0:
            return go.Figure()

        print("📊 Creating enhanced EPL visualizations...")

        # Create comprehensive dashboard
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=('Team Win Rates & Elo Ratings',
                            'Goals Scored vs Conceded',
                            'Over 2.5 Goals Performance',
                            'BTTS Performance',
                            'Attack vs Defense Strength',
                            'Clean Sheets & Goal Difference',
                            'High Scoring Games (Over 3.5)',
                            'Form & Consistency Metrics'))

        # Sort teams by win rate for better visualization
        team_stats_sorted = team_stats.sort_values('WinRate', ascending=False)

        # 1. Win rates & Elo
        fig.add_trace(
            go.Bar(
                name='Win Rate',
                x=team_stats_sorted['Team'],
                y=team_stats_sorted['WinRate'],
                text=team_stats_sorted['WinRate'].apply(lambda x: f"{x:.1%}"),
                textposition='auto',
                yaxis='y1'
            ),
            row=1, col=1
        )

        if 'EloRating' in team_stats_sorted.columns:
            fig.add_trace(
                go.Scatter(
                    name='Elo Rating',
                    x=team_stats_sorted['Team'],
                    y=team_stats_sorted['EloRating'],
                    mode='lines+markers',
                    yaxis='y2',
                    line=dict(color='red')
                ),
                row=1, col=1
            )

        # 2. Goals comparison
        fig.add_trace(
            go.Bar(
                name='Goals Scored',
                x=team_stats['Team'],
                y=team_stats['GoalsPerGame'],
                text=team_stats['GoalsPerGame'].apply(lambda x: f"{x:.1f}"),
                textposition='auto',
            ),
            row=1, col=2
        )

        fig.add_trace(
            go.Bar(
                name='Goals Conceded',
                x=team_stats['Team'],
                y=team_stats['GoalsConcededPerGame'],
                text=team_stats['GoalsConcededPerGame'].apply(lambda x: f"{x:.1f}"),
                textposition='auto',
            ),
            row=1, col=2
        )

        # 3. Over 2.5 performance
        over_2_5_rate = team_stats['Over2.5_Games'] / team_stats['Games']
        fig.add_trace(
            go.Bar(
                name='Over 2.5 Rate',
                x=team_stats['Team'],
                y=over_2_5_rate,
                text=over_2_5_rate.apply(lambda x: f"{x:.1%}"),
                textposition='auto',
            ),
            row=2, col=1
        )

        # 4. BTTS performance
        btts_rate = team_stats['BTTS_Games'] / team_stats['Games']
        fig.add_trace(
            go.Bar(
                name='BTTS Rate',
                x=team_stats['Team'],
                y=btts_rate,
                text=btts_rate.apply(lambda x: f"{x:.1%}"),
                textposition='auto',
            ),
            row=2, col=2
        )

        # 5. Attack vs Defense (scatter plot)
        fig.add_trace(
            go.Scatter(
                mode='markers+text',
                x=team_stats['GoalsPerGame'],
                y=team_stats['GoalsConcededPerGame'],
                text=team_stats['Team'],
                textposition='top center',
                marker=dict(size=10, color=team_stats['WinRate'], colorscale='RdYlGn', showscale=True),
                name='Attack vs Defense'
            ),
            row=3, col=1
        )

        # 6. Clean sheets & Goal difference
        clean_sheet_rate = team_stats['CleanSheets'] / team_stats['Games']
        fig.add_trace(
            go.Bar(
                name='Clean Sheet Rate',
                x=team_stats['Team'],
                y=clean_sheet_rate,
                text=clean_sheet_rate.apply(lambda x: f"{x:.1%}"),
                textposition='auto',
            ),
            row=3, col=2
        )

        # 7. Over 3.5 performance
        over_3_5_rate = team_stats['Over3.5_Games'] / team_stats['Games']
        fig.add_trace(
            go.Bar(
                name='Over 3.5 Rate',
                x=team_stats['Team'],
                y=over_3_5_rate,
                text=over_3_5_rate.apply(lambda x: f"{x:.1%}"),
                textposition='auto',
            ),
            row=4, col=1
        )

        # 8. Goal difference
        fig.add_trace(
            go.Bar(
                name='Goal Difference',
                x=team_stats['Team'],
                y=team_stats['GoalDifference'],
                text=team_stats['GoalDifference'],
                textposition='auto',
            ),
            row=4, col=2
        )

        # Update layout
        fig.update_layout(
            height=1600,
            width=1400,
            showlegend=True,
            title_text=f"Enhanced EPL Analysis Dashboard - {team_stats['Games'].iloc[0] if len(team_stats) > 0 else 'Current'} Season",
        )

        # Update axes
        fig.update_xaxes(tickangle=45)

        return fig

    def calculate_enhanced_percentages(self, team_stats):
        """Calculate enhanced percentage statistics with confidence intervals."""
        if len(team_stats) == 0:
            return pd.DataFrame()

        percentage_stats = team_stats.copy()

        # Basic percentages
        percentage_stats['Win_Percentage'] = (team_stats['Wins'] / team_stats['Games'] * 100).round(1)
        percentage_stats['Draw_Percentage'] = (team_stats['Draws'] / team_stats['Games'] * 100).round(1)
        percentage_stats['Over1.5_Percentage'] = (team_stats['Over1.5_Games'] / team_stats['Games'] * 100).round(1)
        percentage_stats['Over2.5_Percentage'] = (team_stats['Over2.5_Games'] / team_stats['Games'] * 100).round(1)
        percentage_stats['Over3.5_Percentage'] = (team_stats['Over3.5_Games'] / team_stats['Games'] * 100).round(1)
        percentage_stats['BTTS_Percentage'] = (team_stats['BTTS_Games'] / team_stats['Games'] * 100).round(1)
        percentage_stats['CleanSheet_Percentage'] = (team_stats['CleanSheets'] / team_stats['Games'] * 100).round(1)

        # ✨ NEW: Advanced metrics
        percentage_stats['Attack_Rating'] = (team_stats['GoalsPerGame'] / 2.5 * 100).round(1)  # Relative to avg
        percentage_stats['Defense_Rating'] = ((2.5 - team_stats['GoalsConcededPerGame']) / 2.5 * 100).round(1)
        percentage_stats['Overall_Rating'] = (
                    (percentage_stats['Attack_Rating'] + percentage_stats['Defense_Rating']) / 2).round(1)

        # Confidence intervals (simple version)
        percentage_stats['Over2.5_Confidence'] = np.where(
            team_stats['Games'] >= 10, 'High',
            np.where(team_stats['Games'] >= 5, 'Medium', 'Low')
        )

        return percentage_stats

    def generate_gw1_team_insights(self, team_name):
        """
        ✨ NEW: Generate specific GW1 insights for a team.
        """
        if not self.gw1_insights or 'teams' not in self.gw1_insights:
            return None

        team_stats = self.gw1_insights['teams'].get(team_name)
        if not team_stats:
            return None

        insights = {
            'team': team_name,
            'gw1_matches_analyzed': team_stats['matches'],
            'gw1_form_rating': team_stats['gw1_form'],
            'gw1_scoring_tendency': 'High' if team_stats.get('home_goals_avg', 0) + team_stats.get('away_goals_avg',
                                                                                                   0) > 1.5 else 'Low',
            'gw1_defensive_record': 'Strong' if team_stats.get('home_conceded_avg', 2) + team_stats.get(
                'away_conceded_avg', 2) < 1.5 else 'Weak',
            'gw1_over_2_5_tendency': team_stats.get('gw1_over_2_5', 0.5),
            'gw1_prediction_confidence': 'High' if team_stats['matches'] >= 5 else 'Medium'
        }

        return insights

    def run_enhanced_epl_analysis(self, merged_df):
        """
        Enhanced complete EPL analysis with GW1 insights.
        ✨ NEW: Includes GW1 analysis and advanced team metrics.
        """
        print("🚀 Running ENHANCED EPL Analysis...")

        # 1. GW1 Historical Analysis
        gw1_insights = self.analyze_gw1_historical_patterns(merged_df)

        # 2. Team Strength Matrix
        team_strength = self.analyze_team_strength_matrix(merged_df)

        # 3. Current Season Analysis
        team_stats = self.analyze_epl_current_season(merged_df)
        percentage_stats = self.calculate_enhanced_percentages(team_stats)

        # 4. Create Visualizations
        if len(team_stats) > 0:
            main_viz = self.create_enhanced_epl_visualizations(team_stats)
        else:
            main_viz = go.Figure()

        if gw1_insights:
            gw1_viz = self.create_gw1_insights_dashboard(gw1_insights)
        else:
            gw1_viz = go.Figure()

        results = {
            'team_stats': team_stats,
            'percentage_stats': percentage_stats,
            'main_visualization': main_viz,
            'gw1_dashboard': gw1_viz,
            'gw1_insights': gw1_insights,
            'team_strength_matrix': team_strength,
            'analyzer_instance': self
        }

        print("✅ Enhanced EPL Analysis Complete!")
        return results


def run_epl_analysis(merged_df):
    """
    Enhanced EPL analysis function - maintains compatibility with existing code.
    ✨ NEW: Now includes GW1 insights and advanced analytics.
    """
    analyzer = AdvancedEPLAnalyzer()
    results = analyzer.run_enhanced_epl_analysis(merged_df)

    # Return in original format for compatibility
    return (
        results['team_stats'],
        results['percentage_stats'],
        results['main_visualization']
    )


def get_gw1_insights(merged_df):
    """
    ✨ NEW: Standalone function to get GW1 insights.
    Use this for early season predictions.
    """
    analyzer = AdvancedEPLAnalyzer()
    return analyzer.analyze_gw1_historical_patterns(merged_df)


def get_team_gw1_prediction(merged_df, home_team, away_team):
    """
    ✨ NEW: Get GW1-specific prediction insights for a match.
    """
    analyzer = AdvancedEPLAnalyzer()
    gw1_insights = analyzer.analyze_gw1_historical_patterns(merged_df)

    home_insights = analyzer.generate_gw1_team_insights(home_team)
    away_insights = analyzer.generate_gw1_team_insights(away_team)

    if not home_insights or not away_insights:
        return None

    # Generate match-specific GW1 prediction
    gw1_prediction = {
        'match': f"{home_team} vs {away_team}",
        'gw1_context': True,
        'home_gw1_form': home_insights['gw1_form_rating'],
        'away_gw1_form': away_insights['gw1_form_rating'],
        'combined_gw1_over_2_5': (home_insights['gw1_over_2_5_tendency'] + away_insights['gw1_over_2_5_tendency']) / 2,
        'gw1_goal_expectation': 'High' if (home_insights['gw1_over_2_5_tendency'] + away_insights[
            'gw1_over_2_5_tendency']) > 1.0 else 'Low',
        'historical_gw1_avg_goals': gw1_insights['overall']['avg_goals_per_match'],
        'confidence': 'High' if home_insights['gw1_prediction_confidence'] == 'High' and away_insights[
            'gw1_prediction_confidence'] == 'High' else 'Medium',
        'key_insights': [
            f"Historical GW1-5 average: {gw1_insights['overall']['avg_goals_per_match']:.2f} goals",
            f"GW1 Over 2.5 rate: {gw1_insights['overall']['over_2_5_rate']:.1%}",
            f"GW1 BTTS rate: {gw1_insights['overall']['btts_rate']:.1%}",
            f"{home_team} GW1 form: {home_insights['gw1_form_rating']:.1%}",
            f"{away_team} GW1 form: {away_insights['gw1_form_rating']:.1%}"
        ]
    }

    return gw1_prediction


def get_advanced_match_insights(merged_df, home_team, away_team):
    """
    ✨ NEW: Get comprehensive match insights including referee, H2H, and team strength.
    """
    analyzer = AdvancedEPLAnalyzer()

    # Get team strength
    team_strength = analyzer.analyze_team_strength_matrix(merged_df)

    home_strength = team_strength.get(home_team, {})
    away_strength = team_strength.get(away_team, {})

    if not home_strength or not away_strength:
        return None

    # Calculate match insights
    insights = {
        'match': f"{home_team} vs {away_team}",
        'home_team_strength': {
            'attack_rating': home_strength.get('attack_strength', 1.0),
            'defense_rating': home_strength.get('defense_strength', 1.0),
            'recent_form': home_strength.get('form_recent', 0.5),
            'goals_per_match': home_strength.get('goals_per_match', 1.2),
            'elo_rating': home_strength.get('elo_rating', 1500)
        },
        'away_team_strength': {
            'attack_rating': away_strength.get('attack_strength', 1.0),
            'defense_rating': away_strength.get('defense_strength', 1.0),
            'recent_form': away_strength.get('form_recent', 0.5),
            'goals_per_match': away_strength.get('goals_per_match', 1.2),
            'elo_rating': away_strength.get('elo_rating', 1500)
        },
        'match_prediction_factors': {
            'expected_goals': (home_strength.get('goals_per_match', 1.2) + away_strength.get('goals_per_match',
                                                                                             1.2)) * 0.8,
            'home_advantage': 0.1,  # Historical home advantage
            'elo_difference': home_strength.get('elo_rating', 1500) - away_strength.get('elo_rating', 1500),
            'form_difference': home_strength.get('form_recent', 0.5) - away_strength.get('form_recent', 0.5),
        },
        'betting_insights': {
            'over_2_5_likelihood': 'High' if (home_strength.get('goals_per_match', 1.2) + away_strength.get(
                'goals_per_match', 1.2)) > 2.5 else 'Low',
            'btts_likelihood': 'High' if (home_strength.get('btts_rate', 0.5) + away_strength.get('btts_rate',
                                                                                                  0.5)) > 1.0 else 'Low',
            'recommended_focus': 'Goal markets' if (home_strength.get('over_2_5_rate', 0.5) + away_strength.get(
                'over_2_5_rate', 0.5)) > 1.0 else 'Result markets'
        }
    }

    return insights


def create_gw1_special_dashboard(merged_df):
    """
    ✨ NEW: Create special GW1 dashboard for early season analysis.
    """
    analyzer = AdvancedEPLAnalyzer()
    gw1_insights = analyzer.analyze_gw1_historical_patterns(merged_df)

    if not gw1_insights:
        return go.Figure()

    gw1_viz = analyzer.create_gw1_insights_dashboard(gw1_insights)
    return gw1_viz


# Backward compatibility functions
def analyze_epl_current_season(df):
    """Backward compatibility wrapper."""
    analyzer = AdvancedEPLAnalyzer()
    return analyzer.analyze_epl_current_season(df)


def create_epl_visualizations(team_stats):
    """Backward compatibility wrapper."""
    analyzer = AdvancedEPLAnalyzer()
    return analyzer.create_enhanced_epl_visualizations(team_stats)


def calculate_percentages(team_stats):
    """Backward compatibility wrapper."""
    analyzer = AdvancedEPLAnalyzer()
    return analyzer.calculate_enhanced_percentages(team_stats)