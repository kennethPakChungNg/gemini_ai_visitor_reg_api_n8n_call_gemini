from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""
    
    # Application Configuration
    app_name: str = "AI Visitor Registration API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # AI Provider Configuration
    ai_provider: str = "gemini"  # "gemini" or "openrouter"
    ai_model: str = "gemini-2.5-flash"  # Direct Gemini API model
    
    # Gemini AI Configuration (for direct API access)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # OpenRouter API Configuration (alternative to direct Gemini API)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # WhizProp CS API Configuration - Made optional for testing
    whizprop_base_url: str = "https://whizprop-tablet.necess.com.hk"  # Default value
    whizprop_api_key: str = ""  # Default empty, can be set via env
    whizprop_access_token: str = ""  # Legacy field, optional
    
    # WhizProp CS API Configuration - New (for dynamic token management)
    whizprop_device_id: Optional[str] = None
    whizprop_username: Optional[str] = None
    whizprop_password: Optional[str] = None

    # Effective properties for backward compatibility
    @property
    def effective_api_key(self) -> str:
        """Get API key from whizprop configuration."""
        return self.whizprop_api_key
    
    @property 
    def effective_base_url(self) -> str:
        """Get base URL from whizprop configuration."""
        return self.whizprop_base_url or "https://whizprop-tablet.necess.com.hk"
    
    @property
    def effective_device_id(self) -> Optional[str]:
        """Get device ID from whizprop configuration."""
        return self.whizprop_device_id

    model_config = {
        "env_file": [".env", "../.env", "../../.env"],  # Look in multiple locations
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra fields
    }


# Global settings instance
def get_settings():
    """Get a fresh settings instance."""
    return Settings()

settings = get_settings() 