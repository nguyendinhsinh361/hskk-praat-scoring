"""
AI Provider - Abstraction layer for OpenAI and Gemini APIs
Provides STT (Speech-to-Text) and NLP analysis with structured response formats
"""
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, Type
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AIProviderType(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    GEMINI = "gemini"


# ========== Response Schemas ==========

class GrammarAnalysisResponse(BaseModel):
    """Schema for grammar analysis response"""
    errors: list[str] = Field(default_factory=list, description="List of grammar errors found")
    accuracy_score: int = Field(ge=0, le=100, description="Grammar accuracy score 0-100")
    complexity_score: int = Field(ge=0, le=100, description="Sentence complexity score 0-100")
    feedback: str = Field(description="Feedback in Vietnamese")


class VocabularyAnalysisResponse(BaseModel):
    """Schema for vocabulary analysis response"""
    diversity_score: int = Field(ge=0, le=100, description="Vocabulary diversity score 0-100")
    accuracy_score: int = Field(ge=0, le=100, description="Word usage accuracy score 0-100")
    hsk_level_match: bool = Field(description="Whether vocabulary matches HSK level")
    feedback: str = Field(description="Feedback in Vietnamese")


class CoherenceAnalysisResponse(BaseModel):
    """Schema for coherence analysis response"""
    coherence_score: int = Field(ge=0, le=100, description="Coherence score 0-100")
    has_transitions: bool = Field(description="Whether text uses transition words")
    logical_flow: bool = Field(description="Whether ideas flow logically")
    feedback: str = Field(description="Feedback in Vietnamese")


class TaskAchievementAnalysisResponse(BaseModel):
    """Schema for task achievement analysis response"""
    relevance_score: int = Field(ge=0, le=100, description="Topic relevance score 0-100")
    completeness_score: int = Field(ge=0, le=100, description="Content completeness score 0-100")
    feedback: str = Field(description="Feedback in Vietnamese")


class SimilarityAnalysisResponse(BaseModel):
    """Schema for similarity analysis response"""
    similarity_percentage: int = Field(ge=0, le=100, description="Content match percentage 0-100")
    missing_content: list[str] = Field(default_factory=list, description="Content missing from spoken")
    added_content: list[str] = Field(default_factory=list, description="Content added in spoken")
    feedback: str = Field(description="Feedback in Vietnamese")


# Response schema mapping
RESPONSE_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "grammar": GrammarAnalysisResponse,
    "vocabulary": VocabularyAnalysisResponse,
    "coherence": CoherenceAnalysisResponse,
    "task_achievement": TaskAchievementAnalysisResponse,
    "similarity": SimilarityAnalysisResponse,
}


