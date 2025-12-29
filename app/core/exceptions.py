"""
Custom exceptions for the HSKK Scoring System
"""
from typing import Optional


class HSKKBaseError(Exception):
    """Base exception for HSKK system"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class AudioProcessingError(HSKKBaseError):
    """Exception raised when audio processing fails"""
    pass


class AudioValidationError(HSKKBaseError):
    """Exception raised when audio file validation fails"""
    pass


class PraatConnectionError(HSKKBaseError):
    """Exception raised when Praat container connection fails"""
    pass


class PraatExecutionError(HSKKBaseError):
    """Exception raised when Praat script execution fails"""
    pass


class FeatureExtractionError(HSKKBaseError):
    """Exception raised when feature extraction fails"""
    pass


class ScoringError(HSKKBaseError):
    """Exception raised when scoring calculation fails"""
    pass


class ServiceNotInitializedError(HSKKBaseError):
    """Exception raised when a service is not properly initialized"""
    pass
