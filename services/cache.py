import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import ValidationError

from clients.base_client import Message

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)


class CacheService:
    """A file-based caching service to store and retrieve daily message archives."""

    def __init__(self, backend: str):
        self.backend_cache_dir = os.path.join(CACHE_DIR, backend)
        os.makedirs(self.backend_cache_dir, exist_ok=True)
        logger.info(f"CacheService initialized for backend '{backend}' at {self.backend_cache_dir}")

    def _get_cache_path(self, user_identifier: str, chat_id: str, day: datetime) -> str:
        """Constructs a safe file path for a given user, chat, and day."""
        safe_user_id = ''.join(filter(str.isalnum, user_identifier))
        safe_chat_id = ''.join(filter(str.isalnum, str(chat_id)))
        user_cache_dir = os.path.join(self.backend_cache_dir, safe_user_id, safe_chat_id)
        os.makedirs(user_cache_dir, exist_ok=True)
        return os.path.join(user_cache_dir, f"{day.strftime('%Y-%m-%d')}.json")

    def get(self, user_identifier: str, chat_id: str, day: datetime) -> Optional[List[Message]]:
        """Retrieves a list of messages from the cache for a specific day."""
        cache_path = self._get_cache_path(user_identifier, chat_id, day)
        if not os.path.exists(cache_path):
            return None

        logger.info(f"Cache HIT for chat {chat_id} on {day.date()}")
        with open(cache_path, 'r') as f:
            try:
                raw_msgs = json.load(f)
                return [Message(**msg) for msg in raw_msgs]
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Cache file {cache_path} is corrupted and will be ignored: {e}")
                return None

    def set(self, user_identifier: str, chat_id: str, day: datetime, messages: List[Message]):
        """Saves a list of messages to the cache for a specific day."""
        if not messages:
            logger.debug(f"Not caching for {day.date()} as there are no messages.")
            return
            
        cache_path = self._get_cache_path(user_identifier, chat_id, day)
        try:
            with open(cache_path, 'w') as f:
                json.dump([msg.model_dump() for msg in messages], f, indent=2)
                logger.info(f"Cached {len(messages)} messages for {day.date()} at {cache_path}")
        except IOError as e:
            logger.error(f"Failed to write to cache file {cache_path}: {e}")
