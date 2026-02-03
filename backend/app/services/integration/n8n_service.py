import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger("ActionFlow-n8n")

N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "http://n8n:5678/webhook")

class N8NService:
    """
    Service for triggering n8n workflows via webhooks.
    """
    
    def __init__(self):
        self.base_url = N8N_WEBHOOK_BASE
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def trigger_workflow(self, webhook_path: str, payload: Dict[str, Any]) -> bool:
        """
        Triggers an n8n webhook workflow.
        
        Args:
            webhook_path: The specific webhook path (e.g., "booking-confirmation")
            payload: Data to send to the workflow
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/{webhook_path}"
        try:
            logger.info(f"🚀 Triggering n8n workflow: {webhook_path}")
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"✅ n8n workflow triggered successfully: {response.text}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to trigger n8n workflow: {str(e)}")
            return False

    async def close(self):
        await self.http_client.aclose()

# Singleton instance
n8n_service = N8NService()
