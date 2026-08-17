import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.redis import redis_client
from app.db.database import Base, get_db


TEST_DB = "test.db"


# ============================================================
# Async DB - FastAPI
# ============================================================

ASYNC_TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB}"

async_test_engine = create_async_engine(
    ASYNC_TEST_DATABASE_URL,
    echo=False,
)

AsyncTestingSessionLocal = sessionmaker(
    async_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# Sync DB - Celery
# ============================================================

SYNC_TEST_DATABASE_URL = f"sqlite:///{TEST_DB}"

sync_test_engine = create_engine(
    SYNC_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    bind=sync_test_engine,
    autocommit=False,
    autoflush=False,
)


# ============================================================
# Database setup
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_database():

    Base.metadata.create_all(
        bind=sync_test_engine
    )

    yield

    Base.metadata.drop_all(
        bind=sync_test_engine
    )


# ============================================================
# Sync DB
# ============================================================

@pytest.fixture
def sync_db():

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================
# FastAPI client
# ============================================================

# @pytest.fixture
# def test_client():

#     async def override_get_db():

#         async with AsyncTestingSessionLocal() as session:
#             yield session

#     app.dependency_overrides[get_db] = override_get_db

#     client = TestClient(app)

#     yield client

#     app.dependency_overrides.clear()


@pytest.fixture
def test_client():

    async def override_get_db():

        async with AsyncTestingSessionLocal() as session:

            print(">>> API OVERRIDE CALLED")

            yield session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()

# ============================================================
# Redis
# ============================================================

@pytest.fixture(autouse=True)
def clean_redis():

    redis_client.flushdb()

    yield

    redis_client.flushdb()