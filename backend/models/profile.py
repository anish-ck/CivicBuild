"""
BusinessProfile ORM model and Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base


# ── SQLAlchemy ORM Model ─────────────────────────────────────────────

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transcript = Column(Text, nullable=True)
    detected_language = Column(String(10), nullable=True)
    business_type = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    seating_capacity = Column(Integer, nullable=True)
    turnover = Column(Float, nullable=True)
    serves_food = Column(Boolean, nullable=True)
    serves_alcohol = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Schemas ──────────────────────────────────────────────────

class BusinessProfileResponse(BaseModel):
    id: int
    transcript: Optional[str] = None
    detected_language: Optional[str] = None
    business_type: Optional[str] = None
    city: Optional[str] = None
    seating_capacity: Optional[int] = None
    turnover: Optional[float] = None
    serves_food: Optional[bool] = None
    serves_alcohol: Optional[bool] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    question: str
    language: str = "en"
    city: str | None = None


class AskResponse(BaseModel):
    answer: str
    language: str


class LicenseSuggestion(BaseModel):
    license: str
    reason: str
