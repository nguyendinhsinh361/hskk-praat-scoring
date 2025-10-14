from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import time
from pathlib import Path
import logging
import os

from app.models.hskk_models import HSKKAssessmentRequest, HSKKAssessmentResponse, HSKKLevel
from app.services.praat_service import PraatService  
from app.services.scoring_service import HSKKScoringService
from app.services.audio_service import AudioService
from app.config import AUDIO_INPUT_DIR, SUPPORTED_FORMATS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="HSKK Scoring System",
    description="Chinese Speaking Proficiency Assessment using Praat",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

# Create frontend directories if they don't exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Frontend directory: {FRONTEND_DIR}")
logger.info(f"Static directory: {STATIC_DIR} (exists: {STATIC_DIR.exists()})")
logger.info(f"Templates directory: {TEMPLATES_DIR} (exists: {TEMPLATES_DIR.exists()})")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info("✅ Static files mounted successfully")
except Exception as e:
    logger.error(f"❌ Failed to mount static files: {e}")

# Initialize templates
try:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    logger.info("✅ Templates initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize templates: {e}")
    templates = None

# Initialize services
praat_service = None
scoring_service = None
audio_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global praat_service, scoring_service, audio_service
    
    logger.info("Starting HSKK Scoring System...")
    
    # Check if templates exist
    if TEMPLATES_DIR.exists():
        template_files = list(TEMPLATES_DIR.glob("*.html"))
        logger.info(f"Found {len(template_files)} template files: {[f.name for f in template_files]}")
    else:
        logger.warning(f"Templates directory does not exist: {TEMPLATES_DIR}")
    
    try:
        # Initialize services without Docker client dependency
        praat_service = PraatService()
        scoring_service = HSKKScoringService()
        audio_service = AudioService()
        
        logger.info("Services initialized successfully")
        
        # Wait for containers to be fully ready
        time.sleep(5)
        
        # Test Praat connection
        if praat_service.test_connection():
            logger.info("Praat container connection verified")
        else:
            logger.warning("Praat container connection failed - will retry later")
            # Debug container state
            debug_info = praat_service.debug_container_state()
            logger.info(f"Container debug info: {debug_info}")
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

