"""
Scoring API - Extract features and score audio based on HSKK criteria
"""
from enum import Enum
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Query, Depends
from pydantic import BaseModel, Field
import logging

from app.core.dependencies import get_assessment_service
from app.services.assessment_service import AssessmentService
from app.scorers.praat_scorers import PronunciationScorer, FluencyScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/score", tags=["Scoring"])


# ========== Enums ==========

class TaskCode(str, Enum):
    """HSKK Task codes"""
    # Sơ cấp (Beginner - 101)
    HSKKSC1 = "HSKKSC1"  # Nghe và nhắc lại
    HSKKSC2 = "HSKKSC2"  # Nghe và trả lời (câu ngắn)
    HSKKSC3 = "HSKKSC3"  # Trả lời câu hỏi (đoạn ngắn)
    
    # Trung cấp (Intermediate - 102)
    HSKKTC1 = "HSKKTC1"  # Nghe và nhắc lại
    HSKKTC2 = "HSKKTC2"  # Mô tả tranh
    HSKKTC3 = "HSKKTC3"  # Trả lời câu hỏi
    
    # Cao cấp (Advanced - 103)
    HSKKCC1 = "HSKKCC1"  # Nghe và nhắc lại
    HSKKCC2 = "HSKKCC2"  # Đọc đoạn văn
    HSKKCC3 = "HSKKCC3"  # Trả lời câu hỏi


class ExamLevel(str, Enum):
    """HSKK Exam levels"""
    BEGINNER = "101"      # Sơ cấp
    INTERMEDIATE = "102"  # Trung cấp
    ADVANCED = "103"      # Cao cấp


# Task code to internal task mapping
TASK_MAPPING = {
    "HSKKSC1": "task1", "HSKKSC2": "task2", "HSKKSC3": "task3",
    "HSKKTC1": "task1", "HSKKTC2": "task2", "HSKKTC3": "task3",
    "HSKKCC1": "task1", "HSKKCC2": "task2", "HSKKCC3": "task3",
}

LEVEL_MAPPING = {
    "101": "beginner",
    "102": "intermediate", 
    "103": "advanced",
}


# ========== Response Schemas ==========

class ScoreDetail(BaseModel):
    """Individual score detail"""
    criteria_name: str
    score: float
    max_score: float
    percentage: float
    level: str
    issues: list[str]
    feedback: str


class AudioFeaturesDict(BaseModel):
    """Audio features as dict"""
    duration: float
    pitch_mean: float
    pitch_std: float
    pitch_range: float
    pitch_min: float
    pitch_max: float
    pitch_median: float
    pitch_quantile_25: float
    pitch_quantile_75: float
    f1_mean: float
    f1_std: float
    f2_mean: float
    f2_std: float
    f3_mean: float
    f3_std: float
    f4_mean: float
    f4_std: float
    intensity_mean: float
    intensity_std: float
    intensity_min: float
    intensity_max: float
    spectral_centroid: float
    spectral_std: float
    spectral_skewness: float
    spectral_kurtosis: float
    hnr_mean: float
    hnr_std: float
    jitter_local: float
    jitter_rap: float
    jitter_ppq5: float
    shimmer_local: float
    shimmer_apq3: float
    shimmer_apq5: float
    shimmer_apq11: float
    speech_rate: float
    articulation_rate: float
    speech_duration: float
    pause_duration: float
    pause_ratio: float
    num_pauses: int
    mean_pause_duration: float
    cog: float
    slope: float
    spread: float


class ScoreResponse(BaseModel):
    """Combined response with features and scores"""
    success: bool
    exam_level: str
    task_code: str
    
    # Raw features
    features: Optional[AudioFeaturesDict] = None
    
    # Praat-based scores
    pronunciation: Optional[ScoreDetail] = None
    fluency: Optional[ScoreDetail] = None
    
    # Total scores
    praat_score: float = 0
    praat_max_score: float = 0
    praat_percentage: float = 0
    
    # Timing
    processing_time: float = 0
    error_message: Optional[str] = None


