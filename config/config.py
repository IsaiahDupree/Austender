"""
Configuration Module

This module manages application configuration across different environments
(development, testing, production) and provides access to configuration values.
"""

import os
import sys
import json
import socket
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv


class Environment(Enum):
    """Environment enumeration."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Config:
    """Central configuration class with environment-specific settings."""
    
    def __init__(self):
        """Initialize configuration."""
        self._load_environment_variables()
        self._setup_paths()
        self._setup_environment()
        self._load_config()
    
    def _load_environment_variables(self) -> None:
        """Load environment variables from .env file."""
        # Determine which .env file to load based on ENV variable
        env_name = os.getenv("ENV", "development").lower()
        env_file = f".env.{env_name}" if env_name != "development" else ".env"
        
        # Load the appropriate .env file if it exists
        if os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            load_dotenv()  # Fall back to default .env
    
    def _setup_paths(self) -> None:
        """Set up important file paths."""
        self.BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.CONFIG_DIR = self.BASE_DIR / "config"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.DATA_DIR = self.BASE_DIR / "data"
        
        # Create necessary directories
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)
    
    def _setup_environment(self) -> None:
        """Determine and set up the current environment."""
        env_name = os.getenv("ENV", "development").lower()
        
        if env_name == "production" or env_name == "prod":
            self.ENVIRONMENT = Environment.PRODUCTION
        elif env_name == "testing" or env_name == "test":
            self.ENVIRONMENT = Environment.TESTING
        else:
            self.ENVIRONMENT = Environment.DEVELOPMENT
        
        self.IS_DEVELOPMENT = self.ENVIRONMENT == Environment.DEVELOPMENT
        self.IS_TESTING = self.ENVIRONMENT == Environment.TESTING
        self.IS_PRODUCTION = self.ENVIRONMENT == Environment.PRODUCTION
        
        # Get host information
        self.HOSTNAME = socket.gethostname()
    
    def _load_config(self) -> None:
        """Load and set configuration values from various sources."""
        # Database configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{self.BASE_DIR}/database/opportunities.db")
        
        # API Keys with validation
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
        self.FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
        self.API_KEY = os.getenv("API_KEY", "")  # For API authentication
        
        # Check if API keys are present in production
        if self.IS_PRODUCTION:
            missing_keys = []
            if not self.OPENAI_API_KEY:
                missing_keys.append("OPENAI_API_KEY")
            if not self.API_KEY:
                missing_keys.append("API_KEY")
                
            if missing_keys:
                print(f"WARNING: Missing required API keys in production: {', '.join(missing_keys)}")
        
        # Web server configuration
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", 8000))
        self.BASE_URL = os.getenv("BASE_URL", f"http://localhost:{self.PORT}")
        
        # Scraper URLs
        self.AUSTENDER_URL = os.getenv("AUSTENDER_URL", "https://www.tenders.gov.au")
        self.ANI_URL = os.getenv("ANI_URL", "https://www.ani.gov.au")
        self.ICN_URL = os.getenv("ICN_URL", "https://gateway.icn.org.au")
        self.SAM_URL = os.getenv("SAM_URL", "https://sam.gov")
        
        # Scraper settings
        self.USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))  # seconds
        self.RETRY_COUNT = int(os.getenv("RETRY_COUNT", 3))
        self.RETRY_DELAY = int(os.getenv("RETRY_DELAY", 5))  # seconds
        
        # Email configuration
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", "")
        self.EMAIL_BCC = os.getenv("EMAIL_BCC", "").split(",") if os.getenv("EMAIL_BCC") else []
        
        # Scheduler settings
        self.UPDATE_INTERVAL_DAYS = int(os.getenv("UPDATE_INTERVAL_DAYS", 15))  # twice a month
        self.SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
        
        # Logging configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.LOG_FILE = os.path.join(str(self.LOGS_DIR), "app.log")
        
        # Security settings
        self.SECRET_KEY = os.getenv("SECRET_KEY", self._generate_secret_key())
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.RATE_LIMIT = int(os.getenv("RATE_LIMIT", 60))  # requests per minute
        
        # Performance settings
        self.WORKERS = int(os.getenv("WORKERS", 4))
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", 300))  # 5 minutes
    
    def _generate_secret_key(self) -> str:
        """Generate a random secret key for development."""
        if self.IS_PRODUCTION:
            print("WARNING: Using auto-generated SECRET_KEY in production is not recommended")
        return os.urandom(32).hex()
    
    def validate(self) -> List[str]:
        """Validate the configuration and return a list of validation errors."""
        errors = []
        
        # Validate database URL
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        
        # Validate email settings if in production
        if self.IS_PRODUCTION:
            if not self.SMTP_SERVER:
                errors.append("SMTP_SERVER is not set in production")
            if not self.SMTP_USERNAME:
                errors.append("SMTP_USERNAME is not set in production")
            if not self.SMTP_PASSWORD:
                errors.append("SMTP_PASSWORD is not set in production")
            if not self.EMAIL_FROM:
                errors.append("EMAIL_FROM is not set in production")
        
        return errors
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"Config(environment={self.ENVIRONMENT.value}, database_url={self.DATABASE_URL})"
    
    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = {k: v for k, v in self.__dict__.items() 
                     if not k.startswith('_') and k.isupper()}
        
        # Mask sensitive values
        if mask_secrets:
            for key in ["OPENAI_API_KEY", "PERPLEXITY_API_KEY", "FIRECRAWL_API_KEY", 
                       "API_KEY", "SMTP_PASSWORD", "SECRET_KEY"]:
                if key in config_dict and config_dict[key]:
                    config_dict[key] = f"{config_dict[key][:4]}...{config_dict[key][-4:]}" \
                                        if len(config_dict[key]) > 8 else "****"
        
        return config_dict


# Create a singleton instance
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Initialize the config and export all constants
config = get_config()

# Export all uppercase attributes as module-level constants
module = sys.modules[__name__]
for key, value in config.__dict__.items():
    if key.isupper():
        setattr(module, key, value)

# Validate the configuration
validation_errors = config.validate()
if validation_errors:
    for error in validation_errors:
        print(f"CONFIG ERROR: {error}")
