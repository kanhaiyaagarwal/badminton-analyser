"""Application configuration settings."""

from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App settings
    app_name: str = "Badminton Analyzer API"
    debug: bool = False

    # JWT settings
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database (SQLite for dev, MySQL/PostgreSQL for production)
    database_url: str = "sqlite:///./badminton_analyzer.db"

    # File storage
    upload_dir: str = "uploads"
    output_dir: str = "analysis_output"

    # Upload limits
    max_upload_size_mb: int = 500

    # Analysis settings
    max_concurrent_jobs: int = 2

    # CORS - comma-separated string from env
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # S3 Storage (for AWS deployment)
    use_s3: bool = False
    s3_bucket: str = ""
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    cloudfront_domain: str = ""
    s3_upload_prefix: str = "uploads"
    s3_output_prefix: str = "analysis_output"

    # Redis (for WebSocket scaling)
    redis_url: Optional[str] = None

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")

    @property
    def base_dir(self) -> Path:
        """Get base directory."""
        return Path(__file__).parent.parent

    @property
    def upload_path(self) -> Path:
        """Get upload directory path."""
        return self.base_dir / self.upload_dir

    @property
    def output_path(self) -> Path:
        """Get output directory path."""
        return self.base_dir / self.output_dir

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_video_extensions(self) -> set:
        """Allowed video file extensions."""
        return {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
