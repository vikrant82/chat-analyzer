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
  - `/ai`: System prompts, LLM client factories, and OpenAI-compatible streaming implementation. See [`python.ai.openai_compatible_llm`](ai/openai_compatible_llm.py:1).
  - `/clients`: Platform clients (Telegram, Webex). See [`python.clients.telegram_client_impl`](clients/telegram_client_impl.py:1) and [`python.clients.webex_client_impl`](clients/webex_client_impl.py:1).
  - `/static`: Frontend HTML/CSS/JS. The UI sends the browser timezone to the backend and exposes global Image Processing Options. See [`javascript.static/script.js`](static/script.js:1).
  - `/bot_manager.py`: Bot registration/lookup. See [`python.bot_manager`](bot_manager.py:1).
  - `/clients/bot_factory.py`: Unified bot client factory; Webex/Telegram bot senders. See [`python.clients.bot_factory`](clients/bot_factory.py:1).

**4. Execution & Entry Points**
   - **How to Run Locally:** `docker-compose up`
   - **Main Entry Files:** `app.py`
   - **Build Process:** `docker-compose build`

**5. Architecture & Core Logic**
  - **Key Modules/Components:**
    - **File:** `app.py`
      - Orchestration, API routers, session handling, streaming normalization via [`python.app._normalize_stream()`](app.py:73).
      - **Transcript Packaging:** [`python.app._format_messages_for_llm()`](app.py:401) builds a single packaged “Context: Chat History (Local Day)” user message with thread markers, author/timestamp headers, explicit image markers, and adjacent caption grounding. Images are represented as structured parts with metadata and are paired with captions to improve grounding.
      - **/api/chat:** Applies image processing settings from the UI, forwards user’s IANA timezone to clients, performs in-memory caching for historical ranges, and streams LLM output.
    - **File:** `clients/factory.py` — Resolves platform clients based on backend param.
    - **File:** `clients/telegram_client_impl.py`
      - Reads history with Telethon, reconstructs threads by reply-chain root resolution, assigns stable `thread_id`, orders orphan chains deterministically, honors image processing limits, groups/caches by local-day. See [`python.clients.telegram_client_impl.get_messages()`](clients/telegram_client_impl.py:144).
    - **File:** `clients/webex_client_impl.py`
      - Uses native thread IDs, performs local-day grouping/caching with ZoneInfo(timezone), optional image download with HEAD pre-checks, and pagination until window satisfied. See [`python.clients.webex_client_impl.get_messages()`](clients/webex_client_impl.py:137).
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
  - `/api/webex/bots` and `/api/telegram/bots` manage bot registration
  - `/api/bot/webex/webhook` and `/api/bot/telegram/webhook/{token}` receive bot events

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

