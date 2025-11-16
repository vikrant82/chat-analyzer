# Testing Information

## Current Test Coverage: ~5-10% (Minimal)

### Test Infrastructure

**Framework**: pytest
**Configuration**: `pytest.ini`
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v -s
```

**Dependencies**:
- `pytest` - Test framework
- `pytest-mock` - Mocking support
- `pytest-asyncio` - Async test support
- `respx` - HTTP mocking for async requests

### Existing Tests

#### `tests/services/test_auth_service.py` (10 tests) ✅
**Coverage**: auth_service.py - ~90%

**Tests**:
- `test_create_session` - Session creation with token generation
- `test_get_session_data` - Valid session retrieval
- `test_get_session_data_invalid_token` - Invalid token handling
- `test_get_token_for_user` - Token lookup by user/backend
- `test_get_token_for_user_not_found` - Missing token handling
- `test_delete_session_by_token` - Session deletion
- `test_save_app_sessions` - Session persistence to JSON
- `test_load_app_sessions_file_exists` - Session loading
- `test_load_app_sessions_file_not_found` - Missing file handling
- `test_load_app_sessions_json_error` - Corrupted file handling

**Pattern**: Uses pytest fixtures, mocks file I/O operations

#### `tests/services/test_chat_service.py` (7 tests) ✅
**Coverage**: chat_service.py - ~30% (formatting functions only)

**Test Classes**:
1. **`TestChatServiceFormatting`** (4 tests)
   - `test_format_flat_conversation` - Non-threaded message formatting
   - `test_format_threaded_conversation` - Threaded message formatting with indentation
   - `test_format_messages_with_attachments_multimodal` - Image handling for multimodal LLMs
   - `test_format_messages_with_attachments_non_multimodal` - Image skipping for text-only LLMs

2. **`TestProcessChatRequest`** (3 tests)
   - `test_process_chat_request_cache_hit` - Cached message retrieval
   - `test_process_chat_request_cache_miss` - Fresh message fetching and LLM streaming
   - `test_process_chat_request_no_messages` - Empty result handling

**Pattern**: Uses pytest-asyncio, mocks LLM streaming, respx for HTTP mocking

### Test Gaps (Not Tested)

#### Clients (0% coverage) ❌
**Critical Missing Tests**:
- `TelegramClient`
  - Thread reconstruction via reply chain resolution (CRITICAL - complex logic)
  - Parallel date range fetching with shared client
  - Parallel media downloads
  - Session management
  - Cache hit/miss logic
  
- `WebexClient`
  - Parallel date range fetching with asyncio.to_thread
  - OAuth token refresh flow
  - Parallel image downloads
  - Thread grouping by parentId
  - Cache deduplication across chunks

- `RedditClient`
  - Comment tree recursive processing
  - Subreddit sorting (alphabetical, subscribers, activity)
  - Favorites fetching and display
  - Image fetching from submissions and text
  - Post sorting with time filters

- `TelegramBotClient`
  - Webhook setup
  - Message sending
  - Bot info retrieval

- `WebexBotClient`
  - Webhook creation
  - Message posting with threading
  - Room message fetching

- `WebexApiClient`
  - Token expiration detection
  - Token refresh
  - OAuth code exchange
  - Token revocation

#### Routers (0% coverage) ❌
**No API endpoint tests**:
- `auth.py` - Login, verify, logout, OAuth callbacks
- `chat.py` - Chat listing, chat request with streaming
- `reddit.py` - Subreddit posts fetching
- `bots.py` - Bot registration, listing, deletion, webhooks
- `downloads.py` - File generation endpoints

#### Services (Partial ~30% coverage) ⚠️
- ✅ `auth_service.py` - Well tested (90%)
- ⚠️ `chat_service.py` - Partially tested (30% - only formatting)
- ❌ `bot_service.py` - Not tested
  - Webhook event processing
  - Bot chat mode state management (/aimode)
  - Response generation
- ❌ `download_service.py` - Not tested
  - TXT generation
  - PDF generation with embedded images
  - HTML generation with inline images
  - ZIP bundle creation with manifest
- ❌ `reddit_service.py` - Not tested
  - Business logic orchestration

#### LLM Layer (0% coverage) ❌
- `llm_client.py`
  - LLMManager initialization
  - Model discovery
  - Provider orchestration
  - Multimodal support detection

- `google_ai_llm.py`
  - Model initialization
  - Message format conversion
  - Streaming response handling
  - Error handling (safety blocks, API errors)
  - Session cleanup

- `openai_compatible_llm.py`
  - Model discovery from /v1/models endpoint
  - Message format conversion
  - Streaming response parsing
  - Error handling

#### Core Application (0% coverage) ❌
- `app.py` - FastAPI lifespan, initialization
- `bot_manager.py` - Bot config persistence to config.json
- `bot_cli.py` - CLI commands (add, list, remove)

### Critical Test Priorities

#### Priority 1 (High Risk - User-Facing)
1. **Thread Reconstruction** (`telegram_client.py`)
   - Complex recursive logic
   - Edge cases: orphaned threads, circular references, missing parents
   
2. **Parallel Fetching** (`webex_client.py`, `telegram_client.py`)
   - Date range chunking
   - Concurrency control
   - Deduplication
   - Error handling in parallel tasks

3. **Image Processing Pipeline** (all clients)
   - MIME type validation
   - Size limit enforcement
   - Parallel downloads
   - Base64 encoding

4. **Download Formats** (`download_service.py`)
   - PDF generation with fpdf2
   - HTML with inline images (data URIs)
   - ZIP with proper structure
   - Manifest generation

5. **OAuth Flows** (`webex_client.py`, `reddit_client.py`)
   - Token exchange
   - Token refresh
   - Expiration handling
   - Error scenarios

#### Priority 2 (Medium Risk - Background Operations)
6. **Caching Logic** (all clients)
   - Daily boundary handling
   - Today vs historical data
   - Cache corruption recovery
   - Cache path generation

7. **Bot Webhooks** (`bot_service.py`)
   - Event parsing
   - State management
   - Response generation
   - Error handling

8. **LLM Streaming** (LLM clients)
   - Format conversion
   - Stream parsing
   - Error handling
   - Safety blocks

9. **Session Management** (all clients)
   - Session validation
   - Session cleanup
   - Multi-backend coordination

#### Priority 3 (Lower Risk - Integration)
10. **API Endpoints** (routers)
    - Request validation
    - Response formatting
    - Error responses
    - OAuth callbacks

11. **CLI Tools** (`bot_cli.py`)
    - Argument parsing
    - User input validation
    - Config updates

### Recommended Testing Strategy

#### Phase 1: Unit Tests
```bash
# Client tests
tests/clients/test_telegram_client.py
tests/clients/test_webex_client.py
tests/clients/test_reddit_client.py
tests/clients/test_telegram_bot_client.py
tests/clients/test_webex_bot_client.py

