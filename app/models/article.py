from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

VALID_CATEGORIES = [
    "Política", "Economía", "Tecnología", "Deportes",
    "Internacional", "Entretenimiento", "Salud", "Ciencia"
]


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # rss | newsapi | scraper
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Health monitoring
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    articles: Mapped[list["Article"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (Index("ix_articles_url_hash", "url_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)        # scraped full article
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)    # AI-assigned category
    relevance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)   # AI score 1-10
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)     # positive/neutral/negative
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected/sent

    # Enrichment tracking
    enrich_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Thumbnail
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Topic clustering
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # User feedback (-1 = dislike, 0 = none, 1 = like)
    feedback: Mapped[int] = mapped_column(Integer, default=0)

    # Recurring topic flag
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    source: Mapped["Source"] = relationship(back_populates="articles")
    summary: Mapped["Summary | None"] = relationship(back_populates="article", uselist=False, cascade="all, delete-orphan")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id"), unique=True, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured summary fields (populated for new articles)
    key_point: Mapped[str | None] = mapped_column(Text, nullable=True)    # punto clave
    context_note: Mapped[str | None] = mapped_column(Text, nullable=True) # contexto
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)       # impacto
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="summary")


class Subscriber(Base):
    """Public Telegram subscribers who opted in via /suscribir."""
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
