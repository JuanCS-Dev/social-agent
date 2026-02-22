from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from typing import Optional
from src.core.logger import log, log_event
from src.core.config import settings
from src.memory.storage import storage
import uuid
import hmac
import hashlib

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_meta_signature(payload_body: bytes, signature_header: str) -> bool:
    """Valida se o payload veio do Meta usando o app_secret."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = hmac.new(settings.meta_app_secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()

    received_sig = signature_header.split("sha256=")[1]
    return hmac.compare_digest(expected_sig, received_sig)


@router.post("/reddit")
async def reddit_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    MVP: Reddit API uses polling mostly, but exposing an endpoint
    if needed for specific external triggers or apps.
    """
    payload = await request.json()
    event_id = f"evt_rdt_{uuid.uuid4().hex[:10]}"

    background_tasks.add_task(storage.save_event, event_id, "reddit_webhook", payload)
    log_event("reddit_webhook_received", {"event_id": event_id})
    return {"status": "accepted", "event_id": event_id}


@router.post("/x")
async def x_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_social_agent_token: Optional[str] = Header(None),
):
    expected_token = settings.x_webhook_token.strip()
    if expected_token and x_social_agent_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid X webhook token")

    payload = await request.json()
    event_id = f"evt_x_{uuid.uuid4().hex[:10]}"

    background_tasks.add_task(storage.save_event, event_id, "x_webhook", payload)
    log_event("x_webhook_received", {"event_id": event_id})
    return {"status": "accepted", "event_id": event_id}


@router.post("/meta")
async def meta_webhook(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: Optional[str] = Header(None)):
    """
    Receives events from Facebook Pages / Instagram Graph API.
    Validates X-Hub-Signature-256 natively.
    """
    body = await request.body()

    # Validation step based on Meta Docs
    if settings.environment == "production" and not verify_meta_signature(body, x_hub_signature_256 or ""):
        log.warning("Meta Webhook rejected: Invalid Signature.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    event_id = f"evt_mta_{uuid.uuid4().hex[:10]}"

    background_tasks.add_task(storage.save_event, event_id, "meta_webhook", payload)
    log_event("meta_webhook_received", {"event_id": event_id})
    return {"status": "accepted", "event_id": event_id}


@router.get("/meta")
async def meta_webhook_verify(request: Request):
    """
    Handles Meta webhook verification challenge.
    GET ?hub.mode=subscribe&hub.challenge=1158201444&hub.verify_token=meutoken
    """
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and verify_token and challenge:
        if mode == "subscribe" and verify_token == settings.meta_verify_token:
            log.info("WEBHOOK_VERIFIED")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")

    raise HTTPException(status_code=400, detail="Missing parameters")
