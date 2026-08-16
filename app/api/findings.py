from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Finding


router = APIRouter(
    prefix="/findings",
    tags=["findings"],
)


class FindingReviewRequest(BaseModel):
    status: str


@router.patch("/{finding_id}")
async def review_finding(
    finding_id: int,
    payload: FindingReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------
    # Validate status
    # --------------------------------------------------

    if payload.status not in {"ACCEPTED", "REJECTED"}:
        raise HTTPException(
            status_code=400,
            detail="status must be ACCEPTED or REJECTED",
        )

    # --------------------------------------------------
    # Find finding
    # --------------------------------------------------

    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id
        )
    )

    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=404,
            detail="Finding not found",
        )

    # --------------------------------------------------
    # Update finding
    # --------------------------------------------------

    finding.status = payload.status

    await db.commit()
    await db.refresh(finding)

    return {
        "finding_id": finding.id,
        "document_id": finding.document_id,
        "variable": finding.variable,
        "value": finding.value,
        "status": finding.status,
    }