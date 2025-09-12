"""
Environment Configuration Management
Centralized settings for all environment variables and configuration
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import logging

@dataclass
class Settings:
    """Centralized application settings"""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_provider: str = "openrouter"  # "openai", "openrouter", or "both"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    
    # Service URLs
    sut_url: str = "http://localhost:8080/sut/chat"
    proxy_url: str = "https://openrouter.ai/api/v1/chat/completions"
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Performance Settings
    max_turns: int = 18
    request_timeout: int = 120
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # File Paths
    output_dir: str = "output"
    config_dir: str = "config"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """Validate settings after initialization"""
        self._validate_required_fields()
        self._set_derived_settings()
    
    def _validate_required_fields(self):
        """Validate that required fields are set"""
        # Always required
        required_fields = [
            ("langfuse_public_key", "LANGFUSE_PUBLIC_KEY"),
            ("langfuse_secret_key", "LANGFUSE_SECRET_KEY")
        ]
        
        # API provider specific requirements
        if self.api_provider in ["openai", "both"]:
            required_fields.append(("openai_api_key", "OPENAI_API_KEY"))
        
        if self.api_provider in ["openrouter", "both"]:
            required_fields.append(("openrouter_api_key", "OPENROUTER_API_KEY"))
        
        missing_fields = []
        for field_name, env_var in required_fields:
            if not getattr(self, field_name):
                missing_fields.append(f"{field_name} (from {env_var})")
        
        if missing_fields:
            # Only raise error if not in validation mode
            if not os.getenv("SKIP_VALIDATION", "false").lower() == "true":
                raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    def _set_derived_settings(self):
        """Set derived settings based on environment"""
        if self.environment == "production":
            self.debug = False
            self.log_level = "WARNING"
        elif self.environment == "staging":
            self.debug = False
            self.log_level = "INFO"
        else:  # development
            self.debug = True
            self.log_level = "DEBUG"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables"""
        return cls(
            # Environment
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            
            # API Configuration
            api_provider=os.getenv("API_PROVIDER", "openrouter"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            
            # Service URLs
            sut_url=os.getenv("SUT_URL", "http://localhost:8080/sut/chat"),
            proxy_url=os.getenv("PROXY_URL", "https://openrouter.ai/api/v1/chat/completions"),
            langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            
            # Performance Settings
            max_turns=int(os.getenv("MAX_TURNS", "18")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "120")),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            
            # File Paths
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            config_dir=os.getenv("CONFIG_DIR", "config"),
            
            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding sensitive data)"""
        sensitive_fields = {"openai_api_key", "openrouter_api_key", "langfuse_public_key", "langfuse_secret_key"}
        return {k: v for k, v in self.__dict__.items() if k not in sensitive_fields}
    
    def get_langfuse_config(self) -> Dict[str, str]:
        """Get Langfuse configuration"""
        return {
            "public_key": self.langfuse_public_key,
            "secret_key": self.langfuse_secret_key,
            "host": self.langfuse_host
        }
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """Get Proxy configuration"""
        return {
            "url": self.proxy_url,
            "headers": {
                "Authorization": f"Bearer {self.openrouter_api_key}"
            }
        }
    
    def get_sut_config(self) -> Dict[str, str]:
        """Get SUT configuration"""
        return {
            "url": self.sut_url
        }
    
    def get_sut_api_config(self) -> Dict[str, Any]:
        """Get SUT API configuration based on provider setting"""
        if self.api_provider == "openai":
            return {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openai_api_key}"},
                "model": "gpt-4o-mini"
            }
        elif self.api_provider == "openrouter":
            return {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openrouter_api_key}"},
                "model": "openai/gpt-4o-mini"  # OpenRouter model format
            }
        else:  # both - default to OpenAI for SUT
            return {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openai_api_key}"},
                "model": "gpt-4o-mini"
            }
    
    def get_proxy_api_config(self) -> Dict[str, Any]:
        """Get Proxy API configuration based on provider setting"""
        if self.api_provider == "openai":
            return {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openai_api_key}"},
                "model": "gpt-4o-mini"
            }
        elif self.api_provider == "openrouter":
            return {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openrouter_api_key}"},
                "model": "openai/gpt-4o-mini"  # OpenRouter model format
            }
        else:  # both - use OpenRouter for proxy
            return {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {self.openrouter_api_key}"},
                "model": "openai/gpt-4o-mini"
            }

# Global settings instance - will be created when needed
settings = None

def get_settings() -> Settings:
    """Get the global settings instance, creating it if needed"""
    global settings
    if settings is None:
        settings = Settings.from_env()
    return settings
