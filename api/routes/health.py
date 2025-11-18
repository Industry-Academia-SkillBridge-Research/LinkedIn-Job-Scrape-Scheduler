"""
Health check and utility routes
"""
from fastapi import APIRouter
from datetime import datetime

from api.models import HealthResponse
from api.core import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is running"
)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/",
    summary="Root endpoint",
    description="API information"
)
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }
