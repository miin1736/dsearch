"""
애플리케이션 환경설정 관리 모듈
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import logging  # 추가: logging 모듈 import

logger = logging.getLogger("ds")


class Settings(BaseSettings):
    """
    애플리케이션 설정 및 환경변수 관리 클래스.

    모든 환경변수와 설정값들을 중앙에서 관리하며,
    Pydantic BaseSettings를 상속받아 자동 검증 및 타입 변환을 제공합니다.
    """

    # Application
    APP_NAME: str = Field(default="Dsearch API", env="APP_NAME")
    VERSION: str = Field(default="2.0.0", env="VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Security
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    SUPER_KEY: str = Field(default="xlLVg89YUMim03SZ", env="SUPER_KEY")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./dsearch.db", env="DATABASE_URL")

    # Elasticsearch
    ELASTICSEARCH_URLS: List[str] = Field(env="ELASTICSEARCH_URLS")
    ELASTICSEARCH_USERNAME: str = Field(env="ELASTICSEARCH_USERNAME")
    ELASTICSEARCH_PASSWORD: str = Field(env="ELASTICSEARCH_PASSWORD")
    ELASTICSEARCH_VERIFY_CERTS: bool = Field(default=False, env="ELASTICSEARCH_VERIFY_CERTS")
    ELASTICSEARCH_TIMEOUT: int = Field(default=60, env="ELASTICSEARCH_TIMEOUT")
    ELASTICSEARCH_BULK_SIZE: int = Field(default=1000, env="ELASTICSEARCH_BULK_SIZE")
    ELASTICSEARCH_INDEX: str = Field(default="ds_content", env="ELASTICSEARCH_INDEX")   
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")

    # File Storage
    MEDIA_ROOT: str = Field(default="./media", env="MEDIA_ROOT")
    STATIC_ROOT: str = Field(default="./static", env="STATIC_ROOT")

    # Search Configuration
    SEARCH_FIELDS: List[str] = Field(
        default=["title^2", "text", "html_mrc_array^0"],
        env="SEARCH_FIELDS"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_DIR: str = Field(default="./logs", env="LOG_DIR")

    # ML Models
    SENTENCE_TRANSFORMER_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        env="SENTENCE_TRANSFORMER_MODEL"
    )
    VECTOR_DIMENSION: int = Field(default=384, env="VECTOR_DIMENSION")

    # Batch Processing
    BATCH_SIZE: int = Field(default=100, env="BATCH_SIZE")
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")

    # Korean Language
    LANGUAGE_CODE: str = Field(default="ko", env="LANGUAGE_CODE")
    TIME_ZONE: str = Field(default="Asia/Seoul", env="TIME_ZONE")

    # Monitoring and Health Checks
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    캐시된 애플리케이션 설정을 가져옵니다.

    lru_cache 데코레이터를 사용하여 설정 인스턴스를 싱글톤으로 관리합니다.

    Returns:
        Settings: 캐시된 설정 인스턴스
    """
    return Settings()


settings = get_settings()


"""
Elasticsearch Connection and Basic Operations
"""

from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch_dsl import connections

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
            self.client = Elasticsearch(
                hosts=settings.ELASTICSEARCH_URLS,  # 변경: ELASTICSEARCH_URL -> ELASTICSEARCH_URLS
                http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS,
                timeout=settings.ELASTICSEARCH_TIMEOUT
            )
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