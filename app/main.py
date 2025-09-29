from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
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

# Initialize services
praat_service = None
scoring_service = None
audio_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global praat_service, scoring_service, audio_service
    
    logger.info("Starting HSKK Scoring System...")
    
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
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>HSKK Scoring System</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f8f9fa; }
                .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; color: #333; margin-bottom: 30px; }
                .feature { margin: 15px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff; }
                .link { display: inline-block; margin: 10px; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; transition: all 0.3s; }
                .link:hover { background: #0056b3; transform: translateY(-2px); }
                .demo-section { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .code { background: #263238; color: #ffffff; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 14px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎤 HSKK Chinese Speaking Assessment</h1>
                    <p><strong>汉语水平口语考试</strong> - Automated Chinese Speaking Proficiency Testing</p>
                    <p>Powered by Praat Acoustic Analysis</p>
                </div>
                
                <div class="feature">
                    <h3>🎯 Key Features</h3>
                    <ul>
                        <li><strong>Professional Acoustic Analysis:</strong> Pitch, formants, voice quality using Praat</li>
                        <li><strong>HSKK Standard Scoring:</strong> Elementary (初级), Intermediate (中级), Advanced (高级)</li>
                        <li><strong>Comprehensive Assessment:</strong> Pronunciation, fluency, prosody evaluation</li>
                        <li><strong>Real-time Processing:</strong> Upload audio and get instant detailed feedback</li>
                    </ul>
                </div>
                
                <div class="demo-section">
                    <h3>🚀 Quick Test</h3>
                    <p>Upload an audio file (WAV, MP3, M4A, FLAC) to test the system:</p>
                    <div class="code">
curl -X POST "http://localhost:8000/assess" \\
  -F "audio_file=@your_speech.wav" \\
  -F "target_level=intermediate"</div>
                </div>
                
                <div class="feature">
                    <h3>📊 Scoring Methodology</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
                        <div>
                            <h4>🎵 Pronunciation (35%)</h4>
                            <p>发音准确度 - Accuracy, clarity, voice quality</p>
                        </div>
                        <div>
                            <h4>⚡ Fluency (35%)</h4>
                            <p>流利程度 - Speech rate, pauses, natural flow</p>
                        </div>
                        <div>
                            <h4>📝 Grammar (15%)</h4>
                            <p>语法正确性 - Sentence structure, syntax</p>
                        </div>
                        <div>
                            <h4>📚 Vocabulary (15%)</h4>
                            <p>词汇丰富度 - Word variety, appropriateness</p>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/docs" class="link">📚 API Documentation</a>
                    <a href="/health" class="link">🔍 System Health</a>
                    <a href="/levels" class="link">📋 HSKK Levels</a>
                    <a href="/debug" class="link">🛠️ Debug Info</a>
                </div>
            </div>
        </body>
    </html>
    """

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
        "praat_connection": praat_svc.test_connection(),
        "container_debug": praat_svc.debug_container_state(),
        "directories": {
            "audio_input_exists": AUDIO_INPUT_DIR.exists(),
            "audio_input_files": list(AUDIO_INPUT_DIR.glob("*")) if AUDIO_INPUT_DIR.exists() else [],
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
    
    if not dirs_status:
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