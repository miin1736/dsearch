"""
Main Search Service
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, A
import re
import logging

from app.core.config import settings
from app.models.search import SearchQuery, SearchResult, DocumentModel, FacetAggregation, FacetItem
from app.services.elasticsearch import elasticsearch_service
from .text_analyzer import TextAnalyzer
from .highlighter import HighlightService

logger = logging.getLogger("ds")


class SearchService:
    """Main search service for handling text and hybrid searches."""

    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.highlighter = HighlightService()
        self.index_name = "ds_content"

    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform search based on query type."""
        start_time = time.time()

        try:
            # Configure elasticsearch connections
            elasticsearch_service.configure_connections()

            # Create elasticsearch-dsl Search object
            search = Search(index=self.index_name)

            # Build query based on search type
            if query.search_type == "vector":
                # Vector search will be handled by VectorService
                from .vector_service import VectorService
                vector_service = VectorService()
                return await vector_service.vector_search(query)
            elif query.search_type == "hybrid":
                search = await self._build_hybrid_query(search, query)
            else:
                search = await self._build_text_query(search, query)

            # Apply filters
            search = await self._apply_filters(search, query)

            # Apply sorting
            search = await self._apply_sorting(search, query)

            # Apply pagination
            search = search[query.skip:query.skip + query.size]

            # Add aggregations for facets
            search = await self._add_aggregations(search)

            # Add highlighting
            if query.highlight:
                search = await self._add_highlighting(search, query)

            # Execute search
            response = search.execute()

            # Process results
            documents = []
            for hit in response.hits:
                doc = await self._process_hit(hit, query)
                documents.append(doc)

            # Process facets
            facets = await self._process_facets(response.aggregations) if hasattr(response, 'aggregations') else []

            # Get suggestions if needed
            suggestions = []
            typo_corrections = []
            auto_completions = []

            if query.typo_correction:
                typo_corrections = await self._get_typo_corrections(query.query)
            if query.auto_complete:
                auto_completions = await self._get_auto_completions(query.query)

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
                facets=facets,
                suggestions=suggestions,
                typo_corrections=typo_corrections,
                auto_completions=auto_completions,
                page=query.page,
                size=query.size,
                total_pages=total_pages
            )

            # Log search
            await self._log_search(query, result)

            return result

        except Exception as e:
            logger.error(f"Search error: {e}")
            # Return empty result on error
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

    async def get_document_by_id(self, document_id: str) -> Optional[DocumentModel]:
        """Get document by ID."""
        try:
            client = elasticsearch_service.get_client()
            response = client.get(index=self.index_name, id=document_id)

            if response['found']:
                source = response['_source']
                return DocumentModel(
                    id=document_id,
                    title=source.get('title', ''),
                    filename=source.get('filename', ''),
                    content=source.get('text', ''),
                    html_content=source.get('html_content', ''),
                    file_path=source.get('file_path', ''),
                    file_size=source.get('file_size'),
                    file_type=source.get('file_type', ''),
                    category0=source.get('category0', ''),
                    category1=source.get('category1', ''),
                    category2=source.get('category2', ''),
                    created_date=source.get('created_date', ''),
                    modified_date=source.get('modified_date', '')
                )

            return None

        except Exception as e:
            logger.error(f"Error getting document {document_id}: {e}")
            return None

    async def get_categories(self) -> List[str]:
        """Get available document categories."""
        try:
            client = elasticsearch_service.get_client()

            # Aggregate categories
            search_body = {
                "size": 0,
                "aggs": {
                    "categories": {
                        "terms": {
                            "field": "category0.keyword",
                            "size": 1000
                        }
                    }
                }
            }

            response = client.search(index=self.index_name, body=search_body)

            categories = []
            if "aggregations" in response:
                for bucket in response["aggregations"]["categories"]["buckets"]:
                    categories.append(bucket["key"])

            return sorted(categories)

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    async def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        try:
            # This would typically query actual search logs
            # For now, return basic index stats
            stats = await elasticsearch_service.get_index_stats(self.index_name)

            return {
                "total_documents": stats.get("document_count", 0) if stats else 0,
                "index_size": stats.get("store_size_bytes", 0) if stats else 0
            }

        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}

    async def export_results(self, documents: List[DocumentModel], format_type: str) -> bytes:
        """Export search results to various formats."""
        try:
            if format_type == "csv":
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)

                # Write header
                writer.writerow(['Title', 'Filename', 'Category', 'File Type', 'Score'])

                # Write data
                for doc in documents:
                    writer.writerow([
                        doc.title,
                        doc.filename,
                        doc.category0 or '',
                        doc.file_type or '',
                        doc.score or 0
                    ])

                return output.getvalue().encode('utf-8')

            elif format_type == "json":
                import json

                data = []
                for doc in documents:
                    data.append({
                        'id': doc.id,
                        'title': doc.title,
                        'filename': doc.filename,
                        'category': doc.category0,
                        'file_type': doc.file_type,
                        'score': doc.score
                    })

                return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

            else:
                raise ValueError(f"Unsupported export format: {format_type}")

        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            raise

    async def _build_text_query(self, search: Search, query: SearchQuery) -> Search:
        """Build text search query."""
        # Get search fields
        search_fields = query.fields or settings.SEARCH_FIELDS

        # Analyze query text
        analyzed_query = await self.text_analyzer.analyze_query(query.query)

        if query.fuzzy:
            # Fuzzy query
            q = Q('multi_match',
                query=analyzed_query,
                fields=search_fields,
                type='best_fields',
                fuzziness='AUTO'
            )
        else:
            # Regular multi-match query
            q = Q('multi_match',
                query=analyzed_query,
                fields=search_fields,
                type='best_fields',
                operator='and'
            )

            # Add phrase matching boost
            phrase_q = Q('multi_match',
                query=analyzed_query,
                fields=search_fields,
                type='phrase',
                boost=1.5
            )

            q = q | phrase_q

        # Apply time-based boosting
        q = await self._apply_time_boosting(q)

        return search.query(q)

    async def _build_hybrid_query(self, search: Search, query: SearchQuery) -> Search:
        """Build hybrid text + vector search query."""
        # This is a placeholder - actual hybrid search would combine
        # text search with vector similarity
        return await self._build_text_query(search, query)

    async def _apply_filters(self, search: Search, query: SearchQuery) -> Search:
        """Apply filters to search query."""
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

        # Apply filters
        if filters:
            search = search.filter('bool', must=filters)

        return search

    async def _apply_sorting(self, search: Search, query: SearchQuery) -> Search:
        """Apply sorting to search query."""
        if query.sort_field:
            sort_field = query.sort_field
            if query.sort_order == "desc":
                sort_field = f"-{sort_field}"
            search = search.sort(sort_field)
        else:
            # Default sort by relevance score
            search = search.sort('_score')

        return search

    async def _add_aggregations(self, search: Search) -> Search:
        """Add aggregations for faceted search."""
        # Category facets
        search.aggs.bucket('categories', 'terms', field='category0.keyword', size=20)

        # File type facets
        search.aggs.bucket('file_types', 'terms', field='file_type.keyword', size=10)

        # Date histogram
        search.aggs.bucket(
            'date_histogram',
            'date_histogram',
            field='created_date',
            calendar_interval='month',
            format='yyyy-MM'
        )

        return search

    async def _add_highlighting(self, search: Search, query: SearchQuery) -> Search:
        """Add highlighting to search query."""
        highlight_fields = {
            'title': {
                'pre_tags': ["<span style='color: rgb(216, 90, 100)'>"],
                'post_tags': ["</span>"],
                'fragment_size': 150,
                'number_of_fragments': 3
            },
            'text': {
                'pre_tags': ["<span style='color: rgb(216, 90, 100)'>"],
                'post_tags': ["</span>"],
                'fragment_size': 150,
                'number_of_fragments': 3
            }
        }

        search = search.highlight_options(
            require_field_match=False,
            fragment_size=150,
            number_of_fragments=3
        )

        for field, options in highlight_fields.items():
            search = search.highlight(field, **options)

        return search

    async def _apply_time_boosting(self, query: Q) -> Q:
        """Apply time-based boosting to queries."""
        # Boost recent documents
        time_boost = Q('function_score',
            query=query,
            functions=[
                {
                    'filter': Q('range', created_date={'gte': 'now-1y'}),
                    'weight': 1.1
                },
                {
                    'filter': Q('range', created_date={'gte': 'now-2y', 'lt': 'now-1y'}),
                    'weight': 1.08
                },
                {
                    'filter': Q('range', created_date={'gte': 'now-3y', 'lt': 'now-2y'}),
                    'weight': 1.05
                }
            ],
            score_mode='multiply',
            boost_mode='multiply'
        )

        return time_boost

    async def _process_hit(self, hit, query: SearchQuery) -> DocumentModel:
        """Process search hit into DocumentModel."""
        # Extract highlights
        highlights = []
        if hasattr(hit.meta, 'highlight'):
            for field, fragments in hit.meta.highlight.to_dict().items():
                highlights.append({
                    'field': field,
                    'fragments': fragments
                })

        # Create document model
        doc = DocumentModel(
            id=hit.meta.id,
            title=getattr(hit, 'title', ''),
            filename=getattr(hit, 'filename', ''),
            content=getattr(hit, 'text', None),
            html_content=getattr(hit, 'html_content', None),
            file_path=getattr(hit, 'file_path', None),
            file_size=getattr(hit, 'file_size', None),
            file_type=getattr(hit, 'file_type', None),
            category0=getattr(hit, 'category0', None),
            category1=getattr(hit, 'category1', None),
            category2=getattr(hit, 'category2', None),
            created_date=getattr(hit, 'created_date', None),
            modified_date=getattr(hit, 'modified_date', None),
            score=hit.meta.score,
            highlights=highlights
        )

        return doc

    async def _process_facets(self, aggregations) -> List[FacetAggregation]:
        """Process aggregations into facets."""
        facets = []

        # Categories facet
        if 'categories' in aggregations:
            items = []
            for bucket in aggregations.categories.buckets:
                items.append(FacetItem(key=bucket.key, count=bucket.doc_count))
            facets.append(FacetAggregation(name='categories', items=items))

        # File types facet
        if 'file_types' in aggregations:
            items = []
            for bucket in aggregations.file_types.buckets:
                items.append(FacetItem(key=bucket.key, count=bucket.doc_count))
            facets.append(FacetAggregation(name='file_types', items=items))

        return facets

    async def _get_typo_corrections(self, query: str) -> List[str]:
        """Get typo corrections for query."""
        # This is a placeholder - actual implementation would use
        # Elasticsearch suggest API or external service
        return []

    async def _get_auto_completions(self, query: str) -> List[str]:
        """Get auto-completions for query."""
        # This is a placeholder - actual implementation would use
        # completion suggester
        return []

    async def _log_search(self, query: SearchQuery, result: SearchResult):
        """Log search query and results."""
        try:
            log_data = {
                'query': query.query,
                'search_type': query.search_type.value,
                'total_hits': result.total_hits,
                'took_ms': result.took_ms,
                'timestamp': time.time()
            }
            logger.info(f"Search performed: {log_data}")
        except Exception as e:
            logger.error(f"Failed to log search: {e}")


# Global instance
search_service = SearchService()