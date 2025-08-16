# Reddit Integration Guide

This guide explains how to connect your Reddit account to the Chat Analyzer and use its features to analyze posts and comments.

## 1. Creating a Reddit Application

To allow the Chat Analyzer to access your Reddit account, you must first create a "script" application on Reddit's website.

1.  **Log in to Reddit** with the account you want to use.
2.  Go to the [Reddit Apps](https://www.reddit.com/prefs/apps) page.
3.  Scroll to the bottom and click the **"are you a developer? create an app..."** button.
4.  Fill out the form:
    *   **Name:** Give your application a name (e.g., "Chat Analyzer").
    *   **Type:** Select **"script"**.
    *   **Description:** (Optional)
    *   **About URL:** (Optional)
    *   **Redirect URI:** This is the most important step. You must enter the exact callback URL for the application. For a local setup, this is:
        `http://localhost:8000/api/auth/callback/reddit`
5.  Click **"create app"**.

After creating the app, you will be shown your credentials.

-   The **"personal use script"** key is your **`client_id`**.
-   The **"secret"** key is your **`client_secret`**.

Copy these two values into your `config.json` file.

## 2. Configuring the Application

Add the following section to your `config.json` file, filling in the values you obtained from the Reddit app page:

```json
"reddit": {
  "client_id": "YOUR_REDDIT_CLIENT_ID",
  "client_secret": "YOUR_REDDIT_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8000/api/auth/callback/reddit",
  "user_agent": "ChatAnalyzer/0.1 by YourUsername"
},
```

-   Replace `YOUR_REDDIT_CLIENT_ID` and `YOUR_REDDIT_CLIENT_SECRET` with your credentials.
-   The `user_agent` can be any descriptive string.

## 3. Using the Reddit Integration

Once configured, start the Chat Analyzer application.

1.  On the login screen, select **"Reddit"** from the "Chat Service" dropdown.
2.  Click the **"Login with Reddit"** button.
3.  You will be redirected to Reddit to authorize the application. Click **"Allow"**.
4.  You will be redirected back to the Chat Analyzer, now logged in.

### Selecting a Chat

The "Select a Chat" dropdown for Reddit works differently from other services:

-   **Subscribed Subreddits:** The dropdown will be populated with a list of subreddits you are subscribed to. Selecting one of these will reveal a second dropdown, "Select a Post," containing the top "hot" posts from that subreddit.
-   **Popular Posts:** The dropdown also contains a list of current popular posts from r/popular for quick access.
-   **My Posts:** A list of your own most recent posts is also included.

To start an analysis, you must select a specific **post**. You can either select one directly from the "Popular" or "My Posts" groups, or you can select a subreddit first and then a post from the second dropdown.
