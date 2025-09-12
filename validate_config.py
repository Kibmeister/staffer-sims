#!/usr/bin/env python3
"""
Configuration Validation Script
Validates that all required environment variables are set correctly
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from config.env_loader import load_environment_config

def validate_configuration():
    """Validate the current configuration"""
    print("🔍 Validating Configuration...")
    print("=" * 50)
    
    try:
        # Load environment configuration
        load_environment_config()
        
        # Create settings instance (validation will be handled manually)
        settings = Settings.from_env()
        
        print("✅ Configuration loaded successfully!")
        print(f"📊 Environment: {settings.environment}")
        print(f"🐛 Debug Mode: {settings.debug}")
        print(f"📝 Log Level: {settings.log_level}")
        print()
        
        # Validate API Configuration
        print("🔑 API Configuration:")
        print(f"  📊 Provider: {settings.api_provider}")
        
        # Validate API Keys based on provider
        print("🔑 API Keys Validation:")
        if settings.api_provider in ["openai", "both"]:
            if settings.openai_api_key and len(settings.openai_api_key) > 10:
                print(f"  ✅ OpenAI: {'*' * 8}{settings.openai_api_key[-4:]}")
            else:
                print(f"  ❌ OpenAI: Missing or invalid")
        
        if settings.api_provider in ["openrouter", "both"]:
            if settings.openrouter_api_key and len(settings.openrouter_api_key) > 10:
                print(f"  ✅ OpenRouter: {'*' * 8}{settings.openrouter_api_key[-4:]}")
            else:
                print(f"  ❌ OpenRouter: Missing or invalid")
        
        # Always required
        if settings.langfuse_public_key and len(settings.langfuse_public_key) > 10:
            print(f"  ✅ Langfuse Public: {'*' * 8}{settings.langfuse_public_key[-4:]}")
        else:
            print(f"  ❌ Langfuse Public: Missing or invalid")
            
        if settings.langfuse_secret_key and len(settings.langfuse_secret_key) > 10:
            print(f"  ✅ Langfuse Secret: {'*' * 8}{settings.langfuse_secret_key[-4:]}")
        else:
            print(f"  ❌ Langfuse Secret: Missing or invalid")
        
        print()
        
        # Validate Service URLs
        print("🌐 Service URLs:")
        urls = [
            ("SUT", settings.sut_url),
            ("Proxy", settings.proxy_url),
            ("Langfuse", settings.langfuse_host)
        ]
        
        for name, url in urls:
            if url and url.startswith(('http://', 'https://')):
                print(f"  ✅ {name}: {url}")
            else:
                print(f"  ❌ {name}: Invalid URL")
        
        print()
        
        # Validate Performance Settings
        print("⚡ Performance Settings:")
        perf_settings = [
            ("Max Turns", settings.max_turns),
            ("Request Timeout", f"{settings.request_timeout}s"),
            ("Retry Attempts", settings.retry_attempts),
            ("Retry Delay", f"{settings.retry_delay}s")
        ]
        
        for name, value in perf_settings:
            print(f"  📊 {name}: {value}")
        
        print()
        
        # Test configuration methods
        print("🧪 Testing Configuration Methods:")
        try:
            langfuse_config = settings.get_langfuse_config()
            print(f"  ✅ Langfuse Config: {len(langfuse_config)} keys")
            
            proxy_config = settings.get_proxy_api_config()
            print(f"  ✅ Proxy API Config: {len(proxy_config)} keys")
            
            sut_config = settings.get_sut_config()
            print(f"  ✅ SUT Config: {len(sut_config)} keys")
            
            sut_api_config = settings.get_sut_api_config()
            print(f"  ✅ SUT API Config: {len(sut_api_config)} keys")
            
        except Exception as e:
            print(f"  ❌ Configuration method error: {e}")
        
        print()
        print("🎉 Configuration validation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def show_environment_info():
    """Show current environment information"""
    print("🌍 Environment Information:")
    print("=" * 50)
    
    env_vars = [
        "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
        "SUT_URL", "PROXY_URL", "LANGFUSE_HOST",
        "MAX_TURNS", "REQUEST_TIMEOUT", "RETRY_ATTEMPTS"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "Not set")
        if "KEY" in var or "SECRET" in var:
            value = "***" if value != "Not set" else value
        print(f"  {var}: {value}")

if __name__ == "__main__":
    print("🚀 Staffer Sims Configuration Validator")
    print("=" * 50)
    
    show_environment_info()
    print()
    
    success = validate_configuration()
    
    if success:
        print("\n✅ All checks passed! Configuration is ready.")
        sys.exit(0)
    else:
        print("\n❌ Configuration validation failed!")
        print("\n💡 To fix:")
        print("1. Copy env.template to .env")
        print("2. Fill in your API keys")
        print("3. Run this script again")
        sys.exit(1)
