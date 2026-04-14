from pydantic_settings import BaseSettings


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
    telegram_chat_id: str = ""

    # Database
    database_url: str = "sqlite:///./newsbot.db"

    # Scheduler
    fetch_interval_minutes: int = 30
    digest_hour: int = 8

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
