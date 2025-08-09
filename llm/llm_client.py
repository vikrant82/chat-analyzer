import asyncio
import json
import logging
from typing import Dict, Any

from ai.factory import get_all_llm_clients

logger = logging.getLogger(__name__)

llm_clients: Dict[str, Any] = {}
config = {}

async def initialize_llm_clients():
    """
    Initializes the LLM clients by reading the configuration and setting up
    the clients.
    """
    global llm_clients, config
    try:
        with open('config.json', 'r') as f:
            config.update(json.load(f))
        google_ai_config = config.get('google_ai', {})
        openai_compatible_configs = config.get('openai_compatible', [])
        llm_clients.update(get_all_llm_clients(google_ai_config, openai_compatible_configs))
        
        initialization_tasks = [client.initialize_models() for client in llm_clients.values()]
        await asyncio.gather(*initialization_tasks)
        logger.info("LLM clients initialized successfully.")

    except FileNotFoundError:
        logger.error("config.json not found! LLM clients will not be available.")
    except Exception as e:
        logger.error(f"Failed to initialize LLM clients: {e}", exc_info=True)