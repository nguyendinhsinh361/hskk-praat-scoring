"""
Health Router - Health check and debug endpoints
"""
import time
from typing import Dict, Any

from fastapi import APIRouter, Depends

from app.core.config import get_settings, Settings
from app.core.dependencies import get_praat_service
from app.models.schemas import HealthResponse
from app.services.praat_service import PraatService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check system health status"
)
async def health_check(
    settings: Settings = Depends(get_settings),
    praat_service: PraatService = Depends(get_praat_service)
) -> HealthResponse:
    """
    Check health status of all system components
    
    Returns status of:
    - Praat container connection
    - Storage directories
    - Frontend templates
    """
    status = "healthy"
    components = {}
    
    # Check Praat service
    try:
        if praat_service.test_connection():
            components["praat"] = "healthy"
        else:
            components["praat"] = "unhealthy"
            status = "degraded"
    except Exception as e:
        components["praat"] = f"error: {str(e)}"
        status = "degraded"
    
    # Check required directories
    dirs_ok = all([
        settings.audio_input_dir.exists(),
        settings.audio_output_dir.exists(),
        settings.praat_output_dir.exists()
    ])
    components["storage"] = "healthy" if dirs_ok else "unhealthy"
    
    # Check frontend
    components["frontend"] = "healthy" if settings.templates_dir.exists() else "missing"
    
    if not dirs_ok or not settings.templates_dir.exists():
        status = "degraded"
    
    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.app_version,
        timestamp=time.time(),
        components=components
    )


@router.get(
    "/debug",
    summary="Debug Information",
    description="Get detailed system debug information"
)
async def debug_info(
    settings: Settings = Depends(get_settings),
    praat_service: PraatService = Depends(get_praat_service)
) -> Dict[str, Any]:
    """
    Get detailed debug information about the system
    
    Returns:
    - System configuration
    - Frontend paths and status
    - Praat container status
    - Directory contents
    """
    return {
        "system": {
            "praat_container": settings.praat_container_name,
            "audio_formats": settings.supported_formats,
            "target_sample_rate": settings.target_sample_rate
        },
        "frontend": {
            "frontend_dir": str(settings.frontend_dir),
            "frontend_exists": settings.frontend_dir.exists(),
            "static_dir": str(settings.static_dir),
            "static_exists": settings.static_dir.exists(),
            "templates_dir": str(settings.templates_dir),
            "templates_exist": settings.templates_dir.exists(),
            "template_files": [
                f.name for f in settings.templates_dir.glob("*.html")
            ] if settings.templates_dir.exists() else []
        },
        "praat_connection": praat_service.test_connection(),
        "container_debug": praat_service.get_debug_info(),
        "directories": {
            "audio_input_exists": settings.audio_input_dir.exists(),
            "audio_input_files": [
                f.name for f in settings.audio_input_dir.glob("*")
            ] if settings.audio_input_dir.exists() else [],
        }
    }
