"""WebSocket router for real-time LLM streaming and enforcement progress."""
from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.config import settings
from aegis.database import AsyncSessionLocal
from aegis.services.rbac import decode_ws_token

router = APIRouter(prefix="/ws", tags=["websockets"])
logger = logging.getLogger(__name__)


async def _authenticate_ws(websocket: WebSocket, token: str) -> bool:
    """Validate JWT and close with code 4001 if invalid."""
    async with AsyncSessionLocal() as db:
        try:
            await decode_ws_token(token, db)
            return True
        except (ValueError, Exception):
            await websocket.close(code=4001)
            return False


@router.websocket("/codegen/{blueprint_id}")
async def codegen_stream(
    websocket: WebSocket,
    blueprint_id: str,
    token: str = Query(...),
) -> None:
    """
    Subscribe to code generation progress events for a HardeningBlueprint.
    Events are published by the Celery codegen_tasks worker to Redis pub/sub.
    """
    await websocket.accept()
    if not await _authenticate_ws(websocket, token):
        return

    channel = f"ws:codegen:{blueprint_id}"
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    await websocket.send_text(data)
                    parsed = json.loads(data)
                    if parsed.get("type") in ("completed", "failed"):
                        break
                except WebSocketDisconnect:
                    break
                except Exception as exc:
                    logger.warning("WebSocket send error on codegen/%s: %s", blueprint_id, exc)
                    break
    finally:
        await pubsub.unsubscribe(channel)
        await redis_client.aclose()


@router.websocket("/enforcement/{job_id}")
async def enforcement_stream(
    websocket: WebSocket,
    job_id: str,
    token: str = Query(...),
) -> None:
    """
    Subscribe to enforcement job progress events (evaluate/remediate/rollback/dry-run).
    """
    await websocket.accept()
    if not await _authenticate_ws(websocket, token):
        return

    channel = f"ws:enforcement:{job_id}"
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    await websocket.send_text(data)
                    parsed = json.loads(data)
                    if parsed.get("type") in ("completed", "failed"):
                        break
                except WebSocketDisconnect:
                    break
                except Exception as exc:
                    logger.warning("WebSocket send error on enforcement/%s: %s", job_id, exc)
                    break
    finally:
        await pubsub.unsubscribe(channel)
        await redis_client.aclose()
