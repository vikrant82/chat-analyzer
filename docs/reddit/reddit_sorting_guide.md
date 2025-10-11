# Reddit Post Sorting and Filtering Guide

## Overview

The Reddit integration now supports configurable post sorting and filtering options, giving you fine-grained control over what posts are displayed in the chat analyzer.

## Configuration Options

Add these settings to your `config.json` under the `reddit` section:

```json
"reddit": {
  "client_id": "YOUR_REDDIT_CLIENT_ID",
  "client_secret": "YOUR_REDDIT_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8000/api/auth/callback/reddit",
  "user_agent": "ChatAnalyzer/1.0",
  "subreddit_limit": 200,
  "popular_posts_limit": 15,
  "user_posts_limit": 10,
  "subreddit_posts_limit": 75,
  "default_sort": "top",
  "default_time_filter": "week"
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subreddit_limit` | integer | 200 | Maximum number of subscribed subreddits to fetch |
| `popular_posts_limit` | integer | 10 | Number of posts to fetch from r/popular |
| `user_posts_limit` | integer | 10 | Number of user's own posts to fetch |
| `subreddit_posts_limit` | integer | 50 | Number of posts to fetch when a subreddit is selected |
| `default_sort` | string | "hot" | Default sorting method for posts (see options below) |
| `default_time_filter` | string | "week" | Default time filter for "top" and "controversial" sorts |
| `subreddit_sort` | string | "subscribers" | How to sort subscribed subreddits: "subscribers", "alphabetical", or "activity" |
| `show_favorites` | boolean | true | Show favorited subreddits at the top of the list with a ⭐ icon |
| `favorites_limit` | integer | 50 | Maximum number of favorite subreddits to fetch |

### Sort Methods

- **`hot`**: Reddit's "hot" algorithm (trending + recent)
- **`new`**: Newest posts first
- **`top`**: Highest-scoring posts (requires `time_filter`)
- **`controversial`**: Most controversial posts (requires `time_filter`)
- **`rising`**: Posts that are rapidly gaining upvotes

### Time Filters

Used with `top` and `controversial` sorts:

- **`hour`**: Posts from the last hour
- **`day`**: Posts from the last 24 hours
- **`week`**: Posts from the last 7 days
- **`month`**: Posts from the last 30 days
- **`year`**: Posts from the last 365 days
- **`all`**: Posts from all time

### Subreddit Sort Methods

How your subscribed subreddits are ordered in the dropdown:

- **`subscribers`**: Most popular subreddits first (by member count) - **Default**
- **`alphabetical`**: A-Z ordering by subreddit name
- **`activity`**: Most active subreddits first (by current active users)

## Enhanced Display Metadata

Posts and subreddits now display rich metadata to help you identify relevant content:

### Favorite Subreddits (New!)
```
⭐ Subreddit: python [2.5M members]
⭐ Subreddit: learnprogramming [456.7K members]
⭐ Subreddit: webdev [234.5K members]
```

- **⭐ Star icon**: Indicates your favorited subreddits from your Reddit account
- **Always at top**: Favorites appear first in the dropdown (if `show_favorites` is enabled)
- **No duplicates**: Favorited subreddits won't appear again in the regular list
- **Same sorting**: Favorites use the same `subreddit_sort` method as regular subreddits

### Regular Subreddit Display
```
Subreddit: AskReddit [45.2M members]
Subreddit: programming [1.8M members]
```

- **Members count**: Shows subscriber count in K (thousands) or M (millions) notation
- Helps identify the most popular/active communities

### Post Display
```
Post Title [123⬆ 45💬 by u/username]
```

- **⬆**: Upvote score (indicates post popularity)
- **💬**: Comment count (indicates discussion activity)
- **by u/username**: Post author

## Examples

### High Engagement Configuration
For subreddits with lots of activity, fetch more posts sorted by top of the week:

```json
"reddit": {
  ...
  "subreddit_posts_limit": 100,
  "default_sort": "top",
  "default_time_filter": "week"
}
```

### New Content Focus
To always see the newest posts:

```json
"reddit": {
  ...
  "default_sort": "new",
  "subreddit_posts_limit": 50
}
```

### Controversial Topics
To find the most debated posts:

```json
"reddit": {
  ...
  "default_sort": "controversial",
  "default_time_filter": "day"
}
```

### Alphabetical Subreddit List
For easy browsing by name:

```json
"reddit": {
  ...
  "subreddit_sort": "alphabetical"
}
```

### Most Active Communities First
To see your most active subreddits at the top:

```json
"reddit": {
  ...
  "subreddit_sort": "activity"
}
```

### Disable Favorites
If you don't want favorites shown separately:

```json
"reddit": {
  ...
  "show_favorites": false
}
```

## How to Favorite Subreddits on Reddit

To mark subreddits as favorites in your Reddit account:

1. **On Reddit.com** (Desktop):
   - Visit the subreddit
   - Click the "..." menu or "Subscribe" button
   - Look for "Favorite" or "Add to favorites" option
   - Click to toggle favorite status

2. **On Reddit Mobile App**:
   - Visit the subreddit
   - Tap the bell icon or subscription options
   - Enable "Favorite" to mark it as a favorite

