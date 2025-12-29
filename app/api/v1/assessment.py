"""
Assessment Router - HSKK assessment endpoint
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends

from app.core.dependencies import get_assessment_service
from app.models.schemas import AssessmentResponse
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assess", tags=["Assessment"])


@router.post(
    "",
    response_model=AssessmentResponse,
    summary="Assess HSKK Speaking Proficiency",
    description="Upload audio file and get comprehensive HSKK assessment"
)
async def assess_hskk(
    audio_file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, flac)"),
    reference_text: str = Form(None, description="Optional reference text"),
    assessment_service: AssessmentService = Depends(get_assessment_service)
) -> AssessmentResponse:
    """
    Perform HSKK speaking proficiency assessment
    
    - **audio_file**: Audio recording of Chinese speech
    - **reference_text**: Optional reference text for comparison
    
    Returns comprehensive assessment including:
    - Overall score and achieved level
    - Component scores (pronunciation, fluency, grammar, vocabulary)
    - Acoustic features analysis
    - Detailed pronunciation feedback
    """
    # Read file content
    content = await audio_file.read()
    
    # Perform assessment
    return await assessment_service.assess(
        audio_content=content,
        filename=audio_file.filename,
        reference_text=reference_text
    )

