# Chat Analyzer Architecture

## Directory Structure

### Core Application Files
- **`app.py`**: Main FastAPI application entry point with lifespan management
- **`bot_manager.py`**: Handles bot configuration persistence to `config.json`
- **`bot_cli.py`**: CLI for managing bot registrations
- **`config.json`**: User-managed configuration (API keys, credentials, bot settings)

### Module Organization

#### `/clients/` - Platform Clients
- **`base_client.py`**: Abstract `ChatClient` interface with data models (`User`, `Chat`, `Message`, `Attachment`)
- **`factory.py`**: Returns appropriate client based on backend selection
- **`telegram_client.py`**: Telethon-based client with thread reconstruction via reply chains
- **`telegram_bot_client.py`**: Telegram Bot API client
- **`webex_client.py`**: OAuth-based Webex client with native threading
- **`webex_api_client.py`**: Low-level Webex API wrapper
- **`webex_bot_client.py`**: Webex bot client
- **`reddit_client.py`**: asyncpraw-based Reddit client with comment tree processing
- **`bot_factory.py`**: Unified bot client wrapper

#### `/ai/` - LLM Integration
- **`base_llm.py`**: Abstract `LLMClient` interface
- **`factory.py`**: Creates LLM client instances
- **`google_ai_llm.py`**: Google AI (Gemini) implementation
- **`openai_compatible_llm.py`**: OpenAI-compatible endpoint support (LM Studio, etc.)
- **`prompts.py`**: System prompts for AI modes

#### `/llm/` - LLM Manager
- **`llm_client.py`**: `LLMManager` orchestrates all LLM providers, discovers models, provides unified `call_conversational` method

#### `/routers/` - API Endpoints (FastAPI)
- **`auth.py`**: Login, logout, session status, OAuth callbacks
- **`chat.py`**: Generic chat listing and analysis endpoints
- **`reddit.py`**: Reddit-specific post fetching endpoints
- **`bots.py`**: Bot registration, listing, deletion, and webhook endpoints
- **`downloads.py`**: Download transcript in various formats

#### `/services/` - Business Logic
- **`auth_service.py`**: User login session and token management
- **`chat_service.py`**: Generic orchestration (fetch messages, format for LLM, stream AI response)
- **`reddit_service.py`**: Reddit-specific business logic
- **`bot_service.py`**: Incoming webhook handling, bot chat modes (`/aimode`)
- **`download_service.py`**: File generation (TXT, PDF, HTML, ZIP)

#### `/static/` - Frontend
- **`index.html`**: Main UI
- **`style.css`**: Styling
- **`/js/`**: Modular JavaScript files
  - `main.js`, `api.js`, `auth.js`, `bot.js`, `chat.js`, `reddit.js`, `ui.js`, `state.js`, `toast.js`, `eventManager.js`, `buttonStateManager.js`, `choicesWrapper.js`

#### `/tests/` - Test Suite
- **`/services/`**: Unit tests for services (`test_auth_service.py`, `test_chat_service.py`)
- Uses `pytest`, `pytest-mock`, `pytest-asyncio`, `respx`

#### `/cache/` - Auto-generated Cache
- **`/telegram/<user_id>/<chat_id>/<date>.json`**
- **`/webex/<user_id>/<chat_id>/<date>.json`**
- File-based daily message caching

#### `/sessions/` - Auto-generated Sessions
- **`app_sessions.json`**: Active user sessions
- **`webex_tokens.json`**: Webex OAuth tokens
- **`session_<phone>.session`**: Telegram session files
- **`reddit_session_<username>.json`**: Reddit refresh tokens

#### `/docs/` - Documentation
- Installation, user guides, bot guides, technical overview, architecture notes

## Key Architectural Patterns

### Caching Strategy
- **File-based**: Daily cache files per chat/user (`cache/<platform>/<user>/<chat>/<date>.json`)
- **Bypass for "today"**: Ensures fresh data for current day
- **In-memory**: Request-level caching for processed messages

### Performance Optimizations
- **Parallel Image Downloads**: `asyncio.gather()` for concurrent image fetching
- **Parallel Date Range Fetching**: Splits large ranges into configurable chunks (default: 7 days)
  - Webex: `asyncio.to_thread()` for true async parallelism
  - Telegram: Shared client to avoid SQLite locking
- **Configurable Chunking**: `parallel_fetch_chunk_days` and `max_concurrent_fetches` in config.json
- **Concurrency Control**: `asyncio.Semaphore` to limit concurrent API requests
- **Smart Deduplication**: Message IDs tracked across chunks

### Threading Implementation
- **Webex**: Native `thread_id` / `parentId` support
- **Telegram**: Reply chain reconstruction via `reply_to_msg_id`, deterministic root resolution
- **Reddit**: Comment tree with `parent_id` for nested structure, formatted with indentation

### State Management
- **No database**: JSON files for configuration and session persistence
- **Stateless API**: Session validation via file lookups
- **Bot state**: In-memory dict for `/aimode` chat state