3. **Reddit Enhancement Suite (RES)**:
   - Use the star icon next to subreddit names to favorite them

Once favorited in your Reddit account, they'll automatically appear at the top of the Chat Analyzer dropdown with a ⭐ icon!

## Implementation Details

### Code Changes

1. **`RedditClient.__init__()`**: Now loads all configuration parameters with sensible defaults, including `subreddit_sort`, `show_favorites`, and `favorites_limit`
2. **`RedditClient._fetch_posts_with_sort()`**: New helper method that supports all Reddit sorting methods
3. **`RedditClient.get_favorite_subreddits()`**: New method that:
   - Fetches subreddits where `user_has_favorited == True`
   - Adds ⭐ icon prefix to titles
   - Sorts using the same `subreddit_sort` configuration
   - Respects `favorites_limit` setting
4. **`RedditClient.get_chats()`**: Enhanced to:
   - Show favorite subreddits first (if `show_favorites` is enabled)
   - Fetch subreddit metadata (subscribers, active users)
   - Sort subreddits based on `subreddit_sort` configuration
   - Display member counts in the UI
   - Avoid duplicate listings (favorites won't appear in regular list)
   - Use configured limits and display post metadata
5. **`RedditClient.get_posts_for_subreddit()`**: Now accepts optional `sort_method` and `time_filter` parameters

### Backward Compatibility

All parameters have defaults, so existing configurations without these settings will continue to work:

- `subreddit_limit`: 200
- `popular_posts_limit`: 10
- `user_posts_limit`: 10
- `subreddit_posts_limit`: 50
- `default_sort`: "hot"
- `default_time_filter`: "week"
- `subreddit_sort`: "subscribers"
- `show_favorites`: true
- `favorites_limit`: 50

## Testing the Changes

### 1. Update Configuration

Add the new Reddit configuration parameters to your `config.json` file.

### 2. Test Different Sort Methods

Try these configurations to verify different sorting works:

**Hot Posts:**
```json
"default_sort": "hot"
```

**Top Posts of the Day:**
```json
"default_sort": "top",
"default_time_filter": "day"
```

**Rising Posts:**
```json
"default_sort": "rising"
```

### 3. Verify Metadata Display

When you select a subreddit, you should see:
- Upvote scores (⬆)
- Comment counts (💬)
- Author usernames

### 4. Test Different Limits

Change the limits and verify the correct number of items are fetched:

```json
"subreddit_posts_limit": 25,
"popular_posts_limit": 5
```

## Performance Considerations

- **Higher Limits**: Increasing limits will increase API calls and load time
- **Sort Methods**: "new" and "hot" are faster than "top" and "controversial"
- **Time Filters**: Narrower time filters (hour, day) are faster than broader ones (year, all)

## Recommended Settings

### For Active Subreddits (high post volume)
```json
"subreddit_posts_limit": 50,
"default_sort": "hot",
"default_time_filter": "day"
```

### For Research/Analysis (comprehensive coverage)
```json
"subreddit_posts_limit": 100,
"default_sort": "top",
"default_time_filter": "week"
```

### For Quick Browsing (fast loading)
```json
"subreddit_posts_limit": 25,
"default_sort": "hot"
```

## API Reference

### get_posts_for_subreddit()

```python
async def get_posts_for_subreddit(
    self, 
    user_identifier: str, 
    subreddit_name: str, 
    sort_method: str = None, 
    time_filter: str = None
) -> List[Chat]
```

**Parameters:**
- `user_identifier`: Reddit username
- `subreddit_name`: Name of the subreddit (without "r/" prefix)
- `sort_method`: Optional override for sorting (hot, new, top, controversial, rising)
- `time_filter`: Optional override for time filter (hour, day, week, month, year, all)

**Returns:** List of Chat objects with enhanced metadata

## Future Enhancements

Potential future improvements:
1. UI controls to change sort method without editing config
2. Per-subreddit sort preferences
3. Advanced filters (minimum score, minimum comments, specific authors)
4. Custom sorting algorithms (engagement ratio, comment/upvote ratio)
5. Post age filters independent of sorting

## Troubleshooting

### Posts Not Appearing

**Symptom:** Empty list when selecting a subreddit

**Solutions:**
- Check that your Reddit account has access to the subreddit
- Verify the subreddit name is spelled correctly
- Try increasing `subreddit_posts_limit`
- Try changing `default_sort` to "hot" or "new"

### Slow Loading

**Symptom:** Long wait times when loading posts

**Solutions:**
- Reduce `subreddit_posts_limit`
- Use "hot" or "new" instead of "top" or "controversial"
- Use narrower time filters (day instead of year)

### Missing Metadata

**Symptom:** Posts don't show upvotes or comments

**Solutions:**
- This is expected for very new posts (may have 0 upvotes/comments)
- Check that you're using the latest version of the code
- Verify your Reddit API permissions include "read" scope

## Related Documentation

- [Reddit Guide](./reddit_guide.md) - General Reddit integration setup
- [User Guide](./user_guide.md) - Overall application usage
- [Configuration Guide](../readme.md) - Main configuration reference

