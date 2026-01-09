"""
Tri-Core Speech Assessment Service
Architecture: Whisper (Stability Check) + Gemini (Intent Detection) + gpt-5-mini (Judge)

This service implements a tri-core approach for Chinese pronunciation assessment:
1. Whisper - Called 3x with different temperatures to check speech stability
2. Gemini - Uses multimodal capability to detect intended sentence with grammar corrections
3. gpt-5-mini - Acts as judge, comparing all inputs to provide final assessment

All API calls run in parallel for optimal performance (~3-5 seconds total).
"""

import asyncio
import logging
import json
import base64
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.constants.models import (
    WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_TEMPERATURE,
    FUNASR_MODEL, FUNASR_VERSION, FUNASR_DEVICE, FUNASR_DISABLE_UPDATE,
    DEFAULT_GPT_MODEL, GPT_SCORING_TEMPERATURE,
    DEFAULT_AI_CRITERIA_CONFIG
)
from app.constants.audio import AUDIO_MIME_TYPES

logger = logging.getLogger(__name__)


# ========== Response Schemas ==========

class CriteriaScore(BaseModel):
    """Score for individual AI criteria"""
    score: float = Field(ge=0, le=100)
    max_score: float
    feedback: str = ""
    issues: List[str] = Field(default_factory=list)


class TriCoreScoringResult(BaseModel):
    """Result from Tri-Core AI criteria scoring (includes both Praat and AI)"""
    # Praat criteria (pre-scored, feedback rewritten by GPT)
    pronunciation: Optional[CriteriaScore] = None
    fluency: Optional[CriteriaScore] = None
    # AI criteria (scored by GPT)
    task_achievement: Optional[CriteriaScore] = None
    grammar: Optional[CriteriaScore] = None
    vocabulary: Optional[CriteriaScore] = None
    coherence: Optional[CriteriaScore] = None
    overall_feedback: str = ""


# ========== Multi-Model STT Functions ==========

# FunASR model singleton (loaded once for performance)
_funasr_model = None

def _get_funasr_model():
    """Load FunASR model (singleton pattern for performance)"""
    global _funasr_model
    if _funasr_model is None:
        try:
            from funasr import AutoModel
            logger.info(f"Loading FunASR {FUNASR_MODEL} model...")
            _funasr_model = AutoModel(
                model=FUNASR_MODEL,
                model_revision=FUNASR_VERSION,
                disable_update=FUNASR_DISABLE_UPDATE,
                device=FUNASR_DEVICE
            )
            logger.info("FunASR model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FunASR model: {e}")
            _funasr_model = None
    return _funasr_model


async def transcribe_with_whisper(audio_data: bytes, filename: str, api_key: str) -> str:
    """
    STT Model 1: OpenAI Whisper (temp=0)
    - Most deterministic, baseline accuracy
    - Cloud API, requires API key
    """
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        transcription = await client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=(filename, audio_data),
            language=WHISPER_LANGUAGE,
            temperature=WHISPER_TEMPERATURE
        )
        logger.info(f"Whisper STT: {transcription.text[:50]}...")
        return transcription.text
    except Exception as e:
        logger.error(f"Whisper STT error: {e}")
        return f"[Whisper Error: {e}]"


async def transcribe_with_funasr(audio_path: Path, include_timestamps: bool = False) -> dict:
    """
    STT Model 2: FunASR paraformer-zh (Local)
    - Fast inference on CPU
    - No API cost, runs locally
    - Open-source Chinese ASR model from Alibaba
    
    Args:
        audio_path: Path to audio file
        include_timestamps: If True, return word-level timestamps
    
    Returns:
        dict: {"text": str, "words": list} - words only populated if include_timestamps=True
    """
    import asyncio
    
    try:
        model = _get_funasr_model()
        if model is None:
            return {"text": "[FunASR Error: Model not loaded]", "words": []}
        
        # FunASR is sync, run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model.generate(
                input=str(audio_path),
                sentence_timestamp=include_timestamps  # Always get timestamps when requested
            )
        )
        
        if not result or len(result) == 0:
            return {"text": "", "words": []}
        
        raw = result[0]
        text = raw.get('text', '').replace(" ", "")
        
        words = []
        if include_timestamps:
            # Parse timestamps from FunASR output
            if 'timestamp' in raw:
                timestamps = raw['timestamp']
                chars = list(text.replace(" ", ""))
                for i, ts in enumerate(timestamps):
                    if i < len(chars):
                        words.append({
                            "char": chars[i],
                            "start": ts[0] / 1000.0,
                            "end": ts[1] / 1000.0
                        })
            elif 'sentence_info' in raw:
                for sentence in raw['sentence_info']:
                    for w in sentence.get('words', []):
                        words.append({
                            "char": w.get('word', ''),
                            "start": w.get('start', 0) / 1000.0,
                            "end": w.get('end', 0) / 1000.0
                        })
        
        logger.info(f"FunASR STT: {text[:50]}... (timestamps: {len(words)} words)")
        return {"text": text, "words": words}
        
    except Exception as e:
        logger.error(f"FunASR STT error: {e}")
        return {"text": f"[FunASR Error: {e}]", "words": []}


