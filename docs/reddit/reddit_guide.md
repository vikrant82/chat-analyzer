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

## 2.1 Advanced Configuration (Optional)

The Reddit integration supports advanced sorting and filtering options. Add these optional settings to your `reddit` configuration:

```json
"reddit": {
  "client_id": "YOUR_REDDIT_CLIENT_ID",
  "client_secret": "YOUR_REDDIT_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8000/api/auth/callback/reddit",
  "user_agent": "ChatAnalyzer/0.1 by YourUsername",
  "subreddit_limit": 200,
  "popular_posts_limit": 15,
  "user_posts_limit": 10,
  "subreddit_posts_limit": 75,
  "default_sort": "top",
  "default_time_filter": "week",
  "subreddit_sort": "subscribers"
}
```

**New Settings Explained:**

- `subreddit_limit`: Number of subscribed subreddits to fetch (default: 200)
- `popular_posts_limit`: Number of posts from r/popular to show (default: 10)
- `user_posts_limit`: Number of your own posts to show (default: 10)
- `subreddit_posts_limit`: Number of posts to fetch when you select a subreddit (default: 50)
- `default_sort`: How posts are sorted - `"hot"`, `"new"`, `"top"`, `"controversial"`, or `"rising"` (default: "hot")
- `default_time_filter`: For "top" and "controversial" sorts - `"hour"`, `"day"`, `"week"`, `"month"`, `"year"`, or `"all"` (default: "week")
- `subreddit_sort`: How subscribed subreddits are ordered - `"subscribers"`, `"alphabetical"`, or `"activity"` (default: "subscribers")
- `show_favorites`: Show favorited subreddits at the top with a ⭐ icon (default: true)
- `favorites_limit`: Maximum number of favorite subreddits to fetch (default: 50)

**What this means:** With `"default_sort": "top"` and `"default_time_filter": "week"`, you'll see the highest-scoring posts from the last 7 days when you select a subreddit.

For detailed information about sorting and filtering, see **[Reddit Sorting & Filtering Guide](reddit_sorting_guide.md)**.

For information about using favorites, see **[Reddit Favorites Feature Guide](reddit_favorites_feature.md)**.

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
    3.  If you select a subreddit, a second dropdown, "Select a Post," will appear, containing posts from that subreddit (sorted according to your `default_sort` configuration - see section 2.1).
    4.  Select a post from either the main dropdown or the second one. Posts now display metadata including upvotes (⬆), comments (💬), and author.
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

## 4. Advanced Features

### Favorite Subreddits

Your favorited subreddits from your Reddit account are automatically displayed at the top of the dropdown:

- **⭐ Star Icon**: Favorites are marked with a star for easy identification
- **Always on Top**: Appear before all other subreddits
- **Syncs with Reddit**: Uses your actual Reddit favorites (set via Reddit.com or mobile app)
- **No Duplicates**: Favorites won't appear again in the regular subreddit list
- **Configurable**: Can be disabled with `"show_favorites": false`

### Subreddit Sorting

Subscribed subreddits can now be intelligently ordered:

- **By Subscribers** (default): Most popular subreddits first
- **Alphabetically**: A-Z ordering for easy browsing
- **By Activity**: Most active communities first (based on current active users)
- **Member Counts**: Subreddits display subscriber counts (e.g., "Subreddit: python [2.5M members]")

### Post Sorting & Filtering

The Reddit integration supports configurable post sorting and filtering to help you find the most relevant content:

- **Multiple Sort Methods**: Choose from hot, new, top, controversial, or rising
- **Time Filters**: For "top" and "controversial", filter by time period (hour, day, week, month, year, all)
- **Rich Metadata**: Posts display upvotes (⬆), comments (💬), and author information
- **Adjustable Limits**: Configure how many posts to fetch for each category

**Example:** With `"default_sort": "top"` and `"default_time_filter": "week"`, you'll see the highest-scoring posts from the last 7 days.

For complete details, configuration examples, and troubleshooting, see the **[Reddit Sorting & Filtering Guide](reddit_sorting_guide.md)**.

### Recent Changes

For a summary of recent improvements to the Reddit integration, see **[Reddit Changelog (October 2025)](reddit_changelog_2025-10.md)**.
