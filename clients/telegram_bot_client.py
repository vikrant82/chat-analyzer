import httpx
import logging
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone
from telethon.tl.types import User as TelethonUser, Channel as TelethonChannel

from .base_client import Message, User

logger = logging.getLogger(__name__)

class TelegramBotClient:
    """
    A client for Telegram Bot API interactions.
    """
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("Bot token cannot be empty.")
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.client = None

    async def set_webhook(self, webhook_url: str) -> None:
        """
        Sets the webhook for the bot.
        """
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

    async def get_me(self) -> dict:
        """
        Gets the bot's own information.
        """
        url = f"{self.api_url}/getMe"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json().get("result")
            except httpx.HTTPStatusError as e:
                logger.error(f"Error getting bot info: {e.response.text}")
                raise

    async def send_message(self, chat_id: int, text: str) -> None:
        """
        Sends a message to a specific chat.
        """
        url = f"{self.api_url}/sendMessage"
        # Not using Markdown parsing to avoid errors from AI-generated text.
        params = {"chat_id": chat_id, "text": text}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending Telegram message: {e.response.text}")
                raise

