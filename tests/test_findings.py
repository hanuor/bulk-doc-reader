from app.db.models import Batch, Document, Finding


def test_review_finding(test_client, sync_db):

    # Create batch
    batch = Batch(
        status="PROCESSING",
        variables='["effective_date"]',
        total_documents=1,
    )

    sync_db.add(batch)
    sync_db.commit()
    sync_db.refresh(batch)

    # Create document
    document = Document(
        batch_id=batch.id,
        filename="contract.txt",
        storage_path="/tmp/contract.txt",
        status="COMPLETED",
    )

    sync_db.add(document)
    sync_db.commit()
    sync_db.refresh(document)

    # Create finding
    finding = Finding(
        document_id=document.id,
        variable="effective_date",
        value="2027-01-01",
        status="PENDING_REVIEW",
    )

    sync_db.add(finding)
    sync_db.commit()
    sync_db.refresh(finding)

    # Review finding
    response = test_client.patch(
        f"/findings/{finding.id}",
        json={
            "status": "ACCEPTED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["finding_id"] == finding.id
    assert data["status"] == "ACCEPTED"


def test_review_finding_invalid_status(test_client, sync_db):

    batch = Batch(
        status="PROCESSING",
        variables='["effective_date"]',
        total_documents=1,
    )

    sync_db.add(batch)
    sync_db.commit()
    sync_db.refresh(batch)

    document = Document(
        batch_id=batch.id,
        filename="contract.txt",
        storage_path="/tmp/contract.txt",
        status="COMPLETED",
    )

    sync_db.add(document)
    sync_db.commit()
    sync_db.refresh(document)

    finding = Finding(
        document_id=document.id,
        variable="effective_date",
        value="2027-01-01",
        status="PENDING_REVIEW",
    )

    sync_db.add(finding)
    sync_db.commit()
    sync_db.refresh(finding)

    print("TEST DB FINDING ID:", finding.id)

    check = sync_db.get(Finding, finding.id)

    print("SYNC DB FINDING:", check)
    response = test_client.patch(
        f"/findings/{finding.id}",
        json={
            "status": "TESTING",
        },
    )

    assert response.status_code == 400