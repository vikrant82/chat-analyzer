from .base_client import ChatClient
from .telegram_client import TelegramClient
from .webex_client import WebexClient
from .reddit_client import RedditClient

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
        elif backend_name == "reddit":
            # This assumes you have a config loading mechanism.
            # You would pass the reddit-specific config here.
            # For now, let's assume it's loaded somehow.
            import json
            with open('config.json') as f:
                config = json.load(f)
            _clients[backend_name] = RedditClient(config['reddit'])
        else:
            raise ValueError(f"Unknown client backend: {backend_name}")
            
    return _clients[backend_name]
