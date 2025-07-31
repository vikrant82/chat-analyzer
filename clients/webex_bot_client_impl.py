import requests
import logging
from typing import List, Dict, Any, Optional
import httpx

from .base_bot_client import BotClient

logger = logging.getLogger(__name__)

MESSAGES_URL = "https://webexapis.com/v1/messages"
WEBHOOKS_URL = "https://webexapis.com/v1/webhooks"

class WebexBotClient(BotClient):
    """
    A simplified Webex client for bot-specific interactions.
    This client uses a long-lived bot token for authentication.
    """
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("Bot token cannot be empty.")
        self.headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }

    async def get_messages(self, room_id: Optional[str] = None, id: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        params = {}
        if room_id:
            params["roomId"] = room_id
        
        url = f"{MESSAGES_URL}/{id}" if id else MESSAGES_URL
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                if id:
                    return [response.json()]
                return response.json().get("items", [])
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching Webex messages: {e.response.text}")
                raise

    async def post_message(self, room_id: str, text: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        data = {"roomId": room_id, "markdown": text}
        if parent_id:
            data["parentId"] = parent_id

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(MESSAGES_URL, headers=self.headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error posting Webex message: {e.response.text}")
                raise

    async def create_webhook(self, webhook_name: str, target_url: str, resource: str, event: str, filter_str: str) -> Dict[str, Any]:
        data = {
            "name": webhook_name,
            "targetUrl": target_url,
            "resource": resource,
            "event": event,
            "filter": filter_str
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(WEBHOOKS_URL, headers=self.headers, json=data)
                response.raise_for_status()
                logger.info(f"Successfully created webhook '{webhook_name}' for target URL '{target_url}'.")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    logger.warning("Webhook with this name and target URL already exists.")
                    return {"status": "exists", "message": "Webhook already exists."}
                logger.error(f"Error creating Webex webhook: {e.response.text}")
                raise

    async def set_webhook(self, webhook_url: str):
        # Not applicable to Webex
        pass

    async def get_me(self) -> Dict[str, Any]:
        # Not applicable to Webex
        return {}

    async def send_message(self, chat_id: int, text: str):
        # Not applicable to Webex
        pass
