# Open Issues

## 1. Unhandled LLM Errors in UI

**Date:** 2025-08-09

**Problem:**
When the LLM backend encounters an error (e.g., sending images to a model that doesn't support them), the error is logged on the server, but it is not propagated to the user interface. The UI remains in a loading state (e.g., "Found x messages. Summarizing...") without displaying an error message or timing out.

**Server Log Evidence:**
```
2025-08-09 21:07:45,863 - ai.openai_compatible_llm - WARNING - Unexpected structure in OpenAI-compatible stream chunk: {"error":{"message":"Model does not support images. Please use a model that does."},"message":"Model does not support images. Please use a model that does."}
```

**Expected Behavior:**
The UI should display a clear error message to the user when the LLM fails to process the request.

**Task:**
Investigate the streaming response handling in `services/chat_service.py` and the corresponding frontend code to ensure that error chunks from the LLM stream are caught, parsed, and sent to the UI as a distinct error event.