"""
Initialize Weaviate schema and ingest initial medical content
"""
import weaviate
from app.core.config import settings
from app.services.scraper_service import ingest_urls_to_weaviate

# Connect to Weaviate
client = weaviate.Client(
    url=settings.WEAVIATE_URL,
    timeout_config=(5, 15)
)

print("Setting up Weaviate...")

# Delete existing schema if present
try:
    client.schema.delete_class("MedicalKnowledge")
    print("✓ Deleted existing schema")
except:
    pass

# Create schema
schema = {
    "class": "MedicalKnowledge",
    "description": "Medical information from trusted sources",
    "vectorizer": "text2vec-transformers",
    "moduleConfig": {
        "text2vec-transformers": {
            "poolingStrategy": "masked_mean"
        }
    },
    "properties": [
        {
            "name": "content",
            "dataType": ["text"],
            "description": "Main content of the medical article"
        },
        {
            "name": "source_url",
            "dataType": ["string"],
            "description": "URL of the source"
        },
        {
            "name": "title",
            "dataType": ["string"],
            "description": "Title of the article"
        }
    ]
}

client.schema.create_class(schema)
print("✓ Created MedicalKnowledge schema")

# Initial medical URLs to ingest
initial_urls = [
    # Mayo Clinic - Common conditions
    "https://www.mayoclinic.org/diseases-conditions/headache/symptoms-causes/syc-20377135",
    "https://www.mayoclinic.org/diseases-conditions/fever/symptoms-causes/syc-20352759",
    "https://www.mayoclinic.org/drugs-supplements/aspirin-oral-route/description/drg-20068907",
    "https://www.mayoclinic.org/diseases-conditions/common-cold/symptoms-causes/syc-20351605",

    # CDC - Basic health
    "https://www.cdc.gov/flu/symptoms/index.html",
    "https://www.cdc.gov/diabetes/basics/diabetes.html",

    # MedlinePlus
    "https://medlineplus.gov/druginfo/meds/a682878.html",  # Aspirin
    "https://medlineplus.gov/ency/article/003090.htm",  # Fever
]

print(f"\nIngesting {len(initial_urls)} medical articles...")
count = ingest_urls_to_weaviate(initial_urls, client)

print(f"\n✅ Setup complete! Ingested {count}/{len(initial_urls)} articles")
print(f"\nTo add more content:")
print(f"  docker-compose exec backend python setup_weaviate.py")