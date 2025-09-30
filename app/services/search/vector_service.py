"""
Vector Search Service
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from elasticsearch_dsl import Search, Q
import logging

from app.core.config import settings
from app.models.search import SearchQuery, SearchResult, DocumentModel, VectorSearchQuery
from app.services.elasticsearch import elasticsearch_service

logger = logging.getLogger("ds")


class VectorService:
    """Vector search and similarity service."""

    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.index_name = "ds_content"

    def _get_model(self) -> SentenceTransformer:
        """Get or initialize the sentence transformer model."""
        if self.model is None:
            try:
                self.model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
                logger.info(f"Loaded sentence transformer model: {settings.SENTENCE_TRANSFORMER_MODEL}")
            except Exception as e:
                logger.error(f"Failed to load sentence transformer model: {e}")
                # Fallback to a smaller model
                self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

        return self.model

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text."""
        try:
            model = self._get_model()
            embedding = model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for multiple texts."""
        try:
            model = self._get_model()
            embeddings = model.encode(texts, convert_to_tensor=False, batch_size=32)
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return []

    async def vector_search(self, query: SearchQuery) -> SearchResult:
        """Perform vector similarity search."""
        start_time = time.time()

        try:
            # Generate query vector
            query_vector = await self.generate_embedding(query.query)
            if not query_vector:
                raise Exception("Failed to generate query vector")

            # Configure elasticsearch connections
            elasticsearch_service.configure_connections()

            # Create vector search query
            search = Search(index=self.index_name)

            # KNN query for vector similarity
            knn_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": query_vector}
                    }
                }
            }

            # Apply minimum score threshold
            if query.vector_threshold:
                knn_query["script_score"]["min_score"] = query.vector_threshold

            search = search.query(knn_query)

            # Apply filters (same as text search)
            search = await self._apply_filters(search, query)

            # Apply pagination
            search = search[query.skip:query.skip + query.size]

            # Execute search
            response = search.execute()

            # Process results
            documents = []
            for hit in response.hits:
                doc = await self._process_hit(hit, query)
                documents.append(doc)

            # Calculate total pages
            total_pages = (response.hits.total.value + query.size - 1) // query.size

            # Create result
            result = SearchResult(
                query=query.query,
                search_type=query.search_type,
                total_hits=response.hits.total.value,
                max_score=response.hits.max_score,
                took_ms=int((time.time() - start_time) * 1000),
                documents=documents,
                facets=[],  # Vector search typically doesn't use facets
                page=query.page,
                size=query.size,
                total_pages=total_pages
            )

            return result

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return SearchResult(
                query=query.query,
                search_type=query.search_type,
                total_hits=0,
                max_score=None,
                took_ms=int((time.time() - start_time) * 1000),
                documents=[],
                facets=[],
                page=query.page,
                size=query.size,
                total_pages=0
            )

    async def find_similar_documents(self, document_id: str, k: int = 10, threshold: float = 0.7) -> List[DocumentModel]:
        """Find documents similar to a given document."""
        try:
            # Get the source document
            client = elasticsearch_service.get_client()
            doc_response = client.get(index=self.index_name, id=document_id)

            if 'vector' not in doc_response['_source']:
                logger.warning(f"Document {document_id} has no vector embedding")
                return []

            source_vector = doc_response['_source']['vector']

            # Search for similar documents
            search = Search(index=self.index_name)

            similarity_query = {
                "script_score": {
                    "query": {
                        "bool": {
                            "must_not": [
                                {"term": {"_id": document_id}}  # Exclude source document
                            ]
                        }
                    },
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": source_vector}
                    },
                    "min_score": threshold
                }
            }

            search = search.query(similarity_query)
            search = search[:k]

            response = search.execute()

            # Process results
            similar_docs = []
            for hit in response.hits:
                doc = DocumentModel(
                    id=hit.meta.id,
                    title=getattr(hit, 'title', ''),
                    filename=getattr(hit, 'filename', ''),
                    category0=getattr(hit, 'category0', None),
                    category1=getattr(hit, 'category1', None),
                    score=hit.meta.score
                )
                similar_docs.append(doc)

            return similar_docs

        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []

    async def update_document_vector(self, document_id: str, text: str) -> bool:
        """Update vector embedding for a document."""
        try:
            # Generate vector
            vector = await self.generate_embedding(text)
            if not vector:
                return False

            # Update document
            client = elasticsearch_service.get_client()
            client.update(
                index=self.index_name,
                id=document_id,
                body={
                    "doc": {
                        "vector": vector
                    }
                }
            )

            logger.info(f"Updated vector for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating document vector: {e}")
            return False

    async def _apply_filters(self, search: Search, query: SearchQuery) -> Search:
        """Apply filters to vector search (same as text search)."""
        filters = []

        # Category filters
        if query.categories:
            category_filters = []
            for category in query.categories:
                category_filters.extend([
                    Q('term', category0=category),
                    Q('term', category1=category),
                    Q('term', category2=category)
                ])
            if category_filters:
                filters.append(Q('bool', should=category_filters))

        # Date range filter
        if query.date_from or query.date_to:
            date_filter = {}
            if query.date_from:
                date_filter['gte'] = query.date_from
            if query.date_to:
                date_filter['lte'] = query.date_to
            filters.append(Q('range', created_date=date_filter))

        # File type filters
        if query.file_types:
            filters.append(Q('terms', file_type=query.file_types))

        # Apply filters to the inner query
        if filters:
            # This is more complex for script_score queries
            # We need to modify the inner query
            pass

        return search

    async def _process_hit(self, hit, query: SearchQuery) -> DocumentModel:
        """Process search hit into DocumentModel."""
        doc = DocumentModel(
            id=hit.meta.id,
            title=getattr(hit, 'title', ''),
            filename=getattr(hit, 'filename', ''),
            content=getattr(hit, 'text', None),
            file_path=getattr(hit, 'file_path', None),
            file_size=getattr(hit, 'file_size', None),
            file_type=getattr(hit, 'file_type', None),
            category0=getattr(hit, 'category0', None),
            category1=getattr(hit, 'category1', None),
            category2=getattr(hit, 'category2', None),
            created_date=getattr(hit, 'created_date', None),
            modified_date=getattr(hit, 'modified_date', None),
            score=hit.meta.score,
            vector=getattr(hit, 'vector', None)
        )

        return doc

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        try:
            model = self._get_model()
            embeddings = model.encode([text1, text2])

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0


# Global instance
vector_service = VectorService()