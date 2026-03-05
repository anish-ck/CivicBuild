"""
CallLog ORM model for storing Twilio voice call records.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    blueprint_id = Column(Integer, nullable=True)
    phone_number = Column(String(20), nullable=False)
    call_sid = Column(String(100), nullable=True)
    status = Column(String(50), default="initiated")
    summary_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Schemas ──────────────────────────────────────────────────

class CallLogResponse(BaseModel):
    id: int
    blueprint_id: Optional[int] = None
    phone_number: str
    call_sid: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
