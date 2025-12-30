"""
Praat Service - Acoustic feature extraction
Uses Praat CLI via Docker container
"""
import logging
from pathlib import Path
from typing import Optional, Dict

from app.core.config import Settings
from app.core.exceptions import FeatureExtractionError
from app.models.schemas import AudioFeatures
from app.repositories.praat_repository import PraatRepository

logger = logging.getLogger(__name__)


class PraatService:
    """Service for Praat acoustic analysis"""
    
    def __init__(self, settings: Settings, repository: PraatRepository):
        self.settings = settings
        self.repository = repository
    
    def test_connection(self) -> bool:
        """Test connection to Praat container"""
        return self.repository.test_connection()
    
    def get_debug_info(self) -> Dict:
        """Get debug information about Praat container"""
        return self.repository.get_debug_info()
    
    def extract_features(self, audio_path: Path) -> Optional[AudioFeatures]:
        """
        Extract 43 acoustic features from audio file
        """
        output_filename = f"{audio_path.stem}_features.txt"
        
        logger.info(f"Extracting features from {audio_path.name}")
        
        try:
            # Run Praat script (no sleep needed - synchronous)
            success = self.repository.run_script(
                "extract_features.praat",
                audio_path.name,
                output_filename
            )
            
            if not success:
                raise FeatureExtractionError("Praat script execution failed")
            
            # Read and parse results
            features_dict = self.repository.read_output_file(output_filename)
            
            if features_dict is None:
                raise FeatureExtractionError("Could not read features output file")
            
            return self._build_audio_features(features_dict)
            
        except FeatureExtractionError:
            raise
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise FeatureExtractionError(f"Feature extraction failed: {e}")
    
    def _build_audio_features(self, features_dict: Dict[str, float]) -> AudioFeatures:
        """Build AudioFeatures model from parsed dictionary"""
        
        def safe_get(key: str, default: float, min_val: float = None, max_val: float = None) -> float:
            val = features_dict.get(key, default)
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val
        
        duration = safe_get('duration', 0.0, 0.0)
        
        return AudioFeatures(
            duration=duration,
            pitch_mean=safe_get('pitch_mean', 200.0, 50.0, 500.0),
            pitch_std=safe_get('pitch_std', 30.0, 0.0),
            pitch_range=safe_get('pitch_range', 100.0, 0.0),
            pitch_min=safe_get('pitch_min', 150.0, 50.0, 500.0),
            pitch_max=safe_get('pitch_max', 250.0, 50.0, 500.0),
            pitch_median=safe_get('pitch_median', 200.0, 50.0, 500.0),
            pitch_quantile_25=safe_get('pitch_quantile_25', 180.0, 50.0, 500.0),
            pitch_quantile_75=safe_get('pitch_quantile_75', 220.0, 50.0, 500.0),
            f1_mean=safe_get('f1_mean', 500.0, 200.0, 1000.0),
            f1_std=safe_get('f1_std', 50.0, 0.0),
            f2_mean=safe_get('f2_mean', 1500.0, 800.0, 3000.0),
            f2_std=safe_get('f2_std', 100.0, 0.0),
            f3_mean=safe_get('f3_mean', 2500.0, 1500.0, 4000.0),
            f3_std=safe_get('f3_std', 150.0, 0.0),
            f4_mean=safe_get('f4_mean', 3500.0, 2500.0, 5000.0),
            f4_std=safe_get('f4_std', 200.0, 0.0),
            intensity_mean=safe_get('intensity_mean', 60.0, 0.0, 100.0),
            intensity_std=safe_get('intensity_std', 5.0, 0.0),
            intensity_min=safe_get('intensity_min', 40.0, 0.0, 100.0),
            intensity_max=safe_get('intensity_max', 80.0, 0.0, 100.0),
            spectral_centroid=safe_get('spectral_centroid', 1000.0, 100.0),
            spectral_std=safe_get('spectral_std', 500.0, 0.0),
            spectral_skewness=safe_get('spectral_skewness', 0.0),
            spectral_kurtosis=safe_get('spectral_kurtosis', 3.0),
            hnr_mean=safe_get('hnr_mean', 20.0, 0.0, 40.0),
            hnr_std=safe_get('hnr_std', 2.0, 0.0),
            jitter_local=safe_get('jitter_local', 0.01, 0.0, 0.1),
            jitter_rap=safe_get('jitter_rap', 0.01, 0.0, 0.1),
            jitter_ppq5=safe_get('jitter_ppq5', 0.01, 0.0, 0.1),
            shimmer_local=safe_get('shimmer_local', 0.1, 0.0, 1.0),
            shimmer_apq3=safe_get('shimmer_apq3', 0.1, 0.0, 1.0),
            shimmer_apq5=safe_get('shimmer_apq5', 0.1, 0.0, 1.0),
            shimmer_apq11=safe_get('shimmer_apq11', 0.1, 0.0, 1.0),
            speech_rate=safe_get('speech_rate', 180.0, 0.0),
            articulation_rate=safe_get('articulation_rate', 200.0, 0.0),
            speech_duration=safe_get('speech_duration', duration, 0.0, duration),
            pause_duration=safe_get('pause_duration', 0.0, 0.0),
            pause_ratio=safe_get('pause_ratio', 0.1, 0.0, 1.0),
            num_pauses=int(safe_get('num_pauses', 0, 0)),
            mean_pause_duration=safe_get('mean_pause_duration', 0.0, 0.0),
            cog=safe_get('cog', 1000.0, 0.0),
            slope=safe_get('slope', 0.0),
            spread=safe_get('spread', 0.0)
        )