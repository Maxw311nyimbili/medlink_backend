# Web scraping
"""
Web scraper for medical content ingestion into Weaviate
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import hashlib


def scrape_medical_website(url: str) -> Dict:
    """
    Scrape a medical website and extract clean content.
    Returns structured data ready for Weaviate ingestion.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get title
        title = soup.find('title')
        title = title.get_text().strip() if title else url

        # Get main content
        # Try common content containers
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')

        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = ' '.join(text.split())

        # Limit content length
        if len(text) > 5000:
            text = text[:5000]

        # Generate content hash
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        return {
            "url": url,
            "title": title,
            "content": text,
            "content_hash": content_hash,
            "word_count": len(text.split()),
            "domain": url.split('/')[2] if '/' in url else url
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def ingest_urls_to_weaviate(urls: List[str], weaviate_client) -> int:
    """
    Scrape multiple URLs and ingest into Weaviate.
    Returns number of documents successfully ingested.
    """
    from app.db.session import SessionLocal
    from app.db.models import KnowledgeSource

    db = SessionLocal()
    ingested_count = 0

    for url in urls:
        print(f"Scraping: {url}")

        # Check if already ingested
        existing = db.query(KnowledgeSource).filter(KnowledgeSource.url == url).first()
        if existing and existing.ingestion_status == "completed":
            print(f"  ✓ Already ingested")
            continue

        # Scrape content
        scraped = scrape_medical_website(url)
        if not scraped:
            print(f"  ✗ Failed to scrape")
            continue

        try:
            # Add to Weaviate
            result = weaviate_client.data_object.create(
                data_object={
                    "content": scraped["content"],
                    "source_url": scraped["url"],
                    "title": scraped["title"]
                },
                class_name="MedicalKnowledge"
            )

            weaviate_id = result

            # Save to database
            if existing:
                existing.ingestion_status = "completed"
                existing.weaviate_id = weaviate_id
                existing.content_hash = scraped["content_hash"]
                existing.word_count = scraped["word_count"]
            else:
                knowledge_source = KnowledgeSource(
                    url=scraped["url"],
                    title=scraped["title"],
                    domain=scraped["domain"],
                    content_hash=scraped["content_hash"],
                    word_count=scraped["word_count"],
                    weaviate_id=weaviate_id,
                    ingestion_status="completed"
                )
                db.add(knowledge_source)

            db.commit()
            ingested_count += 1
            print(f"  ✓ Ingested successfully")

        except Exception as e:
            print(f"  ✗ Weaviate error: {e}")

    db.close()
    return ingested_count