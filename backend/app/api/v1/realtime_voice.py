"""
Realtime Voice WebSocket Endpoint - ActionFlow
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging
from app.services.voice.realtime_service import realtime_session_handler

router = APIRouter(prefix="/voice", tags=["Realtime Voice"])
logger = logging.getLogger("ActionFlow-RealtimeVoice")


@router.websocket("/realtime")
async def realtime_voice_ws(
    websocket: WebSocket,
    customer_id: str = Query(default="anonymous"),
):
    await websocket.accept()
    logger.info(f"Voice WebSocket connected: customer={customer_id}")
    try:
        await realtime_session_handler(websocket, customer_id)
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: customer={customer_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
