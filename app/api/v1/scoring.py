"""
Scoring API - Extract features, transcribe audio, and score using Praat + AI
Dynamic criteria selection based on task_code
"""
from enum import Enum
from typing import Optional, Dict, List, Any
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException
from pydantic import BaseModel, Field
import logging
import tempfile
import os

from app.core.config import Settings, get_settings
from app.core.dependencies import get_assessment_service
from app.services.assessment_service import AssessmentService
from app.scorers.praat_scorers import PronunciationScorer, FluencyScorer
from app.scorers.ai_scorers.ai_provider import get_ai_provider, AIProviderType
from app.scorers.ai_scorers.task_achievement_scorer import TaskAchievementScorer
from app.scorers.ai_scorers.grammar_scorer import GrammarScorer
from app.scorers.ai_scorers.vocabulary_scorer import VocabularyScorer
from app.scorers.ai_scorers.coherence_scorer import CoherenceScorer
from app.scorers.task_criteria_config import (
    get_task_config, get_criteria_for_task, get_max_scores_for_task,
    task_requires_reference, CriteriaType, DataSource, TaskConfig
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/score", tags=["Scoring"])


# ========== Enums ==========

class TaskCode(str, Enum):
    """HSKK Task codes"""
    HSKKSC1 = "HSKKSC1"
    HSKKSC2 = "HSKKSC2"
    HSKKSC3 = "HSKKSC3"
    HSKKTC1 = "HSKKTC1"
    HSKKTC2 = "HSKKTC2"
    HSKKTC3 = "HSKKTC3"
    HSKKCC1 = "HSKKCC1"
    HSKKCC2 = "HSKKCC2"
    HSKKCC3 = "HSKKCC3"


class ExamLevel(str, Enum):
    """HSKK Exam levels"""
    BEGINNER = "101"
    INTERMEDIATE = "102"
    ADVANCED = "103"


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
    details: Optional[dict] = None


class STTResult(BaseModel):
    """Speech-to-text result"""
    transcribed_text: str
    language: str = "zh"


class TaskInfo(BaseModel):
    """Task metadata"""
    task_code: str
    task_name: str
    exam_level: str
    criteria_count: int
    criteria_types: List[str]
    total_max_score: float


class FullScoreResponse(BaseModel):
    """Full response with features and all scores"""
    success: bool
    task_info: Optional[TaskInfo] = None
    
    # STT result
    stt: Optional[STTResult] = None
    
    # Scores by criteria
    scores: Dict[str, ScoreDetail] = Field(default_factory=dict)
    
    # Summary
    total_score: float = 0
    max_total_score: float = 0
    total_percentage: float = 0
    
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
        feedback=result.feedback,
        details=result.details if hasattr(result, 'details') else None
    )


async def transcribe_audio_with_whisper(audio_path: Path, api_key: str) -> str:
    """Transcribe audio using OpenAI Whisper"""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key=api_key)
    
    with open(audio_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="zh"
        )
    
    logger.info(f"Transcribed: {transcription.text[:100]}...")
    return transcription.text


