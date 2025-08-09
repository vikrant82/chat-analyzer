from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional

class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass

class LLMClient(ABC):
    """
    An abstract interface for Large Language Model (LLM) clients.
    """

    @abstractmethod
    async def initialize_models(self) -> None:
        """
        Initializes the available models for the client.
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Returns a list of available models for the client.
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> Optional[str]:
        """
        Returns the default model for the client.
        """
        pass

    @abstractmethod
    async def call_conversational(
        self,
        model_name: str,
        conversation: List[Dict[str, Any]],
        original_messages: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Calls the LLM with a streaming response for a conversational query.
        """
        pass
