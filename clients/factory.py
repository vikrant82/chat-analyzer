from .base_client import ChatClient
from .telegram_client import TelegramClient
from .webex_client import WebexClient

# Keep instances cached to reuse connections and tokens
_clients = {}

def get_client(backend_name: str) -> ChatClient:
    """
    Factory function to get the appropriate client instance.
    """
    if backend_name not in _clients:
        if backend_name == "telegram":
            _clients[backend_name] = TelegramClient()
        elif backend_name == "webex":
            _clients[backend_name] = WebexClient()
        else:
            raise ValueError(f"Unknown client backend: {backend_name}")
            
    return _clients[backend_name]