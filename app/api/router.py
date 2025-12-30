"""
API Router Aggregator
Combines all v1 routers
"""
from fastapi import APIRouter

from app.api.v1 import health, scoring

api_router = APIRouter()

# Include routers
api_router.include_router(health.router)
api_router.include_router(scoring.router)
