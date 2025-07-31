from .base_bot_client import BotClient
from .telegram_bot_client_impl import TelegramBotClient
from .webex_bot_client_impl import WebexBotClient

def get_bot_client(backend: str, token: str) -> BotClient:
    """
    Factory function to get the appropriate bot client instance.
    """
    if backend == "telegram":
        return TelegramBotClient(bot_token=token)
    elif backend == "webex":
        return WebexBotClient(bot_token=token)
    else:
        raise ValueError(f"Unknown bot backend: {backend}")
