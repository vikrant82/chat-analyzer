# Parallel Downloads Architecture & Connection Pool Management

## Overview
This document describes the parallel download architecture implemented across all chat clients (Webex, Telegram, Reddit) to prevent connection pool exhaustion and timeout errors when downloading large batches of images/media.

## Problem Statement
When downloading hundreds of images concurrently (e.g., 500 images from a Webex room with 3000 messages), unlimited parallel downloads cause:
- **httpx.PoolTimeout errors** - Connection pool exhaustion
- **Resource starvation** - No connections available for API calls
- **Poor performance** - Too many concurrent connections overwhelming the system

## Solution: Semaphore-Based Rate Limiting

### Architecture Pattern
All clients now use **asyncio.Semaphore** to limit concurrent downloads while maintaining good performance:

```python
# Create semaphore with configurable limit
semaphore = asyncio.Semaphore(max_concurrent_downloads)

async def download_with_limit(url):
    """Download with semaphore-based rate limiting."""
    async with semaphore:
        return await download_function(url)

# Download all items with controlled concurrency
results = await asyncio.gather(
    *[download_with_limit(url) for url in all_urls],
    return_exceptions=True
)
```

**Key Benefit**: Only N downloads run concurrently, preventing pool exhaustion while still being much faster than sequential downloads.

## Implementation by Client

### 1. Webex Client (`clients/webex_client.py`)

**Configuration**:
```json
{
  "webex": {
    "max_concurrent_image_downloads": 20,
    "max_concurrent_fetches": 5,
    "parallel_fetch_chunk_days": 7
  }
}
```

**Connection Pool Setup** (lines 48-53):
```python
limits = httpx.Limits(
    max_connections=100,        # Total connections allowed
    max_keepalive_connections=20  # Idle connections to maintain
)
timeout = httpx.Timeout(
    connect=10.0, read=60.0, write=10.0, pool=5.0
)
self.http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
```

**Image Download Control** (lines 387-415):
```python
# Limit to 20 concurrent image downloads
semaphore = asyncio.Semaphore(self.max_concurrent_image_downloads)

async def download_with_limit(file_url: str):
    async with semaphore:
        return await self._download_and_encode_file(file_url, settings)

download_results = await asyncio.gather(
    *[download_with_limit(url) for url in all_file_urls],
    return_exceptions=True
)
```

**Resource Usage** (3000 messages + 500 images):
- Message API calls: ~15 connections (5 ranges × 3 batches)
- Image downloads: 20 concurrent connections
- **Peak usage**: ~55 connections out of 100 pool limit
- **Safety margin**: 45 spare connections ✅

### 2. Telegram Client (`clients/telegram_client.py`)

**Configuration**:
```json
{
  "telegram": {
    "max_concurrent_media_downloads": 20,
    "max_concurrent_fetches": 5,
    "parallel_fetch_chunk_days": 7
  }
}
```

**Media Download Control** (lines 347-362):
```python
# Limit to 20 concurrent media downloads
semaphore = asyncio.Semaphore(self.max_concurrent_media_downloads)

async def download_with_limit(msg_info):
    async with semaphore:
        return await download_message_media(msg_info)

media_results = await asyncio.gather(
    *[download_with_limit(msg_info) for msg_info in messages],
    return_exceptions=True
)
```

**Note**: Telegram uses Telethon's own connection management for API calls, so only media downloads need explicit rate limiting.

### 3. Reddit Client (`clients/reddit_client.py`)

**Configuration**:
```json
{
  "reddit": {
    "max_concurrent_image_downloads": 20
  }
}
```

**Connection Pool Setup** (ImageFetcher class, lines 56-65):
```python
limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20
)
timeout = httpx.Timeout(
    connect=10.0, read=60.0, write=10.0, pool=5.0
)
self.http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
```

**Image Download Control** (lines 108-133):
```python
semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

async def download_single_image(url: str):
    async with semaphore:
        try:
            response = await self.http_client.get(url)
            # ... process image
        except httpx.PoolTimeout:
            # Handle timeout gracefully
            return None

results = await asyncio.gather(
    *[download_single_image(url) for url in urls],
    return_exceptions=True
)
```

## Connection Pool vs Concurrent Downloads

### Important Distinction

**Connection Pool Size (100)** - HTTP infrastructure level:
- Total connections the httpx client can maintain across **ALL operations**
- Includes: API calls, HEAD requests, image downloads, token refresh, etc.
- Not just for image downloads - shared across entire client

**Concurrent Downloads (20)** - Application-level rate limiting:
- Specifically controls parallel image/media download operations
- Prevents overwhelming the connection pool with just downloads
- Leaves headroom for other operations

### Why Both Are Needed

**Scenario**: Downloading 500 images from a Webex room
- **Without semaphore**: All 500 try to download → Pool exhausted → PoolTimeout ❌
- **With semaphore (20)**: Only 20 downloads at once → 80 connections free for API calls → Smooth operation ✅

**Resource Allocation**:
```
Total Pool: 100 connections
├── Image downloads: 20 (rate-limited by semaphore)
├── Message API calls: ~15 (parallel date range fetches)
├── HEAD requests: ~5 (file size checks)
└── Available headroom: 60 connections for other operations
```

## Image Processing Configuration

### Two-Layer System

#### Layer 1: Global Config (Performance Tuning)
**File**: `config.json`
```json
{
  "webex": {
    "max_concurrent_image_downloads": 20  // Server-side performance limit
  }
}
```
**Purpose**: Admin-controlled rate limiting to prevent connection pool exhaustion

#### Layer 2: Per-Request Settings (User Control)
**Source**: Frontend UI → API request
```javascript
{
  "imageProcessing": {
    "enabled": true,           // User's toggle checkbox
    "max_size_bytes": 10485760 // User's size limit
  }
}
```
**Purpose**: User decides whether to download images for each request

### Settings Merge Logic

```python
# 1. Start with global config defaults
final_settings = self.image_processing_config.copy()
# Result: {"max_concurrent_downloads": 20}

# 2. Override with user's per-request settings
if image_processing_settings:  # From API
    final_settings.update(image_processing_settings)
# Result: {
#   "enabled": true,              ← From UX
#   "max_size_bytes": 10485760,   ← From UX
#   "max_concurrent_downloads": 20 ← From config.json
# }

# 3. Use merged settings
if final_settings.get('enabled'):
    download_images_with_rate_limit(final_settings)
```

### Configuration Responsibility Matrix

| Setting | Source | Purpose | User Control? | Admin Control? |
|---------|--------|---------|---------------|----------------|
| `enabled` | **UX Toggle** | Enable/disable downloads | ✅ YES | ❌ NO |
| `max_size_bytes` | **UX Input** | Filter by file size | ✅ YES | ❌ NO |
| `max_concurrent_downloads` | **config.json** | Rate limit (pool safety) | ❌ NO | ✅ YES |

**Key Point**: The `enabled` flag should NEVER be in config.json because the UX always provides it, making any config default meaningless.

## Error Handling

### Timeout Exceptions
All clients now handle connection pool timeouts gracefully:

```python
try:
    response = await self.http_client.get(url)
except httpx.PoolTimeout:
    logger.error(f"Connection pool timeout for {url}. "
                 "Too many concurrent downloads - consider reducing "
                 "max_concurrent_image_downloads in config.json")
    return None
except httpx.TimeoutException as e:
    logger.error(f"Request timeout for {url}: {e}")
    return None
```

**Benefits**:
- Informative error messages
- Graceful degradation (continue with other downloads)
- Clear guidance for configuration tuning

## Performance Analysis

### Benchmark: 3000 Messages + 500 Images

| Client | Message Fetching | Image Downloads | Peak Connections | Pool Limit | Safety |
|--------|------------------|-----------------|------------------|------------|--------|
| **Webex** | Sequential batches (1000/batch) | 20 concurrent | ~55 | 100 | ✅ Safe |
| **Telegram** | Sequential pagination | 20 concurrent | ~25 | N/A* | ✅ Safe |
| **Reddit** | Sequential API calls | 20 concurrent | ~25 | 100 | ✅ Safe |

*Telegram uses Telethon's internal connection management

### Performance vs Safety Trade-off

**Too Low** (e.g., max_concurrent_downloads = 5):
- ✅ Very safe, minimal pool usage
- ❌ Slow for large batches (500 images ÷ 5 = 100 sequential batches)

**Optimal** (default = 20):
- ✅ Good performance (500 images ÷ 20 = 25 sequential batches)
- ✅ Safe pool usage (~20-30% of pool)
- ✅ Enough headroom for other operations

**Too High** (e.g., max_concurrent_downloads = 80):
- ❌ Risk of pool exhaustion
- ❌ Little headroom for API calls
- ⚠️ Diminishing returns (network bandwidth becomes bottleneck)

