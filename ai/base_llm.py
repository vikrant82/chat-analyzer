from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional

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
    async def call_streaming(
        self,
        model_name: str,
        text_to_summarize: str,
        start_date_str: str,
        end_date_str: str,
        question: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Calls the LLM with a streaming response.
        """
        pass
