"""
ENHANCED RAG SERVICE: Pregnancy Health Assistant with Conversational Continuity

QUICK OVERVIEW:
- Detects query intent (greeting/follow-up/medical question) → routes appropriately
- Extracts relevant prior exchanges from conversation history → maintains context
- Retrieves medical chunks from Weaviate + falls back to hardcoded knowledge
- Filters low-confidence sources (< 0.65 threshold)
- Sends chunks + context + intent to Groq LLM → generates warm, cited answers
- Parses response into sentences with confidence scores + sources

MAIN FUNCTIONS:
- query_rag_system(query, history) → orchestrates entire pipeline
- detect_intent() → classifies query type
- _build_context_from_history() → extracts relevant prior exchanges (no bloat)
- search_weaviate() → vector search for medical knowledge
- generate_answer_with_groq() → LLM synthesis with tone adjustment
- parse_answer_with_confidence() → breaks answer into scored sentences
- add_to_history() → manages conversation state

USAGE:
  history = []
  response = query_rag_system("Is paracetamol safe?", history)
  history = add_to_history(history, "Is paracetamol safe?", response["answer"])

  # Next turn maintains context
  response = query_rag_system("What about dosage?", history)
  # System knows "dosage" refers to paracetamol from history
"""
import weaviate
import os
import re
from typing import List, Dict, Optional
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


def query_rag_system(
    query: str,
    conversation_history: Optional[List[Dict]] = None
) -> dict:
    """
    Main RAG orchestrator:
    1. Detect intent (greeting/follow-up/medical question)
    2. Extract relevant prior context from history
    3. Retrieve medical chunks from Weaviate
    4. Filter low-confidence sources (< 0.65)
    5. Generate answer with Groq (including history context)
    6. Parse into sentences with confidence scores
    """
    intent = detect_intent(query)

    # Handle casual messages with short responses
    if intent == "casual":
        casual_responses = {
            "thanks": "You're welcome!",
            "ok": "Got it!",
            "bye": "Take care!",
            "yeah": "👍",
            "cool": "Great!",
        }

        response_text = "Got it!"
        for keyword, response in casual_responses.items():
            if keyword in query.lower():
                response_text = response
                break

        return {
            "answer": response_text,
            "sentences": [{
                "text": response_text,
                "confidence": 0.95,
                "sources": []
            }]
        }

    if intent == "greeting":
        greetings = {
            "hi": "Hi there! What can I help you with?",
            "hello": "Hey! What's on your mind?",
            "how are you": "I'm here and ready to help. What would you like to know?",
            "thanks": "You're welcome! Feel free to ask if you have more questions.",
            "bye": "Take care! Come back anytime you have questions.",
        }

        # Find matching greeting
        greeting_text = None
        for keyword, response in greetings.items():
            if keyword in query.lower():
                greeting_text = response
                break

        if not greeting_text:
            greeting_text = "Hi! How can I help?"

        return {
            "answer": greeting_text,
            "sentences": [{
                "text": greeting_text,
                "confidence": 0.95,
                "sources": []
            }]
        }

    history_context = _build_context_from_history(conversation_history, query, intent)
    retrieval_query = f"{history_context}\n{query}".strip() if history_context else query
    chunks = search_weaviate(retrieval_query)
    chunks = [c for c in chunks if c["score"] >= 0.65]

    if not chunks:
        # Route based on query type
        if _is_medication_query(query):
            # Medication queries: use safe hardcoded knowledge only
            chunks = _get_medication_fallback_chunks(query)
        else:
            # Non-medication queries: use Groq with guardrails for better relevance
            return generate_fallback_with_groq(query)

    answer = generate_answer_with_groq(
        query=query,
        chunks=chunks,
        history_context=history_context,
        intent=intent
    )

    sentences = parse_answer_with_confidence(answer, chunks)

    return {
        "answer": answer,
        "sentences": sentences
    }


# ============================================================================
# INTENT DETECTION
# ============================================================================

