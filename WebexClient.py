import os
import json
from typing import List, Any, Dict

import requests
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import logging

# Assume these helpers exist and work as intended
# from config.config_values import auth_keys
# from config.wrapper import session
# from data_listeners.Room import iso_to_datetime, Room
# from utils.decorators import retry_on_failure

# For standalone demonstration, we will define placeholders
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=2):
    def decorator(func):
        # This is a placeholder for the real decorator
        return func
    return decorator

TOKEN_URL = "https://webexapis.com/v1/access_token"
ROOMS_URL = "https://webexapis.com/v1/rooms"
MESSAGES_URL = "https://webexapis.com/v1/messages"
PEOPLE_ME_URL = "https://webexapis.com/v1/people/me"
CONTEXT_MESSAGES_COUNT = int(os.getenv("CONTEXT_MESSAGES_COUNT", 2))
CONTEXT_MESSAGES_THRESHOLD = timedelta(hours=int(os.getenv("CONTEXT_MESSAGES_THRESHOLD", 2)))

class WebexClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: List[str], token_storage_path: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = " ".join(scopes)
        self.token_storage_path = token_storage_path
        self.token_data = self._load_token_data()
        self.headers = {}
        if self.token_data:
            self._update_headers()

    def _load_token_data(self) -> Dict[str, Any]:
        if os.path.exists(self.token_storage_path):
            with open(self.token_storage_path, "r") as f:
                return json.load(f)
        return {}

    def _save_token_data(self):
        # Ensure the directory exists before writing the file
        os.makedirs(os.path.dirname(self.token_storage_path), exist_ok=True)
        with open(self.token_storage_path, "w") as f:
            json.dump(self.token_data, f)

    def _update_headers(self):
        access_token = self.get_access_token()
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def get_auth_headers(self) -> Dict[str, str]:
        """Returns just the authorization headers, useful for external HTTP clients."""
        access_token = self.get_access_token()
        return {"Authorization": f"Bearer {access_token}"}

    def get_authorization_url(self) -> str:
        """Constructs the URL for the user to grant consent."""
        auth_url = "https://webexapis.com/v1/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": "set_by_client_for_security" # Recommended
        }
        # Use requests to properly encode params
        req = requests.Request('GET', auth_url, params=params)
        prep = req.prepare()
        if prep.url is None:
            raise ValueError("Failed to construct Webex authorization URL")
        return prep.url

    def _is_token_expired(self) -> bool:
        if not self.token_data:
            return True
        # Add a 5-minute buffer to be safe
        expiration_time = datetime.fromtimestamp(self.token_data.get("created_at", 0)) + \
                          timedelta(seconds=self.token_data.get("expires_in", 3600) - 300)
        return datetime.now() > expiration_time

    def get_access_token(self) -> str:
        """
        Returns a valid access token, refreshing if necessary.
        """
        if not self.token_data or "refresh_token" not in self.token_data:
            raise Exception("User not authenticated. Please initiate login.")

        if self._is_token_expired():
            logger.info("Webex access token expired. Refreshing...")
            self._refresh_token()
        
        return self.token_data["access_token"]

    def exchange_code_for_tokens(self, auth_code: str):
        """Exchanges the one-time authorization code for access and refresh tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": self.redirect_uri
        }
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status() # Will raise an exception for 4xx/5xx status
        
        new_token_data = response.json()
        new_token_data["created_at"] = datetime.now().timestamp()
        self.token_data = new_token_data
        self._save_token_data()
        self._update_headers()
        logger.info("Successfully exchanged auth code for Webex tokens.")

    def _refresh_token(self):
        """Refreshes the access token using the stored refresh token."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.token_data["refresh_token"]
        }
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()

        new_token_data = response.json()
        new_token_data["created_at"] = datetime.now().timestamp()
        # The refresh token can also be rotated, so we must update it.
        self.token_data["access_token"] = new_token_data["access_token"]
        self.token_data["refresh_token"] = new_token_data["refresh_token"]
        self.token_data["expires_in"] = new_token_data["expires_in"]
        self.token_data["created_at"] = new_token_data["created_at"]
        
        self._save_token_data()
        self._update_headers()
        logger.info("Successfully refreshed Webex access token.")

    @retry_on_failure(max_retries=3, delay=2)
    def get_rooms(self, max_rooms=200):
        self._update_headers()
        params = {"sortBy": "lastactivity", "max": max_rooms}
        response = requests.get(ROOMS_URL, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("items", [])

    @retry_on_failure(max_retries=3, delay=2)
    def get_messages(self, room_id: str, **kwargs):
        self._update_headers()
        params = {"roomId": room_id}
        params.update(kwargs)
        response = requests.get(MESSAGES_URL, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("items", [])

    @retry_on_failure(max_retries=3, delay=2)
    def get_user_details(self, user_id: str = "me"):
        self._update_headers()
        url = f"https://webexapis.com/v1/people/{user_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def revoke_token(self):
        """Revokes the current token, effectively logging out."""
        if not self.token_data.get("access_token"):
            return
            
        self._update_headers()
        data = {
            "token": self.token_data["access_token"]
        }
        response = requests.post(f"{TOKEN_URL}/revoke", data=data, auth=(self.client_id, self.client_secret))
        
        if response.status_code == 204:
            logger.info("Webex token revoked successfully.")
        else:
            logger.warning(f"Could not revoke Webex token, status: {response.status_code}, text: {response.text}")
        
        # Clear local token regardless
        self.token_data = {}
        if os.path.exists(self.token_storage_path):
            os.remove(self.token_storage_path)
