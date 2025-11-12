import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from telethon import TelegramClient as TelethonApiClient
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
async def telegram_api_client(phone: str, check_authorized: bool = True) -> AsyncGenerator[TelethonApiClient, None]:
    if not API_ID or not API_HASH:
        raise ValueError("Telegram API_ID and API_HASH must be configured in config.json")
    session_path = get_session_path(phone)
    client = TelethonApiClient(session_path, int(API_ID), API_HASH)
    try:
        await client.connect()
        if check_authorized and not await client.is_user_authorized():
            raise Exception("User not authorized (401)")
        yield client
    finally:
        if client.is_connected():
            client.disconnect()

class TelegramClient(ChatClient):

    def __init__(self):
        self.parallel_fetch_chunk_days = TELEGRAM_CONFIG.get('parallel_fetch_chunk_days', 7)
        self.max_concurrent_fetches = TELEGRAM_CONFIG.get('max_concurrent_fetches', 5)
        self.max_concurrent_media_downloads = TELEGRAM_CONFIG.get('max_concurrent_media_downloads', 20)

    def _get_cache_path(self, user_identifier: str, chat_id: str, day: datetime) -> str:
        safe_user_id = ''.join(filter(str.isalnum, user_identifier))
        safe_chat_id = ''.join(filter(str.isalnum, str(chat_id)))
        user_cache_dir = os.path.join(CACHE_DIR, safe_user_id, safe_chat_id)
        os.makedirs(user_cache_dir, exist_ok=True)
        return os.path.join(user_cache_dir, f"{day.strftime('%Y-%m-%d')}.json")

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
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

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str, enable_caching: bool = True, image_processing_settings: Optional[Dict[str, Any]] = None, timezone_str: Optional[str] = None) -> List[Message]:
        user_tz = ZoneInfo(timezone_str) if timezone_str else ZoneInfo("UTC")

        final_image_settings = {
            "enabled": False,
            "max_size_bytes": 0,
            "allowed_mime_types": []
        }
        if isinstance(image_processing_settings, dict):
            final_image_settings.update({k: v for k, v in image_processing_settings.items() if v is not None})

        start_dt_local = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=user_tz)
        end_dt_local = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=user_tz) + timedelta(days=1, microseconds=-1)

        start_dt_utc = start_dt_local.astimezone(timezone.utc)
        end_dt_utc = end_dt_local.astimezone(timezone.utc)

        today_local = datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_messages = []
        dates_to_fetch_from_api_local = []
        
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

        # Group uncached days into contiguous ranges for parallel fetching
        def group_into_contiguous_ranges(days: List[datetime], max_chunk_size: int = 7) -> List[List[datetime]]:
            """
            Group days into contiguous date ranges, splitting large ranges into chunks for parallel fetching.
            
            Args:
                days: List of datetime objects representing days to fetch
                max_chunk_size: Maximum number of days in a single chunk (default: 7)
            
            Returns:
                List of lists, where each inner list is a contiguous date range
            """
            if not days:
                return []
            
            days_sorted = sorted(days)
            ranges = []
            current_range = [days_sorted[0]]
            
            # First pass: identify contiguous ranges
            for i in range(1, len(days_sorted)):
                if (days_sorted[i] - days_sorted[i-1]).days == 1:
                    current_range.append(days_sorted[i])
                else:
                    ranges.append(current_range)
                    current_range = [days_sorted[i]]
            ranges.append(current_range)
            
            # Second pass: split large ranges into chunks for parallel fetching
            chunked_ranges = []
            for date_range in ranges:
                if len(date_range) > max_chunk_size:
                    # Split into chunks
                    for i in range(0, len(date_range), max_chunk_size):
                        chunk = date_range[i:i + max_chunk_size]
                        chunked_ranges.append(chunk)
                    logger.info(f"Split large range of {len(date_range)} days into {len(range(0, len(date_range), max_chunk_size))} chunks for parallel fetching")
                else:
                    chunked_ranges.append(date_range)
            
            return chunked_ranges

        if dates_to_fetch_from_api_local:
            # Group uncached days into contiguous ranges
            date_ranges = group_into_contiguous_ranges(dates_to_fetch_from_api_local, max_chunk_size=self.parallel_fetch_chunk_days)
            logger.info(f"Cache MISS for Telegram chat {chat_id}. Found {len(date_ranges)} date range(s) to fetch (chunk size: {self.parallel_fetch_chunk_days} days)")
            
            # Combine global config with per-request settings
            final_image_settings = image_processing_settings or {}
            
            # For Telegram, we must use a SINGLE client connection shared across all chunks
            # to avoid SQLite "database is locked" errors from concurrent session file access
            newly_fetched_messages = []
            all_fetched_ranges = []
            
            async with telegram_api_client(user_identifier) as client:
                # Helper function to fetch messages for a single date range using shared client
                async def fetch_date_range(range_days: List[datetime], shared_client):
                    range_start_local = range_days[0]
                    range_end_local = range_days[-1] + timedelta(days=1, microseconds=-1)
                    range_start_utc = range_start_local.astimezone(timezone.utc)
                    range_end_utc = range_end_local.astimezone(timezone.utc)
                    
                    logger.info(f"Fetching Telegram messages for range {range_start_local.date()} to {range_days[-1].date()}")
                    
                    range_messages = []
                    try:
                        chat_id_input = chat_id
                        if isinstance(chat_id_input, str) and chat_id_input.lstrip('-').isdigit():
                            chat_id_input = int(chat_id_input)
                    
                        from telethon.tl.types import PeerUser
                        
                        chat_id_int = int(chat_id_input)
                        target_entity = await shared_client.get_entity(PeerUser(chat_id_int))
                        if isinstance(target_entity, list):
                            target_entity = target_entity[0]

                    except Exception as e:
                        logger.error(f"Error resolving entity '{chat_id}': {e}", exc_info=True)
                        return [], range_days

                    logger.info(f"Fetching messages with offset_date={range_end_utc.isoformat()} and reverse=False")
                    
                    # First pass: collect all raw messages
                    raw_messages_to_process = []
                    async for message in shared_client.iter_messages(target_entity, limit=500, offset_date=range_end_utc, reverse=False):
                        msg_date_utc = message.date.replace(tzinfo=timezone.utc)

                        if msg_date_utc < range_start_utc:
                            logger.info(f"Message {message.id} is older than range_start date {range_start_utc.isoformat()}, stopping.")
                            break
                        
                        has_text = bool(getattr(message, "message", None) or getattr(message, "text", None))
                        has_media = bool(getattr(message, "media", None))
                        if not (has_text or has_media):
                            logger.info(f"Message {message.id} has no text or media, skipping.")
                            continue
        
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
                        
                        raw_messages_to_process.append({
                            'message': message,
                            'author_name': author_name,
                            'author_id': author_id,
                            'reply_to_id': reply_to_id,
                            'has_media': has_media
                        })
                    
                    # Second pass: download all media in parallel
                    async def download_message_media(msg_info):
                        """Download media for a single message"""
                        message = msg_info['message']
                        if not msg_info['has_media'] or not final_image_settings.get("enabled", False):
                            return []
                        
                        try:
                            import base64
                            from io import BytesIO
                            buf = BytesIO()
                            await shared_client.download_media(message, file=buf)
                            data_bytes = buf.getvalue() or b""
                            max_size = int(final_image_settings.get("max_size_bytes") or 0)
                            if max_size > 0 and len(data_bytes) > max_size:
                                logger.info(f"Skipping media for message {message.id}: {len(data_bytes)} bytes exceeds cap {max_size} bytes")
                                return []
                            elif len(data_bytes) > 0:
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

                                allowed = final_image_settings.get("allowed_mime_types") or []
                                if allowed and mime not in allowed:
                                    logger.info(f"Skipping media for message {message.id}: MIME {mime} not allowed")
                                    return []
                                else:
                                    encoded = base64.b64encode(data_bytes).decode("utf-8")
                                    return [Attachment(mime_type=mime, data=encoded)]
                            return []
                        except Exception as e:
                            logger.warning(f"Failed to process media for message {message.id}: {e}", exc_info=True)
                            return []
                    
                    # Download all media with concurrency control to prevent connection pool exhaustion
                    if raw_messages_to_process:
                        logger.info(f"Downloading media for {len(raw_messages_to_process)} messages with max {self.max_concurrent_media_downloads} concurrent downloads")
                        
                        # Create semaphore to limit concurrent media downloads
                        semaphore = asyncio.Semaphore(self.max_concurrent_media_downloads)
                        
                        async def download_with_limit(msg_info):
                            """Download media for a single message with semaphore-based rate limiting."""
                            async with semaphore:
                                return await download_message_media(msg_info)
                        
                        media_results = await asyncio.gather(
                            *[download_with_limit(msg_info) for msg_info in raw_messages_to_process],
                            return_exceptions=True
                        )
                    else:
                        media_results = []
                    
                    # Third pass: create Message objects with downloaded media
                    for idx, msg_info in enumerate(raw_messages_to_process):
                        message = msg_info['message']
                        attachments = media_results[idx] if idx < len(media_results) and not isinstance(media_results[idx], Exception) else []
                        
                        range_messages.append(Message(
                            id=str(message.id),
                            text=(getattr(message, "message", None) or getattr(message, "text", None)),
                            author=User(id=msg_info['author_id'], name=msg_info['author_name']),
                            timestamp=message.date.isoformat(),
                            thread_id=msg_info['reply_to_id'],
                            attachments=attachments if attachments else None,
                        ))
                
                    logger.info(f"Fetched {len(range_messages)} messages for range {range_start_local.date()} to {range_days[-1].date()}")
                    return range_messages, range_days
                
                # Resolve entity once (outside the parallel loop to avoid conflicts)
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
                
                # Fetch all date ranges in parallel using the shared client with concurrency limit
                # The shared client prevents SQLite locking issues while still allowing parallel API calls
                if len(date_ranges) > 1:
                    logger.info(f"Fetching {len(date_ranges)} date range(s) with max {self.max_concurrent_fetches} concurrent requests (shared client)")
                    
                    # Use a semaphore to limit concurrency
                    semaphore = asyncio.Semaphore(self.max_concurrent_fetches)
                    
                    async def fetch_with_limit(range_days):
                        async with semaphore:
                            return await fetch_date_range(range_days, client)
                    
                    fetch_results = await asyncio.gather(*[fetch_with_limit(range_days) for range_days in date_ranges], return_exceptions=True)
                else:
                    # Single small range, no need for parallelization overhead
                    logger.info(f"Fetching single date range of {len(date_ranges[0])} days")
                    fetch_results = [await fetch_date_range(date_ranges[0], client)]
                
                # Combine results and deduplicate
                seen_message_ids = set()
                for result in fetch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error fetching date range: {result}")
                        continue
                    messages, range_days = result
                    
                    # Deduplicate messages by ID
                    for msg in messages:
                        if msg.id not in seen_message_ids:
                            newly_fetched_messages.append(msg)
                            seen_message_ids.add(msg.id)
                    
                    all_fetched_ranges.extend(range_days)
                
                logger.info(f"After processing {len(date_ranges)} range(s): {len(newly_fetched_messages)} unique messages")

            all_messages.extend(newly_fetched_messages)

            if enable_caching:
                grouped_by_day_local = {}
                for msg in newly_fetched_messages:
                    msg_dt_aware = datetime.fromisoformat(msg.timestamp)
                    if msg_dt_aware.tzinfo is None:
                        msg_dt_aware = msg_dt_aware.replace(tzinfo=timezone.utc)
                    msg_dt_local = msg_dt_aware.astimezone(user_tz)
                    msg_day_local = msg_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    if msg_day_local not in grouped_by_day_local:
                        grouped_by_day_local[msg_day_local] = []
                    grouped_by_day_local[msg_day_local].append(msg)

                for day_to_cache_local in all_fetched_ranges:
                    if day_to_cache_local < today_local:
                        messages_for_this_day = grouped_by_day_local.get(day_to_cache_local, [])
                        cache_path = self._get_cache_path(user_identifier, chat_id, day_to_cache_local)
                        with open(cache_path, 'w') as f:
                            logger.info(f"Caching {len(messages_for_this_day)} messages for {day_to_cache_local.date()} at {cache_path}")
                            json.dump([msg.model_dump() for msg in messages_for_this_day], f)

        by_id: Dict[str, Message] = {m.id: m for m in all_messages}
        reply_to: Dict[str, Optional[str]] = {}
        for m in all_messages:
            reply_to[m.id] = m.thread_id if m.thread_id else None

        def resolve_root(start_id: str) -> Tuple[str, bool]:
            visited = set()
            current = start_id
            last_known = start_id
            while True:
                if current in visited:
                    return current, False
                visited.add(current)
                parent = reply_to.get(current)
                if not parent:
                    return current, False
                if parent not in by_id:
                    return last_known, True
                last_known = parent
                current = parent

        for m in all_messages:
            if m.thread_id:
                root_id, is_local = resolve_root(m.id)
                m.thread_id = root_id
            else:
                pass

        threads: Dict[str, List[Message]] = {}
        top_level_messages: List[Message] = []

        for msg in all_messages:
            if msg.thread_id:
                parent_id = msg.thread_id
                if parent_id not in threads:
                    threads[parent_id] = []
                if msg.id != parent_id:
                    threads[parent_id].append(msg)
                else:
                    top_level_messages.append(msg)
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

        sorted_orphaned_threads = sorted(threads.values(), key=lambda t: t[0].timestamp)
        for thread in sorted_orphaned_threads:
            final_message_list.extend(thread)

        logger.info(f"Returning {len(final_message_list)} messages from get_messages after threading.")
        return final_message_list

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
