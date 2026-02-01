"""
Test Ollama Connection
"""
import requests
import json

print("Testing Ollama connection...")
print("=" * 60)

try:
    # Test if Ollama is running
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    
    if response.status_code == 200:
        print("✅ Ollama is running!")
        
        data = response.json()
        if 'models' in data and len(data['models']) > 0:
            print(f"\n✅ Models installed:")
            for model in data['models']:
                print(f"   - {model['name']}")
        
        # Test a simple chat
        print("\n" + "=" * 60)
        print("Testing AI chat...")
        print("=" * 60)
        
        chat_data = {
            "model": "qwen2.5:7b",
            "messages": [
                {"role": "user", "content": "In one sentence, what makes a good football prediction?"}
            ],
            "stream": False
        }
        
        chat_response = requests.post(
            "http://localhost:11434/api/chat",
            json=chat_data,
            timeout=30
        )
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            print("\n✅ AI Response:")
            print(f"\n{result['message']['content']}\n")
            print("=" * 60)
            print("\n🎉 SUCCESS! Ollama is working perfectly!")
            print("\nYou can now use the AI at: http://localhost:5000/chat")
        else:
            print(f"❌ Chat failed: {chat_response.status_code}")
    else:
        print(f"❌ Ollama not responding: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to Ollama")
    print("   Make sure Ollama app is running (check system tray)")
except Exception as e:
    print(f"❌ Error: {e}")
