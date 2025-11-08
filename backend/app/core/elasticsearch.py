"""
Elasticsearch Configuration
Sprint 13: Search & Discovery System

Elasticsearch client setup and document mappings.
"""

from elasticsearch import AsyncElasticsearch
from typing import Optional, Dict, Any
import os


# ============================================================================
# Elasticsearch Client
# ============================================================================

class ElasticsearchClient:
    """Singleton Elasticsearch client"""

    _instance: Optional[AsyncElasticsearch] = None

    @classmethod
    def get_client(cls) -> AsyncElasticsearch:
        """Get or create Elasticsearch client"""
        if cls._instance is None:
            # Get configuration from environment
            es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
            es_port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
            es_user = os.getenv("ELASTICSEARCH_USER")
            es_password = os.getenv("ELASTICSEARCH_PASSWORD")

            # Create client
            if es_user and es_password:
                cls._instance = AsyncElasticsearch(
                    hosts=[f"http://{es_host}:{es_port}"],
                    basic_auth=(es_user, es_password),
                    request_timeout=30,
                    max_retries=3,
                    retry_on_timeout=True
                )
            else:
                cls._instance = AsyncElasticsearch(
                    hosts=[f"http://{es_host}:{es_port}"],
                    request_timeout=30,
                    max_retries=3,
                    retry_on_timeout=True
                )

        return cls._instance

    @classmethod
    async def close(cls):
        """Close Elasticsearch client"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


# ============================================================================
# Document Mappings
# ============================================================================

VENDOR_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "autocomplete_filter"]
                },
                "search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"]
                }
            },
            "filter": {
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20
                }
            }
        },
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "business_name": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "search_analyzer": "search_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {
                        "type": "completion"
                    }
                }
            },
            "description": {
                "type": "text",
                "analyzer": "standard"
            },
            "category": {"type": "keyword"},
            "subcategories": {"type": "keyword"},
            "services": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "price": {"type": "float"},
                    "category": {"type": "keyword"}
                }
            },
            "location": {
                "type": "geo_point"
            },
            "city": {"type": "keyword"},
            "region": {"type": "keyword"},
            "country": {"type": "keyword"},
            "address": {"type": "text"},
            "rating": {"type": "float"},
            "review_count": {"type": "integer"},
            "verified": {"type": "boolean"},
            "featured": {"type": "boolean"},
            "price_range": {"type": "keyword"},
            "availability_status": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "languages": {"type": "keyword"},
            "years_experience": {"type": "integer"},
            "portfolio_items": {
                "type": "nested",
                "properties": {
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "tags": {"type": "keyword"}
                }
            },
            "certifications": {"type": "keyword"},
            "team_size": {"type": "integer"},
            "instant_booking": {"type": "boolean"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "is_active": {"type": "boolean"}
        }
    }
}


EVENT_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "autocomplete_filter"]
                }
            },
            "filter": {
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20
                }
            }
        },
        "index": {
            "number_of_shards": 2,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"}
                }
            },
            "description": {"type": "text"},
            "event_type": {"type": "keyword"},
            "status": {"type": "keyword"},
            "organizer_id": {"type": "keyword"},
            "organizer_name": {"type": "text"},
            "event_date": {"type": "date"},
            "venue_name": {"type": "text"},
            "location": {"type": "geo_point"},
            "city": {"type": "keyword"},
            "region": {"type": "keyword"},
            "country": {"type": "keyword"},
            "guest_count": {"type": "integer"},
            "budget_total": {"type": "float"},
            "cultural_elements": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "is_public": {"type": "boolean"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }
}


SERVICE_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "autocomplete_filter"]
                }
            },
            "filter": {
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20
                }
            }
        },
        "index": {
            "number_of_shards": 2,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "vendor_id": {"type": "keyword"},
            "vendor_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "service_name": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"}
                }
            },
            "description": {"type": "text"},
            "category": {"type": "keyword"},
            "subcategory": {"type": "keyword"},
            "price": {"type": "float"},
            "price_type": {"type": "keyword"},
            "duration": {"type": "integer"},
            "duration_unit": {"type": "keyword"},
            "capacity": {"type": "integer"},
            "tags": {"type": "keyword"},
            "is_featured": {"type": "boolean"},
            "is_available": {"type": "boolean"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

async def create_index_if_not_exists(
    client: AsyncElasticsearch,
    index_name: str,
    mapping: Dict[str, Any]
) -> bool:
    """Create an index if it doesn't exist"""
    try:
        exists = await client.indices.exists(index=index_name)
        if not exists:
            await client.indices.create(index=index_name, body=mapping)
            return True
        return False
    except Exception as e:
        print(f"Error creating index {index_name}: {str(e)}")
        return False


async def delete_index(client: AsyncElasticsearch, index_name: str) -> bool:
    """Delete an index"""
    try:
        exists = await client.indices.exists(index=index_name)
        if exists:
            await client.indices.delete(index=index_name)
            return True
        return False
    except Exception as e:
        print(f"Error deleting index {index_name}: {str(e)}")
        return False


async def initialize_indices():
    """Initialize all search indices"""
    client = ElasticsearchClient.get_client()

    # Create indices
    await create_index_if_not_exists(client, "vendors", VENDOR_INDEX_MAPPING)
    await create_index_if_not_exists(client, "events", EVENT_INDEX_MAPPING)
    await create_index_if_not_exists(client, "services", SERVICE_INDEX_MAPPING)


# ============================================================================
# Index Names
# ============================================================================

INDEX_VENDORS = "vendors"
INDEX_EVENTS = "events"
INDEX_SERVICES = "services"
