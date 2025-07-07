from typing import Dict, Any, Optional

from .base_llm import LLMClient
from .google_ai_llm import GoogleAILLM
from .lm_studio_llm import LMStudioLLM

_clients: Dict[str, LLMClient] = {}

def get_llm_client(provider_name: str, config: Dict[str, Any]) -> Optional[LLMClient]:
    """
    Factory function to get the appropriate LLM client instance.
    """
    if provider_name not in _clients:
        if provider_name == "google_ai":
            _clients[provider_name] = GoogleAILLM(config)
        elif provider_name == "lm_studio":
            _clients[provider_name] = LMStudioLLM(config)
        else:
            return None
    return _clients.get(provider_name)

def get_all_llm_clients(google_ai_config: Dict[str, Any], lm_studio_config: Dict[str, Any]) -> Dict[str, LLMClient]:
    """
    Returns all available LLM clients.
    """
    clients = {}
    if google_ai_config.get("api_key"):
        clients["google_ai"] = get_llm_client("google_ai", google_ai_config)
    if lm_studio_config.get("url"):
        clients["lm_studio"] = get_llm_client("lm_studio", lm_studio_config)
    return clients
