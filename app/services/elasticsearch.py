"""
Elasticsearch Connection and Basic Operations
"""

from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch_dsl import connections
import logging

from app.core.config import settings

logger = logging.getLogger("ds")


class ElasticsearchService:
    """Elasticsearch service for managing connections and basic operations."""

    def __init__(self):
        self._client: Optional[Elasticsearch] = None
        self._connections_configured = False

    def get_client(self) -> Elasticsearch:
        """Get Elasticsearch client instance."""
        if not self._client:
            self._client = Elasticsearch(
                settings.ELASTICSEARCH_URLS,
                http_auth=(
                    settings.ELASTICSEARCH_USERNAME,
                    settings.ELASTICSEARCH_PASSWORD
                ),
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS,
                timeout=settings.ELASTICSEARCH_TIMEOUT,
                retry_on_timeout=True,
                max_retries=3
            )
        return self._client

    def configure_connections(self):
        """Configure elasticsearch-dsl connections."""
        if not self._connections_configured:
            connections.create_connection(
                hosts=settings.ELASTICSEARCH_URLS,
                http_auth=(
                    settings.ELASTICSEARCH_USERNAME,
                    settings.ELASTICSEARCH_PASSWORD
                ),
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS,
                timeout=settings.ELASTICSEARCH_TIMEOUT
            )
            self._connections_configured = True

    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health."""
        try:
            client = self.get_client()
            health = client.cluster.health()
            return {
                "status": "healthy" if health["status"] in ["green", "yellow"] else "unhealthy",
                "cluster_name": health["cluster_name"],
                "status_detail": health["status"],
                "number_of_nodes": health["number_of_nodes"],
                "number_of_data_nodes": health["number_of_data_nodes"],
                "active_primary_shards": health["active_primary_shards"],
                "active_shards": health["active_shards"],
            }
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def create_index(self, index_name: str, mappings: Dict[str, Any], settings_dict: Optional[Dict[str, Any]] = None) -> bool:
        """Create an index with mappings and settings."""
        try:
            client = self.get_client()

            body = {"mappings": mappings}
            if settings_dict:
                body["settings"] = settings_dict

            response = client.indices.create(
                index=index_name,
                body=body,
                ignore=[400]  # Ignore if index already exists
            )

            if "error" in response:
                if response["error"]["type"] == "resource_already_exists_exception":
                    logger.warning(f"Index {index_name} already exists")
                    return True
                else:
                    logger.error(f"Failed to create index {index_name}: {response['error']}")
                    return False

            logger.info(f"Created index {index_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            return False

    async def delete_index(self, index_name: str) -> bool:
        """Delete an index."""
        try:
            client = self.get_client()
            client.indices.delete(index=index_name, ignore=[404])
            logger.info(f"Deleted index {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
            return False

    async def index_exists(self, index_name: str) -> bool:
        """Check if index exists."""
        try:
            client = self.get_client()
            return client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Error checking index existence {index_name}: {e}")
            return False

    async def refresh_index(self, index_name: str) -> bool:
        """Refresh an index."""
        try:
            client = self.get_client()
            client.indices.refresh(index=index_name)
            logger.info(f"Refreshed index {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error refreshing index {index_name}: {e}")
            return False

    async def get_index_stats(self, index_name: str) -> Optional[Dict[str, Any]]:
        """Get index statistics."""
        try:
            client = self.get_client()
            response = client.indices.stats(index=index_name)
            if index_name in response["indices"]:
                stats = response["indices"][index_name]
                return {
                    "document_count": stats["total"]["docs"]["count"],
                    "deleted_docs": stats["total"]["docs"]["deleted"],
                    "store_size_bytes": stats["total"]["store"]["size_in_bytes"],
                    "segments_count": stats["total"]["segments"]["count"]
                }
        except Exception as e:
            logger.error(f"Error getting index stats {index_name}: {e}")
        return None

    async def bulk_index(self, index_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk index documents."""
        try:
            client = self.get_client()

            # Prepare bulk body
            body = []
            for doc in documents:
                body.append({
                    "index": {
                        "_index": index_name,
                        "_id": doc.get("id")
                    }
                })
                body.append(doc)

            response = client.bulk(body=body, refresh=True)

            # Analyze response
            success_count = 0
            error_count = 0
            errors = []

            for item in response["items"]:
                if "index" in item:
                    if item["index"].get("status") in [200, 201]:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(item["index"].get("error"))

            return {
                "success": error_count == 0,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors,
                "took": response["took"]
            }

        except Exception as e:
            logger.error(f"Error bulk indexing to {index_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
elasticsearch_service = ElasticsearchService()