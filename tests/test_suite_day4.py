"""
Day 4: Comprehensive Backend Test Suite
Tests all endpoints and core functionality
"""
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token-day2", "Content-Type": "application/json"}


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'


def test(name, func):
    """Run a test and display results"""
    print(f"\n{Colors.YELLOW}Testing: {name}{Colors.END}")
    try:
        result = func()
        print(f"{Colors.GREEN}✓ PASS{Colors.END}")
        return True, result
    except AssertionError as e:
        print(f"{Colors.RED}✗ FAIL: {e}{Colors.END}")
        return False, None
    except Exception as e:
        print(f"{Colors.RED}✗ ERROR: {e}{Colors.END}")
        return False, None


print(f"\n{Colors.CYAN}{'=' * 70}")
print("MEDLINK BACKEND - DAY 4 TEST SUITE")
print(f"{'=' * 70}{Colors.END}\n")
print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

results = []

# ============================================================================
# HEALTH & INFRASTRUCTURE TESTS
# ============================================================================

print(f"\n{Colors.CYAN}=== INFRASTRUCTURE TESTS ==={Colors.END}")


def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.json()["status"] == "healthy"
    return r.json()


def test_root():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "MedLink API" in r.json()["message"]
    return r.json()


results.append(test("Health Check", test_health))
results.append(test("Root Endpoint", test_root))

# ============================================================================
# LANDING PAGE TESTS
# ============================================================================

print(f"\n{Colors.CYAN}=== LANDING PAGE TESTS ==={Colors.END}")


def test_announcements():
    r = requests.get(f"{BASE_URL}/landing/announcements")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list), "Should return a list"
    if len(data) > 0:
        assert "title" in data[0]
        assert "content" in data[0]
    return f"Found {len(data)} announcements"


def test_consent():
    r = requests.get(f"{BASE_URL}/landing/consent/latest")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "content" in data
    return f"Version: {data['version']}"


def test_user_preferences():
    r = requests.get(f"{BASE_URL}/landing/preferences", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "preferred_language" in data
    return data


results.append(test("Get Announcements", test_announcements))
results.append(test("Get Consent", test_consent))
results.append(test("Get User Preferences", test_user_preferences))

# ============================================================================
# FORUM TESTS
# ============================================================================

print(f"\n{Colors.CYAN}=== FORUM TESTS ==={Colors.END}")

CREATED_POST_ID = None


def test_create_post():
    global CREATED_POST_ID
    r = requests.post(
        f"{BASE_URL}/forum/posts",
        headers=HEADERS,
        json={
            "title": "Day 4 Test Post",
            "content": "Testing forum functionality",
            "category": "general"
        }
    )
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"
    data = r.json()
    assert "id" in data
    CREATED_POST_ID = data["id"]
    return f"Created post ID: {CREATED_POST_ID}"


def test_get_posts():
    r = requests.get(f"{BASE_URL}/forum/posts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    return f"Found {len(data)} posts"


def test_get_single_post():
    if not CREATED_POST_ID:
        raise AssertionError("No post created yet")
    r = requests.get(f"{BASE_URL}/forum/posts/{CREATED_POST_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == CREATED_POST_ID
    return f"Retrieved post: {data['title']}"


def test_create_comment():
    if not CREATED_POST_ID:
        raise AssertionError("No post created yet")
    r = requests.post(
        f"{BASE_URL}/forum/posts/{CREATED_POST_ID}/comments",
        headers=HEADERS,
        json={"content": "Test comment on day 4"}
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    return f"Created comment ID: {data['id']}"


def test_get_comments():
    if not CREATED_POST_ID:
        raise AssertionError("No post created yet")
    r = requests.get(f"{BASE_URL}/forum/posts/{CREATED_POST_ID}/comments")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    return f"Found {len(data)} comments"


results.append(test("Create Forum Post", test_create_post))
results.append(test("Get All Posts", test_get_posts))
results.append(test("Get Single Post", test_get_single_post))
results.append(test("Create Comment", test_create_comment))
results.append(test("Get Comments", test_get_comments))

# ============================================================================
# CHAT / RAG TESTS
# ============================================================================

print(f"\n{Colors.CYAN}=== CHAT / RAG TESTS ==={Colors.END}")


def test_chat_query():
    print("  (This may take 10-30 seconds...)")
    start = time.time()
    r = requests.post(
        f"{BASE_URL}/chat/query",
        headers=HEADERS,
        json={"query": "What is a headache?"},
        timeout=60
    )
    elapsed = time.time() - start

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "answer" in data
    assert "sentences" in data
    assert len(data["sentences"]) > 0

    # Check confidence scores
    for sentence in data["sentences"]:
        assert "text" in sentence
        assert "confidence" in sentence
        assert 0 <= sentence["confidence"] <= 1

    avg_confidence = sum(s["confidence"] for s in data["sentences"]) / len(data["sentences"])
    return f"Response time: {elapsed:.1f}s, Avg confidence: {avg_confidence:.2f}"


def test_chat_history():
    r = requests.get(f"{BASE_URL}/chat/history", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    return f"Found {len(data)} messages in history"


results.append(test("Chat Query (RAG)", test_chat_query))
results.append(test("Chat History", test_chat_history))

# ============================================================================
# MEDIA UPLOAD TEST
# ============================================================================

print(f"\n{Colors.CYAN}=== MEDIA UPLOAD TEST ==={Colors.END}")


def test_media_upload():
    # Create a fake image file
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }
    data = {'scan_type': 'barcode'}

    r = requests.post(
        f"{BASE_URL}/media/upload",
        headers={"Authorization": "Bearer test-token-day2"},
        files=files,
        data=data
    )
    assert r.status_code == 200
    result = r.json()
    assert "id" in result
    assert "file_name" in result
    return f"Uploaded file ID: {result['id']}"


results.append(test("Media Upload", test_media_upload))

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

print(f"\n{Colors.CYAN}{'=' * 70}")
print("TEST RESULTS SUMMARY")
print(f"{'=' * 70}{Colors.END}\n")

passed = sum(1 for r in results if r[0])
total = len(results)
percentage = (passed / total * 100) if total > 0 else 0

print(f"Total Tests: {total}")
print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
print(f"{Colors.RED}Failed: {total - passed}{Colors.END}")
print(f"Success Rate: {percentage:.1f}%\n")

if percentage == 100:
    print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! Backend is ready for production.{Colors.END}")
elif percentage >= 80:
    print(f"{Colors.YELLOW}⚠️  Most tests passed. Fix remaining issues before deployment.{Colors.END}")
else:
    print(f"{Colors.RED}❌ Multiple failures detected. Review logs and fix critical issues.{Colors.END}")

print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")