"""
PDF API
Routes:
  GET  /list/all             → List all ingested PDFs
  GET  /{pdf_name}           → Fetch text from DB, send to LLM, return analysis
  POST /ingest/{pdf_name}    → Trigger ingestion of a specific PDF by name
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from service.database import get_db, PDFListItem, PDFContentResponse, IngestResponse
from service.pdf_service import list_all_pdfs, get_pdf_content, ingest_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.get("/list/all", response_model=List[PDFListItem])
async def list_pdfs(db: AsyncSession = Depends(get_db)):
    """List all ingested PDFs."""
    return await list_all_pdfs(db)


@router.get("/{pdf_name}", response_model=PDFContentResponse)
async def get_pdf(pdf_name: str, db: AsyncSession = Depends(get_db)):
    """Fetch raw text content from DB for a PDF."""
    return await get_pdf_content(pdf_name, db)


@router.post("/ingest/{pdf_name}", response_model=IngestResponse)
async def ingest_pdf_endpoint(pdf_name: str, db: AsyncSession = Depends(get_db)):
    """Trigger ingestion of a specific PDF by name."""
    return await ingest_pdf(pdf_name, db)
