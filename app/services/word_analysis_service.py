"""
Word Analysis Service - Simplified for HSKK
Maps FunASR word timestamps to Praat interval features for per-word pronunciation analysis
Only uses HSKK-relevant features: pitch, HNR (no formants, intensity)
Includes GPT analysis for personalized improvement suggestions
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ========== Constants - Quality Thresholds ==========
DEFAULT_PITCH_MEAN = 200.0
DEFAULT_HNR_MEAN = 15.0
PITCH_DEVIATION_THRESHOLD = 0.5  # 50% deviation from mean
PITCH_STD_THRESHOLD = 50.0  # Hz, high std = unstable tone
HNR_POOR_THRESHOLD = 8.0  # Below this = poor voice quality
HNR_LOW_RATIO = 0.6  # Below 60% of mean = low clarity
MAX_WORDS_IN_GPT_DETAIL = 100  # Limit words shown to GPT
CHINESE_PUNCTUATION = "。，！？、"

# ========== Constants - GPT Prompts ==========
GPT_SYSTEM_PROMPT = """Bạn là giáo viên chấm phát âm tiếng Trung chuyên nghiệp cho kỳ thi HSKK.
Với dữ liệu phân tích âm thanh từng từ, hãy đưa ra đánh giá như một giáo viên thực sự.

BẮT BUỘC trả về JSON theo schema (không cần score_description hay summary):
{
    "overall_assessment": {
        "strengths": ["Điểm mạnh 1", "Điểm mạnh 2"],
        "weaknesses": ["Điểm yếu 1", "Điểm yếu 2"]
    },
    "problem_areas": [
        {
            "words": "từ hoặc cụm từ có vấn đề",
            "problem_description": "Mô tả vấn đề cụ thể",
            "how_to_improve": "Hướng dẫn cách phát âm đúng"
        }
    ],
    "improvement_tips": [
        {
            "category": "Thanh điệu / Độ rõ / Nhịp điệu / Tổng quát",
            "tip": "Lời khuyên cụ thể",
            "example": "Ví dụ hoặc bài tập (nếu có)"
        }
    ],
    "encouragement": "Lời động viên ngắn cho học viên"
}

Quy tắc:
1. Viết tiếng Việt, giọng văn thân thiện như giáo viên
2. NHÓM CỤM TỪ LINH ĐỘNG: Gộp các từ thành CỤM TỪ có nghĩa (2-4 chữ) để học viên dễ luyện tập.
   - Nếu từ sai đứng cạnh từ đúng, hãy ghép cả hai thành cụm để tạo ngữ cảnh học tập
   - Ví dụ: Nếu "很" đúng nhưng "高兴" sai → ghi "很高兴" để học viên luyện cả cụm
   - KHÔNG liệt kê từng chữ riêng lẻ như "我", "很", "高"
3. problem_areas CHỈ chứa các từ/cụm từ CẦN CẢI THIỆN (có vấn đề). KHÔNG đưa vào các từ đã phát âm tốt.
4. problem_areas phải có ÍT NHẤT 15 mục (mỗi mục là CỤM TỪ). Nếu số cụm lỗi < 15 thì liệt kê TẤT CẢ cụm lỗi
5. Đưa ra 2-3 improvement_tips thiết thực
6. Nếu phát âm tốt (>80% đạt), hãy khen ngợi và chỉ đưa ra tips duy trì

