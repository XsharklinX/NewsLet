from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DigestConfig(Base):
    __tablename__ = "digest_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hour: Mapped[int] = mapped_column(Integer, default=8)           # 0-23
    count: Mapped[int] = mapped_column(Integer, default=10)         # articles per digest
    min_score: Mapped[int] = mapped_column(Integer, default=0)      # min relevance score
    categories: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
