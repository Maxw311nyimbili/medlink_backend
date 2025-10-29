import requests

BASE_URL = "http://localhost:8000"

# Test that backend started (Firebase initialized successfully)
response = requests.get(f"{BASE_URL}/health")
print(f"Backend status: {response.json()}")

# Try auth endpoint with fake token (should reject gracefully)
response = requests.post(
    f"{BASE_URL}/auth/exchange",
    json={"id_token": "fake-token-for-testing"}
)

print(f"\nAuth endpoint status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 401:
    print("\n Firebase is working! (correctly rejected fake token)")
else:
    print("\n Unexpected response")