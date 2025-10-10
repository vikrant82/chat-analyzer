# Telegram Bot Integration Guide

This guide provides step-by-step instructions for creating, configuring, and using a Telegram bot with the Chat Analyzer application.

**Important Notes:**
- **Threading Preservation:** Telegram does not have native threads like Webex. The app reconstructs threads by following reply chains to provide more coherent context to the AI.
- **Image Processing:** Images from Telegram can be included in the analysis when the global Image Processing option is enabled in the main UI.

## 1. Creating Your Telegram Bot

All Telegram bots are created and managed through a special bot called `@BotFather`.

1.  **Start a chat with `@BotFather`:** Open Telegram and search for the user `@BotFather` (it has a blue checkmark).
2.  **Create a new bot:** Send the `/newbot` command to `@BotFather`.
3.  **Name your bot:** Provide a display name, like "My Project Analyzer".
4.  **Choose a username:** Provide a unique username that ends in `bot` (e.g., `my_project_analyzer_bot`).
5.  **Save your token:** `@BotFather` will give you a unique API token. **Keep this token private.** You will need it for the next step.

## 2. Registering Your Bot in Chat Analyzer

After creating your bot, you must register it in the Chat Analyzer UI. This process also handles the webhook setup automatically.

1.  **Expose Your Application (if running locally):** For Telegram to send messages to your bot, your application must be accessible from the public internet. If you are running the Chat Analyzer locally, you must use a tunneling service like **ngrok**.
    *   Start ngrok: `ngrok http 8000`
    *   Copy the public HTTPS URL provided by ngrok (e.g., `https://abcdef123.ngrok.io`). This is your **Public Webhook URL**.

2.  **Navigate to the Bot Management Page:**
    *   Open the Chat Analyzer web interface and log in.
    *   Click the **"Manage Bots"** button.

3.  **Enter Bot Details:**
    *   **Bot Name:** Enter the name you gave your bot.
    *   **Bot Token:** Paste the API token you received from `@BotFather`.
    *   **Public Webhook URL:** Paste the public URL of your application (e.g., your ngrok URL).

4.  **Register:** Click the "Register Bot" button. The application will save the configuration and automatically set the webhook with Telegram.

## 3. Usage and Features

Your bot has two primary modes of operation.

### Default: Summarizer Mode
By default, the bot functions as a chat summarizer. When you send a message like `summarize last 3 days` in a private chat or a group where the bot is mentioned, it will analyze the history and provide a summary.

### Conversational AI Mode (`/aimode`)
You can switch the bot into a general-purpose conversational AI.
*   **To activate:** Type the command `/aimode` in a chat with the bot.
*   **Functionality:** In this mode, the bot acts as a helpful AI assistant, remembering the context of your conversation.
*   **To deactivate:** Type `/aimode` again to toggle it back to the default Summarizer Mode. This will also clear the bot's conversational memory.

### Downloads
From the main web UI, you can export the analyzed conversation in several formats:
- Text (`.txt`): text-only.
- PDF (`.pdf`): includes embedded images.
- HTML (`.html`): includes images embedded inline.
- ZIP (`.zip`): a bundle containing the transcript, all images, and a metadata file.

## 4. Important Considerations

### Group Chat Privacy Mode
By default, Telegram bots operate in **Privacy Mode**, meaning they only receive commands or direct mentions. For the analyzer to see all messages in a group (which is necessary for summarization), you **must disable privacy mode**.

**How to Disable Privacy Mode:**
1.  Go back to your chat with `@BotFather`.
2.  Send the `/mybots` command and select your bot.
3.  Go to **Bot Settings** -> **Group Privacy**.
4.  Click the **"Turn off"** button. It should now say "Privacy: DISABLED".

### Group Chat Mentions
In a group chat, the bot will only process and respond to messages that **explicitly mention it** (e.g., `@my_analyzer_bot, what was discussed?`) or are **direct replies** to one of its own messages. This prevents the bot from spamming the chat.

### User vs. Bot Sessions Explained
It's important to understand how the application interacts with Telegram:
*   **Reading History (Your Account):** The application uses your main Telegram account (logged in via the UI) to *read* the chat history. This is necessary because bots cannot access historical messages from before they were added to a group.
*   **Sending Messages (Bot's Account):** The application uses your bot's token to *send* messages back into the chat.