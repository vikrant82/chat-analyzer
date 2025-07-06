# Multi-Backend AI Chat Analyzer

This web application allows users to connect to their personal chat accounts (currently supporting **Telegram** and **Webex**) to generate AI-powered summaries or ask specific questions about their chat history within a selected date range.

The application features a robust caching system to ensure fast, repeated analysis and a flexible AI backend that can connect to both Google AI and local models via LM Studio.

## Features

-   **Multi-Service Connectivity**: Securely log in to either Telegram or Webex accounts.
-   **Multi-Session Support**: Stay logged into both Telegram and Webex simultaneously and seamlessly switch between them without needing to re-authenticate each time.
-   **AI-Powered Analysis**:
    -   **Real-time Streaming**: View AI responses as they are generated, word-by-word.
    -   **Summarization**: Generate concise summaries of chat conversations for a given period.
    -   **Question & Answering**: Ask specific questions about the chat content and receive AI-generated answers based *only* on the provided message history.
-   **Flexible AI Model Support**:
    -   Connects to **Google AI** (e.g., Gemini family) via API key.
    -   Connects to any locally-hosted model served through **LM Studio**.
    -   Dynamically populates and allows selection from all available models.
-   **Intelligent Caching System**:
    -   **Configurable**: Users can enable or disable caching.
    -   Dramatically speeds up analysis of historical data.
    -   Caches messages on a per-day, per-chat basis.
    -   Caches "empty" days to prevent redundant API calls for periods with no activity.
    -   Always fetches fresh data for "today" to ensure summaries are up-to-date.
-   **User-Friendly Interface**:
    -   **Searchable Chat List**: Quickly find the chat you're looking for.
    -   **Modern Date Picker**: Includes pre-defined ranges like "Last 7 Days".
    -   Simple, step-by-step process: Login -> Select Chat -> Analyze.

## Project Structure

```
/
├── cache/                  # Auto-generated: Stores cached messages
├── clients/                # Contains the logic for each chat service
├── sessions/               # Auto-generated: Stores login session files
├── static/                 # Frontend CSS, JavaScript and single-page frontend
├── app.py                  # Main FastAPI backend application
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
3.  **Select a Date Range**: Use the modern date picker to choose the start and end dates. You can also select from pre-defined ranges like "Today", "Last 7 Days", etc.
4.  **Configure Caching**: Use the "Cache fetched chats" checkbox to enable or disable caching for the current analysis.
5.  **Choose an Action**:
    -   **For a Summary**: Leave the "Ask a specific question" box unchecked and click **"Get Summary"**.
    -   **To Ask a Question**: Check the "Ask a specific question" box, type your question into the text area, and click **"Get Answer"**.
6.  View the results as they stream in from the AI model.

### Switching Services

You can be logged into both Telegram and Webex at the same time.

1.  While on the "Analyze Chats" screen, click the **"Switch Service"** button.
2.  A small dialog will appear asking you to confirm the switch to the other service.
3.  The application will instantly switch you to your other account's chat list if you have a valid session. If not, it will take you to the login page for that service.

### Logging Out

-   Clicking **"Logout"** will log you out of the currently active service. If you are logged into another service, the application will automatically switch to it. If not, you will be returned to the main login page.
