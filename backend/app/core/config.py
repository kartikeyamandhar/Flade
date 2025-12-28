"""
Configuration module for Manual Knowledge Graph application.
Loads and validates environment variables using Pydantic settings.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    APP_NAME: str = "Manual Knowledge Graph"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"
    
    # File Upload
    UPLOAD_DIR: str = "../data/uploads"
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: str = ".pdf"  # Changed to string, will convert to list
    
    # Processing
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS_PER_BATCH: int = 10
    PROCESSING_WORKERS: int = 3
    
    # Cost Controls
    MAX_PAGES_PER_DOCUMENT: int = 50  # Limit for learning project
    ENABLE_WEB_SEARCH: bool = False
    USE_CHEAPER_MODEL: bool = True  # Use gpt-3.5-turbo instead of gpt-4
    
    @field_validator('ALLOWED_EXTENSIONS')
    @classmethod
    def parse_extensions(cls, v):
        """Convert ALLOWED_EXTENSIONS to list if it's a string."""
        if isinstance(v, str):
            # Split by comma if multiple, otherwise single item list
            return [ext.strip() for ext in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Create cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Global settings instance
settings = get_settings()