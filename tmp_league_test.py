from understatapi import UnderstatClient
client = UnderstatClient()

test_leagues = [
    'EPL', 'epl', 'La_liga', 'La_Liga', 'la_liga', 'La liga', 
    'Bundesliga', 'bundesliga', 
    'Serie_A', 'serie_a', 'Serie A',
    'Ligue_1', 'ligue_1', 'Ligue 1'
]

print("Testing Understat Leagues:")
for l in test_leagues:
    try:
        data = client.league(league=l).get_match_data(season="2024")
        print(f"✅ EXACT MATCH FOUND: {l}")
    except Exception as e:
        print(f"❌ FAILED {l}: {e}")