async def transcribe_with_funasr_timestamps(audio_path: Path) -> dict:
    """
    FunASR with word-level timestamps for word analysis.
    
    Returns:
        dict: {
            "text": "完整文本",
            "words": [
                {"char": "准", "start": 0.5, "end": 0.7},
                {"char": "备", "start": 0.7, "end": 0.9},
                ...
            ]
        }
    """
    import asyncio
    
    try:
        model = _get_funasr_model()
        if model is None:
            return {"text": "", "words": []}
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model.generate(
                input=str(audio_path),
                sentence_timestamp=True  # Enable timestamps
            )
        )
        
        if not result or len(result) == 0:
            return {"text": "", "words": []}
        
        raw = result[0]
        text = raw.get('text', '').replace(" ", "")
        
        # Parse timestamps from FunASR output
        words = []
        
        # FunASR returns timestamps in 'timestamp' field
        if 'timestamp' in raw:
            timestamps = raw['timestamp']
            chars = list(text.replace(" ", ""))
            
            # timestamps format: [[start_ms, end_ms], ...]
            for i, ts in enumerate(timestamps):
                if i < len(chars):
                    words.append({
                        "char": chars[i],
                        "start": ts[0] / 1000.0,  # Convert ms to seconds
                        "end": ts[1] / 1000.0
                    })
        
        # Fallback: if sentence structure available
        elif 'sentence_info' in raw:
            for sentence in raw['sentence_info']:
                sentence_words = sentence.get('words', [])
                for w in sentence_words:
                    words.append({
                        "char": w.get('word', ''),
                        "start": w.get('start', 0) / 1000.0,
                        "end": w.get('end', 0) / 1000.0
                    })
        
        logger.info(f"FunASR timestamps: {len(words)} words extracted")
        return {"text": text, "words": words}
        
    except Exception as e:
        logger.error(f"FunASR timestamps error: {e}")
        return {"text": "", "words": []}


async def transcribe_with_gemini_stt(audio_path: Path, api_key: str, model: str = "gemini-2.5-flash-lite") -> str:
    """
    STT Model 3: Gemini Multimodal STT
    - Uses Gemini's audio understanding capability
    - Pure transcription (no grammar correction)
    - Uses prompts from prompts.py for language flexibility
    """
    import google.generativeai as genai
    from app.services.prompts import PROMPTS
    
    try:
        genai.configure(api_key=api_key)
        
        # Read audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Determine MIME type
        suffix = audio_path.suffix.lower()
        mime_type = AUDIO_MIME_TYPES.get(suffix, "audio/wav")
        
        # Get prompt from prompts module (flexible language)
        prompt = PROMPTS.gemini_stt
        
        gemini_model = genai.GenerativeModel(model)
        
        # Create inline data for audio
        audio_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(audio_data).decode("utf-8")
            }
        }
        
        # Use async API
        response = await gemini_model.generate_content_async([prompt, audio_part])
        text = response.text.strip()
        logger.info(f"Gemini STT: {text[:50]}...")
        return text
        
    except Exception as e:
        logger.error(f"Gemini STT error: {e}")
        return f"[Gemini STT Error: {e}]"


