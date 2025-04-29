# footy/epl_analyzer.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def analyze_epl_current_season(df):
    """
    Analyze current season EPL (E0) statistics
    """
    # Filter for EPL current season
    epl_df = df[(df['League'] == 'E0') & (df['Season'] == '2024-2025')].copy()

    # Calculate match statistics
    epl_df['TotalGoals'] = epl_df['FTHG'] + epl_df['FTAG']
    epl_df['TotalFouls'] = epl_df['HF'] + epl_df['AF']
    epl_df['BTTS'] = ((epl_df['FTHG'] > 0) & (epl_df['FTAG'] > 0)).astype(int)
    epl_df['Over1.5'] = (epl_df['TotalGoals'] > 1.5).astype(int)
    epl_df['Over2.5'] = (epl_df['TotalGoals'] > 2.5).astype(int)

    # Create team statistics
    team_stats = []
    for team in epl_df['HomeTeam'].unique():
        home_games = epl_df[epl_df['HomeTeam'] == team]
        away_games = epl_df[epl_df['AwayTeam'] == team]

        stats = {
            'Team': team,
            'Games': len(home_games) + len(away_games),
            'Draws': len(home_games[home_games['FTR'] == 'D']) + len(away_games[away_games['FTR'] == 'D']),
            'TotalFouls': home_games['TotalFouls'].sum() + away_games['TotalFouls'].sum(),
            'AvgFouls': (home_games['TotalFouls'].sum() + away_games['TotalFouls'].sum()) / (
                        len(home_games) + len(away_games)),
            'GoalsScored': home_games['FTHG'].sum() + away_games['FTAG'].sum(),
            'GoalsConceded': home_games['FTAG'].sum() + away_games['FTHG'].sum(),
            'Over1.5_Games': len(home_games[home_games['Over1.5'] == 1]) + len(away_games[away_games['Over1.5'] == 1]),
            'Over2.5_Games': len(home_games[home_games['Over2.5'] == 1]) + len(away_games[away_games['Over2.5'] == 1]),
            'BTTS_Games': len(home_games[home_games['BTTS'] == 1]) + len(away_games[away_games['BTTS'] == 1])
        }
        team_stats.append(stats)

    return pd.DataFrame(team_stats)


def create_epl_visualizations(team_stats):
    """
    Create comprehensive EPL visualizations
    """
    # Create subplot figure
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Draws by Team',
                        'Average Fouls per Game',
                        'Goals Scored vs Conceded',
                        'Over 1.5 & 2.5 Goals Games',
                        'BTTS (Both Teams to Score) Games',
                        'Total Goals Contribution'))

    # 1. Draws by Team
    fig.add_trace(
        go.Bar(
            name='Draws',
            x=team_stats['Team'],
            y=team_stats['Draws'],
            text=team_stats['Draws'],
            textposition='auto',
        ),
        row=1, col=1
    )

    # 2. Average Fouls
    fig.add_trace(
        go.Bar(
            name='Avg Fouls',
            x=team_stats['Team'],
            y=team_stats['AvgFouls'],
            text=team_stats['AvgFouls'].round(1),
            textposition='auto',
        ),
        row=1, col=2
    )

    # 3. Goals Scored vs Conceded
    fig.add_trace(
        go.Bar(
            name='Goals Scored',
            x=team_stats['Team'],
            y=team_stats['GoalsScored'],
            text=team_stats['GoalsScored'],
            textposition='auto',
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Bar(
            name='Goals Conceded',
            x=team_stats['Team'],
            y=team_stats['GoalsConceded'],
            text=team_stats['GoalsConceded'],
            textposition='auto',
        ),
        row=2, col=1
    )

    # 4. Over 1.5 & 2.5 Goals
    fig.add_trace(
        go.Bar(
            name='Over 1.5',
            x=team_stats['Team'],
            y=team_stats['Over1.5_Games'],
            text=team_stats['Over1.5_Games'],
            textposition='auto',
        ),
        row=2, col=2
    )

    fig.add_trace(
        go.Bar(
            name='Over 2.5',
            x=team_stats['Team'],
            y=team_stats['Over2.5_Games'],
            text=team_stats['Over2.5_Games'],
            textposition='auto',
        ),
        row=2, col=2
    )

    # 5. BTTS Games
    fig.add_trace(
        go.Bar(
            name='BTTS Games',
            x=team_stats['Team'],
            y=team_stats['BTTS_Games'],
            text=team_stats['BTTS_Games'],
            textposition='auto',
        ),
        row=3, col=1
    )

    # 6. Total Goals Contribution
    total_goals = go.Bar(
        name='Total Goals',
        x=team_stats['Team'],
        y=team_stats['GoalsScored'] + team_stats['GoalsConceded'],
        text=team_stats['GoalsScored'] + team_stats['GoalsConceded'],
        textposition='auto',
    )
    fig.add_trace(total_goals, row=3, col=2)

    # Update layout
    fig.update_layout(
        height=1500,
        width=1200,
        showlegend=True,
        title_text="EPL 2023-2024 Season Analysis",
        barmode='group'
    )

    # Update axes
    for i in fig['layout']['annotations']:
        i['font'] = dict(size=12, color='black')

    # Update all xaxes
    fig.update_xaxes(tickangle=45)

    return fig


def calculate_percentages(team_stats):
    """
    Calculate percentages for various metrics
    """
    percentage_stats = team_stats.copy()
    percentage_stats['Draw_Percentage'] = (team_stats['Draws'] / team_stats['Games'] * 100).round(1)
    percentage_stats['Over1.5_Percentage'] = (team_stats['Over1.5_Games'] / team_stats['Games'] * 100).round(1)
    percentage_stats['Over2.5_Percentage'] = (team_stats['Over2.5_Games'] / team_stats['Games'] * 100).round(1)
    percentage_stats['BTTS_Percentage'] = (team_stats['BTTS_Games'] / team_stats['Games'] * 100).round(1)

    return percentage_stats


def run_epl_analysis(merged_df):
    """
    Run complete EPL analysis
    """
    team_stats = analyze_epl_current_season(merged_df)
    percentage_stats = calculate_percentages(team_stats)

    # Create visualization
    fig = create_epl_visualizations(team_stats)

    return team_stats, percentage_stats, fig