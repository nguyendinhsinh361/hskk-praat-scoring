"""
Multi-language Prompts for Speech Assessment
Easy to switch between English, Vietnamese, Chinese

Usage:
    from app.services.prompts import PROMPTS_ZH as PROMPTS  # Chinese
    from app.services.prompts import PROMPTS_EN as PROMPTS  # English
    from app.services.prompts import PROMPTS_VI as PROMPTS  # Vietnamese
"""

from typing import Dict, Optional, Any


class PromptTemplates:
    """Base class for prompt templates"""
    
    # Gemini STT (pure transcription)
    gemini_stt: str = ""
    
    # Criteria descriptions
    criteria_names: Dict[str, str] = {}
    
    # Praat criteria descriptions
    praat_criteria_names: Dict[str, str] = {}


# ========== ENGLISH PROMPTS ==========
class PromptsEN(PromptTemplates):
    """English prompts"""
    
    gemini_stt = """Transcribe this Chinese audio to text.
Requirements:
1. Only output what was spoken, no explanations
2. Transcribe exactly as heard, don't correct grammar or pronunciation
3. Use [...] for unclear parts"""

    @staticmethod
    def get_unified_scoring_system(all_criteria: Dict[str, float], has_praat: bool = False) -> str:
        """
        Unified scoring prompt that includes both AI and Praat criteria.
        GPT will score AI criteria AND rewrite Praat feedback professionally.
        """
        praat_section = ""
        if has_praat:
            praat_section = """
**PRAAT CRITERIA (Pre-scored by acoustic analysis):**
You will receive pre-calculated Praat scores with raw feedback. Your task:
1. Keep the EXACT same scores (do NOT change scores)
2. Rewrite the feedback to be more professional and educational
3. Add specific improvement suggestions based on the metrics

Praat Metrics Reference:
- HNR (Harmonics-to-Noise Ratio): Voice clarity. >20dB = excellent, 15-20 = good, <15 = needs improvement
- Jitter: Frequency stability. <0.01 = excellent, 0.01-0.015 = acceptable, >0.015 = unstable
- Shimmer: Volume consistency. <0.05 = excellent, 0.05-0.08 = acceptable, >0.08 = inconsistent
- Speech Rate: 150-220 syllables/min = ideal
- Pause Ratio: <0.15 = excellent, 0.15-0.25 = acceptable, >0.25 = too many pauses
"""

        return f"""You are a professional Chinese language assessment expert. Evaluate the student's oral performance comprehensively.

{praat_section}

**AI CRITERIA (You must score these):**
Based on STT transcriptions and Gemini intent analysis.

**Scoring Rules:**
1. task_achievement: Compare with reference text if provided, else evaluate content completeness
2. grammar: If STT variants are consistent but differ from Gemini intent → grammar error
3. vocabulary: Evaluate richness and accuracy of vocabulary
4. coherence: Evaluate logical flow and coherence

**Output Requirements:**
Return JSON format. ALL feedback MUST be in Vietnamese (tiếng Việt):
{{
    "pronunciation": {{"score": <from praat>, "feedback": "<professional Vietnamese feedback>", "issues": [...]}},
    "fluency": {{"score": <from praat>, "feedback": "<professional Vietnamese feedback>", "issues": [...]}},
    "task_achievement": {{"score": <0-max>, "feedback": "<Vietnamese>", "issues": [...]}},
    "grammar": {{"score": <0-max>, "feedback": "<Vietnamese>", "issues": [...]}},
    "vocabulary": {{"score": <0-max>, "feedback": "<Vietnamese>", "issues": [...]}},
    "coherence": {{"score": <0-max>, "feedback": "<Vietnamese>", "issues": [...]}},
    "overall_feedback": "<comprehensive Vietnamese summary>"
}}

IMPORTANT: 
- Only include criteria that are requested
- For Praat criteria: KEEP THE SAME SCORE, only improve the feedback
- All feedback must be in Vietnamese"""

    @staticmethod
    def get_unified_scoring_user(
        stt_variants: list,
        gemini_intent: str,
        praat_scores: Optional[Dict[str, Any]] = None,
        reference_text: Optional[str] = None,
        criteria_config: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Build user prompt with all data including Praat pre-scores.
        """
        # STT section
        stt_section = f"""**STT Variants:**
- Whisper: {stt_variants[0] if len(stt_variants) > 0 else 'N/A'}
- FunASR: {stt_variants[1] if len(stt_variants) > 1 else 'N/A'}
- Gemini STT: {stt_variants[2] if len(stt_variants) > 2 else 'N/A'}

**Gemini Intent (correct sentence user intended to say):**
{gemini_intent}"""

        # Reference section
        reference_section = ""
        if reference_text:
            reference_section = f"""
**Reference Text:**
{reference_text}
(Compare with this when scoring task_achievement)"""

        # Praat pre-scores section
        praat_section = ""
        if praat_scores:
            praat_section = """
**PRAAT PRE-SCORES (from acoustic analysis):**
"""
            if "pronunciation" in praat_scores:
                p = praat_scores["pronunciation"]
                praat_section += f"""
Pronunciation:
- Score: {p.get('score', 0)}/{p.get('max_score', 0)} (KEEP THIS SCORE)
- Raw metrics: HNR={p.get('details', {}).get('hnr_mean', 'N/A')}, Jitter={p.get('details', {}).get('jitter_local', 'N/A')}, Shimmer={p.get('details', {}).get('shimmer_local', 'N/A')}
- Raw feedback: {p.get('feedback', '')}
- Issues: {p.get('issues', [])}
"""
            if "fluency" in praat_scores:
                f = praat_scores["fluency"]
                praat_section += f"""
Fluency:
- Score: {f.get('score', 0)}/{f.get('max_score', 0)} (KEEP THIS SCORE)
- Raw metrics: Speech Rate={f.get('details', {}).get('speech_rate', 'N/A')}, Pause Ratio={f.get('details', {}).get('pause_ratio', 'N/A')}, Num Pauses={f.get('details', {}).get('num_pauses', 'N/A')}
- Raw feedback: {f.get('feedback', '')}
- Issues: {f.get('issues', [])}
"""

        # Criteria to score
        criteria_section = ""
        if criteria_config:
            criteria_section = f"""
**AI Criteria to score:**
{list(criteria_config.keys())}
Max scores: {criteria_config}"""

        return f"""{stt_section}
{reference_section}
{praat_section}
{criteria_section}

Please provide your assessment in JSON format. 
- For Praat criteria: Keep the exact same score, but rewrite feedback professionally in Vietnamese
- For AI criteria: Score and provide Vietnamese feedback"""

    @staticmethod
    def get_reference_section(reference_text: str) -> str:
        return f"""
**Reference Text:**
{reference_text}

Compare with reference text when scoring task_achievement."""

    # Legacy methods for backward compatibility
    @staticmethod
    def get_ai_scoring_system(criteria_str: str, criteria_config: Dict[str, float]) -> str:
        return PromptsEN.get_unified_scoring_system(criteria_config, has_praat=False)
    
    @staticmethod
    def get_ai_scoring_user(whisper_variants, gemini_intent, reference_section: str = "") -> str:
        ref_text = reference_section.replace("**Reference Text:**", "").strip() if reference_section else None
        return PromptsEN.get_unified_scoring_user(whisper_variants, gemini_intent, None, ref_text)

    criteria_names = {
        "task_achievement": "task_achievement (Task Completion)",
        "grammar": "grammar (Grammar Accuracy)",
        "vocabulary": "vocabulary (Vocabulary Usage)",
        "coherence": "coherence (Coherence)"
    }
    
    praat_criteria_names = {
        "pronunciation": "pronunciation (Phát âm)",
        "fluency": "fluency (Độ trôi chảy)"
    }


# ========== VIETNAMESE PROMPTS ==========
class PromptsVI(PromptTemplates):
    """Vietnamese prompts"""
    
    gemini_stt = """Chuyển đổi audio tiếng Trung này thành văn bản.
Yêu cầu:
1. Chỉ xuất nội dung được nói, không giải thích
2. Chép nguyên văn như nghe thấy, không sửa ngữ pháp hay phát âm
3. Sử dụng [...] cho phần không nghe rõ"""

    @staticmethod
    def get_unified_scoring_system(all_criteria: Dict[str, float], has_praat: bool = False) -> str:
        praat_section = ""
        if has_praat:
            praat_section = """
**TIÊU CHÍ PRAAT (Đã chấm sẵn bằng phân tích âm học):**
Bạn sẽ nhận điểm Praat đã tính sẵn với feedback thô. Nhiệm vụ của bạn:
1. GIỮ NGUYÊN ĐIỂM (KHÔNG thay đổi điểm)
2. Viết lại feedback chuyên nghiệp và mang tính giáo dục hơn
3. Thêm gợi ý cải thiện cụ thể dựa trên các chỉ số

Tham khảo chỉ số Praat:
- HNR (Harmonics-to-Noise Ratio): Độ trong giọng. >20dB = tốt, 15-20 = khá, <15 = cần cải thiện
- Jitter: Độ ổn định tần số. <0.01 = tốt, 0.01-0.015 = chấp nhận được, >0.015 = không ổn định
- Shimmer: Độ đều âm lượng. <0.05 = tốt, 0.05-0.08 = chấp nhận được, >0.08 = không đều
- Speech Rate: 150-220 âm tiết/phút = lý tưởng
- Pause Ratio: <0.15 = tốt, 0.15-0.25 = chấp nhận được, >0.25 = ngắt nghỉ quá nhiều
"""

        return f"""Bạn là chuyên gia đánh giá ngôn ngữ tiếng Trung. Đánh giá toàn diện kỹ năng nói của học sinh.

{praat_section}

**TIÊU CHÍ AI (Bạn phải chấm):**
Dựa trên các phiên bản STT và phân tích Gemini intent.

**Quy tắc chấm:**
1. task_achievement: So sánh với reference text nếu có, nếu không đánh giá tính đầy đủ
2. grammar: Nếu STT nhất quán nhưng khác Gemini intent → lỗi ngữ pháp
3. vocabulary: Đánh giá độ phong phú và chính xác của từ vựng
4. coherence: Đánh giá tính logic và mạch lạc

**Yêu cầu đầu ra:**
Trả về JSON. TẤT CẢ feedback PHẢI bằng tiếng Việt:
{{
    "pronunciation": {{"score": <từ praat>, "feedback": "<feedback chuyên nghiệp tiếng Việt>", "issues": [...]}},
    "fluency": {{"score": <từ praat>, "feedback": "<feedback chuyên nghiệp tiếng Việt>", "issues": [...]}},
    "task_achievement": {{"score": <0-max>, "feedback": "<tiếng Việt>", "issues": [...]}},
    ...
    "overall_feedback": "<tổng kết tiếng Việt>"
}}

QUAN TRỌNG:
- Chỉ trả về tiêu chí được yêu cầu
- Với tiêu chí Praat: GIỮ NGUYÊN ĐIỂM, chỉ cải thiện feedback
- Tất cả feedback phải bằng tiếng Việt"""

    @staticmethod
    def get_unified_scoring_user(
        stt_variants: list,
        gemini_intent: str,
        praat_scores: Optional[Dict[str, Any]] = None,
        reference_text: Optional[str] = None,
        criteria_config: Optional[Dict[str, float]] = None
    ) -> str:
        return PromptsEN.get_unified_scoring_user(
            stt_variants, gemini_intent, praat_scores, reference_text, criteria_config
        )

    @staticmethod
    def get_reference_section(reference_text: str) -> str:
        return f"""
**Văn bản tham chiếu (Reference Text):**
{reference_text}

So sánh với văn bản tham chiếu khi chấm task_achievement."""

    # Legacy methods
    @staticmethod
    def get_ai_scoring_system(criteria_str: str, criteria_config: Dict[str, float]) -> str:
        return PromptsVI.get_unified_scoring_system(criteria_config, has_praat=False)
    
    @staticmethod
    def get_ai_scoring_user(whisper_variants, gemini_intent, reference_section: str = "") -> str:
        ref_text = reference_section.replace("**Văn bản tham chiếu", "").strip() if reference_section else None
        return PromptsVI.get_unified_scoring_user(whisper_variants, gemini_intent, None, ref_text)

    criteria_names = {
        "task_achievement": "task_achievement (Hoàn thành nhiệm vụ)",
        "grammar": "grammar (Ngữ pháp)",
        "vocabulary": "vocabulary (Từ vựng)",
        "coherence": "coherence (Mạch lạc)"
    }
    
    praat_criteria_names = {
        "pronunciation": "pronunciation (Phát âm)",
        "fluency": "fluency (Độ trôi chảy)"
    }


# ========== CHINESE PROMPTS ==========
class PromptsZH(PromptTemplates):
    """Chinese prompts"""
    
    gemini_stt = """请将这段中文音频转录成文字。
要求：
1. 只输出音频中说的内容，不要添加任何解释
2. 原样转录，不要纠正语法或发音错误
3. 如果听不清楚，用[...]表示"""

    @staticmethod
    def get_unified_scoring_system(all_criteria: Dict[str, float], has_praat: bool = False) -> str:
        praat_section = ""
        if has_praat:
            praat_section = """
**PRAAT评分标准（由声学分析预先评分）：**
你将收到预先计算的Praat分数和原始反馈。你的任务：
1. 保持完全相同的分数（不要更改分数）
2. 将反馈重写为更专业、更有教育意义的内容
3. 根据指标添加具体的改进建议

Praat指标参考：
- HNR（谐噪比）：声音清晰度。>20dB = 优秀，15-20 = 良好，<15 = 需改进
- Jitter：频率稳定性。<0.01 = 优秀，0.01-0.015 = 可接受，>0.015 = 不稳定
- Shimmer：音量一致性。<0.05 = 优秀，0.05-0.08 = 可接受，>0.08 = 不一致
- 语速：150-220音节/分钟 = 理想
- 停顿比例：<0.15 = 优秀，0.15-0.25 = 可接受，>0.25 = 停顿过多
"""

        return f"""你是一位专业的中文语言评估专家。全面评估学生的口语表现。

{praat_section}

**AI评分标准（你必须评分）：**
基于STT转录和Gemini意图分析。

**评分规则：**
1. task_achievement：如果有参考文本则对比，否则评估内容完整性
2. grammar：如果STT一致但与Gemini意图不同 → 语法错误
3. vocabulary：评估词汇的丰富度和准确性
4. coherence：评估逻辑性和连贯性

**输出要求：**
返回JSON格式。所有feedback必须用越南语（Vietnamese）书写：
{{
    "pronunciation": {{"score": <来自praat>, "feedback": "<越南语专业反馈>", "issues": [...]}},
    ...
    "overall_feedback": "<越南语综合总结>"
}}

重要：
- 只返回请求的标准
- 对于Praat标准：保持相同分数，只改进反馈
- 所有反馈必须用越南语"""

    @staticmethod
    def get_unified_scoring_user(
        stt_variants: list,
        gemini_intent: str,
        praat_scores: Optional[Dict[str, Any]] = None,
        reference_text: Optional[str] = None,
        criteria_config: Optional[Dict[str, float]] = None
    ) -> str:
        return PromptsEN.get_unified_scoring_user(
            stt_variants, gemini_intent, praat_scores, reference_text, criteria_config
        )

    @staticmethod
    def get_reference_section(reference_text: str) -> str:
        return f"""
**参考文本 (Reference Text):**
{reference_text}

评估task_achievement时，请对比参考文本。"""

    # Legacy methods
    @staticmethod
    def get_ai_scoring_system(criteria_str: str, criteria_config: Dict[str, float]) -> str:
        return PromptsZH.get_unified_scoring_system(criteria_config, has_praat=False)
    
    @staticmethod
    def get_ai_scoring_user(whisper_variants, gemini_intent, reference_section: str = "") -> str:
        return PromptsEN.get_unified_scoring_user(whisper_variants, gemini_intent, None, None)

    criteria_names = {
        "task_achievement": "task_achievement (任务完成度)",
        "grammar": "grammar (语法准确性)",
        "vocabulary": "vocabulary (词汇使用)",
        "coherence": "coherence (表达连贯性)"
    }
    
    praat_criteria_names = {
        "pronunciation": "pronunciation (发音)",
        "fluency": "fluency (流利度)"
    }


# ========== EXPORTS ==========
PROMPTS_ZH = PromptsZH()
PROMPTS_EN = PromptsEN()
PROMPTS_VI = PromptsVI()

# Active prompts (change this to switch language)
PROMPTS = PROMPTS_EN  # Default to English
