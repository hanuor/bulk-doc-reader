# Contract Document Processing API

FastAPI application for bulk contract-document processing.

The application accepts a ZIP containing up to 1,000 documents and a JSON array of variables to extract. Documents are processed asynchronously with Celery using a mocked extraction service. Findings are then available for human review.

## Prerequisites

- Python 3.8.10+
- Redis
- `pip`

## 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start Redis (macOS/Homebrew):

```bash
brew services start redis
```

Or:

```bash
redis-server
```

## 2. Start FastAPI

In terminal 1:

```bash
uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 3. Start Celery

In terminal 2:

```bash
celery -A app.workers.celery worker --loglevel=info
```

Use the Celery application path configured in the project if it differs.

Wait until the worker reports:

```text
celery@... ready.
```

Keep this terminal running while testing.

## 4. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/batches` | Upload ZIP and create a batch |
| GET | `/batches/{batch_id}` | Track batch progress |
| GET | `/batches/{batch_id}/documents` | List batch documents |
| GET | `/documents/{document_id}/findings` | View extracted findings |
| PATCH | `/findings/{finding_id}` | Accept/reject a finding |

## 5. Create a batch

Open `/docs` and use:

```text
POST /batches
```

Upload a ZIP containing sample contract documents.

For `variables`, provide a JSON array, for example:

```json
[
  "effective_date",
  "expiry_date",
  "governing_law",
  "termination_clause"
]
```

For house-rent agreements:

```json
[
  "security_deposit",
  "monthly_rent",
  "maintenance_charges",
  "notice_period"
]
```

A successful response should look similar to:

```json
{
  "batch_id": 1,
  "status": "PROCESSING",
  "total_documents": 3,
  "variables": [
    "effective_date",
    "expiry_date",
    "governing_law",
    "termination_clause"
  ]
}
```

Save the `batch_id`.

### ZIP constraints

- Maximum 1,000 documents
- Maximum 15 MB per document
- ZIP format required
- ZIP path traversal is prevented

## 6. Watch background processing

In the Celery terminal, you should see one task per document:

```text
Task app.workers.tb.process_document[...] received
Task app.workers.tb.process_document[...] succeeded
```

The worker calls the mocked extraction service, which generates a value for every requested variable.

## 7. Track the batch

Call:

```text
GET /batches/{batch_id}
```

For example:

```text
GET /batches/1
```

During processing you may see:

```json
{
  "batch_id": 1,
  "status": "PROCESSING",
  "total_documents": 3,
  "processed_documents": 1,
  "successful_documents": 1,
  "failed_documents": 0,
  "processing_documents": 2,
  "pending_documents": 0,
  "progress": 33.33
}
```

After completion:

```json
{
  "batch_id": 1,
  "status": "COMPLETED",
  "total_documents": 3,
  "processed_documents": 3,
  "successful_documents": 3,
  "failed_documents": 0,
  "processing_documents": 0,
  "pending_documents": 0,
  "progress": 100.0
}
```

## 8. View batch documents

Call:

```text
GET /batches/{batch_id}/documents
```

This shows each document and its processing status.

## 9. View extracted findings

Choose a completed document ID and call:

```text
GET /documents/{document_id}/findings
```

Example:

```json
{
  "document_id": 1,
  "findings": [
    {
      "id": 1,
      "variable": "effective_date",
      "value": "2027-01-01",
      "status": "PENDING_REVIEW"
    },
    {
      "id": 2,
      "variable": "expiry_date",
      "value": "2028-01-01",
      "status": "PENDING_REVIEW"
    }
  ]
}
```

## 10. Review findings

Accept:

```text
PATCH /findings/{finding_id}
```

```json
{
  "status": "ACCEPTED"
}
```

Reject:

```json
{
  "status": "REJECTED"
}
```

Example response:

```json
{
  "finding_id": 1,
  "document_id": 1,
  "variable": "effective_date",
  "value": "2027-01-01",
  "status": "ACCEPTED"
}
```

Only `ACCEPTED` and `REJECTED` are valid review statuses.

## 11. Run automated tests

From the project root:

```bash
pytest -v
```

The current suite covers:

- Batch not found
- Batch retrieval/progress calculation
- Finding acceptance
- Invalid finding status
- Celery document processing and finding creation

Expected result:

```text
5 passed
```

## 12. Recommended end-to-end test

Run the following sequence:

```text
Start Redis
    ↓
Start FastAPI
    ↓
Start Celery worker
    ↓
POST /batches
    ↓
Upload ZIP + variables
    ↓
Observe Celery tasks
    ↓
GET /batches/{batch_id}
    ↓
GET /batches/{batch_id}/documents
    ↓
GET /documents/{document_id}/findings
    ↓
PATCH /findings/{finding_id}
    ↓
GET /documents/{document_id}/findings
    ↓
Verify ACCEPTED / REJECTED
```

## 13. Error cases to test

### Invalid file type

Upload a non-ZIP file.

Expected: `400`

### More than 1,000 documents

Upload a ZIP containing more than 1,000 documents.

Expected: `400`

### Document larger than 15 MB

Upload a ZIP containing a document larger than 15 MB.

Expected: `400`

### Invalid review status

```json
{
  "status": "TESTING"
}
```

Expected: `400`

### Missing batch

```text
GET /batches/999999
```

Expected: `404`

## 14. Current storage architecture

The current implementation intentionally keeps infrastructure simple:

- SQLite for persistence
- Redis as the Celery broker
- Local filesystem for uploaded documents
- Celery for asynchronous processing
- Mocked extraction service

FastAPI uses an asynchronous SQLAlchemy session, while Celery uses a synchronous SQLAlchemy session.

## 15. Future evolution

### PostgreSQL

SQLite can be replaced with PostgreSQL while retaining SQLAlchemy.

### Object storage

Local document storage can move to S3 or another object-storage provider.

### Real extraction/OCR

The mocked extraction implementation can be replaced by an abstraction such as:

```text
ExtractionService
    ├── MockExtractionProvider
    ├── OCRProvider
    └── LLMProvider
```

This keeps the worker independent of a specific vendor.

### Distributed workers

Celery workers can scale horizontally:

```text
Redis
 ├── Worker 1
 ├── Worker 2
 ├── Worker 3
 └── Worker N
```

### Audit history

Add an audit table recording finding changes, reviewer, timestamp, previous value/status, and new value/status.

### Multiple reviewers and roles

Introduce users, roles, authentication and authorization.

### Editing findings

Extend the review API to allow reviewers to edit extracted values before accepting them.

## MVP scope

The implementation covers:

- Bulk ZIP upload
- Up to 1,000 documents
- 15 MB per-document limit
- Asynchronous processing
- Mocked extraction
- Batch/document status tracking
- Human review
- SQLite persistence
- Automated tests
