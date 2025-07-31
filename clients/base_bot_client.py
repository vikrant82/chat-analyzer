from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BotClient(ABC):
    """
    An abstract interface for bot clients, defining a unified contract for bot interactions.
    """

    @abstractmethod
    async def set_webhook(self, webhook_url: str):
        """
        Sets the webhook for the bot.
        """
        pass

    @abstractmethod
    async def get_me(self) -> Dict[str, Any]:
        """
        Gets the bot's own information.
        """
        pass

    @abstractmethod
    async def send_message(self, chat_id: int, text: str):
        """
        Sends a message to a specific chat.
        """
        pass

    @abstractmethod
    async def post_message(self, room_id: str, text: str, parent_id: Optional[str] = None):
        """
        Posts a message to a specific room, with an optional parent for threading.
        """
        pass

    @abstractmethod
    async def get_messages(self, **kwargs) -> list[Dict[str, Any]]:
        """
        Fetches messages based on the provided criteria.
        """
        pass

    @abstractmethod
    async def create_webhook(self, webhook_name: str, target_url: str, resource: str, event: str, filter_str: str):
        """
        Creates a new webhook for the bot.
        """
        pass