async def score_with_criteria(
    task_config: TaskConfig,
    features_dict: Dict[str, Any],
    transcribed_text: str,
    reference_text: Optional[str],
    ai_provider,
    settings: Settings
) -> Dict[str, ScoreDetail]:
    """Score based on task-specific criteria"""
    scores = {}
    level = task_config.level_name
    max_scores = get_max_scores_for_task(task_config.task_code)
    
    for criteria in task_config.criteria:
        criteria_type = criteria.type
        max_score = criteria.max_score
        
        try:
            if criteria.source == DataSource.PRAAT:
                # Praat-based scoring
                if criteria_type == CriteriaType.PRONUNCIATION:
                    scorer = PronunciationScorer(exam_level=level)
                    scorer.max_scores[level] = {"task": max_score}
                    result = scorer.score(features_dict, task="task")
                    scores["pronunciation"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
                elif criteria_type == CriteriaType.FLUENCY:
                    scorer = FluencyScorer(exam_level=level)
                    scorer.max_scores[level] = {"task": max_score}
                    result = scorer.score(features_dict, task="task")
                    scores["fluency"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
            elif criteria.source == DataSource.AI:
                # AI-based scoring
                text_data = {"text": transcribed_text}
                
                if criteria_type == CriteriaType.TASK_ACHIEVEMENT:
                    scorer = TaskAchievementScorer(ai_provider, level)
                    if criteria.requires_reference and reference_text:
                        result = await scorer.score(
                            text_data, 
                            task="task1",
                            reference_text=reference_text
                        )
                    else:
                        result = await scorer.score(text_data, task="task3")
                    # Adjust max score
                    result.max_score = max_score
                    result.score = min(result.score, max_score)
                    scores["task_achievement"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
                elif criteria_type == CriteriaType.GRAMMAR:
                    scorer = GrammarScorer(ai_provider, level)
                    result = await scorer.score(text_data, task="task")
                    result.max_score = max_score
                    result.score = min(result.score, max_score)
                    scores["grammar"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
                elif criteria_type == CriteriaType.VOCABULARY:
                    scorer = VocabularyScorer(ai_provider, level)
                    result = await scorer.score(text_data, task="task")
                    result.max_score = max_score
                    result.score = min(result.score, max_score)
                    scores["vocabulary"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
                elif criteria_type == CriteriaType.COHERENCE:
                    scorer = CoherenceScorer(ai_provider, level)
                    result = await scorer.score(text_data, task="task")
                    result.max_score = max_score
                    result.score = min(result.score, max_score)
                    scores["coherence"] = scoring_result_to_detail(
                        result, criteria.name_vi
                    )
                    
        except Exception as e:
            logger.error(f"Error scoring {criteria_type}: {e}")
            # Create error score detail
            scores[criteria_type.value] = ScoreDetail(
                criteria_name=criteria.name_vi,
                score=0,
                max_score=max_score,
                percentage=0,
                level="error",
                issues=[f"Scoring error: {str(e)}"],
                feedback="Không thể chấm điểm tiêu chí này"
            )
    
    return scores


# ========== Endpoints ==========

@router.post(
    "/full",
    response_model=FullScoreResponse,
    summary="Full Scoring with STT + Praat + AI",
    description="Upload audio, transcribe with Whisper, and score based on task-specific criteria"
)
async def full_score_audio(
    audio_file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, flac)"),
    exam_level: ExamLevel = Query(
        default=ExamLevel.BEGINNER,
        description="Exam level: 101, 102, 103"
    ),
    task_code: TaskCode = Query(
        default=TaskCode.HSKKSC1,
        description="Task code: HSKKSC1-3, HSKKTC1-3, HSKKCC1-3"
    ),
    reference_text: Optional[str] = Query(
        default=None,
        description="Reference text for repeat/read tasks (required for task1 types)"
    ),
    assessment_service: AssessmentService = Depends(get_assessment_service),
    settings: Settings = Depends(get_settings)
) -> FullScoreResponse:
    """
    Full scoring pipeline based on task-specific criteria.
    
    Each task has different criteria:
    - HSKKSC1: 3 criteria (Task Achievement, Pronunciation, Fluency)
    - HSKKSC2: 4 criteria (Task Achievement, Grammar, Pronunciation, Fluency)
    - HSKKSC3: 6 criteria (All)
    - etc.
    """
    import time
    start_time = time.time()
    
    # Get task configuration
    task_config = get_task_config(task_code.value)
    if not task_config:
        raise HTTPException(status_code=400, detail=f"Unknown task code: {task_code}")
    
    # Check API key for AI criteria
    if task_config.has_ai_criteria and not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY required for AI-based scoring"
        )
    
    # Check reference text for similarity tasks
    if task_requires_reference(task_code.value) and not reference_text:
        logger.warning(f"Task {task_code} requires reference_text for accurate scoring")
    
    try:
        content = await audio_file.read()
        
        # Create task info
        task_info = TaskInfo(
            task_code=task_config.task_code,
            task_name=task_config.task_name,
            exam_level=task_config.exam_level,
            criteria_count=len(task_config.criteria),
            criteria_types=[c.type.value for c in task_config.criteria],
            total_max_score=sum(c.max_score for c in task_config.criteria)
        )
        
        # Save to temp file for Whisper
        temp_dir = tempfile.mkdtemp()
        temp_audio_path = Path(temp_dir) / audio_file.filename
        
        with open(temp_audio_path, "wb") as f:
            f.write(content)
        
        # Step 1: Transcribe with Whisper
        logger.info(f"Step 1: Transcribing for {task_code.value}...")
        transcribed_text = await transcribe_audio_with_whisper(
            temp_audio_path,
            settings.openai_api_key
        )
        stt_result = STTResult(transcribed_text=transcribed_text)
        
        # Step 2: Extract Praat features
        logger.info("Step 2: Extracting Praat features...")
        raw_result = await assessment_service.extract_raw_features(
            audio_content=content,
            filename=audio_file.filename
        )
        
        if not raw_result.success or raw_result.features is None:
            return FullScoreResponse(
                success=False,
                task_info=task_info,
                stt=stt_result,
                processing_time=time.time() - start_time,
                error_message=raw_result.error_message
            )
        
        features_dict = raw_result.features.model_dump()
        
        # Step 3: Score with task-specific criteria
        logger.info(f"Step 3: Scoring {len(task_config.criteria)} criteria...")
        ai_provider = get_ai_provider(
            AIProviderType.OPENAI,
            settings.openai_api_key,
            settings.openai_model
        )
        
        scores = await score_with_criteria(
            task_config=task_config,
            features_dict=features_dict,
            transcribed_text=transcribed_text,
            reference_text=reference_text,
            ai_provider=ai_provider,
            settings=settings
        )
        
        # Cleanup
        os.unlink(temp_audio_path)
        os.rmdir(temp_dir)
        
        # Calculate totals
        total_score = sum(s.score for s in scores.values())
        max_total = sum(s.max_score for s in scores.values())
        total_pct = (total_score / max_total * 100) if max_total > 0 else 0
        
        return FullScoreResponse(
            success=True,
            task_info=task_info,
            stt=stt_result,
            scores=scores,
            total_score=round(total_score, 2),
            max_total_score=round(max_total, 2),
            total_percentage=round(total_pct, 1),
            processing_time=round(time.time() - start_time, 3)
        )
        
    except Exception as e:
        logger.error(f"Full scoring error: {e}", exc_info=True)
        return FullScoreResponse(
            success=False,
            task_info=TaskInfo(
                task_code=task_code.value,
                task_name="",
                exam_level=exam_level.value,
                criteria_count=0,
                criteria_types=[],
                total_max_score=0
            ),
            processing_time=round(time.time() - start_time, 3),
            error_message=str(e)
        )


@router.post(
    "/praat",
    response_model=FullScoreResponse,
    summary="Praat-only Scoring (No AI)",
    description="Score using only Praat features (faster, no API key needed)"
)
async def praat_only_score(
    audio_file: UploadFile = File(..., description="Audio file"),
    exam_level: ExamLevel = Query(default=ExamLevel.BEGINNER),
    task_code: TaskCode = Query(default=TaskCode.HSKKSC1),
    assessment_service: AssessmentService = Depends(get_assessment_service)
) -> FullScoreResponse:
    """
    Praat-only scoring - only Pronunciation and Fluency.
    Faster and doesn't require API keys.
    """
    import time
    start_time = time.time()
    
    task_config = get_task_config(task_code.value)
    if not task_config:
        raise HTTPException(status_code=400, detail=f"Unknown task code: {task_code}")
    
    try:
        content = await audio_file.read()
        
        # Get only Praat criteria
        praat_criteria = [c for c in task_config.criteria if c.source == DataSource.PRAAT]
        
        task_info = TaskInfo(
            task_code=task_config.task_code,
            task_name=task_config.task_name,
            exam_level=task_config.exam_level,
            criteria_count=len(praat_criteria),
            criteria_types=[c.type.value for c in praat_criteria],
            total_max_score=sum(c.max_score for c in praat_criteria)
        )
        
        # Extract features
        raw_result = await assessment_service.extract_raw_features(
            audio_content=content,
            filename=audio_file.filename
        )
        
        if not raw_result.success or raw_result.features is None:
            return FullScoreResponse(
                success=False,
                task_info=task_info,
                processing_time=time.time() - start_time,
                error_message=raw_result.error_message
            )
        
        features_dict = raw_result.features.model_dump()
        level = task_config.level_name
        scores = {}
        
        # Score Praat criteria only
        for criteria in praat_criteria:
            if criteria.type == CriteriaType.PRONUNCIATION:
                scorer = PronunciationScorer(exam_level=level)
                scorer.max_scores[level] = {"task": criteria.max_score}
                result = scorer.score(features_dict, task="task")
                scores["pronunciation"] = scoring_result_to_detail(result, criteria.name_vi)
                
            elif criteria.type == CriteriaType.FLUENCY:
                scorer = FluencyScorer(exam_level=level)
                scorer.max_scores[level] = {"task": criteria.max_score}
                result = scorer.score(features_dict, task="task")
                scores["fluency"] = scoring_result_to_detail(result, criteria.name_vi)
        
        total_score = sum(s.score for s in scores.values())
        max_total = sum(s.max_score for s in scores.values())
        total_pct = (total_score / max_total * 100) if max_total > 0 else 0
        
        return FullScoreResponse(
            success=True,
            task_info=task_info,
            scores=scores,
            total_score=round(total_score, 2),
            max_total_score=round(max_total, 2),
            total_percentage=round(total_pct, 1),
            processing_time=round(time.time() - start_time, 3)
        )
        
    except Exception as e:
        logger.error(f"Praat scoring error: {e}")
        return FullScoreResponse(
            success=False,
            processing_time=round(time.time() - start_time, 3),
            error_message=str(e)
        )


@router.get(
    "/task-info/{task_code}",
    summary="Get Task Info",
    description="Get criteria information for a specific task"
)
async def get_task_info(task_code: TaskCode):
    """Get task configuration and criteria list"""
    config = get_task_config(task_code.value)
    if not config:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_code}")
    
    return {
        "task_code": config.task_code,
        "task_name": config.task_name,
        "exam_level": config.exam_level,
        "level_name": config.level_name,
        "question_count": config.question_count,
        "points_per_question": config.points_per_question,
        "total_points": config.total_points,
        "criteria": [
            {
                "type": c.type.value,
                "source": c.source.value,
                "max_score": c.max_score,
                "name": c.name_vi,
                "requires_reference": c.requires_reference
            }
            for c in config.criteria
        ],
        "total_max_score": sum(c.max_score for c in config.criteria)
    }


@router.post(
    "/transcribe",
    response_model=STTResult,
    summary="Transcribe Audio Only"
)
async def transcribe_only(
    audio_file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
) -> STTResult:
    """Transcribe Chinese audio using OpenAI Whisper"""
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    content = await audio_file.read()
    
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / audio_file.filename
    
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        text = await transcribe_audio_with_whisper(temp_path, settings.openai_api_key)
        return STTResult(transcribed_text=text)
    finally:
        os.unlink(temp_path)
        os.rmdir(temp_dir)
