from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agent.intelligence import social_intelligence
from src.agent.profiles import profile_registry
from src.core.config import settings
from src.memory.storage import storage
from src.planner.scheduler import scheduler

router = APIRouter(prefix="/ops", tags=["ops"])


class OperatorTaskUpdate(BaseModel):
    status: str = "done"
    external_id: str = ""
    notes: str = ""


@router.get("/status")
async def ops_status():
    queue_stats = await storage.get_queue_stats()
    operator_queue_stats = await storage.get_operator_queue_stats()
    latest_reflection = await storage.get_latest_reflection()
    recent_signals = await storage.get_recent_signals(hours=24)
    growth_kpis = social_intelligence.estimate_growth_kpis(recent_signals)
    active_strategy = {}
    if isinstance(latest_reflection, dict):
        payload = latest_reflection.get("payload", {})
        if isinstance(payload, dict):
            strategy = payload.get("strategy", {})
            if isinstance(strategy, dict):
                active_strategy = strategy
    return {
        "status": "ok",
        "environment": settings.environment,
        "proactive_enabled": settings.autonomy_enable_proactive,
        "x_execution_mode": settings.x_execution_mode,
        "profiles": profile_registry.as_dict_list(),
        "dominant_mode": settings.agent_dominant_mode,
        "scheduler": scheduler.snapshot(),
        "queue": queue_stats,
        "operator_queue": operator_queue_stats,
        "growth_kpis_24h": growth_kpis,
        "active_strategy": active_strategy,
        "latest_reflection": latest_reflection,
    }


@router.get("/operator/tasks")
async def list_operator_tasks(
    platform: str = "x",
    status: str = "pending",
    limit: int = 50,
):
    normalized_platform = platform.strip().lower()
    normalized_status = status.strip().lower()

    if normalized_platform and normalized_platform not in {"x", "reddit", "facebook", "instagram"}:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    if normalized_status and normalized_status not in {"pending", "done", "cancelled"}:
        raise HTTPException(status_code=400, detail="Unsupported status")

    tasks = await storage.list_operator_tasks(
        platform=normalized_platform or None,
        status=normalized_status or None,
        limit=limit,
    )
    return {
        "status": "ok",
        "tasks": tasks,
    }


@router.post("/operator/tasks/{task_id}/complete")
async def complete_operator_task(task_id: int, payload: OperatorTaskUpdate):
    status = payload.status.strip().lower()
    if status not in {"done", "cancelled"}:
        raise HTTPException(status_code=400, detail="Status must be done or cancelled")

    updated = await storage.update_operator_task(
        task_id=task_id,
        status=status,
        external_id=payload.external_id.strip() or None,
        notes=payload.notes.strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "status": "ok",
        "task_id": task_id,
        "task_status": status,
    }
