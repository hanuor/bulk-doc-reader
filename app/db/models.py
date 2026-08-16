from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Column,
    Text,
    func,
    UniqueConstraint,
)

from app.db.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=False),
                        default=func.now(), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=False), default=func.now(
    ), server_default=func.now(), onupdate=func.now())


class BatchStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FindingStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Batch(TimestampMixin, Base):
    __tablename__ = "batches"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        unique=True,
        index=True,
    )

    status = Column(String, nullable=False, default="PENDING")
    variables = Column(Text, nullable=False)
    total_documents = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    completed_at = Column(DateTime, nullable=True)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        unique=True,
        index=True,
    )

    batch_id = Column(
        Integer,
        ForeignKey("batches.id"),
        nullable=False,
        index=True,
    )

    filename = Column(String, nullable=False)
    storage_path = Column(Text, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="PENDING",
    )

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    processed_at = Column(DateTime, nullable=True)


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        unique=True,
        index=True,
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    variable = Column(String, nullable=False)
    value = Column(Text, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="PENDING_REVIEW",
    )

    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "variable",
            name="uq_document_variable",
        ),
    )
