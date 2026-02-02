"""Configuration management for urlinsta."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""

    FB_APP_ID: str = os.getenv("FB_APP_ID", "")
    FB_APP_SECRET: str = os.getenv("FB_APP_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv("OAUTH_REDIRECT_URI", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Facebook Graph API
    GRAPH_API_VERSION: str = "v21.0"
    GRAPH_API_BASE_URL: str = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 180  # Conservative limit (Instagram allows 200/hour)
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour in seconds

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        required = ["FB_APP_ID", "FB_APP_SECRET", "OAUTH_REDIRECT_URI", "SUPABASE_URL", "SUPABASE_KEY"]
        missing = [key for key in required if not getattr(cls, key)]
        return missing


config = Config()
