"""
Pydantic schemas for request/response models
"""
from typing import Optional, Dict

from pydantic import BaseModel, Field


# ============== Audio Features ==============

class AudioFeatures(BaseModel):
    """43 acoustic features extracted from audio"""
    
    # Basic info (1)
    duration: float = Field(..., description="Audio duration in seconds")
    
    # Pitch features (8)
    pitch_mean: float = Field(..., ge=0, description="Mean pitch in Hz")
    pitch_std: float = Field(..., ge=0, description="Pitch standard deviation")
    pitch_range: float = Field(..., ge=0, description="Pitch range in Hz")
    pitch_min: float = Field(..., ge=0, description="Minimum pitch")
    pitch_max: float = Field(..., ge=0, description="Maximum pitch")
    pitch_median: float = Field(..., ge=0, description="Median pitch")
    pitch_quantile_25: float = Field(..., ge=0, description="25th percentile pitch")
    pitch_quantile_75: float = Field(..., ge=0, description="75th percentile pitch")
    
    # Formants F1-F4 (8)
    f1_mean: float = Field(..., ge=0)
    f1_std: float = Field(..., ge=0)
    f2_mean: float = Field(..., ge=0)
    f2_std: float = Field(..., ge=0)
    f3_mean: float = Field(..., ge=0)
    f3_std: float = Field(..., ge=0)
    f4_mean: float = Field(..., ge=0)
    f4_std: float = Field(..., ge=0)
    
    # Intensity (4)
    intensity_mean: float = Field(..., ge=0)
    intensity_std: float = Field(..., ge=0)
    intensity_min: float = Field(..., ge=0)
    intensity_max: float = Field(..., ge=0)
    
    # Spectral features (4)
    spectral_centroid: float = Field(..., ge=0)
    spectral_std: float = Field(..., ge=0)
    spectral_skewness: float
    spectral_kurtosis: float
    
    # Voice quality (10)
    hnr_mean: float = Field(..., description="Harmonics-to-Noise Ratio")
    hnr_std: float = Field(..., ge=0)
    jitter_local: float = Field(..., ge=0)
    jitter_rap: float = Field(..., ge=0)
    jitter_ppq5: float = Field(..., ge=0)
    shimmer_local: float = Field(..., ge=0)
    shimmer_apq3: float = Field(..., ge=0)
    shimmer_apq5: float = Field(..., ge=0)
    shimmer_apq11: float = Field(..., ge=0)
    
    # Speech timing (7)
    speech_rate: float = Field(..., ge=0, description="Syllables per minute")
    articulation_rate: float = Field(..., ge=0)
    speech_duration: float = Field(..., ge=0)
    pause_duration: float = Field(..., ge=0)
    pause_ratio: float = Field(..., ge=0, le=1)
    num_pauses: int = Field(..., ge=0)
    mean_pause_duration: float = Field(..., ge=0)
    
    # Additional measures (3)
    cog: float = Field(..., description="Center of Gravity")
    slope: float
    spread: float = Field(..., description="Spectral spread")


# ============== API Response ==============

class RawFeaturesResponse(BaseModel):
    """Response schema for raw Praat features"""
    success: bool
    features: Optional[AudioFeatures] = None
    error_message: Optional[str] = None
    processing_time: float = Field(..., ge=0)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: float
    components: Dict[str, str] = Field(default_factory=dict)
