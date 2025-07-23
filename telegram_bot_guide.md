# Telegram Bot Integration Guide for Chat Analyzer

This guide provides step-by-step instructions for creating, configuring, and using a Telegram bot with the Chat Analyzer application.

## 1. Creating Your Telegram Bot

All Telegram bots are created and managed through a special bot called `@BotFather`.

1.  **Start a chat with `@BotFather`:** Open Telegram and search for the user `@BotFather` (it has a blue checkmark). Start a chat with it.
2.  **Create a new bot:** Send the `/newbot` command to `@BotFather`.
3.  **Name your bot:** It will ask for a name for your bot. This is the display name, like "My Project Analyzer".
4.  **Choose a username:** It will then ask for a username. This must be unique and end in `bot`. For example: `my_project_analyzer_bot`.
5.  **Save your token:** `@BotFather` will provide you with a unique API token. **This is very important and should be kept private.** Copy this token immediately.

## 2. Registering Your Bot in Chat Analyzer

After creating your bot and getting the API token, you need to register it within the Chat Analyzer application. This allows the app to use your bot for sending messages.

1.  **Navigate to the Bot Management Page:**
    *   Open the Chat Analyzer web interface in your browser.
    *   Find and click on the **"Manage Bots"** button, which will take you to the bot configuration page.

2.  **Enter Bot Details:**
    *   You will see a form asking for your bot's information.
    *   **Bot Token:** Carefully paste the API token you received from `@BotFather` into this field.
    *   **Webhook Domain:** Enter the public-facing URL where your Chat Analyzer application is hosted (e.g., `https://your-app-domain.com`). This is crucial for Telegram to send updates to your app.

3.  **Save Configuration:**
    *   Once you've filled in the details, click the **"Save"** or **"Add Bot"** button.

The application will verify the token and set up the webhook. If successful, your bot is now registered and ready to be used.

## 3. Usage and Features

Your bot has two primary modes of operation.

### Default: Summarizer Mode

By default, the bot functions as a chat summarizer. When you mention the bot in a group chat, it will analyze the recent conversation history and provide a concise summary.

### Conversational AI Mode (`/aimode`)

You can switch the bot into a general-purpose conversational AI.

*   **To activate:** Type the command `/aimode` in a chat with the bot.
*   **Functionality:** In this mode, instead of summarizing, the bot will act as a helpful AI assistant, answering general questions, providing information, or just chatting. It uses the context of the current conversation to inform its responses.
*   **To deactivate:** Type `/aimode` again to toggle it back to the default Summarizer Mode.

## 4. Troubleshooting & Gotchas

Please read this section carefully to avoid common issues.

### Group Chat Privacy Mode

By default, Telegram bots operate in **Privacy Mode**. This means they will *not* receive all messages sent to a group chat, only commands (`/start`, etc.) and messages that explicitly mention them. For the Chat Analyzer to work correctly, you **must disable privacy mode**.

**How to Disable Privacy Mode:**

1.  Go back to your chat with `@BotFather`.
2.  Send the `/mybots` command.
3.  Select the bot you created.
4.  Click on "Bot Settings".
5.  Click on "Group Privacy".
6.  Click the "Turn off" button. It should now say "Privacy: DISABLED".

### Group Chat Mentions

Even with privacy mode disabled, our bot is configured for efficiency. In a group chat, it will only process and respond to messages under two conditions:

1.  When it is **explicitly mentioned** (e.g., `@my_project_analyzer_bot, what was discussed?`).
2.  When a user **replies directly** to one of the bot's own messages.

This prevents the bot from spamming the chat and ensures it only engages when needed.

### User vs. Bot Sessions Explained

It's important to understand how the application interacts with Telegram:

*   **Reading History (Your Account):** The application uses your main Telegram account (the one logged in with your phone number) to *read* the chat history for analysis. This is necessary because bots cannot access historical messages before they were added to a group.
*   **Sending Messages (Bot's Account):** The application uses your newly created **bot's token** to *send* messages back into the chat.

This dual-account system allows the Chat Analyzer to both analyze past conversations and participate actively as a bot.