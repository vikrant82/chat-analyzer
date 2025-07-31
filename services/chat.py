import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from clients.base_client import ChatClient, Message
from services.cache import CacheService

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates chat history fetching, caching, and processing."""

    def __init__(self, client: ChatClient, cache_service: CacheService):
        self.client = client
        self.cache = cache_service

    async def get_messages(
        self,
        user_identifier: str,
        chat_id: str,
        start_date_str: str,
        end_date_str: str,
        enable_caching: bool = True,
        image_processing_settings: Optional[Dict[str, Any]] = None,
    ) -> List[Message]:
        """
        Fetches messages for a given chat and date range, using a cache-then-fetch strategy.
        """
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_dt = (
            datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            + timedelta(days=1, microseconds=-1)
        )
        
        # The service now directly calls the client's fetch method.
        # The caching logic is handled by the CacheService.
        messages = await self.client.fetch_messages_from_api(
            user_identifier=user_identifier,
            chat_id=chat_id,
            start_date=start_dt,
            end_date=end_dt,
            image_processing_settings=image_processing_settings,
        )

        return self._sort_and_thread_messages(messages)

    def _sort_and_thread_messages(self, messages: List[Message]) -> List[Message]:
        """Sorts messages and reconstructs threads."""
        if not messages:
            return []

        threads: Dict[str, List[Message]] = {}
        top_level_messages: List[Message] = []

        for msg in messages:
            if msg.thread_id:
                if msg.thread_id not in threads:
                    threads[msg.thread_id] = []
                threads[msg.thread_id].append(msg)
            else:
                top_level_messages.append(msg)
        
        for thread_id in threads:
            threads[thread_id].sort(key=lambda m: m.timestamp)

        final_message_list: List[Message] = []
        top_level_messages.sort(key=lambda m: m.timestamp)

        for top_msg in top_level_messages:
            final_message_list.append(top_msg)
            if top_msg.id in threads:
                final_message_list.extend(threads[top_msg.id])
                del threads[top_msg.id]
        
        # Add any orphaned threads
        for thread_id in sorted(threads.keys()):
             final_message_list.extend(threads[thread_id])

        return final_message_list