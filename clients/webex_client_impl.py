import os
import base64
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_client import ChatClient, Chat, Message, User, Attachment
from WebexClient import WebexClient
import logging
from config import settings

logger = logging.getLogger(__name__)

# --- Configuration ---
WEBEX_CONFIG = settings.get_webex_config()

# --- Directory Setup ---
SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)
TOKEN_STORAGE_PATH = os.path.join(SESSION_DIR, 'webex_tokens.json')


class WebexClientImpl(ChatClient):
    def __init__(self):
        client_id = WEBEX_CONFIG.get('client_id')
        client_secret = WEBEX_CONFIG.get('client_secret')
        redirect_uri = WEBEX_CONFIG.get('redirect_uri')

        if not all([client_id, client_secret, redirect_uri]):
            raise ValueError("Webex client_id, client_secret, and redirect_uri must be set in config.json")

        self.api = WebexClient(
            client_id=str(client_id),
            client_secret=str(client_secret),
            redirect_uri=str(redirect_uri),
            scopes=WEBEX_CONFIG.get('scopes', []),
            token_storage_path=TOKEN_STORAGE_PATH
        )
        self.http_client = httpx.AsyncClient()
        self.image_processing_config = WEBEX_CONFIG.get('image_processing', {})


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
            logger.error(f"Error during Webex token revocation for user {user_identifier}: {e}", exc_info=True)

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        raw_rooms = self.api.get_rooms()
        return [
            Chat(
                id=room['id'],
                title=room['title'],
                type='group' if room['type'] == 'group' else 'private'
            ) for room in raw_rooms
        ]

    async def fetch_messages_from_api(
        self,
        user_identifier: str,
        chat_id: str,
        start_date: datetime,
        end_date: datetime,
        image_processing_settings: Optional[Dict[str, Any]] = None,
    ) -> List[Message]:
        
        logger.info(f"Fetching Webex messages for room {chat_id} from API.")
        
        all_raw_messages = []
        params = {"roomId": chat_id, "max": 1000}
        
        while True:
            try:
                raw_batch = self.api.get_messages(**params)
                if not raw_batch:
                    break
                all_raw_messages.extend(raw_batch)
                
                # Pagination logic
                oldest_message_dt = datetime.fromisoformat(raw_batch[-1]['created'].replace('Z', '+00:00'))
                if oldest_message_dt < start_date:
                    break # We've gone back far enough
                
                params['before'] = raw_batch[-1]['created']

            except Exception as e:
                logger.error(f"Failed to fetch message batch for Webex room {chat_id}: {e}", exc_info=True)
                break

        # Process the raw messages
        messages = []
        final_image_settings = self.image_processing_config.copy()
        if image_processing_settings:
            final_image_settings.update(image_processing_settings)

        for msg_raw in all_raw_messages:
            msg_dt = datetime.fromisoformat(msg_raw['created'].replace('Z', '+00:00'))
            if not (start_date <= msg_dt <= end_date):
                continue

            if not msg_raw.get('text') and not msg_raw.get('files'):
                continue

            attachments = []
            if msg_raw.get('files'):
                for file_url in msg_raw['files']:
                    attachment = await self._download_and_encode_file(file_url, final_image_settings)
                    if attachment:
                        attachments.append(attachment)

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
                messages.append(message)
                
        return messages

    async def is_session_valid(self, user_identifier: str) -> bool:
        try:
            # A simple check to see if we can get user details
            self.api.get_user_details()
            return True
        except Exception:
            return False
