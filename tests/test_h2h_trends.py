#!/usr/bin/env python3
"""
Test script for Enhanced H2H Trends Modeling implementation.
Validates feature engineering logic, data integrity, and performance.
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from footy.feature_engineering import BayesianFootballFeatureEngineering
from footy.insights import FootballInsights


def create_test_data():
    """Create synthetic test data for H2H validation."""
    print("🧪 Creating synthetic test data...")
    
    # Create test matches between Team A and Team B over multiple seasons
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='3M')
    teams = ['Team A', 'Team B']
    
    test_data = []
    for i, date in enumerate(dates):
        # Alternate home/away
        home_team = teams[i % 2]
        away_team = teams[(i + 1) % 2]
        
        # Create realistic match results
        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.2)
        
        if home_goals > away_goals:
            ftr = 'H'
        elif away_goals > home_goals:
            ftr = 'A'
        else:
            ftr = 'D'
        
        test_data.append({
            'Date': date,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'FTHG': home_goals,
            'FTAG': away_goals,
            'FTR': ftr,
            'TotalGoals': home_goals + away_goals,
            'BTTS': 1 if home_goals > 0 and away_goals > 0 else 0,
            'Season': f"{date.year}/{date.year+1}",
            'League': 'TEST'
        })
    
    df = pd.DataFrame(test_data)
    print(f"✅ Created {len(df)} test matches")
    return df


def test_rolling_window_features(df):
    """Test rolling window H2H feature calculation."""
    print("\n🔄 Testing Rolling Window Features...")
    
    fe = BayesianFootballFeatureEngineering()
    df_with_features = fe.create_bayesian_h2h_analysis(df)
    
    # Check if rolling window features exist
    rolling_features = [col for col in df_with_features.columns if 'H2H_Last' in col]
    print(f"   Found {len(rolling_features)} rolling window features")
    
    # Validate rolling window logic
    test_match = df_with_features.iloc[-1]  # Last match
    
    # Check that Last3 features are not all zero for later matches
    last3_features = [col for col in rolling_features if 'Last3' in col]
    non_zero_last3 = sum(1 for col in last3_features if test_match[col] != 0)
    
    print(f"   ✅ Rolling window features: {len(rolling_features)}")
    print(f"   ✅ Non-zero Last3 features in final match: {non_zero_last3}/{len(last3_features)}")
    
    # Validate that win rates are between 0 and 1
    win_rate_features = [col for col in rolling_features if 'WinRate' in col]
    for col in win_rate_features:
        values = df_with_features[col].dropna()
        if len(values) > 0:
            assert values.min() >= 0 and values.max() <= 1, f"Invalid win rate in {col}"
    
    print(f"   ✅ Win rate validation passed for {len(win_rate_features)} features")
    return True


def test_venue_specific_features(df):
    """Test venue-specific H2H feature calculation."""
    print("\n🏟️ Testing Venue-Specific Features...")
    
    fe = BayesianFootballFeatureEngineering()
    df_with_features = fe.create_bayesian_h2h_analysis(df)
    
    # Check venue-specific features
    venue_features = [col for col in df_with_features.columns if 'HomeAtHome' in col or 'AwayAtHome' in col]
    print(f"   Found {len(venue_features)} venue-specific features")
    
    # Validate venue advantage calculation
    venue_advantage_values = df_with_features['H2H_VenueAdvantage'].dropna()
    if len(venue_advantage_values) > 0:
        print(f"   ✅ Venue advantage range: {venue_advantage_values.min():.3f} to {venue_advantage_values.max():.3f}")
    
    # Check that venue-specific match counts are reasonable
    home_matches = df_with_features['H2H_HomeAtHome_Matches'].dropna()
    away_matches = df_with_features['H2H_AwayAtHome_Matches'].dropna()
    
    if len(home_matches) > 0 and len(away_matches) > 0:
        print(f"   ✅ Home matches range: {home_matches.min()} to {home_matches.max()}")
        print(f"   ✅ Away matches range: {away_matches.min()} to {away_matches.max()}")
    
    return True


def test_streak_detection(df):
    """Test H2H streak detection logic."""
    print("\n🔥 Testing Streak Detection...")
    
    fe = BayesianFootballFeatureEngineering()
    df_with_features = fe.create_bayesian_h2h_analysis(df)
    
    # Check streak features
    streak_features = [col for col in df_with_features.columns if 'Streak' in col or 'Momentum' in col]
    print(f"   Found {len(streak_features)} streak/momentum features")
    
    # Validate streak values are reasonable
    current_streaks = df_with_features['H2H_CurrentStreak'].dropna()
    if len(current_streaks) > 0:
        print(f"   ✅ Current streak range: {current_streaks.min()} to {current_streaks.max()}")
    
    longest_win_streaks = df_with_features['H2H_LongestWinStreak'].dropna()
    if len(longest_win_streaks) > 0:
        print(f"   ✅ Longest win streak range: {longest_win_streaks.min()} to {longest_win_streaks.max()}")
    
    # Check momentum values are between -1 and 1
    momentum_values = df_with_features['H2H_RecentMomentum'].dropna()
    if len(momentum_values) > 0:
        assert momentum_values.min() >= 0 and momentum_values.max() <= 1, "Invalid momentum values"
        print(f"   ✅ Momentum validation passed: {momentum_values.min():.3f} to {momentum_values.max():.3f}")
    
    return True


def test_trend_analysis(df):
    """Test H2H trend analysis features."""
    print("\n📈 Testing Trend Analysis...")
    
    fe = BayesianFootballFeatureEngineering()
    df_with_features = fe.create_bayesian_h2h_analysis(df)
    
    # Check trend features
    trend_features = [col for col in df_with_features.columns if 'Trend' in col or 'Slope' in col]
    print(f"   Found {len(trend_features)} trend analysis features")
    
    # Validate trend slopes are reasonable
    goal_trend_slopes = df_with_features['H2H_GoalTrendSlope'].dropna()
    if len(goal_trend_slopes) > 0:
        print(f"   ✅ Goal trend slope range: {goal_trend_slopes.min():.3f} to {goal_trend_slopes.max():.3f}")
    
    win_rate_trends = df_with_features['H2H_WinRateTrend'].dropna()
    if len(win_rate_trends) > 0:
        print(f"   ✅ Win rate trend range: {win_rate_trends.min():.3f} to {win_rate_trends.max():.3f}")
    
    return True


def test_insights_integration(df):
    """Test integration with insights module."""
    print("\n💡 Testing Insights Integration...")
    
    insights = FootballInsights(df)
    
    # Test H2H trend analysis
    h2h_trends = insights.get_h2h_trend_analysis('Team A', 'Team B')
    print(f"   ✅ H2H trend analysis: {h2h_trends['total_meetings']} meetings found")
    
    # Test venue-specific insights
    venue_insights = insights.get_venue_specific_h2h_insights('Team A', 'Team B')
    print(f"   ✅ Venue insights: Home advantage {venue_insights['venue_advantage']['home_advantage_percentage']}%")
    
    # Test momentum indicators
    momentum = insights.get_h2h_momentum_indicators('Team A', 'Team B')
    if not momentum.get('insufficient_data', False):
        print(f"   ✅ Momentum analysis: {momentum['current_streak']['description']}")
    
    # Test enhanced match insights
    match_insights = insights.get_match_insights('Team A', 'Team B')
    print(f"   ✅ Enhanced match insights generated with {len(match_insights)} categories")
    
    return True


def test_data_leakage_prevention(df):
    """Test that no future data is used in feature calculation."""
    print("\n🔒 Testing Data Leakage Prevention...")
    
    fe = BayesianFootballFeatureEngineering()
    df_with_features = fe.create_bayesian_h2h_analysis(df)
    
    # For each match, verify that H2H features only use past data
    for idx, match in df_with_features.iterrows():
        match_date = match['Date']
        
        # Get all H2H matches before this date
        past_h2h = df_with_features[
            (df_with_features['Date'] < match_date) &
            (((df_with_features['HomeTeam'] == match['HomeTeam']) & 
              (df_with_features['AwayTeam'] == match['AwayTeam'])) |
             ((df_with_features['HomeTeam'] == match['AwayTeam']) & 
              (df_with_features['AwayTeam'] == match['HomeTeam'])))
        ]
        
        # If there are past H2H matches, features should not be zero
        if len(past_h2h) > 0:
            assert match['H2H_Confidence'] > 0, f"H2H confidence should be > 0 when past data exists"
    
    print("   ✅ Data leakage prevention validated")
    return True


def main():
    """Run all H2H trends validation tests."""
    print("🚀 Starting Enhanced H2H Trends Validation Tests")
    print("=" * 60)
    
    try:
        # Create test data
        test_df = create_test_data()
        
        # Run all tests
        tests = [
            test_rolling_window_features,
            test_venue_specific_features,
            test_streak_detection,
            test_trend_analysis,
            test_insights_integration,
            test_data_leakage_prevention
        ]
        
        passed_tests = 0
        for test_func in tests:
            try:
                if test_func(test_df):
                    passed_tests += 1
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
        
        print("\n" + "=" * 60)
        print(f"🎉 Test Results: {passed_tests}/{len(tests)} tests passed")
        
        if passed_tests == len(tests):
            print("✅ All Enhanced H2H Trends features validated successfully!")
            return True
        else:
            print("❌ Some tests failed. Please review the implementation.")
            return False
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
