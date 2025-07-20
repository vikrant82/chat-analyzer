import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

MESSAGES_URL = "https://webexapis.com/v1/messages"
WEBHOOKS_URL = "https://webexapis.com/v1/webhooks"

class WebexBotClient:
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

    def get_messages(self, room_id: Optional[str] = None, id: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches messages from a specific Webex room.
        """
        params = {}
        if room_id:
            params["roomId"] = room_id
        if id:
            # If fetching a single message by ID, the URL is different
            url = f"{MESSAGES_URL}/{id}"
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return [response.json()] # Return as a list for consistency
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Webex message {id}: {e}")
                raise

        params.update(kwargs)
        try:
            response = requests.get(MESSAGES_URL, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("items", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Webex messages for room {room_id}: {e}")
            raise

    def post_message(self, room_id: str, text: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Posts a message to a specific Webex room.
        Can be a new message or a reply to an existing one.
        """
        data = {
            "roomId": room_id,
            "markdown": text
        }
        if parent_id:
            data["parentId"] = parent_id

        try:
            response = requests.post(MESSAGES_URL, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting Webex message to room {room_id}: {e}")
            raise

    def create_webhook(self, webhook_name: str, target_url: str, resource: str, event: str, filter_str: str) -> Dict[str, Any]:
        """
        Creates a new webhook for the bot.
        """
        data = {
            "name": webhook_name,
            "targetUrl": target_url,
            "resource": resource,
            "event": event,
            "filter": filter_str
        }
        try:
            response = requests.post(WEBHOOKS_URL, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info(f"Successfully created webhook '{webhook_name}' for target URL '{target_url}'.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Webex webhook: {e}")
            # Check for specific error message if webhook already exists
            if e.response and e.response.status_code == 409:
                logger.warning("Webhook with this name and target URL already exists.")
                # You might want to return a specific indicator or the existing webhook details
                return {"status": "exists", "message": "Webhook already exists."}
            raise
