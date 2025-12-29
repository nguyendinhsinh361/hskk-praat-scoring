"""
Audio Service - Audio processing logic
Handles validation, preprocessing, and normalization
"""
import logging
from pathlib import Path
from typing import Optional, Tuple

import librosa

from app.core.config import Settings
from app.core.exceptions import AudioValidationError, AudioProcessingError
from app.repositories.audio_repository import AudioRepository

logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio processing operations"""
    
    def __init__(self, settings: Settings, repository: AudioRepository):
        self.settings = settings
        self.repository = repository
        self.target_sr = settings.target_sample_rate
        self.supported_formats = settings.supported_formats
        self.max_duration = settings.max_audio_duration
        self.max_file_size = settings.max_file_size
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if audio format is supported"""
        suffix = Path(filename).suffix.lower()
        return suffix in self.supported_formats
    
    def validate_audio_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate audio file size and duration
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        file_size = self.repository.get_file_size(file_path)
        if file_size > self.max_file_size:
            size_mb = file_size / 1024 / 1024
            max_mb = self.max_file_size / 1024 / 1024
            return False, f"File too large: {size_mb:.1f}MB (max: {max_mb:.0f}MB)"
        
        # Check duration
        try:
            duration = librosa.get_duration(path=str(file_path))
            if duration > self.max_duration:
                return False, f"Audio too long: {duration:.1f}s (max: {self.max_duration}s)"
        except Exception as e:
            return False, f"Could not read audio file: {str(e)}"
        
        return True, None
    
    def preprocess_audio(self, input_path: Path) -> Optional[Path]:
        """
        Preprocess audio file for Praat analysis
        
        Steps:
        1. Validate file
        2. Load audio at target sample rate
        3. Normalize amplitude
        4. Trim silence
        5. Save as WAV
        6. Copy to Praat input directory
        
        Returns:
            Path to preprocessed file or None if failed
        """
        try:
            logger.info(f"Preprocessing audio: {input_path}")
            
            # Validate
            is_valid, error_msg = self.validate_audio_file(input_path)
            if not is_valid:
                raise AudioValidationError(error_msg)
            
            # Load and process
            audio, sr = librosa.load(input_path, sr=self.target_sr)
            logger.info(f"Loaded: {len(audio)} samples at {sr}Hz")
            
            # Normalize
            audio = librosa.util.normalize(audio)
            
            # Trim silence
            audio, _ = librosa.effects.trim(audio, top_db=20)
            logger.info(f"After trimming: {len(audio)} samples")
            
            # Save processed audio
            output_filename = f"processed_{input_path.stem}.wav"
            output_path = self.repository.save_processed_audio(
                audio, self.target_sr, output_filename
            )
            
            # Copy to Praat input directory
            praat_input_path = self.repository.copy_to_input_dir(output_path)
            
            logger.info(f"Preprocessed audio ready: {praat_input_path}")
            return praat_input_path
            
        except AudioValidationError:
            raise
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            raise AudioProcessingError(f"Preprocessing failed: {e}")
    
    def get_audio_info(self, audio_path: Path) -> dict:
        """Get basic audio information"""
        try:
            audio, sr = librosa.load(audio_path, sr=None)
            duration = len(audio) / sr
            
            return {
                "duration": duration,
                "sample_rate": sr,
                "channels": 1,
                "format": audio_path.suffix,
                "file_size": self.repository.get_file_size(audio_path)
            }
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}