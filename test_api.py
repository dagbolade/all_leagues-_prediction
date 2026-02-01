"""
Test the API endpoints to make sure everything works
"""

import requests
import json
import time

API_BASE = "http://localhost:5000"

def test_status():
    """Test status endpoint."""
    print("\n1. Testing /api/status...")
    try:
        response = requests.get(f"{API_BASE}/api/status", timeout=5)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_sports():
    """Test sports listing."""
    print("\n2. Testing /api/sports...")
    try:
        response = requests.get(f"{API_BASE}/api/sports", timeout=5)
        print(f"   Status Code: {response.status_code}")
        data = response.json()
        print(f"   Available Sports: {list(data.get('sports', {}).keys())}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_teams():
    """Test teams endpoint."""
    print("\n3. Testing /api/basketball/teams...")
    try:
        response = requests.get(f"{API_BASE}/api/basketball/teams", timeout=5)
        print(f"   Status Code: {response.status_code}")
        data = response.json()
        teams = data.get('teams', [])
        print(f"   Found {len(teams)} teams")
        if teams:
            print(f"   Sample: {teams[:5]}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_prediction():
    """Test prediction endpoint."""
    print("\n4. Testing /api/basketball/predict...")
    try:
        payload = {
            'home': 'Los Angeles Lakers',
            'away': 'Boston Celtics'
        }
        response = requests.post(
            f"{API_BASE}/api/basketball/predict",
            json=payload,
            timeout=5
        )
        print(f"   Status Code: {response.status_code}")
        data = response.json()
        print(f"   Prediction: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def main():
    """Run all API tests."""
    print("="*60)
    print("API TESTING")
    print("="*60)

    print("\nWaiting for API to start...")
    time.sleep(3)

    results = []

    results.append(("Status", test_status()))
    results.append(("Sports List", test_sports()))
    results.append(("Teams", test_teams()))
    results.append(("Prediction", test_prediction()))

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("="*60)


if __name__ == "__main__":
    main()
