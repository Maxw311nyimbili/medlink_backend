"""
Test real RAG system (Weaviate + Ollama)
"""
import requests

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token-day2"}

print("=" * 60)
print("REAL RAG SYSTEM TEST")
print("=" * 60)

queries = [
    "What is aspirin used for?",
    "How do I treat a headache?",
    "What causes a fever?"
]

for i, query in enumerate(queries, 1):
    print(f"\n{i}. Query: {query}")

    response = requests.post(
        f"{BASE_URL}/chat/query",
        headers=HEADERS,
        json={"query": query},
        timeout=60  # Ollama can take time
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   Answer: {data['answer'][:150]}...")
        print(f"\n   Confidence scores:")
        for sentence in data['sentences']:
            print(f"     - {sentence['confidence']:.2f}: {sentence['text'][:60]}...")
            if sentence['sources']:
                print(f"       Sources: {len(sentence['sources'])} found")
    else:
        print(f"   Error: {response.status_code}")
        print(f"   {response.json()}")

print("\n" + "=" * 60)
print("✅ Real RAG system tested!")