from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import Enum

class HSKKLevel(str, Enum):
    ELEMENTARY = "elementary"    # 初级 (Elementary) 
    INTERMEDIATE = "intermediate"  # 中级 (Intermediate)
    ADVANCED = "advanced"        # 高级 (Advanced)

class AudioFeatures(BaseModel):
    duration: float
    pitch_mean: float
    pitch_std: float
    pitch_range: float
    f1_mean: float
    f2_mean: float
    f3_mean: float
    intensity_mean: float
    intensity_std: float
    spectral_centroid: float
    hnr_mean: float  # Harmonics-to-Noise Ratio
    jitter: float
    shimmer: float
    speech_rate: float  # syllables per minute
    speech_duration: float
    pause_ratio: float

class PronunciationAssessment(BaseModel):
    accuracy_score: float  # 0-1
    fluency_score: float   # 0-1
    completeness_score: float  # 0-1
    prosody_score: float   # 0-1
    detailed_feedback: Dict[str, str]

class HSKKScore(BaseModel):
    overall_score: float  # 0-100
    level_achieved: HSKKLevel
    pronunciation: float  # 0-100
    fluency: float       # 0-100
    grammar: float       # 0-100 (if available from STT)
    vocabulary: float    # 0-100 (if available from STT)
    
class HSKKAssessmentRequest(BaseModel):
    audio_file: str
    target_level: Optional[HSKKLevel] = HSKKLevel.INTERMEDIATE
    reference_text: Optional[str] = None  # For read-aloud tasks
    
class HSKKAssessmentResponse(BaseModel):
    success: bool
    score: Optional[HSKKScore]
    features: Optional[AudioFeatures]
    pronunciation: Optional[PronunciationAssessment]
    transcription: Optional[str]
    error_message: Optional[str]
    processing_time: float