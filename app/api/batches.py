import json
import os
import shutil
import tempfile
import zipfile
from fastapi import Query

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.database import get_db
from app.db.models import Batch, Document
from app.workers.tb import process_document

from fastapi import Depends, HTTPException
from sqlalchemy import select, func
from app.db.database import get_db
from app.db.models import Batch, Document, Finding


router = APIRouter(prefix="/batches", tags=["batches"])

MAX_DOCUMENTS = 1000
MAX_DOCUMENT_SIZE = 15 * 1024 * 1024


@router.post("")
async def create_batch(
    file: UploadFile = File(...),
    variables: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------
    # 1. Validate variables
    # --------------------------------------------------
    variables_list = [
        variable.strip()
        for variable in variables.split(",")
        if variable.strip()
    ]

    if not variables_list:
        raise HTTPException(
            status_code=400,
            detail="At least one variable must be provided",
        )

    # --------------------------------------------------
    # 2. Validate ZIP
    # --------------------------------------------------

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported",
        )

    # Store uploaded ZIP temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        shutil.copyfileobj(file.file, tmp)
        zip_path = tmp.name

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:

            members = [
                member
                for member in archive.infolist()
                if not member.is_dir()
            ]

            # --------------------------------------------------
            # 3. Validate document count
            # --------------------------------------------------

            if len(members) > MAX_DOCUMENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"ZIP cannot contain more than {MAX_DOCUMENTS} documents",
                )

            # --------------------------------------------------
            # 4. Validate individual document sizes
            # --------------------------------------------------
            document_ids = []
            for member in members:
                if member.file_size > MAX_DOCUMENT_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Document '{member.filename}' exceeds "
                            f"the 15 MB limit"
                        ),
                    )

            # --------------------------------------------------
            # 5. Create batch
            # --------------------------------------------------

            batch = Batch(
                status="PENDING",
                variables=json.dumps(variables_list),
                total_documents=len(members),
            )

            db.add(batch)
            await db.flush()

            # --------------------------------------------------
            # 6. Extract documents
            # --------------------------------------------------

            batch_directory = os.path.join(
                "storage",
                "batches",
                str(batch.id),
            )

            os.makedirs(batch_directory, exist_ok=True)

            for member in members:

                # Prevent ZIP path traversal
                filename = os.path.basename(member.filename)

                document_path = os.path.join(
                    batch_directory,
                    filename,
                )

                with archive.open(member) as source, open(
                    document_path,
                    "wb",
                ) as target:
                    shutil.copyfileobj(source, target)

                document = Document(
                    batch_id=batch.id,
                    filename=filename,
                    storage_path=document_path,
                    status="PENDING",
                )

                db.add(document)
                await db.flush()
                document_ids.append(document.id)

            await db.commit()

            # init batch processing via celery

            for document_id in document_ids:
                process_document.delay(document_id)
            batch.status = "PROCESSING"
            await db.commit()

            return {
                "batch_id": batch.id,
                "status": batch.status,
                "total_documents": batch.total_documents,
                "variables": variables_list,
            }

    finally:
        os.unlink(zip_path)

@router.get("/{batch_id}")
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------
    # Get batch
    # --------------------------------------------------

    result = await db.execute(
        select(Batch).where(Batch.id == batch_id)
    )

    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Batch not found",
        )

    # --------------------------------------------------
    # Get documents
    # --------------------------------------------------

    result = await db.execute(
        select(Document).where(
            Document.batch_id == batch_id
        )
    )

    documents = result.scalars().all()

    # --------------------------------------------------
    # Calculate statistics
    # --------------------------------------------------

    total = len(documents)

    completed = sum(
        1
        for document in documents
        if document.status == "COMPLETED"
    )

    failed = sum(
        1
        for document in documents
        if document.status == "FAILED"
    )

    processing = sum(
        1
        for document in documents
        if document.status == "PROCESSING"
    )

    pending = sum(
        1
        for document in documents
        if document.status == "PENDING"
    )

    processed = completed + failed

    # --------------------------------------------------
    # Determine batch status
    # --------------------------------------------------

    if total == 0:
        status = "PENDING"

    elif processed == total:
        if failed > 0:
            status = "COMPLETED_WITH_ERRORS"
        else:
            status = "COMPLETED"

    elif processing > 0 or completed > 0 or failed > 0:
        status = "PROCESSING"

    else:
        status = "PENDING"

    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    return {
        "batch_id": batch.id,
        "status": status,
        "total_documents": total,
        "processed_documents": processed,
        "successful_documents": completed,
        "failed_documents": failed,
        "processing_documents": processing,
        "pending_documents": pending,
        "progress": round(
            (processed / total) * 100,
            2,
        ) if total else 0,
        "created_at": batch.created_at,
        "completed_at": (
            batch.completed_at
            if status in (
                "COMPLETED",
                "COMPLETED_WITH_ERRORS",
            )
            else None
        ),
    }

@router.get("/{batch_id}/documents")
async def get_batch_documents(
    batch_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------------------------------
    # Check batch exists
    # --------------------------------------------------

    result = await db.execute(
        select(Batch).where(Batch.id == batch_id)
    )

    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Batch not found",
        )

    # --------------------------------------------------
    # Get documents
    # --------------------------------------------------
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Document)
        .where(Document.batch_id == batch_id)
        .order_by(Document.id)
        .offset(offset)
        .limit(page_size)
    )

    documents = result.scalars().all()

    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    return {
        "batch_id": batch_id,
        "total_documents": len(documents),
        "documents": [
            {
                "document_id": document.id,
                "filename": document.filename,
                "status": document.status,
                "error_message": document.error_message,
                "processed_at": document.processed_at,
            }
            for document in documents
        ],
    }