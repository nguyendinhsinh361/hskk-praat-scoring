"""
Assessment Service - Main orchestrator
Coordinates audio and praat services for raw feature extraction
"""
import time
import logging
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import (
    AudioProcessingError,
    AudioValidationError,
    FeatureExtractionError,
    PraatExecutionError,
)
from app.models.schemas import RawFeaturesResponse
from app.services.audio_service import AudioService
from app.services.praat_service import PraatService

logger = logging.getLogger(__name__)


class AssessmentService:
    """Main orchestrator service for Praat feature extraction"""
    
    def __init__(
        self,
        settings: Settings,
        audio_service: AudioService,
        praat_service: PraatService
    ):
        self.settings = settings
        self.audio_service = audio_service
        self.praat_service = praat_service
    
    async def extract_raw_features(
        self,
        audio_content: bytes,
        filename: str
    ) -> RawFeaturesResponse:
        """
        Extract raw 43 Praat acoustic features from audio
        
        Args:
            audio_content: Raw audio file bytes
            filename: Original filename
            
        Returns:
            RawFeaturesResponse with raw acoustic features
        """
        start_time = time.time()
        
        try:
            # Validate format
            if not self.audio_service.is_supported_format(filename):
                return self._error_response(
                    f"Unsupported format. Supported: {self.settings.supported_formats}",
                    start_time
                )
            
            # Save uploaded file
            input_path = self._save_uploaded_file(audio_content, filename)
            logger.info(f"Processing: {filename} ({len(audio_content)} bytes)")
            
            # Preprocess audio
            processed_path = self.audio_service.preprocess_audio(input_path)
            if not processed_path:
                return self._error_response("Audio preprocessing failed", start_time)
            
            logger.info(f"Preprocessed: {processed_path}")
            
            # Extract features
            features = self.praat_service.extract_features(processed_path)
            if not features:
                debug_info = self.praat_service.get_debug_info()
                logger.error(f"Feature extraction failed. Debug: {debug_info}")
                return self._error_response(
                    "Failed to extract audio features. Check system health.",
                    start_time
                )
            
            processing_time = time.time() - start_time
            logger.info(f"Features extracted in {processing_time:.2f}s")
            
            return RawFeaturesResponse(
                success=True,
                features=features,
                error_message=None,
                processing_time=processing_time
            )
            
        except AudioValidationError as e:
            return self._error_response(f"Validation error: {e.message}", start_time)
        except AudioProcessingError as e:
            return self._error_response(f"Audio error: {e.message}", start_time)
        except (FeatureExtractionError, PraatExecutionError) as e:
            return self._error_response(f"Praat error: {e.message}", start_time)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return self._error_response(f"System error: {str(e)}", start_time)
    
    def _save_uploaded_file(self, content: bytes, filename: str) -> Path:
        """Save uploaded file and return path"""
        input_path = self.settings.audio_input_dir / filename
        with open(input_path, "wb") as f:
            f.write(content)
        return input_path
    
    def _error_response(self, message: str, start_time: float) -> RawFeaturesResponse:
        """Create error response"""
        return RawFeaturesResponse(
            success=False,
            features=None,
            error_message=message,
            processing_time=time.time() - start_time
        )
