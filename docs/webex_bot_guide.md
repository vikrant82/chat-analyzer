# Webex Bot Setup Guide

This guide provides step-by-step instructions for creating a Webex bot and registering it with the Chat Analyzer application.

**Note:**
- **Threading:** Conversation threading is preserved in summaries. The application uses native Webex thread IDs to group messages, ensuring responses remain thread-aware.
- **Image Processing:** Image analysis is supported and can be configured globally from the main UI (enabled/disabled, max size, allowed MIME types).
- **Date Handling:** Analysis uses a local-day concept based on the user’s browser timezone (IANA tz).

## 1. Creating a Webex Bot

First, you need to create a new bot in the Webex Developer Portal.

1.  **Navigate to the Webex Developer Portal:** Open your browser and go to `https://developer.webex.com`.
2.  **Log In and Go to My Apps:** Log in with your Webex account and navigate to "My Apps" from the user menu in the top-right corner.
3.  **Create a New Bot:** Click on "Create a New App" and then select "Create a Bot".
4.  **Fill in Bot Details:**
    *   **Bot name:** A user-friendly name that will be displayed in Webex (e.g., "Chat Analyzer Bot").
    *   **Bot username:** A unique identifier for your bot (e.g., `chatanalyzer@webex.bot`).
    *   **Icon:** Upload a custom icon for your bot.
    *   **Description:** A brief description of what your bot does.
5.  **Get the Bot Access Token & ID:** After creating the bot, you will be taken to its configuration page.
    *   Copy the **Bot access token**.
    *   Find the **Bot ID** (this is a long, Base64-encoded string).
    *   Both are required to register the bot in the Chat Analyzer UI.

## 2. Registering the Bot in Chat Analyzer

Next, register the new bot in the Chat Analyzer web UI. This process also handles the webhook setup automatically.

1.  **Expose Your Application (if running locally):** For Webex to send messages to your bot, your application must be accessible from the public internet. If you are running the Chat Analyzer locally, you must use a tunneling service like **ngrok**.
    *   Start ngrok: `ngrok http 8000`
    *   Copy the public HTTPS URL provided by ngrok (e.g., `https://abcdef123.ngrok.io`). This is your **Public Webhook URL**.

2.  **Open the Chat Analyzer UI:** Navigate to the application in your browser and log in.
3.  **Go to Bot Management:** Click the **"Manage Bots"** button.
4.  **Enter Bot Details:**
    *   **Bot Name:** Enter the name you gave your bot.
    *   **Bot ID:** Paste the **Bot ID** you copied from the Webex Developer Portal.
    *   **Bot Token:** Paste the **Bot access token**.
    *   **Public Webhook URL:** Paste the public URL of your application (e.g., your ngrok URL).
5.  **Register:** Click the "Register Bot" button. The application will use this information to save the bot's configuration and automatically create the necessary webhook in Webex for you.

## 3. Usage and Features

The Webex bot is now ready to use.

*   **Adding the Bot to a Space:** Add the bot to any Webex space just like you would add a regular user.
*   **Mentioning the Bot:** The bot will only listen for messages where it is directly @-mentioned.
*   **Example Command:** `@YourBotName summarize last 2 days`
*   **Downloads:** After an analysis is run from the UI, you can download the results as:
    - Text (`.txt`): text-only.
    - PDF (`.pdf`): includes embedded images.
    - HTML (`.html`): includes images embedded inline.
    - ZIP (`.zip`): a bundle containing the transcript, all images, and a metadata file.