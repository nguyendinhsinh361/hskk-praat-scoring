"""
Dependency Injection for FastAPI
Provides singleton instances of services
"""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings


# Forward declarations to avoid circular imports
_praat_repository = None
_audio_repository = None
_praat_service = None
_audio_service = None
_scoring_service = None
_assessment_service = None


def get_praat_repository():
    """Get PraatRepository singleton"""
    global _praat_repository
    if _praat_repository is None:
        from app.repositories.praat_repository import PraatRepository
        _praat_repository = PraatRepository(get_settings())
    return _praat_repository


def get_audio_repository():
    """Get AudioRepository singleton"""
    global _audio_repository
    if _audio_repository is None:
        from app.repositories.audio_repository import AudioRepository
        _audio_repository = AudioRepository(get_settings())
    return _audio_repository


def get_praat_service():
    """Get PraatService singleton"""
    global _praat_service
    if _praat_service is None:
        from app.services.praat_service import PraatService
        _praat_service = PraatService(
            settings=get_settings(),
            repository=get_praat_repository()
        )
    return _praat_service


def get_audio_service():
    """Get AudioService singleton"""
    global _audio_service
    if _audio_service is None:
        from app.services.audio_service import AudioService
        _audio_service = AudioService(
            settings=get_settings(),
            repository=get_audio_repository()
        )
    return _audio_service


def get_scoring_service():
    """Get ScoringService singleton"""
    global _scoring_service
    if _scoring_service is None:
        from app.services.scoring_service import ScoringService
        _scoring_service = ScoringService(get_settings())
    return _scoring_service


def get_assessment_service():
    """Get AssessmentService singleton"""
    global _assessment_service
    if _assessment_service is None:
        from app.services.assessment_service import AssessmentService
        _assessment_service = AssessmentService(
            settings=get_settings(),
            audio_service=get_audio_service(),
            praat_service=get_praat_service(),
            scoring_service=get_scoring_service()
        )
    return _assessment_service


# Type aliases for FastAPI dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
