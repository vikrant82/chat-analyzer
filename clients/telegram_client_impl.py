# --- START OF FILE clients/telegram_client_impl.py ---

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime, timezone, timedelta

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, RPCError, FloodWaitError
from telethon.tl.types import User as TelethonUser, Channel as TelethonChannel

from .base_client import ChatClient, Chat, Message, User

logger = logging.getLogger(__name__)

# --- Configuration Loading ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    TELEGRAM_CONFIG = config.get('telegram', {})
    API_ID = TELEGRAM_CONFIG.get('api_id')
    API_HASH = TELEGRAM_CONFIG.get('api_hash')
except (FileNotFoundError, KeyError):
    API_ID, API_HASH = None, None
    logger.error("Telegram config (api_id, api_hash) not found in config.json")

# --- Directory Setup ---
SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache', 'telegram')
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

active_login_attempts: Dict[str, Dict[str, Any]] = {}

def get_session_path(phone: str) -> str:
    safe_phone = ''.join(filter(str.isalnum, phone))
    return os.path.join(SESSION_DIR, f'session_{safe_phone}')

def get_session_file(phone: str) -> str:
    return f"{get_session_path(phone)}.session"

@asynccontextmanager
async def telegram_api_client(phone: str, check_authorized: bool = True) -> AsyncGenerator[TelegramClient, None]:
    if not API_ID or not API_HASH:
        raise ValueError("Telegram API_ID and API_HASH must be configured in config.json")
    session_path = get_session_path(phone)
    client = TelegramClient(session_path, int(API_ID), API_HASH)
    try:
        await client.connect()
        if check_authorized and not await client.is_user_authorized():
            raise Exception("User not authorized (401)")
        yield client
    finally:
        if client.is_connected():
            client.disconnect()

