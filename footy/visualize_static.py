import matplotlib.pyplot as plt

def visualize_average_goals(df):
    """
    Visualize average home and away goals by season.
    """
    home_goals_avg = df.groupby('Season')['FTHG'].mean()
    away_goals_avg = df.groupby('Season')['FTAG'].mean()

    plt.figure(figsize=(10, 6))
    plt.bar(home_goals_avg.index, home_goals_avg, label='Home Goals', color='blue', alpha=0.6)
    plt.bar(away_goals_avg.index, away_goals_avg, label='Away Goals', color='red', alpha=0.6)
    plt.title('Average Goals per Game by Season (Home vs Away)')
    plt.ylabel('Average Goals')
    plt.xlabel('Season')
    plt.legend()
    plt.show()


def visualize_total_goals(df):
    """
    Visualize total goals scored by home and away teams.
    """
    home_goals_total = df['FTHG'].sum()
    away_goals_total = df['FTAG'].sum()

    plt.figure(figsize=(10, 6))
    plt.bar(['Home Goals', 'Away Goals'], [home_goals_total, away_goals_total], color=['blue', 'red'])
    plt.title('Total Goals Scored (Home vs Away)')
    plt.ylabel('Goals')
    plt.show()


def visualize_draw_frequency(df):
    """
    Visualize the frequency of draws vs non-draws.
    """
    draw_count = df[df['FTR'] == 'D'].shape[0]
    non_draw_count = df.shape[0] - draw_count

    plt.figure(figsize=(10, 6))
    plt.bar(['Draws', 'Non-Draws'], [draw_count, non_draw_count], color=['gray', 'lightgray'])
    plt.title('Frequency of Draws vs Non-Draws')
    plt.ylabel('Number of Games')
    plt.show()
