from typing import Optional
from .telegram_bot_client import TelegramBotClient
from .webex_bot_client import WebexBotClient

class UnifiedBotClient:
    def __init__(self, client):
        self._client = client

    async def set_webhook(self, webhook_url: str):
        if isinstance(self._client, TelegramBotClient):
            await self._client.set_webhook(webhook_url)
        else:
            # WebexBotClient does not have a set_webhook method
            pass

    async def create_webhook(self, webhook_name: str, target_url: str, resource: str, event: str, filter_str: str):
        if isinstance(self._client, WebexBotClient):
            self._client.create_webhook(webhook_name, target_url, resource, event, filter_str)
        else:
            # TelegramBotClient does not have a create_webhook method
            pass

    async def send_message(self, chat_id: int, text: str):
        if isinstance(self._client, TelegramBotClient):
            await self._client.send_message(chat_id, text)
        else:
            # WebexBotClient does not have a send_message method
            pass

    def post_message(self, room_id: str, text: str, parent_id: Optional[str] = None):
        if isinstance(self._client, WebexBotClient):
            self._client.post_message(room_id, text, parent_id)
        else:
            # TelegramBotClient does not have a post_message method
            pass

    async def get_messages(self, **kwargs):
        return self._client.get_messages(**kwargs)

    async def get_me(self) -> dict:
        if isinstance(self._client, TelegramBotClient):
            return await self._client.get_me()
        # Return a default/empty dict or raise an error if not applicable
        return {}


def get_bot_client(backend: str, token: str):
    """
    Factory function to get the appropriate bot client instance.
    """
    if backend == "telegram":
        return UnifiedBotClient(TelegramBotClient(bot_token=token))
    elif backend == "webex":
        return UnifiedBotClient(WebexBotClient(bot_token=token))
    else:
        raise ValueError(f"Unknown bot backend: {backend}")