# Service tests
tests/services/test_bot_service.py
tests/services/test_download_service.py
tests/services/test_reddit_service.py

# LLM tests
tests/llm/test_llm_client.py
tests/ai/test_google_ai_llm.py
tests/ai/test_openai_compatible_llm.py
```

#### Phase 2: Integration Tests
```bash
# API endpoint tests
tests/routers/test_auth_router.py
tests/routers/test_chat_router.py
tests/routers/test_reddit_router.py
tests/routers/test_bots_router.py
tests/routers/test_downloads_router.py

# End-to-end flows
tests/integration/test_full_chat_flow.py
tests/integration/test_bot_workflow.py
```

#### Phase 3: Coverage & CI/CD
```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Coverage goals
# - Clients: 80%+
# - Services: 80%+
# - Routers: 70%+
# - LLM: 70%+
```

### Testing Best Practices for This Project

#### Mocking External APIs
```python
import respx
from httpx import Response

@pytest.mark.asyncio
@respx.mock
async def test_webex_fetch_messages():
    # Mock Webex API
    respx.get("https://webexapis.com/v1/messages").mock(
        return_value=Response(200, json={"items": [...]})
    )
    
    # Test client
    client = WebexClient()
    messages = await client.get_messages(...)
    assert len(messages) > 0
```

#### Async Test Pattern
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

#### File I/O Mocking
```python
from unittest.mock import mock_open, patch

def test_session_save():
    with patch("builtins.open", mock_open()) as mock_file:
        save_session(data)
        mock_file.assert_called_once()
```

#### Fixture Usage
```python
@pytest.fixture
def mock_telegram_client(mocker):
    client = mocker.Mock()
    client.get_messages.return_value = [...]
    return client

def test_with_fixture(mock_telegram_client):
    # Use the fixture
    messages = mock_telegram_client.get_messages()
    assert messages
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/services/test_auth_service.py

# Run specific test
pytest tests/services/test_auth_service.py::TestAuthService::test_create_session

# Run with output (no capture)
pytest -s

# Run async tests only
pytest -k "async"

# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html  # macOS
```

### Known Testing Challenges

1. **Telegram SQLite Sessions**: Hard to mock Telethon's session management
2. **Async Streaming**: Testing SSE streams requires special handling
3. **External API Dependencies**: Need comprehensive mocking for Telegram, Webex, Reddit APIs
4. **File System Operations**: Cache and session file handling requires careful cleanup
5. **Timezone Handling**: Date boundary tests need timezone consideration
6. **Thread Reconstruction**: Complex logic with many edge cases
7. **Parallel Operations**: Race conditions and timing issues in tests

### Future Improvements

1. **Add pytest-cov** for coverage tracking
2. **CI/CD Integration** (GitHub Actions)
3. **Performance Tests** for parallel fetching
4. **Load Tests** for API endpoints
5. **Integration Tests** with Docker compose
6. **Contract Tests** for external APIs
7. **Property-based Tests** (hypothesis) for thread reconstruction
8. **Mutation Testing** to verify test quality