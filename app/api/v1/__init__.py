"""
API Version 1
"""

from fastapi import APIRouter
from .search.endpoints import router as search_router
from .admin.endpoints import router as admin_router
from .batch.endpoints import router as batch_router
from .ml.endpoints import router as ml_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(batch_router, prefix="/batch", tags=["batch"])
api_router.include_router(ml_router, prefix="/ml", tags=["ml"])

__all__ = ["api_router"]