import logging
from datetime import datetime
from typing import Dict, Any

from app.services.integration.n8n_service import n8n_service

logger = logging.getLogger("ActionFlow-BookingNotifications")


async def trigger_booking_confirmation(booking_data: Dict[str, Any], booking_type: str):
    """n8n booking confirmation workflow'unu tetikle"""
    
    payload = {
        "event": "booking_confirmed",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "booking_type": booking_type,
        "customer_email": booking_data.get("contact_email"),
        "total_amount": booking_data["total_amount"],
        "currency": booking_data["currency"],
        "details": booking_data["details"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add passenger info for flights/packages
    if "passengers" in booking_data:
        passengers = booking_data["passengers"]
        if passengers:
            payload["customer_name"] = f"{passengers[0].get('first_name', '')} {passengers[0].get('last_name', '')}".strip()
    elif "guest_name" in booking_data:
        payload["customer_name"] = booking_data["guest_name"]
    
    success = await n8n_service.trigger_workflow("booking-confirmation", payload)
    
    if success:
        logger.info(f"📧 Booking confirmation workflow triggered for {booking_data['id']}")
    else:
        logger.warning(f"⚠️ Failed to trigger confirmation workflow for {booking_data['id']}")

async def trigger_cancellation_notification(booking_data: Dict[str, Any]):
    """n8n cancellation workflow'unu tetikle"""
    
    payload = {
        "event": "booking_cancelled",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "customer_email": booking_data.get("contact_email"),
        "refund_amount": booking_data.get("refund_amount", 0),
        "currency": booking_data["currency"],
        "reason": booking_data.get("cancellation_reason"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await n8n_service.trigger_workflow("booking-cancellation", payload)
    logger.info(f"📧 Cancellation notification triggered for {booking_data['id']}")

async def trigger_modification_notification(booking_data: Dict[str, Any], changes: Dict[str, Any]):
    """n8n modification workflow'unu tetikle"""
    
    payload = {
        "event": "booking_modified",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "customer_email": booking_data.get("contact_email"),
        "changes": changes,
        "updated_details": booking_data["details"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await n8n_service.trigger_workflow("booking-modification", payload)
    logger.info(f"📧 Modification notification triggered for {booking_data['id']}")

