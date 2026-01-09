"""
Scoring API - Full scoring pipeline using Multi-Model STT + Praat + AI
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
from app.scorers.task_criteria_config import (
    get_task_config, get_max_scores_for_task, task_requires_reference,
    CriteriaType, DataSource, TaskConfig
)
from app.constants.audio import (
    AUDIO_SAMPLE_RATE, AUDIO_NORMALIZE_MAX, AUDIO_HASH_LENGTH,
    AUDIO_HASH_PREFIX_BYTES, PRAAT_TIMEOUT_SECONDS, PRAAT_PCM_SUBTYPE
)
from app.constants.messages import ERROR_SCORING

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


class OpenAIModel(str, Enum):
    """Available OpenAI models for testing"""
    GPT_5_MINI = "gpt-5-mini"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"


class GeminiModel(str, Enum):
    """Available Gemini models for testing"""
    GEMINI_2_0_FLASH = "gemini-2.0-flash-exp"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"


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


class TaskInfo(BaseModel):
    """Task metadata"""
    task_code: str
    task_name: str
    exam_level: str
    criteria_count: int
    criteria_types: List[str]
    total_max_score: float


class MultiModelSTTResult(BaseModel):
    """Multi-model STT results"""
    whisper: str = Field(default="", description="OpenAI Whisper STT result")
    fun_asr: str = Field(default="", description="FunASR local STT result")
    gemini: str = Field(default="", description="Gemini multimodal STT result")


class WordAnalysis(BaseModel):
    """Per-word acoustic analysis (HSKK-relevant only)"""
    char: str
    start: float
    end: float
    duration: float
    # Pitch (for tonal assessment)
    pitch_mean: float = 0
    pitch_std: float = 0
    # Voice quality
    hnr: float = 0
    # Assessment
    quality: str = "unknown"  # good, needs_improvement, poor
    issues: List[str] = Field(default_factory=list)


class WordAnalysisSummary(BaseModel):
    """Summary of word-level analysis"""
    total_words: int = 0
    good_count: int = 0
    needs_improvement_count: int = 0
    poor_count: int = 0
    average_pitch: float = 0
    average_hnr: float = 0


class FullScoreResponse(BaseModel):
    """Full response with features and all scores"""
    success: bool
    task_info: Optional[TaskInfo] = None
    
    # Multi-Model STT results
    stt: Optional[MultiModelSTTResult] = None
    
    # Scores by criteria
    scores: Dict[str, ScoreDetail] = Field(default_factory=dict)
    
    # Word-level analysis (optional)
    word_analysis: Optional[List[WordAnalysis]] = None
    word_analysis_summary: Optional[WordAnalysisSummary] = None
    word_feedback: Optional[dict] = Field(None, description="GPT-generated structured assessment with overall_assessment, problem_areas, improvement_tips")
    
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


async def run_unified_praat_analysis(
    assessment_service,
    audio_content: bytes,
    filename: str
) -> Optional[dict]:
    """
    Run the unified Praat script that extracts both overall and per-interval features.
    Returns parsed JSON data or None if failed.
    """
    import subprocess
    import json
    import hashlib
    import tempfile
    import soundfile as sf
    import numpy as np
    from pathlib import Path
    
    try:
        # Generate unique filename
        audio_hash = hashlib.md5(audio_content[:AUDIO_HASH_PREFIX_BYTES]).hexdigest()[:AUDIO_HASH_LENGTH]
        base_name = Path(filename).stem
        audio_filename = f"{base_name}_{audio_hash}_unified.wav"
        output_filename = f"{base_name}_{audio_hash}_unified.json"
        
        settings = assessment_service.settings
        audio_input_dir = settings.audio_input_dir
        praat_output_dir = settings.praat_output_dir
        
        # Step 1: Write raw audio to temp file first
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(audio_content)
            temp_input_path = Path(tmp.name)
        
        # Step 2: Preprocess audio to WAV format for Praat
        try:
            # Load with librosa (handles various formats)
            import librosa
            audio, sr = librosa.load(str(temp_input_path), sr=AUDIO_SAMPLE_RATE, mono=True)
            
            # Normalize
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * AUDIO_NORMALIZE_MAX
            
            # Save as WAV to shared directory
            audio_path = audio_input_dir / audio_filename
            sf.write(str(audio_path), audio, sr, subtype=PRAAT_PCM_SUBTYPE)
            
            logger.info(f"Preprocessed audio for Praat: {audio_path}")
            
        finally:
            # Cleanup temp file
            temp_input_path.unlink(missing_ok=True)
        
        # Step 3: Run unified Praat script
        container_name = settings.praat_container_name
        container_audio = f"/data/audio_input/{audio_filename}"
        container_output = f"/data/praat_output/{output_filename}"
        
        cmd = [
            "docker", "exec", container_name,
            "praat", "--run", "/praat/scripts/extract_features_unified.praat",
            container_audio, container_output
        ]
        
        logger.info(f"Running unified Praat script...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PRAAT_TIMEOUT_SECONDS
        )
        
        if result.returncode != 0:
            logger.error(f"Unified Praat failed: {result.stderr}")
            audio_path.unlink(missing_ok=True)
            return None
        
        # Step 4: Read and parse JSON output
        output_path = praat_output_dir / output_filename
        if output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                praat_data = json.load(f)
            
            # Cleanup
            audio_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            
            logger.info(f"Unified Praat: {len(praat_data.get('intervals', []))} intervals extracted")
            return praat_data
        else:
            logger.error(f"Praat output not found: {output_path}")
            audio_path.unlink(missing_ok=True)
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Unified Praat timed out")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Praat JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Unified Praat error: {e}")
        return None


async def score_with_criteria(
    task_config: TaskConfig,
    features_dict: Dict[str, Any],
    transcribed_text: str,
    reference_text: Optional[str],
    ai_provider,
    settings: Settings,
    whisper_variants: List[str] = None,
    gemini_intent: str = None,
    openai_model: str = "gpt-4.1-nano"
) -> Dict[str, ScoreDetail]:
    """
    Score based on task-specific criteria.
    
    - Praat criteria: scored by PronunciationScorer, FluencyScorer
    - AI criteria: scored by Tri-Core GPT Judge (using whisper_variants + gemini_intent)
    """
    scores = {}
    level = task_config.level_name
    max_scores = get_max_scores_for_task(task_config.task_code)
    
    # Separate Praat and AI criteria
    praat_criteria = [c for c in task_config.criteria if c.source == DataSource.PRAAT]
    ai_criteria = [c for c in task_config.criteria if c.source == DataSource.AI]
    
    # Score Praat criteria
    for criteria in praat_criteria:
        criteria_type = criteria.type
        max_score = criteria.max_score
        
        try:
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
                
        except Exception as e:
            logger.error(f"Error scoring {criteria_type}: {e}")
            scores[criteria_type.value] = ScoreDetail(
                criteria_name=criteria.name_vi,
                score=0,
                max_score=max_score,
                percentage=0,
                level="error",
                issues=[f"Scoring error: {str(e)}"],
                feedback=ERROR_SCORING
            )
    
    # Score AI criteria using Unified AI Scoring (includes Praat feedback rewriting)
    if ai_criteria and whisper_variants and gemini_intent:
        from app.services.tri_core_service import unified_ai_scoring, CriteriaScore
        
        # Build AI criteria config from task config
        ai_criteria_config = {}
        criteria_names_vi = {}
        for criteria in ai_criteria:
            ai_criteria_config[criteria.type.value] = criteria.max_score
            criteria_names_vi[criteria.type.value] = criteria.name_vi
        
        # Prepare Praat pre-scores for GPT to rewrite feedback
        praat_scores_for_gpt = {}
        if "pronunciation" in scores:
            p = scores["pronunciation"]
            praat_scores_for_gpt["pronunciation"] = {
                "score": p.score,
                "max_score": p.max_score,
                "feedback": p.feedback,
                "issues": p.issues,
                "details": p.details or {}
            }
        if "fluency" in scores:
            f = scores["fluency"]
            praat_scores_for_gpt["fluency"] = {
                "score": f.score,
                "max_score": f.max_score,
                "feedback": f.feedback,
                "issues": f.issues,
                "details": f.details or {}
            }
        
        try:
            # Call Unified AI scoring (GPT scores AI criteria + rewrites Praat feedback)
            unified_result = await unified_ai_scoring(
                stt_variants=whisper_variants,
                gemini_intent=gemini_intent,
                api_key=settings.openai_api_key,
                model=openai_model,
                ai_criteria_config=ai_criteria_config,
                praat_scores=praat_scores_for_gpt if praat_scores_for_gpt else None,
                reference_text=reference_text
            )
            
            # Update Praat scores with GPT's professional feedback (keep original scores)
            for praat_name in ["pronunciation", "fluency"]:
                praat_result = getattr(unified_result, praat_name, None)
                if praat_result and praat_name in scores:
                    # Keep original Praat score but use GPT's professional feedback
                    original = scores[praat_name]
                    scores[praat_name] = ScoreDetail(
                        criteria_name=original.criteria_name,
                        score=original.score,  # Keep original score
                        max_score=original.max_score,
                        percentage=original.percentage,
                        level=original.level,
                        issues=praat_result.issues if praat_result.issues else original.issues,
                        feedback=praat_result.feedback if praat_result.feedback else original.feedback,
                        details=original.details
                    )
            
            # Add AI criteria scores from GPT
            for criteria_name in ai_criteria_config.keys():
                criteria_score = getattr(unified_result, criteria_name, None)
                if criteria_score:
                    percentage = (criteria_score.score / criteria_score.max_score * 100) if criteria_score.max_score > 0 else 0
                    scores[criteria_name] = ScoreDetail(
                        criteria_name=criteria_names_vi.get(criteria_name, criteria_name),
                        score=criteria_score.score,
                        max_score=criteria_score.max_score,
                        percentage=round(percentage, 1),
                        level="ai-scored",
                        issues=criteria_score.issues,
                        feedback=criteria_score.feedback
                    )
                else:
                    # Criteria not scored, create placeholder
                    max_score = ai_criteria_config[criteria_name]
                    scores[criteria_name] = ScoreDetail(
                        criteria_name=criteria_names_vi.get(criteria_name, criteria_name),
                        score=0,
                        max_score=max_score,
                        percentage=0,
                        level="error",
                        issues=["Không có kết quả chấm điểm"],
                        feedback=unified_result.overall_feedback or "Không thể chấm điểm"
                    )
                    
        except Exception as e:
            logger.error(f"Unified AI scoring error: {e}")
            # Fallback: create error scores for all AI criteria
            for criteria in ai_criteria:
                scores[criteria.type.value] = ScoreDetail(
                    criteria_name=criteria.name_vi,
                    score=0,
                    max_score=criteria.max_score,
                    percentage=0,
                    level="error",
                    issues=[f"Unified scoring error: {str(e)}"],
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
    openai_model: OpenAIModel = Query(
        default=OpenAIModel.GPT_4_1_NANO,
        description="OpenAI model for scoring"
    ),
    gemini_model: GeminiModel = Query(
        default=GeminiModel.GEMINI_2_5_FLASH_LITE,
        description="Gemini model for intent detection"
    ),
    enable_word_analysis: bool = Query(
        default=False,
        description="Enable per-word acoustic analysis (maps FunASR timestamps to Praat intervals)"
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
        
        # Step 1: Run STT and Praat extraction IN PARALLEL
        # If word analysis enabled, also run Praat Unified in parallel
        logger.info(f"Step 1: Multi-Model STT + Praat extraction in parallel for {task_code.value}...")
        from app.services.tri_core_service import get_multi_model_stt
        import asyncio
        
        # Create tasks for parallel execution
        # Request timestamps from FunASR if word analysis enabled (eliminates duplicate call)
        stt_task = get_multi_model_stt(
            audio_path=temp_audio_path,
            openai_api_key=settings.openai_api_key,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=gemini_model.value,
            include_timestamps=enable_word_analysis  # Request timestamps upfront
        )
        praat_task = assessment_service.extract_raw_features(
            audio_content=content,
            filename=audio_file.filename
        )
        
        # If word analysis enabled, also run Praat Unified in parallel (saves ~2-3s)
        parallel_tasks = [stt_task, praat_task]
        praat_unified_task = None
        if enable_word_analysis:
            praat_unified_task = run_unified_praat_analysis(
                assessment_service, content, audio_file.filename
            )
            parallel_tasks.append(praat_unified_task)
        
        # Run all tasks in parallel
        parallel_results = await asyncio.gather(*parallel_tasks)
        
        # Unpack results
        stt_results = parallel_results[0]  # Now returns dict with texts + funasr_words
        raw_result = parallel_results[1]
        unified_praat_data = parallel_results[2] if enable_word_analysis else None
        
        # Extract STT texts and FunASR word timestamps
        stt_texts = stt_results["texts"]
        funasr_words = stt_results.get("funasr_words", [])
        
        # Create STT result object
        stt_result = MultiModelSTTResult(
            whisper=stt_texts[0] if len(stt_texts) > 0 else "",
            fun_asr=stt_texts[1] if len(stt_texts) > 1 else "",
            gemini=stt_texts[2] if len(stt_texts) > 2 else ""
        )
        
        # Use Whisper as primary transcription for scoring
        transcribed_text = stt_result.whisper
        logger.info(f"STT complete. FunASR words: {len(funasr_words)}. Praat Unified: {'ready' if unified_praat_data else 'skipped'}")
        
        # Check Praat result
        if not raw_result.success or raw_result.features is None:
            return FullScoreResponse(
                success=False,
                task_info=task_info,
                stt=stt_result,
                processing_time=time.time() - start_time,
                error_message=raw_result.error_message
            )
        
        features_dict = raw_result.features.model_dump()
        
        # Step 2: Score with task-specific criteria
        # If word analysis enabled, run GPT Word Feedback in PARALLEL with AI Scoring (saves ~2-3s)
        logger.info(f"Step 2: Scoring {len(task_config.criteria)} criteria...")
        ai_provider = get_ai_provider(
            AIProviderType.OPENAI,
            settings.openai_api_key,
            settings.openai_model
        )
        
        # Prepare word analysis data first (if enabled and data available)
        word_analysis_list = None
        word_analysis_summary_obj = None
        word_result = None
        
        if enable_word_analysis and unified_praat_data and funasr_words:
            from app.services.word_analysis_service import analyze_words
            logger.info(f"Analyzing {len(funasr_words)} words from FunASR...")
            word_result = analyze_words(funasr_words, unified_praat_data)
            
            # Convert to response models
            word_analysis_list = [
                WordAnalysis(
                    char=w.char,
                    start=w.start,
                    end=w.end,
                    duration=w.duration,
                    pitch_mean=w.pitch_mean,
                    pitch_std=w.pitch_std,
                    hnr=w.hnr,
                    quality=w.quality,
                    issues=w.issues or []
                )
                for w in word_result.words
            ]
            
            word_analysis_summary_obj = WordAnalysisSummary(
                total_words=word_result.total_words,
                good_count=word_result.good_count,
                needs_improvement_count=word_result.needs_improvement_count,
                poor_count=word_result.poor_count,
                average_pitch=word_result.average_pitch,
                average_hnr=word_result.average_hnr
            )
            logger.info(f"Word analysis: {word_result.good_count}/{word_result.total_words} good")
        
        # Create scoring task
        scoring_task = score_with_criteria(
            task_config=task_config,
            features_dict=features_dict,
            transcribed_text=transcribed_text,
            reference_text=reference_text,
            ai_provider=ai_provider,
            settings=settings,
            whisper_variants=stt_texts,
            gemini_intent=stt_result.gemini,
            openai_model=openai_model.value
        )
        
        # Run AI scoring and GPT Word Feedback in PARALLEL (if word analysis enabled)
        word_feedback_text = None
        if enable_word_analysis and word_result:
            from app.services.word_analysis_service import get_gpt_word_feedback
            word_feedback_task = get_gpt_word_feedback(
                word_result=word_result,
                transcribed_text=transcribed_text,
                api_key=settings.openai_api_key,
                model=openai_model.value
            )
            # Run both in parallel
            scores, word_feedback_text = await asyncio.gather(scoring_task, word_feedback_task)
            logger.info("Scoring + GPT word feedback completed in parallel")
        else:
            # Just run scoring
            scores = await scoring_task
        
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
            word_analysis=word_analysis_list,
            word_analysis_summary=word_analysis_summary_obj,
            word_feedback=word_feedback_text,
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
