import json

from app.db.models import Batch, Document, Finding
from app.workers.tb import process_document
from tests.conftest import TestingSessionLocal


def test_process_document(sync_db, monkeypatch):

    batch = Batch(
        status="PROCESSING",
        variables=json.dumps([
            "effective_date",
            "expiry_date",
        ]),
        total_documents=1,
    )

    sync_db.add(batch)
    sync_db.commit()
    sync_db.refresh(batch)

    document = Document(
        batch_id=batch.id,
        filename="contract.txt",
        storage_path="/tmp/contract.txt",
        status="PENDING",
    )

    sync_db.add(document)
    sync_db.commit()
    sync_db.refresh(document)

    def mock_extraction(variables):
        return {
            "effective_date": "2027-01-01",
            "expiry_date": "2028-01-01",
        }

    monkeypatch.setattr(
        "app.workers.tb.SessionLocal",
        TestingSessionLocal,
    )

    monkeypatch.setattr(
        "app.workers.tb.mock_extraction",
        mock_extraction,
    )

    process_document.apply(
        args=[document.id],
    )

    sync_db.refresh(document)

    assert document.status == "COMPLETED"

    findings = (
        sync_db.query(Finding)
        .filter(Finding.document_id == document.id)
        .all()
    )

    assert len(findings) == 2