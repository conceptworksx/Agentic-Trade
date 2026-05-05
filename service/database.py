from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

from config.settings import settings


# ── Engine & Base ─────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass


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

class IngestResponse(BaseModel):
    message: str
    pdf_name: str
    total_pages: int
    file_path: str

class PDFContentResponse(BaseModel):
    pdf_name: str
    content: str
    total_pages: int

class SectorSelection(BaseModel):
    sector_name: str
    confidence: float
    reason: str

class PDFListItem(BaseModel):
    pdf_name: str
    total_pages: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Dependency & Init ─────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """Dependency: yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