Giải thích chỉ số (KHÔNG dùng từ tiếng Anh như "pitch", "HNR" trong phản hồi, hãy dùng từ Việt dễ hiểu):
- Thanh điệu: độ cao-thấp của giọng khi phát âm (quan trọng với 4 thanh tiếng Trung)
- Độ ổn định thanh điệu: giọng có đều đặn không (dao động nhiều = thanh chưa chuẩn)
- Độ rõ giọng: giọng có trong trẻo không (thấp = hơi khàn, ồn, chưa rõ ràng)"""


@dataclass
class WordFeatures:
    """Acoustic features for a single word/character (HSKK-relevant only)"""
    char: str
    start: float
    end: float
    duration: float
    # Pitch (for tonal assessment)
    pitch_mean: float = 0.0
    pitch_std: float = 0.0
    # Voice quality
    hnr: float = 0.0
    # Quality assessment
    quality: str = "unknown"  # good, needs_improvement, poor
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class WordAnalysisResult:
    """Result of word-level analysis"""
    words: List[WordFeatures]
    total_words: int = 0
    good_count: int = 0
    needs_improvement_count: int = 0
    poor_count: int = 0
    average_pitch: float = 0.0
    average_hnr: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "words": [asdict(w) for w in self.words],
            "summary": {
                "total_words": self.total_words,
                "good_count": self.good_count,
                "needs_improvement_count": self.needs_improvement_count,
                "poor_count": self.poor_count,
                "average_pitch": round(self.average_pitch, 2),
                "average_hnr": round(self.average_hnr, 2)
            }
        }


def parse_praat_json(praat_output_path: Path) -> Dict[str, Any]:
    """Parse the unified Praat JSON output"""
    try:
        with open(praat_output_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Praat JSON: {e}")
        return {"overall": {}, "intervals": []}
    except Exception as e:
        logger.error(f"Error reading Praat output: {e}")
        return {"overall": {}, "intervals": []}


def map_words_to_intervals(
    funasr_words: List[Dict[str, Any]],
    praat_intervals: List[Dict[str, Any]]
) -> List[WordFeatures]:
    """
    Map FunASR word timestamps to Praat interval features.
    
    Args:
        funasr_words: List of {char, start, end} from FunASR
        praat_intervals: List of interval data from Praat
    
    Returns:
        List of WordFeatures with mapped acoustic data
    """
    if not funasr_words or not praat_intervals:
        return []
    
    word_features = []
    
    for word in funasr_words:
        char = word.get("char", word.get("text", ""))
        w_start = word.get("start", 0)
        w_end = word.get("end", 0)
        
        # Skip punctuation or empty
        if not char or char in CHINESE_PUNCTUATION:
            continue
        
        # Find the best matching Praat interval (by time overlap)
        best_interval = None
        best_overlap = 0
        
        for interval in praat_intervals:
            i_start = interval.get("start", 0)
            i_end = interval.get("end", 0)
            
            # Calculate overlap
            overlap_start = max(w_start, i_start)
            overlap_end = min(w_end, i_end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > best_overlap:
                best_overlap = overlap
                best_interval = interval
        
        # Create word features with mapped data
        features = WordFeatures(
            char=char,
            start=w_start,
            end=w_end,
            duration=w_end - w_start
        )
        
        if best_interval:
            features.pitch_mean = best_interval.get("pitch_mean", 0)
            features.pitch_std = best_interval.get("pitch_std", 0)
            features.hnr = best_interval.get("hnr", 0)
        
        word_features.append(features)
    
    return word_features


def assess_word_quality(
    word: WordFeatures,
    overall_pitch_mean: float = DEFAULT_PITCH_MEAN,
    overall_hnr_mean: float = DEFAULT_HNR_MEAN
) -> WordFeatures:
    """
    Assess the pronunciation quality of a word based on its acoustic features.
    
    Quality criteria (HSKK-focused):
    - Pitch: Should be within reasonable range of overall mean
    - Pitch stability: Low std = more stable
    - HNR: Higher is better (clearer voice)
    """
    issues = []
    quality = "good"
    
    # Skip if no data
    if word.pitch_mean <= 0:
        word.quality = "no_data"
        word.issues = ["Không có dữ liệu âm thanh"]
        return word
    
    # Check pitch deviation (important for Chinese tones)
    if overall_pitch_mean > 0:
        pitch_deviation = abs(word.pitch_mean - overall_pitch_mean) / overall_pitch_mean
        if pitch_deviation > PITCH_DEVIATION_THRESHOLD:
            issues.append(f"Cao độ lệch ({word.pitch_mean:.0f}Hz)")
            quality = "needs_improvement"
    
    # Check pitch stability (high std = unstable tone)
    if word.pitch_std > PITCH_STD_THRESHOLD:
        issues.append("Thanh điệu không ổn định")
        if quality == "good":
            quality = "needs_improvement"
    
    # Check HNR (voice clarity - important for pronunciation)
    if word.hnr < HNR_POOR_THRESHOLD:
        issues.append(f"Giọng chưa rõ (HNR={word.hnr:.1f})")
        quality = "poor"
    elif word.hnr < overall_hnr_mean * HNR_LOW_RATIO:
        issues.append("Độ trong giọng thấp")
        if quality == "good":
            quality = "needs_improvement"
    
    word.quality = quality
    word.issues = issues
    return word


def analyze_words(
    funasr_words: List[Dict[str, Any]],
    praat_data: Dict[str, Any]
) -> WordAnalysisResult:
    """
    Complete word-level analysis.
    
    Args:
        funasr_words: Word timestamps from FunASR
        praat_data: Parsed Praat JSON output
    
    Returns:
        WordAnalysisResult with all word features and summary
    """
    # Extract data
    praat_intervals = praat_data.get("intervals", [])
    overall = praat_data.get("overall", {})
    
    overall_pitch_mean = overall.get("pitch_mean", DEFAULT_PITCH_MEAN)
    overall_hnr_mean = overall.get("hnr_mean", DEFAULT_HNR_MEAN)
    
    # Map words to intervals
    word_features = map_words_to_intervals(funasr_words, praat_intervals)
    
    # Assess each word
    for word in word_features:
        assess_word_quality(word, overall_pitch_mean, overall_hnr_mean)
    
    # Calculate summary
    good_count = sum(1 for w in word_features if w.quality == "good")
    needs_improvement = sum(1 for w in word_features if w.quality == "needs_improvement")
    poor_count = sum(1 for w in word_features if w.quality == "poor")
    
    valid_words = [w for w in word_features if w.pitch_mean > 0]
    avg_pitch = sum(w.pitch_mean for w in valid_words) / len(valid_words) if valid_words else 0
    avg_hnr = sum(w.hnr for w in valid_words) / len(valid_words) if valid_words else 0
    
    logger.info(f"Word analysis: {good_count} good, {needs_improvement} needs improvement, {poor_count} poor")
    
    return WordAnalysisResult(
        words=word_features,
        total_words=len(word_features),
        good_count=good_count,
        needs_improvement_count=needs_improvement,
        poor_count=poor_count,
        average_pitch=avg_pitch,
        average_hnr=avg_hnr
    )


# ========== GPT Analysis for Word-Level Data ==========

def prepare_word_data_for_gpt(word_result: WordAnalysisResult, transcribed_text: str) -> str:
    """
    Prepare word-level data in a format suitable for GPT analysis.
    Groups consecutive problematic words into phrases.
    """
    all_words = word_result.words
    
    # Build detailed data for GPT
    word_data_lines = []
    for i, w in enumerate(all_words):
        status = "✓" if w.quality == "good" else ("!" if w.quality == "needs_improvement" else "✗")
        issues = ", ".join(w.issues) if w.issues else ""
        word_data_lines.append(
            f"{i+1}. [{status}] '{w.char}' @ {w.start:.2f}s | pitch={w.pitch_mean:.0f}Hz, std={w.pitch_std:.0f}, hnr={w.hnr:.1f} | {issues}"
        )
    
    summary = f"""
