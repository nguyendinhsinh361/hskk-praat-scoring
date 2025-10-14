from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import Enum

class HSKKLevel(str, Enum):
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class AudioFeatures(BaseModel):
    # Basic info
    duration: float
    
    # Pitch features
    pitch_mean: float
    pitch_std: float
    pitch_range: float
    pitch_min: float
    pitch_max: float
    pitch_median: float
    pitch_quantile_25: float
    pitch_quantile_75: float
    
    # Formants (F1-F5)
    f1_mean: float
    f1_std: float
    f2_mean: float
    f2_std: float
    f3_mean: float
    f3_std: float
    f4_mean: float
    f4_std: float
    
    # Intensity
    intensity_mean: float
    intensity_std: float
    intensity_min: float
    intensity_max: float
    
    # Spectral features
    spectral_centroid: float
    spectral_std: float
    spectral_skewness: float
    spectral_kurtosis: float
    
    # Voice quality
    hnr_mean: float
    hnr_std: float
    jitter_local: float
    jitter_rap: float
    jitter_ppq5: float
    shimmer_local: float
    shimmer_apq3: float
    shimmer_apq5: float
    shimmer_apq11: float
    
    # Speech timing
    speech_rate: float
    articulation_rate: float
    speech_duration: float
    pause_duration: float
    pause_ratio: float
    num_pauses: int
    mean_pause_duration: float
    
    # Additional measures
    cog: float  # Center of Gravity
    slope: float  # Spectral slope
    spread: float  # Spectral spread

class PronunciationAssessment(BaseModel):
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: float
    detailed_feedback: Dict[str, str]

class HSKKScore(BaseModel):
    overall_score: float
    level_achieved: HSKKLevel
    pronunciation: float
    fluency: float
    grammar: float
    vocabulary: float
    
class HSKKAssessmentRequest(BaseModel):
    audio_file: str
    target_level: Optional[HSKKLevel] = HSKKLevel.INTERMEDIATE
    reference_text: Optional[str] = None
    
class HSKKAssessmentResponse(BaseModel):
    success: bool
    score: Optional[HSKKScore]
    features: Optional[AudioFeatures]
    pronunciation: Optional[PronunciationAssessment]
    transcription: Optional[str]
    error_message: Optional[str]
    processing_time: float