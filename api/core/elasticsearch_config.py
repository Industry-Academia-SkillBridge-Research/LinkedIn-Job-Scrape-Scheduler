"""
Elasticsearch configuration and client setup
"""
import logging
from typing import Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from api.core.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Singleton Elasticsearch client"""
    
    _instance: Optional['ElasticsearchClient'] = None
    _client: Optional[Elasticsearch] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Initialize Elasticsearch connection"""
        try:
            # Check if Elasticsearch is enabled
            if not settings.ELASTICSEARCH_ENABLED:
                logger.info("Elasticsearch is disabled in configuration")
                return
            
            # Build connection URL
            es_url = f"{settings.ELASTICSEARCH_SCHEME}://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
            
            logger.info(f"Connecting to Elasticsearch at {es_url}")
            
            # Create client with authentication if provided
            if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
                self._client = Elasticsearch(
                    [es_url],
                    basic_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD),
                    verify_certs=False,
                    request_timeout=30
                )
            else:
                self._client = Elasticsearch(
                    [es_url],
                    verify_certs=False,
                    request_timeout=30
                )
            
            # Test connection
            if self._client.ping():
                logger.info("✅ Successfully connected to Elasticsearch")
                
                # Get cluster info
                info = self._client.info()
                logger.info(f"   Cluster: {info['cluster_name']}")
                logger.info(f"   Version: {info['version']['number']}")
                
                # Setup index
                self._setup_index()
            else:
                logger.error("❌ Failed to connect to Elasticsearch")
                self._client = None
                
        except ESConnectionError as e:
            logger.error(f"❌ Elasticsearch connection error: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"❌ Error initializing Elasticsearch: {e}")
            self._client = None
    
    def _setup_index(self):
        """Create index with mapping if it doesn't exist"""
        try:
            index_name = settings.ELASTICSEARCH_INDEX
            
            if not self._client.indices.exists(index=index_name):
                logger.info(f"Creating index: {index_name}")
                
                # Define mapping for job data
                mapping = {
                    "mappings": {
                        "properties": {
                            "job_id": {"type": "keyword"},
                            "title": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "company": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "location": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "posted_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                            "description": {"type": "text"},
                            "employment_type": {"type": "keyword"},
                            "seniority_level": {"type": "keyword"},
                            "job_function": {"type": "keyword"},
                            "industries": {"type": "keyword"},
                            "apply_url": {"type": "keyword"},
                            "skills": {"type": "keyword"},
                            "salary": {"type": "text"},
                            "scraped_at": {"type": "date"},
                            "country_code": {"type": "keyword"},
                            "job_role": {"type": "keyword"},
                            "source": {"type": "keyword"}
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "custom_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": ["lowercase", "asciifolding"]
                                }
                            }
                        }
                    }
                }
                
                self._client.indices.create(index=index_name, body=mapping)
                logger.info(f"✅ Index '{index_name}' created successfully")
            else:
                logger.info(f"✅ Index '{index_name}' already exists")
                
        except Exception as e:
            logger.error(f"❌ Error setting up index: {e}")
    
    @property
    def client(self) -> Optional[Elasticsearch]:
        """Get Elasticsearch client instance"""
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Elasticsearch"""
        return self._client is not None and self._client.ping()
    
    def reconnect(self):
        """Attempt to reconnect to Elasticsearch"""
        logger.info("Attempting to reconnect to Elasticsearch...")
        self._client = None
        self._connect()
    
    def close(self):
        """Close Elasticsearch connection"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Elasticsearch connection closed")


# Singleton instance
es_client = ElasticsearchClient()


def get_elasticsearch_client() -> Optional[Elasticsearch]:
    """
    Get Elasticsearch client instance
    
    Returns:
        Elasticsearch client or None if not connected
    """
    return es_client.client
