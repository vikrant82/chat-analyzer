import os
import json
import logging
import secrets
from typing import Dict, Optional
from fastapi import HTTPException, Header

logger = logging.getLogger(__name__)

session_tokens: Dict[str, Dict[str, str]] = {}
SESSIONS_FILE = "sessions/app_sessions.json"

def save_app_sessions():
    """Saves the current session_tokens dictionary to the file system."""
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(session_tokens, f)

def load_app_sessions():
    """Loads session_tokens from the file system if the file exists."""
    global session_tokens
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                session_tokens = json.load(f)
            logger.info(f"Successfully loaded {len(session_tokens)} app sessions.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load app sessions from {SESSIONS_FILE}: {e}")
            session_tokens = {}
    else:
        logger.info("No app session file found. Starting with empty sessions.")
        session_tokens = {}

def create_session(user_id: str, backend: str) -> str:
    """Creates a new session token for a user."""
    token = secrets.token_urlsafe(32)
    session_tokens[token] = {"user_id": user_id, "backend": backend}
    save_app_sessions()
    return token

def get_session_data(token: str) -> Optional[Dict[str, str]]:
    """Gets session data for a given token."""
    return session_tokens.get(token)

def get_token_for_user(user_id: str) -> Optional[str]:
    """Gets a token for a given user_id."""
    for token, data in session_tokens.items():
        if data.get("user_id") == user_id:
            return token
    return None

def delete_session_by_token(token: str):
    """Deletes a session by token."""
    if token in session_tokens:
        del session_tokens[token]
        save_app_sessions()

def get_all_active_sessions() -> Dict[str, Dict[str, str]]:
    """Returns the entire dictionary of active sessions."""
    return session_tokens

async def get_current_user_id(authorization: str = Header(...)) -> str:
    """
    Dependency that handles unified token-based authentication.
    """
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme.")
    
    session_data = get_session_data(token)
    if not session_data or "user_id" not in session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return session_data["user_id"]