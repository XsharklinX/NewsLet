from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    conditions: Mapped[str] = mapped_column(Text, default="[]")   # JSON list of condition objects
    actions: Mapped[str] = mapped_column(Text, default="[]")      # JSON list of action objects
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=10)    # lower = evaluated first
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
