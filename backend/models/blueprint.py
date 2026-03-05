"""
BlueprintRecord ORM model and Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base


# ── SQLAlchemy ORM Model ─────────────────────────────────────────────

class BlueprintRecord(Base):
    __tablename__ = "blueprint_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)

    # Extracted fields from LLM
    total_area = Column(String(100), nullable=True)
    overall_width = Column(String(100), nullable=True)
    overall_height = Column(String(100), nullable=True)
    floors = Column(Integer, nullable=True)
    floor_height = Column(String(100), nullable=True)
    seating_capacity = Column(Integer, nullable=True)
    number_of_exits = Column(Integer, nullable=True)
    number_of_staircases = Column(Integer, nullable=True)
    kitchen_present = Column(Boolean, nullable=True)

    # Geolocation fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    formatted_address = Column(String(500), nullable=True)
    locality = Column(String(200), nullable=True)
    administrative_area = Column(String(200), nullable=True)
    zone_detected = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Schemas ──────────────────────────────────────────────────

class BlueprintResponse(BaseModel):
    id: int
    filename: Optional[str] = None
    total_area: Optional[str] = None
    overall_width: Optional[str] = None
    overall_height: Optional[str] = None
    floors: Optional[int] = None
    floor_height: Optional[str] = None
    seating_capacity: Optional[int] = None
    number_of_exits: Optional[int] = None
    number_of_staircases: Optional[int] = None
    kitchen_present: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    locality: Optional[str] = None
    administrative_area: Optional[str] = None
    zone_detected: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    blueprint_id: Optional[int] = None


class LocationResponse(BaseModel):
    formatted_address: str
    locality: Optional[str] = None
    administrative_area: Optional[str] = None
    zone_detected: Optional[str] = None
    disclaimer: str


class LifecycleRequest(BaseModel):
    blueprint_id: int
    recipient_email: str
    language: str = "hi-IN"
