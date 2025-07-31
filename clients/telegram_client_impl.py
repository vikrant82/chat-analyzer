# --- START OF FILE clients/telegram_client_impl.py ---

import os
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import User as TelethonUser, Channel as TelethonChannel

from .base_client import ChatClient, Chat, Message, User
from config import settings

logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_CONFIG = settings.get_telegram_config()
API_ID = TELEGRAM_CONFIG.get('api_id')
API_HASH = TELEGRAM_CONFIG.get('api_hash')

# --- Directory Setup ---
SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

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

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        phone = auth_details.get('phone')
        if not phone:
            raise ValueError("Phone number is required for Telegram login.")
        
        session_file = get_session_file(phone)
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                logger.info(f"Removed existing session file: {session_file}")
            except OSError as e:
                logger.error(f"Failed to remove existing session file {session_file}: {e}")

        async with telegram_api_client(phone, check_authorized=False) as client:
            sent_code = await client.send_code_request(phone)
            active_login_attempts[phone] = {'phone_code_hash': sent_code.phone_code_hash}
        
        return {"status": "code_required"}

    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        phone = auth_details.get('phone')
        code = auth_details.get('code')
        password = auth_details.get('password')

        if not phone or not code:
            raise ValueError("Phone and code are required for verification.")
        
        login_attempt = active_login_attempts.get(phone)
        if not login_attempt or 'phone_code_hash' not in login_attempt:
            raise ValueError("No active login attempt found or phone_code_hash is missing.")

        async with telegram_api_client(phone, check_authorized=False) as client:
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=login_attempt['phone_code_hash'])
            except SessionPasswordNeededError:
                if not password:
                    return {"status": "password_required"}
                await client.sign_in(password=password)

        if phone in active_login_attempts:
            del active_login_attempts[phone]
            
        return {"status": "success", "user_identifier": phone}

    async def logout(self, user_identifier: str) -> None:
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

    async def fetch_messages_from_api(
        self,
        user_identifier: str,
        chat_id: str,
        start_date: datetime,
        end_date: datetime,
        image_processing_settings: Optional[Dict[str, Any]] = None,
    ) -> List[Message]:
        
        logger.info(f"Fetching messages for chat {chat_id} from {start_date.date()} to {end_date.date()}")
        
        messages = []
        async with telegram_api_client(user_identifier) as client:
            try:
                chat_id_int = int(chat_id)
                target_entity = await client.get_entity(chat_id_int)
                if isinstance(target_entity, list):
                    target_entity = target_entity[0]
            except (ValueError, TypeError) as e:
                 logger.error(f"Invalid chat_id '{chat_id}': {e}", exc_info=True)
                 return []
            except Exception as e:
                logger.error(f"Error resolving entity '{chat_id}': {e}", exc_info=True)
                return []

            async for message in client.iter_messages(
                target_entity,
                offset_date=end_date + timedelta(days=1),
                reverse=True
            ):
                msg_date_utc = message.date.replace(tzinfo=timezone.utc)

                if msg_date_utc > end_date:
                    continue
                if msg_date_utc < start_date:
                    break  # Since messages are reversed, we can stop

                if not message.text and not message.photo:
                    continue

                sender = await message.get_sender()
                author_name, author_id = "Unknown", "0"
                if isinstance(sender, TelethonUser):
                    author_name = sender.first_name or sender.username or f"User {sender.id}"
                    author_id = str(sender.id)
                elif isinstance(sender, TelethonChannel):
                    author_name = sender.title
                    author_id = str(sender.id)
                
                messages.append(Message(
                    id=str(message.id),
                    text=message.text,
                    author=User(id=author_id, name=author_name),
                    timestamp=message.date.isoformat(),
                    thread_id=str(message.reply_to_msg_id) if message.reply_to_msg_id else None,
                ))
        
        return messages

    async def is_session_valid(self, user_identifier: str) -> bool:
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
