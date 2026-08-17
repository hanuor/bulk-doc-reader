# Future Scopes

The current implementation is intentionally designed as an **MVP**, but its core components can be extended to support the following requirements.

## Real Document Extraction / OCR Providers

The mocked extraction function can be replaced with production-grade technologies such as **NLP parsing, SLMs/LLMs, or OCR providers** without requiring changes to the existing batch-processing workflow.

## Editing Extracted Findings

The findings API can be extended to allow reviewers to modify an extracted value before accepting it. The finding would retain its existing status while storing the updated value.

## Audit History

Introduce a `finding_audit` table to record every change to a finding, including:

- Finding ID
- Previous value and status
- New value and status
- Reviewer
- Timestamp

> **Important:** Since audit history can be a core requirement, using a relational SQL database schema is preferable to a NoSQL approach. A relational model provides strong consistency, structured relationships, and reliable auditability.

## Multiple Reviewers and User Roles

Introduce an IAM table in the database to manage users, roles, and permissions. **Redis** can additionally be used to cache authentication and authorization information for fast access at the API layer.

## Persistent Object Storage

Move documents from the local filesystem to persistent object storage such as **Amazon S3**.

The database can store the corresponding presigned URLs, allowing documents to be accessed independently of the application server. This decouples document storage from application-server infrastructure and provides a more scalable and secure architecture.

## Higher Processing Volumes

For higher processing volumes:

- Migrate from SQLite to **PostgreSQL**.
- Scale the **Celery worker pool horizontally**.
- Process batch and document records independently.
- Distribute document-processing tasks across multiple workers.

This allows large batches to be processed concurrently without requiring a single worker to handle the entire batch.

## Distributed Workers

The existing **Redis/Celery** architecture already provides a natural foundation for distributed processing.

Additional workers can consume tasks from the queue, with separate queues introduced for:

- Different document types
- Processing priorities
- Resource-intensive workloads

For particularly long-running asynchronous workloads, serverless workers such as **AWS Lambda**, or other dedicated worker infrastructure, can also be introduced where appropriate.

## Additional Document Formats and Extraction Rules

Introduce a dedicated **document-processing layer** responsible for format-specific handling such as:

- PDF
- DOCX
- TXT
- Other supported document formats

An **extraction-rule abstraction** can then be introduced independently of document parsing.

This separation keeps **format parsing, extraction logic, and batch orchestration** decoupled, making it easier to add new document formats and extraction rules without modifying the core batch-processing workflow.