"""
Environment Loader Utility
Handles loading environment-specific configurations
"""
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EnvironmentLoader:
    """Loads environment-specific configuration files"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.environments_dir = self.config_dir / "environments"
    
    def load_environment_file(self, environment: str) -> Dict[str, str]:
        """Load environment-specific configuration file"""
        env_file = self.environments_dir / f"{environment}.env"
        
        if not env_file.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return {}
        
        config = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            
            logger.info(f"Loaded {len(config)} settings from {env_file}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading environment file {env_file}: {e}")
            return {}
    
    def apply_environment_config(self, environment: str) -> None:
        """Apply environment-specific configuration to os.environ"""
        config = self.load_environment_file(environment)
        
        for key, value in config.items():
            if key not in os.environ:  # Don't override existing env vars
                os.environ[key] = value
                logger.debug(f"Set {key} from environment config")
    
    def get_available_environments(self) -> list:
        """Get list of available environment configurations"""
        if not self.environments_dir.exists():
            return []
        
        env_files = []
        for env_file in self.environments_dir.glob("*.env"):
            env_files.append(env_file.stem)
        
        return sorted(env_files)

def load_environment_config(environment: str = None) -> None:
    """Load environment configuration"""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    loader = EnvironmentLoader()
    loader.apply_environment_config(environment)
    
    logger.info(f"Environment configuration loaded for: {environment}")
    logger.info(f"Available environments: {loader.get_available_environments()}")

# Auto-load environment config when module is imported
if __name__ != "__main__":
    load_environment_config()