def get_services():
    """Dependency to get services"""
    if not all([praat_service, scoring_service, audio_service]):
        raise HTTPException(status_code=503, detail="Services not initialized")
    return praat_service, scoring_service, audio_service

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main landing page"""
    if templates is None:
        return HTMLResponse(content="""
            <h1>Template Error</h1>
            <p>Templates directory not found. Please create frontend/templates/index.html</p>
        """, status_code=500)
    
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        return HTMLResponse(content=f"""
            <h1>Error Loading Page</h1>
            <p>Error: {str(e)}</p>
            <p>Please ensure frontend/templates/index.html exists</p>
        """, status_code=500)

@app.get("/features-tester", response_class=HTMLResponse)
async def features_tester(request: Request):
    """Features testing page"""
    if templates is None:
        return HTMLResponse(content="""
            <h1>Template Error</h1>
            <p>Templates directory not found. Please create frontend/templates/features_tester.html</p>
        """, status_code=500)
    
    try:
        return templates.TemplateResponse("features_tester.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering features_tester.html: {e}")
        return HTMLResponse(content=f"""
            <h1>Error Loading Features Tester</h1>
            <p>Error: {str(e)}</p>
            <p>Please ensure frontend/templates/features_tester.html exists</p>
        """, status_code=500)

@app.post("/assess", response_model=HSKKAssessmentResponse)
async def assess_hskk(
    audio_file: UploadFile = File(...),
    target_level: HSKKLevel = HSKKLevel.INTERMEDIATE,
    reference_text: str = None,
    services = Depends(get_services)
):
    """Assess HSKK speaking proficiency"""
    praat_svc, scoring_svc, audio_svc = services
    start_time = time.time()
    
    try:
        # Validate file format
        if not audio_svc.is_supported_format(audio_file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported audio format. Supported: {SUPPORTED_FORMATS}"
            )
        
        # Save uploaded file
        input_path = AUDIO_INPUT_DIR / audio_file.filename
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        logger.info(f"Processing audio file: {audio_file.filename} ({input_path.stat().st_size} bytes)")
        
        # Process audio (this will also copy to the right location for Praat)
        processed_path = audio_svc.preprocess_audio(input_path)
        if not processed_path:
            raise HTTPException(status_code=500, detail="Audio preprocessing failed")
        
        logger.info(f"Audio preprocessed successfully: {processed_path}")
        
        # Extract acoustic features using Praat
        features = praat_svc.extract_features(processed_path)
        if not features:
            # Try to get debug information
            debug_info = praat_svc.debug_container_state()
            logger.error(f"Feature extraction failed. Debug info: {debug_info}")
            raise HTTPException(status_code=500, detail="Failed to extract audio features. Check system health.")
        
        logger.info(f"Features extracted successfully: duration={features.duration:.2f}s, pitch_mean={features.pitch_mean:.1f}Hz")
        
        # Generate transcription placeholder (integrate Whisper here if needed)
        transcription = f"音频分析完成。文件: {audio_file.filename}, 时长: {features.duration:.1f}秒, 平均音高: {features.pitch_mean:.1f}Hz"
        
        # Calculate HSKK score
        hskk_score = scoring_svc.calculate_hskk_score(
            features, target_level, transcription
        )
        
        # Create pronunciation assessment
        pronunciation = scoring_svc.create_pronunciation_assessment(
            features, reference_text
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"Assessment completed successfully in {processing_time:.2f}s - Overall Score: {hskk_score.overall_score:.1f}")
        
        return HSKKAssessmentResponse(
            success=True,
            score=hskk_score,
            features=features,
            pronunciation=pronunciation,
            transcription=transcription,
            error_message=None,
            processing_time=processing_time
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Assessment failed with unexpected error: {e}")
        return HSKKAssessmentResponse(
            success=False,
            score=None,
            features=None,
            pronunciation=None,
            transcription=None,
            error_message=f"System error: {str(e)}",
            processing_time=time.time() - start_time
        )

@app.get("/debug")
async def debug_info(services = Depends(get_services)):
    """Debug endpoint for system information"""
    praat_svc, scoring_svc, audio_svc = services
    
    debug_data = {
        "system": {
            "praat_container": praat_svc.container_name,
            "audio_formats": SUPPORTED_FORMATS,
            "target_sample_rate": audio_svc.target_sr
        },
        "frontend": {
            "frontend_dir": str(FRONTEND_DIR),
            "frontend_exists": FRONTEND_DIR.exists(),
            "static_dir": str(STATIC_DIR),
            "static_exists": STATIC_DIR.exists(),
            "templates_dir": str(TEMPLATES_DIR),
            "templates_exist": TEMPLATES_DIR.exists(),
            "template_files": [f.name for f in TEMPLATES_DIR.glob("*.html")] if TEMPLATES_DIR.exists() else []
        },
        "praat_connection": praat_svc.test_connection(),
        "container_debug": praat_svc.debug_container_state(),
        "directories": {
            "audio_input_exists": AUDIO_INPUT_DIR.exists(),
            "audio_input_files": [f.name for f in AUDIO_INPUT_DIR.glob("*")] if AUDIO_INPUT_DIR.exists() else [],
        }
    }
    
    return debug_data

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "service": "HSKK Scoring System",
        "version": "1.0.0",
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check Praat service
    try:
        if praat_service and praat_service.test_connection():
            status["components"]["praat"] = "healthy"
        else:
            status["components"]["praat"] = "unhealthy"
            status["status"] = "degraded"
    except Exception as e:
        status["components"]["praat"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Check required directories
    required_dirs = [
        AUDIO_INPUT_DIR,
        Path("data/audio_output"),
        Path("data/praat_output")
    ]
    
    dirs_status = all(dir_path.exists() for dir_path in required_dirs)
    status["components"]["storage"] = "healthy" if dirs_status else "unhealthy"
    
    # Check frontend
    status["components"]["frontend"] = "healthy" if TEMPLATES_DIR.exists() else "missing"
    
    if not dirs_status or not TEMPLATES_DIR.exists():
        status["status"] = "degraded"
    
    return status

@app.get("/levels")
async def get_hskk_levels():
    """Get available HSKK levels and detailed descriptions"""
    return {
        "levels": [level.value for level in HSKKLevel],
        "descriptions": {
            "elementary": {
                "chinese": "初级",
                "english": "Elementary Level",
                "description": "Basic Chinese speaking skills for daily communication",
                "equivalent": "HSK 1-3 equivalent",
                "speech_rate": "60-120 syllables/minute",
                "requirements": [
                    "Simple expressions and basic vocabulary",
                    "Clear pronunciation of individual sounds", 
                    "Basic sentence patterns",
                    "Ability to express basic needs and ideas"
                ]
            },
            "intermediate": {
                "chinese": "中级", 
                "english": "Intermediate Level",
                "description": "Intermediate Chinese speaking skills for academic/professional contexts",
                "equivalent": "HSK 4-5 equivalent",
                "speech_rate": "120-180 syllables/minute",
                "requirements": [
                    "Complex sentence structures",
                    "Natural speech rhythm and flow",
                    "Appropriate use of tone and intonation",
                    "Coherent expression of abstract ideas"
                ]
            },
            "advanced": {
                "chinese": "高级",
                "english": "Advanced Level", 
                "description": "Advanced Chinese speaking skills approaching native fluency",
                "equivalent": "HSK 6+ equivalent",
                "speech_rate": "150-220 syllables/minute", 
                "requirements": [
                    "Near-native pronunciation accuracy",
                    "Sophisticated vocabulary and expressions",
                    "Natural prosody and emotional expression",
                    "Ability to handle complex topics with nuance"
                ]
            }
        },
        "scoring_criteria": {
            "pronunciation": {
                "weight": "35%",
                "chinese": "发音准确度",
                "english": "Pronunciation Accuracy",
                "measures": ["Sound accuracy", "Voice quality", "Articulation clarity"]
            },
            "fluency": {
                "weight": "35%",
                "chinese": "流利程度", 
                "english": "Speaking Fluency",
                "measures": ["Speech rate", "Pause patterns", "Rhythm and flow"]
            },
            "grammar": {
                "weight": "15%",
                "chinese": "语法正确性",
                "english": "Grammar Correctness", 
                "measures": ["Sentence structure", "Word order", "Grammatical accuracy"]
            },
            "vocabulary": {
                "weight": "15%",
                "chinese": "词汇丰富度",
                "english": "Vocabulary Richness",
                "measures": ["Word variety", "Appropriate usage", "Complexity level"]
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)