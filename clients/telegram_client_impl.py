# --- START OF FILE clients/telegram_client_impl.py ---

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, RPCError, FloodWaitError
from telethon.tl.types import User as TelethonUser, Channel as TelethonChannel

from .base_client import ChatClient, Chat, Message, User, Attachment

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

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str, enable_caching: bool = True, image_processing_settings: Optional[Dict[str, Any]] = None, timezone_str: Optional[str] = None) -> List[Message]:
        # Align behavior with user-local day semantics (e.g., IST) similar to Webex fix
        user_tz = ZoneInfo(timezone_str) if timezone_str else ZoneInfo("UTC")

        # Resolve image processing toggles (UX/global config + per-request)
        # Defaults: disabled unless explicitly enabled by UX/config
        final_image_settings = {
            "enabled": False,
            "max_size_bytes": 0,
            "allowed_mime_types": []
        }
        # Merge per-request if provided
        if isinstance(image_processing_settings, dict):
            final_image_settings.update({k: v for k, v in image_processing_settings.items() if v is not None})

        # Local start/end-of-day (inclusive) for the requested dates
        start_dt_local = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=user_tz)
        end_dt_local = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=user_tz) + timedelta(days=1, microseconds=-1)

        # UTC equivalents for API boundaries
        start_dt_utc = start_dt_local.astimezone(timezone.utc)
        end_dt_utc = end_dt_local.astimezone(timezone.utc)

        # Today boundary in local tz for cacheability
        today_local = datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_messages = []
        dates_to_fetch_from_api_local = []
        
        # Iterate local calendar days for cache keys and decisions
        current_day_local = start_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        last_day_local = end_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_day_local <= last_day_local:
            is_cacheable = current_day_local < today_local
            cache_path = self._get_cache_path(user_identifier, chat_id, current_day_local)
            
            if is_cacheable and os.path.exists(cache_path):
                logger.info(f"Cache HIT for Telegram chat {chat_id} on {current_day_local.date()}")
                with open(cache_path, 'r') as f:
                    try:
                        raw_msgs = json.load(f)
                        all_messages.extend([Message(**msg) for msg in raw_msgs])
                    except json.JSONDecodeError:
                        logger.warning(f"Cache file {cache_path} is corrupted. Re-fetching.")
                        dates_to_fetch_from_api_local.append(current_day_local)
            else:
                dates_to_fetch_from_api_local.append(current_day_local)
            
            current_day_local += timedelta(days=1)

        if dates_to_fetch_from_api_local:
            # UTC window for fetching; Telethon's offset_date expects aware dt, we pass end in UTC
            fetch_start_utc = start_dt_utc
            fetch_end_utc = end_dt_utc

            logger.info(f"Cache MISS for Telegram chat {chat_id}. Fetching local-window {start_dt_local.date()}..{end_dt_local.date()} (offset_date={fetch_end_utc.isoformat()}).")

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

                logger.info(f"Fetching messages with offset_date={fetch_end_utc.isoformat()} and reverse=False")
                async for message in client.iter_messages(target_entity, limit=500, offset_date=fetch_end_utc, reverse=False):
                    # Telethon message.date is naive in UTC; make it aware
                    msg_date_utc = message.date.replace(tzinfo=timezone.utc)

                    # Stop when older than start of requested window (UTC equivalent)
                    if msg_date_utc < fetch_start_utc:
                        logger.info(f"Message {message.id} is older than fetch_start date {fetch_start_utc.isoformat()}, stopping.")
                        break
                    
                    # if msg_date_utc > fetch_end:
                    #     logger.info(f"Message {message.id} is newer than fetch_end date {fetch_end.isoformat()}, skipping.")
                    #     continue
                    
                    #logger.info(f"Full message object: {message.to_json()}")
    
                    # Detect textual content or media; keep messages that have any user-perceivable content
                    has_text = bool(getattr(message, "message", None) or getattr(message, "text", None))
                    # Telethon exposes media on .media and convenience flags; use .media for robustness
                    has_media = bool(getattr(message, "media", None))
                    if not (has_text or has_media):
                        logger.info(f"Message {message.id} has no text or media, skipping.")
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
                    
                    reply_to_id = None
                    if message.reply_to and message.reply_to.reply_to_msg_id:
                        reply_to_id = str(message.reply_to.reply_to_msg_id)

                    # Build attachments if media present; honor image processing settings (enabled + size cap)
                    attachments: List[Attachment] = []
                    if not final_image_settings.get("enabled", False):
                        if getattr(message, "media", None):
                            logger.info("Image processing is disabled by configuration. Skipping file download.")
                    else:
                        if getattr(message, "media", None):
                            try:
                                import base64
                                from io import BytesIO
                                buf = BytesIO()
                                # Telethon writes bytes to BinaryIO when file is a stream
                                await client.download_media(message, file=buf)
                                data_bytes = buf.getvalue() or b""
                                # Enforce max size if configured (>0)
                                max_size = int(final_image_settings.get("max_size_bytes") or 0)
                                if max_size > 0 and len(data_bytes) > max_size:
                                    logger.info(f"Skipping media for message {message.id}: {len(data_bytes)} bytes exceeds cap {max_size} bytes")
                                elif len(data_bytes) > 0:
                                    # Infer MIME using magic numbers
                                    mime = "application/octet-stream"
                                    sig4 = bytes(data_bytes[:4])
                                    if sig4.startswith(b"\x89PNG"):
                                        mime = "image/png"
                                    elif sig4.startswith(b"\xFF\xD8\xFF"):
                                        mime = "image/jpeg"
                                    elif data_bytes[:6] in (b"GIF89a", b"GIF87a"):
                                        mime = "image/gif"
                                    elif data_bytes[:4] == b"RIFF" and data_bytes[8:12] == b"WEBP":
                                        mime = "image/webp"

                                    # Filter by allowed_mime_types if provided
                                    allowed = final_image_settings.get("allowed_mime_types") or []
                                    if allowed and mime not in allowed:
                                        logger.info(f"Skipping media for message {message.id}: MIME {mime} not allowed")
                                    else:
                                        encoded = base64.b64encode(data_bytes).decode("utf-8")
                                        attachments.append(Attachment(mime_type=mime, data=encoded))
                            except Exception as e:
                                logger.warning(f"Failed to process media for message {message.id}: {e}", exc_info=True)

                    newly_fetched_messages.append(Message(
                        id=str(message.id),
                        text=(getattr(message, "message", None) or getattr(message, "text", None)),
                        author=User(id=author_id, name=author_name),
                        timestamp=message.date.isoformat(),
                        thread_id=reply_to_id,  # temporary; will be replaced by resolved thread root id
                        attachments=attachments if attachments else None,
                    ))

            all_messages.extend(newly_fetched_messages)

            # Simplified caching logic when not disabled
            if enable_caching:
                # Group and cache by LOCAL day to align with UI expectations
                grouped_by_day_local = {}
                for msg in newly_fetched_messages:
                    msg_dt_aware = datetime.fromisoformat(msg.timestamp)
                    # If timestamp is naive, assume UTC (Telethon behavior), then convert
                    if msg_dt_aware.tzinfo is None:
                        msg_dt_aware = msg_dt_aware.replace(tzinfo=timezone.utc)
                    msg_dt_local = msg_dt_aware.astimezone(user_tz)
                    msg_day_local = msg_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    if msg_day_local not in grouped_by_day_local:
                        grouped_by_day_local[msg_day_local] = []
                    grouped_by_day_local[msg_day_local].append(msg)

                for day_to_cache_local in dates_to_fetch_from_api_local:
                    if day_to_cache_local < today_local:
                        messages_for_this_day = grouped_by_day_local.get(day_to_cache_local, [])
                        cache_path = self._get_cache_path(user_identifier, chat_id, day_to_cache_local)
                        with open(cache_path, 'w') as f:
                            logger.info(f"Caching {len(messages_for_this_day)} messages for {day_to_cache_local.date()} at {cache_path}")
                            json.dump([msg.model_dump() for msg in messages_for_this_day], f)

        # Resolve Telegram "threads" based on reply chains:
        # - Determine a stable thread root for each message (ultimate ancestor if available within-range).
        # - Assign thread_id = root_msg_id when root is known; otherwise synthesize a local root.
        # Build maps for resolution
        by_id: Dict[str, Message] = {m.id: m for m in all_messages}
        reply_to: Dict[str, Optional[str]] = {}
        for m in all_messages:
            reply_to[m.id] = m.thread_id if m.thread_id else None

        # Helper to walk up the chain to the earliest known ancestor within-range
        # Returns (root_id, is_local_root)
        def resolve_root(start_id: str) -> Tuple[str, bool]:
            visited = set()
            current = start_id
            last_known = start_id
            while True:
                if current in visited:
                    # cycle guard; treat current as root
                    return current, False
                visited.add(current)
                parent = reply_to.get(current)
                if not parent:
                    return current, False
                if parent not in by_id:
                    # parent outside of range; use last known as local root
                    return last_known, True
                last_known = parent
                current = parent

        # Assign resolved thread ids
        for m in all_messages:
            if m.thread_id:
                root_id, is_local = resolve_root(m.id)
                # Prefer true root id. If local, still use the resolved earliest-known id in-range.
                m.thread_id = root_id
            else:
                # Non-reply remains top-level with no thread_id
                pass

        # Group messages by thread_id (root id)
        threads: Dict[str, List[Message]] = {}
        top_level_messages: List[Message] = []

        for msg in all_messages:
            if msg.thread_id:
                parent_id = msg.thread_id
                if parent_id not in threads:
                    threads[parent_id] = []
                # Exclude the root itself from being double-added as a child if present
                if msg.id != parent_id:
                    threads[parent_id].append(msg)
                else:
                    # The root stays as a top-level message
                    top_level_messages.append(msg)
            else:
                top_level_messages.append(msg)

        # Sort messages within each thread by timestamp
        for thread_id in threads:
            threads[thread_id].sort(key=lambda m: m.timestamp)

        # Reconstruct the final list, with threaded messages following their parent root
        final_message_list: List[Message] = []

        # Sort top-level messages by timestamp to maintain overall order
        top_level_messages.sort(key=lambda m: m.timestamp)

        for top_msg in top_level_messages:
            final_message_list.append(top_msg)
            # If this top-level message is a root of a thread, append its replies
            if top_msg.id in threads:
                final_message_list.extend(threads[top_msg.id])
                del threads[top_msg.id]

        # Orphaned threads: roots outside range; place by first-reply timestamp
        sorted_orphaned_threads = sorted(threads.values(), key=lambda t: t[0].timestamp)
        for thread in sorted_orphaned_threads:
            final_message_list.extend(thread)

        logger.info(f"Returning {len(final_message_list)} messages from get_messages after threading.")
        return final_message_list

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
