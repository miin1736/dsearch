"""
Vector Search Service
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from elasticsearch_dsl import Search, Q

from app.core.config import settings
from app.models.search import SearchQuery, SearchResult, DocumentModel, VectorSearchQuery
from app.services.elasticsearch import elasticsearch_service

logger = logging.getLogger("ds")


class VectorService:
    """벡터 검색 및 유사도 서비스 클래스."""

    def __init__(self):
        self.model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)

    async def encode_query(self, query: str) -> List[float]:
        """쿼리를 벡터로 인코딩합니다."""
        try:
            return self.model.encode(query).tolist()
        except Exception as e:
            logger.error(f"Query encoding failed: {e}")
            return []

    async def search_similar(self, vector: List[float], index_name: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """벡터 유사도 검색을 수행합니다."""
        try:
            es_client = elasticsearch_service.get_client()
            search = Search(using=es_client, index=index_name)
            # 벡터 검색 쿼리 구성 (구체적 구현 생략)
            results = search.execute()
            return [hit.to_dict() for hit in results.hits[:top_k]]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def index_documents_for_vector_search(self, source_index: str, target_index: str) -> int:
        """
        문서를 벡터로 변환하여 인덱싱합니다.

        Args:
            source_index: 소스 인덱스명
            target_index: 타겟 벡터 인덱스명

        Returns:
            int: 인덱싱된 문서 수
        """
        try:
            client = elasticsearch_service.get_client()
            query = {"query": {"match_all": {}}, "size": 10000}

            # 소스 문서 검색
            response = client.search(index=source_index, body=query)

            indexed_count = 0
            for hit in response.get("hits", {}).get("hits", []):
                doc_id = hit["_id"]
                source = hit["_source"]
                text = source.get("text", "")

                if text:
                    # 텍스트를 벡터로 변환
                    embeddings = self.model.encode(text)

                    vector_doc = {
                        "full_text": text,
                        "vector": embeddings.tolist(),
                        "created": source.get("created", ""),
                        "category": source.get("category", "")
                    }

                    # 벡터 인덱스에 저장
                    await elasticsearch_service.index_document(
                        index=target_index,
                        doc_id=doc_id,
                        document=vector_doc
                    )

                    indexed_count += 1

            return indexed_count

        except Exception as e:
            logger.error(f"Vector indexing error: {e}")
            return 0

# Global instance
vector_service = VectorService()