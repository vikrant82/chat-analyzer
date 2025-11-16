# Key Implementation Details

## Caching System

### Strategy
- **Granularity**: Daily cache files per user/chat (`YYYY-MM-DD.json`)
- **Location**: `cache/<platform>/<user_id>/<chat_id>/<date>.json`
- **Fresh data**: Always bypass cache for current day
- **Format**: JSON array of Message objects serialized via Pydantic `model_dump()`

### Cache Hit/Miss Logic
```python
current_day_local < today_local  # is_cacheable
if enable_caching and is_cacheable and os.path.exists(cache_path):
    # Cache HIT - load from file
else:
    # Cache MISS - fetch from API
```

## Threading & Reply Chain Reconstruction

### Webex
- **Native support**: Uses `parentId` / `thread_id` from API
- **Simple grouping**: Messages with same `thread_id` grouped together

### Telegram
- **Challenge**: Reply chains, not native threads
- **Solution**: Recursive root resolution
  1. Track all `reply_to_msg_id` relationships
  2. For each message, walk up the reply chain to find root
  3. Set `thread_id` to root message ID
  4. Group by `thread_id` and sort chronologically

```python
def resolve_root(start_id: str) -> Tuple[str, bool]:
    visited = set()
    current = start_id
    while True:
        parent = reply_to.get(current)
        if not parent or parent not in by_id:
            return current, False
        current = parent
```

### Reddit
- **Native tree**: Comment tree with `parent_id`
- **Recursive processing**: Depth-first traversal
- **Formatting**: Service layer adds indentation based on depth

## Parallel Fetching Optimization

### Webex Implementation
- **Problem**: Large date ranges slow (sequential API calls)
- **Solution**: Split into chunks, fetch in parallel
- **Mechanism**: `asyncio.to_thread()` wraps synchronous API calls
- **Concurrency control**: `asyncio.Semaphore(max_concurrent_fetches)`
- **Deduplication**: Track message IDs across chunks

### Telegram Implementation
- **Constraint**: SQLite session file doesn't support concurrent access
- **Solution**: Shared client connection across all chunks
- **Parallelism**: Multiple API calls with same client, semaphore-controlled
- **Media download**: Parallel within each chunk using `asyncio.gather()`

### Configuration
```json
{
  "telegram": {
    "parallel_fetch_chunk_days": 7,
    "max_concurrent_fetches": 5
  },
  "webex": {
    "parallel_fetch_chunk_days": 7,
    "max_concurrent_fetches": 5
  }
}
```

## Image Processing Pipeline

### Download & Encode Flow
1. **Check if enabled**: `image_processing_settings.enabled`
2. **Fetch metadata**: HEAD request to check MIME type and size
3. **Validate MIME**: Against `allowed_mime_types` list
4. **Validate size**: Against `max_size_bytes` limit
5. **Download**: Full file download if checks pass
6. **Encode**: Base64 encoding
7. **Attach**: Create `Attachment(mime_type, data)` object

### Parallel Downloads
- **Webex/Telegram**: All images downloaded concurrently using `asyncio.gather()`
- **Efficiency**: Reduces total fetch time significantly for image-heavy chats

### Multimodal LLM Support
- **Google AI**: Supports `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`
- **OpenAI-compatible**: Supports `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- **Format conversion**: Images embedded as base64 data URIs in LLM requests

## LLM Integration Architecture

### Provider Management (`LLMManager`)
- **Initialization**: Discovers all available models on startup
- **Provider types**: Google AI, OpenAI-compatible (LM Studio, etc.)
- **Model selection**: Frontend dropdown populated from discovered models
- **Streaming**: All providers use `AsyncGenerator[str, None]` for word-by-word streaming

### Conversation Context
- **Server-side state**: `conversations` dict keyed by `conversation_id`
- **Structure**: List of messages with roles (`user`, `assistant`/`model`)
- **Multimodal**: Messages can contain text + image parts
- **Mode switching**:
  - Summarizer: `original_messages` (chat transcript) + `conversation` (follow-ups)
  - AI Chat: Just `conversation` history

### Message Formatting
```python
# Standard format (internal)
{
  "role": "user" | "assistant" | "model",
  "content": "string" | [
    {"type": "text", "text": "..."},
    {"type": "image", "source": {"media_type": "...", "data": "..."}}
  ]
}

# Google AI format
{
  "role": "user" | "model",
  "parts": [
    {"text": "..."},
    {"inline_data": {"mime_type": "...", "data": "..."}}
  ]
}

# OpenAI format
{
  "role": "user" | "assistant",
  "content": [
    {"type": "text", "text": "..."},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]
}
```

## Bot Integration

### Registration Flow
1. User provides bot token and name
2. System validates token (calls `getMe` for Telegram, creates webhook for Webex)
3. Saves to `config.json` under `bots` array
4. Automatically sets up webhook pointing to server

### Webhook Handling
- **Telegram**: `POST /api/bots/telegram/webhook/{token}`
- **Webex**: `POST /api/bots/webex/webhook`
- **State**: In-memory dict tracks which chats are in `/aimode`
- **Response**: Direct message to chat via Bot API

### Chat Modes
- **Normal**: Bot is silent, doesn't respond
- **AI Mode**: Triggered by `/aimode` command, bot responds to all messages
- **Exit**: `/aimode off` or `/stop`

## Session Management

### Telegram
- **File**: `sessions/session_<phone>.session` (Telethon SQLite)
- **Validation**: `client.is_user_authorized()`
- **Cleanup**: File deletion on logout

### Webex
- **File**: `sessions/webex_tokens.json`
- **Structure**: `{"access_token": "...", "refresh_token": "...", "expires_in": 3600, "created_at": timestamp}`
- **Auto-refresh**: Checks expiration, refreshes proactively
- **Validation**: Try to fetch user details, catch 401

### Reddit
- **File**: `sessions/reddit_session_<username>.json`
- **Structure**: `{"refresh_token": "..."}`
- **Validation**: Try to fetch user info via asyncpraw

### Cross-Session State
- **File**: `sessions/app_sessions.json`
- **Structure**: `{backend: {logged_in: bool, user_identifier: str}}`
- **Purpose**: Track active sessions for session-status endpoint