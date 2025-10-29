import requests

# Test Ollama directly
print("Testing Ollama connection...")
try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
            "prompt": "Is paracetamol safe for pregnant women? Answer in one sentence",
            "stream": False
        },
        timeout=30
    )
    if response.status_code == 200:
        print("✅ Ollama is responding")
        print(f"   Response: {response.json()['response']}...")
    else:
        print(f"❌ Ollama returned: {response.status_code}")
except Exception as e:
    print(f"❌ Cannot connect to Ollama: {e}")