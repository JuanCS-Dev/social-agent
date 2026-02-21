import asyncio
from src.agent.loop import autonomy_loop
from src.core.logger import log
from src.ingestion.app import app as fastapi_app


async def run_loop() -> None:
    """Background task running the OODA core."""
    await autonomy_loop.run()


@fastapi_app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(run_loop())
    log.info("App Startup: Webhooks API + Autonomy Loop Initialized.")


@fastapi_app.on_event("shutdown")
async def shutdown_event() -> None:
    autonomy_loop.running = False
    log.info("App Shutdown: Gracefully stopping.")
