import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

from ai.factory import get_all_llm_clients
from ai.base_llm import LLMClient

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Manages the lifecycle of LLM clients, including initialization and access.
    """
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.clients: Dict[str, LLMClient] = {}
        self.config: Dict[str, Any] = {}

    async def initialize_clients(self):
        """
        Initializes the LLM clients by reading the configuration and setting up
        the clients.
        """
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            
            google_ai_config = self.config.get('google_ai', {})
            openai_compatible_configs = self.config.get('openai_compatible', [])
            
            # This function now returns a dictionary of clients
            self.clients = get_all_llm_clients(google_ai_config, openai_compatible_configs)
            
            initialization_tasks = [client.initialize_models() for client in self.clients.values()]
            await asyncio.gather(*initialization_tasks)
            logger.info("LLM clients initialized successfully.")

        except FileNotFoundError:
            logger.error(f"{self.config_path} not found! LLM clients will not be available.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}", exc_info=True)

    def get_client(self, provider: str) -> LLMClient:
        """
        Retrieves a specific LLM client by provider name.
        """
        client = self.clients.get(provider)
        if not client:
            raise ValueError(f"No LLM client found for provider: {provider}")
        return client

    def get_all_clients(self) -> List[LLMClient]:
        """
        Returns a list of all initialized LLM clients.
        """
        return list(self.clients.values())

    def get_available_models(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary of all available models, grouped by provider.
        """
        return {provider: client.get_available_models() for provider, client in self.clients.items()}

    def is_multimodal(self, provider: str, model_name: str) -> bool:
        """
        Checks if a given model is multimodal.
        """
        # For now, assume all models are multimodal.
        # TODO: Implement more sophisticated logic to check model capabilities.
        return True

    async def call_conversational(
        self,
        provider: str,
        model_name: str,
        conversation: List[Dict[str, Any]],
        original_messages: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Routes a conversational call to the appropriate LLM client.
        """
        client = self.get_client(provider)
        if model_name not in client.get_available_models():
            raise ValueError(f"Model '{model_name}' is not available for provider '{provider}'.")
        
        return client.call_conversational(model_name, conversation, original_messages)
