"""
N8N Webhook Integration
Trigger workflows for booking confirmations, cancellations, escalations
"""

import logging
import os
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("ActionFlow-N8N")

N8N_BASE_URL = os.getenv("N8N_WEBHOOK_BASE", "http://n8n:5678/webhook")


async def trigger_booking_confirmation(
    booking_id: str,
    email: str,
    details: Dict[str, Any]
) -> bool:
    """Trigger booking confirmation email workflow"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{N8N_BASE_URL}/booking-confirmation",
                json={
                    "booking_id": booking_id,
                    "email": email,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ n8n booking confirmation sent: {booking_id}")
                return True
            else:
                logger.error(f"❌ n8n error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ n8n request failed: {e}")
            return False


async def trigger_escalation_alert(
    conversation_id: str,
    urgency: str,
    reason: str,
    customer_info: Optional[Dict] = None
) -> bool:
    """Trigger escalation alert (email + Slack)"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{N8N_BASE_URL}/escalation-alert",
                json={
                    "conversation_id": conversation_id,
                    "urgency": urgency,
                    "reason": reason,
                    "customer_info": customer_info or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ n8n escalation alert sent: {conversation_id}")
                return True
            else:
                logger.error(f"❌ n8n escalation error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ n8n escalation failed: {e}")
            return False