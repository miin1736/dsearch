"""
애플리케이션 환경설정 관리 모듈
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    애플리케이션 설정 및 환경변수 관리 클래스.

    모든 환경변수와 설정값들을 중앙에서 관리하며,
    Pydantic BaseSettings를 상속받아 자동 검증 및 타입 변환을 제공합니다.
    """

    # Application
    APP_NAME: str = "Dsearch API"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Security
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    SUPER_KEY: str = Field(default="xlLVg89YUMim03SZ", env="SUPER_KEY")

    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL", default="sqlite:///./dsearch.db")

    # Elasticsearch
    ELASTICSEARCH_URLS: List[str] = Field(env="ELASTICSEARCH_URLS")
    ELASTICSEARCH_USERNAME: str = Field(env="ELASTICSEARCH_USERNAME")
    ELASTICSEARCH_PASSWORD: str = Field(env="ELASTICSEARCH_PASSWORD")
    ELASTICSEARCH_VERIFY_CERTS: bool = Field(default=False, env="ELASTICSEARCH_VERIFY_CERTS")
    ELASTICSEARCH_TIMEOUT: int = Field(default=60, env="ELASTICSEARCH_TIMEOUT")

    # Redis
    REDIS_URL: str = Field(env="REDIS_URL", default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")

    # File Storage
    MEDIA_ROOT: str = Field(default="media", env="MEDIA_ROOT")
    STATIC_ROOT: str = Field(default="static", env="STATIC_ROOT")

    # Search Configuration
    SEARCH_FIELDS: List[str] = Field(
        default=["title^2", "text", "html_mrc_array^0"],
        env="SEARCH_FIELDS"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_DIR: str = Field(default="/home/logs", env="LOG_DIR")

    # ML Models
    SENTENCE_TRANSFORMER_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        env="SENTENCE_TRANSFORMER_MODEL"
    )

    # Batch Processing
    BATCH_SIZE: int = Field(default=100, env="BATCH_SIZE")
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")

    # Korean Language
    LANGUAGE_CODE: str = Field(default="ko", env="LANGUAGE_CODE")
    TIME_ZONE: str = Field(default="Asia/Seoul", env="TIME_ZONE")

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