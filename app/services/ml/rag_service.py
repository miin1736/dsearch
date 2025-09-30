"""
RAG (Retrieval-Augmented Generation) Service
"""

from typing import List, Dict, Any, Optional
import logging

from app.models.search import SearchQuery, SearchType
from app.services.search.search_service import search_service
from app.services.search.vector_service import vector_service
from .openai_service import openai_service

logger = logging.getLogger("ds")


class RAGService:
    """Service for Retrieval-Augmented Generation using search results and GPT."""

    def __init__(self):
        self.search_service = search_service
        self.vector_service = vector_service
        self.openai_service = openai_service

    async def ask_question(self, question: str, search_type: SearchType = SearchType.HYBRID,
                          max_documents: int = 5, context_length: int = 4000) -> Dict[str, Any]:
        """
        Answer a question using RAG approach:
        1. Retrieve relevant documents using search
        2. Use documents as context for GPT generation
        """
        try:
            if not await self.openai_service.is_available():
                return {
                    "success": False,
                    "error": "AI service not available",
                    "answer": None
                }

            # Step 1: Retrieve relevant documents
            search_query = SearchQuery(
                query=question,
                search_type=search_type,
                size=max_documents,
                highlight=True
            )

            search_result = await self.search_service.search(search_query)

            if not search_result.documents:
                return {
                    "success": True,
                    "answer": "죄송하지만, 질문과 관련된 문서를 찾을 수 없습니다.",
                    "sources": [],
                    "search_results": search_result
                }

            # Step 2: Prepare context from search results
            context_documents = []
            for doc in search_result.documents:
                context_documents.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content or "",
                    "score": doc.score,
                    "highlights": doc.highlights
                })

            # Step 3: Generate answer using GPT with context
            answer = await self.openai_service.answer_question_with_context(
                question=question,
                documents=context_documents,
                max_context_length=context_length
            )

            if not answer:
                return {
                    "success": False,
                    "error": "Failed to generate answer",
                    "answer": None,
                    "sources": context_documents,
                    "search_results": search_result
                }

            return {
                "success": True,
                "answer": answer,
                "sources": context_documents,
                "search_results": search_result,
                "metadata": {
                    "question": question,
                    "search_type": search_type.value,
                    "documents_used": len(context_documents),
                    "total_search_results": search_result.total_hits
                }
            }

        except Exception as e:
            logger.error(f"Error in RAG question answering: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": None
            }

    async def ask_question_streaming(self, question: str, search_type: SearchType = SearchType.HYBRID,
                                   max_documents: int = 5, context_length: int = 4000):
        """
        Answer a question using RAG with streaming response.
        """
        try:
            if not await self.openai_service.is_available():
                yield {"type": "error", "data": "AI service not available"}
                return

            # Step 1: Retrieve relevant documents
            yield {"type": "status", "data": "문서를 검색하고 있습니다..."}

            search_query = SearchQuery(
                query=question,
                search_type=search_type,
                size=max_documents,
                highlight=True
            )

            search_result = await self.search_service.search(search_query)

            if not search_result.documents:
                yield {"type": "answer", "data": "질문과 관련된 문서를 찾을 수 없습니다."}
                return

            # Step 2: Provide search results
            yield {"type": "search_results", "data": search_result}

            # Step 3: Prepare context
            yield {"type": "status", "data": "답변을 생성하고 있습니다..."}

            context_documents = []
            for doc in search_result.documents:
                context_documents.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content or "",
                    "score": doc.score
                })

            # Step 4: Stream answer generation
            context = "\n\n".join([
                f"문서: {doc['title']}\n내용: {doc['content'][:1000]}"
                for doc in context_documents
            ])

            yield {"type": "answer_start", "data": None}

            async for chunk in self.openai_service.generate_streaming_response(
                prompt=question,
                context=context,
                max_tokens=1000,
                temperature=0.3
            ):
                yield {"type": "answer_chunk", "data": chunk}

            yield {"type": "answer_end", "data": None}
            yield {"type": "sources", "data": context_documents}

        except Exception as e:
            logger.error(f"Error in streaming RAG: {e}")
            yield {"type": "error", "data": str(e)}

    async def summarize_documents(self, document_ids: List[str],
                                summary_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Summarize multiple documents using RAG approach.
        """
        try:
            if not await self.openai_service.is_available():
                return {
                    "success": False,
                    "error": "AI service not available"
                }

            # Retrieve documents
            documents = []
            for doc_id in document_ids:
                doc = await self.search_service.get_document_by_id(doc_id)
                if doc:
                    documents.append(doc)

            if not documents:
                return {
                    "success": False,
                    "error": "No documents found"
                }

            # Prepare context
            context_parts = []
            for doc in documents:
                content = doc.content or doc.title
                context_parts.append(f"문서: {doc.title}\n내용: {content[:1000]}\n")

            context = "\n".join(context_parts)

            # Generate summary based on type
            if summary_type == "brief":
                prompt = "다음 문서들의 핵심 내용을 3-4문장으로 간략히 요약해 주세요:"
                max_tokens = 200
            elif summary_type == "detailed":
                prompt = "다음 문서들의 주요 내용을 상세히 요약해 주세요. 각 문서의 주요 포인트를 포함해 주세요:"
                max_tokens = 800
            else:  # comprehensive
                prompt = "다음 문서들의 전체적인 내용을 포괄적으로 요약해 주세요:"
                max_tokens = 500

            summary = await self.openai_service.generate_response(
                prompt=f"{prompt}\n\n{context}",
                max_tokens=max_tokens,
                temperature=0.3
            )

            return {
                "success": True,
                "summary": summary,
                "documents_summarized": len(documents),
                "summary_type": summary_type
            }

        except Exception as e:
            logger.error(f"Error summarizing documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def compare_documents(self, document_ids: List[str],
                              comparison_aspect: Optional[str] = None) -> Dict[str, Any]:
        """
        Compare multiple documents using GPT.
        """
        try:
            if not await self.openai_service.is_available():
                return {
                    "success": False,
                    "error": "AI service not available"
                }

            if len(document_ids) < 2:
                return {
                    "success": False,
                    "error": "At least 2 documents required for comparison"
                }

            # Retrieve documents
            documents = []
            for doc_id in document_ids:
                doc = await self.search_service.get_document_by_id(doc_id)
                if doc:
                    documents.append(doc)

            if len(documents) < 2:
                return {
                    "success": False,
                    "error": "Could not retrieve enough documents for comparison"
                }

            # Prepare context
            context_parts = []
            for i, doc in enumerate(documents, 1):
                content = doc.content or doc.title
                context_parts.append(f"문서 {i}: {doc.title}\n내용: {content[:800]}\n")

            context = "\n".join(context_parts)

            # Generate comparison
            if comparison_aspect:
                prompt = f"다음 문서들을 '{comparison_aspect}' 측면에서 비교 분석해 주세요:"
            else:
                prompt = "다음 문서들의 주요 내용, 관점, 특징을 비교 분석해 주세요:"

            comparison = await self.openai_service.generate_response(
                prompt=f"{prompt}\n\n{context}",
                max_tokens=1000,
                temperature=0.3
            )

            return {
                "success": True,
                "comparison": comparison,
                "documents_compared": len(documents),
                "comparison_aspect": comparison_aspect
            }

        except Exception as e:
            logger.error(f"Error comparing documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_insights(self, query: str, max_documents: int = 10) -> Dict[str, Any]:
        """
        Extract insights from documents related to a query.
        """
        try:
            if not await self.openai_service.is_available():
                return {
                    "success": False,
                    "error": "AI service not available"
                }

            # Search for relevant documents
            search_query = SearchQuery(
                query=query,
                search_type=SearchType.HYBRID,
                size=max_documents
            )

            search_result = await self.search_service.search(search_query)

            if not search_result.documents:
                return {
                    "success": True,
                    "insights": "관련 문서를 찾을 수 없어 인사이트를 추출할 수 없습니다.",
                    "sources": []
                }

            # Prepare context from top documents
            context_documents = search_result.documents[:max_documents]
            context_parts = []

            for doc in context_documents:
                content = doc.content or doc.title
                context_parts.append(f"- {doc.title}: {content[:500]}")

            context = "\n".join(context_parts)

            # Generate insights
            prompt = f"""다음 '{query}'와 관련된 문서들을 분석하여 주요 인사이트를 추출해 주세요:

{context}

다음 형식으로 답변해 주세요:
1. 주요 트렌드:
2. 핵심 발견사항:
3. 시사점:
4. 권장사항:"""

            insights = await self.openai_service.generate_response(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.4
            )

            return {
                "success": True,
                "insights": insights,
                "query": query,
                "documents_analyzed": len(context_documents),
                "sources": [{"id": doc.id, "title": doc.title, "score": doc.score}
                           for doc in context_documents]
            }

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check RAG service health."""
        try:
            # Check dependencies
            search_health = True  # search_service is always available
            vector_health = True  # vector_service is always available
            openai_health = await self.openai_service.is_available()

            overall_status = "healthy" if all([search_health, vector_health, openai_health]) else "degraded"

            return {
                "status": overall_status,
                "dependencies": {
                    "search_service": "healthy" if search_health else "unhealthy",
                    "vector_service": "healthy" if vector_health else "unhealthy",
                    "openai_service": "healthy" if openai_health else "unavailable"
                }
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
rag_service = RAGService()