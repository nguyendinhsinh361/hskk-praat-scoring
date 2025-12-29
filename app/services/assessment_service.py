"""
Assessment Service - Main orchestrator
Coordinates audio, praat, and scoring services
"""
import time
import logging
from pathlib import Path
from typing import Optional

from app.core.config import Settings
from app.core.exceptions import (
    AudioProcessingError,
    AudioValidationError,
    FeatureExtractionError,
    PraatExecutionError,
)
from app.models.schemas import AssessmentResponse
from app.services.audio_service import AudioService
from app.services.praat_service import PraatService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class AssessmentService:
    """Main orchestrator service for HSKK assessment"""
    
    def __init__(
        self,
        settings: Settings,
        audio_service: AudioService,
        praat_service: PraatService,
        scoring_service: ScoringService
    ):
        self.settings = settings
        self.audio_service = audio_service
        self.praat_service = praat_service
        self.scoring_service = scoring_service
    
    async def assess(
        self,
        audio_content: bytes,
        filename: str,
        reference_text: Optional[str] = None
    ) -> AssessmentResponse:
        """
        Perform full HSKK assessment on audio file
        
        Args:
            audio_content: Raw audio file bytes
            filename: Original filename
            reference_text: Optional reference text
            
        Returns:
            AssessmentResponse with scores and features
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
            
            logger.info(f"Features: duration={features.duration:.2f}s, pitch={features.pitch_mean:.1f}Hz")
            
            # Generate transcription placeholder
            transcription = self._generate_transcription(filename, features)
            
            # Calculate score
            score = self.scoring_service.calculate_score(features, transcription)
            
            # Create pronunciation assessment
            pronunciation = self.scoring_service.create_pronunciation_assessment(
                features, reference_text
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Assessment done in {processing_time:.2f}s - Score: {score.overall_score:.1f}")
            
            return AssessmentResponse(
                success=True,
                score=score,
                features=features,
                pronunciation=pronunciation,
                transcription=transcription,
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
    
    def _generate_transcription(self, filename: str, features) -> str:
        """Generate transcription placeholder (integrate Whisper here)"""
        return (
            f"音频分析完成。文件: {filename}, "
            f"时长: {features.duration:.1f}秒, "
            f"平均音高: {features.pitch_mean:.1f}Hz"
        )
    
    def _error_response(self, message: str, start_time: float) -> AssessmentResponse:
        """Create error response"""
        return AssessmentResponse(
            success=False,
            score=None,
            features=None,
            pronunciation=None,
            transcription=None,
            error_message=message,
            processing_time=time.time() - start_time
        )
