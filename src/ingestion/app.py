from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.core.logger import log
from src.memory.storage import storage
from src.ingestion.routers import webhooks, ops


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Byte Social Agent Ingestion Service...")
    await storage.init_db()
    log.info("Ingestion Service Ready.")
    yield
    log.info("Shutting down Ingestion Service...")


app = FastAPI(title="Byte Social Agent Ingestion API", description="Webhook target and ingestion points for the autonomous social agent", version="1.0.0", lifespan=lifespan)

app.include_router(webhooks.router)
app.include_router(ops.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "byte-social-agent"}
