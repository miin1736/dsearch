"""
OpenAI GPT Integration Service
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import openai
from openai import AsyncOpenAI
import logging

from app.core.config import settings

logger = logging.getLogger("ds")


class OpenAIService:
    """Service for OpenAI GPT integration."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client."""
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not provided. GPT features will be disabled.")
            return

        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    async def is_available(self) -> bool:
        """Check if OpenAI service is available."""
        return self.client is not None

    async def generate_response(self, prompt: str, context: Optional[str] = None,
                              max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        """Generate text response using GPT."""
        if not self.client:
            return None

        try:
            # Prepare messages
            messages = []

            if context:
                messages.append({
                    "role": "system",
                    "content": f"다음 문서 내용을 참고하여 질문에 답변해 주세요:\n\n{context}"
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Generate response
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            if response.choices:
                return response.choices[0].message.content

            return None

        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return None

    async def generate_streaming_response(self, prompt: str, context: Optional[str] = None,
                                        max_tokens: int = 1000, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Generate streaming text response using GPT."""
        if not self.client:
            return

        try:
            # Prepare messages
            messages = []

            if context:
                messages.append({
                    "role": "system",
                    "content": f"다음 문서 내용을 참고하여 질문에 답변해 주세요:\n\n{context}"
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Generate streaming response
            stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error generating streaming OpenAI response: {e}")

    async def answer_question_with_context(self, question: str, documents: List[Dict[str, Any]],
                                         max_context_length: int = 4000) -> Optional[str]:
        """Answer a question using provided documents as context."""
        if not self.client or not documents:
            return None

        try:
            # Build context from documents
            context_parts = []
            context_length = 0

            for doc in documents:
                doc_text = f"문서: {doc.get('title', 'Unknown')}\n내용: {doc.get('content', '')}\n\n"

                if context_length + len(doc_text) <= max_context_length:
                    context_parts.append(doc_text)
                    context_length += len(doc_text)
                else:
                    # Truncate the last document if it would exceed the limit
                    remaining_length = max_context_length - context_length
                    if remaining_length > 100:  # Only include if there's meaningful space
                        truncated_text = doc_text[:remaining_length] + "...\n\n"
                        context_parts.append(truncated_text)
                    break

            context = "".join(context_parts)

            # Generate answer
            return await self.generate_response(
                prompt=question,
                context=context,
                max_tokens=1000,
                temperature=0.3  # Lower temperature for more factual responses
            )

        except Exception as e:
            logger.error(f"Error answering question with context: {e}")
            return None

    async def summarize_document(self, text: str, max_length: int = 200) -> Optional[str]:
        """Generate a summary of document text."""
        if not self.client:
            return None

        try:
            prompt = f"""다음 문서의 주요 내용을 {max_length}자 이내로 요약해 주세요:

{text}

요약:"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=max_length * 2,  # Allow some buffer for Korean text
                temperature=0.3
            )

            return response

        except Exception as e:
            logger.error(f"Error summarizing document: {e}")
            return None

    async def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using GPT."""
        if not self.client:
            return []

        try:
            prompt = f"""다음 텍스트에서 가장 중요한 키워드 {max_keywords}개를 추출해 주세요.
키워드는 쉼표로 구분하여 나열해 주세요:

{text}

키워드:"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )

            if response:
                # Parse keywords from response
                keywords = [kw.strip() for kw in response.split(',')]
                return [kw for kw in keywords if kw and len(kw) > 1][:max_keywords]

            return []

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []

    async def generate_search_suggestions(self, query: str, max_suggestions: int = 5) -> List[str]:
        """Generate alternative search suggestions for a query."""
        if not self.client:
            return []

        try:
            prompt = f"""다음 검색어와 관련된 대안 검색 제안 {max_suggestions}개를 생성해 주세요:

검색어: {query}

각 제안은 한 줄씩 작성해 주세요:"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7
            )

            if response:
                # Parse suggestions from response
                suggestions = [s.strip() for s in response.split('\n') if s.strip()]
                return suggestions[:max_suggestions]

            return []

        except Exception as e:
            logger.error(f"Error generating search suggestions: {e}")
            return []

    async def classify_document(self, text: str, categories: List[str]) -> Optional[str]:
        """Classify document text into one of the provided categories."""
        if not self.client or not categories:
            return None

        try:
            categories_text = ", ".join(categories)
            prompt = f"""다음 문서를 이 카테고리 중 하나로 분류해 주세요: {categories_text}

문서 내용:
{text}

분류 결과 (카테고리 이름만):"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=50,
                temperature=0.1  # Very low temperature for classification
            )

            if response and response.strip() in categories:
                return response.strip()

            return None

        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            return None

    async def generate_title(self, text: str) -> Optional[str]:
        """Generate a title for document text."""
        if not self.client:
            return None

        try:
            prompt = f"""다음 텍스트에 적합한 제목을 생성해 주세요 (20자 이내):

{text[:500]}...

제목:"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=50,
                temperature=0.3
            )

            return response.strip() if response else None

        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return None

    async def translate_text(self, text: str, target_language: str = "en") -> Optional[str]:
        """Translate text to target language."""
        if not self.client:
            return None

        try:
            prompt = f"""다음 텍스트를 {target_language}로 번역해 주세요:

{text}

번역:"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=len(text) * 2,  # Buffer for translation
                temperature=0.3
            )

            return response

        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return None

    async def check_content_relevance(self, query: str, content: str,
                                    threshold: float = 0.7) -> Dict[str, Any]:
        """Check how relevant content is to a query using GPT."""
        if not self.client:
            return {"relevant": False, "score": 0.0, "reason": "GPT not available"}

        try:
            prompt = f"""다음 검색어와 내용의 관련성을 0.0~1.0 사이의 점수로 평가해 주세요:

검색어: {query}
내용: {content[:1000]}...

평가 결과 (점수와 이유):"""

            response = await self.generate_response(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )

            if response:
                # Try to extract score from response
                # This is a simplified approach - in production, you might use a more structured prompt
                lines = response.split('\n')
                score = 0.0
                reason = response

                for line in lines:
                    if '점수' in line or 'score' in line.lower():
                        try:
                            # Extract number from line
                            import re
                            numbers = re.findall(r'[0-9]*\.?[0-9]+', line)
                            if numbers:
                                score = float(numbers[0])
                                if score > 1.0:  # If score is out of 10, normalize
                                    score /= 10.0
                                break
                        except:
                            pass

                return {
                    "relevant": score >= threshold,
                    "score": score,
                    "reason": reason
                }

            return {"relevant": False, "score": 0.0, "reason": "No response"}

        except Exception as e:
            logger.error(f"Error checking content relevance: {e}")
            return {"relevant": False, "score": 0.0, "reason": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI service health."""
        try:
            if not self.client:
                return {
                    "status": "unavailable",
                    "message": "OpenAI API key not configured"
                }

            # Test with a simple request
            response = await self.generate_response(
                prompt="Hello",
                max_tokens=10,
                temperature=0.1
            )

            if response:
                return {
                    "status": "healthy",
                    "message": "OpenAI service is working",
                    "model": settings.OPENAI_MODEL
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "OpenAI service not responding"
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
openai_service = OpenAIService()