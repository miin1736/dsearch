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
        self.client: Optional[Elasticsearch] = None
        self._initialize_connection()

    def _initialize_connection(self):
        """Elasticsearch 연결을 초기화합니다."""
        try:
            self.client = Elasticsearch(settings.ELASTICSEARCH_URL)
            connections.add_connection('default', self.client)
        except Exception as e:
            logger.error(f"Elasticsearch connection failed: {e}")
            raise

    def get_client(self) -> Elasticsearch:
        """Elasticsearch 클라이언트를 반환합니다."""
        if self.client is None:
            raise RuntimeError("Elasticsearch client not initialized")
        return self.client

    async def health_check(self) -> Dict[str, Any]:
        """Elasticsearch 상태를 확인합니다."""
        try:
            info = self.client.info()
            return {"status": "healthy", "cluster_name": info['cluster_name']}
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def index_document(self, index: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서를 인덱싱합니다."""
        try:
            response = self.client.index(index=index, id=doc_id, document=document)
            return response['result'] == 'created' or response['result'] == 'updated'
        except Exception as e:
            logger.error(f"Document indexing failed: {e}")
            return False

# Global instance
elasticsearch_service = ElasticsearchService()