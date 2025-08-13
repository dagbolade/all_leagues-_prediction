# footy/opening_weekend_analyzer.py - DYNAMIC GW1 ANALYSIS

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging


class OpeningWeekendAnalyzer:
    """Extract dynamic opening weekend insights from historical data"""

    def __init__(self, df):
        self.df = df.copy()
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df = self.df.sort_values('Date')

        # Calculate additional columns if not present
        if 'TotalGoals' not in self.df.columns:
            self.df['TotalGoals'] = self.df['FTHG'] + self.df['FTAG']
        if 'BTTS' not in self.df.columns:
            self.df['BTTS'] = ((self.df['FTHG'] > 0) & (self.df['FTAG'] > 0)).astype(int)

        print(f"🔍 Analyzing {len(self.df)} matches for opening weekend patterns...")

    def extract_gw1_matches(self):
        """Dynamically extract opening weekend matches from each season"""
        gw1_matches = []

        # Group by season and league
        for (season, league), season_data in self.df.groupby(['Season', 'League']):
            season_data = season_data.sort_values('Date')

            if len(season_data) > 0:
                # Take first weekend of matches (usually first 10-20 matches depending on league size)
                first_date = season_data['Date'].min()
                # Opening weekend = first 7 days of season
                opening_weekend = season_data[
                    season_data['Date'] <= (first_date + timedelta(days=7))
                    ]

                if len(opening_weekend) > 0:
                    # Mark as GW1
                    opening_weekend = opening_weekend.copy()
                    opening_weekend['IsGW1'] = True
                    opening_weekend['SeasonStart'] = season
                    gw1_matches.append(opening_weekend)

        if gw1_matches:
            gw1_df = pd.concat(gw1_matches, ignore_index=True)
            print(f"✅ Found {len(gw1_df)} opening weekend matches across {len(gw1_matches)} seasons")
            return gw1_df
        else:
            print("❌ No opening weekend matches found")
            return pd.DataFrame()

    def analyze_gw1_patterns(self):
        """Analyze opening weekend patterns from real data"""
        gw1_matches = self.extract_gw1_matches()

        if len(gw1_matches) == 0:
            return self._get_fallback_analysis()

        # Calculate key metrics
        total_matches = len(gw1_matches)

        analysis = {
            'total_gw1_matches': total_matches,
            'goal_patterns': {
                'avg_goals_per_match': round(gw1_matches['TotalGoals'].mean(), 2),
                'over_15_rate': round((gw1_matches['TotalGoals'] > 1.5).mean() * 100, 1),
                'over_25_rate': round((gw1_matches['TotalGoals'] > 2.5).mean() * 100, 1),
                'over_35_rate': round((gw1_matches['TotalGoals'] > 3.5).mean() * 100, 1),
                'btts_rate': round(gw1_matches['BTTS'].mean() * 100, 1),
                'high_scoring_games': len(gw1_matches[gw1_matches['TotalGoals'] >= 4])
            },
            'match_outcomes': {
                'home_win_rate': round((gw1_matches['FTR'] == 'H').mean() * 100, 1),
                'draw_rate': round((gw1_matches['FTR'] == 'D').mean() * 100, 1),
                'away_win_rate': round((gw1_matches['FTR'] == 'A').mean() * 100, 1)
            },
            'seasonal_trends': self._analyze_seasonal_trends(gw1_matches),
            'league_comparison': self._analyze_by_league(gw1_matches)
        }

        return analysis

    def _analyze_seasonal_trends(self, gw1_matches):
        """Analyze how opening weekends vary by season"""
        seasonal_stats = []

        for season in gw1_matches['SeasonStart'].unique():
            season_data = gw1_matches[gw1_matches['SeasonStart'] == season]

            if len(season_data) > 0:
                seasonal_stats.append({
                    'season': season,
                    'matches': len(season_data),
                    'avg_goals': round(season_data['TotalGoals'].mean(), 2),
                    'over_25_rate': round((season_data['TotalGoals'] > 2.5).mean() * 100, 1),
                    'btts_rate': round(season_data['BTTS'].mean() * 100, 1),
                    'home_advantage': round((season_data['FTR'] == 'H').mean() * 100, 1)
                })

        return seasonal_stats

    def _analyze_by_league(self, gw1_matches):
        """Compare opening weekend patterns by league"""
        league_stats = []

        for league in gw1_matches['League'].unique():
            league_data = gw1_matches[gw1_matches['League'] == league]

            if len(league_data) >= 10:  # Only leagues with sufficient data
                league_stats.append({
                    'league': league,
                    'league_name': self._get_league_name(league),
                    'matches': len(league_data),
                    'avg_goals': round(league_data['TotalGoals'].mean(), 2),
                    'over_25_rate': round((league_data['TotalGoals'] > 2.5).mean() * 100, 1),
                    'btts_rate': round(league_data['BTTS'].mean() * 100, 1),
                    'home_wins': round((league_data['FTR'] == 'H').mean() * 100, 1)
                })

        # Sort by avg goals (most exciting leagues first)
        league_stats.sort(key=lambda x: x['avg_goals'], reverse=True)
        return league_stats

    def _get_league_name(self, code):
        """Convert league codes to readable names"""
        league_names = {
            'E0': 'Premier League',
            'E1': 'Championship',
            'E2': 'League One',
            'E3': 'League Two',
            'D1': 'Bundesliga',
            'D2': '2. Bundesliga',
            'SP1': 'La Liga',
            'SP2': 'La Liga 2',
            'I1': 'Serie A',
            'I2': 'Serie B',
            'F1': 'Ligue 1',
            'F2': 'Ligue 2',
            'B1': 'Belgian Pro League',
            'N1': 'Eredivisie',
            'P1': 'Primeira Liga',
            'T1': 'Turkish Super Lig'
        }
        return league_names.get(code, code)

    def get_team_gw1_history(self, team_name, league='E0'):
        """Get specific team's opening weekend history"""
        gw1_matches = self.extract_gw1_matches()

        if len(gw1_matches) == 0:
            return {'error': 'No GW1 data available'}

        # Filter for specific team
        team_gw1 = gw1_matches[
            ((gw1_matches['HomeTeam'] == team_name) |
             (gw1_matches['AwayTeam'] == team_name)) &
            (gw1_matches['League'] == league)
            ].sort_values('Date', ascending=False)

        if len(team_gw1) == 0:
            return {'error': f'No GW1 data found for {team_name}'}

        # Calculate team-specific stats
        wins = draws = losses = goals_for = goals_against = 0

        for _, match in team_gw1.iterrows():
            if match['HomeTeam'] == team_name:
                goals_for += match['FTHG']
                goals_against += match['FTAG']
                if match['FTR'] == 'H':
                    wins += 1
                elif match['FTR'] == 'D':
                    draws += 1
                else:
                    losses += 1
            else:
                goals_for += match['FTAG']
                goals_against += match['FTHG']
                if match['FTR'] == 'A':
                    wins += 1
                elif match['FTR'] == 'D':
                    draws += 1
                else:
                    losses += 1

        return {
            'team': team_name,
            'gw1_appearances': len(team_gw1),
            'record': f"{wins}W-{draws}D-{losses}L",
            'win_rate': round(wins / len(team_gw1) * 100, 1) if len(team_gw1) > 0 else 0,
            'avg_goals_scored': round(goals_for / len(team_gw1), 1) if len(team_gw1) > 0 else 0,
            'avg_goals_conceded': round(goals_against / len(team_gw1), 1) if len(team_gw1) > 0 else 0,
            'recent_gw1_results': [
                {
                    'season': match['SeasonStart'],
                    'opponent': match['AwayTeam'] if match['HomeTeam'] == team_name else match['HomeTeam'],
                    'venue': 'Home' if match['HomeTeam'] == team_name else 'Away',
                    'result': f"{match['FTHG']}-{match['FTAG']}",
                    'outcome': self._get_team_result(match, team_name)
                }
                for _, match in team_gw1.head(5).iterrows()
            ]
        }

    def _get_team_result(self, match, team_name):
        """Get result from team's perspective"""
        if match['HomeTeam'] == team_name:
            if match['FTR'] == 'H':
                return 'Win'
            elif match['FTR'] == 'D':
                return 'Draw'
            else:
                return 'Loss'
        else:
            if match['FTR'] == 'A':
                return 'Win'
            elif match['FTR'] == 'D':
                return 'Draw'
            else:
                return 'Loss'

    def detect_new_manager_bounce(self):
        """Detect new manager impact patterns from data"""
        # This would require manager change data
        # For now, return analysis based on team performance variations
        gw1_matches = self.extract_gw1_matches()

        if len(gw1_matches) == 0:
            return {'insight': 'Insufficient data for manager analysis'}

        # Analyze teams with significantly different GW1 vs season performance
        insights = []

        # Compare GW1 home win rate vs overall home win rate
        gw1_home_rate = (gw1_matches['FTR'] == 'H').mean()
        overall_home_rate = (self.df['FTR'] == 'H').mean()

        difference = (gw1_home_rate - overall_home_rate) * 100

        if abs(difference) > 5:
            trend = "higher" if difference > 0 else "lower"
            insights.append(f"Opening weekend home advantage is {abs(difference):.1f}% {trend} than season average")

        return {
            'gw1_home_advantage': round(gw1_home_rate * 100, 1),
            'season_home_advantage': round(overall_home_rate * 100, 1),
            'difference': round(difference, 1),
            'insights': insights
        }

    def _get_fallback_analysis(self):
        """Fallback analysis if no GW1 data found"""
        return {
            'total_gw1_matches': 0,
            'goal_patterns': {
                'avg_goals_per_match': 0,
                'over_15_rate': 0,
                'over_25_rate': 0,
                'over_35_rate': 0,
                'btts_rate': 0,
                'high_scoring_games': 0
            },
            'match_outcomes': {
                'home_win_rate': 0,
                'draw_rate': 0,
                'away_win_rate': 0
            },
            'seasonal_trends': [],
            'league_comparison': [],
            'error': 'No opening weekend data could be extracted'
        }

    def generate_gw1_insights(self, league='E0'):
        """Generate actionable insights for upcoming opening weekend"""
        analysis = self.analyze_gw1_patterns()

        if analysis.get('error'):
            return ['Unable to generate insights - insufficient data']

        insights = []

        # Goal patterns
        goal_avg = analysis['goal_patterns']['avg_goals_per_match']
        over25_rate = analysis['goal_patterns']['over_25_rate']

        if goal_avg > 2.7:
            insights.append(f"🔥 Opening weekends are typically high-scoring (avg {goal_avg} goals)")
        elif goal_avg < 2.3:
            insights.append(f"🛡️ Opening weekends tend to be tight affairs (avg {goal_avg} goals)")

        if over25_rate > 60:
            insights.append(f"⚽ Over 2.5 Goals hits {over25_rate}% of the time in GW1")
        elif over25_rate < 40:
            insights.append(f"🎯 Under 2.5 Goals is strong in GW1 ({100 - over25_rate}% hit rate)")

        # BTTS patterns
        btts_rate = analysis['goal_patterns']['btts_rate']
        if btts_rate > 60:
            insights.append(f"🥅 Both Teams to Score is likely in GW1 ({btts_rate}% hit rate)")
        elif btts_rate < 40:
            insights.append(f"🚫 Clean sheets are common in GW1 (BTTS only {btts_rate}%)")

        # Home advantage
        home_rate = analysis['match_outcomes']['home_win_rate']
        if home_rate > 50:
            insights.append(f"🏠 Strong home advantage in GW1 ({home_rate}% home wins)")
        elif home_rate < 40:
            insights.append(f"✈️ Away teams perform well in GW1 ({home_rate}% home wins only)")

        return insights