"""
RAG Service: Weaviate retrieval + Groq generation with confidence scoring
"""
import weaviate
import os
import re
from typing import List, Dict
from app.core.config import settings


def get_weaviate_client():
    """Get or create Weaviate client"""
    try:
        client = weaviate.Client(
            url=settings.WEAVIATE_URL,
            timeout_config=(5, 15)
        )
        return client
    except Exception as e:
        print(f"Weaviate connection error: {e}")
        return None


def query_rag_system(query: str) -> dict:
    """
    Main RAG pipeline:
    1. Retrieve relevant chunks from Weaviate
    2. Generate answer with Groq
    3. Parse response and assign confidence scores
    """
    # Step 1: Retrieve chunks from Weaviate
    chunks = search_weaviate(query)

    if not chunks:
        return {
            "answer": "I don't have enough information to answer that question accurately. Please consult a healthcare professional for medical advice.",
            "sentences": [
                {
                    "text": "I don't have enough information to answer that question accurately.",
                    "confidence": 0.3,
                    "sources": []
                },
                {
                    "text": "Please consult a healthcare professional for medical advice.",
                    "confidence": 0.9,
                    "sources": []
                }
            ]
        }

    # Step 2: Generate answer with Groq
    answer = generate_answer_with_groq(query, chunks)

    # Step 3: Parse answer and assign confidence based on chunk scores
    sentences = parse_answer_with_confidence(answer, chunks)

    return {
        "answer": answer,
        "sentences": sentences
    }


def search_weaviate(query: str, limit: int = 5) -> List[Dict]:
    """
    Search Weaviate for relevant medical information.
    Returns chunks with certainty scores.
    """
    client = get_weaviate_client()

    if not client:
        print("Weaviate not available, using fallback")
        return []

    try:
        # Check if schema exists
        schema = client.schema.get()
        if not schema.get("classes"):
            print("No Weaviate schema found - need to ingest data first")
            return _get_fallback_chunks(query)

        # Search for relevant content
        result = (
            client.query
            .get("MedicalKnowledge", ["content", "source_url", "title"])
            .with_near_text({"concepts": [query]})
            .with_additional(["certainty"])
            .with_limit(limit)
            .do()
        )

        if not result.get("data", {}).get("Get", {}).get("MedicalKnowledge"):
            print("No results from Weaviate, using fallback")
            return _get_fallback_chunks(query)

        chunks = []
        for item in result["data"]["Get"]["MedicalKnowledge"]:
            chunks.append({
                "content": item["content"],
                "source_url": item.get("source_url", ""),
                "title": item.get("title", ""),
                "score": item["_additional"]["certainty"]
            })

        return chunks

    except Exception as e:
        print(f"Weaviate search error: {e}")
        return _get_fallback_chunks(query)


def _get_fallback_chunks(query: str) -> List[Dict]:
    """
    Fallback knowledge when Weaviate is empty or unavailable.
    """
    query_lower = query.lower()

    fallback_knowledge = {
        "aspirin": {
            "content": "Aspirin (acetylsalicylic acid) is a medication used to reduce pain, fever, and inflammation. It works by blocking cyclooxygenase enzymes. Common uses include headache relief, reducing fever, and as an anti-inflammatory. Always consult a doctor before starting aspirin therapy, especially for long-term use.",
            "source_url": "https://www.mayoclinic.org/drugs-supplements/aspirin-oral-route/description/drg-20068907",
            "title": "Mayo Clinic - Aspirin Information",
            "score": 0.85
        },
        "headache": {
            "content": "Headaches can be caused by stress, dehydration, lack of sleep, or underlying medical conditions. Treatment depends on the type and cause. Over-the-counter pain relievers like ibuprofen or acetaminophen may help. Rest, hydration, and stress management are also beneficial. Persistent or severe headaches should be evaluated by a healthcare provider.",
            "source_url": "https://www.mayoclinic.org/diseases-conditions/headache/symptoms-causes/syc-20377135",
            "title": "Mayo Clinic - Headache Overview",
            "score": 0.82
        },
        "fever": {
            "content": "A fever is a temporary increase in body temperature, often due to infection. Normal body temperature is around 98.6°F (37°C). A fever is generally considered 100.4°F (38°C) or higher. Treatment includes rest, fluids, and fever-reducing medications if needed. Seek medical attention for high fevers (above 103°F), persistent fevers, or concerning symptoms.",
            "source_url": "https://www.mayoclinic.org/diseases-conditions/fever/symptoms-causes/syc-20352759",
            "title": "Mayo Clinic - Fever",
            "score": 0.88
        }
    }

    for keyword, chunk in fallback_knowledge.items():
        if keyword in query_lower:
            return [chunk]

    return [{
        "content": "For specific medical questions, it's important to consult with a healthcare professional. They can provide personalized advice based on your medical history and current health status.",
        "source_url": "https://www.cdc.gov/",
        "title": "CDC - General Health Information",
        "score": 0.6
    }]


def generate_answer_with_groq(query: str, chunks: List[Dict]) -> str:
    """
    Generate answer using Groq LLM with retrieved context.
    """
    from groq import Groq

    # Build context from chunks
    context = "\n\n".join([
        f"[Source {i + 1}: {chunk['title']}]\n{chunk['content']}"
        for i, chunk in enumerate(chunks)
    ])

    # Prompt engineering for medical Q&A
    prompt = f"""You are a medical information assistant. Answer the question using ONLY the provided sources. Be accurate and cite which source supports each statement.

Sources:
{context}

Question: {query}

Answer in 2-4 sentences. After each sentence that uses information from a source, add [1], [2], etc. to cite the source number.

Answer:"""

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Groq generation error: {e}")
        return f"Based on available information: {chunks[0]['content'][:200]}..."


def parse_answer_with_confidence(answer: str, chunks: List[Dict]) -> List[Dict]:
    """
    Parse answer into sentences and assign confidence scores.
    Confidence = average certainty of cited sources.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', answer)

    result = []
    for sentence in sentences:
        if not sentence.strip():
            continue

        # Find citation numbers [1], [2], etc.
        citations = re.findall(r'\[(\d+)\]', sentence)

        # Remove citation markers for clean text
        clean_text = re.sub(r'\s*\[\d+\]\s*', ' ', sentence).strip()

        if not citations:
            # No citations = lower confidence
            result.append({
                "text": clean_text,
                "confidence": 0.5,
                "sources": []
            })
        else:
            # Get cited chunks
            cited_chunks = []
            for citation in citations:
                idx = int(citation) - 1
                if 0 <= idx < len(chunks):
                    cited_chunks.append(chunks[idx])

            # Average confidence from cited sources
            if cited_chunks:
                avg_confidence = sum(c["score"] for c in cited_chunks) / len(cited_chunks)
                sources = [
                    {"url": c["source_url"], "title": c["title"]}
                    for c in cited_chunks
                ]
            else:
                avg_confidence = 0.5
                sources = []

            result.append({
                "text": clean_text,
                "confidence": round(avg_confidence, 2),
                "sources": sources
            })

    return result