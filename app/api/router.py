"""
API Router Aggregator
Combines all v1 routers
"""
from fastapi import APIRouter

from app.api.v1 import assessment, health

api_router = APIRouter()

# Include all routers
api_router.include_router(assessment.router)
api_router.include_router(health.router)
