from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# --- Backend-Agnostic Data Models ---
class User(BaseModel):
    id: str
    name: str

class Chat(BaseModel):
    id: str
    title: str
    type: str  # e.g., 'private', 'group'

class Message(BaseModel):
    id: str
    text: str
    author: User
    timestamp: str # ISO 8601 format
    thread_id: Optional[str] = None

# --- The Abstract Base Class ---
class ChatClient(ABC):
    """
    An abstract interface for chat service clients.
    Defines the contract for all specific client implementations.
    """

    @abstractmethod
    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiates the login process.
        - For Telegram: auth_details might be {'phone': '...'}
        - For Webex: This will return the auth URL for redirection.
        Returns a dictionary with status and required next steps.
        """
        pass

    @abstractmethod
    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Completes the login/verification process.
        - For Telegram: auth_details would be {'phone': '...', 'code': '...'}
        - For Webex: auth_details would be {'code': '...'} from OAuth callback.
        """
        pass

    @abstractmethod
    async def logout(self, user_identifier: str) -> None:
        """
        Logs the user out and cleans up the session.
        """
        pass

    @abstractmethod
    async def get_chats(self, user_identifier: str) -> List[Chat]:
        """
        Fetches a list of available chats/rooms for the user.
        """
        pass

    @abstractmethod
    async def get_messages(self, user_identifier: str, chat_id: str, start_date: str, end_date: str) -> List[Message]:
        """
        Fetches messages from a specific chat within a date range.
        """
        pass

    @abstractmethod
    async def is_session_valid(self, user_identifier: str) -> bool:
        """
        Checks if the current session for the user is still active and authorized.
        """
        pass