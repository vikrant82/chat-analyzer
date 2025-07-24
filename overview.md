### **Project Knowledge Base: `[chat_analyzer]`**

**1. High-Level Summary**
   - **Purpose:** This project provides a chat analysis service that can be invoked via Webex or Telegram bots. It summarizes chat conversations and can also act as a conversational AI.
   - **User:** Developers and end-users who want to quickly understand the content of a chat conversation.
   - **Core Functionality:**
     - **Webex Bot Integration**: Allows users to register a Webex bot and invoke the chat analyzer from any Webex space by mentioning the bot.
           - **Webex Threading**: The application now correctly handles threaded conversations in Webex. Messages are grouped by thread, and the context is formatted to preserve the conversational flow of the threads.
     - **Telegram Bot Integration**: Allows users to register a Telegram bot and interact with it directly to get summaries of any chat.
     - **/aimode for Telegram Bot**: A feature that enables a conversational AI mode, allowing users to ask direct questions to the AI about the chat history.

**2. Technology Stack**
   - **Languages:** Python
   - **Frameworks:** FastAPI
   - **Key Libraries/Dependencies:** See `requirements.txt`. Key libraries include `telethon` for the Telegram user client, `httpx` for the Telegram bot client, and `fastapi` for the web server.
   - **Database:** None.

**3. Directory Structure Map**
   - `/ai`: Contains all AI-related logic, including prompts and model factories.
   - `/clients`: Contains the client implementations for interacting with different chat platforms (Telegram, Webex).
   - `/static`: Contains the frontend files for the web UI.

**4. Execution & Entry Points**
   - **How to Run Locally:** `docker-compose up`
   - **Main Entry Files:** `app.py`
   - **Build Process:** `docker-compose build`

**5. Architecture & Core Logic**
   - **Key Modules/Components:**
     - **File:** `app.py`
     - **Responsibility:** Main FastAPI application. Handles all API routing, user authentication, and orchestrates the chat analysis process. Contains the webhook handler for bot interactions. It also manages the state of each chat via the `chat_modes` global dictionary.
     - **File:** `bot_manager.py`
     - **Responsibility:** Handles the registration, retrieval, and deletion of bot configurations.
     - **File:** `clients/factory.py`
     - **Responsibility:** Implements the factory pattern to instantiate the correct chat client (`telegram`, `webex`) based on the user's selection.
     - **File:** `clients/telegram_client_impl.py`
     - **Responsibility:** Implements the **user client** for Telegram using Telethon. This client is responsible for reading chat history and requires a `.session` file for stateful authentication.
     - **File:** `clients/telegram_bot_client_impl.py`
     - **Responsibility:** Implements the stateless **bot client** for Telegram using `httpx` and the Bot API. This client is used for sending messages back to the user.
     - **File:** `ai/prompts.py`
     - **Responsibility:** Contains the system prompts used by the AI. This includes the `UNIFIED_SYSTEM_PROMPT` for summarization and the `GENERAL_AI_SYSTEM_PROMPT` for the conversational AI mode.
   - **Telegram Bot Architecture:**
     - The system uses a dual-client architecture for the Telegram bot:
       - **User Client (Telethon):** A stateful client used for reading chat history. It authenticates using a `.session` file.
       - **Bot Client (httpx):** A stateless client that uses the Telegram Bot API to send messages.
   - **Stateful Bot Logic:**
     - The `chat_modes` global dictionary in `app.py` tracks the current mode (`summarizer` or `aimode`) for each chat, allowing the bot to maintain state across interactions.
   - **/aimode Feature:**
     - The `_process_telegram_bot_command` function in `app.py` acts as a dispatcher.
     - It handles the `/aimode` command, toggling the chat's mode in the `chat_modes` dictionary.
     - Based on the current mode, it delegates to either `_handle_summarizer_mode` or `_handle_ai_mode`.
   - **Dynamic Prompts:**
     - The `call_conversational` method in the AI logic dynamically selects a system prompt.
     - If the `original_messages` parameter is provided, it uses the `UNIFIED_SYSTEM_PROMPT` for summarization.
     - Otherwise, it uses the `GENERAL_AI_SYSTEM_PROMPT` for conversational AI.

**6. API & External Interactions**
   - **Internal APIs:**
     - `POST /api/login`: Initiates the login process for a given backend (Telegram or Webex).
     - `GET /api/chats`: Fetches the list of available chats for the authenticated user.
     - `POST /api/chat`: The main endpoint for performing AI analysis on a selected chat.
     - `POST /api/{backend}/bots`: Registers a new bot for the specified backend.
     - `GET /api/{backend}/bots`: Retrieves the list of registered bots for a backend.
     - `DELETE /api/{backend}/bots/{bot_name}`: Deletes a registered bot.
     - `POST /api/bot/webex/webhook`: The public endpoint that receives webhook notifications from Webex when a bot is mentioned.
     - `POST /api/bot/telegram/webhook/{bot_token}`: The public endpoint that receives webhook notifications from Telegram.
   - **External Services:**
     - Telegram API
     - Webex API
     - Google AI API (or any other configured LLM)

**7. Configuration & Environment**
   - **Configuration Files:** `config.json`
   - **Environment Variables:** See `config.json` for a list of required variables.

**8. Testing**
   - **Testing Frameworks:** Not yet implemented.
   - **Test Location:** Not yet implemented.
   - **How to Run Tests:** Not yet implemented.

**9. Missing Information & Inferences**
   - The project lacks a formal testing suite.


**Developer Notes:**

*   **Attempted Fixes (2025-07-24):** An attempt was made to fix various Pylance warning in `app.py` related to an not having an `await` call on a stream. This change, while technically correct, caused the UI to stop updating. A subsequent attempt to fix the streaming response format also failed. These fixes should not be attempted again without a deeper investigation into the frontend's handling of the stream.
