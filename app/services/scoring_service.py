import numpy as np
from typing import Dict, Optional
import logging

from app.models.hskk_models import (
    AudioFeatures, HSKKScore, HSKKLevel, PronunciationAssessment
)
from app.config import HSKK_THRESHOLDS

logger = logging.getLogger(__name__)

class HSKKScoringService:
    def __init__(self):
        self.thresholds = HSKK_THRESHOLDS
        
    def calculate_hskk_score(self, features: AudioFeatures, 
                            target_level: HSKKLevel = HSKKLevel.INTERMEDIATE,
                            transcription: Optional[str] = None) -> HSKKScore:
        """Calculate comprehensive HSKK score"""
        
        # Get thresholds for target level
        level_thresholds = self.thresholds[target_level.value]
        
        # Calculate individual scores
        pronunciation_score = self._calculate_pronunciation_score(features, level_thresholds)
        fluency_score = self._calculate_fluency_score(features, level_thresholds)
        
        # Grammar and vocabulary scores (placeholder - would need STT integration)
        grammar_score = 75.0  # Placeholder
        vocabulary_score = 75.0  # Placeholder
        
        if transcription:
            grammar_score, vocabulary_score = self._analyze_text_quality(transcription)
        
        # Calculate overall score (weighted average)
        weights = {
            'pronunciation': 0.35,
            'fluency': 0.35, 
            'grammar': 0.15,
            'vocabulary': 0.15
        }
        
        overall_score = (
            pronunciation_score * weights['pronunciation'] +
            fluency_score * weights['fluency'] +
            grammar_score * weights['grammar'] +
            vocabulary_score * weights['vocabulary']
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
    
    def _calculate_pronunciation_score(self, features: AudioFeatures, 
                                 thresholds: Dict) -> float:
        """Calculate pronunciation score based on acoustic features"""
        score = 100.0
        
        # Pitch range assessment (prosody)
        if features.pitch_range < thresholds['pitch_range_min']:
            score -= 20 * (1 - features.pitch_range / thresholds['pitch_range_min'])
        
        # Voice quality (HNR - Harmonics to Noise Ratio)
        if features.hnr_mean < thresholds['hnr_min']:
            score -= 15 * (1 - features.hnr_mean / thresholds['hnr_min'])
        
        # Jitter (voice stability) - sử dụng jitter_local
        if features.jitter_local > 0.01:  # Normal jitter < 1%
            score -= 10 * min(features.jitter_local / 0.01, 2)
        
        # Shimmer (amplitude stability) - sử dụng shimmer_local
        if features.shimmer_local > 0.1:  # Normal shimmer < 10%
            score -= 10 * min(features.shimmer_local / 0.1, 2)
        
        # Formant clarity (approximation)
        if features.f1_mean < 300 or features.f1_mean > 1000:
            score -= 5
        if features.f2_mean < 800 or features.f2_mean > 3000:
            score -= 5
            
        return max(0, min(100, score))
    
    def _calculate_fluency_score(self, features: AudioFeatures, 
                               thresholds: Dict) -> float:
        """Calculate fluency score"""
        score = 100.0
        
        # Speech rate assessment
        rate_min = thresholds['speech_rate_min'] 
        rate_max = thresholds['speech_rate_max']
        
        if features.speech_rate < rate_min:
            score -= 30 * (1 - features.speech_rate / rate_min)
        elif features.speech_rate > rate_max:
            score -= 20 * (features.speech_rate / rate_max - 1)
        
        # Pause ratio assessment
        if features.pause_ratio > thresholds['pause_ratio_max']:
            score -= 25 * (features.pause_ratio / thresholds['pause_ratio_max'] - 1)
        
        # Duration appropriateness (very short or very long recordings)
        if features.duration < 10:  # Too short
            score -= 15
        elif features.duration > 180:  # Too long
            score -= 10
            
        return max(0, min(100, score))
    
    def _analyze_text_quality(self, transcription: str) -> tuple[float, float]:
        """Analyze grammar and vocabulary from transcription"""
        # This is a placeholder implementation
        # In practice, you'd use NLP tools for Chinese text analysis
        
        grammar_score = 75.0
        vocabulary_score = 75.0
        
        # Basic text analysis
        if len(transcription) < 50:  # Too short
            grammar_score -= 20
            vocabulary_score -= 20
        
        # Character count analysis
        chinese_chars = len([c for c in transcription if '\u4e00' <= c <= '\u9fff'])
        if chinese_chars < len(transcription) * 0.7:  # Should be mostly Chinese
            vocabulary_score -= 15
        
        return grammar_score, vocabulary_score
    
    def _determine_level(self, overall_score: float) -> HSKKLevel:
        """Determine HSKK level based on overall score"""
        if overall_score >= 80:
            return HSKKLevel.ADVANCED
        elif overall_score >= 65:
            return HSKKLevel.INTERMEDIATE
        else:
            return HSKKLevel.ELEMENTARY
    
    def create_pronunciation_assessment(self, features: AudioFeatures, 
                                      reference_text: Optional[str] = None) -> PronunciationAssessment:
        """Create detailed pronunciation assessment"""
        
        # Calculate component scores
        accuracy_score = min(1.0, features.hnr_mean / 25)  # Based on HNR
        fluency_score = self._normalize_fluency(features.speech_rate, features.pause_ratio)
        completeness_score = 1.0  # Placeholder - would need reference comparison
        prosody_score = self._assess_prosody(features)
        
        # Generate detailed feedback
        feedback = self._generate_pronunciation_feedback(features)
        
        return PronunciationAssessment(
            accuracy_score=accuracy_score,
            fluency_score=fluency_score,
            completeness_score=completeness_score,
            prosody_score=prosody_score,
            detailed_feedback=feedback
        )
    
    def _normalize_fluency(self, speech_rate: float, pause_ratio: float) -> float:
        """Normalize fluency to 0-1 scale"""
        ideal_rate = 180  # syllables per minute
        rate_score = 1 - abs(speech_rate - ideal_rate) / ideal_rate
        pause_score = 1 - min(pause_ratio / 0.3, 1)  # Penalize excessive pauses
        
        return (rate_score + pause_score) / 2
    
    def _assess_prosody(self, features: AudioFeatures) -> float:
        """Assess prosodic features"""
        # Pitch variation (good prosody has reasonable pitch range)
        pitch_score = min(features.pitch_range / 100, 1.0)
        
        # Intensity variation 
        intensity_score = min(features.intensity_std / 5, 1.0)
        
        return (pitch_score + intensity_score) / 2
    
    def _generate_pronunciation_feedback(self, features: AudioFeatures) -> Dict[str, str]:
        """Generate detailed pronunciation feedback"""
        feedback = {}
        
        if features.speech_rate < 120:
            feedback["speech_rate"] = "语速较慢，建议提高说话速度 (Speech rate is slow, try to speak faster)"
        elif features.speech_rate > 250:
            feedback["speech_rate"] = "语速较快，建议放慢说话速度 (Speech rate is fast, try to slow down)"
            
        if features.pause_ratio > 0.3:
            feedback["pauses"] = "停顿过多，注意语句连贯性 (Too many pauses, focus on fluency)"
            
        if features.hnr_mean < 15:
            feedback["voice_quality"] = "声音质量需改善，注意发音清晰度 (Voice quality needs improvement)"
            
        if features.pitch_range < 50:
            feedback["prosody"] = "语调变化较少，注意语句的抑扬顿挫 (Limited pitch variation, work on prosody)"
            
        return feedback