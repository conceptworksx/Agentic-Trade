import os
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

import config.settings as settings
from service.database import PDFDocument, PDFListItem, PDFContentResponse, IngestResponse


async def list_all_pdfs(db: AsyncSession) -> List[PDFListItem]:
    """List all ingested PDFs."""
    result = await db.execute(select(PDFDocument))
    pdfs = result.scalars().all()
    return [
        PDFListItem(
            pdf_name=pdf.pdf_name,
            total_pages=pdf.total_pages,
            created_at=pdf.created_at,
        )
        for pdf in pdfs
    ]


async def get_pdf_content(pdf_name: str, db: AsyncSession) -> PDFContentResponse:
    """Fetch PDF text from DB and return raw content."""
    # Fetch PDF from DB
    result = await db.execute(
        select(PDFDocument).where(PDFDocument.pdf_name == pdf_name)
    )
    pdf = result.scalar_one_or_none()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    return PDFContentResponse(
        pdf_name=pdf.pdf_name,
        content=pdf.content,
        total_pages=pdf.total_pages,
    )



async def ingest_pdf(pdf_name: str, db: AsyncSession) -> IngestResponse:
    """Trigger ingestion of a specific PDF by name."""
    pdf_path = os.path.join(settings.PDF_FOLDER, pdf_name)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Format the name: remove .pdf, lower case, replace spaces and dashes with underscores
    base_name = pdf_name
    if base_name.lower().endswith(".pdf"):
        base_name = base_name[:-4]
    
    formatted_name = base_name.lower().replace("-", "_").replace(" ", "_")

    # Check if already ingested using formatted name
    result = await db.execute(
        select(PDFDocument).where(PDFDocument.pdf_name == formatted_name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="PDF already ingested")

    # Extract text from PDF
    try:
        content, total_pages = extract_text_from_pdf(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")

    # Save to DB
    pdf_doc = PDFDocument(
        pdf_name=formatted_name, total_pages=total_pages, content=content, file_path=pdf_path
    )
    db.add(pdf_doc)
    await db.commit()
    await db.refresh(pdf_doc)

    return IngestResponse(
        message="PDF ingested successfully",
        pdf_name=formatted_name,
        total_pages=total_pages,
        file_path=pdf_path,
    )


def extract_text_from_pdf(pdf_path: str) -> tuple[str, int]:
    """Extract text from PDF file. Returns (content, total_pages)."""
    # For now, mock implementation. In real, use PyPDF2 or similar.
    # Assume we need to add pypdf to dependencies.
    try:
        from pypdf import PdfReader
    except ImportError:
        raise Exception("PyPDF2 or pypdf not installed")

    reader = PdfReader(pdf_path)
    content = ""
    for page in reader.pages:
        content += page.extract_text() + "\n"
    return content.strip(), len(reader.pages)
