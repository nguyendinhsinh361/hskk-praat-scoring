"""
Task Criteria Configuration
Maps each task code to its specific scoring criteria and max scores
Based on HSKK official criteria files
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class CriteriaType(str, Enum):
    """Types of scoring criteria"""
    TASK_ACHIEVEMENT = "task_achievement"
    PRONUNCIATION = "pronunciation"
    FLUENCY = "fluency"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    COHERENCE = "coherence"


class DataSource(str, Enum):
    """Data source for criteria"""
    PRAAT = "praat"
    AI = "ai"


@dataclass
class CriteriaConfig:
    """Configuration for a single criteria"""
    type: CriteriaType
    source: DataSource
    max_score: float
    name_vi: str  # Vietnamese name
    requires_reference: bool = False  # For task1 similarity comparison


@dataclass
class TaskConfig:
    """Configuration for a specific task"""
    task_code: str
    task_name: str
    exam_level: str  # "101", "102", "103"
    level_name: str  # "beginner", "intermediate", "advanced"
    question_count: int
    points_per_question: float
    total_points: float
    criteria: List[CriteriaConfig] = field(default_factory=list)
    
    @property
    def criteria_names(self) -> List[str]:
        return [c.type.value for c in self.criteria]
    
    @property
    def has_ai_criteria(self) -> bool:
        return any(c.source == DataSource.AI for c in self.criteria)
    
    @property
    def has_praat_criteria(self) -> bool:
        return any(c.source == DataSource.PRAAT for c in self.criteria)


# ========== 101 Sơ cấp (Beginner) ==========

HSKKSC1_CONFIG = TaskConfig(
    task_code="HSKKSC1",
    task_name="Nghe và nhắc lại",
    exam_level="101",
    level_name="beginner",
    question_count=15,
    points_per_question=2.0,
    total_points=30.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=1.0,
            name_vi="Khả năng hoàn thành yêu cầu",
            requires_reference=True
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=0.5,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=0.5,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKSC2_CONFIG = TaskConfig(
    task_code="HSKKSC2",
    task_name="Nghe và trả lời (câu ngắn)",
    exam_level="101",
    level_name="beginner",
    question_count=10,
    points_per_question=3.0,
    total_points=30.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=1.5,
            name_vi="Khả năng hoàn thành yêu cầu"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=0.5,
            name_vi="Độ chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=0.5,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=0.5,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKSC3_CONFIG = TaskConfig(
    task_code="HSKKSC3",
    task_name="Trả lời câu hỏi (đoạn ngắn)",
    exam_level="101",
    level_name="beginner",
    question_count=2,
    points_per_question=20.0,
    total_points=40.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=6.0,
            name_vi="Khả năng hoàn thành yêu cầu"
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=4.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=4.0,
            name_vi="Độ đa dạng và chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.VOCABULARY,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Vốn từ vựng"
        ),
        CriteriaConfig(
            type=CriteriaType.COHERENCE,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Tính mạch lạc và liên kết"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=2.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)


# ========== 102 Trung cấp (Intermediate) ==========

HSKKTC1_CONFIG = TaskConfig(
    task_code="HSKKTC1",
    task_name="Nghe và nhắc lại",
    exam_level="102",
    level_name="intermediate",
    question_count=10,
    points_per_question=3.0,
    total_points=30.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=1.5,
            name_vi="Khả năng hoàn thành yêu cầu",
            requires_reference=True
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=1.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=0.5,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKTC2_CONFIG = TaskConfig(
    task_code="HSKKTC2",
    task_name="Mô tả tranh (đoạn văn ngắn)",
    exam_level="102",
    level_name="intermediate",
    question_count=2,
    points_per_question=15.0,
    total_points=30.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=5.0,
            name_vi="Khả năng hoàn thành yêu cầu"
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=3.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=3.0,
            name_vi="Độ đa dạng và chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.VOCABULARY,
            source=DataSource.AI,
            max_score=1.0,
            name_vi="Vốn từ vựng"
        ),
        CriteriaConfig(
            type=CriteriaType.COHERENCE,
            source=DataSource.AI,
            max_score=1.0,
            name_vi="Tính mạch lạc và liên kết"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=2.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKTC3_CONFIG = TaskConfig(
    task_code="HSKKTC3",
    task_name="Trả lời câu hỏi (đoạn ngắn)",
    exam_level="102",
    level_name="intermediate",
    question_count=2,
    points_per_question=20.0,
    total_points=40.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=6.0,
            name_vi="Khả năng hoàn thành yêu cầu"
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=4.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=4.0,
            name_vi="Độ đa dạng và chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.VOCABULARY,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Vốn từ vựng"
        ),
        CriteriaConfig(
            type=CriteriaType.COHERENCE,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Tính mạch lạc và liên kết"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=2.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)


# ========== 103 Cao cấp (Advanced) ==========

HSKKCC1_CONFIG = TaskConfig(
    task_code="HSKKCC1",
    task_name="Nghe và nhắc lại",
    exam_level="103",
    level_name="advanced",
    question_count=3,
    points_per_question=10.0,
    total_points=30.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=4.0,
            name_vi="Khả năng hoàn thành yêu cầu",
            requires_reference=True
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=2.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Độ chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=2.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKCC2_CONFIG = TaskConfig(
    task_code="HSKKCC2",
    task_name="Đọc đoạn văn",
    exam_level="103",
    level_name="advanced",
    question_count=1,
    points_per_question=20.0,
    total_points=20.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=10.0,
            name_vi="Khả năng hoàn thành yêu cầu",
            requires_reference=True
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=5.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=5.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)

HSKKCC3_CONFIG = TaskConfig(
    task_code="HSKKCC3",
    task_name="Trả lời câu hỏi (đoạn ngắn)",
    exam_level="103",
    level_name="advanced",
    question_count=2,
    points_per_question=25.0,
    total_points=50.0,
    criteria=[
        CriteriaConfig(
            type=CriteriaType.TASK_ACHIEVEMENT,
            source=DataSource.AI,
            max_score=8.0,
            name_vi="Khả năng hoàn thành yêu cầu"
        ),
        CriteriaConfig(
            type=CriteriaType.PRONUNCIATION,
            source=DataSource.PRAAT,
            max_score=5.0,
            name_vi="Phát âm"
        ),
        CriteriaConfig(
            type=CriteriaType.GRAMMAR,
            source=DataSource.AI,
            max_score=4.0,
            name_vi="Độ đa dạng và chính xác ngữ pháp"
        ),
        CriteriaConfig(
            type=CriteriaType.VOCABULARY,
            source=DataSource.AI,
            max_score=2.0,
            name_vi="Vốn từ vựng"
        ),
        CriteriaConfig(
            type=CriteriaType.COHERENCE,
            source=DataSource.AI,
            max_score=3.0,
            name_vi="Tính mạch lạc và liên kết"
        ),
        CriteriaConfig(
            type=CriteriaType.FLUENCY,
            source=DataSource.PRAAT,
            max_score=3.0,
            name_vi="Độ trôi chảy"
        ),
    ]
)


# ========== Task Config Registry ==========

TASK_CONFIGS: Dict[str, TaskConfig] = {
    # 101 Sơ cấp
    "HSKKSC1": HSKKSC1_CONFIG,
    "HSKKSC2": HSKKSC2_CONFIG,
    "HSKKSC3": HSKKSC3_CONFIG,
    # 102 Trung cấp
    "HSKKTC1": HSKKTC1_CONFIG,
    "HSKKTC2": HSKKTC2_CONFIG,
    "HSKKTC3": HSKKTC3_CONFIG,
    # 103 Cao cấp
    "HSKKCC1": HSKKCC1_CONFIG,
    "HSKKCC2": HSKKCC2_CONFIG,
    "HSKKCC3": HSKKCC3_CONFIG,
}


def get_task_config(task_code: str) -> Optional[TaskConfig]:
    """Get task configuration by task code"""
    return TASK_CONFIGS.get(task_code)


def get_criteria_for_task(task_code: str) -> List[CriteriaConfig]:
    """Get list of criteria for a specific task"""
    config = get_task_config(task_code)
    return config.criteria if config else []


def get_max_scores_for_task(task_code: str) -> Dict[str, float]:
    """Get max scores by criteria type for a task"""
    config = get_task_config(task_code)
    if not config:
        return {}
    return {c.type.value: c.max_score for c in config.criteria}


def task_requires_reference(task_code: str) -> bool:
    """Check if task requires reference text (for similarity scoring)"""
    config = get_task_config(task_code)
    if not config:
        return False
    return any(c.requires_reference for c in config.criteria)
