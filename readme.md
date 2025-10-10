# Multi-Backend AI Chat Analyzer

This web application allows users to connect to their personal chat accounts (currently supporting **Telegram**, **Webex**, and **Reddit**) to generate AI-powered summaries or ask specific questions about their chat history within a selected date range.

The application features a robust caching system to ensure fast, repeated analysis and a flexible AI backend that can connect to multiple LLM providers.

## Features

-   **Multi-Service Connectivity**: Securely log in to Telegram, Webex, and Reddit accounts.
-   **Multi-Session Support**: Stay logged into all services simultaneously and seamlessly switch between them without needing to re-authenticate each time.
-   **Unified Chat Experience**:
    -   Engage in a continuous conversation with the AI about your chat data.
    -   Ask follow-up questions without re-submitting the initial query.
    -   The AI maintains context throughout the conversation.
    -   **Stop Generation**: Cancel an in-progress AI response at any time.
-   **AI-Powered Analysis & Bot Integration**:
    -   **Threaded Conversation Support (Webex, Telegram, Reddit)**: Preserves native threading context end-to-end.
        - Webex: Groups by parent/threadId.
        - Telegram: Reconstructs reply-quote chains to deterministically resolve a thread root.
        - Reddit: Correctly represents deeply nested comment trees with proper indentation. It supports two streamlined workflows (deep analysis of a post via subreddit selection, or a quick summary from a URL) controlled via a simple radio button interface.
    -   **Configurable Image Analysis (All Providers)**: Globally enable/disable image processing from the UI and set maximum file sizes.
    -   **Webex & Telegram Bot Support**: Register bots to invoke the analyzer directly from any chat space.
    -   **Real-time Streaming**: View AI responses as they are generated, word-by-word.
    -   **Summarization & Q&A**: Generate concise summaries or ask specific questions about the chat content.
-   **Flexible AI Model Support**:
    -   Connects to **Google AI**, **LM Studio**, and any **OpenAI-compatible** endpoint.
    -   Dynamically populates and allows selection from all available models.
-   **Intelligent Caching System**:
    -   Dramatically speeds up analysis of historical data.
    -   Always fetches fresh data for "today" to ensure summaries are up-to-date.
-   **Performance Optimizations**:
    -   **Parallel Image Downloads**: Multiple images download concurrently for faster analysis (Webex & Telegram).
    -   **Parallel Date Range Fetching**: Large date ranges are split into chunks and fetched in parallel (up to 3x faster).
        - Webex: Uses token-based auth for multi-client parallelization.
        - Telegram: Uses shared client approach to avoid SQLite locking while enabling parallel chunk fetching.
    -   **Configurable Chunking**: Tune `parallel_fetch_chunk_days` (default: 7) and `max_concurrent_fetches` (default: 5) in config.json for optimal performance.
-   **User-Friendly Interface**:
    -   Searchable chat list, modern date picker, and global image options.
    -   **Flexible Downloads**: Export results in multiple formats:
        - Text (.txt): text-only.
        - PDF (.pdf): includes embedded images.
        - HTML (.html): includes images inline via data URIs.
        - ZIP (.zip): bundle with transcript.txt, transcript_with_images.html (references images/), images/ files, and manifest.json metadata.
    -   **Bot Management UI**: A simple interface to register, view, and delete your bots.
    -   **Automated Webhook Setup**: Simplifies bot setup by automatically registering webhooks.

## Documentation

For detailed information on how to set up, configure, and use the application, please see the guides in the `docs/` folder:

-   **[Installation Guide](./docs/installation.md)**: Detailed instructions for setting up the application using Docker or Python.
-   **[User Guide](./docs/user_guide.md)**: A complete walkthrough of the application's features.
-   **[Webex Bot Guide](./docs/webex_bot_guide.md)**: How to create and use the Webex bot.
-   **[Telegram Bot Guide](./docs/telegram_bot_guide.md)**: How to create and use the Telegram bot.
-   **[Reddit Guide](./docs/reddit_guide.md)**: How to connect and use the Reddit integration.
-   **[Technical Overview](./docs/overview.md)**: A high-level look at the project's architecture.

## Bot Management CLI

A command-line interface is available to manage bot registrations.

-   **Add a bot**:
    ```bash
    python bot_cli.py add <backend> <name> <user_id>
    ```
-   **List bots**:
    ```bash
    python bot_cli.py list <user_id> [--backend <backend>]
    ```
-   **Remove a bot**:
    ```bash
    python bot_cli.py remove <user_id> <backend> <name>
    ```

## Project Structure

```
/
├── docs/                   # All documentation files
├── cache/                  # Auto-generated: Stores cached messages
├── sessions/               # Auto-generated: Stores login session files
├── clients/                # Logic for communicating with chat services
├── llm/                    # Logic for communicating with LLM providers
├── routers/                # API endpoint definitions (FastAPI)
├── services/               # Core business logic
├── static/                 # Frontend HTML, CSS, and JavaScript
├── app.py                  # Main FastAPI application
├── bot_manager.py          # Handles bot configuration persistence
├── config.json             # User-created: Main configuration file
├── requirements.txt        # Python dependencies
├── Dockerfile              # Instructions to build the Docker image
└── docker-compose.yaml     # Service definition for pre-built Docker Hub image
