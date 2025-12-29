"""
Scoring Service - HSKK score calculation
Handles score calculation based on acoustic features from Praat

================================================================================
DATA SOURCE DOCUMENTATION
================================================================================

This service uses two types of data sources for scoring:

1. PRAAT (Acoustic Analysis) - Used for:
   - Phát âm (Pronunciation): hnr_mean, jitter_local, shimmer_local, f1_mean, f2_mean
   - Độ trôi chảy (Fluency): speech_rate, pause_ratio, num_pauses, mean_pause_duration

2. AI (Speech-to-Text + NLP) - Required for:
   - Khả năng hoàn thành yêu cầu (Task Achievement): text similarity comparison
   - Độ chính xác ngữ pháp (Grammatical Accuracy): grammar error detection
   - Vốn từ vựng (Lexical Resource): vocabulary analysis
   - Tính mạch lạc (Coherence): discourse analysis
   - Phát hiện lặp từ (Word Repetition): requires transcription

================================================================================
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.config import Settings, SCORING_THRESHOLDS
from app.models.enums import HSKKLevel
from app.models.schemas import AudioFeatures, HSKKScore, PronunciationAssessment

logger = logging.getLogger(__name__)


# =============================================================================
# PRAAT THRESHOLDS - Ngưỡng đánh giá dựa trên thông số Praat
# =============================================================================

class PronunciationThresholds:
    """
    Ngưỡng đánh giá phát âm từ Praat
    
    Các thông số Praat sử dụng:
    - hnr_mean: Harmonics-to-Noise Ratio (tỷ lệ hài hòa trên nhiễu)
      → Cao = giọng trong, rõ ràng
      → Thấp = giọng khàn, nhiễu
    
    - jitter_local: Biến thiên tần số cơ bản (F0 perturbation)
      → Thấp = giọng ổn định
      → Cao = giọng run, không đều
    
    - shimmer_local: Biến thiên biên độ (amplitude perturbation)
      → Thấp = âm lượng đều
      → Cao = âm lượng dao động
    """
    # HNR thresholds (dB) - Higher is better
    HNR_EXCELLENT = 20    # Giọng rất trong, chất lượng cao
    HNR_GOOD = 15         # Giọng tốt, chấp nhận được
    HNR_POOR = 10         # Giọng yếu, cần cải thiện
    
    # Jitter thresholds (ratio) - Lower is better
    JITTER_EXCELLENT = 0.01   # Giọng rất ổn định
    JITTER_ACCEPTABLE = 0.015  # Chấp nhận được
    JITTER_POOR = 0.02         # Giọng không ổn định
    
    # Shimmer thresholds (ratio) - Lower is better
    SHIMMER_EXCELLENT = 0.05   # Âm lượng rất đều
    SHIMMER_ACCEPTABLE = 0.08  # Chấp nhận được
    SHIMMER_POOR = 0.12        # Âm lượng không đều
    
    # Formant ranges (Hz) - For vowel quality
    F1_MIN = 300   # Below this = unclear vowel
    F1_MAX = 1000  # Above this = too open
    F2_MIN = 800   # Below this = back vowel issues
    F2_MAX = 3000  # Above this = front vowel issues


class FluencyThresholds:
    """
    Ngưỡng đánh giá độ trôi chảy từ Praat
    
    Các thông số Praat sử dụng:
    - speech_rate: Tốc độ nói (syllables/minute, bao gồm cả ngắt nghỉ)
    - articulation_rate: Tốc độ phát âm (syllables/minute, không tính ngắt nghỉ)
    - pause_ratio: Tỷ lệ thời gian ngắt nghỉ / tổng thời gian
    - num_pauses: Số lần ngắt nghỉ
    - mean_pause_duration: Thời lượng trung bình mỗi lần ngắt nghỉ (giây)
    """
    # Speech rate thresholds (syllables/minute)
    RATE_SLOW = 100           # Quá chậm
    RATE_IDEAL_MIN = 150      # Tốc độ lý tưởng tối thiểu
    RATE_IDEAL_MAX = 220      # Tốc độ lý tưởng tối đa
    RATE_FAST = 280           # Quá nhanh
    
    # Pause ratio thresholds (0-1)
    PAUSE_RATIO_EXCELLENT = 0.15  # Ít ngắt nghỉ, trôi chảy
    PAUSE_RATIO_ACCEPTABLE = 0.25  # Chấp nhận được
    PAUSE_RATIO_POOR = 0.35        # Quá nhiều ngắt nghỉ
    
    # Mean pause duration (seconds)
    MEAN_PAUSE_EXCELLENT = 0.3     # Ngắt nghỉ ngắn, tự nhiên
    MEAN_PAUSE_ACCEPTABLE = 0.6    # Chấp nhận được
    
    # Rate variance threshold
    RATE_VARIANCE_THRESHOLD = 50   # |articulation_rate - speech_rate|


class FluencyIssue(Enum):
    """Các loại lỗi độ trôi chảy có thể phát hiện bằng Praat"""
    NGAT_NGHI_SAI = "ngat_nghi_sai"           # Improper pauses
    NGAP_NGUNG = "ngap_ngung"                  # Hesitation
    LAP_TU = "lap_tu"                          # Word repetition (requires STT)
    TOC_DO_KHONG_ON_DINH = "toc_do_khong_on_dinh"  # Unstable speed


@dataclass
class FluencyAnalysis:
    """Kết quả phân tích độ trôi chảy"""
    score: float
    detected_issues: List[FluencyIssue]
    feedback: Dict[str, str]


@dataclass
class PronunciationAnalysis:
    """Kết quả phân tích phát âm"""
    score: float
    hnr_quality: str      # excellent/good/poor
    voice_stability: str  # excellent/acceptable/poor
    feedback: Dict[str, str]


class ScoringService:
    """
    Service for calculating HSKK scores
    
    Tiêu chí sử dụng Praat:
    - Phát âm (Pronunciation): hnr_mean, jitter, shimmer, formants
    - Độ trôi chảy (Fluency): speech_rate, pause_ratio, num_pauses
    
    Tiêu chí cần AI/STT:
    - Task Achievement, Grammar, Vocabulary, Coherence
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.thresholds = SCORING_THRESHOLDS
        self.weights = {
            "pronunciation": settings.weight_pronunciation,
            "fluency": settings.weight_fluency,
            "grammar": settings.weight_grammar,
            "vocabulary": settings.weight_vocabulary,
        }
    
    def calculate_score(
        self,
        features: AudioFeatures,
        transcription: Optional[str] = None
    ) -> HSKKScore:
        """
        Calculate comprehensive HSKK score
        
        Args:
            features: Extracted acoustic features from Praat
            transcription: Optional transcription for text analysis (requires STT)
            
        Returns:
            HSKKScore object with overall and component scores
            
        Data Sources:
            - pronunciation_score: PRAAT (hnr_mean, jitter, shimmer, formants)
            - fluency_score: PRAAT (speech_rate, pause_ratio, num_pauses)
            - grammar_score: AI/STT (placeholder without transcription)
            - vocabulary_score: AI/STT (placeholder without transcription)
        """
        # Calculate Praat-based scores
        pronunciation_analysis = self._analyze_pronunciation(features)
        fluency_analysis = self._analyze_fluency(features)
        
        pronunciation_score = pronunciation_analysis.score
        fluency_score = fluency_analysis.score
        
        # Grammar and vocabulary (requires STT/NLP integration)
        # NOTE: These are placeholders - actual scoring needs AI transcription
        grammar_score = 75.0
        vocabulary_score = 75.0
        
        if transcription:
            grammar_score, vocabulary_score = self._analyze_text_quality(transcription)
        
        # Log detected fluency issues
        if fluency_analysis.detected_issues:
            logger.info(f"Detected fluency issues: {[i.value for i in fluency_analysis.detected_issues]}")
        
        # Calculate weighted overall score
        overall_score = (
            pronunciation_score * self.weights['pronunciation'] +
            fluency_score * self.weights['fluency'] +
            grammar_score * self.weights['grammar'] +
            vocabulary_score * self.weights['vocabulary']
        )
        
        # Determine achieved level
        achieved_level = self._determine_level(overall_score)
        
        return HSKKScore(
            overall_score=overall_score,
            level_achieved=achieved_level,
            pronunciation=pronunciation_score,
            fluency=fluency_score,
            grammar=grammar_score,
            vocabulary=vocabulary_score
        )
    
    def create_pronunciation_assessment(
        self,
        features: AudioFeatures,
        reference_text: Optional[str] = None
    ) -> PronunciationAssessment:
        """
        Create detailed pronunciation assessment using Praat metrics
        
        Praat metrics used:
        - hnr_mean: Voice clarity (accuracy_score)
        - speech_rate, pause_ratio: Speaking fluency (fluency_score)
        - pitch_range, intensity_std: Prosody (prosody_score)
        """
        # Calculate component scores using Praat metrics
        accuracy_score = self._calculate_accuracy_from_hnr(features.hnr_mean)
        fluency_score = self._normalize_fluency(features.speech_rate, features.pause_ratio)
        completeness_score = 1.0  # Placeholder - needs STT for actual measurement
        prosody_score = self._assess_prosody(features)
        
        # Generate feedback based on Praat analysis
        feedback = self._generate_feedback(features)
        
        return PronunciationAssessment(
            accuracy_score=accuracy_score,
            fluency_score=fluency_score,
            completeness_score=completeness_score,
            prosody_score=prosody_score,
            detailed_feedback=feedback
        )
    
    # =========================================================================
    # PRAAT-BASED PRONUNCIATION ANALYSIS (Phát âm)
    # =========================================================================
    
    def _analyze_pronunciation(self, features: AudioFeatures) -> PronunciationAnalysis:
        """
        Phân tích phát âm dựa trên thông số Praat
        
        Praat metrics used:
        - hnr_mean: Harmonics-to-Noise Ratio → độ trong của giọng
        - jitter_local: Voice stability (F0 perturbation)
        - shimmer_local: Amplitude stability
        - f1_mean, f2_mean: Formant clarity → chất lượng nguyên âm
        - pitch_range: Prosody indicator
        """
        score = 100.0
        feedback = {}
        
        # ========================
        # 1. HNR Assessment (Voice Clarity)
        # ========================
        hnr = features.hnr_mean
        if hnr >= PronunciationThresholds.HNR_EXCELLENT:
            hnr_quality = "excellent"
        elif hnr >= PronunciationThresholds.HNR_GOOD:
            hnr_quality = "good"
            # Deduct proportionally
            score -= 10 * (1 - (hnr - PronunciationThresholds.HNR_GOOD) / 
                          (PronunciationThresholds.HNR_EXCELLENT - PronunciationThresholds.HNR_GOOD))
        else:
            hnr_quality = "poor"
            score -= 20
            feedback["voice_quality"] = "Giọng nói chưa rõ ràng, cần cải thiện độ trong của giọng"
        
        # ========================
        # 2. Jitter Assessment (Voice Stability)
        # ========================
        jitter = features.jitter_local
        if jitter <= PronunciationThresholds.JITTER_EXCELLENT:
            voice_stability = "excellent"
        elif jitter <= PronunciationThresholds.JITTER_ACCEPTABLE:
            voice_stability = "acceptable"
            score -= 10 * ((jitter - PronunciationThresholds.JITTER_EXCELLENT) / 
                          (PronunciationThresholds.JITTER_ACCEPTABLE - PronunciationThresholds.JITTER_EXCELLENT))
        else:
            voice_stability = "poor"
            score -= 15
            feedback["voice_stability"] = "Giọng nói không ổn định, có hiện tượng run giọng"
        
        # ========================
        # 3. Shimmer Assessment (Amplitude Stability)
        # ========================
        shimmer = features.shimmer_local
        if shimmer > PronunciationThresholds.SHIMMER_ACCEPTABLE:
            score -= 10
            feedback["amplitude"] = "Âm lượng không đều, cần kiểm soát hơi thở tốt hơn"
        elif shimmer > PronunciationThresholds.SHIMMER_EXCELLENT:
            score -= 5
        
        # ========================
        # 4. Formant Clarity (Vowel Quality)
        # ========================
        f1_valid = PronunciationThresholds.F1_MIN <= features.f1_mean <= PronunciationThresholds.F1_MAX
        f2_valid = PronunciationThresholds.F2_MIN <= features.f2_mean <= PronunciationThresholds.F2_MAX
        
        if not f1_valid:
            score -= 5
            feedback["f1"] = "Độ mở nguyên âm chưa chuẩn"
        if not f2_valid:
            score -= 5
            feedback["f2"] = "Vị trí lưỡi phát âm nguyên âm chưa chính xác"
        
        # ========================
        # 5. Pitch Range (Prosody)
        # ========================
        if features.pitch_range < 50:
            score -= 10
            feedback["prosody"] = "Ngữ điệu đơn điệu, cần tăng biến thiên cao độ"
        
        return PronunciationAnalysis(
            score=max(0, min(100, score)),
            hnr_quality=hnr_quality,
            voice_stability=voice_stability,
            feedback=feedback
        )
    
    def _calculate_pronunciation_score(
        self,
        features: AudioFeatures,
        thresholds: Dict
    ) -> float:
        """
        Calculate pronunciation score based on Praat acoustic features
        
        PRAAT METRICS MAPPING:
        ┌────────────────────┬──────────────────────────────────────────┐
        │ Praat Metric       │ What it measures                         │
        ├────────────────────┼──────────────────────────────────────────┤
        │ hnr_mean           │ Voice clarity (HNR cao = giọng trong)    │
        │ jitter_local       │ Pitch stability (thấp = ổn định)         │
        │ shimmer_local      │ Volume stability (thấp = đều)            │
        │ f1_mean, f2_mean   │ Vowel quality (formant positions)        │
        │ pitch_range        │ Prosody/intonation variation             │
        └────────────────────┴──────────────────────────────────────────┘
        """
        analysis = self._analyze_pronunciation(features)
        return analysis.score
    
    # =========================================================================
    # PRAAT-BASED FLUENCY ANALYSIS (Độ trôi chảy)
    # =========================================================================
    
    def _analyze_fluency(self, features: AudioFeatures) -> FluencyAnalysis:
        """
        Phân tích độ trôi chảy dựa trên thông số Praat
        
        Praat metrics used:
        - speech_rate: Tốc độ nói tổng thể (syllables/min)
        - articulation_rate: Tốc độ phát âm thực (không tính pause)
        - pause_ratio: Tỷ lệ thời gian ngắt nghỉ
        - num_pauses: Số lần ngắt nghỉ
        - mean_pause_duration: Thời lượng trung bình mỗi pause
        
        Detected issues:
        - ngat_nghi_sai: pause_ratio > 0.25 OR mean_pause > 0.6
        - ngap_ngung: num_pauses > 10 AND mean_pause < 0.5
        - toc_do_khong_on_dinh: |articulation_rate - speech_rate| > 50
        - lap_tu: requires STT (cannot detect with Praat alone)
        """
        score = 100.0
        detected_issues: List[FluencyIssue] = []
        feedback = {}
        
        # ========================
        # 1. Speech Rate Assessment (Tốc độ nói)
        # ========================
        rate = features.speech_rate
        
        if rate < FluencyThresholds.RATE_SLOW:
            # Quá chậm
            score -= 30
            feedback["speech_rate"] = "Tốc độ nói quá chậm, cần tăng nhịp điệu"
        elif rate < FluencyThresholds.RATE_IDEAL_MIN:
            # Hơi chậm
            penalty = 20 * (1 - (rate - FluencyThresholds.RATE_SLOW) / 
                          (FluencyThresholds.RATE_IDEAL_MIN - FluencyThresholds.RATE_SLOW))
            score -= penalty
            feedback["speech_rate"] = "Tốc độ nói hơi chậm"
        elif rate > FluencyThresholds.RATE_FAST:
            # Quá nhanh
            score -= 25
            feedback["speech_rate"] = "Tốc độ nói quá nhanh, cần chậm lại"
        elif rate > FluencyThresholds.RATE_IDEAL_MAX:
            # Hơi nhanh
            penalty = 15 * ((rate - FluencyThresholds.RATE_IDEAL_MAX) / 
                           (FluencyThresholds.RATE_FAST - FluencyThresholds.RATE_IDEAL_MAX))
            score -= penalty
        
        # ========================
        # 2. Pause Ratio Assessment (Ngắt nghỉ sai)
        # Detection: pause_ratio > 0.25 OR mean_pause_duration > 0.6
        # ========================
        if (features.pause_ratio > FluencyThresholds.PAUSE_RATIO_ACCEPTABLE or 
            features.mean_pause_duration > FluencyThresholds.MEAN_PAUSE_ACCEPTABLE):
            
            detected_issues.append(FluencyIssue.NGAT_NGHI_SAI)
            
            if features.pause_ratio > FluencyThresholds.PAUSE_RATIO_POOR:
                score -= 25
                feedback["pauses"] = "Ngắt nghỉ quá nhiều, ảnh hưởng nghiêm trọng đến độ trôi chảy"
            else:
                score -= 15
                feedback["pauses"] = "Có hiện tượng ngắt nghỉ sai vị trí hoặc quá dài"
        
        # ========================
        # 3. Hesitation Detection (Ngập ngừng)
        # Detection: num_pauses > 10 AND mean_pause_duration < 0.5
        # (Many short pauses indicate hesitation)
        # ========================
        if features.num_pauses > 10 and features.mean_pause_duration < 0.5:
            detected_issues.append(FluencyIssue.NGAP_NGUNG)
            score -= 15
            feedback["hesitation"] = "Có hiện tượng ngập ngừng, đọc/nói không liền mạch"
        
        # ========================
        # 4. Rate Instability (Tốc độ không ổn định)
        # Detection: |articulation_rate - speech_rate| > 50
        # ========================
        rate_variance = abs(features.articulation_rate - features.speech_rate)
        if rate_variance > FluencyThresholds.RATE_VARIANCE_THRESHOLD:
            detected_issues.append(FluencyIssue.TOC_DO_KHONG_ON_DINH)
            score -= 10
            feedback["rate_stability"] = "Tốc độ nói không ổn định, có lúc nhanh lúc chậm"
        
        # ========================
        # 5. Duration Check
        # ========================
        if features.duration < 10:
            score -= 15
            feedback["duration"] = "Bài nói quá ngắn"
        elif features.duration > 180:
            score -= 10
            feedback["duration"] = "Bài nói quá dài"
        
        # NOTE: LAP_TU (word repetition) cannot be detected by Praat
        # Requires speech-to-text transcription to detect
        
        return FluencyAnalysis(
            score=max(0, min(100, score)),
            detected_issues=detected_issues,
            feedback=feedback
        )
    
    def _calculate_fluency_score(
        self,
        features: AudioFeatures,
        thresholds: Dict
    ) -> float:
        """
        Calculate fluency score based on Praat timing metrics
        
        PRAAT METRICS MAPPING:
        ┌─────────────────────────┬────────────────────────────────────────┐
        │ Praat Metric            │ Fluency Issue Detected                 │
        ├─────────────────────────┼────────────────────────────────────────┤
        │ speech_rate             │ Too slow / too fast                    │
        │ pause_ratio > 0.25      │ Ngắt nghỉ sai (improper pauses)        │
        │ mean_pause > 0.6        │ Ngắt nghỉ sai (pauses too long)        │
        │ num_pauses > 10 +       │ Ngập ngừng (hesitation)                │
        │   mean_pause < 0.5      │                                        │
        │ |art_rate - speech| > 50│ Tốc độ không ổn định                   │
        │ (STT required)          │ Lặp từ (word repetition)               │
        └─────────────────────────┴────────────────────────────────────────┘
        """
        analysis = self._analyze_fluency(features)
        return analysis.score
    
    def detect_fluency_issues(self, features: AudioFeatures) -> List[str]:
        """
        Public method to detect fluency issues from Praat metrics
        
        Returns:
            List of detected issue codes: 
            ['ngat_nghi_sai', 'ngap_ngung', 'toc_do_khong_on_dinh']
            
        Note: 'lap_tu' (word repetition) requires STT and cannot be detected here
        """
        analysis = self._analyze_fluency(features)
        return [issue.value for issue in analysis.detected_issues]
    
    # =========================================================================
    # AI/STT-BASED ANALYSIS (Requires transcription)
    # =========================================================================
    
    def _analyze_text_quality(self, transcription: str) -> Tuple[float, float]:
        """
        Analyze grammar and vocabulary from transcription
        
        NOTE: This is a PLACEHOLDER implementation.
        Actual implementation requires:
        - Speech-to-Text (STT) engine (e.g., Whisper, Azure Speech)
        - NLP pipeline for Chinese (e.g., Jieba, HanLP)
        - Grammar checking model
        - Vocabulary level classification
        
        Data source: AI (not Praat)
        """
        grammar_score = 75.0
        vocabulary_score = 75.0
        
        # Basic text analysis (placeholder)
        if len(transcription) < 50:
            grammar_score -= 20
            vocabulary_score -= 20
        
        # Chinese character count
        chinese_chars = len([c for c in transcription if '\u4e00' <= c <= '\u9fff'])
        if chinese_chars < len(transcription) * 0.7:
            vocabulary_score -= 15
        
        return grammar_score, vocabulary_score
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _determine_level(self, overall_score: float) -> HSKKLevel:
        """Determine HSKK level based on overall score"""
        if overall_score >= 80:
            return HSKKLevel.ADVANCED
        elif overall_score >= 65:
            return HSKKLevel.INTERMEDIATE
        else:
            return HSKKLevel.ELEMENTARY
    
    def _calculate_accuracy_from_hnr(self, hnr: float) -> float:
        """
        Convert HNR (Praat metric) to accuracy score (0-1)
        
        HNR (Harmonics-to-Noise Ratio) measures voice clarity.
        Higher HNR = clearer voice = better pronunciation clarity
        """
        if hnr >= PronunciationThresholds.HNR_EXCELLENT:
            return 1.0
        elif hnr >= PronunciationThresholds.HNR_GOOD:
            return 0.7 + 0.3 * ((hnr - PronunciationThresholds.HNR_GOOD) / 
                               (PronunciationThresholds.HNR_EXCELLENT - PronunciationThresholds.HNR_GOOD))
        elif hnr >= PronunciationThresholds.HNR_POOR:
            return 0.4 + 0.3 * ((hnr - PronunciationThresholds.HNR_POOR) / 
                               (PronunciationThresholds.HNR_GOOD - PronunciationThresholds.HNR_POOR))
        else:
            return max(0, hnr / PronunciationThresholds.HNR_POOR * 0.4)
    
    def _normalize_fluency(self, speech_rate: float, pause_ratio: float) -> float:
        """
        Normalize fluency to 0-1 scale using Praat metrics
        
        Praat metrics used:
        - speech_rate: Target around 150-220 syllables/min
        - pause_ratio: Lower is better (target < 0.15)
        """
        # Rate score: peak at ideal range
        if FluencyThresholds.RATE_IDEAL_MIN <= speech_rate <= FluencyThresholds.RATE_IDEAL_MAX:
            rate_score = 1.0
        elif speech_rate < FluencyThresholds.RATE_IDEAL_MIN:
            rate_score = max(0, speech_rate / FluencyThresholds.RATE_IDEAL_MIN)
        else:
            rate_score = max(0, 1 - (speech_rate - FluencyThresholds.RATE_IDEAL_MAX) / 100)
        
        # Pause score: lower pause_ratio is better
        if pause_ratio <= FluencyThresholds.PAUSE_RATIO_EXCELLENT:
            pause_score = 1.0
        elif pause_ratio <= FluencyThresholds.PAUSE_RATIO_ACCEPTABLE:
            pause_score = 0.7 + 0.3 * (1 - (pause_ratio - FluencyThresholds.PAUSE_RATIO_EXCELLENT) /
                                       (FluencyThresholds.PAUSE_RATIO_ACCEPTABLE - FluencyThresholds.PAUSE_RATIO_EXCELLENT))
        else:
            pause_score = max(0, 0.7 * (1 - (pause_ratio - FluencyThresholds.PAUSE_RATIO_ACCEPTABLE) / 0.3))
        
        return (rate_score + pause_score) / 2
    
    def _assess_prosody(self, features: AudioFeatures) -> float:
        """
        Assess prosodic features using Praat metrics
        
        Praat metrics used:
        - pitch_range: Variation in fundamental frequency
        - intensity_std: Variation in loudness
        """
        # Pitch variation (higher pitch_range = more expressive)
        pitch_score = min(features.pitch_range / 100, 1.0)
        
        # Intensity variation (some variation is good)
        intensity_score = min(features.intensity_std / 5, 1.0)
        
        return (pitch_score + intensity_score) / 2
    
    def _generate_feedback(self, features: AudioFeatures) -> Dict[str, str]:
        """
        Generate detailed pronunciation feedback based on Praat metrics
        
        This method analyzes Praat features and generates
        actionable feedback in Chinese and English.
        """
        feedback = {}
        
        # Speech rate feedback (Praat: speech_rate)
        if features.speech_rate < FluencyThresholds.RATE_SLOW:
            feedback["speech_rate"] = "语速过慢，建议提高说话速度 (Speech rate too slow)"
        elif features.speech_rate < FluencyThresholds.RATE_IDEAL_MIN:
            feedback["speech_rate"] = "语速较慢，可适当加快 (Speech rate is slow)"
        elif features.speech_rate > FluencyThresholds.RATE_FAST:
            feedback["speech_rate"] = "语速过快，建议放慢说话速度 (Speech rate too fast)"
        elif features.speech_rate > FluencyThresholds.RATE_IDEAL_MAX:
            feedback["speech_rate"] = "语速较快，可适当放慢 (Speech rate is fast)"
        
        # Pause feedback (Praat: pause_ratio)
        if features.pause_ratio > FluencyThresholds.PAUSE_RATIO_POOR:
            feedback["pauses"] = "停顿过多，严重影响流利度 (Too many pauses, severely affecting fluency)"
        elif features.pause_ratio > FluencyThresholds.PAUSE_RATIO_ACCEPTABLE:
            feedback["pauses"] = "停顿较多，注意语句连贯性 (Too many pauses, watch coherence)"
        
        # Voice quality feedback (Praat: hnr_mean)
        if features.hnr_mean < PronunciationThresholds.HNR_POOR:
            feedback["voice_quality"] = "声音质量需大幅改善，发音不够清晰 (Voice quality needs major improvement)"
        elif features.hnr_mean < PronunciationThresholds.HNR_GOOD:
            feedback["voice_quality"] = "声音质量需改善，可更加清晰 (Voice quality could be clearer)"
        
        # Prosody feedback (Praat: pitch_range)
        if features.pitch_range < 30:
            feedback["prosody"] = "语调过于平淡，缺乏抑扬顿挫 (Monotone intonation, needs variation)"
        elif features.pitch_range < 50:
            feedback["prosody"] = "语调变化较少，可增加抑扬顿挫 (Limited pitch variation)"
        
        # Voice stability feedback (Praat: jitter_local)
        if features.jitter_local > PronunciationThresholds.JITTER_POOR:
            feedback["stability"] = "声音不够稳定，有颤抖现象 (Voice instability, tremor detected)"
        
        return feedback