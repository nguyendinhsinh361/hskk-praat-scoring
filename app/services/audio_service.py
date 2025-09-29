import librosa
import soundfile as sf
from pathlib import Path
import logging
import shutil
from typing import Optional

from app.config import SUPPORTED_FORMATS, TARGET_SAMPLE_RATE, AUDIO_OUTPUT_DIR, AUDIO_INPUT_DIR

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.target_sr = TARGET_SAMPLE_RATE
        self.supported_formats = SUPPORTED_FORMATS
        
    def is_supported_format(self, filename: str) -> bool:
        """Check if audio format is supported"""
        suffix = Path(filename).suffix.lower()
        return suffix in self.supported_formats
    
    def preprocess_audio(self, input_path: Path) -> Optional[Path]:
        """Preprocess audio file for Praat analysis"""
        try:
            logger.info(f"Preprocessing audio: {input_path}")
            
            # Load audio
            audio, sr = librosa.load(input_path, sr=self.target_sr)
            logger.info(f"Loaded audio: {len(audio)} samples at {sr} Hz")
            
            # Normalize audio
            audio = librosa.util.normalize(audio)
            
            # Remove silence from beginning and end
            audio, _ = librosa.effects.trim(audio, top_db=20)
            logger.info(f"After trimming: {len(audio)} samples")
            
            # Save processed audio to audio_output
            output_filename = f"processed_{input_path.name.replace(input_path.suffix, '.wav')}"
            output_path = AUDIO_OUTPUT_DIR / output_filename
            sf.write(output_path, audio, self.target_sr)
            logger.info(f"Audio saved to: {output_path}")
            
            # IMPORTANT: Copy processed file to audio_input for Praat access
            praat_input_path = AUDIO_INPUT_DIR / output_filename
            shutil.copy2(output_path, praat_input_path)
            logger.info(f"Audio copied for Praat access: {praat_input_path}")
            
            # Return the path that Praat will use
            return praat_input_path
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            return None
    
    def get_audio_info(self, audio_path: Path) -> dict:
        """Get basic audio information"""
        try:
            audio, sr = librosa.load(audio_path, sr=None)
            duration = len(audio) / sr
            
            return {
                "duration": duration,
                "sample_rate": sr,
                "channels": 1,  # librosa loads as mono by default
                "format": audio_path.suffix,
                "file_size": audio_path.stat().st_size if audio_path.exists() else 0
            }
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}