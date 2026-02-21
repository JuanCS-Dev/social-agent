import uvicorn
from src.app.server import fastapi_app
from src.core.logger import log

if __name__ == "__main__":
    log.info("Starting Byte Social Agent (Uvicorn)...")
    uvicorn.run("main:fastapi_app", host="0.0.0.0", port=8000, reload=True)
