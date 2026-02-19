# Code Style and Conventions

## General Python Conventions

### Import Organization
- Standard library imports first
- Third-party imports second
- Local imports last
- Generally grouped without blank lines between groups
- Example from codebase:
```python
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from .base_client import ChatClient
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `ChatClient`, `TelegramClient`, `BotManager`)
- **Functions/Methods**: snake_case (e.g., `get_messages`, `process_chat_request`, `_format_messages`)
- **Private Methods**: Prefix with underscore (e.g., `_download_and_encode_file`, `_get_cache_path`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `CACHE_DIR`, `SESSION_DIR`, `API_URL`)
- **Variables**: snake_case (e.g., `user_identifier`, `chat_id`, `start_date_str`)

### Type Hints
- **Extensive use**: All function signatures include type hints
- **Return types**: Always specified, including `None`, `Dict[str, Any]`, `List[Message]`
- **Optional types**: Used with `Optional[str]` for nullable values
- **Generic types**: `List[Chat]`, `Dict[str, List[Message]]`, `AsyncGenerator[str, None]`
- Example:
```python
async def get_messages(
    self, 
    user_identifier: str, 
    chat_id: str, 
    start_date_str: str, 
    end_date_str: str,
    enable_caching: bool = True,
    image_processing_settings: Optional[Dict[str, Any]] = None,
    timezone_str: Optional[str] = None
) -> List[Message]:
```

### Docstrings
- **Triple quotes**: Used for all class and function docstrings
- **Format**: Simple descriptive text, sometimes with Args/Returns sections
- **Example**:
```python
def get_authorization_url(self) -> str:
    """Constructs the URL for the user to grant consent."""
```
- **Detailed docstrings** for complex functions:
```python
async def _fetch_posts_with_sort(self, subreddit, sort_method: str = None, time_filter: str = None, limit: int = 50) -> List:
    """
    Helper method to fetch posts from a subreddit with specified sorting and time filter.
    
    Args:
        subreddit: The subreddit object to fetch from
        sort_method: One of "hot", "new", "top", "controversial", "rising" (defaults to self.default_sort)
        time_filter: One of "hour", "day", "week", "month", "year", "all" (only used for "top" and "controversial")
        limit: Maximum number of posts to fetch
        
    Returns:
        List of submission objects
    """
```

### Error Handling
- **Try-except blocks**: Extensive use with specific exception types
- **Logging**: Always log errors with `logger.error()` or `logger.warning()`
- **HTTPException**: Used in routers for API errors
- **Custom exceptions**: `LLMError` for LLM-specific errors
- **Raise with context**: Include helpful error messages
- Example:
```python
try:
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"Error fetching messages: {e.response.text}")
    raise
```

### Logging
- **Logger per module**: `logger = logging.getLogger(__name__)`
- **Log levels**: INFO for normal operations, WARNING for recoverable issues, ERROR for failures
- **Contextual messages**: Include relevant variables (user_id, chat_id, etc.)
- **Example**:
```python
logger.info(f"Cache HIT for Webex chat {chat_id} on {current_day_local.date()}")
logger.warning(f"Cache file {cache_path} is corrupted. Re-fetching.")
logger.error(f"HTTP error while fetching file from {file_url}: {e.response.status_code}")
```

### Async Patterns
- **Async/await**: Consistently used for I/O operations
- **Context managers**: `async with` for clients and connections
- **Generators**: `AsyncGenerator[str, None]` for streaming responses
- **Parallelism**: `asyncio.gather()` for concurrent operations
- **Threading**: `asyncio.to_thread()` for wrapping sync calls
- Example:
```python
async with telegram_api_client(user_identifier) as client:
    async for dialog in client.iter_dialogs(limit=200):
        # process dialogs
```

### Data Models (Pydantic)
- **BaseModel**: Used for API request/response schemas
- **Example**:
```python
class User(BaseModel):
    id: str
    name: str

class Message(BaseModel):
    id: str
    text: Optional[str] = None
    author: User
    timestamp: str  # ISO 8601 format
    thread_id: Optional[str] = None
    parent_id: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
```

### File Organization
- **One class per file** (generally)
- **Factories in separate files**: `factory.py` for factory functions
- **Constants at top**: After imports, before functions/classes
- **Helper functions**: Placed before or after main class, often prefixed with `_`

### Comments
- **Inline comments**: Sparingly used, explain "why" not "what"
- **Section headers**: Sometimes used for clarity in long files
- **Example**:
```python
# 1. Add the post itself as the first message
# 2. Fetch and process all comments
# --- Optimization ---
# Get all message IDs that were successfully loaded from the daily caches
```

### Configuration Management
- **JSON files**: `config.json` for user settings
- **Environment variables**: `HOST`, `PORT`, `RELOAD` for runtime config
- **Config access**: Via dictionary lookups with `.get()` for safe defaults
- **Example**:
```python
self.parallel_fetch_chunk_days = config.get('parallel_fetch_chunk_days', 7)
```

## Design Patterns

### Abstract Base Classes
- Used for `ChatClient` and `LLMClient` interfaces
- `@abstractmethod` decorator for interface methods

### Factory Pattern
- `get_client(backend)` in `clients/factory.py`
- `get_bot_client(backend, token)` in `clients/bot_factory.py`
- LLM factory in `ai/factory.py`

### Dependency Injection
- FastAPI's `Depends()` for shared dependencies (auth, clients)

### Decorator Pattern
- `@retry_on_failure(max_retries=3, delay=2)` for API resilience

### Strategy Pattern
- Different client implementations for each platform
- Different LLM provider implementations