# ========== Base Provider ==========

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> str:
        """Transcribe audio to text (STT)"""
        pass
    
    @abstractmethod
    async def analyze_text(
        self, 
        text: str, 
        analysis_type: str,
        reference_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze text using NLP with structured response"""
        pass


# ========== OpenAI Provider ==========

class OpenAIProvider(AIProvider):
    """OpenAI API provider for STT and NLP"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client
    
    async def transcribe(self, audio_path: Path) -> str:
        """Transcribe audio using OpenAI Whisper"""
        client = self._get_client()
        
        with open(audio_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh"  # Chinese
            )
        
        return transcription.text
    
    async def analyze_text(
        self,
        text: str,
        analysis_type: str,
        reference_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze text using GPT-4 with structured output"""
        client = self._get_client()
        
        # Get response schema for this analysis type
        response_schema = RESPONSE_SCHEMAS.get(analysis_type)
        
        prompt = self._build_prompt(text, analysis_type, reference_text, context)
        system_prompt = self._get_system_prompt(analysis_type)
        
        if response_schema:
            # Use structured output with response_format
            response = await client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_schema
            )
            return response.choices[0].message.parsed.model_dump()
        else:
            # Fallback to JSON mode
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
    
    def _get_system_prompt(self, analysis_type: str) -> str:
        """Get system prompt based on analysis type"""
        prompts = {
            "grammar": """Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích ngữ pháp của văn bản.
Trả về JSON với các trường: errors (danh sách lỗi), accuracy_score (0-100), complexity_score (0-100), feedback (bằng tiếng Việt).""",
            
            "vocabulary": """Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích việc sử dụng từ vựng.
Trả về JSON với: diversity_score (0-100), accuracy_score (0-100), hsk_level_match (true/false), feedback (bằng tiếng Việt).""",
            
            "coherence": """Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích tính mạch lạc và liên kết của văn bản.
Trả về JSON với: coherence_score (0-100), has_transitions (true/false), logical_flow (true/false), feedback (bằng tiếng Việt).""",
            
            "task_achievement": """Bạn là chuyên gia ngôn ngữ Trung Quốc. Đánh giá xem câu trả lời có đáp ứng yêu cầu đề bài không.
Trả về JSON với: relevance_score (0-100), completeness_score (0-100), feedback (bằng tiếng Việt).""",
            
            "similarity": """So sánh văn bản nói với văn bản gốc.
Trả về JSON với: similarity_percentage (0-100), missing_content (mảng), added_content (mảng), feedback (bằng tiếng Việt)."""
        }
        return prompts.get(analysis_type, prompts["grammar"])
    
    def _build_prompt(
        self,
        text: str,
        analysis_type: str,
        reference_text: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build analysis prompt"""
        prompt = f"Phân tích văn bản tiếng Trung sau:\n\n{text}"
        
        if reference_text:
            prompt += f"\n\nVăn bản tham chiếu:\n{reference_text}"
        
        if context:
            prompt += f"\n\nNgữ cảnh: {context}"
        
        return prompt


# ========== Gemini Provider ==========

class GeminiProvider(AIProvider):
    """Google Gemini API provider for STT and NLP"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._configured = False
    
    def _configure(self):
        if not self._configured:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._configured = True
            except ImportError:
                raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    def _get_client(self):
        self._configure()
        if self._client is None:
            import google.generativeai as genai
            self._client = genai.GenerativeModel(self.model)
        return self._client
    
    async def transcribe(self, audio_path: Path) -> str:
        """Transcribe audio using Gemini"""
        self._configure()
        import google.generativeai as genai
        
        # Upload file
        audio_file = genai.upload_file(str(audio_path))
        
        model = self._get_client()
        response = await model.generate_content_async([
            audio_file,
            "Chuyển đổi audio tiếng Trung này thành văn bản. Chỉ trả về văn bản đã chuyển đổi, không kèm thêm gì khác."
        ])
        
        return response.text
    
    async def analyze_text(
        self,
        text: str,
        analysis_type: str,
        reference_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze text using Gemini with structured output"""
        import google.generativeai as genai
        from google.generativeai.types import content_types
        
        self._configure()
        
        # Get response schema for this analysis type
        response_schema = RESPONSE_SCHEMAS.get(analysis_type)
        
        prompt = self._build_prompt(text, analysis_type, reference_text, context)
        
        model = self._get_client()
        
        if response_schema:
            # Use structured output with response_schema
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
        else:
            # Fallback to JSON mode
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
        
        import json
        return json.loads(response.text)
    
    def _build_prompt(
        self,
        text: str,
        analysis_type: str,
        reference_text: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build analysis prompt with instructions"""
        base_prompts = {
            "grammar": f"""Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích ngữ pháp của văn bản tiếng Trung sau:

"{text}"

Trả về JSON với các trường:
- errors: mảng các lỗi ngữ pháp được phát hiện
- accuracy_score: điểm độ chính xác ngữ pháp (0-100)
- complexity_score: điểm độ phức tạp cấu trúc câu (0-100)
- feedback: nhận xét ngắn gọn bằng tiếng Việt""",

            "vocabulary": f"""Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích việc sử dụng từ vựng trong văn bản tiếng Trung sau:

"{text}"

Trả về JSON với các trường:
- diversity_score: điểm sự đa dạng từ vựng (0-100)
- accuracy_score: điểm độ chính xác sử dụng từ (0-100)
- hsk_level_match: true nếu từ vựng phù hợp với trình độ HSK
- feedback: nhận xét ngắn gọn bằng tiếng Việt""",

            "coherence": f"""Bạn là chuyên gia ngôn ngữ Trung Quốc. Phân tích tính mạch lạc và liên kết trong văn bản tiếng Trung sau:

"{text}"

Trả về JSON với các trường:
- coherence_score: điểm tính mạch lạc logic (0-100)
- has_transitions: true nếu văn bản sử dụng từ liên kết phù hợp
- logical_flow: true nếu các ý được sắp xếp logic
- feedback: nhận xét ngắn gọn bằng tiếng Việt""",

            "task_achievement": f"""Bạn là chuyên gia ngôn ngữ Trung Quốc. Đánh giá xem câu trả lời tiếng Trung sau có đáp ứng yêu cầu đề bài không:

"{text}"

Trả về JSON với các trường:
- relevance_score: điểm độ liên quan đến chủ đề (0-100)
- completeness_score: điểm độ đầy đủ nội dung (0-100)
- feedback: nhận xét ngắn gọn bằng tiếng Việt""",

            "similarity": f"""So sánh hai văn bản tiếng Trung sau:

Văn bản nói: "{text}"
Văn bản gốc: "{reference_text}"

Trả về JSON với các trường:
- similarity_percentage: phần trăm nội dung khớp (0-100)
- missing_content: mảng các nội dung có trong văn bản gốc nhưng thiếu trong văn bản nói
- added_content: mảng các nội dung được thêm vào trong văn bản nói
- feedback: nhận xét ngắn gọn bằng tiếng Việt"""
        }
        
        prompt = base_prompts.get(analysis_type, base_prompts["grammar"])
        
        if context:
            prompt += f"\n\nNgữ cảnh bổ sung: {context}"
        
        return prompt


# ========== Factory Function ==========

def get_ai_provider(
    provider_type: AIProviderType,
    api_key: str,
    model: Optional[str] = None
) -> AIProvider:
    """
    Factory function to get AI provider
    
    Args:
        provider_type: OPENAI or GEMINI
        api_key: API key for the provider
        model: Optional model override
        
    Returns:
        AIProvider instance
    """
    if provider_type == AIProviderType.OPENAI:
        return OpenAIProvider(api_key, model or "gpt-4o")
    elif provider_type == AIProviderType.GEMINI:
        return GeminiProvider(api_key, model or "gemini-2.0-flash-exp")
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
