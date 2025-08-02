# Webex Bot Setup Guide

This guide provides step-by-step instructions for creating a Webex bot, registering it with the Chat Analyzer, and making it available for users.

Note:
- Threading context is preserved in summaries. Webex native thread IDs are grouped, and the transcript includes explicit thread boundary markers so responses remain thread-aware.
- Image processing is supported and configurable globally (enabled flag, max size, optional allowed MIME types). When enabled, images may be included in analysis if within limits.
- Date handling uses a local-day concept based on the user’s browser timezone (IANA tz).

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
5.  **Get the Bot Access Token:** After creating the bot, you will be taken to its configuration page. Find the **Bot access token** and copy it. This token is required to register the bot with the Chat Analyzer.

## 2. Registering the Bot in Chat Analyzer

Next, register the new bot in the Chat Analyzer web UI.

1.  **Open the Chat Analyzer UI:** Navigate to the Chat Analyzer application in your browser.
2.  **Go to Bot Registration:** Find the section for registering new bots.
3.  **Enter Bot Details:**
    *   **Bot Name:** Enter the name you gave your bot.
    *   **Access Token:** Paste the "Bot access token" you copied from the Webex Developer Portal.
4.  **Save:** Save the configuration. The Chat Analyzer is now authenticated to use your bot.

## 3. Webhook Setup

For the bot to receive messages, you must create a webhook that points from Webex to the Chat Analyzer application.

1.  **Webhook URL:** The webhook must point to the Chat Analyzer's API endpoint for Webex. The URL will have the following structure:
    `https://your-app-url.com/api/bot/webex/webhook`
    Replace `your-app-url.com` with the actual public URL of your Chat Analyzer instance.
2.  **Create the Webhook in Webex:**
    *   Go back to your bot's settings page on the Webex Developer Portal.
    *   Click on the "Webhooks" tab.
    *   Click "Add Webhook" and fill in the details:
        *   **Name:** A descriptive name for your webhook.
        *   **Target URL:** The full webhook URL from the previous step.
        *   **Resource:** Select "messages".
        *   **Event:** Select "created".
    *   Save the webhook.

## 4. Usage and Features

The Webex bot is now ready to use.

*   **Adding the Bot to a Space:** Add the bot to any Webex space just like you would add a regular user.
*   **Mentioning the Bot:** The bot will only listen for messages where it is directly @-mentioned.
*   **Default Behavior:** The default summarizer will respond to requests like:
    `@BotName summarize last 2 days`