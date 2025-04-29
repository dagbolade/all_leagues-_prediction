# services/football_service.py
import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FootballDataService:
    def __init__(self):
        self.API_KEY = os.getenv('API_KEY')
        self.BASE_URL = 'https://api.football-data.org/v4'
        self.headers = {
            'X-Auth-Token': self.API_KEY
        }

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_live_matches(self):
        try:
            response = requests.get(
                f"{self.BASE_URL}/matches",
                headers=self.headers,
                params={'status': 'LIVE,IN_PLAY,PAUSED,SCHEDULED'}
            )

            # Print debug information
            print("API Response Status:", response.status_code)
            print("API Response Headers:", response.headers)
            print("API Response Content:", response.text[:500])  # First 500 chars

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error Status Code: {response.status_code}")
                print(f"Error Response: {response.text}")
                return None

        except Exception as e:
            print(f"API Request Error: {str(e)}")
            return None

    def handle_api_response(self, response, error_context="API"):
        """Helper method to handle API responses consistently."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"{error_context} HTTP Error: {e}")
            self.logger.error(f"Response content: {response.text}")
        except Exception as e:
            self.logger.error(f"{error_context} Error: {e}")
        return None

    def get_matches_by_competition(self, competition_id):
        """Get matches for a specific competition."""
        try:
            url = f"{self.BASE_URL}/competitions/{competition_id}/matches"
            response = requests.get(url, headers=self.headers)
            return self.handle_api_response(response, "Competition matches")
        except Exception as e:
            self.logger.error(f"Error fetching competition matches: {str(e)}")
            return None

    def get_todays_matches(self):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            response = requests.get(
                f"{self.BASE_URL}/matches",
                headers=self.headers,
                params={
                    'dateFrom': today,
                    'dateTo': today,
                    'status': 'SCHEDULED,LIVE,IN_PLAY'
                }
            )
            matches_data = self.handle_api_response(response, "Today's matches")
            return matches_data.get('matches', []) if matches_data else []
        except Exception as e:
            self.logger.error(f"Error fetching today's matches: {str(e)}")
            return []

    # app/services/football_service.py

    # In football_service.py
    def get_predictions_for_matches(self):  # Only needs self
        try:
            matches = self.get_live_matches()
            predictions = []

            if not matches or 'matches' not in matches:
                return []

            for match in matches['matches']:
                try:
                    home_team = match['homeTeam']['name']
                    away_team = match['awayTeam']['name']

                    if self.predictor and home_team and away_team:  # Using self.predictor
                        try:
                            match_predictions, probabilities = self.predictor.predict_match(home_team, away_team)
                            predictions.append({
                                'match_details': {
                                    'competition': match['competition']['name'],
                                    'kickoff': match['utcDate'],
                                    'homeTeam': home_team,
                                    'awayTeam': away_team,
                                    'status': match['status']
                                },
                                'predictions': match_predictions,
                                'probabilities': probabilities
                            })
                            print(f"Successfully predicted {home_team} vs {away_team}")
                        except Exception as e:
                            print(f"Error making prediction for {home_team} vs {away_team}: {e}")
                            continue
                except Exception as e:
                    print(f"Error processing match: {str(e)}")
                    continue

            return predictions
        except Exception as e:
            print(f"Error in get_predictions_for_matches: {str(e)}")
            return []