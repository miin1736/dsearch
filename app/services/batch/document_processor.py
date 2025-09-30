"""
Document Processing Service for Batch Operations
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import mimetypes
import logging
from datetime import datetime

from app.core.config import settings
from app.services.elasticsearch import elasticsearch_service
from app.services.search.vector_service import vector_service
from app.utils.file_handler import FileHandler
from app.utils.text_extractor import TextExtractor

logger = logging.getLogger("batch")


class DocumentProcessor:
    """Service for processing documents in batch operations."""

    def __init__(self):
        self.file_handler = FileHandler()
        self.text_extractor = TextExtractor()

    async def index_document(self, file_path: str, document_id: Optional[str] = None,
                           category: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                           generate_vector: bool = True) -> Dict[str, Any]:
        """Index a single document."""
        try:
            if not self.file_handler.file_exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Generate document ID if not provided
            if not document_id:
                document_id = self.file_handler.generate_document_id(file_path)

            # Extract file information
            file_info = await self.file_handler.get_file_info(file_path)

            # Extract text content
            text_content = await self.text_extractor.extract_text(file_path)
            if not text_content:
                logger.warning(f"No text content extracted from {file_path}")

            # Prepare document data
            document_data = {
                "id": document_id,
                "title": file_info["name"],
                "filename": file_info["filename"],
                "text": text_content,
                "file_path": file_path,
                "file_size": file_info["size"],
                "file_type": file_info["type"],
                "created_date": file_info["created"].isoformat(),
                "modified_date": file_info["modified"].isoformat(),
                "indexed_date": datetime.utcnow().isoformat(),
            }

            # Add category information
            if category:
                document_data["category0"] = category
            else:
                # Try to extract category from file path
                category_parts = Path(file_path).parts
                if len(category_parts) >= 2:
                    document_data["category0"] = category_parts[-2]

            # Add metadata
            if metadata:
                document_data.update(metadata)

            # Generate vector embedding if requested
            if generate_vector and text_content:
                vector = await vector_service.generate_embedding(text_content)
                if vector:
                    document_data["vector"] = vector

            # Index document
            client = elasticsearch_service.get_client()
            response = client.index(
                index="ds_content",
                id=document_id,
                body=document_data,
                refresh=True
            )

            logger.info(f"Indexed document {document_id}: {file_path}")

            return {
                "success": True,
                "document_id": document_id,
                "indexed_at": document_data["indexed_date"],
                "file_size": file_info["size"],
                "has_vector": bool(vector) if generate_vector else False
            }

        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }

    async def bulk_index_documents(self, source_path: str, index_name: str = "ds_content",
                                 batch_size: int = 100, include_patterns: Optional[List[str]] = None,
                                 exclude_patterns: Optional[List[str]] = None,
                                 overwrite_existing: bool = False, generate_vectors: bool = True,
                                 progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Bulk index documents from a directory."""
        try:
            # Find all files to process
            files = await self._find_files_to_process(
                source_path, include_patterns, exclude_patterns
            )

            if not files:
                return {
                    "success": True,
                    "message": "No files found to process",
                    "processed_count": 0,
                    "failed_count": 0
                }

            logger.info(f"Found {len(files)} files to process in {source_path}")

            # Process files in batches
            total_files = len(files)
            processed_count = 0
            failed_count = 0
            failed_files = []

            for i in range(0, total_files, batch_size):
                batch_files = files[i:i + batch_size]
                batch_documents = []

                # Process batch
                for file_path in batch_files:
                    try:
                        # Check if document already exists
                        document_id = self.file_handler.generate_document_id(file_path)

                        if not overwrite_existing:
                            client = elasticsearch_service.get_client()
                            if client.exists(index=index_name, id=document_id):
                                logger.info(f"Skipping existing document: {file_path}")
                                continue

                        # Process document
                        result = await self.index_document(
                            file_path=file_path,
                            document_id=document_id,
                            generate_vector=generate_vectors
                        )

                        if result["success"]:
                            processed_count += 1
                        else:
                            failed_count += 1
                            failed_files.append(file_path)

                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
                        failed_count += 1
                        failed_files.append(file_path)

                # Update progress
                if progress_callback:
                    progress = int((processed_count + failed_count) / total_files * 100)
                    progress_callback(progress)

                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)

            # Refresh index
            await elasticsearch_service.refresh_index(index_name)

            result = {
                "success": True,
                "total_files": total_files,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "failed_files": failed_files[:10],  # Limit to first 10 failed files
                "index_name": index_name
            }

            logger.info(f"Bulk indexing completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in bulk indexing: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def regenerate_vectors(self, index_name: str = "ds_content",
                               batch_size: int = 100) -> Dict[str, Any]:
        """Regenerate vector embeddings for existing documents."""
        try:
            client = elasticsearch_service.get_client()

            # Search for documents without vectors or to update all vectors
            search_body = {
                "query": {"match_all": {}},
                "_source": ["text", "title"],
                "size": batch_size
            }

            processed_count = 0
            failed_count = 0
            scroll_id = None

            # Use scroll API for large datasets
            response = client.search(
                index=index_name,
                body=search_body,
                scroll="5m"
            )

            scroll_id = response.get("_scroll_id")
            hits = response["hits"]["hits"]

            while hits:
                batch_updates = []

                for hit in hits:
                    try:
                        document_id = hit["_id"]
                        source = hit["_source"]

                        # Get text content for vector generation
                        text = source.get("text", "")
                        if not text:
                            text = source.get("title", "")

                        if text:
                            # Generate vector
                            vector = await vector_service.generate_embedding(text)
                            if vector:
                                batch_updates.append({
                                    "update": {
                                        "_index": index_name,
                                        "_id": document_id
                                    }
                                })
                                batch_updates.append({
                                    "doc": {
                                        "vector": vector,
                                        "vector_updated_at": datetime.utcnow().isoformat()
                                    }
                                })
                                processed_count += 1
                            else:
                                failed_count += 1
                        else:
                            failed_count += 1

                    except Exception as e:
                        logger.error(f"Error processing document {hit['_id']}: {e}")
                        failed_count += 1

                # Bulk update vectors
                if batch_updates:
                    try:
                        client.bulk(body=batch_updates, refresh=True)
                        logger.info(f"Updated vectors for {len(batch_updates)//2} documents")
                    except Exception as e:
                        logger.error(f"Error in bulk vector update: {e}")
                        failed_count += len(batch_updates) // 2

                # Get next batch
                if scroll_id:
                    response = client.scroll(scroll_id=scroll_id, scroll="5m")
                    hits = response["hits"]["hits"]
                else:
                    break

            # Clear scroll
            if scroll_id:
                client.clear_scroll(scroll_id=scroll_id)

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "index_name": index_name
            }

        except Exception as e:
            logger.error(f"Error regenerating vectors: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_document(self, document_id: str, index_name: str = "ds_content") -> Dict[str, Any]:
        """Delete a document from the index."""
        try:
            client = elasticsearch_service.get_client()

            response = client.delete(
                index=index_name,
                id=document_id,
                refresh=True
            )

            logger.info(f"Deleted document {document_id} from {index_name}")

            return {
                "success": True,
                "document_id": document_id,
                "result": response["result"]
            }

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }

    async def _find_files_to_process(self, source_path: str, include_patterns: Optional[List[str]],
                                   exclude_patterns: Optional[List[str]]) -> List[str]:
        """Find files to process based on patterns."""
        files = []

        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source path not found: {source_path}")

        # Default include patterns for common document types
        if not include_patterns:
            include_patterns = ["*.pdf", "*.doc", "*.docx", "*.txt", "*.html", "*.htm"]

        # Default exclude patterns
        if not exclude_patterns:
            exclude_patterns = [".*", "*~", "*.tmp", "*.temp"]

        # Walk through directory
        for root, dirs, filenames in os.walk(source_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)

                # Check include patterns
                include_match = False
                for pattern in include_patterns:
                    if self._match_pattern(filename, pattern):
                        include_match = True
                        break

                if not include_match:
                    continue

                # Check exclude patterns
                exclude_match = False
                for pattern in exclude_patterns:
                    if self._match_pattern(filename, pattern):
                        exclude_match = True
                        break

                if exclude_match:
                    continue

                files.append(file_path)

        return sorted(files)

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching for file inclusion/exclusion."""
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), pattern.lower())