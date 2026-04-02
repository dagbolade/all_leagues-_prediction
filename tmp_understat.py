from understatapi import UnderstatClient

def test_understat():
    try:
        client = UnderstatClient()
        # EPL 2024 means 2024/2025 season in Understat terms typically
        epl = client.league(league="EPL").get_team_data(season="2024")
        print("Understat EPL Teams 2024:")
        for team_id, team_data in epl.items():
            print(f" - {team_data['title']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_understat()
