from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.db.database import Base, engine
from app.db.database import Base, engine
from app.api.batches import router as batches_router
from app.api.documents import router as documents_router
from app.api.findings import router as findings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(
    title="Bulk Doc Reader",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(batches_router)
app.include_router(documents_router)
app.include_router(findings_router)

# @app.get("/")
# async def health():
#     return {"status": "healthy"}
