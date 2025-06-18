from .base_client import ChatClient
from .telegram_client_impl import TelegramClientImpl
from .webex_client_impl import WebexClientImpl

# Keep instances cached to reuse connections and tokens
_clients = {
    "telegram": TelegramClientImpl(),
    "webex": WebexClientImpl()
}

def get_client(backend_name: str) -> ChatClient:
    """
    Factory function to get the appropriate client instance.
    """
    client = _clients.get(backend_name)
    if not client:
        raise ValueError(f"Unknown client backend: {backend_name}")
    return client