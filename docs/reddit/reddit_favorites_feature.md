# Reddit Favorites Feature

## Overview

The Chat Analyzer now automatically displays your **favorited subreddits** at the top of the dropdown, making it easy to quickly access your most important communities!

## What Are Favorites?

Favorites are subreddits you've marked as special in your Reddit account. They're displayed with a ⭐ star icon and always appear at the top of the subreddit list in Chat Analyzer.

## How It Works

### 1. Mark Favorites on Reddit

First, favorite subreddits in your Reddit account using any of these methods:

**On Reddit.com (Desktop):**
1. Visit the subreddit you want to favorite
2. Click the "..." menu or subscription options
3. Look for "Favorite" or "Add to favorites"
4. Click to toggle favorite status

**On Reddit Mobile App:**
1. Visit the subreddit
2. Tap the bell icon or subscription menu
3. Enable "Favorite"

**Reddit Enhancement Suite (RES):**
- Use the star icon next to subreddit names

### 2. See Them in Chat Analyzer

Once you've favorited subreddits in Reddit, they'll automatically appear at the top of the Chat Analyzer dropdown:

```
Select a Chat:
├─ ⭐ Subreddit: python [2.5M members]           ← Your favorites
├─ ⭐ Subreddit: learnprogramming [456.7K members]
├─ ⭐ Subreddit: webdev [234.5K members]
├─ Subreddit: AskReddit [45.2M members]         ← Regular subscriptions
├─ Subreddit: programming [1.8M members]
└─ ...
```

## Configuration

### Enable/Disable Favorites

Add these settings to your `config.json` under the `reddit` section:

