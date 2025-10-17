"""
API v1 라우터 모듈
"""

from fastapi import APIRouter

from .search.endpoints import router as search_router
from .ranking.endpoints import router as ranking_router
from .auth.endpoints import router as auth_router
from .utility.endpoints import router as utility_router
from .batch.endpoints import router as batch_router
from .ml.endpoints import router as ml_router
from .admin.endpoints import router as admin_router

api_router = APIRouter(prefix="/api/v1")

# 라우터 등록
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(ranking_router, prefix="/ranking", tags=["ranking"])
api_router.include_router(utility_router, prefix="/utility", tags=["utility"])
api_router.include_router(batch_router, prefix="/batch", tags=["batch"])
api_router.include_router(ml_router, prefix="/ml", tags=["ml"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

__all__ = ["api_router"]