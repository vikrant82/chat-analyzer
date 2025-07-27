# Multi-Backend AI Chat Analyzer

This web application allows users to connect to their personal chat accounts (currently supporting **Telegram** and **Webex**) to generate AI-powered summaries or ask specific questions about their chat history within a selected date range.

The application features a robust caching system to ensure fast, repeated analysis and a flexible AI backend that can connect to both Google AI and local models via LM Studio.

## Features

-   **Multi-Service Connectivity**: Securely log in to either Telegram or Webex accounts.
-   **Multi-Session Support**: Stay logged into both Telegram and Webex simultaneously and seamlessly switch between them without needing to re-authenticate each time.
-   **Unified Chat Experience**:
    -   Engage in a continuous conversation with the AI about your chat data.
    -   Ask follow-up questions without re-submitting the initial query.
    -   The AI maintains context throughout the conversation.
-   **AI-Powered Analysis & Bot Integration**:
    -   **Threaded Conversation Support**: Automatically detects and groups threaded conversations in Webex, providing the LLM with the full context of the conversation.
    -   **Webex Bot Support**: Register a Webex bot to invoke the analyzer directly from any Webex space. The bot leverages the permissions of the logged-in user to access and summarize chat history.
    -   **Telegram Bot Support**: Register a Telegram bot and interact with it directly to get summaries of any chat your user account is in.
    -   Mention the bot (e.g., `@MyAnalyzerBot summarize last 2 days`) to get an instant summary.
    -   **Real-time Streaming**: View AI responses as they are generated, word-by-word.
    -   **Summarization**: Generate concise summaries of chat conversations for a given period.
    -   **Question & Answering**: Ask specific questions about the chat content and receive AI-generated answers based *only* on the provided message history.
-   **Flexible AI Model Support**:
    -   Connects to **Google AI** (e.g., Gemini family) via API key.
    -   Connects to any locally-hosted model served through **LM Studio**.
    -   Support for any OpenAI compatible endpoint.
    -   Dynamically populates and allows selection from all available models.
-   **Intelligent Caching System**:
    -   **Configurable**: Users can enable or disable caching.
    -   Dramatically speeds up analysis of historical data.
    -   Caches messages on a per-day, per-chat basis.
    -   Caches "empty" days to prevent redundant API calls for periods with no activity.
    -   Always fetches fresh data for "today" to ensure summaries are up-to-date.
-   **User-Friendly Interface**:
    -   **Searchable Chat List**: Quickly find the chat you're looking for.
    -   **Modern Date Picker**: A modern, dark-theme friendly date picker.
    -   Simple, step-by-step process: Login -> Select Chat -> Analyze.
    -   **Bot Management UI**: A simple interface to register, view, and delete your bots.
    -   **Automated Webhook Setup**: Automatically registers the necessary webhook with Webex when you provide a public URL, simplifying setup.

## Project Structure

```
/
├── cache/                  # Auto-generated: Stores cached messages
├── clients/                # Contains the logic for each chat service
├── sessions/               # Auto-generated: Stores login session files
├── static/                 # Frontend CSS, JavaScript and single-page frontend
├── app.py                  # Main FastAPI backend application
├── bot_manager.py          # Handles bot configuration
├── WebexClient.py          # Low-level client for Webex API
├── config.json             # Main configuration file
├── requirements.txt        # Python dependencies
├── Dockerfile              # Instructions to build the Docker image
└── docker-compose.yaml     # Service definition for Docker Compose
```

## Setup and Installation

You can run this application either directly on your machine with Python or as a Docker container.

### Method 1.1: Run Pre-Built Image from Docker Hub (Recommended for End-Users)

This is the simplest method for users who just want to run the application without dealing with the source code. It pulls the ready-made image from Docker Hub.

