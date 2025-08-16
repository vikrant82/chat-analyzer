# Technical Overview: Chat Analyzer

## 1. High-Level Summary
- **Purpose:** A web application for AI-powered analysis of chat histories from multiple platforms (Telegram, Webex, and Reddit). Users log in, select a chat/post and date range, and receive summaries or ask questions. It also supports optional bot integrations for invoking analysis directly from chat clients.
- **Users:** End-users seeking to understand chat conversations and developers looking for a reference implementation.
- **Core Functionality:**
    - **Web & Bot Interaction:** Main interface is a web UI. Optional bots for Webex and Telegram can be registered to trigger analysis.
    - **Cancellable AI Responses:** Users can stop an in-progress AI response stream at any time via a "Stop" button in the UI.
    - **Recent Chats:** The UI includes a "Recent Chats" feature that saves analysis sessions (including model, date range, and other settings), allowing users to quickly restore and re-run previous analyses.
    - **Advanced Threading:** Reconstructs and preserves conversation threads from both Webex (native) and Telegram (reply-chains) to provide accurate context to the LLM.
    - **Multimodal Analysis:** Can process and analyze images within conversations, subject to user-defined rules (size, type, etc.).

## 2. Technology Stack
- **Languages:** Python
- **Frameworks:** FastAPI
- **Key Libraries:** `telethon` (Telegram), `asyncpraw` (Reddit), `httpx` (Webex/Bots), `fastapi`, `uvicorn`. See [`requirements.txt`](./requirements.txt) for full list.
- **Database:** None. State is managed via session files and a JSON configuration file.

## 3. Directory Structure Map
- `ai/`: System prompts, LLM client factories, and OpenAI-compatible streaming logic.
- `clients/`: Platform-specific clients (Telegram, Webex, Reddit) for fetching chat data.
- `llm/`: Manages LLM provider clients (e.g., Google AI, LM Studio).
- `routers/`: FastAPI API endpoint definitions.
- `services/`: Core business logic (auth, chat processing, downloads).
- `static/`: Frontend HTML, CSS, and modular JavaScript files (`static/js/`).
- `bot_manager.py`: Handles registration and persistence of bot configurations into `config.json`.
- `app.py`: Main FastAPI application entry point.
- `config.json`: User-managed file for API keys, credentials, and bot settings.

## 4. Execution & Entry Points
- **Local Execution:** `uvicorn app:app --reload`
- **Docker Execution:** `docker-compose up` (using pre-built image) or `docker-compose -f docker-compose-localbuild.yaml up --build` (for local builds).
- **Main Entry File:** `app.py`
- **Download Formats:**
    - Text-only: `.txt`, `.pdf`
    - With Images: `.html` (embedded), `.zip` (includes separate image files)

## 5. Architecture & Core Logic
- **`app.py`**: Initializes the FastAPI app, mounts the static frontend, and includes the API routers.
- **`routers/`**: Defines all API endpoints for authentication, chat, bots, and downloads.
- **`services/`**:
    - `auth_service.py`: Manages user login sessions and token persistence.
    - `chat_service.py`: Orchestrates fetching messages, formatting them for the LLM (including threading and images), and streaming the AI response.
    - `bot_service.py`: Handles incoming webhooks from bots, holds in-memory state for bot chat modes (`/aimode`), and coordinates with other services to generate a response.
    - `download_service.py`: Creates downloadable files in various formats.
- **`clients/`**:
    - `factory.py`: Returns the correct client instance based on the selected backend (`telegram` or `webex`).
    - `telegram_client.py`: Uses Telethon to read chat history and reconstructs threads from reply chains.
    - `webex_client.py`: Uses native thread IDs for simple threading.
    - `reddit_client.py`: Fetches posts and comment trees, populating a `parent_id` for each comment to represent the nested structure. The `chat_service` is responsible for formatting the final threaded output.
- **`llm/llm_client.py`**: The `LLMManager` initializes all configured LLM providers (Google AI, LM Studio, etc.), discovers their available models, and provides a unified `call_conversational` method for services to use.
- **`bot_manager.py`**: Provides methods to read, add, and remove bot configurations from the `config.json` file, ensuring changes are persisted.
- **Caching Architecture:**
    - **File-based:** Caches historical message data per-day at `cache/<platform>/<user_id>/<chat_id>/<date>.json`.
    - **In-memory:** Caches processed message structures for the duration of a request. Bypassed if the date range includes the current day to ensure fresh data.

## 6. API & External Interactions
- **Authentication:**
    - `POST /api/login`: Initiates login (phone code for Telegram, OAuth for Webex and Reddit).
    - `GET /api/session-status`: Checks if a user has active sessions.
    - `POST /api/logout`: Logs out the current user.
- **Chat & Data:**
    - `GET /api/chats`: Lists available chats for the logged-in user.
    - `POST /api/chat`: Main endpoint to start a chat analysis. Streams the response.
    - `POST /api/download`: Generates and returns a downloadable transcript.
    - `POST /api/clear-session`: Clears server-side caches for the user.
- **Bot Management:**
    - `POST /api/{backend}/bots`: Registers a new bot.
    - `GET /api/{backend}/bots`: Lists registered bots.
    - `DELETE /api/{backend}/bots/{bot_name}`: Deletes a bot.
- **Webhooks:**
    - `POST /api/bots/webex/webhook`: Receives events from the Webex bot.
    - `POST /api/bots/telegram/webhook/{token}`: Receives events from the Telegram bot.

## 7. Configuration & Environment
- **`config.json`**:
    - `telegram`, `webex`, `reddit`: API credentials and settings.
    - `google_ai`, `lm_studio`: LLM provider URLs and API keys.
    - `bots`: A list where new bot configurations are stored.
- **Environment Variables:** `HOST`, `PORT`, `RELOAD` for server configuration.
- **Session Persistence:** Active user sessions are stored in `sessions/app_sessions.json`.

## 8. Testing
- **Status:** A formal test suite is pending.
- **Areas for Future Tests:**
    - Unit tests for Telegram thread reconstruction logic.
    - Tests for image processing rules (gating by size/type).
    - Verification of timezone handling and date range bucketing.
