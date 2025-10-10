import os
import base64
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from .base_client import ChatClient, Chat, Message, User, Attachment
from .webex_api_client import WebexClient as WebexApiClient
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


class WebexClient(ChatClient):
    def __init__(self):
        client_id = WEBEX_CONFIG.get('client_id')
        client_secret = WEBEX_CONFIG.get('client_secret')
        redirect_uri = WEBEX_CONFIG.get('redirect_uri')

        if client_id is None or client_secret is None or redirect_uri is None:
            raise ValueError("Webex client_id, client_secret, and redirect_uri must be set in config.json")

        self.api = WebexApiClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=WEBEX_CONFIG.get('scopes', []),
            token_storage_path=TOKEN_STORAGE_PATH
        )
        self.http_client = httpx.AsyncClient()
        self.image_processing_config = WEBEX_CONFIG.get('image_processing', {})
        self.parallel_fetch_chunk_days = WEBEX_CONFIG.get('parallel_fetch_chunk_days', 7)
        self.max_concurrent_fetches = WEBEX_CONFIG.get('max_concurrent_fetches', 5)


    async def _download_and_encode_file(self, file_url: str, settings: Dict[str, Any]) -> Optional[Attachment]:
        """
        Downloads a file from a URL, applying filtering based on settings,
        and returns it as a Base64 encoded string.
        """
        if not settings.get('enabled', False):
            logger.info("Image processing is disabled by configuration. Skipping file download.")
            return None

        try:
            headers = self.api.get_auth_headers()

            # Use a HEAD request to check file metadata before downloading content
            async with httpx.AsyncClient() as client:
                head_response = await client.head(file_url, headers=headers)
                head_response.raise_for_status()

            content_type = head_response.headers.get('Content-Type', 'application/octet-stream')
            content_length = int(head_response.headers.get('Content-Length', 0))

            # 1. Check MIME type against allowed list
            allowed_mime_types = settings.get('allowed_mime_types', [])
            if allowed_mime_types and content_type not in allowed_mime_types:
                logger.info(f"Skipping file of type '{content_type}' as it is not in the allowed list.")
                return None

            # 2. Check file size against the maximum
            max_size_bytes = settings.get('max_size_bytes', 0)
            if max_size_bytes > 0 and content_length > max_size_bytes:
                logger.info(f"Skipping file of size {content_length} bytes as it exceeds the max size of {max_size_bytes} bytes.")
                return None

            # If all checks pass, proceed with downloading the actual file content
            response = await self.http_client.get(file_url, headers=headers)
            response.raise_for_status()

            encoded_data = base64.b64encode(response.content).decode('utf-8')
            return Attachment(mime_type=content_type, data=encoded_data)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while fetching file from {file_url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing file {file_url}: {e}", exc_info=True)
            return None

    def _get_cache_path(self, user_identifier: str, chat_id: str, day: datetime) -> str:
        safe_user_id = ''.join(filter(str.isalnum, user_identifier))
        safe_chat_id = ''.join(filter(str.isalnum, str(chat_id)))
        user_cache_dir = os.path.join(CACHE_DIR, safe_user_id, safe_chat_id)
        os.makedirs(user_cache_dir, exist_ok=True)
        return os.path.join(user_cache_dir, f"{day.strftime('%Y-%m-%d')}.json")

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        auth_url = self.api.get_authorization_url()
        return {"status": "redirect_required", "url": auth_url}

    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
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
        try:
            self.api.revoke_token()
        except Exception as e:
            logger.error(f"Error during Webex token revocation: {e}", exc_info=True)

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        raw_rooms = self.api.get_rooms()
        chats = [
            Chat(
                id=room['id'],
                title=room['title'],
                type='group' if room['type'] == 'group' else 'private'
            ) for room in raw_rooms
        ]
        return chats

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str, enable_caching: bool = True, image_processing_settings: Optional[Dict[str, Any]] = None, timezone_str: Optional[str] = None) -> List[Message]:
        # Determine user's timezone for local-day semantics
        user_tz = ZoneInfo(timezone_str) if timezone_str else ZoneInfo("UTC")

        # Parse requested dates as local (user timezone) start/end of day
        start_dt_local = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=user_tz)
        # inclusive local end-of-day
        end_dt_local = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=user_tz) + timedelta(days=1, microseconds=-1)

        # Also compute UTC equivalents for pagination/window checks if needed later
        start_dt_utc = start_dt_local.astimezone(timezone.utc)
        end_dt_utc = end_dt_local.astimezone(timezone.utc)

        # Today boundary in user's local timezone (midnight local)
        today_local = datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        all_messages = []
        dates_to_fetch_from_api_local = []

        # Iterate days by local calendar days
        current_day_local = start_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        last_day_local = end_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_day_local <= last_day_local:
            is_cacheable = current_day_local < today_local
            cache_path = self._get_cache_path(user_identifier, chat_id, current_day_local)
            
            if enable_caching and is_cacheable and os.path.exists(cache_path):
                logger.info(f"Cache HIT for Webex chat {chat_id} on {current_day_local.date()}")
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
            # Combine global config with per-request settings
            final_image_settings = self.image_processing_config.copy()
            if image_processing_settings:
                final_image_settings.update(image_processing_settings)
            logger.info(f"Image processing settings for this request: {final_image_settings}")

            # Group uncached days into contiguous ranges
            date_ranges = group_into_contiguous_ranges(dates_to_fetch_from_api_local, max_chunk_size=self.parallel_fetch_chunk_days)
            logger.info(f"Cache MISS for Webex chat {chat_id}. Found {len(date_ranges)} date range(s) to fetch (chunk size: {self.parallel_fetch_chunk_days} days)")
            
            # Helper function to fetch messages for a single date range
            async def fetch_date_range(range_days: List[datetime]):
                range_start_local = range_days[0]
                range_end_local = range_days[-1] + timedelta(days=1, microseconds=-1)
                range_start_utc = range_start_local.astimezone(timezone.utc)
                range_end_utc = range_end_local.astimezone(timezone.utc)
                
                logger.info(f"Fetching Webex messages for range {range_start_local.date()} to {range_days[-1].date()}")
                
                range_messages = []
                # Initialize to the end of this specific chunk range
                oldest_message_dt_utc = range_end_utc
                params = {"room_id": chat_id, "max": 1000}
                
                # Always set 'before' to start fetching from the end of this chunk's range
                # This ensures each chunk only fetches its own time window
                params['before'] = range_end_utc.isoformat().replace('+00:00', 'Z')
                
                batch_count = 0
                messages_in_range = 0
                while oldest_message_dt_utc > range_start_utc:
                    batch_count += 1
                    try:
                        # Wrap synchronous API call in to_thread for true async parallelism
                        raw_batch = await asyncio.to_thread(self.api.get_messages, **params)
                    except Exception as e:
                        logger.error(f"Failed to fetch message batch #{batch_count} for range {range_start_local.date()}-{range_days[-1].date()}: {e}", exc_info=True)
                        break
                    
                    if not raw_batch:
                        logger.info(f"Range {range_start_local.date()}-{range_days[-1].date()}: No messages in batch #{batch_count}, stopping pagination")
                        break
                    
                    # Filter messages to only include those within this chunk's date range
                    batch_in_range = []
                    for msg in raw_batch:
                        msg_dt = datetime.fromisoformat(msg['created'].replace('Z', '+00:00'))
                        if range_start_utc <= msg_dt <= range_end_utc:
                            batch_in_range.append(msg)
                    
                    messages_in_range += len(batch_in_range)
                    range_messages.extend(batch_in_range)
                    
                    oldest_message_in_batch_raw = raw_batch[-1]
                    oldest_message_dt_utc = datetime.fromisoformat(oldest_message_in_batch_raw['created'].replace('Z', '+00:00'))
                    
                    logger.info(f"Range {range_start_local.date()}-{range_days[-1].date()}: Batch #{batch_count} received {len(raw_batch)} messages ({len(batch_in_range)} in range), oldest={raw_batch[-1]['created']}")
                    
                    params['before'] = oldest_message_in_batch_raw['created']
                    
                    # Stop if we got a partial batch OR if we've gone past the range start
                    if len(raw_batch) < 1000 or oldest_message_dt_utc <= range_start_utc:
                        logger.info(f"Range {range_start_local.date()}-{range_days[-1].date()}: Stopping pagination (batch_size={len(raw_batch)}, past_range_start={oldest_message_dt_utc <= range_start_utc})")
                        break
                
                logger.info(f"Range {range_start_local.date()}-{range_days[-1].date()}: Total {len(range_messages)} raw messages fetched in {batch_count} batch(es)")
                return range_messages, range_days
            
            # Fetch all date ranges in parallel with concurrency limit
            if len(date_ranges) > 1:
                logger.info(f"Fetching {len(date_ranges)} date range(s) with max {self.max_concurrent_fetches} concurrent requests")
                
                # Use a semaphore to limit concurrency
                semaphore = asyncio.Semaphore(self.max_concurrent_fetches)
                
                async def fetch_with_limit(range_days):
                    async with semaphore:
                        return await fetch_date_range(range_days)
                
                fetch_results = await asyncio.gather(*[fetch_with_limit(range_days) for range_days in date_ranges], return_exceptions=True)
            else:
                # Single small range, no need for parallelization overhead
                logger.info(f"Fetching single date range of {len(date_ranges[0])} days")
                fetch_results = [await fetch_date_range(date_ranges[0])]
            
            # Combine all fetched messages and their associated date ranges
            all_fetched_raw_messages = []
            all_fetched_ranges = []
            seen_message_ids = set()  # Deduplicate messages across chunks
            
            for result in fetch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching date range: {result}")
                    continue
                messages, range_days = result
                
                # Deduplicate messages by ID
                for msg in messages:
                    msg_id = msg.get('id')
                    if msg_id and msg_id not in seen_message_ids:
                        all_fetched_raw_messages.append(msg)
                        seen_message_ids.add(msg_id)
                
                all_fetched_ranges.extend(range_days)
            
            logger.info(f"After deduplication: {len(all_fetched_raw_messages)} unique messages from {len(seen_message_ids)} total fetched")

            # Group by LOCAL day
            grouped_by_day_local: Dict[datetime, List[Message]] = {}
            
            # --- Optimization ---
            # Get all message IDs that were successfully loaded from the daily caches.
            # We will use this to avoid re-processing and re-downloading attachments
            # for messages we already have.
            existing_ids_from_cache = {m.id for m in all_messages}

            # First pass: collect all messages that need processing and their file URLs
            messages_to_process = []
            for msg_raw in all_fetched_raw_messages:
                # If this message was already loaded from a daily cache, skip it.
                if msg_raw.get('id') in existing_ids_from_cache:
                    continue

                # A message must have text OR files to be considered
                if not msg_raw.get('text') and not msg_raw.get('files'):
                    continue
                
                # Parse as aware UTC, convert to user's timezone
                msg_dt_utc = datetime.fromisoformat(msg_raw['created'].replace('Z', '+00:00'))
                msg_dt_local = msg_dt_utc.astimezone(user_tz)
                msg_day_local = msg_dt_local.replace(hour=0, minute=0, second=0, microsecond=0)

                # Filter by local window
                if start_dt_local <= msg_dt_local <= end_dt_local:
                    messages_to_process.append({
                        'raw': msg_raw,
                        'day_local': msg_day_local,
                        'file_urls': msg_raw.get('files', [])
                    })

            # Second pass: download all files in parallel
            logger.info(f"Downloading files for {len(messages_to_process)} messages in parallel")
            all_download_tasks = []
            task_to_msg_index = {}
            
            for idx, msg_info in enumerate(messages_to_process):
                for file_url in msg_info['file_urls']:
                    task = self._download_and_encode_file(file_url, final_image_settings)
                    all_download_tasks.append(task)
                    task_to_msg_index[len(all_download_tasks) - 1] = (idx, file_url)
            
            # Download all files concurrently
            if all_download_tasks:
                logger.info(f"Starting parallel download of {len(all_download_tasks)} files")
                download_results = await asyncio.gather(*all_download_tasks, return_exceptions=True)
                
                # Map results back to messages
                msg_attachments = {idx: [] for idx in range(len(messages_to_process))}
                for task_idx, result in enumerate(download_results):
                    if task_idx in task_to_msg_index:
                        msg_idx, file_url = task_to_msg_index[task_idx]
                        if isinstance(result, Exception):
                            logger.error(f"Error downloading file {file_url}: {result}")
                        elif result is not None:
                            msg_attachments[msg_idx].append(result)
            else:
                msg_attachments = {}

            # Third pass: create Message objects with downloaded attachments
            for idx, msg_info in enumerate(messages_to_process):
                msg_raw = msg_info['raw']
                msg_day_local = msg_info['day_local']
                attachments = msg_attachments.get(idx, [])
                
                if msg_day_local not in grouped_by_day_local:
                    grouped_by_day_local[msg_day_local] = []
                
                # Only create a message if it has text or a successfully processed attachment
                if msg_raw.get('text') or attachments:
                    author = User(id=msg_raw.get('personId', 'unknown'), name=msg_raw.get('personEmail', 'Unknown User'))
                    message = Message(
                        id=msg_raw['id'],
                        text=msg_raw.get('text'),
                        author=author,
                        timestamp=msg_raw['created'],
                        thread_id=msg_raw.get('parentId'),
                        attachments=attachments if attachments else None
                    )
                    grouped_by_day_local[msg_day_local].append(message)

            # Cache messages for each fetched day
            for day_to_cache_local in all_fetched_ranges:
                messages_for_this_day = grouped_by_day_local.get(day_to_cache_local, [])
                
                all_messages.extend(messages_for_this_day)
                
                if day_to_cache_local < today_local and enable_caching:
                    cache_path = self._get_cache_path(user_identifier, chat_id, day_to_cache_local)
                    with open(cache_path, 'w') as f:
                        logger.info(f"Caching {len(messages_for_this_day)} messages for Webex on {day_to_cache_local.date()} at {cache_path}")
                        json.dump([msg.model_dump() for msg in messages_for_this_day], f)

        # Group messages by thread_id
        threads: Dict[str, List[Message]] = {}
        top_level_messages: List[Message] = []

        for msg in all_messages:
            if msg.thread_id:
                if msg.thread_id not in threads:
                    threads[msg.thread_id] = []
                threads[msg.thread_id].append(msg)
            else:
                # This is a top-level message
                top_level_messages.append(msg)
        
        # Sort messages within each thread
        for thread_id in threads:
            threads[thread_id].sort(key=lambda m: m.timestamp)

        # Reconstruct the final list, with threaded messages following their parent
        final_message_list: List[Message] = []
        
        # Sort top-level messages by timestamp to maintain overall order
        top_level_messages.sort(key=lambda m: m.timestamp)

        for top_msg in top_level_messages:
            final_message_list.append(top_msg)
            # If this top-level message has a thread, append it
            if top_msg.id in threads:
                final_message_list.extend(threads[top_msg.id])
                # Remove the thread once it's been added
                del threads[top_msg.id]

        # Add any remaining threads that might have been orphaned (optional, but good practice)
        for thread_id in sorted(threads.keys()):
             final_message_list.extend(threads[thread_id])

        return final_message_list

    async def is_session_valid(self, user_identifier: str) -> bool:
        try:
            self.api.get_user_details()
            return True
        except Exception:
            return False
