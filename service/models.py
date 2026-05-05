from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import Base


# ── Database Models ────────────────────────────────────────────────────────────

class PDFDocument(Base):
    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, index=True)
    pdf_name = Column(String, unique=True, index=True, nullable=False)
    total_pages = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)  # Extracted text content
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

# ── Ingestion
class IngestResponse(BaseModel):
    message: str
    pdf_name: str
    total_pages: int
    file_path: str


# ── Main API response
class PDFContentResponse(BaseModel):
    pdf_name: str
    content: str
    total_pages: int


class SectorSelection(BaseModel):
    sector_name: str
    confidence: float
    reason: str


# ── List endpoint
class PDFListItem(BaseModel):
    pdf_name: str
    total_pages: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
