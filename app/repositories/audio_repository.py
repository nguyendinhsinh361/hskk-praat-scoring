"""
Audio Repository - File I/O operations for audio files
Handles saving, copying, and cleanup of audio files
"""
import shutil
import logging
from pathlib import Path
from typing import Optional

from app.core.config import Settings
from app.core.exceptions import AudioProcessingError

logger = logging.getLogger(__name__)


class AudioRepository:
    """Repository for audio file operations"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.audio_input_dir = settings.audio_input_dir
        self.audio_output_dir = settings.audio_output_dir
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """
        Save uploaded file to input directory
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Path to saved file
            
        Raises:
            AudioProcessingError: If save fails
        """
        try:
            input_path = self.audio_input_dir / filename
            with open(input_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Saved uploaded file: {input_path} ({len(file_content)} bytes)")
            return input_path
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise AudioProcessingError(f"Failed to save file: {e}")
    
    def save_processed_audio(self, audio_data, sample_rate: int, filename: str) -> Path:
        """
        Save processed audio to output directory
        
        Args:
            audio_data: NumPy array of audio samples
            sample_rate: Sample rate in Hz
            filename: Output filename
            
        Returns:
            Path to saved file
            
        Raises:
            AudioProcessingError: If save fails
        """
        try:
            import soundfile as sf
            
            output_path = self.audio_output_dir / filename
            sf.write(output_path, audio_data, sample_rate)
            
            logger.info(f"Saved processed audio: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save processed audio: {e}")
            raise AudioProcessingError(f"Failed to save processed audio: {e}")
    
    def copy_to_input_dir(self, source_path: Path) -> Path:
        """
        Copy file to audio input directory for Praat processing
        
        Args:
            source_path: Source file path
            
        Returns:
            Path to copied file
        """
        try:
            dest_path = self.audio_input_dir / source_path.name
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied to input dir: {dest_path}")
            return dest_path
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            raise AudioProcessingError(f"Failed to copy file: {e}")
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def cleanup_file(self, file_path: Path) -> bool:
        """
        Remove temporary file
        
        Args:
            file_path: Path to file to remove
            
        Returns:
            True if successful
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up file: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
            return False
    
    def list_input_files(self) -> list[Path]:
        """List all files in input directory"""
        return list(self.audio_input_dir.glob("*"))
