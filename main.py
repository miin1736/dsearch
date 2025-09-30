"""
FastAPI Main Application
Korean Document Search Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import api_router

def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션을 생성하고 설정합니다.

    한국어 문서 검색 플랫폼의 메인 FastAPI 애플리케이션을 생성하고
    필요한 미들웨어, 라우팅 및 설정을 초기화합니다.

    Returns:
        FastAPI: 설정된 FastAPI 애플리케이션 인스턴스
    """

    app = FastAPI(
        title="Dsearch API",
        description="Korean Enterprise Document Search Platform",
        version="2.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/media", StaticFiles(directory="media"), name="media")

    return app

app = create_app()

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )