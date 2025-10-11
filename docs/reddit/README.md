# Reddit Integration Documentation

This folder contains all documentation for the Chat Analyzer Reddit integration.

## Quick Start

**New to Reddit integration?** Start here:
- 📖 **[Reddit Guide](reddit_guide.md)** - Setup, configuration, and usage

## Feature Documentation

### Core Features
- 🔍 **[Sorting & Filtering Guide](reddit_sorting_guide.md)** - Configure post sorting, time filters, and subreddit ordering
- ⭐ **[Favorites Feature](reddit_favorites_feature.md)** - Using Reddit favorites for quick access
- 📊 **[Visual Examples](reddit_favorites_visual_example.md)** - Before/after comparisons and real-world examples

### Comparisons & References
- 🔄 **[Subreddit Ordering Comparison](reddit_subreddit_ordering_comparison.md)** - How ordering improvements work
- 📋 **[Changelog October 2025](reddit_changelog_2025-10.md)** - What changed and why
- 🛠️ **[Backend Documentation](reddit_backend.md)** - Technical backend details

### Implementation Details
- 📝 **[Favorites Implementation Summary](REDDIT_FAVORITES_IMPLEMENTATION_SUMMARY.md)** - Technical details of favorites feature
- 📝 **[Subreddit Sorting Summary](SUBREDDIT_SORTING_SUMMARY.md)** - Technical details of sorting feature

## Features at a Glance

### Post Sorting
- **5 sort methods**: hot, new, top, controversial, rising
- **6 time filters**: hour, day, week, month, year, all
- **Rich metadata**: upvotes ⬆, comments 💬, authors

### Subreddit Management
- **3 sort methods**: by subscribers, alphabetically, by activity
- **Member counts**: Displayed in K/M notation
- **Favorites support**: ⭐ Auto-synced from Reddit account

### Configuration
```json
{
  "subreddit_limit": 200,
  "subreddit_posts_limit": 75,
  "default_sort": "top",
  "default_time_filter": "week",
  "subreddit_sort": "subscribers",
  "show_favorites": true,
  "favorites_limit": 50
}
```

## Common Tasks

### Change Post Sorting
Edit `config.json`:
```json
"default_sort": "new"  // or "hot", "top", "controversial", "rising"
```

### Change Subreddit Order
Edit `config.json`:
```json
"subreddit_sort": "alphabetical"  // or "subscribers", "activity"
```

### Enable/Disable Favorites
Edit `config.json`:
```json
"show_favorites": true  // or false
```

### Increase Limits
Edit `config.json`:
```json
"subreddit_posts_limit": 100,  // More posts when selecting a subreddit
"favorites_limit": 75           // More favorites displayed
```

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| `reddit_guide.md` | Main setup and usage guide | All users |
| `reddit_sorting_guide.md` | Complete sorting reference | Users wanting customization |
| `reddit_favorites_feature.md` | Favorites feature guide | Users with Reddit favorites |
| `reddit_favorites_visual_example.md` | Visual examples | Visual learners |
| `reddit_subreddit_ordering_comparison.md` | Before/after comparisons | Decision makers |
| `reddit_changelog_2025-10.md` | What's new | Existing users |
| `reddit_backend.md` | Technical backend details | Developers |
| `REDDIT_FAVORITES_IMPLEMENTATION_SUMMARY.md` | Implementation details | Developers |
| `SUBREDDIT_SORTING_SUMMARY.md` | Sorting implementation | Developers |

## Quick Links

- [Main README](../../readme.md)
- [Installation Guide](../installation.md)
- [User Guide](../user_guide.md)
- [Configuration Examples](reddit_sorting_guide.md#examples)
- [Troubleshooting](reddit_sorting_guide.md#troubleshooting)

---

**All documentation is up-to-date as of October 11, 2025**

