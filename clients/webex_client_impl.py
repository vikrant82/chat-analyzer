# --- START OF FILE clients/webex_client_impl.py ---

import os
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from .base_client import ChatClient, Chat, Message, User
from WebexClient import WebexClient
import json
import logging

logger = logging.getLogger(__name__)

# --- Configuration Loading ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f).get('webex', {})
    WEBEX_CONFIG = config
except FileNotFoundError:
    WEBEX_CONFIG = {}
    logger.error("Webex config not found in config.json")

# --- Directory Setup ---
SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'webex')
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
TOKEN_STORAGE_PATH = os.path.join(SESSION_DIR, 'webex_tokens.json')


class WebexClientImpl(ChatClient):
    def __init__(self):
        self.api = WebexClient(
            client_id=WEBEX_CONFIG.get('client_id'),
            client_secret=WEBEX_CONFIG.get('client_secret'),
            redirect_uri=WEBEX_CONFIG.get('redirect_uri'),
            scopes=WEBEX_CONFIG.get('scopes', []),
            token_storage_path=TOKEN_STORAGE_PATH
        )

    def _get_cache_path(self, user_identifier: str, chat_id: str, day: datetime) -> str:
        safe_user_id = ''.join(filter(str.isalnum, user_identifier))
        safe_chat_id = ''.join(filter(str.isalnum, str(chat_id)))
        user_cache_dir = os.path.join(CACHE_DIR, safe_user_id, safe_chat_id)
        os.makedirs(user_cache_dir, exist_ok=True)
        return os.path.join(user_cache_dir, f"{day.strftime('%Y-%m-%d')}.json")

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        # This method is correct and unchanged
        auth_url = self.api.get_authorization_url()
        return {"status": "redirect_required", "url": auth_url}

    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        # This method is correct and unchanged
        auth_code = auth_details.get("code")
        if not auth_code:
            raise ValueError("Authorization code is required for Webex verification.")
        try:
            self.api.exchange_code_for_tokens(auth_code)
            user_details = self.api.get_user_details()
            user_id = user_details['id']
            return {"status": "success", "user_identifier": user_id}
        except Exception as e:
            logger.error(f"Webex token exchange failed: {e}", exc_info=True)
            raise

    async def logout(self, user_identifier: str) -> None:
        # This method is correct and unchanged
        try:
            self.api.revoke_token()
        except Exception as e:
            logger.error(f"Error during Webex token revocation: {e}", exc_info=True)

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        # This method is correct and unchanged
        raw_rooms = self.api.get_rooms()
        chats = [
            Chat(
                id=room['id'],
                title=room['title'],
                type='group' if room['type'] == 'group' else 'private'
            ) for room in raw_rooms
        ]
        return chats

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str) -> List[Message]:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        today_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        all_messages = []
        dates_to_fetch_from_api = []

        current_day = start_dt
        while current_day <= end_dt:
            is_cacheable = current_day < today_dt
            cache_path = self._get_cache_path(user_identifier, chat_id, current_day)
            
            if is_cacheable and os.path.exists(cache_path):
                logger.info(f"Cache HIT for Webex chat {chat_id} on {current_day.date()}")
                with open(cache_path, 'r') as f:
                    try:
                        raw_msgs = json.load(f)
                        all_messages.extend([Message(**msg) for msg in raw_msgs])
                    except json.JSONDecodeError:
                        logger.warning(f"Cache file {cache_path} is corrupted. Re-fetching.")
                        dates_to_fetch_from_api.append(current_day)
            else:
                dates_to_fetch_from_api.append(current_day)
            
            current_day += timedelta(days=1)
        
        if dates_to_fetch_from_api:
            logger.info(f"Cache MISS for Webex chat {chat_id}. Fetching recent messages to build cache.")
            
            # Fetch a large batch to cover missing days.
            all_recent_raw_messages = self.api.get_messages(room_id=chat_id, max=1000)
            
            grouped_by_day = {}
            for msg_raw in all_recent_raw_messages:
                if not msg_raw.get('text'):
                    continue
                
                msg_dt = datetime.fromisoformat(msg_raw['created'].replace('Z', '+00:00'))
                msg_day = msg_dt.replace(hour=0, minute=0, second=0, microsecond=0)

                if msg_day in dates_to_fetch_from_api:
                    if msg_day not in grouped_by_day:
                        grouped_by_day[msg_day] = []
                    
                    author = User(id=msg_raw.get('personId', 'unknown'), name=msg_raw.get('personEmail', 'Unknown User'))
                    message = Message(
                        id=msg_raw['id'],
                        text=msg_raw['text'],
                        author=author,
                        timestamp=msg_raw['created'],
                        thread_id=msg_raw.get('parentId')
                    )
                    grouped_by_day[msg_day].append(message)

            # --- THIS IS THE CORRECTED CACHING LOGIC ---
            
            # 1. Iterate through ALL days we intended to fetch
            for day_to_cache in dates_to_fetch_from_api:
                # 2. Get messages for this day, or an empty list if none were found
                messages_for_this_day = grouped_by_day.get(day_to_cache, [])
                
                # 3. Add them to the main list for the final result
                all_messages.extend(messages_for_this_day)
                
                # 4. If the day is before today, cache the result, even if it's empty
                if day_to_cache < today_dt:
                    cache_path = self._get_cache_path(user_identifier, chat_id, day_to_cache)
                    with open(cache_path, 'w') as f:
                        logger.info(f"Caching {len(messages_for_this_day)} messages for Webex on {day_to_cache.date()} at {cache_path}")
                        json.dump([msg.model_dump() for msg in messages_for_this_day], f)

        return sorted(all_messages, key=lambda m: m.timestamp)

    async def is_session_valid(self, user_identifier: str) -> bool:
        # This method is correct and unchanged
        try:
            self.api.get_user_details()
            return True
        except Exception:
            return False

# --- END OF FILE clients/webex_client_impl.py ---