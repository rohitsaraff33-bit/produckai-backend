"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Mode
    demo_mode: bool = Field(default=True, description="Run in demo mode with sample data")

    # Database
    database_url: str = Field(
        default="postgresql://produckai:produckai_dev_password@localhost:5432/produckai",
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")

    # JWT
    jwt_secret: str = Field(
        default="your-secret-key-change-in-production", description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(
        default=24, description="JWT expiration in hours"
    )

    # Embeddings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformers model name",
    )
    embedding_dimension: int = Field(
        default=384, description="Embedding vector dimension"
    )
    embedding_batch_size: int = Field(
        default=32, description="Batch size for embedding generation"
    )

    # Clustering
    hdbscan_min_cluster_size: int = Field(
        default=5, description="Minimum feedback items per cluster"
    )
    hdbscan_min_samples: int = Field(
        default=3, description="Minimum samples for core points"
    )
    clustering_min_feedback_count: int = Field(
        default=20, description="Minimum feedback count to run clustering"
    )

    # Scoring weights
    score_weight_frequency: float = Field(default=0.35, description="Weight for frequency")
    score_weight_acv: float = Field(default=0.30, description="Weight for ACV")
    score_weight_sentiment: float = Field(default=0.10, description="Weight for sentiment")
    score_weight_segment: float = Field(default=0.15, description="Weight for segment")
    score_weight_trend: float = Field(default=0.10, description="Weight for trend")
    score_weight_duplicate: float = Field(default=0.10, description="Weight for duplicate penalty")

    # Segment priorities
    segment_priority_ent: float = Field(default=1.0, description="Enterprise segment priority")
    segment_priority_mm: float = Field(default=0.7, description="Mid-market segment priority")
    segment_priority_smb: float = Field(default=0.5, description="SMB segment priority")

    # Slack
    slack_bot_token: str = Field(default="", description="Slack bot token")
    slack_app_token: str = Field(default="", description="Slack app token")
    slack_channels: str = Field(
        default="general,product-feedback,support",
        description="Comma-separated channel names",
    )

    # Jira
    jira_url: str = Field(
        default="https://your-domain.atlassian.net", description="Jira base URL"
    )
    jira_email: str = Field(default="", description="Jira user email")
    jira_api_token: str = Field(default="", description="Jira API token")
    jira_project_keys: str = Field(
        default="PROD,ENG", description="Comma-separated project keys"
    )
    jira_jql: str = Field(
        default="project in (PROD,ENG) AND created >= -90d",
        description="JQL query for fetching issues",
    )

    # Linear
    linear_api_key: str = Field(default="", description="Linear API key")
    linear_team_id: str = Field(default="", description="Linear team ID")

    # OpenAI (optional)
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")

    # OAuth
    app_secret: str = Field(default="", description="APP_SECRET for token encryption (base64-encoded 32 bytes)")
    oauth_redirect_base_url: str = Field(default="http://localhost:8000", description="OAuth redirect base URL")
    google_client_id: str = Field(default="", description="Google OAuth client ID")
    google_client_secret: str = Field(default="", description="Google OAuth client secret")
    zoom_client_id: str = Field(default="", description="Zoom OAuth client ID")
    zoom_client_secret: str = Field(default="", description="Zoom OAuth client secret")

    # Observability
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_exporter_otlp_endpoint: str = Field(
        default="", description="OTLP endpoint URL"
    )

    @property
    def score_weights(self) -> dict[str, float]:
        """Return scoring weights as a dictionary."""
        return {
            "frequency": self.score_weight_frequency,
            "acv": self.score_weight_acv,
            "sentiment": self.score_weight_sentiment,
            "segment": self.score_weight_segment,
            "trend": self.score_weight_trend,
            "duplicate": self.score_weight_duplicate,
        }

    @property
    def segment_priorities(self) -> dict[str, float]:
        """Return segment priorities as a dictionary."""
        return {
            "ENT": self.segment_priority_ent,
            "MM": self.segment_priority_mm,
            "SMB": self.segment_priority_smb,
        }

    @property
    def encryption_key(self) -> str:
        """Get encryption key from app_secret."""
        if not self.app_secret:
            # Generate a temporary key for development if not set
            import base64
            import os
            return base64.b64encode(os.urandom(32)).decode("utf-8")
        return self.app_secret


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
