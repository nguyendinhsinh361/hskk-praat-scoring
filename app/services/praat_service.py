import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging
import time

from app.config import PRAAT_CONTAINER_NAME, PRAAT_OUTPUT_DIR
from app.models.hskk_models import AudioFeatures

logger = logging.getLogger(__name__)

class PraatService:
    def __init__(self):
        self.container_name = PRAAT_CONTAINER_NAME
        
    def _check_file_exists_in_container(self, file_path: str) -> bool:
        """Check if file exists in container"""
        try:
            cmd = ["docker", "exec", self.container_name, "ls", "-la", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking file in container: {e}")
            return False
    
    def _run_praat_script(self, script_name: str, audio_file: Path, output_file: Path, 
                         additional_args: list = None) -> bool:
        """Run a Praat script using docker exec with better error handling"""
        try:
            # Check if audio file exists in container
            container_audio_path = f"/data/audio_input/{audio_file.name}"
            if not self._check_file_exists_in_container(container_audio_path):
                logger.error(f"Audio file not found in container: {container_audio_path}")
                return False
            
            # Check if script exists
            container_script_path = f"/praat/scripts/{script_name}"
            if not self._check_file_exists_in_container(container_script_path):
                logger.error(f"Praat script not found in container: {container_script_path}")
                return False
            
            # Prepare Docker exec command
            cmd = [
                "docker", "exec", self.container_name,
                "praat", "--run", container_script_path,
                container_audio_path,
                f"/data/praat_output/{output_file.name}"
            ]
            
            if additional_args:
                cmd.extend(additional_args)
            
            logger.info(f"Running Praat command: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info(f"Praat script {script_name} executed successfully")
                if result.stdout.strip():
                    logger.debug(f"Praat output: {result.stdout}")
                return True
            else:
                logger.error(f"Praat script failed with return code {result.returncode}")
                logger.error(f"Praat stderr: {result.stderr}")
                logger.error(f"Praat stdout: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Praat script execution timed out")
            return False
        except FileNotFoundError:
            logger.error("Docker command not found. Is Docker installed and running?")
            return False
        except Exception as e:
            logger.error(f"Error running Praat script: {e}")
            return False
    
    def extract_features(self, audio_file: Path) -> Optional[AudioFeatures]:
        """Extract acoustic features using Praat"""
        output_file = PRAAT_OUTPUT_DIR / f"{audio_file.stem}_features.txt"
        
        logger.info(f"Extracting features from {audio_file.name}")
        logger.info(f"Audio file path: {audio_file}")
        logger.info(f"Output file path: {output_file}")
        
        # Ensure output directory exists
        PRAAT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Run Praat feature extraction
        if not self._run_praat_script("extract_features.praat", audio_file, output_file):
            logger.error("Feature extraction failed")
            return None
            
        # Wait a moment for file to be written
        time.sleep(1)
        
        # Parse results
        if output_file.exists():
            logger.info(f"Features file created successfully: {output_file}")
            return self._parse_features_file(output_file)
        else:
            logger.error(f"Output file not created: {output_file}")
            # List files in output directory for debugging
            try:
                output_files = list(PRAAT_OUTPUT_DIR.glob("*"))
                logger.info(f"Files in output directory: {output_files}")
            except Exception as e:
                logger.error(f"Could not list output directory: {e}")
            return None
    
    def _parse_features_file(self, features_file: Path) -> Optional[AudioFeatures]:
        """Parse Praat features output file"""
        try:
            features_dict = {}
            
            logger.info(f"Parsing features file: {features_file}")
            file_size = features_file.stat().st_size
            logger.info(f"Features file size: {file_size} bytes")
            
            with open(features_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Features file content:\n{content}")
            
            # Parse line by line
            with open(features_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                        
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value_str = parts[1].strip()
                            try:
                                if value_str.lower() in ['undefined', '--undefined--', 'nan', 'inf', '-inf']:
                                    logger.warning(f"Undefined value for {key}, using default")
                                    features_dict[key] = 0.0
                                else:
                                    features_dict[key] = float(value_str)
                            except ValueError:
                                logger.warning(f"Could not parse value for {key}: '{value_str}' on line {line_num}")
                                features_dict[key] = 0.0
            
            logger.info(f"Parsed {len(features_dict)} features")
            
            # Safe value extraction with defaults
            def safe_get(key, default, min_val=None, max_val=None):
                val = features_dict.get(key, default)
                if min_val is not None:
                    val = max(min_val, val)
                if max_val is not None:
                    val = min(max_val, val)
                return val
            
            duration = safe_get('duration', 0.0, 0.0)
            
            return AudioFeatures(
                # Basic
                duration=duration,
                
                # Pitch
                pitch_mean=safe_get('pitch_mean', 200.0, 50.0, 500.0),
                pitch_std=safe_get('pitch_std', 30.0, 0.0),
                pitch_range=safe_get('pitch_range', 100.0, 0.0),
                pitch_min=safe_get('pitch_min', 150.0, 50.0, 500.0),
                pitch_max=safe_get('pitch_max', 250.0, 50.0, 500.0),
                pitch_median=safe_get('pitch_median', 200.0, 50.0, 500.0),
                pitch_quantile_25=safe_get('pitch_quantile_25', 180.0, 50.0, 500.0),
                pitch_quantile_75=safe_get('pitch_quantile_75', 220.0, 50.0, 500.0),
                
                # Formants
                f1_mean=safe_get('f1_mean', 500.0, 200.0, 1000.0),
                f1_std=safe_get('f1_std', 50.0, 0.0),
                f2_mean=safe_get('f2_mean', 1500.0, 800.0, 3000.0),
                f2_std=safe_get('f2_std', 100.0, 0.0),
                f3_mean=safe_get('f3_mean', 2500.0, 1500.0, 4000.0),
                f3_std=safe_get('f3_std', 150.0, 0.0),
                f4_mean=safe_get('f4_mean', 3500.0, 2500.0, 5000.0),
                f4_std=safe_get('f4_std', 200.0, 0.0),
                
                # Intensity
                intensity_mean=safe_get('intensity_mean', 60.0, 0.0, 100.0),
                intensity_std=safe_get('intensity_std', 5.0, 0.0),
                intensity_min=safe_get('intensity_min', 40.0, 0.0, 100.0),
                intensity_max=safe_get('intensity_max', 80.0, 0.0, 100.0),
                
                # Spectral
                spectral_centroid=safe_get('spectral_centroid', 1000.0, 100.0),
                spectral_std=safe_get('spectral_std', 500.0, 0.0),
                spectral_skewness=safe_get('spectral_skewness', 0.0),
                spectral_kurtosis=safe_get('spectral_kurtosis', 3.0),
                
                # Voice quality
                hnr_mean=safe_get('hnr_mean', 20.0, 0.0, 40.0),
                hnr_std=safe_get('hnr_std', 2.0, 0.0),
                jitter_local=safe_get('jitter_local', 0.01, 0.0, 0.1),
                jitter_rap=safe_get('jitter_rap', 0.01, 0.0, 0.1),
                jitter_ppq5=safe_get('jitter_ppq5', 0.01, 0.0, 0.1),
                shimmer_local=safe_get('shimmer_local', 0.1, 0.0, 1.0),
                shimmer_apq3=safe_get('shimmer_apq3', 0.1, 0.0, 1.0),
                shimmer_apq5=safe_get('shimmer_apq5', 0.1, 0.0, 1.0),
                shimmer_apq11=safe_get('shimmer_apq11', 0.1, 0.0, 1.0),
                
                # Speech timing
                speech_rate=safe_get('speech_rate', 180.0, 0.0),
                articulation_rate=safe_get('articulation_rate', 200.0, 0.0),
                speech_duration=safe_get('speech_duration', duration, 0.0, duration),
                pause_duration=safe_get('pause_duration', 0.0, 0.0),
                pause_ratio=safe_get('pause_ratio', 0.1, 0.0, 1.0),
                num_pauses=int(safe_get('num_pauses', 0, 0)),
                mean_pause_duration=safe_get('mean_pause_duration', 0.0, 0.0),
                
                # Additional
                cog=safe_get('cog', 1000.0, 0.0),
                slope=safe_get('slope', 0.0),
                spread=safe_get('spread', 0.0)
            )
            
        except Exception as e:
            logger.error(f"Error parsing features file: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to Praat container"""
        try:
            # Test simple Praat command
            cmd = ["docker", "exec", self.container_name, "praat", "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Praat container connection successful. Version: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Praat test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Praat connection test timed out")
            return False
        except FileNotFoundError:
            logger.error("Docker command not found")
            return False
        except Exception as e:
            logger.error(f"Praat connection test failed: {e}")
            return False
    
    def debug_container_state(self) -> dict:
        """Debug container state and file system"""
        debug_info = {}
        
        try:
            # Check container status
            cmd = ["docker", "inspect", self.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            debug_info["container_running"] = result.returncode == 0
            
            if result.returncode == 0:
                # List data directories
                for dir_path in ["/data/audio_input", "/data/audio_output", "/data/praat_output", "/praat/scripts"]:
                    cmd = ["docker", "exec", self.container_name, "ls", "-la", dir_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    debug_info[f"dir_{dir_path.replace('/', '_')}"] = {
                        "success": result.returncode == 0,
                        "content": result.stdout if result.returncode == 0 else result.stderr
                    }
        except Exception as e:
            debug_info["error"] = str(e)
        
        return debug_info