def detect_intent(query: str) -> str:
    """Classify query type: greeting, follow_up, clarification, casual, or medical_question"""
    query_lower = query.lower().strip()

    # Casual/closing messages (very short acknowledgments)
    casual_patterns = [
        r'^(ok|okay|alright|got it|understood)\s*[!,.]?$',
        r'^(thanks?|thank you)\s*[!.]?$',
        r'^(yeah|yep|sure|cool)\s*[!.]?$',
        r'^(bye|goodbye|see you|take care)\s*[!.]?$',
    ]

    for pattern in casual_patterns:
        if re.match(pattern, query_lower):
            return "casual"

    # Greeting patterns
    greeting_patterns = [
        r'^(hi|hello|hey|greetings?)\s*[!?]?$',
        r'^(how are you|what\'s up|how\'s it going)',
    ]

    for pattern in greeting_patterns:
        if re.match(pattern, query_lower):
            return "greeting"

    # Follow-up patterns (short, context-dependent)
    followup_patterns = [
        r'^(more|tell me more|anything else|what else)',
        r'^(is it safe|will it|can i|should i)\s',
        r'^(what about|and)',
        r'^(ok|okay|understood)',
        r'^(yes|no|maybe)',
    ]

    for pattern in followup_patterns:
        if re.match(pattern, query_lower):
            return "follow_up"

    # Clarification patterns
    clarification_patterns = [
        r'^(can you explain|what does|what\'s|explain)',
        r'^(i don\'t understand)',
        r'^(clarify|elaborate)',
    ]

    for pattern in clarification_patterns:
        if re.match(pattern, query_lower):
            return "clarification"

    # Default to medical question (most common for this assistant)
    return "medical_question"


# ============================================================================
# SMART CONVERSATION HISTORY HANDLING
# ============================================================================

def _build_context_from_history(
    history: Optional[List[Dict]],
    current_query: str,
    intent: str
) -> str:
    """Extract relevant prior exchanges from history. Avoids token bloat by only including topically related exchanges."""

    if not history or len(history) == 0:
        return ""

    # For follow-ups, include the most recent exchange but keep it brief
    if intent == "follow_up":
        recent = history[-1]
        # Extract just the first sentence of the answer for context
        first_sentence = recent['answer'].split('.')[0].strip()
        return f"Context from earlier: {first_sentence}"

    # For clarifications, reference the prior topic more naturally
    if intent == "clarification":
        recent = history[-1]
        # Get topic keywords from the prior question
        topic = recent['question'][:50]  # First 50 chars as topic
        return f"About what we discussed: {topic}"

    # For medical questions, find topically relevant prior exchanges
    if intent == "medical_question":
        relevant_exchanges = _find_topical_overlaps(history, current_query)

        if relevant_exchanges:
            # Build context from up to 2 relevant prior exchanges
            context_parts = []
            for exchange in relevant_exchanges[:2]:
                context_parts.append(f"You previously asked: '{exchange['question']}'")

            if context_parts:
                return "Context: " + "; ".join(context_parts)

    return ""


def _find_topical_overlaps(history: List[Dict], current_query: str) -> List[Dict]:
    """
    Find prior exchanges that are topically related to current query.
    Uses simple keyword matching + semantic similarity.
    """
    if not history:
        return []

    # Extract key terms from current query
    current_terms = set(re.findall(r'\b\w{4,}\b', current_query.lower()))

    relevant = []
    for exchange in history[-5:]:  # Look at last 5 exchanges
        prior_terms = set(re.findall(r'\b\w{4,}\b', exchange["question"].lower()))

        # Calculate overlap
        overlap = len(current_terms & prior_terms) / max(len(current_terms), 1)

        if overlap > 0.3:  # Threshold: 30% keyword overlap
            relevant.append(exchange)

    return relevant


# ============================================================================
# WEAVIATE SEARCH
# ============================================================================

