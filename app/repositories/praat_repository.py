"""
Praat Repository - Docker container operations for Praat
Handles Docker commands, script execution, and output file reading
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict

from app.core.config import Settings
from app.core.exceptions import PraatConnectionError, PraatExecutionError

logger = logging.getLogger(__name__)


class PraatRepository:
    """Repository for Praat Docker container operations"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.container_name = settings.praat_container_name
        self.timeout = settings.praat_timeout
        self.praat_output_dir = settings.praat_output_dir
    
    def test_connection(self) -> bool:
        """
        Test connection to Praat container
        
        Returns:
            True if container is accessible
        """
        try:
            cmd = ["docker", "exec", self.container_name, "praat", "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Praat connection OK: {result.stdout.strip()}")
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
    
    def check_file_in_container(self, container_path: str) -> bool:
        """
        Check if file exists in container
        
        Args:
            container_path: Path inside container
            
        Returns:
            True if file exists
        """
        try:
            cmd = ["docker", "exec", self.container_name, "ls", "-la", container_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking file in container: {e}")
            return False
    
    def run_script(
        self, 
        script_name: str, 
        audio_filename: str, 
        output_filename: str
    ) -> bool:
        """
        Run Praat script in container
        
        Args:
            script_name: Name of Praat script
            audio_filename: Input audio filename
            output_filename: Output filename
            
        Returns:
            True if execution successful
            
        Raises:
            PraatExecutionError: If execution fails
        """
        try:
            # Container paths
            container_audio_path = f"/data/audio_input/{audio_filename}"
            container_script_path = f"/praat/scripts/{script_name}"
            container_output_path = f"/data/praat_output/{output_filename}"
            
            # Verify files exist
            if not self.check_file_in_container(container_audio_path):
                raise PraatExecutionError(f"Audio file not found: {container_audio_path}")
            
            if not self.check_file_in_container(container_script_path):
                raise PraatExecutionError(f"Script not found: {container_script_path}")
            
            # Build command
            cmd = [
                "docker", "exec", self.container_name,
                "praat", "--run", container_script_path,
                container_audio_path,
                container_output_path
            ]
            
            logger.info(f"Running Praat: {' '.join(cmd)}")
            
            # Execute
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Praat script executed successfully")
                return True
            else:
                logger.error(f"Praat failed: {result.stderr}")
                raise PraatExecutionError(f"Praat script failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise PraatExecutionError("Praat script timed out")
        except PraatExecutionError:
            raise
        except Exception as e:
            raise PraatExecutionError(f"Error running Praat: {e}")
    
    def read_output_file(self, filename: str) -> Optional[Dict[str, float]]:
        """
        Read and parse Praat output file
        
        Args:
            filename: Output filename
            
        Returns:
            Dictionary of feature name -> value, or None if failed
        """
        output_path = self.praat_output_dir / filename
        
        if not output_path.exists():
            logger.error(f"Output file not found: {output_path}")
            return None
        
        try:
            features = {}
            
            with open(output_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if line.startswith('#') or not line:
                        continue
                    
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value_str = parts[1].strip()
                            
                            try:
                                # Handle undefined values
                                if value_str.lower() in ['undefined', '--undefined--', 'nan', 'inf', '-inf']:
                                    features[key] = 0.0
                                else:
                                    features[key] = float(value_str)
                            except ValueError:
                                logger.warning(f"Could not parse {key}: '{value_str}'")
                                features[key] = 0.0
            
            logger.info(f"Parsed {len(features)} features from {filename}")
            return features
            
        except Exception as e:
            logger.error(f"Error reading output file: {e}")
            return None
    
    def get_debug_info(self) -> Dict:
        """Get container debug information"""
        debug_info = {"container_name": self.container_name}
        
        try:
            # Check container running
            cmd = ["docker", "inspect", self.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            debug_info["container_running"] = result.returncode == 0
            
            if result.returncode == 0:
                # List directories
                for dir_path in ["/data/audio_input", "/data/praat_output", "/praat/scripts"]:
                    cmd = ["docker", "exec", self.container_name, "ls", "-la", dir_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    debug_info[dir_path] = {
                        "accessible": result.returncode == 0,
                        "content": result.stdout if result.returncode == 0 else result.stderr
                    }
                    
        except Exception as e:
            debug_info["error"] = str(e)
        
        return debug_info
