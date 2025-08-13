# footy/weekly_insights_analyzer.py - DYNAMIC WEEKLY INSIGHTS

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging


class WeeklyInsightsAnalyzer:
    """Dynamic weekly insights that evolve throughout the season"""

    def __init__(self, df):
        self.df = df.copy()
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df = self.df.sort_values('Date')

        # Calculate additional columns if not present
        if 'TotalGoals' not in self.df.columns:
            self.df['TotalGoals'] = self.df['FTHG'] + self.df['FTAG']
        if 'BTTS' not in self.df.columns:
            self.df['BTTS'] = ((self.df['FTHG'] > 0) & (self.df['FTAG'] > 0)).astype(int)

        print(f"🔍 Weekly insights analyzer initialized with {len(self.df)} matches")

    def detect_current_gameweek(self, league='E0', season='2024/25'):
        """Detect current gameweek based on season progress"""
        # In real implementation, this would check current date vs season start
        # For now, return configurable gameweek
        return self._get_simulated_gameweek()

    def _get_simulated_gameweek(self):
        """Simulate current gameweek - FIXED for pre-season"""
        current_date = datetime.now()

        # For 2024/25 season starting August 16, 2024
        season_start = datetime(2024, 8, 16)

        # If we're before season start, return GW1 (pre-season)
        if current_date < season_start:
            return 1  # Show GW1 insights even before season starts

        # Calculate weeks since season start
        weeks_elapsed = (current_date - season_start).days // 7

        # Each gameweek is roughly 1 week apart
        gameweek = min(weeks_elapsed + 1, 38)  # Max 38 gameweeks

        # For now (pre-season), force return GW1
        return 1  # HARDCODE GW1 until season actually starts

    def get_weekly_insights(self, home_team, away_team, league='E0'):
        """Get insights based on current gameweek"""
        current_gw = self.detect_current_gameweek(league)

        print(f"🗓️ Generating insights for Gameweek {current_gw}")

        if current_gw <= 1:
            return self._get_gw1_insights(home_team, away_team)
        elif current_gw <= 3:
            return self._get_early_season_insights(home_team, away_team, current_gw)
        elif current_gw <= 10:
            return self._get_settling_period_insights(home_team, away_team, current_gw)
        elif current_gw <= 20:
            return self._get_mid_season_insights(home_team, away_team, current_gw)
        elif current_gw <= 30:
            return self._get_business_end_insights(home_team, away_team, current_gw)
        else:
            return self._get_final_stretch_insights(home_team, away_team, current_gw)

    def _get_gw1_insights(self, home_team, away_team):
        """Gameweek 1 specific insights"""
        insights = [
            "🆕 Opening weekend - teams may lack match sharpness",
            "🔄 New signings may not be fully integrated yet",
            "🏠 Home advantage could be stronger with excited fans back"
        ]

        # Add team-specific GW1 history from historical data
        home_gw1_record = self._get_team_gw1_record(home_team)
        away_gw1_record = self._get_team_gw1_record(away_team)

        if home_gw1_record:
            insights.append(f"📊 {home_team} GW1 history: {home_gw1_record}")
        if away_gw1_record:
            insights.append(f"📊 {away_team} GW1 history: {away_gw1_record}")

        return {
            'gameweek': 1,
            'phase': 'Opening Weekend',
            'key_themes': ['Match fitness', 'New signings integration', 'Season expectations'],
            'insights': insights
        }

    def _get_early_season_insights(self, home_team, away_team, gw):
        """Gameweeks 2-3 insights"""
        insights = [
            f"📈 Early season form still developing (GW{gw})",
            "⚡ Teams finding their rhythm after opening weekend",
            "🔄 Tactical adjustments from managers after GW1 lessons"
        ]

        # Analyze if teams had surprising GW1 results
        if gw == 2:
            insights.append("🎯 Reactions to opening weekend results - expect corrections")
        elif gw == 3:
            insights.append("📊 First patterns emerging - but still early to judge")

        return {
            'gameweek': gw,
            'phase': 'Early Season',
            'key_themes': ['Form development', 'Tactical adjustments', 'Early patterns'],
            'insights': insights
        }

    def _get_settling_period_insights(self, home_team, away_team, gw):
        """Gameweeks 4-10 insights"""
        insights = [
            f"🏃‍♂️ Teams hitting their stride (GW{gw})",
            "📊 Meaningful form patterns now emerging",
            "🔄 Squad rotation starting as fixture congestion begins"
        ]

        if gw <= 6:
            insights.append("🆕 New signings finding their feet in new systems")
        if gw >= 8:
            insights.append("🏆 First international break effects on form")

        return {
            'gameweek': gw,
            'phase': 'Settling Period',
            'key_themes': ['Established patterns', 'Squad rotation', 'International breaks'],
            'insights': insights
        }

    def _get_mid_season_insights(self, home_team, away_team, gw):
        """Gameweeks 11-20 insights"""
        insights = [
            f"⚖️ Mid-season form showing true team strength (GW{gw})",
            "🎯 Tactical systems fully implemented",
            "🔄 Squad depth being tested with fixture congestion"
        ]

        if gw >= 15:
            insights.append("🎄 Festive period approaching - fitness will be key")
        if gw >= 18:
            insights.append("❄️ Festive fixture pile-up - rotation and squad depth crucial")

        return {
            'gameweek': gw,
            'phase': 'Mid Season',
            'key_themes': ['True form', 'Tactical maturity', 'Squad depth tested'],
            'insights': insights
        }

    def _get_business_end_insights(self, home_team, away_team, gw):
        """Gameweeks 21-30 insights"""
        insights = [
            f"🎯 Business end approaching (GW{gw})",
            "🔥 Pressure mounting for results",
            "💰 January transfer window effects may be showing"
        ]

        if gw >= 25:
            insights.append("🏃‍♂️ Title race/relegation battle intensifying")
        if gw >= 28:
            insights.append("📈 Every point crucial - expect tight, tactical games")

        return {
            'gameweek': gw,
            'phase': 'Business End',
            'key_themes': ['Pressure mounting', 'January signings', 'Title/relegation races'],
            'insights': insights
        }

    def _get_final_stretch_insights(self, home_team, away_team, gw):
        """Gameweeks 31-38 insights"""
        insights = [
            f"🏁 Final stretch - every point matters (GW{gw})",
            "💪 Mental strength as important as tactical setup",
            "🎯 Teams with nothing to play for may be unpredictable"
        ]

        if gw >= 35:
            insights.append("🔥 Season climax - expect high-intensity matches")
        if gw >= 37:
            insights.append("🏆 Final day drama possible - motivations key")

        return {
            'gameweek': gw,
            'phase': 'Final Stretch',
            'key_themes': ['Maximum pressure', 'Mental strength', 'Season objectives'],
            'insights': insights
        }

    def _get_team_gw1_record(self, team_name):
        """Get team's historical GW1 record"""
        try:
            # Extract GW1 matches for this team
            gw1_matches = self._extract_gw1_matches_for_team(team_name)

            if len(gw1_matches) >= 3:  # Need at least 3 seasons of data
                wins = draws = losses = 0

                for _, match in gw1_matches.iterrows():
                    if match['HomeTeam'] == team_name:
                        if match['FTR'] == 'H':
                            wins += 1
                        elif match['FTR'] == 'D':
                            draws += 1
                        else:
                            losses += 1
                    else:
                        if match['FTR'] == 'A':
                            wins += 1
                        elif match['FTR'] == 'D':
                            draws += 1
                        else:
                            losses += 1

                win_rate = round(wins / len(gw1_matches) * 100, 1)
                return f"{wins}W-{draws}D-{losses}L ({win_rate}% win rate)"

        except Exception as e:
            print(f"Error getting GW1 record for {team_name}: {e}")

        return None

    def _extract_gw1_matches_for_team(self, team_name):
        """Extract GW1 matches for specific team"""
        gw1_matches = []

        # Group by season
        for season in self.df['Season'].unique():
            season_data = self.df[
                (self.df['Season'] == season) &
                ((self.df['HomeTeam'] == team_name) | (self.df['AwayTeam'] == team_name))
                ].sort_values('Date')

            if len(season_data) > 0:
                # First match of season for this team
                first_match = season_data.head(1)
                gw1_matches.append(first_match)

        if gw1_matches:
            return pd.concat(gw1_matches, ignore_index=True)
        else:
            return pd.DataFrame()

    def get_season_phase_analysis(self):
        """Get overall season phase analysis"""
        current_gw = self.detect_current_gameweek()

        phase_info = {
            'current_gameweek': current_gw,
            'season_progress': round((current_gw / 38) * 100, 1),
            'matches_played': current_gw - 1,
            'matches_remaining': 38 - current_gw + 1
        }

        if current_gw <= 1:
            phase_info.update({
                'phase': 'Opening Weekend',
                'description': 'Season kicks off - expect rusty performances and surprises',
                'key_factors': ['Match fitness', 'New signings', 'Manager tactics']
            })
        elif current_gw <= 10:
            phase_info.update({
                'phase': 'Early Season',
                'description': 'Teams finding their rhythm and establishing patterns',
                'key_factors': ['Form development', 'Tactical adjustments', 'Squad settling']
            })
        elif current_gw <= 20:
            phase_info.update({
                'phase': 'Mid Season',
                'description': 'True team strength emerging with established patterns',
                'key_factors': ['Consistent form', 'Squad rotation', 'Fixture congestion']
            })
        elif current_gw <= 30:
            phase_info.update({
                'phase': 'Business End',
                'description': 'Pressure mounting as season objectives become clear',
                'key_factors': ['Mental strength', 'Squad depth', 'Injury management']
            })
        else:
            phase_info.update({
                'phase': 'Final Stretch',
                'description': 'Every point crucial as season reaches climax',
                'key_factors': ['Maximum pressure', 'Motivation levels', 'Season objectives']
            })

        return phase_info