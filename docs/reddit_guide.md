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

### Workflows

The Reddit backend offers two distinct, streamlined workflows, which you can switch between using the "Select a Workflow" radio buttons:

-   **Analyze a Subreddit**: This workflow allows you to perform a deep analysis of a specific post and its entire comment tree.
    1.  Select the "Analyze a Subreddit" workflow.
    2.  In the "Select a Chat" dropdown, choose a source for posts. This list contains your subscribed subreddits, popular posts from r/popular, and your own recent posts.
    3.  If you select a subreddit, a second dropdown, "Select a Post," will appear, containing the top "hot" posts from that subreddit.
    4.  Select a post from either the main dropdown or the second one.
    5.  Click the main **"Start Chat"** button to begin the analysis.

-   **Summarize from URL**: This workflow allows you to quickly get a summary of any Reddit post.
    1.  Select the "Summarize from URL" workflow.
    2.  Paste the full URL of the Reddit post into the "Paste a Reddit Post URL" text box.
    3.  Click the main **"Start Chat"** button to begin the analysis.

### Image Processing

The Reddit backend now supports fetching and analyzing images from posts and comments.

-   **Supported Image Types:**
    -   **Direct Links:** Posts that are a direct link to an image file (e.g., `.jpg`, `.png`).
    -   **Reddit Galleries:** Posts that contain multiple images in a gallery format.
    -   **Inline Links:** Image URLs found within the text of the main post or any of its comments.
-   **Enabling Image Processing:** To enable this feature, simply check the **"Enable Image Processing"** checkbox before starting the chat.