class TelegramClientImpl(ChatClient):

    def _get_cache_path(self, user_identifier: str, chat_id: str, day: datetime) -> str:
        safe_user_id = ''.join(filter(str.isalnum, user_identifier))
        safe_chat_id = ''.join(filter(str.isalnum, str(chat_id)))
        user_cache_dir = os.path.join(CACHE_DIR, safe_user_id, safe_chat_id)
        os.makedirs(user_cache_dir, exist_ok=True)
        return os.path.join(user_cache_dir, f"{day.strftime('%Y-%m-%d')}.json")

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        # This method is correct and unchanged
        phone = auth_details.get('phone')
        if not phone:
            raise ValueError("Phone number is required for Telegram login.")
        session_file = get_session_file(phone)
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except OSError as e:
                logger.error(f"Failed to remove existing session file {session_file}: {e}")
        async with telegram_api_client(phone, check_authorized=False) as client:
            sent_code = await client.send_code_request(phone)
            active_login_attempts[phone] = {'phone_code_hash': sent_code.phone_code_hash}
        return {"status": "code_required"}

    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        # This method is correct and unchanged
        phone = auth_details.get('phone')
        code = auth_details.get('code')
        password = auth_details.get('password')
        if not phone:
            raise ValueError("Missing phone for verification.")
        login_attempt = active_login_attempts.get(phone)
        if not login_attempt:
            raise ValueError("No active login attempt found for this phone number.")
        if not code:
            raise ValueError("Missing code for verification.")

        phone_code_hash = login_attempt.get('phone_code_hash')
        if not phone_code_hash:
            raise ValueError("phone_code_hash not found in login attempt.")

        async with telegram_api_client(phone, check_authorized=False) as client:
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                if not password:
                    return {"status": "password_required"}
                await client.sign_in(password=password)
        if phone in active_login_attempts:
            del active_login_attempts[phone]
        return {"status": "success", "user_identifier": phone}

    async def logout(self, user_identifier: str) -> None:
        # This method is correct and unchanged
        session_file = get_session_file(user_identifier)
        if not os.path.exists(session_file):
            return
        try:
            async with telegram_api_client(user_identifier, check_authorized=True) as client:
                await client.log_out()
        except Exception as e:
            logger.warning(f"Error during Telegram server logout for {user_identifier}, proceeding with local cleanup: {e}")
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except OSError as e:
                logger.error(f"Failed to remove session file on logout {session_file}: {e}")

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        # This method is correct and unchanged
        chats = []
        async with telegram_api_client(user_identifier) as client:
            async for dialog in client.iter_dialogs(limit=200):
                chat_type = "private"
                if dialog.is_group: chat_type = "group"
                elif dialog.is_channel: chat_type = "channel"
                chats.append(Chat(
                    id=str(dialog.id),
                    title=dialog.name or dialog.title or f"Chat ID {dialog.id}",
                    type=chat_type
                ))
        return chats

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str, enable_caching: bool = True) -> List[Message]:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1, microseconds=-1)
        today_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_messages = []
        dates_to_fetch_from_api = []
        
        current_day = start_dt
        while current_day <= end_dt:
            is_cacheable = current_day < today_dt
            cache_path = self._get_cache_path(user_identifier, chat_id, current_day)
            
            if is_cacheable and os.path.exists(cache_path):
                logger.info(f"Cache HIT for Telegram chat {chat_id} on {current_day.date()}")
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
            fetch_start = dates_to_fetch_from_api[0]
            fetch_end = dates_to_fetch_from_api[-1] + timedelta(days=1, microseconds=-1)

            logger.info(f"Cache MISS for Telegram chat {chat_id}. Fetching from {fetch_start.date()} to {fetch_end.date()}.")

            newly_fetched_messages = []
            async with telegram_api_client(user_identifier) as client:
                try:
                    chat_id_input = chat_id
                    if isinstance(chat_id_input, str) and chat_id_input.lstrip('-').isdigit():
                        chat_id_input = int(chat_id_input)
                    
                    from telethon.tl.types import PeerUser
                    
                    chat_id_int = int(chat_id_input)
                    target_entity = await client.get_entity(PeerUser(chat_id_int))
                    if isinstance(target_entity, list):
                        target_entity = target_entity[0]

                except Exception as e:
                    logger.error(f"Error resolving entity '{chat_id}': {e}", exc_info=True)
                    return []

                logger.info(f"Fetching messages with offset_date={fetch_end.isoformat()} and reverse=False")
                async for message in client.iter_messages(target_entity, limit=200, offset_date=fetch_end, reverse=False):
                    #logger.info(f"Processing message {message.id} from {message.date.isoformat()}")
                    
                    msg_date_utc = message.date.replace(tzinfo=timezone.utc)

                    if msg_date_utc < fetch_start:
                        logger.info(f"Message {message.id} is older than fetch_start date {fetch_start.isoformat()}, stopping.")
                        break
                    
                    # if msg_date_utc > fetch_end:
                    #     logger.info(f"Message {message.id} is newer than fetch_end date {fetch_end.isoformat()}, skipping.")
                    #     continue
                    
                    #logger.info(f"Full message object: {message.to_json()}")
    
                    if not message.text:
                        logger.info(f"Message {message.id} does not have text, skipping.")
                        continue
    
                    #logger.info(f"Message {message.id} has text: '{message.text[:50]}...'")
                    sender = await message.get_sender()
                    author_name, author_id = "Unknown", "0"
                    if isinstance(sender, TelethonUser):
                        author_name = sender.first_name or sender.username or f"User {sender.id}"
                        author_id = str(sender.id)
                    elif isinstance(sender, TelethonChannel):
                        author_name = sender.title
                        author_id = str(sender.id)
                    
                    newly_fetched_messages.append(Message(
                        id=str(message.id),
                        text=message.text,
                        author=User(id=author_id, name=author_name),
                        timestamp=message.date.isoformat(),
                    ))
            
            all_messages.extend(newly_fetched_messages)

            # Simplified caching logic when not disabled
            if enable_caching:
                grouped_by_day = {}
                for msg in newly_fetched_messages:
                    msg_day = datetime.fromisoformat(msg.timestamp).replace(hour=0, minute=0, second=0, microsecond=0)
                    if msg_day not in grouped_by_day:
                        grouped_by_day[msg_day] = []
                    grouped_by_day[msg_day].append(msg)

                for day_to_cache in dates_to_fetch_from_api:
                    if day_to_cache < today_dt:
                        messages_for_this_day = grouped_by_day.get(day_to_cache, [])
                        cache_path = self._get_cache_path(user_identifier, chat_id, day_to_cache)
                        with open(cache_path, 'w') as f:
                            logger.info(f"Caching {len(messages_for_this_day)} messages for {day_to_cache.date()} at {cache_path}")
                            json.dump([msg.model_dump() for msg in messages_for_this_day], f)
        
        logger.info(f"Returning {len(all_messages)} messages from get_messages.")
        return sorted(all_messages, key=lambda m: m.timestamp)

    async def is_session_valid(self, user_identifier: str) -> bool:
        # This method is correct and unchanged
        session_file = get_session_file(user_identifier)
        if not os.path.exists(session_file):
            return False
        try:
            async with telegram_api_client(user_identifier, check_authorized=True):
                pass
            return True
        except Exception:
            return False

# --- END OF FILE clients/telegram_client_impl.py ---