async def get_multi_model_stt(
    audio_path: Path,
    openai_api_key: str,
    gemini_api_key: str,
    gemini_model: str = "gemini-2.5-flash-lite",
    include_timestamps: bool = False
) -> dict:
    """
    Call 3 different STT models in parallel for voting.
    
    Models:
    1. OpenAI Whisper (temp=0) - Cloud, baseline accuracy
    2. FunASR paraformer-zh - Local, fast, no cost (with optional timestamps)
    3. Gemini STT - Cloud, multimodal, different approach
    
    If all 3 results are similar -> stable/clear pronunciation
    If results vary significantly -> pronunciation issues detected
    
    Args:
        include_timestamps: If True, FunASR returns word-level timestamps for reuse
    
    Returns:
        dict: {
            "texts": [whisper, funasr, gemini],
            "funasr_words": [...] if include_timestamps else []
        }
    """
    # Read audio data for Whisper
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    filename = audio_path.name
    
    # Run all 3 STT models in parallel (FunASR with timestamps if requested)
    whisper_task = transcribe_with_whisper(audio_data, filename, openai_api_key)
    funasr_task = transcribe_with_funasr(audio_path, include_timestamps=include_timestamps)
    gemini_task = transcribe_with_gemini_stt(audio_path, gemini_api_key, gemini_model)
    
    whisper_result, funasr_result, gemini_result = await asyncio.gather(
        whisper_task, funasr_task, gemini_task
    )
    
    # Extract texts (FunASR now returns dict)
    texts = [
        whisper_result,
        funasr_result["text"],
        gemini_result
    ]
    
    logger.info(f"Multi-Model STT: {[t[:30]+'...' if len(t) > 30 else t for t in texts]}")
    
    return {
        "texts": texts,
        "funasr_words": funasr_result.get("words", [])
    }


# ========== Tri-Core AI Criteria Scoring ==========

async def tri_core_ai_scoring(
    whisper_variants: List[str],
    gemini_intent: str,
    api_key: str,
    model: str = "gpt-4.1-nano",
    criteria_config: Optional[Dict[str, float]] = None,
    reference_text: Optional[str] = None
) -> TriCoreScoringResult:
    """
    Score AI criteria using Tri-Core GPT Judge.
    Uses prompts from prompts.py for flexible language switching.
    
    Args:
        whisper_variants: 3 STT transcriptions (Whisper, FunASR, Gemini)
        gemini_intent: Gemini's grammar-corrected transcription
        api_key: OpenAI API key
        model: GPT model to use
        criteria_config: Dict mapping criteria name to max_score
        reference_text: Optional reference text for task achievement
    
    Returns:
        TriCoreScoringResult with scores for each AI criteria
    """
    from openai import AsyncOpenAI
    from app.services.prompts import PROMPTS
    
    client = AsyncOpenAI(api_key=api_key)
    
    # Default criteria config if not provided
    if criteria_config is None:
        criteria_config = {
            "task_achievement": 20,
            "grammar": 15,
            "vocabulary": 10,
            "coherence": 10
        }
    
    # Build criteria description using prompts module
    criteria_list = []
    for name, max_score in criteria_config.items():
        criteria_name = PROMPTS.criteria_names.get(name, name)
        criteria_list.append(f"- {criteria_name}: 0-{max_score}")
    
    criteria_str = "\n".join(criteria_list)
    
    # Get reference section from prompts
    reference_section = ""
    if reference_text:
        reference_section = PROMPTS.get_reference_section(reference_text)
    
    # Build prompts using prompts module
    system_prompt = PROMPTS.get_ai_scoring_system(criteria_str, criteria_config)
    user_prompt = PROMPTS.get_ai_scoring_user(whisper_variants, gemini_intent, reference_section)


    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        result_text = response.choices[0].message.content
        result_dict = json.loads(result_text)
        
        logger.info(f"Tri-Core AI Scoring result: {result_dict}")
        
        # Parse results into TriCoreScoringResult
        result = TriCoreScoringResult(overall_feedback=result_dict.get("overall_feedback", ""))
        
        for criteria_name, max_score in criteria_config.items():
            if criteria_name in result_dict:
                criteria_data = result_dict[criteria_name]
                score_obj = CriteriaScore(
                    score=min(criteria_data.get("score", 0), max_score),
                    max_score=max_score,
                    feedback=criteria_data.get("feedback", ""),
                    issues=criteria_data.get("issues", [])
                )
                setattr(result, criteria_name, score_obj)
        
        return result
        
    except Exception as e:
        logger.error(f"Tri-Core AI Scoring error: {e}")
        # Return empty result with error feedback
        return TriCoreScoringResult(
            overall_feedback=f"Lỗi khi chấm điểm: {str(e)}"
        )