```json
"reddit": {
  ...
  "show_favorites": true,
  "favorites_limit": 50
}
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `show_favorites` | boolean | true | Show favorited subreddits at the top with ⭐ icon |
| `favorites_limit` | integer | 50 | Maximum number of favorites to fetch |

### Disable Favorites

If you don't want favorites shown separately:

```json
"show_favorites": false
```

Favorites will then be mixed with regular subreddits (no star icon, no special positioning).

## Features

### ⭐ Visual Distinction
- Favorites have a star emoji (⭐) prefix
- Easy to identify at a glance
- Consistent with Reddit's favorites concept

### 🔝 Priority Positioning
- Always appear at the top of the dropdown
- Before all other subreddits
- Quick access to your most important communities

### 🚫 No Duplicates
- Favorited subreddits won't appear twice
- Automatically excluded from the regular subreddit list
- Clean, organized dropdown

### 📊 Rich Metadata
- Same member count display as regular subreddits
- Shows subscriber counts (K/M notation)
- Example: `⭐ Subreddit: python [2.5M members]`

### 🔀 Consistent Sorting
- Favorites use the same `subreddit_sort` setting
- Sort by subscribers, alphabetically, or by activity
- Example: With `"subreddit_sort": "subscribers"`, favorites are sorted by popularity

## Examples

### Example 1: Tech Professional

**Favorites on Reddit:**
- r/python
- r/programming
- r/webdev

**Result in Chat Analyzer:**
```
⭐ Subreddit: python [2.5M members]
⭐ Subreddit: programming [1.8M members]
⭐ Subreddit: webdev [456.7K members]
─────────────────────────────────────
Subreddit: AskReddit [45.2M members]
Subreddit: learnprogramming [234.5K members]
...
```

### Example 2: Researcher with Many Subscriptions

Without favorites: Scroll through 200 subreddits to find r/MachineLearning

With favorites: It's at position #1 with a star icon!

### Example 3: Alphabetical Sorting with Favorites

**Configuration:**
```json
"subreddit_sort": "alphabetical",
"show_favorites": true
```

**Result:**
```
⭐ Subreddit: learnprogramming [456.7K members]  ← Favorites (alphabetical)
⭐ Subreddit: python [2.5M members]
⭐ Subreddit: webdev [234.5K members]
Subreddit: AskReddit [45.2M members]              ← Regular (alphabetical)
Subreddit: coding [123.4K members]
...
```

## Use Cases

### 1. Quick Access to Work Communities
Favorite your work-related subreddits (tech, industry-specific) to access them instantly.

### 2. Research Projects
Mark subreddits relevant to your current research for easy access during analysis sessions.

### 3. Content Monitoring
Favorite communities you need to monitor regularly for trending topics or discussions.

### 4. Personal Interests
Keep your favorite hobby/interest subreddits at the top for quick browsing.

## Technical Details

### How Favorites Are Detected

The Chat Analyzer reads the `user_has_favorited` attribute from Reddit's API:

```python
is_favorited = getattr(sub, 'user_has_favorited', False)
```

This is a **server-side** attribute managed by Reddit, not a client-side setting.

### Performance

- **Single API Call**: Favorites are detected during the regular subreddit fetch
- **No Extra Delay**: No additional API requests needed
- **Efficient Filtering**: Uses Python's built-in filtering (O(n) complexity)
- **Deduplication**: Set-based tracking prevents duplicates (O(1) lookup)

### Sorting Logic

Favorites use the **same sorting method** as regular subreddits:

1. Fetch all subscribed subreddits
2. Filter where `user_has_favorited == True`
3. Sort using `subreddit_sort` configuration
4. Add ⭐ prefix
5. Return as separate list

Regular subreddits are then filtered to exclude favorites and sorted the same way.

## Troubleshooting

### Favorites Not Showing

**Problem:** No favorites appear even though you have favorites on Reddit

**Solutions:**
1. Check that `"show_favorites": true` in config.json
2. Verify you're logged into the correct Reddit account
3. Ensure you've actually favorited subreddits on Reddit
4. Try refreshing the chat list in the UI
5. Restart the application to reload configuration

### Star Icon Not Displaying

**Problem:** Favorites show but without the ⭐ icon

**Solutions:**
1. Check your browser/terminal supports Unicode emoji
2. Try a different font that supports emoji
3. The star is there - it might render differently on some systems

### Too Many/Few Favorites

**Problem:** Want to show more or fewer favorites

**Solution:**
```json
"favorites_limit": 100  // Or any number you prefer
```

### Favorites in Wrong Order

**Problem:** Favorites aren't sorted how you want

**Solution:** Change the `subreddit_sort` setting:
```json
"subreddit_sort": "alphabetical"  // Or "activity" or "subscribers"
```

Both favorites and regular subreddits use the same sort method.

## FAQ

**Q: Do I need to configure anything in Chat Analyzer to use favorites?**  
A: No! Favorites are enabled by default. Just favorite subreddits in your Reddit account and they'll appear automatically.

**Q: Can I disable favorites?**  
A: Yes, set `"show_favorites": false` in config.json

**Q: Will favoriting a subreddit in Chat Analyzer sync back to Reddit?**  
A: No, Chat Analyzer is read-only. You must favorite subreddits in Reddit itself.

**Q: How many favorites can I have?**  
A: Reddit doesn't have a built-in limit, but Chat Analyzer will fetch up to `favorites_limit` (default: 50).

**Q: Do favorites affect the regular subreddit list?**  
A: Yes - favorites won't appear in the regular list to avoid duplicates.

**Q: Can I have different sorting for favorites vs regular subreddits?**  
A: Currently they use the same `subreddit_sort` setting. This keeps the UI consistent.

**Q: What happens if a favorite is also in r/popular?**  
A: The favorite will appear with a star at the top. If it's also in the popular posts section, it will appear there too (different context).

## Benefits

1. **Faster Navigation**: Immediate access to your most important subreddits
2. **Better Organization**: Clear separation between favorites and all subscriptions
3. **Synced with Reddit**: Automatically uses your Reddit account favorites
4. **Zero Configuration**: Works out of the box
5. **Visual Clarity**: Star icon makes favorites instantly recognizable
6. **No Duplicates**: Clean list without redundant entries
7. **Flexible**: Can be disabled or configured as needed

## Related Documentation

- **How to Favorite**: [Reddit Sorting Guide - How to Favorite Subreddits](./reddit_sorting_guide.md#how-to-favorite-subreddits-on-reddit)
- **Configuration**: [Reddit Sorting Guide - Configuration](./reddit_sorting_guide.md#configuration-parameters)
- **Main Guide**: [Reddit Integration Guide](./reddit_guide.md)

## Summary

The favorites feature brings your Reddit account's favorite subreddits directly into Chat Analyzer, displaying them prominently at the top of the list with a ⭐ icon. It's zero-configuration, performant, and makes navigating to your most important communities faster and easier!