## Configuration Recommendations

### Default Settings (All Clients)
```json
{
  "max_concurrent_image_downloads": 20,  // Good balance
  "max_concurrent_fetches": 5,           // Date range parallelism
  "parallel_fetch_chunk_days": 7         // Chunk size for parallel fetching
}
```

### Tuning Guidelines

**For Slower Networks**:
```json
{
  "max_concurrent_image_downloads": 10  // Reduce concurrent load
}
```

**For High-Performance Servers**:
```json
{
  "max_concurrent_image_downloads": 30,  // Increase throughput
  "max_connections": 150                  // Larger pool
}
```

**For Large Rooms (10,000+ messages)**:
```json
{
  "parallel_fetch_chunk_days": 14,       // Larger chunks
  "max_concurrent_fetches": 10           // More parallel date ranges
}
```

## Testing Scenarios

### Scenario 1: Large Webex Room
- **Input**: 5000 messages, 800 images, date range: 30 days
- **Expected Behavior**:
  - Parallel date range fetching (5 ranges × 6 days each)
  - 20 images download concurrently
  - No PoolTimeout errors
  - Completion time: ~2-3 minutes
  - Peak connections: ~60-70

### Scenario 2: Heavy Telegram Channel
- **Input**: 10,000 messages, 1200 media items
- **Expected Behavior**:
  - Sequential message batches (1000/batch × 10)
  - 20 media downloads concurrently
  - No connection issues
  - Completion time: ~5-7 minutes
  - Memory usage: ~500MB-1GB

### Scenario 3: Reddit Multi-Subreddit
- **Input**: 50 posts × 20 comments each, 300 images
- **Expected Behavior**:
  - Sequential post fetching
  - 20 images download concurrently
  - Graceful handling of missing images
  - Completion time: ~1-2 minutes

## Troubleshooting

### Symptom: PoolTimeout Errors
**Cause**: Too many concurrent downloads
**Solution**: Reduce `max_concurrent_image_downloads` in config.json
```json
{"max_concurrent_image_downloads": 10}  // Lower from 20 to 10
```

### Symptom: Slow Download Performance
**Cause**: Too few concurrent downloads
**Solution**: Increase rate limit (if no timeouts occurring)
```json
{"max_concurrent_image_downloads": 30}  // Increase from 20 to 30
```

### Symptom: Memory Issues
**Cause**: Large batches held in memory
**Solution**: 
1. Enable caching to write to disk immediately
2. Use smaller date ranges
3. Disable image processing for very large exports

### Symptom: API Rate Limits
**Cause**: Too many parallel API calls
**Solution**: Reduce message fetch parallelism
```json
{
  "max_concurrent_fetches": 3,  // Lower from 5 to 3
  "parallel_fetch_chunk_days": 5  // Smaller chunks
}
```

## Future Improvements

### Potential Enhancements
1. **Dynamic Rate Limiting**: Auto-adjust based on error rates
2. **Progressive Image Loading**: Stream images as they download
3. **Disk Caching for Images**: Store encoded images on disk during download
4. **Bandwidth Throttling**: Limit total bandwidth usage
5. **Priority Queue**: Download critical images first
6. **Retry Logic**: Exponential backoff for failed downloads

### Monitoring Metrics to Add
- Connection pool utilization percentage
- Average download time per image
- Success/failure rate for downloads
- Memory usage during large batches
- API rate limit proximity

## Related Files

### Core Implementation
- `clients/webex_client.py` - Webex image downloads (lines 54-111, 387-415)
- `clients/telegram_client.py` - Telegram media downloads (lines 330-362)
- `clients/reddit_client.py` - Reddit image downloads (ImageFetcher class)

### Configuration
- `config.json` - Active user configuration
- `example-config.json` - Template with documented defaults

### Frontend
- `static/js/chat.js` - Image processing toggle logic
- `static/js/main.js` - User preference persistence
- `services/chat_service.py` - Request handling and settings merge

## Summary

The parallel download architecture successfully prevents connection pool exhaustion while maintaining excellent performance through:
1. **Semaphore-based rate limiting** - Control concurrent downloads
2. **Connection pool configuration** - Explicit limits and timeouts
3. **Graceful error handling** - Informative messages and degradation
4. **Configurable performance** - Admin tuning without code changes
5. **User control** - Toggle image downloads per request

This architecture ensures reliable operation even when downloading hundreds of images from large chat rooms or channels.
