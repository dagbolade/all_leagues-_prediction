import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.services.live_scores_service import get_live_scores_service

def test_verification():
    service = get_live_scores_service()
    print(f"Service initialized. API Key present: {bool(service.api_key)}")
    
    # Test Search
    team_id = service.search_team("Arsenal")
    print(f"Arsenal ID: {team_id}")
    
    if team_id:
        # Get Matches
        print("Fetching recent matches for Arsenal...")
        matches = service.get_team_matches(team_id, limit=10, status='FINISHED')
        print(f"Found {len(matches)} matches")
        
        target_date = "2024-05-19"
        for m in matches:
            print(f"Match: {m['date']} - {m['home_team']} vs {m['away_team']} ({m['status']}) - {m['score']['fullTime']['home']}-{m['score']['fullTime']['away']}")

if __name__ == "__main__":
    test_verification()