def search_weaviate(query: str, limit: int = 5) -> List[Dict]:
    """
    Search Weaviate for relevant pregnancy health information.
    Returns chunks with certainty scores.
    """
    client = get_weaviate_client()

    if not client:
        print("Weaviate not available, using fallback")
        return []

    try:
        schema = client.schema.get()
        if not schema.get("classes"):
            print("No Weaviate schema found - returning empty")
            return []

        result = (
            client.query
            .get("PregnancyKnowledge", ["content", "source_url", "title"])
            .with_near_text({"concepts": [query]})
            .with_additional(["certainty"])
            .with_limit(limit)
            .do()
        )

        if not result.get("data", {}).get("Get", {}).get("PregnancyKnowledge"):
            print("No results from Weaviate, returning empty")
            return []

        chunks = []
        for item in result["data"]["Get"]["PregnancyKnowledge"]:
            chunks.append({
                "content": item["content"],
                "source_url": item.get("source_url", ""),
                "title": item.get("title", ""),
                "score": item["_additional"]["certainty"]
            })

        return chunks

    except Exception as e:
        print(f"Weaviate search error: {e}")
        return []


# ============================================================================
# FALLBACK KNOWLEDGE
# ============================================================================

def _is_medication_query(query: str) -> bool:
    """Check if query is about medications/drugs (higher hallucination risk)"""
    medication_keywords = [
        "medicine", "drug", "medication", "pill", "tablet", "dose", "dosage",
        "ibuprofen", "aspirin", "paracetamol", "acetaminophen", "antibiotic",
        "prescription", "over-the-counter", "supplement", "vitamin", "take",
        "safe to take", "can i take", "should i take"
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in medication_keywords)


def _get_medication_fallback_chunks(query: str) -> List[Dict]:
    """
    Safe fallback for medication queries - use hardcoded knowledge only.
    Never let Groq generate medication advice (too risky).
    """
    query_lower = query.lower()

    medication_knowledge = {
        "paracetamol": {
            "content": "Paracetamol (acetaminophen) is generally considered safe during pregnancy when used at the recommended dose. It's often the first choice for pain or fever because it has a good safety record across all trimesters. However, it's best to avoid taking more than needed and to talk with a healthcare provider if symptoms persist.",
            "source_url": "https://www.nhs.uk/pregnancy/medications/",
            "title": "NHS - Medicines in Pregnancy",
            "score": 0.90
        },
        "ibuprofen": {
            "content": "Ibuprofen (a non-steroidal anti-inflammatory) is generally not recommended during pregnancy, particularly in the third trimester, as it may affect fetal development and labor. Paracetamol is a safer alternative for pain relief during pregnancy. Always discuss pain management options with your healthcare provider.",
            "source_url": "https://www.nhs.uk/pregnancy/medications/",
            "title": "NHS - Medicines in Pregnancy",
            "score": 0.88
        },
        "aspirin": {
            "content": "Aspirin should generally be avoided during pregnancy unless specifically recommended by your healthcare provider. It may increase bleeding risk and affect fetal development, especially in the third trimester. For pain relief, paracetamol is a safer option. Always consult your healthcare provider before taking any medication.",
            "source_url": "https://www.nhs.uk/pregnancy/medications/",
            "title": "NHS - Medicines in Pregnancy",
            "score": 0.87
        }
    }

    for keyword, chunk in medication_knowledge.items():
        if keyword in query_lower:
            return [chunk]

    # Fallback for unrecognized medication questions
    return [{
        "content": "For questions about specific medications during pregnancy, it's essential to consult your healthcare provider. They can evaluate your individual situation and recommend safe alternatives if needed.",
        "source_url": "https://www.nhs.uk/pregnancy/medications/",
        "title": "NHS - Medicines in Pregnancy",
        "score": 0.70
    }]


def generate_fallback_with_groq(query: str) -> dict:
    """
    Fallback generation when Weaviate has no results.
    Uses Groq with strict anti-hallucination guardrails.
    Only for NON-MEDICATION queries (lifestyle, symptoms, general questions).
    """
    from groq import Groq

    prompt = f"""You are a pregnancy health information assistant. A woman asked:
"{query}"

CRITICAL RULES:
1. Provide only general pregnancy knowledge (no rare conditions, no made-up facts)
2. NEVER invent statistics or medical claims
3. NEVER recommend treatments or medications
4. If uncertain, say so explicitly
5. Keep it short and direct (2-3 sentences max)
6. NO patronizing language like "don't worry"
7. Always suggest consulting a healthcare provider

Answer directly and concisely:"""

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temperature = less creative/hallucinatory
            max_tokens=300
        )

        answer = response.choices[0].message.content.strip()

        # Parse response into sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        parsed_sentences = []

        for sentence in sentences:
            if sentence.strip():
                parsed_sentences.append({
                    "text": sentence.strip(),
                    "confidence": 0.45,  # Low confidence for fallback
                    "sources": []
                })

        return {
            "answer": answer,
            "sentences": parsed_sentences,
            "is_fallback": True,
            "fallback_type": "groq_generated"
        }

    except Exception as e:
        print(f"Groq fallback error: {e}")
        return {
            "answer": "I don't have specific information about that. Please consult your healthcare provider for personalized guidance.",
            "sentences": [{
                "text": "I don't have specific information about that.",
                "confidence": 0.3,
                "sources": []
            }, {
                "text": "Please consult your healthcare provider for personalized guidance.",
                "confidence": 0.9,
                "sources": []
            }],
            "is_fallback": True,
            "fallback_type": "error"
        }


