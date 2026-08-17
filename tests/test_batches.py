from app.db.models import Batch


def test_get_batch_not_found(test_client):
    response = test_client.get("/batches/999999")

    assert response.status_code == 404


def test_get_batch(test_client, sync_db):
    batch = Batch(
        status="PROCESSING",
        variables='["effective_date"]',
        total_documents=2,
    )

    sync_db.add(batch)
    sync_db.commit()
    sync_db.refresh(batch)

    response = test_client.get(
        f"/batches/{batch.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["batch_id"] == batch.id
    assert data["total_documents"] == 0
    assert data["progress"] == 0