import json
import os
import pytest
from fastapi import HTTPException
from unittest.mock import mock_open, patch

from services import auth_service

@pytest.fixture(autouse=True)
def clear_sessions():
    """Fixture to clear session_tokens before and after each test."""
    auth_service.session_tokens = {}
    yield
    auth_service.session_tokens = {}

class TestAuthService:

    def test_create_session(self, mocker):
        """Test that a session is created and saved."""
        mocker.patch('services.auth_service.save_app_sessions')
        user_id = "test_user"
        backend = "test_backend"
        token = auth_service.create_session(user_id, backend)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 10

        session_data = auth_service.get_session_data(token)
        assert session_data is not None
        assert session_data["user_id"] == user_id
        assert session_data["backend"] == backend
        auth_service.save_app_sessions.assert_called_once()

    def test_get_session_data(self):
        """Test retrieving session data for a valid token."""
        token = "test_token"
        data = {"user_id": "test_user", "backend": "test_backend"}
        auth_service.session_tokens[token] = data
        
        retrieved_data = auth_service.get_session_data(token)
        assert retrieved_data == data

    def test_get_session_data_invalid_token(self):
        """Test retrieving session data for an invalid token."""
        retrieved_data = auth_service.get_session_data("invalid_token")
        assert retrieved_data is None

    def test_get_token_for_user(self):
        """Test retrieving a token for a given user_id and backend."""
        user_id = "test_user"
        backend = "test_backend"
        token = "test_token"
        auth_service.session_tokens[token] = {"user_id": user_id, "backend": backend}

        retrieved_token = auth_service.get_token_for_user(user_id, backend)
        assert retrieved_token == token

    def test_get_token_for_user_not_found(self):
        """Test retrieving a token for a user that does not exist."""
        retrieved_token = auth_service.get_token_for_user("non_existent_user", "backend")
        assert retrieved_token is None

    def test_delete_session_by_token(self, mocker):
        """Test that a session is correctly deleted by its token."""
        mocker.patch('services.auth_service.save_app_sessions')
        token = "test_token_to_delete"
        auth_service.session_tokens[token] = {"user_id": "user", "backend": "backend"}

        auth_service.delete_session_by_token(token)
        assert token not in auth_service.session_tokens
        auth_service.save_app_sessions.assert_called_once()

    def test_save_app_sessions(self):
        """Test that sessions are correctly written to a file."""
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("os.makedirs") as mock_makedirs:
            
            auth_service.session_tokens = {"test_token": {"user_id": "test_user"}}
            auth_service.save_app_sessions()

            mock_makedirs.assert_called_once_with(os.path.dirname(auth_service.SESSIONS_FILE), exist_ok=True)
            mock_file.assert_called_once_with(auth_service.SESSIONS_FILE, "w")
            
            # Instead of checking write calls, check the final content
            mock_file().write.assert_called()
            written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
            assert json.loads(written_content) == auth_service.session_tokens

    def test_load_app_sessions_file_exists(self):
        """Test loading sessions from an existing file."""
        mock_data = json.dumps({"test_token": {"user_id": "test_user"}})
        with patch("builtins.open", mock_open(read_data=mock_data)) as mock_file, \
             patch("os.path.exists", return_value=True):
            
            auth_service.load_app_sessions()
            assert auth_service.session_tokens == json.loads(mock_data)

    def test_load_app_sessions_file_not_found(self):
        """Test that sessions are empty when the session file is not found."""
        with patch("os.path.exists", return_value=False):
            auth_service.load_app_sessions()
            assert auth_service.session_tokens == {}

    def test_load_app_sessions_json_error(self, caplog):
        """Test handling of JSON decoding errors when loading sessions."""
        with patch("builtins.open", mock_open(read_data="invalid json")), \
             patch("os.path.exists", return_value=True):
            
            auth_service.load_app_sessions()
            assert auth_service.session_tokens == {}
            assert "Failed to load app sessions" in caplog.text

@pytest.mark.asyncio
async def test_get_current_user_id_success():
    """Test the dependency for a valid bearer token."""
    token = "valid_token"
    user_id = "test_user"
    auth_service.session_tokens[token] = {"user_id": user_id, "backend": "test"}
    
    authorization = f"Bearer {token}"
    retrieved_user_id = await auth_service.get_current_user_id(authorization)
    assert retrieved_user_id == user_id

@pytest.mark.asyncio
async def test_get_current_user_id_invalid_scheme():
    """Test the dependency for an invalid authorization scheme."""
    with pytest.raises(HTTPException) as excinfo:
        await auth_service.get_current_user_id("Basic some_token")
    assert excinfo.value.status_code == 401
    assert "Invalid authorization scheme" in excinfo.value.detail

@pytest.mark.asyncio
async def test_get_current_user_id_invalid_token():
    """Test the dependency for an invalid or expired token."""
    with pytest.raises(HTTPException) as excinfo:
        await auth_service.get_current_user_id("Bearer invalid_token")
    assert excinfo.value.status_code == 401
    assert "Invalid or expired token" in excinfo.value.detail