"""
Direct test of Ollama API with qwen2.5:7b model
"""
import requests
import json

print("Testing Ollama API directly...")
print("=" * 60)

# Test 1: Check if Ollama is running
print("\n1. Checking if Ollama is running...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Ollama is running!")
        print(f"\n   Available models:")
        for model in data.get('models', []):
            print(f"      - {model['name']}")
    else:
        print(f"   ❌ Unexpected status: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Test 2: Try to generate a response with qwen2.5:7b
print("\n2. Testing chat generation with qwen2.5:7b...")
try:
    url = "http://localhost:11434/api/generate"
    
    payload = {
        'model': 'qwen2.5:7b',
        'prompt': 'Say "Hello, I am working!" in one sentence.',
        'stream': False
    }
    
    print(f"   Sending request to: {url}")
    print(f"   Model: {payload['model']}")
    print(f"   Waiting for response...")
    
    response = requests.post(url, json=payload, timeout=60)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n   ✅ SUCCESS!")
        print(f"\n   AI Response:")
        print(f"   {result.get('response', 'No response')}")
        print(f"\n   Model used: {result.get('model', 'Unknown')}")
    else:
        print(f"   ❌ Failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.Timeout:
    print(f"   ❌ Request timed out (model might be loading)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
