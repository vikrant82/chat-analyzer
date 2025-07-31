import httpx
import logging
from typing import Optional, List, Any, Dict

from .base_bot_client import BotClient

logger = logging.getLogger(__name__)

class TelegramBotClient(BotClient):
    """
    A client for Telegram Bot API interactions.
    """
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("Bot token cannot be empty.")
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def set_webhook(self, webhook_url: str) -> None:
        url = f"{self.api_url}/setWebhook"
        params = {"url": webhook_url}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params)
                response.raise_for_status()
                logger.info(f"Successfully set webhook for Telegram bot to {webhook_url}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Error setting Telegram webhook: {e.response.text}")
                raise

    async def get_me(self) -> Dict[str, Any]:
        url = f"{self.api_url}/getMe"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json().get("result", {})
            except httpx.HTTPStatusError as e:
                logger.error(f"Error getting bot info: {e.response.text}")
                raise

    async def send_message(self, chat_id: int, text: str):
        url = f"{self.api_url}/sendMessage"
        params = {"chat_id": chat_id, "text": text}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending Telegram message: {e.response.text}")
                raise

    async def post_message(self, room_id: str, text: str, parent_id: Optional[str] = None):
        # Not applicable to Telegram
        pass

    async def get_messages(self, **kwargs) -> list[Dict[str, Any]]:
        # Not applicable to Telegram
        return []

    async def create_webhook(self, webhook_name: str, target_url: str, resource: str, event: str, filter_str: str):
        # Not applicable to Telegram
        pass

