import json
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.database import AsyncSessionLocal as SessionLocal
from app.db.models import Batch, Document, Finding
from app.workers.celery import celery_app


def mock_extraction(variables):
    """
    Mock extraction API.

    Given a list of variables, return a randomly generated
    value for each variable.
    """

    result = {}

    for variable in variables:
        if variable == "effective_date":
            result[variable] = random_date()

        elif variable == "expiry_date":
            result[variable] = random_date()

        elif variable == "governing_law":
            result[variable] = random.choice([
                "State of Delaware",
                "State of New York",
                "State of California",
                "State of Texas",
            ])

        elif variable == "termination_clause":
            result[variable] = random.choice([
                "30 days written notice",
                "60 days written notice",
                "90 days written notice",
            ])

        elif variable == "monthly_rent":
            result[variable] = f"INR {random.randint(20000, 100000):,}"

        elif variable == "security_deposit":
            result[variable] = f"INR {random.randint(50000, 300000):,}"

        elif variable == "maintenance_charges":
            result[variable] = f"INR {random.randint(1000, 10000):,}"

        elif variable == "notice_period":
            result[variable] = f"{random.choice([30, 60, 90])} days"

        else:
            result[variable] = f"mock-value-{random.randint(1000, 9999)}"

    return result


def random_date():
    start = datetime.now()
    random_days = random.randint(0, 1000)

    return (
        start + timedelta(days=random_days)
    ).strftime("%Y-%m-%d")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_document(self, document_id: int):
    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            return

        # Prevent accidentally processing an already completed document
        if document.status == "COMPLETED":
            return

        document.status = "PROCESSING"
        db.commit()

        batch = (
            db.query(Batch)
            .filter(Batch.id == document.batch_id)
            .first()
        )

        if not batch:
            raise ValueError(
                f"Batch {document.batch_id} not found"
            )

        variables = json.loads(batch.variables)

        # Mock external extraction API
        extracted_values = mock_extraction(variables)

        for variable, value in extracted_values.items():

            finding = Finding(
                document_id=document.id,
                variable=variable,
                value=value,
                status="PENDING_REVIEW",
            )

            db.add(finding)

        document.status = "COMPLETED"
        
        document.processed_at = datetime.utcnow()

        db.commit()

    except Exception as exc:
        db.rollback()

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if document:
            document.status = "FAILED"
            document.error_message = str(exc)
            db.commit()

        raise

    finally:
        db.close()