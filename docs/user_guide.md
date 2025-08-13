# User Guide

This guide explains how to use the Chat Analyzer application, from logging in to analyzing chats and using the integrated bots.

## Logging In

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

## Analyzing a Chat

Once logged in, you will be on the "Analyze Chats" screen.

1.  **Select a Chat**: Your chats/rooms will be listed in the searchable dropdown. If the list is empty, click the **"Refresh List"** link to load them.
2.  **Select an AI Model**: Choose your preferred AI model from the list. A sensible default will be pre-selected if configured.
3.  **Select a Date Range**: Use the date picker to choose the start and end dates. You can also select from pre-defined ranges like "Last 2 Days", "Last Week", etc. Date ranges are interpreted using your browser’s IANA timezone (Local-Day semantics).
4.  **Configure Caching**: Use the "Enable caching for faster analysis" checkbox to enable or disable caching for the current analysis.
5.  **Configure Image Processing**: Globally toggle image analysis and set a maximum image size (MB); applies to all providers.
6.  **(Optional) Start with a Specific Question**: Before starting the chat, you can enter a specific question in the text box. If you do, the AI will answer that question directly instead of providing a general summary.
7.  **Start Chat**: Click the **"Start Chat"** button to begin the analysis and open the conversational chat window.
8.  **Stop Generation**: While the AI is generating a response, the "Send" button will turn into a red "Stop" button. Click it at any time to cancel the current analysis.
9.  **Ask Follow-up Questions**: Use the chat input to ask follow-up questions about the analyzed data.
10. **Clear & Start New**: Click the **"Clear & Start New"** button to clear the conversation and start a new analysis.
11. **Download Results**: Use the Download menu to export:
    - Text (.txt) and PDF (.pdf): text-only.
    - HTML (.html): images embedded inline via data URIs.
    - ZIP (.zip): transcript.txt, transcript_with_images.html referencing images/, images files, and manifest.json metadata.
    Use HTML or ZIP to include images in the export.

### About Threading (Why this matters for Telegram)
Telegram conversations often interleave replies across multiple topics, making it hard to follow context. The analyzer reconstructs Telegram reply chains, assigns a deterministic thread root, and presents replies under the correct root—resulting in coherent threads for summaries and Q&A. This dramatically reduces confusion when analyzing busy Telegram groups.

## Using the Bots

After registering a bot via the **"Manage Bots"** UI, you can interact with it directly in its respective chat application.

**Important**: For bots to receive messages from Webex or Telegram, your application must be accessible from the public internet. If running locally, you must use a tunneling service like **ngrok**.
1.  Start ngrok: `ngrok http 8000`
2.  Copy the public HTTPS URL (e.g., `https://abcdef123.ngrok.io`).
3.  Use this URL in the "Public Webhook URL" field when registering your bot in the UI. The application will set the webhook for you automatically.

### Webex Bot Usage
-   **Interaction**: Mention the bot in any space it has been added to.
-   **Example**: `@YourBotName summarize last 2 days`
-   **For more details, see the [Webex Bot Guide](webex_bot_guide.md)**.

### Telegram Bot Usage
-   **Interaction**: By default, the bot is in "Summarizer" mode. Send it a message in a private chat or a group it belongs to.
-   **Example**: `summarize last 3 days`
-   **Conversational AI Mode**: Send the `/aimode` command to toggle the bot into a conversational assistant. It will remember the context of your conversation. Send `/aimode` again to switch back to summarizer mode and clear the conversation history.
-   **For more details, see the [Telegram Bot Guide](telegram_bot_guide.md)**.

## Switching Services & Logging Out

-   **Switching**: You can be logged into both Telegram and Webex simultaneously. Use the **"Switch Service"** button to toggle between them.
-   **Logout**: Clicking **"Logout"** will sign you out of the currently active service. If you are logged into the other service, the app will switch to it; otherwise, it will return to the main login screen.
