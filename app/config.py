import os
from pydantic_settings import BaseSettings


def _default_db_url() -> str:
    """
    Resolve the best DB path for the current environment:
    - Fly.io: /app/data/newslet.db (persistent volume)
    - Local dev: ./newslet.db
    """
    fly_volume = "/app/data"
    if os.path.isdir(fly_volume):
        return f"sqlite:///{fly_volume}/newslet.db"
    return "sqlite:///./newslet.db"


class Settings(BaseSettings):
    # AI Provider: "groq" (free) or "openai"
    ai_provider: str = "groq"

    # Groq (FREE - https://console.groq.com)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenAI (fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # NewsAPI
    newsapi_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""          # owner / primary admin chat ID

    # Telegram admin IDs — comma-separated list of chat IDs that can use
    # admin commands. TELEGRAM_CHAT_ID is always included automatically.
    telegram_admin_ids: str = ""

    # Database — auto-resolves to /app/data/newslet.db on Fly.io
    database_url: str = ""

    def model_post_init(self, __context) -> None:
        # If DATABASE_URL wasn't set via env, use the default
        if not self.database_url:
            object.__setattr__(self, "database_url", _default_db_url())

    # Scheduler
    fetch_interval_minutes: int = 30
    digest_hour: int = 8

    # Timezone for display / digest scheduling (pytz name, e.g. "America/Argentina/Buenos_Aires")
    app_timezone: str = "America/Argentina/Buenos_Aires"

    # AI Enrichment
    relevance_threshold: int = 5       # min score (1-10) to auto-send to Telegram
    enrich_articles: bool = True        # enable category + score enrichment
    scrape_full_text: bool = True       # enable full article scraping before summary

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_file: str = "logs/newslet.log"
    log_max_bytes: int = 10_485_760    # 10 MB
    log_backup_count: int = 5

    # Panel security (optional PIN gate)
    panel_pin: str = ""

    # JWT Auth (set admin_password to enable login page)
    jwt_secret: str = "change-me-in-production-please"
    jwt_expire_minutes: int = 1440   # 24 h
    admin_password: str = ""          # empty = JWT auth disabled

    # Email digest via SMTP
    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""                 # comma-separated recipients

    # Source health
    source_max_failures: int = 5     # auto-disable after N consecutive failures

    # Backup — set to path of a writable directory to enable daily DB backups
    backup_dir: str = ""              # e.g. "/app/data/backups"

    # Service key — used by GitHub Actions to call protected API endpoints
    # Generate any random string: python -c "import secrets; print(secrets.token_hex(32))"
    service_key: str = ""

    # Telegram webhook mode (production) — set to your public HTTPS base URL
    # e.g. https://newslet-pro.onrender.com
    # Leave empty to use polling (local development)
    webhook_base_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_admin_ids(self) -> set[str]:
        """Return the full set of Telegram admin chat IDs."""
        ids: set[str] = set()
        if self.telegram_chat_id:
            ids.add(str(self.telegram_chat_id).strip())
        for raw in self.telegram_admin_ids.split(","):
            stripped = raw.strip()
            if stripped:
                ids.add(stripped)
        return ids


settings = Settings()
