# api/app/routes/ws.py
"""
WebSocket endpoint: GET /ws/alerts
Subscribes to Redis pub/sub channel "alerts" and pushes messages to
connected clients in real time.
"""
import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

router = APIRouter(tags=["websocket"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("alerts")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    data = {"text": message["data"]}
                await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("alerts")
        await r.aclose()
