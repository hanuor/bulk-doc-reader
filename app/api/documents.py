from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, Finding


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.get("/{document_id}/findings")
async def get_document_findings(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------
    # Get document
    # --------------------------------------------------

    result = await db.execute(
        select(Document).where(
            Document.id == document_id
        )
    )

    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # --------------------------------------------------
    # Get findings
    # --------------------------------------------------

    result = await db.execute(
        select(Finding)
        .where(Finding.document_id == document_id)
        .order_by(Finding.id)
    )

    findings = result.scalars().all()

    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "findings": [
            {
                "finding_id": finding.id,
                "variable": finding.variable,
                "value": finding.value,
                "status": finding.status,
            }
            for finding in findings
        ],
    }