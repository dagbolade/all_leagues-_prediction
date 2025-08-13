# footy/insights.py - Comprehensive Football Insights Engine

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class FootballInsights:
    """Comprehensive insights engine for football predictions and analysis."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df = self.df.sort_values('Date')

        # Cache for expensive calculations
        self._cache = {}

    # ==================== GAMEWEEK 1 INSIGHTS ====================

    def gw1_goal_trends(self, leagues=['E0']) -> dict:
        """Analyze goals scored in Gameweek 1 across seasons."""
        results = {}

        for league in leagues:
            league_data = self.df[self.df['League'] == league].copy()

            # Get GW1 matches (first week of each season)
            gw1_matches = []
            for season in league_data['Season'].unique():
                season_data = league_data[league_data['Season'] == season].sort_values('Date')
                if len(season_data) > 0:
                    # First week of matches (usually first 10 matches)
                    first_week = season_data.head(10)
                    gw1_matches.append(first_week)

            if gw1_matches:
                gw1_df = pd.concat(gw1_matches)

                results[league] = {
                    'total_matches': len(gw1_df),
                    'total_goals': int(gw1_df['TotalGoals'].sum()),
                    'avg_goals_per_match': round(gw1_df['TotalGoals'].mean(), 2),
                    'over_25_rate': round((gw1_df['TotalGoals'] > 2.5).mean() * 100, 1),
                    'btts_rate': round(gw1_df['BTTS'].mean() * 100, 1),
                    'home_win_rate': round((gw1_df['FTR'] == 'H').mean() * 100, 1),
                    'by_season': gw1_df.groupby('Season').agg({
                        'TotalGoals': ['sum', 'mean'],
                        'BTTS': 'mean',
                        'FTR': lambda x: (x == 'H').mean()
                    }).round(2).to_dict()
                }

        return results

    def promoted_teams_gw1_performance(self, leagues=['E0']) -> dict:
        """Analyze how promoted teams perform in their first matches."""
        results = {}

        for league in leagues:
            league_data = self.df[self.df['League'] == league].copy()

            # Find promoted team matches in GW1
            promoted_gw1 = league_data[
                (league_data['HomePromoted'] == 1) | (league_data['AwayPromoted'] == 1)
                ].groupby('Season').head(3)  # First 3 matches for promoted teams

            if len(promoted_gw1) > 0:
                # Promoted team results
                promoted_home_results = promoted_gw1[promoted_gw1['HomePromoted'] == 1]
                promoted_away_results = promoted_gw1[promoted_gw1['AwayPromoted'] == 1]

                results[league] = {
                    'total_promoted_matches': len(promoted_gw1),
                    'home_record': {
                        'matches': len(promoted_home_results),
                        'wins': int((promoted_home_results['FTR'] == 'H').sum()),
                        'draws': int((promoted_home_results['FTR'] == 'D').sum()),
                        'losses': int((promoted_home_results['FTR'] == 'A').sum()),
                        'win_rate': round((promoted_home_results['FTR'] == 'H').mean() * 100, 1)
                    },
                    'away_record': {
                        'matches': len(promoted_away_results),
                        'wins': int((promoted_away_results['FTR'] == 'A').sum()),
                        'draws': int((promoted_away_results['FTR'] == 'D').sum()),
                        'losses': int((promoted_away_results['FTR'] == 'H').sum()),
                        'win_rate': round((promoted_away_results['FTR'] == 'A').mean() * 100, 1)
                    },
                    'avg_goals_scored': round(
                        (promoted_home_results['FTHG'].sum() + promoted_away_results['FTAG'].sum()) /
                        len(promoted_gw1), 2
                    ) if len(promoted_gw1) > 0 else 0
                }

        return results

    def big6_opening_day_trends(self, league='E0') -> dict:
        """Analyze Big 6 teams' opening day performance."""
        big6 = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham']
        league_data = self.df[self.df['League'] == league].copy()

        results = {}
        for team in big6:
            # Get first match of each season for this team
            first_matches = []
            for season in league_data['Season'].unique():
                season_data = league_data[league_data['Season'] == season]
                team_first = season_data[
                    (season_data['HomeTeam'] == team) | (season_data['AwayTeam'] == team)
                    ].sort_values('Date').head(1)

                if len(team_first) > 0:
                    first_matches.append(team_first)

            if first_matches:
                first_df = pd.concat(first_matches)

                # Calculate results for this team
                wins = 0
                draws = 0
                losses = 0
                goals_scored = 0
                goals_conceded = 0

                for _, match in first_df.iterrows():
                    if match['HomeTeam'] == team:
                        if match['FTR'] == 'H':
                            wins += 1
                        elif match['FTR'] == 'D':
                            draws += 1
                        else:
                            losses += 1
                        goals_scored += match['FTHG']
                        goals_conceded += match['FTAG']
                    else:
                        if match['FTR'] == 'A':
                            wins += 1
                        elif match['FTR'] == 'D':
                            draws += 1
                        else:
                            losses += 1
                        goals_scored += match['FTAG']
                        goals_conceded += match['FTHG']

                results[team] = {
                    'matches': len(first_df),
                    'wins': wins,
                    'draws': draws,
                    'losses': losses,
                    'win_rate': round(wins / len(first_df) * 100, 1),
                    'avg_goals_scored': round(goals_scored / len(first_df), 2),
                    'avg_goals_conceded': round(goals_conceded / len(first_df), 2)
                }

        return results

    # ==================== SEASONAL INSIGHTS ====================

    def seasonal_momentum_analysis(self, team: str, current_season: str) -> dict:
        """Analyze team's momentum across different parts of the season."""
        team_data = self.df[
            ((self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)) &
            (self.df['Season'] == current_season)
            ].copy()

        if len(team_data) == 0:
            return {}

        # Split season into quarters
        team_data['match_number'] = range(1, len(team_data) + 1)
        team_data['season_quarter'] = pd.cut(team_data['match_number'],
                                             bins=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

        results = {}
        for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
            quarter_data = team_data[team_data['season_quarter'] == quarter]
            if len(quarter_data) == 0:
                continue

            # Calculate team performance in this quarter
            points = 0
            goals_for = 0
            goals_against = 0

            for _, match in quarter_data.iterrows():
                if match['HomeTeam'] == team:
                    goals_for += match['FTHG']
                    goals_against += match['FTAG']
                    if match['FTR'] == 'H':
                        points += 3
                    elif match['FTR'] == 'D':
                        points += 1
                else:
                    goals_for += match['FTAG']
                    goals_against += match['FTHG']
                    if match['FTR'] == 'A':
                        points += 3
                    elif match['FTR'] == 'D':
                        points += 1

            results[quarter] = {
                'matches': len(quarter_data),
                'points': points,
                'ppg': round(points / len(quarter_data), 2),
                'goals_for': goals_for,
                'goals_against': goals_against,
                'goal_difference': goals_for - goals_against
            }

        return results

    def fixture_difficulty_analysis(self, team: str, upcoming_matches: list) -> dict:
        """Analyze upcoming fixture difficulty based on historical performance."""
        results = []

        for opponent in upcoming_matches:
            # Head-to-head record
            h2h = self.df[
                ((self.df['HomeTeam'] == team) & (self.df['AwayTeam'] == opponent)) |
                ((self.df['HomeTeam'] == opponent) & (self.df['AwayTeam'] == team))
                ].copy()

            if len(h2h) > 0:
                team_wins = len(h2h[
                                    ((h2h['HomeTeam'] == team) & (h2h['FTR'] == 'H')) |
                                    ((h2h['AwayTeam'] == team) & (h2h['FTR'] == 'A'))
                                    ])

                difficulty_score = 1 - (team_wins / len(h2h))  # Higher = more difficult

                results.append({
                    'opponent': opponent,
                    'h2h_matches': len(h2h),
                    'team_wins': team_wins,
                    'win_rate': round(team_wins / len(h2h) * 100, 1),
                    'difficulty_score': round(difficulty_score, 2),
                    'avg_goals_in_h2h': round(h2h['TotalGoals'].mean(), 2)
                })

        return sorted(results, key=lambda x: x['difficulty_score'], reverse=True)

    # ==================== MANAGER & TACTICAL INSIGHTS ====================

    def referee_influence_analysis(self, referee_col='Referee') -> dict:
        """Analyze referee influence on match outcomes (if referee data available)."""
        if referee_col not in self.df.columns:
            return {"error": "Referee data not available"}

        ref_stats = self.df.groupby(referee_col).agg({
            'TotalGoals': 'mean',
            'BTTS': 'mean',
            'FTR': lambda x: (x == 'H').mean(),  # Home win rate
            'Date': 'count'  # Number of matches
        }).round(3)

        ref_stats.columns = ['avg_goals', 'btts_rate', 'home_win_rate', 'matches']
        ref_stats = ref_stats[ref_stats['matches'] >= 10]  # Only refs with 10+ matches

        return {
            'high_scoring_refs': ref_stats.nlargest(5, 'avg_goals').to_dict(),
            'low_scoring_refs': ref_stats.nsmallest(5, 'avg_goals').to_dict(),
            'home_friendly_refs': ref_stats.nlargest(5, 'home_win_rate').to_dict(),
            'away_friendly_refs': ref_stats.nsmallest(5, 'home_win_rate').to_dict()
        }

    def venue_analysis(self, team: str) -> dict:
        """Analyze team's performance at different venues."""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
            ].copy()

        # Home performance
        home_matches = team_matches[team_matches['HomeTeam'] == team]
        home_stats = {
            'matches': len(home_matches),
            'win_rate': round((home_matches['FTR'] == 'H').mean() * 100, 1),
            'avg_goals_scored': round(home_matches['FTHG'].mean(), 2),
            'avg_goals_conceded': round(home_matches['FTAG'].mean(), 2),
            'clean_sheet_rate': round((home_matches['FTAG'] == 0).mean() * 100, 1)
        }

        # Away performance
        away_matches = team_matches[team_matches['AwayTeam'] == team]
        away_stats = {
            'matches': len(away_matches),
            'win_rate': round((away_matches['FTR'] == 'A').mean() * 100, 1),
            'avg_goals_scored': round(away_matches['FTAG'].mean(), 2),
            'avg_goals_conceded': round(away_matches['FTHG'].mean(), 2),
            'clean_sheet_rate': round((away_matches['FTHG'] == 0).mean() * 100, 1)
        }

        return {
            'home': home_stats,
            'away': away_stats,
            'home_advantage': round(home_stats['win_rate'] - away_stats['win_rate'], 1)
        }

    # ==================== REFEREE INSIGHTS ====================

    def referee_deep_analysis(self, referee_name: str) -> dict:
        """Deep analysis of referee tendencies using card and foul data."""
        ref_matches = self.df[self.df['Referee'] == referee_name].copy()

        if len(ref_matches) < 5:
            return {"error": f"Insufficient data for referee {referee_name}"}

        return {
            'total_matches': len(ref_matches),
            'goal_stats': {
                'avg_goals': round(ref_matches['TotalGoals'].mean(), 2),
                'over_25_rate': round((ref_matches['TotalGoals'] > 2.5).mean() * 100, 1),
                'btts_rate': round(ref_matches['BTTS'].mean() * 100, 1)
            },
            'card_tendencies': {
                'avg_yellow_cards': round((ref_matches['HY'] + ref_matches['AY']).mean(), 2),
                'avg_red_cards': round((ref_matches['HR'] + ref_matches['AR']).mean(), 2),
                'card_heavy_games': round(((ref_matches['HY'] + ref_matches['AY']) >= 5).mean() * 100, 1)
            },
            'foul_patterns': {
                'avg_fouls': round((ref_matches['HF'] + ref_matches['AF']).mean(), 2),
                'foul_heavy_games': round(((ref_matches['HF'] + ref_matches['AF']) >= 25).mean() * 100, 1)
            },
            'corner_stats': {
                'avg_corners': round((ref_matches['HC'] + ref_matches['AC']).mean(), 2),
                'corner_heavy_games': round(((ref_matches['HC'] + ref_matches['AC']) >= 12).mean() * 100, 1)
            },
            'home_bias': {
                'home_win_rate': round((ref_matches['FTR'] == 'H').mean() * 100, 1),
                'home_card_bias': round((ref_matches['AY'] - ref_matches['HY']).mean(), 2),
                'home_foul_bias': round((ref_matches['AF'] - ref_matches['HF']).mean(), 2)
            }
        }

    def team_vs_referee_analysis(self, team: str, referee: str) -> dict:
        """Analyze how a specific team performs with a specific referee."""
        team_ref_matches = self.df[
            (self.df['Referee'] == referee) &
            ((self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team))
            ].copy()

        if len(team_ref_matches) == 0:
            return {"error": f"No matches found for {team} with referee {referee}"}

        # Calculate team performance with this referee
        wins = draws = losses = 0
        goals_for = goals_against = cards = 0

        for _, match in team_ref_matches.iterrows():
            if match['HomeTeam'] == team:
                goals_for += match['FTHG']
                goals_against += match['FTAG']
                cards += match['HY'] + match['HR']
                if match['FTR'] == 'H':
                    wins += 1
                elif match['FTR'] == 'D':
                    draws += 1
                else:
                    losses += 1
            else:
                goals_for += match['FTAG']
                goals_against += match['FTHG']
                cards += match['AY'] + match['AR']
                if match['FTR'] == 'A':
                    wins += 1
                elif match['FTR'] == 'D':
                    draws += 1
                else:
                    losses += 1

        return {
            'matches': len(team_ref_matches),
            'record': f"{wins}W-{draws}D-{losses}L",
            'win_rate': round(wins / len(team_ref_matches) * 100, 1),
            'avg_goals_scored': round(goals_for / len(team_ref_matches), 2),
            'avg_goals_conceded': round(goals_against / len(team_ref_matches), 2),
            'avg_cards_per_game': round(cards / len(team_ref_matches), 2)
        }

    # ==================== SHOT EFFICIENCY INSIGHTS ====================

    def shot_efficiency_analysis(self, team: str, matches: int = 10) -> dict:
        """Analyze team's shot efficiency and xG patterns."""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
            ].sort_values('Date').tail(matches)

        home_matches = team_matches[team_matches['HomeTeam'] == team]
        away_matches = team_matches[team_matches['AwayTeam'] == team]

        # Home shooting stats
        home_stats = {
            'shots_per_game': round(home_matches['HS'].mean(), 2) if len(home_matches) > 0 else 0,
            'shots_on_target_per_game': round(home_matches['HST'].mean(), 2) if len(home_matches) > 0 else 0,
            'shot_accuracy': round((home_matches['HST'] / home_matches['HS'].replace(0, 1)).mean() * 100, 1) if len(
                home_matches) > 0 else 0,
            'conversion_rate': round((home_matches['FTHG'] / home_matches['HST'].replace(0, 1)).mean() * 100, 1) if len(
                home_matches) > 0 else 0
        }

        # Away shooting stats
        away_stats = {
            'shots_per_game': round(away_matches['AS'].mean(), 2) if len(away_matches) > 0 else 0,
            'shots_on_target_per_game': round(away_matches['AST'].mean(), 2) if len(away_matches) > 0 else 0,
            'shot_accuracy': round((away_matches['AST'] / away_matches['AS'].replace(0, 1)).mean() * 100, 1) if len(
                away_matches) > 0 else 0,
            'conversion_rate': round((away_matches['FTAG'] / away_matches['AST'].replace(0, 1)).mean() * 100, 1) if len(
                away_matches) > 0 else 0
        }

        return {
            'team': team,
            'last_matches': matches,
            'home_shooting': home_stats,
            'away_shooting': away_stats,
            'overall_xg_indicators': {
                'shot_volume': 'High' if (home_stats['shots_per_game'] + away_stats[
                    'shots_per_game']) / 2 > 12 else 'Low',
                'clinical_finishing': 'High' if (home_stats['conversion_rate'] + away_stats[
                    'conversion_rate']) / 2 > 15 else 'Low'
            }
        }

    # ==================== CORNER BETTING INSIGHTS ====================

    def corner_analysis(self, home_team: str, away_team: str) -> dict:
        """Analyze corner patterns for both teams."""
        home_team_matches = self.df[self.df['HomeTeam'] == home_team].tail(10)
        away_team_matches = self.df[self.df['AwayTeam'] == away_team].tail(10)

        h2h_matches = self.df[
            ((self.df['HomeTeam'] == home_team) & (self.df['AwayTeam'] == away_team)) |
            ((self.df['HomeTeam'] == away_team) & (self.df['AwayTeam'] == home_team))
            ]

        return {
            'home_team_corners': {
                'avg_corners_won_at_home': round(home_team_matches['HC'].mean(), 2),
                'avg_corners_conceded_at_home': round(home_team_matches['AC'].mean(), 2),
                'total_corners_per_home_game': round((home_team_matches['HC'] + home_team_matches['AC']).mean(), 2)
            },
            'away_team_corners': {
                'avg_corners_won_away': round(away_team_matches['AC'].mean(), 2),
                'avg_corners_conceded_away': round(away_team_matches['HC'].mean(), 2),
                'total_corners_per_away_game': round((away_team_matches['HC'] + away_team_matches['AC']).mean(), 2)
            },
            'h2h_corner_stats': {
                'total_h2h_matches': len(h2h_matches),
                'avg_total_corners_h2h': round((h2h_matches['HC'] + h2h_matches['AC']).mean(), 2) if len(
                    h2h_matches) > 0 else 0,
                'over_10_corners_rate': round(((h2h_matches['HC'] + h2h_matches['AC']) > 10).mean() * 100, 1) if len(
                    h2h_matches) > 0 else 0
            },
            'prediction': {
                'expected_total_corners': round(
                    (home_team_matches['HC'].mean() + home_team_matches['AC'].mean() +
                     away_team_matches['HC'].mean() + away_team_matches['AC'].mean()) / 2, 1
                ),
                'corner_market_suggestion': 'Over 9.5' if round(
                    (home_team_matches['HC'].mean() + home_team_matches['AC'].mean() +
                     away_team_matches['HC'].mean() + away_team_matches['AC'].mean()) / 2, 1
                ) > 9.5 else 'Under 9.5'
            }
        }

    # ==================== TIME-BASED INSIGHTS ====================

    def kickoff_time_analysis(self, league: str = 'E0') -> dict:
        """Analyze how kickoff times affect match outcomes."""
        league_data = self.df[self.df['League'] == league].copy()

        # Convert Excel time to hours
        league_data['KickoffHour'] = (league_data['Time'] * 24).round().astype(int)

        time_stats = league_data.groupby('KickoffHour').agg({
            'TotalGoals': 'mean',
            'BTTS': 'mean',
            'FTR': lambda x: (x == 'H').mean(),
            'Date': 'count'
        }).round(3)

        time_stats.columns = ['avg_goals', 'btts_rate', 'home_win_rate', 'matches']
        time_stats = time_stats[time_stats['matches'] >= 10]

        return {
            'by_kickoff_time': time_stats.to_dict(),
            'insights': {
                'highest_scoring_time': time_stats['avg_goals'].idxmax() if len(time_stats) > 0 else None,
                'lowest_scoring_time': time_stats['avg_goals'].idxmin() if len(time_stats) > 0 else None,
                'most_home_friendly_time': time_stats['home_win_rate'].idxmax() if len(time_stats) > 0 else None
            }
        }

    # ==================== BETTING ODDS ANALYSIS ====================

    def odds_value_analysis(self, home_team: str, away_team: str) -> dict:
        """Analyze historical odds patterns for teams."""
        # Get recent matches for both teams
        home_recent = self.df[self.df['HomeTeam'] == home_team].tail(5)
        away_recent = self.df[self.df['AwayTeam'] == away_team].tail(5)

        # Calculate average closing odds
        home_odds_analysis = {
            'avg_home_odds_when_home': round(home_recent['B365H'].mean(), 2),
            'avg_over25_odds_at_home': round(home_recent['B365>2.5'].mean(), 2),
            'home_win_roi': self._calculate_simple_roi(home_recent, 'H', 'B365H')
        }

        away_odds_analysis = {
            'avg_away_odds_when_away': round(away_recent['B365A'].mean(), 2),
            'avg_over25_odds_away': round(away_recent['B365>2.5'].mean(), 2),
            'away_win_roi': self._calculate_simple_roi(away_recent, 'A', 'B365A')
        }

        return {
            'home_team_odds_patterns': home_odds_analysis,
            'away_team_odds_patterns': away_odds_analysis,
            'market_insights': {
                'typically_high_odds_team': home_team if home_odds_analysis['avg_home_odds_when_home'] >
                                                         away_odds_analysis['avg_away_odds_when_away'] else away_team,
                'goals_market_tendency': 'Over 2.5 friendly' if (home_odds_analysis['avg_over25_odds_at_home'] +
                                                                 away_odds_analysis[
                                                                     'avg_over25_odds_away']) / 2 < 1.8 else 'Under 2.5 friendly'
            }
        }

    def _calculate_simple_roi(self, matches, target_result, odds_col):
        """Calculate simple ROI for a betting strategy."""
        if len(matches) == 0:
            return 0

        total_stake = len(matches)
        total_return = 0

        for _, match in matches.iterrows():
            if match['FTR'] == target_result:
                total_return += match[odds_col]

        roi = ((total_return - total_stake) / total_stake) * 100
        return round(roi, 1)

    # ==================== BETTING INSIGHTS ====================

    def value_bet_indicators(self, match_predictions: dict, bookmaker_odds: dict = None) -> dict:
        """Identify potential value bets based on model vs market odds."""
        if not bookmaker_odds:
            return {"message": "Bookmaker odds needed for value analysis"}

        value_bets = []

        for market, prediction in match_predictions.items():
            if market in bookmaker_odds:
                model_prob = prediction.get('probability', 0)
                market_prob = 1 / bookmaker_odds[market]  # Convert odds to probability

                if model_prob > market_prob * 1.1:  # 10% edge threshold
                    value_bets.append({
                        'market': market,
                        'model_probability': round(model_prob * 100, 1),
                        'market_probability': round(market_prob * 100, 1),
                        'edge': round((model_prob - market_prob) * 100, 1),
                        'recommended_stake': 'High' if model_prob > market_prob * 1.2 else 'Medium'
                    })

        return sorted(value_bets, key=lambda x: x['edge'], reverse=True)

    def streaks_and_patterns(self, team: str, pattern_type: str = 'all') -> dict:
        """Identify current streaks and patterns for a team."""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
            ].sort_values('Date').copy()

        # Calculate team results
        results = []
        for _, match in team_matches.iterrows():
            if match['HomeTeam'] == team:
                if match['FTR'] == 'H':
                    results.append('W')
                elif match['FTR'] == 'D':
                    results.append('D')
                else:
                    results.append('L')
            else:
                if match['FTR'] == 'A':
                    results.append('W')
                elif match['FTR'] == 'D':
                    results.append('D')
                else:
                    results.append('L')

        # Find current streaks
        current_streak = 1
        if len(results) > 1:
            last_result = results[-1]
            for i in range(len(results) - 2, -1, -1):
                if results[i] == last_result:
                    current_streak += 1
                else:
                    break

        return {
            'current_streak': f"{current_streak} {results[-1] if results else 'N/A'}",
            'last_5_form': ''.join(results[-5:]) if len(results) >= 5 else ''.join(results),
            'wins_in_last_10': results[-10:].count('W') if len(results) >= 10 else results.count('W'),
            'losses_in_last_10': results[-10:].count('L') if len(results) >= 10 else results.count('L')
        }

    # ==================== VISUALIZATION HELPERS ====================

    def create_team_form_chart(self, team: str, matches: int = 10):
        """Create interactive form chart for a team."""
        team_matches = self.df[
            (self.df['HomeTeam'] == team) | (self.df['AwayTeam'] == team)
            ].sort_values('Date').tail(matches)

        results = []
        dates = []
        opponents = []

        for _, match in team_matches.iterrows():
            dates.append(match['Date'])
            if match['HomeTeam'] == team:
                opponents.append(f"vs {match['AwayTeam']} (H)")
                if match['FTR'] == 'H':
                    results.append(3)
                elif match['FTR'] == 'D':
                    results.append(1)
                else:
                    results.append(0)
            else:
                opponents.append(f"@ {match['HomeTeam']} (A)")
                if match['FTR'] == 'A':
                    results.append(3)
                elif match['FTR'] == 'D':
                    results.append(1)
                else:
                    results.append(0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=results,
            mode='lines+markers',
            name=f'{team} Form',
            line=dict(width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{text}</b><br>Points: %{y}<br>Date: %{x}<extra></extra>',
            text=opponents
        ))

        fig.update_layout(
            title=f'{team} - Last {matches} Matches',
            xaxis_title='Date',
            yaxis_title='Points',
            yaxis=dict(tickvals=[0, 1, 3], ticktext=['Loss', 'Draw', 'Win']),
            height=400
        )

        return fig

    def comprehensive_match_preview(self, home_team: str, away_team: str, referee: str = None) -> dict:
        """Generate comprehensive match preview with all available insights."""
        preview = {
            'teams': {'home': home_team, 'away': away_team},
            'basic_insights': self.get_match_insights(home_team, away_team),
            'shooting_analysis': {
                'home': self.shot_efficiency_analysis(home_team),
                'away': self.shot_efficiency_analysis(away_team)
            },
            'corner_analysis': self.corner_analysis(home_team, away_team),
            'odds_patterns': self.odds_value_analysis(home_team, away_team)
        }

        # Add referee analysis if referee is known
        if referee:
            preview['referee_analysis'] = {
                'referee_tendencies': self.referee_deep_analysis(referee),
                'home_team_vs_ref': self.team_vs_referee_analysis(home_team, referee),
                'away_team_vs_ref': self.team_vs_referee_analysis(away_team, referee)
            }

        # Generate key insights summary
        preview['key_insights'] = self._generate_key_insights_summary(preview)

        return preview

    def _generate_key_insights_summary(self, preview_data: dict) -> list:
        """Generate bullet-point key insights from comprehensive analysis."""
        insights = []

        # Shot efficiency insights
        home_shot = preview_data['shooting_analysis']['home']['overall_xg_indicators']
        away_shot = preview_data['shooting_analysis']['away']['overall_xg_indicators']

        if home_shot['shot_volume'] == 'High' and home_shot['clinical_finishing'] == 'High':
            insights.append(
                f"ðŸŽ¯ {preview_data['teams']['home']} showing high shot volume AND clinical finishing recently")

        if away_shot['shot_volume'] == 'High' and away_shot['clinical_finishing'] == 'High':
            insights.append(
                f"ðŸŽ¯ {preview_data['teams']['away']} showing high shot volume AND clinical finishing recently")

        # Corner insights
        corner_pred = preview_data['corner_analysis']['prediction']
        insights.append(
            f"âš½ Expected corners: {corner_pred['expected_total_corners']} - Market suggestion: {corner_pred['corner_market_suggestion']}")

        # H2H insights
        h2h_corners = preview_data['corner_analysis']['h2h_corner_stats']
        if h2h_corners['over_10_corners_rate'] > 60:
            insights.append(f"ðŸ“Š H2H: {h2h_corners['over_10_corners_rate']}% of their meetings go Over 10.5 corners")

        # Odds patterns
        odds_insight = preview_data['odds_patterns']['market_insights']
        insights.append(f"ðŸ’° Goals market: {odds_insight['goals_market_tendency']}")

        return insights

    def gw1_comprehensive_insights(self, league: str = 'E0') -> dict:
        """Ultra-comprehensive GW1 insights using all available data."""
        league_data = self.df[self.df['League'] == league].copy()

        # Get first 10 matches of each season (GW1)
        gw1_matches = []
        for season in league_data['Season'].unique():
            season_data = league_data[league_data['Season'] == season].sort_values('Date')
            if len(season_data) > 0:
                gw1_matches.append(season_data.head(10))

        if not gw1_matches:
            return {"error": "No GW1 data found"}

        gw1_df = pd.concat(gw1_matches)

        return {
            'basic_stats': {
                'total_gw1_matches': len(gw1_df),
                'avg_goals_per_match': round(gw1_df['TotalGoals'].mean(), 2),
                'over_25_rate': round((gw1_df['TotalGoals'] > 2.5).mean() * 100, 1),
                'btts_rate': round(gw1_df['BTTS'].mean() * 100, 1),
                'home_win_rate': round((gw1_df['FTR'] == 'H').mean() * 100, 1)
            },
            'shooting_patterns': {
                'avg_shots_per_match': round((gw1_df['HS'] + gw1_df['AS']).mean(), 2),
                'avg_shots_on_target': round((gw1_df['HST'] + gw1_df['AST']).mean(), 2),
                'shot_accuracy': round(((gw1_df['HST'] + gw1_df['AST']) / (gw1_df['HS'] + gw1_df['AS'])).mean() * 100,
                                       1)
            },
            'disciplinary_patterns': {
                'avg_yellow_cards': round((gw1_df['HY'] + gw1_df['AY']).mean(), 2),
                'avg_red_cards': round((gw1_df['HR'] + gw1_df['AR']).mean(), 2),
                'card_heavy_matches_rate': round(((gw1_df['HY'] + gw1_df['AY']) >= 5).mean() * 100, 1)
            },
            'corner_patterns': {
                'avg_corners_per_match': round((gw1_df['HC'] + gw1_df['AC']).mean(), 2),
                'over_10_corners_rate': round(((gw1_df['HC'] + gw1_df['AC']) > 10).mean() * 100, 1),
                'corner_heavy_matches': round(((gw1_df['HC'] + gw1_df['AC']) >= 12).mean() * 100, 1)
            },
            'time_analysis': {
                'kickoff_time_distribution': gw1_df.groupby((gw1_df['Time'] * 24).round())['Date'].count().to_dict(),
                'weekend_vs_weekday': self._analyze_weekend_patterns(gw1_df)
            },
            'referee_gw1_tendencies': self._analyze_gw1_referees(gw1_df),
            'betting_market_analysis': {
                'avg_home_odds': round(gw1_df['B365H'].mean(), 2),
                'avg_draw_odds': round(gw1_df['B365D'].mean(), 2),
                'avg_away_odds': round(gw1_df['B365A'].mean(), 2),
                'avg_over25_odds': round(gw1_df['B365>2.5'].mean(), 2),
                'market_efficiency': self._calculate_market_efficiency(gw1_df)
            }
        }

    def _analyze_weekend_patterns(self, df):
        """Analyze weekend vs weekday patterns."""
        df['DayOfWeek'] = pd.to_datetime(df['Date']).dt.dayofweek
        df['IsWeekend'] = df['DayOfWeek'].isin([5, 6])  # Saturday, Sunday

        weekend_stats = df[df['IsWeekend']].agg({
            'TotalGoals': 'mean',
            'BTTS': 'mean',
            'FTR': lambda x: (x == 'H').mean()
        })

        weekday_stats = df[~df['IsWeekend']].agg({
            'TotalGoals': 'mean',
            'BTTS': 'mean',
            'FTR': lambda x: (x == 'H').mean()
        })

        return {
            'weekend': {
                'avg_goals': round(weekend_stats['TotalGoals'], 2),
                'btts_rate': round(weekend_stats['BTTS'] * 100, 1),
                'home_win_rate': round(weekend_stats['FTR'] * 100, 1)
            },
            'weekday': {
                'avg_goals': round(weekday_stats['TotalGoals'], 2),
                'btts_rate': round(weekday_stats['BTTS'] * 100, 1),
                'home_win_rate': round(weekday_stats['FTR'] * 100, 1)
            }
        }

    def _analyze_gw1_referees(self, gw1_df):
        """Analyze referee patterns in GW1."""
        ref_stats = gw1_df.groupby('Referee').agg({
            'TotalGoals': 'mean',
            'HY': 'mean',
            'AY': 'mean',
            'Date': 'count'
        }).round(2)

        ref_stats.columns = ['avg_goals', 'avg_home_yellows', 'avg_away_yellows', 'matches']
        ref_stats = ref_stats[ref_stats['matches'] >= 2]

        return {
            'most_common_gw1_refs': ref_stats.nlargest(5, 'matches').to_dict(),
            'highest_scoring_gw1_refs': ref_stats.nlargest(3, 'avg_goals').to_dict() if len(ref_stats) > 0 else {},
            'card_happy_gw1_refs': ref_stats.nlargest(3, 'avg_home_yellows').to_dict() if len(ref_stats) > 0 else {}
        }

    def _calculate_market_efficiency(self, df):
        """Calculate how efficient betting markets were in GW1."""
        # Simple efficiency check: did favorites (lowest odds) win more often?
        df['Favorite'] = df[['B365H', 'B365D', 'B365A']].idxmin(axis=1)
        df['FavoriteWon'] = (
                ((df['Favorite'] == 'B365H') & (df['FTR'] == 'H')) |
                ((df['Favorite'] == 'B365D') & (df['FTR'] == 'D')) |
                ((df['Favorite'] == 'B365A') & (df['FTR'] == 'A'))
        )

        return {
            'favorite_win_rate': round(df['FavoriteWon'].mean() * 100, 1),
            'market_predictiveness': 'High' if df['FavoriteWon'].mean() > 0.6 else 'Medium' if df[
                                                                                                   'FavoriteWon'].mean() > 0.4 else 'Low'
        }
        """Get comprehensive insights for a specific match."""
        return {
            'head_to_head': self.fixture_difficulty_analysis(home_team, [away_team]),
            'home_team_form': self.streaks_and_patterns(home_team),
            'away_team_form': self.streaks_and_patterns(away_team),
            'home_venue_advantage': self.venue_analysis(home_team),
            'away_venue_record': self.venue_analysis(away_team)
        }

    def get_league_insights(self, league: str = 'E0') -> dict:
        """Get comprehensive league insights."""
        return {
            'gw1_trends': self.gw1_goal_trends([league]),
            'promoted_teams': self.promoted_teams_gw1_performance([league]),
            'big6_trends': self.big6_opening_day_trends(league),
            'referee_analysis': self.referee_influence_analysis()
        }