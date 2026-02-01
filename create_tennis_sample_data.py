"""
Create sample tennis data for testing

Generates realistic tennis match data with:
- ATP/WTA players
- Different surfaces
- Rankings
- Tournament rounds
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Top players for sample data
ATP_PLAYERS = [
    'Novak Djokovic', 'Carlos Alcaraz', 'Daniil Medvedev',
    'Jannik Sinner', 'Andrey Rublev', 'Stefanos Tsitsipas',
    'Holger Rune', 'Casper Ruud', 'Hubert Hurkacz',
    'Taylor Fritz', 'Alexander Zverev', 'Tommy Paul',
    'Grigor Dimitrov', 'Alex de Minaur', 'Frances Tiafoe',
    'Karen Khachanov', 'Lorenzo Musetti', 'Ben Shelton'
]

WTA_PLAYERS = [
    'Iga Swiatek', 'Aryna Sabalenka', 'Coco Gauff',
    'Elena Rybakina', 'Jessica Pegula', 'Ons Jabeur',
    'Marketa Vondrousova', 'Qinwen Zheng', 'Maria Sakkari',
    'Karolina Muchova', 'Barbora Krejcikova', 'Jelena Ostapenko',
    'Madison Keys', 'Daria Kasatkina', 'Beatriz Haddad Maia'
]

SURFACES = ['Hard', 'Clay', 'Grass']
TOURNAMENTS = [
    'Australian Open', 'French Open', 'Wimbledon', 'US Open',
    'Indian Wells', 'Miami', 'Monte Carlo', 'Madrid', 'Rome',
    'Cincinnati', 'Shanghai', 'Paris Masters',
    'ATP 250', 'ATP 500', 'WTA 1000'
]

ROUNDS = ['Final', 'Semi-Final', 'Quarter-Final', 'Round of 16', 'Round of 32']


def create_tennis_sample_data(num_matches=800, tour='ATP'):
    """
    Create sample tennis match data.

    Args:
        num_matches: Number of matches to generate
        tour: 'ATP' or 'WTA'

    Returns:
        DataFrame with sample tennis matches
    """
    print(f"Creating {num_matches} sample {tour} tennis matches...")

    players = ATP_PLAYERS if tour == 'ATP' else WTA_PLAYERS

    data = []
    start_date = datetime(2023, 1, 1)

    # Assign rankings (1-50)
    player_rankings = {player: i+1 for i, player in enumerate(players)}

    for i in range(num_matches):
        # Random date in last 2 years
        match_date = start_date + timedelta(days=np.random.randint(0, 730))

        # Select two different players
        player1, player2 = np.random.choice(players, size=2, replace=False)

        # Get rankings
        rank1 = player_rankings[player1]
        rank2 = player_rankings[player2]

        # Surface
        surface = np.random.choice(SURFACES, p=[0.5, 0.3, 0.2])  # More hard court matches

        # Tournament
        tournament = np.random.choice(TOURNAMENTS)

        # Round
        round_name = np.random.choice(ROUNDS, p=[0.05, 0.10, 0.15, 0.30, 0.40])

        # Winner (higher ranked player has better chance)
        rank_diff = rank2 - rank1  # Positive if player1 is better ranked

        # Probability player1 wins based on ranking
        prob_p1_wins = 0.5 + (rank_diff / 100)  # Simple ranking-based probability
        prob_p1_wins = np.clip(prob_p1_wins, 0.2, 0.8)  # Keep reasonable

        winner = 'Player1' if np.random.random() < prob_p1_wins else 'Player2'

        # Sets (best of 3 for most, best of 5 for Grand Slams)
        is_grand_slam = tournament in ['Australian Open', 'French Open', 'Wimbledon', 'US Open']

        if winner == 'Player1':
            if is_grand_slam:
                sets = np.random.choice(['3-0', '3-1', '3-2'], p=[0.3, 0.4, 0.3])
            else:
                sets = np.random.choice(['2-0', '2-1'], p=[0.5, 0.5])
        else:
            if is_grand_slam:
                sets = np.random.choice(['0-3', '1-3', '2-3'], p=[0.3, 0.4, 0.3])
            else:
                sets = np.random.choice(['0-2', '1-2'], p=[0.5, 0.5])

        # Serve stats (realistic approximations)
        p1_aces = int(np.random.normal(6, 3))
        p2_aces = int(np.random.normal(6, 3))
        p1_double_faults = int(np.random.normal(2, 1))
        p2_double_faults = int(np.random.normal(2, 1))

        match = {
            'Date': match_date,
            'Player1': player1,
            'Player2': player2,
            'Player1Rank': rank1,
            'Player2Rank': rank2,
            'Tournament': tournament,
            'Round': round_name,
            'Surface': surface,
            'Winner': winner,
            'Sets': sets,
            'Player1Aces': max(0, p1_aces),
            'Player2Aces': max(0, p2_aces),
            'Player1DoubleFaults': max(0, p1_double_faults),
            'Player2DoubleFaults': max(0, p2_double_faults),
            'Tour': tour
        }

        data.append(match)

    df = pd.DataFrame(data)
    df = df.sort_values('Date').reset_index(drop=True)

    print(f"  Created {len(df)} matches")
    print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"  Surfaces: {df['Surface'].value_counts().to_dict()}")

    return df


def main():
    """Create and save sample tennis data."""
    print("=" * 80)
    print("CREATING SAMPLE TENNIS DATA")
    print("=" * 80)

    # Create ATP data
    atp_data = create_tennis_sample_data(num_matches=500, tour='ATP')

    # Create WTA data
    wta_data = create_tennis_sample_data(num_matches=300, tour='WTA')

    # Combine
    combined_data = pd.concat([atp_data, wta_data], ignore_index=True)
    combined_data = combined_data.sort_values('Date').reset_index(drop=True)

    # Save
    output_dir = Path("data/tennis/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "tennis_sample.csv"
    combined_data.to_csv(output_file, index=False)

    print(f"\n[OK] Saved {len(combined_data)} matches to {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()
