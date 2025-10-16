"""
OpenAI GPT Integration Service
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
import logging
from app.core.config import settings

logger = logging.getLogger("ds")


class OpenAIService:
    """OpenAI GPT 통합 서비스 클래스."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """OpenAI 클라이언트를 초기화합니다."""
        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"OpenAI client initialization failed: {e}")
            raise

    async def is_available(self) -> bool:
        """서비스 가용성을 확인합니다."""
        try:
            if self.client:
                await self.client.models.list()
                return True
            return False
        except Exception as e:
            logger.error(f"OpenAI availability check failed: {e}")
            return False

    async def generate_text(self, prompt: str, max_tokens: int = 100) -> Optional[str]:
        """텍스트를 생성합니다."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return None

# Global instance
openai_service = OpenAIService()