#### Prerequisites
-   [Docker](https://www.docker.com/products/docker-desktop/) installed and running.
-   API credentials.

#### Option A: Using Docker Compose (Easiest)

1.  **Create `config.json`**: Create a `config.json` file as described in the "Configuration Details" section.

2.  **Run the Application**:
    ```bash
    docker-compose up -d
    ```
3.  **Access the App**: Navigate to **http://localhost:8000**.

#### Option B: Using `docker run` Command

If you prefer not to use a compose file, you can run the application with a single `docker run` command. Make sure your `config.json` is in your current directory.

```bash
docker run -d \
  --name my-chat-analyzer \
  -p 8000:8000 \
  -v "$(pwd)/config.json":/app/config.json:ro \
  -v chat_analyzer_sessions:/app/sessions \
  -v chat_analyzer_cache:/app/cache \
  vikrant82/chat-analyzer:latest
```
**Persistent Data**: The `docker-compose-localbuild.yaml` file is configured to use Docker volumes (`sessions_data` and `cache_data`). This means your login sessions and message cache will persist even if you stop and restart the container.

### Method 1.2: Running with Docker (Building a local image)

You may want to build a local image with changes or if unable to access docker hub or if your os/arch image is missing:

#### Prerequisites
-   [Docker](https://www.docker.com/products/docker-desktop/) installed and running on your machine.
-   API credentials (see "Get API Credentials" section below).

#### Steps
1.  **Create `config.json`**: Before building the container, you must create a `config.json` file in the root of the project directory. See the "Configure the Application" section below for the structure and what to put in it.

2.  **Build and Run the Container**: Open a terminal in the project's root directory and run the following command:
    ```bash
    docker-compose -f docker-compose-localbuild.yaml up --build
    ```
    -   This will build the Docker image based on the `Dockerfile` and start the application.
    -   The `-d` flag can be added (`docker-compose -f docker-compose-localbuild.yaml up --build -d`) to run it in the background.

3.  **Access the Application**: Open your web browser and navigate to **http://localhost:8000**.

4.  **Persistent Data**: The `docker-compose-localbuild.yaml` file is configured to use Docker volumes (`sessions_data` and `cache_data`). This means your login sessions and message cache will persist even if you stop and restart the container.

### Method 2.1: Running Directly with Python using Virtual Env (Recommended if running using python)

#### Prerequisites
-   Python 3.9+
-   API credentials (see "Get API Credentials" section below).

#### Steps
1.  **Create a Virtual Environment**: It is highly recommended to use a virtual environment to isolate project dependencies. From the project's root directory, run:
    ```bash
    # Create the virtual environment (e.g., named 'venv')
    python3 -m venv venv
    ```

2.  **Activate the Virtual Environment**:
    -   **On macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```
    -   **On Windows**:
        ```bash
        .\venv\Scripts\activate
        ```
    Your terminal prompt should now be prefixed with `(venv)`.

3.  **Install Dependencies**: With the virtual environment active, install the required packages.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Application**: Create and fill out your `config.json` file as described in the section below.

5.  **Run the Backend Server**:
    ```bash
    uvicorn app:app --reload
    ```

6.  **Access the Application**: Open your web browser and navigate to **http://localhost:8000**.

7.  **To Stop**: Press `Ctrl+C` in the terminal. To deactivate the virtual environment, simply type `deactivate`.

### Method 2.2: Running Directly with Python (without venv, just in case)

#### Prerequisites
-   Python 3.9+
-   API credentials (see "Get API Credentials" section below).

#### Steps
1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure the Application**: Create and fill out your `config.json` file as described below.

3.  **Run the Backend Server**:
    ```bash
    uvicorn app:app --reload
    ```
4.  **Access the Application**: Open your web browser and navigate to **http://localhost:8000**.

---

## Configuration Details

### Get API Credentials

-   **Telegram**:
    1.  Log into [my.telegram.org](https://my.telegram.org).
    2.  Go to "API development tools" and create a new app.
    3.  Copy the `api_id` and `api_hash`.
-   **Webex**:
    1.  Log into the [Webex App Hub for Developers](https://developer.webex.com/my-apps).
    2.  Click "Create a New App" -> "Create an Integration".
    3.  For the **Redirect URI(s)**, you **must** enter: `http://localhost:8000/api/webex/callback`
    4.  Define the **Scopes**. Select `spark:all`.
    5.  After creating the app, copy the **Client ID** and **Client Secret**.
-   **Google AI**:
    1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
    2.  Create and copy your API key.

### Configure a Webex Bot (Optional)
1.  Go to the [Webex App Hub for Developers](https://developer.webex.com/my-apps) and create a new Bot.
2.  Give your bot a name and icon.
3.  Copy the **Bot access token**. This is the token you will use to register the bot in the Chat Analyzer.
### Configure a Webex Bot (Optional)
1.  Go to the [Webex App Hub for Developers](https://developer.webex.com/my-apps) and create a new Bot.
2.  Give your bot a name and icon.
3.  Copy the **Bot access token**. This is the token you will use to register the bot in the Chat Analyzer.
4.  To find your bot's **Person ID**, use the following `curl` command in your terminal, replacing `YOUR_BOT_ACCESS_TOKEN` with the token you just copied:
    ```bash
    curl --request GET --header "Authorization: Bearer YOUR_BOT_ACCESS_TOKEN" https://webexapis.com/v1/people/me
    ```
5.  The `id` field in the JSON response is your bot's Person ID.

### Configure a Telegram Bot (Optional)
1.  Talk to the **BotFather** on Telegram.
2.  Create a new bot by sending the `/newbot` command.
3.  Follow the instructions to give your bot a name and username.
4.  BotFather will give you a **token** to access the HTTP API. This is the token you will use to register the bot in the Chat Analyzer.
5.  You do not need a "Bot ID" for Telegram bots, you can enter any dummy value.

### Create `config.json` File

In the root of the project, create a `config.json` file and populate it with your credentials.

```json
{
  "telegram": {
    "api_id": "YOUR_TELEGRAM_API_ID",
    "api_hash": "YOUR_TELEGRAM_API_HASH"
  },
  "webex": {
    "client_id": "YOUR_WEBEX_CLIENT_ID",
    "client_secret": "YOUR_WEBEX_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000/api/webex/callback",
    "scopes": [
      "spark:all"
    ]
  },
  "google_ai": {
    "api_key": "YOUR_GOOGLE_AI_API_KEY",
    "default_model": "gemini-1.5-flash" 
  },
  "lm_studio": {
    "url": "http://localhost:1234/v1/chat/completions",
    "default_model": "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"
  },
  "bots": {
    "webex": [
      {
        "name": "My Analyzer Bot",
        "bot_id": "YOUR_BOTS_PERSON_ID (Base64 Encoded)",
        "token": "YOUR_BOTS_ACCESS_TOKEN"
      }
    ],
    "telegram": [
      {
        "name": "My Telegram Analyzer",
        "bot_id": "dummy_id",
        "token": "YOUR_TELEGRAM_BOT_TOKEN"
      }
    ]
  }
}
```
*Note: If you are running the app in Docker and want to connect to LM Studio running on your host machine, use `http://host.docker.internal:1234/v1/chat/completions` as the `url`.*

## User Guide

### Logging In

1.  Upon opening the app, you will see the login screen.
2.  Select either **Telegram** or **Webex** from the "Chat Service" dropdown.
3.  **For Telegram**:
    -   Enter your full phone number, including the country code (e.g., `+14155552671`).
    -   Click "Send Code".
    -   Enter the code you receive in your Telegram app. If you have 2-Factor Authentication enabled, you will also be prompted for your password.
4.  **For Webex**:
    -   Click "Login with Webex".
    -   You will be redirected to the official Webex login page. Sign in with your credentials.
    -   Grant the application permission to access your account.
    -   You will be automatically redirected back to the app, now logged in.

### Analyzing a Chat

Once logged in, you will be on the "Analyze Chats" screen.

1.  **Select a Chat**: Your chats/rooms will be listed in the searchable dropdown. If the list is empty, click the **"Refresh List"** link to load them.
2.  **Select an AI Model**: Choose your preferred AI model from the list. A sensible default will be pre-selected if configured.
3.  **Select a Date Range**: Use the date picker to choose the start and end dates. You can also select from pre-defined ranges like "Last 2 Days", "Last Week", etc.
4.  **Configure Caching**: Use the "Enable caching for faster analysis" checkbox to enable or disable caching for the current analysis.
5.  **(Optional) Start with a Specific Question**: Before starting the chat, you can enter a specific question in the text box. If you do, the AI will answer that question directly instead of providing a general summary.
6.  **Start Chat**: Click the **"Start Chat"** button to begin the analysis and open the conversational chat window.
7.  **Ask Follow-up Questions**: Use the chat input to ask follow-up questions about the analyzed data.
8.  **Clear & Start New**: Click the **"Clear & Start New"** button to clear the conversation and start a new analysis.

### Using the Webex Bot

1.  After logging into the application, click the **"Manage Bots"** button.
2.  Register your Webex bot using the name, Person ID, and Access Token you retrieved earlier.
3.  **Crucially**, if you are running the application locally, you must expose it to the internet using a tool like **ngrok**. Start ngrok with the command `ngrok http 8000`.
4.  Copy the public HTTPS URL provided by ngrok (e.g., `https://abcdef123.ngrok.io`).
5.  In the "Manage Bots" UI, provide this public URL in the "Public Webhook URL" field during registration. This will allow the application to automatically create the necessary webhook in Webex.
6.  Once registered, go to any Webex space your bot has been added to and type `@YourBotName summarize last 2 days`. The bot will respond in the space.

For a complete guide on setting up and using the Webex bot, including detailed command instructions and examples, please see the **[Webex Bot Guide](webex_bot_guide.md)**.

### Using the Telegram Bot

1.  After logging into the application, click the **"Manage Bots"** button.
2.  Register your Telegram bot using the name and Access Token you retrieved from BotFather.
3.  **Crucially**, if you are running the application locally, you must expose it to the internet using a tool like **ngrok**. Start ngrok with the command `ngrok http 8000`.
4.  Copy the public HTTPS URL provided by ngrok (e.g., `https://abcdef123.ngrok.io`).
5.  In the "Manage Bots" UI, provide this public URL in the "Public Webhook URL" field during registration. This will allow the application to automatically set the necessary webhook with Telegram.
6.  Once registered, you can send a message to your bot in any chat it is a part of. For example: `summarize last 2 days`.

### Telegram Bot Features

The Telegram bot supports multiple commands to enhance your chat analysis experience. Beyond basic summarization, the bot now includes a conversational AI mode.

-   **/summarize**: Generate a summary of chat messages for a specified duration (e.g., `summarize last 3 days`).
-   **/aimode**: Switch to a conversational mode where you can ask the AI direct questions about the chat history.

For a complete guide on setting up and using the Telegram bot, including detailed command instructions and examples, please see the **[Telegram Bot Guide](telegram_bot_guide.md)**.

### Switching Services

You can be logged into both Telegram and Webex at the same time.

1.  While on the "Analyze Chats" screen, click the **"Switch Service"** button.
2.  A small dialog will appear asking you to confirm the switch to the other service.
3.  The application will instantly switch you to your other account's chat list if you have a valid session. If not, it will take you to the login page for that service.

### Logging Out

-   Clicking **"Logout"** will log you out of the currently active service. If you are logged into another service, the application will automatically switch to it. If not, you will be returned to the main login page.


### Publishing images:

```
docker buildx create --name mybuilder --driver docker-container --use
docker buildx build --platform linux/arm64,linux/amd64 -t vikrant82/chat-analyzer:latest -t vikrant82/chat-analyzer:1.0 --push .
```
