import plotly.express as px

def visualize_draws_per_league(df):
    """
    Interactive visualization of draws per league and season.
    """
    draw_counts = df[df['FTR'] == 'D'].groupby(['League', 'Season']).size().reset_index(name='Draws')

    fig = px.bar(draw_counts, x='League', y='Draws', color='Season', barmode='group',
                 title='Frequency of Draws in Each League per Season')
    fig.update_layout(xaxis_title='League', yaxis_title='Number of Draws')
    fig.show()


def visualize_over_goals(df, goal_threshold):
    """
    Interactive visualization of games with goals over a threshold (e.g., 1.5, 2.5).
    """
    df['TotalGoals'] = df['FTHG'] + df['FTAG']
    goal_label = f'Over_{goal_threshold}_Games'
    over_goal_count = df[df['TotalGoals'] > goal_threshold].groupby(['League', 'Season']).size().reset_index(name=goal_label)

    fig = px.bar(over_goal_count, x='League', y=goal_label, color='Season', barmode='group',
                 title=f'Frequency of Games with Over {goal_threshold} Goals per League and Season')
    fig.update_layout(xaxis_title='League', yaxis_title=f'Number of Games (Over {goal_threshold} Goals)')
    fig.show()


def visualize_fouls_per_league(df):
    """
    Interactive visualization of fouls per league and season.
    """
    df['TotalFouls'] = df['HF'] + df['AF']
    fouls_count = df.groupby(['League', 'Season'])['TotalFouls'].sum().reset_index()

    fig = px.bar(fouls_count, x='League', y='TotalFouls', color='Season', barmode='group',
                 title='Total Fouls in Each League per Season')
    fig.update_layout(xaxis_title='League', yaxis_title='Total Fouls')
    fig.show()
