
import requests
import time

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token-day2"}

print("="*70)
print("COMPLETE MEDLINK BACKEND TEST")
print("="*70)

# Test 1: Health
print("\n1. HEALTH CHECK")
r = requests.get(f"{BASE_URL}/health")
print(f"   ✓ Status: {r.status_code} - {r.json()}")

# Test 2: Announcements
print("\n2. LANDING - Announcements")
r = requests.get(f"{BASE_URL}/landing/announcements")
print(f"   ✓ Found {len(r.json())} announcements")

# Test 3: Consent
print("\n3. LANDING - Consent")
r = requests.get(f"{BASE_URL}/landing/consent/latest")
print(f"   ✓ Version: {r.json()['version']}")

# Test 4: Create Forum Post
print("\n4. FORUM - Create Post")
r = requests.post(
    f"{BASE_URL}/forum/posts",
    headers=HEADERS,
    json={
        "title": "Managing Type 2 Diabetes",
        "content": "What are the best dietary changes for managing type 2 diabetes?",
        "category": "chronic-conditions"
    }
)
if r.status_code == 201:
    post_id = r.json()["id"]
    print(f"   ✓ Created post ID: {post_id}")
else:
    print(f"   ✗ Error: {r.json()}")
    post_id = None

# Test 5: Get Posts
print("\n5. FORUM - Get All Posts")
r = requests.get(f"{BASE_URL}/forum/posts")
print(f"   ✓ Total posts: {len(r.json())}")

# Test 6: RAG Chat
print("\n6. CHAT - RAG Query (may take 10-30 seconds)")
print("   Querying: 'What is aspirin used for?'")
start = time.time()
r = requests.post(
    f"{BASE_URL}/chat/query",
    headers=HEADERS,
    json={"query": "What is aspirin used for?"},
    timeout=60
)
elapsed = time.time() - start

if r.status_code == 200:
    data = r.json()
    print(f"   ✓ Response time: {elapsed:.1f}s")
    print(f"   ✓ Answer: {data['answer'][:100]}...")
    print(f"   ✓ Sentences with confidence:")
    for s in data['sentences']:
        print(f"      - {s['confidence']:.2f}: {s['text'][:50]}...")
else:
    print(f"   ✗ Error: {r.json()}")

# Test 7: Chat History
print("\n7. CHAT - Get History")
r = requests.get(f"{BASE_URL}/chat/history", headers=HEADERS)
print(f"   ✓ Messages in history: {len(r.json())}")

print("\n" + "="*70)
print("✅ ALL TESTS COMPLETED!")
print("="*70)
