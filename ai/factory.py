from typing import Dict, Any, Optional, List

from .base_llm import LLMClient
from .google_ai_llm import GoogleAILLM
from .openai_compatible_llm import OpenAICompatibleLLM

_clients: Dict[str, LLMClient] = {}

def get_llm_client(provider_name: str, config: Dict[str, Any]) -> Optional[LLMClient]:
    """
    Factory function to get the appropriate LLM client instance.
    """
    if provider_name not in _clients:
        if provider_name == "google_ai":
            _clients[provider_name] = GoogleAILLM(config)
        else:
            # Assume any other provider is OpenAI compatible
            _clients[provider_name] = OpenAICompatibleLLM(config)
            
    return _clients.get(provider_name)

def get_all_llm_clients(google_ai_config: Dict[str, Any], openai_compatible_configs: List[Dict[str, Any]]) -> Dict[str, LLMClient]:
    """
    Returns all available LLM clients.
    """
    clients = {}
    if google_ai_config.get("api_key"):
        clients["google_ai"] = get_llm_client("google_ai", google_ai_config)
    
    for config in openai_compatible_configs:
        provider_name = config.get("name")
        if provider_name and config.get("url"):
            clients[provider_name] = get_llm_client(provider_name, config)
            
    return clients