# ========== Helper Functions ==========

def scoring_result_to_detail(result, criteria_name: str) -> ScoreDetail:
    """Convert ScoringResult to ScoreDetail"""
    return ScoreDetail(
        criteria_name=criteria_name,
        score=result.score,
        max_score=result.max_score,
        percentage=result.percentage,
        level=result.level.value,
        issues=result.issues,
        feedback=result.feedback
    )


# ========== Endpoint ==========

@router.post(
    "/praat",
    response_model=ScoreResponse,
    summary="Extract Features and Score Audio",
    description="Upload audio file, extract Praat features, and calculate pronunciation & fluency scores"
)
async def score_audio(
    audio_file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, flac)"),
    exam_level: ExamLevel = Query(
        default=ExamLevel.BEGINNER,
        description="Exam level: 101 (beginner), 102 (intermediate), 103 (advanced)"
    ),
    task_code: TaskCode = Query(
        default=TaskCode.HSKKSC1,
        description="Task code: HSKKSC1-3, HSKKTC1-3, HSKKCC1-3"
    ),
    assessment_service: AssessmentService = Depends(get_assessment_service)
) -> ScoreResponse:
    """
    Extract Praat features and calculate scores for audio file.
    
    **Exam Levels:**
    - 101: Sơ cấp (Beginner)
    - 102: Trung cấp (Intermediate)
    - 103: Cao cấp (Advanced)
    
    **Task Codes:**
    - HSKKSC1/TC1/CC1: Nghe và nhắc lại
    - HSKKSC2/TC2: Nghe và trả lời / Mô tả tranh
    - HSKKSC3/TC3/CC3: Trả lời câu hỏi
    - HSKKCC2: Đọc đoạn văn
    """
    import time
    start_time = time.time()
    
    try:
        # Read file content
        content = await audio_file.read()
        
        # Extract raw features using assessment service
        raw_result = await assessment_service.extract_raw_features(
            audio_content=content,
            filename=audio_file.filename
        )
        
        if not raw_result.success or raw_result.features is None:
            return ScoreResponse(
                success=False,
                exam_level=exam_level.value,
                task_code=task_code.value,
                processing_time=time.time() - start_time,
                error_message=raw_result.error_message
            )
        
        # Convert features to dict for scoring
        features_dict = raw_result.features.model_dump()
        
        # Get internal level and task
        level = LEVEL_MAPPING[exam_level.value]
        task = TASK_MAPPING[task_code.value]
        
        # Initialize scorers
        pronunciation_scorer = PronunciationScorer(exam_level=level)
        fluency_scorer = FluencyScorer(exam_level=level)
        
        # Calculate scores
        pronunciation_result = pronunciation_scorer.score(features_dict, task=task)
        fluency_result = fluency_scorer.score(features_dict, task=task)
        
        # Convert to response format
        pronunciation_detail = scoring_result_to_detail(
            pronunciation_result,
            pronunciation_scorer.get_criteria_name()
        )
        fluency_detail = scoring_result_to_detail(
            fluency_result,
            fluency_scorer.get_criteria_name()
        )
        
        # Calculate totals
        total_score = pronunciation_result.score + fluency_result.score
        max_total = pronunciation_result.max_score + fluency_result.max_score
        total_pct = (total_score / max_total * 100) if max_total > 0 else 0
        
        return ScoreResponse(
            success=True,
            exam_level=exam_level.value,
            task_code=task_code.value,
            features=AudioFeaturesDict(**features_dict),
            pronunciation=pronunciation_detail,
            fluency=fluency_detail,
            praat_score=round(total_score, 2),
            praat_max_score=round(max_total, 2),
            praat_percentage=round(total_pct, 1),
            processing_time=round(time.time() - start_time, 3)
        )
        
    except Exception as e:
        logger.error(f"Scoring error: {e}")
        return ScoreResponse(
            success=False,
            exam_level=exam_level.value,
            task_code=task_code.value,
            processing_time=round(time.time() - start_time, 3),
            error_message=str(e)
        )
