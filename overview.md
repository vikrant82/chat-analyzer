### **Project Knowledge Base: `[chat_analyzer]`**

**1. High-Level Summary**
   - **Purpose:** This project provides a chat analysis service that can be invoked via Webex or Telegram bots. It summarizes chat conversations and can also act as a conversational AI.
   - **Users:** Developers and end-users who want to quickly understand the content of a chat conversation.
   - **Core Functionality:**
     - **Webex Bot Integration:** Register a Webex bot and invoke the analyzer from any Webex space by mentioning the bot.
       - **Threading (Webex + Telegram):** Threaded conversations are preserved. Webex uses native thread IDs. Telegram threads are reconstructed by resolving reply-chain roots; replies are grouped under the root. Transcript packaging emits explicit “--- Thread Started/Ended ---” markers to preserve conversational flow for the LLM.
       - **Image Support (Provider-Agnostic):** Images from Webex and Telegram can be included, subject to configurable processing rules (enable flag, max size, optional allowed MIME types). Media is base64-encoded and sent to multimodal models as image parts with adjacent caption grounding.
     - **Telegram Bot Integration:** Register a Telegram bot and interact directly for summaries. Supports `/aimode` to switch to conversational AI.

**2. Technology Stack**
   - **Languages:** Python
   - **Frameworks:** FastAPI
   - **Key Libraries/Dependencies:** See `requirements.txt`. Key libraries include `telethon` for the Telegram user client, `httpx` for the Telegram bot client, and `fastapi` for the web server.
   - **Database:** None.

**3. Directory Structure Map**
  - `/ai`: System prompts, LLM client factories, and OpenAI-compatible streaming implementation.
  - `/clients`: Platform clients (Telegram, Webex).
  - `/routers`: API endpoint definitions for authentication, downloads, etc.
  - `/services`: Business logic for authentication, downloads, etc.
  - `/static`: Frontend HTML/CSS/JS.
  - `/bot_manager.py`: Bot registration/lookup.

**4. Execution & Entry Points**
  - **How to Run Locally:** `docker-compose up`
  - **Main Entry Files:** `app.py`
  - **Build Process:** `docker-compose build`
  - **Downloads:**
    - Formats supported: Text (.txt), PDF (.pdf, text-only), HTML (.html with images embedded), Bundle (.zip with transcript.txt, transcript_with_images.html, images/, manifest.json).
    - Use HTML or ZIP to include images in the export.

**5. Architecture & Core Logic**
  - **Key Modules/Components:**
    - **File:** `app.py`
      - Main application entry point. Initializes the FastAPI app and includes the API routers.
    - **File:** `routers/auth.py`
      - Handles all authentication-related API endpoints.
    - **File:** `routers/downloads.py`
      - Handles the API endpoint for downloading chat transcripts.
    - **File:** `services/auth_service.py`
      - Manages session tokens and user authentication state.
    - **File:** `services/download_service.py`
      - Contains the business logic for creating download files in various formats (PDF, TXT, HTML, ZIP).
    - **File:** `clients/factory.py` — Resolves platform clients based on backend param.
    - **File:** `clients/telegram_client_impl.py`
      - Reads history with Telethon, reconstructs threads by reply-chain root resolution, assigns stable `thread_id`, orders orphan chains deterministically, honors image processing limits, groups/caches by local-day.
    - **File:** `clients/webex_client_impl.py`
      - Uses native thread IDs, performs local-day grouping/caching with ZoneInfo(timezone), optional image download with HEAD pre-checks, and pagination until window satisfied.
    - **File:** `ai/prompts.py`
      - Defines `UNIFIED_SYSTEM_PROMPT` describing transcript packaging at the start; removes any instruction to add packaging notes in outputs.
    - **File:** `ai/openai_compatible_llm.py`
      - Formats mixed text/image parts into OpenAI-compatible payloads; streams deltas via SSE/HTTPX; handles multimodal parts.
  - **Telegram Bot Architecture:**
    - Dual-client: stateful Telethon for reading; stateless Bot API for sending.
  - **Stateful Bot Logic:**
    - `chat_modes` in `app.py` toggles summarizer vs `/aimode`.
   - **Caching Architecture (Local-Day Semantics):**
     - The user’s browser timezone (IANA tz) is used for filtering, grouping, and per-day cache keys across Webex and Telegram, while preserving each provider’s API pagination.
     - File-based retrieval cache: `cache/<platform>/<user_id>/<chat_id>/<date>.json` (past days only).
     - In-memory processing cache: keyed by session token and date range; bypassed when the range includes “today” in the user’s local timezone.

**6. API & External Interactions**
  - `/api/login` (Telegram: phone-based code flow; Webex: OAuth redirect)
  - `/api/session-status` validates active sessions and clears caches on invalidation
  - `/api/chats` lists available rooms/chats for the active backend
  - `/api/chat` summarizes using single-message transcript + conversation; streams output
  - `/api/download` exports threaded transcript (PDF/TXT)
  - `/api/clear-session`, `/api/logout` clear caches/sessions
  - `/api/{backend}/bots` manage bot registration, listing, and deletion.
  - `/api/bots/webex/webhook` and `/api/bots/telegram/webhook/{token}` receive bot events

**7. Configuration & Environment**
  - `config.json`:
    - `openai_compatible`: endpoints and model defaults
    - `google_ai`: optional config for Gemini
    - `webex`: OAuth credentials, scopes, and optional `image_processing` defaults
    - `bots`: optional predefined bots
  - Environment variables: HOST, PORT, RELOAD
  - Sessions persisted at `sessions/app_sessions.json`

**8. Testing**
  - Pending: unit tests for threading reconstruction, image gating, and timezone bucketing.
  - Suggested: golden transcripts for complex Telegram threads; media MIME/size matrix tests; cross-day window tests.

**9. Missing Information & Inferences**
  - Formal test suite pending.
  - Logging: add trace points for thread root resolution, orphan ordering, and media inclusion/exclusion decisions.

**Developer Notes:**
- Keep streaming implementation aligned with frontend expectations; avoid unverified streaming refactors.
