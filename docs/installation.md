# Setup and Installation Guide

This guide provides detailed instructions for setting up and running the Chat Analyzer application.

## Method 1: Running with Docker

This is the recommended method for most users.

### Option A: Use the Pre-Built Image from Docker Hub (Easiest)
This is the simplest method. It pulls the ready-made image from Docker Hub.

1.  **Prerequisites**: [Docker](https://www.docker.com/products/docker-desktop/) installed and running.
2.  **Create `config.json`**: Create a `config.json` file as described in the "Configuration Details" section below.
3.  **Create `docker-compose.yaml`**: Create a file named `docker-compose.yaml` with the following content:
    ```yaml
    version: '3.8'
    services:
      chat-analyzer:
        image: vikrant82/chat-analyzer:latest
        container_name: chat-analyzer
        ports:
          - "8000:8000"
        volumes:
          - ./config.json:/app/config.json:ro
          - sessions_data:/app/sessions
          - cache_data:/app/cache
        restart: unless-stopped

    volumes:
      sessions_data:
      cache_data:
    ```
4.  **Run the Application**:
    ```bash
    docker-compose up -d
    ```
5.  **Access the App**: Navigate to **http://localhost:8000**.

### Option B: Build a Local Image
Use this method if you have made changes to the source code or need a build for a different architecture.

1.  **Prerequisites**: [Docker](https://www.docker.com/products/docker-desktop/) installed and running.
2.  **Create `config.json`**: Create your `config.json` file.
3.  **Build and Run**: Use the provided `docker-compose-localbuild.yaml` file to build and run the container.
    ```bash
    docker-compose -f docker-compose-localbuild.yaml up --build -d
    ```
4.  **Access the Application**: Navigate to **http://localhost:8000**.

**Persistent Data**: Both Docker methods use named volumes (`sessions_data` and `cache_data`) to ensure your login sessions and message cache persist even if you stop and restart the container.

## Method 2: Running Directly with Python

#### Prerequisites
-   Python 3.9+
-   API credentials (see "Configuration Details" section below).

#### Steps
1.  **Create a Virtual Environment**: It is highly recommended to use a virtual environment to isolate project dependencies.
    ```bash
    # Create the virtual environment (e.g., named 'venv')
    python3 -m venv venv
    ```

2.  **Activate the Virtual Environment**:
    -   **On macOS/Linux**: `source venv/bin/activate`
    -   **On Windows**: `.\venv\Scripts\activate`
    *(Your terminal prompt should now be prefixed with `(venv)`)*

3.  **Install Dependencies**:
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
-   **Reddit**:
    1.  Go to the [Reddit Apps](https://www.reddit.com/prefs/apps) page.
    2.  Create a new "script" application.
    3.  For the **Redirect URI**, you **must** enter: `http://localhost:8000/api/auth/callback/reddit`
    4.  Copy the **Client ID** (under "personal use script") and the **Client Secret**.

### Create `config.json` File

In the root of the project, create a `config.json` file and populate it with your credentials.

-   **Image Processing**: The `image_processing` block within the `webex` configuration allows you to control how images are handled to manage AI costs.
    -   `enabled`: Set to `true` to allow the application to download and analyze images, or `false` to disable it globally.
    -   `max_size_bytes`: The maximum size of an image (in bytes) that will be processed.
    -   `allowed_mime_types`: A list of image formats (e.g., "image/jpeg", "image/png") that are permitted for analysis.

***Note:** The `bots` section of the configuration is managed automatically by the application. Do not add bot configurations here manually. Use the "Manage Bots" interface in the web UI.*

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
    ],
    "image_processing": {
      "enabled": true,
      "max_size_bytes": 10485760,
      "allowed_mime_types": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp"
      ]
    }
  },
  "google_ai": {
    "api_key": "YOUR_GOOGLE_AI_API_KEY",
    "default_model": "gemini-1.5-flash" 
  },
  "lm_studio": {
    "url": "http://localhost:1234/v1/chat/completions",
    "default_model": "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"
  },
  "reddit": {
    "client_id": "YOUR_REDDIT_CLIENT_ID",
    "client_secret": "YOUR_REDDIT_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000/api/auth/callback/reddit",
    "user_agent": "ChatAnalyzer/0.1 by YourUsername"
  }
}
```
*Note: If you are running the app in Docker and want to connect to LM Studio running on your host machine, use `http://host.docker.internal:1234/v1/chat/completions` as the `url`.*