# ========== Unified AI Scoring (Praat + AI Criteria) ==========

async def unified_ai_scoring(
    stt_variants: List[str],
    gemini_intent: str,
    api_key: str,
    model: str = "gpt-4.1-nano",
    ai_criteria_config: Optional[Dict[str, float]] = None,
    praat_scores: Optional[Dict[str, Any]] = None,
    reference_text: Optional[str] = None
) -> TriCoreScoringResult:
    """
    Unified scoring function that sends both Praat and AI criteria to GPT.
    
    GPT will:
    1. Keep Praat scores (pronunciation, fluency) but rewrite feedback professionally
    2. Score AI criteria (task_achievement, grammar, vocabulary, coherence)
    3. Generate overall_feedback in Vietnamese
    
    Args:
        stt_variants: 3 STT transcriptions (Whisper, FunASR, Gemini STT)
        gemini_intent: Gemini's grammar-corrected transcription (intent)
        api_key: OpenAI API key
        model: GPT model to use
        ai_criteria_config: Dict mapping AI criteria name to max_score
        praat_scores: Dict with Praat pre-scores (pronunciation, fluency)
        reference_text: Optional reference text for task achievement
    
    Returns:
        TriCoreScoringResult with all criteria (Praat + AI)
    """
    from openai import AsyncOpenAI
    from app.services.prompts import PROMPTS
    
    client = AsyncOpenAI(api_key=api_key)
    
    # Default AI criteria config
    if ai_criteria_config is None:
        ai_criteria_config = {
            "task_achievement": 20,
            "grammar": 15,
            "vocabulary": 10,
            "coherence": 10
        }
    
    # Build prompts using unified methods
    has_praat = praat_scores is not None and len(praat_scores) > 0
    system_prompt = PROMPTS.get_unified_scoring_system(ai_criteria_config, has_praat=has_praat)
    user_prompt = PROMPTS.get_unified_scoring_user(
        stt_variants=stt_variants,
        gemini_intent=gemini_intent,
        praat_scores=praat_scores,
        reference_text=reference_text,
        criteria_config=ai_criteria_config
    )
    
    logger.info(f"Unified AI Scoring - Praat included: {has_praat}, AI criteria: {list(ai_criteria_config.keys())}")
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        result_text = response.choices[0].message.content
        result_dict = json.loads(result_text)
        
        logger.info(f"Unified AI Scoring result: {list(result_dict.keys())}")
        
        # Build result object
        result = TriCoreScoringResult(overall_feedback=result_dict.get("overall_feedback", ""))
        
        # Parse Praat criteria (use GPT's feedback but keep original score)
        for praat_name in ["pronunciation", "fluency"]:
            if praat_name in result_dict:
                gpt_data = result_dict[praat_name]
                # Get original score from praat_scores if available
                original_score = 0
                original_max = 0
                if praat_scores and praat_name in praat_scores:
                    original_score = praat_scores[praat_name].get("score", 0)
                    original_max = praat_scores[praat_name].get("max_score", 0)
                else:
                    original_score = gpt_data.get("score", 0)
                    original_max = gpt_data.get("max_score", 10)
                
                score_obj = CriteriaScore(
                    score=original_score,  # Keep original Praat score
                    max_score=original_max,
                    feedback=gpt_data.get("feedback", ""),  # Use GPT's professional feedback
                    issues=gpt_data.get("issues", [])
                )
                setattr(result, praat_name, score_obj)
        
        # Parse AI criteria
        for criteria_name, max_score in ai_criteria_config.items():
            if criteria_name in result_dict:
                criteria_data = result_dict[criteria_name]
                score_obj = CriteriaScore(
                    score=min(criteria_data.get("score", 0), max_score),
                    max_score=max_score,
                    feedback=criteria_data.get("feedback", ""),
                    issues=criteria_data.get("issues", [])
                )
                setattr(result, criteria_name, score_obj)
        
        return result
        
    except Exception as e:
        logger.error(f"Unified AI Scoring error: {e}")
        return TriCoreScoringResult(
            overall_feedback=f"Lỗi khi chấm điểm: {str(e)}"
        )
