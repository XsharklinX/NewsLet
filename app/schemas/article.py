from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ─── Source ────────────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    name: str
    source_type: str
    url: str

    @field_validator("source_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("rss", "newsapi", "scraper"):
            raise ValueError("source_type must be 'rss', 'newsapi', or 'scraper'")
        return v


class SourceOut(BaseModel):
    id: int
    name: str
    source_type: str
    url: str
    is_active: bool
    created_at: datetime
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_success_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ─── Summary ───────────────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    id: int
    summary_text: str
    model_used: str
    tokens_used: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Article ───────────────────────────────────────────────────────────────

class ArticleOut(BaseModel):
    id: int
    source_id: int
    title: str
    url: str
    original_text: Optional[str] = None
    full_text: Optional[str] = None
    category: Optional[str] = None
    relevance_score: Optional[int] = None
    sentiment: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime
    status: str
    summary: Optional[SummaryOut] = None
    source: Optional[SourceOut] = None
    model_config = {"from_attributes": True}


class ArticleStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("pending", "approved", "rejected"):
            raise ValueError("status must be pending, approved, or rejected")
        return v


class ArticleListOut(BaseModel):
    articles: list[ArticleOut]
    total: int
    page: int
    page_size: int


# ─── Keyword ───────────────────────────────────────────────────────────────

class KeywordCreate(BaseModel):
    keyword: str

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Keyword must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Keyword too long (max 100 chars)")
        return v.lower()


class KeywordOut(BaseModel):
    id: int
    keyword: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Digest Config ─────────────────────────────────────────────────────────

class DigestConfigUpdate(BaseModel):
    hour: Optional[int] = None
    count: Optional[int] = None
    min_score: Optional[int] = None
    categories: Optional[str] = None
    is_active: Optional[bool] = None


class DigestConfigOut(BaseModel):
    id: int
    hour: int
    count: int
    min_score: int
    categories: Optional[str] = None
    is_active: bool
    updated_at: datetime
    model_config = {"from_attributes": True}


# ─── Stats ─────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total_articles: int
    pending: int
    approved: int
    rejected: int
    sent: int
    total_sources: int
    total_keywords: int
    articles_with_summary: int
    articles_with_category: int
    avg_score: Optional[float] = None
    unread_notifications: int = 0


class ChartDailyPoint(BaseModel):
    day: str
    count: int


class ChartCategoryPoint(BaseModel):
    category: str
    count: int


class ChartOut(BaseModel):
    daily: list[ChartDailyPoint]
    categories: list[ChartCategoryPoint]
    days: int
    avg_score: Optional[float] = None


# ─── Heatmap ───────────────────────────────────────────────────────────────

class HeatmapHourPoint(BaseModel):
    hour: int
    count: int


class HeatmapDayPoint(BaseModel):
    day: int          # 0=Mon … 6=Sun
    day_name: str
    count: int


class HeatmapOut(BaseModel):
    hours: list[HeatmapHourPoint]
    days: list[HeatmapDayPoint]


# ─── Trending ──────────────────────────────────────────────────────────────

class TrendingTopic(BaseModel):
    word: str
    count: int


class TrendingOut(BaseModel):
    topics: list[TrendingTopic]
    window_hours: int


# ─── Notification ──────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Webhook ───────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: str = "fetch,keyword"
    secret: Optional[str] = None


class WebhookOut(BaseModel):
    id: int
    name: str
    url: str
    events: str
    is_active: bool
    last_fired_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Source Stats ──────────────────────────────────────────────────────────

class SourceStatsOut(BaseModel):
    source_id: int
    name: str
    total_articles: int
    avg_score: Optional[float] = None
    categories: dict[str, int]
    sentiments: dict[str, int]
