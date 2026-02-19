# API Endpoints Reference

## Authentication & Session Management

### `POST /api/login`
Initiates login process for selected backend (Telegram, Webex, Reddit).

**Request Body**:
```json
{
  "backend": "telegram" | "webex" | "reddit",
  "phone": "string"  // Telegram only
}
```

**Response**: Varies by backend
- Telegram: `{"status": "code_required"}`
- Webex/Reddit: `{"status": "redirect_required", "url": "..."}`

### `POST /api/verify`
Completes authentication verification.

**Request Body**:
```json
{
  "backend": "telegram" | "webex" | "reddit",
  "phone": "string",  // Telegram
  "code": "string",   // Telegram/OAuth
  "password": "string"  // Telegram 2FA (optional)
}
```

### `GET /api/session-status`
Checks active session status across all backends.

**Response**:
```json
{
  "telegram": {
    "logged_in": true,
    "user_identifier": "phone_number"
  },
  "webex": { ... },
  "reddit": { ... }
}
```

### `POST /api/logout`
Logs out from specified backend.

**Request Body**:
```json
{
  "backend": "telegram" | "webex" | "reddit"
}
```

## Chat & Data Retrieval

### `GET /api/chats`
Lists available chats/rooms for logged-in user.

**Query Parameters**:
- `backend`: "telegram" | "webex" | "reddit"

**Response**:
```json
[
  {
    "id": "string",
    "title": "string",
    "type": "private" | "group" | "channel" | "subreddit" | "post"
  }
]
```

### `GET /api/reddit/posts`
Fetches posts for a specific subreddit.

**Query Parameters**:
- `subreddit_name`: string
- `sort_method`: "hot" | "new" | "top" | "controversial" | "rising" (optional)
- `time_filter`: "hour" | "day" | "week" | "month" | "year" | "all" (optional)

### `POST /api/chat`
Main endpoint for chat analysis. Streams AI response.

**Request Body**:
```json
{
  "backend": "telegram" | "webex" | "reddit",
  "chat_id": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "user_query": "string",
  "model": "string",
  "provider": "google_ai" | "openai_compatible",
  "image_processing": {
    "enabled": true,
    "max_size_bytes": 5242880,
    "allowed_mime_types": ["image/jpeg", "image/png"]
  },
  "timezone": "America/Los_Angeles",
  "conversation_id": "string"  // For follow-up questions
}
```

**Response**: Server-Sent Events (SSE) stream

### `POST /api/clear-session`
Clears server-side caches for user.

## Downloads

### `POST /api/download`
Generates downloadable transcript.

**Request Body**:
```json
{
  "format": "txt" | "pdf" | "html" | "zip",
  "backend": "telegram" | "webex" | "reddit",
  "chat_id": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "ai_response": "string",
  "model": "string",
  "provider": "string",
  "image_processing": { ... },
  "timezone": "string"
}
```

**Response**: File download

## Bot Management

### `POST /api/{backend}/bots`
Registers a new bot.

**Path Parameters**:
- `backend`: "telegram" | "webex"

**Request Body**:
```json
{
  "bot_name": "string",
  "bot_token": "string",
  "webhook_url": "string"
}
```

### `GET /api/{backend}/bots`
Lists registered bots for user.

**Query Parameters**:
- `user_id`: string

### `DELETE /api/{backend}/bots/{bot_name}`
Deletes a registered bot.

**Path Parameters**:
- `backend`: "telegram" | "webex"
- `bot_name`: string

**Query Parameters**:
- `user_id`: string

## Webhooks (Bot Endpoints)

### `POST /api/bots/webex/webhook`
Receives events from Webex bot.

**Request Body**: Webex webhook payload

### `POST /api/bots/telegram/webhook/{token}`
Receives events from Telegram bot.

**Path Parameters**:
- `token`: Bot token

**Request Body**: Telegram update object

## OAuth Callbacks

### `GET /api/webex/callback`
OAuth callback for Webex authentication.

**Query Parameters**:
- `code`: Authorization code
- `state`: Security state

### `GET /api/auth/callback/reddit`
OAuth callback for Reddit authentication.

**Query Parameters**:
- `code`: Authorization code
- `state`: Security state

## Frontend Routes

### `GET /`
Serves the main frontend application (index.html).

## Error Responses

All endpoints may return:
```json
{
  "detail": "Error message"
}
```

HTTP Status Codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error