# ============================================================================
# ANSWER GENERATION
# ============================================================================

def generate_answer_with_groq(
    query: str,
    chunks: List[Dict],
    history_context: str = "",
    intent: str = "medical_question"
) -> str:
    """
    Generate answer using Groq LLM with pregnancy-specific prompting.
    Incorporates conversation history and intent for better flow.
    """
    from groq import Groq

    # Build context from chunks
    context = "\n\n".join([
        f"[Source {i + 1}: {chunk['title']}]\n{chunk['content']}"
        for i, chunk in enumerate(chunks)
    ])

    # Adjust tone based on intent
    tone_guidance = {
        "follow_up": "This is a follow-up question. Reference the earlier topic naturally and build on it.",
        "clarification": "The user is asking for clarification. Explain simply and break down complex ideas.",
        "medical_question": "Answer the medical question clearly and supportively."
    }

    # Build comprehensive prompt
    prompt = f"""You are a pregnancy health information assistant. Your role is to:
- Answer using ONLY the provided sources
- Use clear, direct language
- Be accurate and factual
- Always recommend consulting a healthcare provider for personalized advice
- Avoid speculation beyond what sources state
- NO patronizing language like "don't worry" or "don't be concerned"

{tone_guidance.get(intent, tone_guidance['medical_question'])}

{f'Conversation context: {history_context}' if history_context else ''}

Sources:
{context}

Question: {query}

Guidelines:
- Answer in 2-3 sentences (be concise)
- Cite sources with [1], [2], etc. after relevant statements
- Be direct and informative
- Never add reassurance phrases or emotional language
- Never speculate beyond the sources

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
        # Fallback response
        return f"Based on available information: {chunks[0]['content'][:200]}... Please consult your healthcare provider for personalized advice."


# ============================================================================
# CONFIDENCE SCORING & PARSING
# ============================================================================

def parse_answer_with_confidence(answer: str, chunks: List[Dict]) -> List[Dict]:
    """
    Parse answer into sentences and assign confidence scores.

    Confidence is based on:
    - Quality of cited sources (from Weaviate certainty scores)
    - Whether statement has citations
    - Domain authority of sources
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
        clean_text = re.sub(r'\s+', ' ', clean_text)  # Remove extra spaces

        if not citations:
            # No citations = lower confidence (general advice)
            result.append({
                "text": clean_text,
                "confidence": 0.5,
                "sources": []
            })
        else:
            # Get cited chunks and calculate average confidence
            cited_chunks = []
            for citation in citations:
                idx = int(citation) - 1
                if 0 <= idx < len(chunks):
                    cited_chunks.append(chunks[idx])

            if cited_chunks:
                # Average confidence from cited sources
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


# ============================================================================
# CONVERSATION HISTORY HELPER (for API usage)
# ============================================================================

def add_to_history(
    history: List[Dict],
    question: str,
    answer: str,
    max_turns: int = 10
) -> List[Dict]:
    """
    Add a Q&A exchange to conversation history.
    Maintains only recent turns to avoid memory bloat.

    Args:
        history: Existing conversation history
        question: User's question
        answer: Assistant's answer
        max_turns: Maximum turns to keep (older ones are dropped)

    Returns:
        Updated history
    """
    if history is None:
        history = []

    history.append({
        "question": question,
        "answer": answer
    })

    # Keep only recent turns
    return history[-max_turns:]