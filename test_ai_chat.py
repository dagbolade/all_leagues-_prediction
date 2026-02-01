"""
Simple test to call AI chat API and see detailed error
"""
import requests
import json

print("Testing AI Chat API...")
print("=" * 60)

url = "http://localhost:5000/api/ai-chat"
data = {"message": "hi"}

try:
    print(f"Sending POST to: {url}")
    print(f"Data: {data}")
    
    response = requests.post(url, json=data, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"\nError: {e}")

print("=" * 60)
print("\nNow check the Flask terminal for detailed logs!")