Câu nói: "{transcribed_text}"

Tổng quan:
- Tổng số từ: {word_result.total_words}
- Tốt (✓): {word_result.good_count} ({word_result.good_count/max(word_result.total_words,1)*100:.0f}%)
- Cần cải thiện (!): {word_result.needs_improvement_count}
- Kém (✗): {word_result.poor_count}
- Pitch trung bình: {word_result.average_pitch:.0f}Hz
- HNR trung bình: {word_result.average_hnr:.1f}dB

Chi tiết từng từ:
{chr(10).join(word_data_lines[:MAX_WORDS_IN_GPT_DETAIL])}
"""
    if len(word_data_lines) > MAX_WORDS_IN_GPT_DETAIL:
        summary += f"\n... và {len(word_data_lines) - MAX_WORDS_IN_GPT_DETAIL} từ khác"
    
    return summary


async def get_gpt_word_feedback(
    word_result: WordAnalysisResult,
    transcribed_text: str,
    api_key: str,
    model: str = "gpt-4.1-nano"
) -> dict:
    """
    Send word-level analysis to GPT for professional pronunciation assessment.
    
    Returns:
        dict: Structured JSON with overall_assessment, problem_areas, improvement_tips
    """
    client = AsyncOpenAI(api_key=api_key)
    
    # Prepare word data (dùng toàn bộ nội dung đã chuyển âm)
    word_data = prepare_word_data_for_gpt(word_result, transcribed_text)
    problem_word_count = word_result.needs_improvement_count + word_result.poor_count
    
    gpt_user_prompt = f"""{word_data}

Số từ/cụm có vấn đề: {problem_word_count}. 
YÊU CẦU BẮT BUỘC: problem_areas phải có ÍT NHẤT 10 mục (mỗi mục là một từ hoặc cụm từ có vấn đề). Nếu số từ lỗi < 10 thì liệt kê TẤT CẢ các từ lỗi (tối đa {problem_word_count} mục).

Hãy phân tích như một giáo viên chấm phát âm chuyên nghiệp và trả về JSON theo format yêu cầu.
CHỈ trả về JSON, không có text khác."""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GPT_SYSTEM_PROMPT},
                {"role": "user", "content": gpt_user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "word_pronunciation_feedback",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "overall_assessment",
                            "problem_areas",
                            "improvement_tips",
                            "encouragement"
                        ],
                        "properties": {
                            "overall_assessment": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["strengths", "weaknesses"],
                                "properties": {
                                    "strengths": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "weaknesses": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            },
                            "problem_areas": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "words",
                                        "problem_description",
                                        "how_to_improve"
                                    ],
                                    "properties": {
                                        "words": {"type": "string"},
                                        "problem_description": {
                                            "type": "string"
                                        },
                                        "how_to_improve": {"type": "string"}
                                    }
                                }
                            },
                            "improvement_tips": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["category", "tip"],
                                    "properties": {
                                        "category": {"type": "string"},
                                        "tip": {"type": "string"},
                                        "example": {"type": "string"}
                                    }
                                }
                            },
                            "encouragement": {"type": "string"}
                        }
                    }
                }
            }
        )
        
        feedback_json = response.choices[0].message.content
        logger.info(f"GPT word feedback generated: {len(feedback_json)} chars")
        
        # Parse JSON
        try:
            return json.loads(feedback_json)
        except json.JSONDecodeError:
            logger.warning("GPT returned invalid JSON, returning as text")
            return {"raw_feedback": feedback_json}
        
    except Exception as e:
        logger.error(f"GPT word feedback error: {e}")
        return {
            "error": str(e),
            "overall_assessment": {
                "strengths": [],
                "weaknesses": ["Không thể tạo nhận xét chi tiết"]
            },
            "problem_areas": [],
            "improvement_tips": [],
            "encouragement": "Vui lòng thử lại sau"
        }
