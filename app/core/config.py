"""
Configuration module using Pydantic Settings
Centralized configuration for the entire application
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = "HSKK Scoring System"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    
    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"
    
    @property
    def audio_input_dir(self) -> Path:
        path = self.data_dir / "audio_input"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def audio_output_dir(self) -> Path:
        path = self.data_dir / "audio_output"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def praat_output_dir(self) -> Path:
        path = self.data_dir / "praat_output"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # Docker/Praat
    praat_container_name: str = "hskk-praat-scoring_praat_1"
    praat_timeout: int = 10
    
    # Audio
    supported_formats: List[str] = [".wav", ".mp3", ".m4a", ".flac"]
    target_sample_rate: int = 16000
    max_audio_duration: int = 180
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Scoring weights
    weight_pronunciation: float = 0.35
    weight_fluency: float = 0.35
    weight_grammar: float = 0.15
    weight_vocabulary: float = 0.15


# Standard scoring thresholds for audio analysis
SCORING_THRESHOLDS = {
    "pitch_range_min": 80,
    "speech_rate_min": 100,
    "speech_rate_max": 250,
    "pause_ratio_max": 0.35,
    "hnr_min": 17,
    "pronunciation_accuracy_min": 0.7
}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)"""
    return Settings()
