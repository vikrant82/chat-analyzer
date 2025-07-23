import httpx
import logging
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone

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

    async def send_message(self, chat_id: int, text: str) -> None:
        """
        Sends a message to a specific chat.
        """
        url = f"{self.api_url}/sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending Telegram message: {e.response.text}")
                raise

    async def get_chat_history(self, user_client: Any, chat_id: int, days: int) -> List[Message]:
        """
        Fetches the chat history for a given chat and number of days.
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        return await user_client.get_messages(
            user_client.user_identifier, str(chat_id), start_date, end_date, enable_caching=False
        )
