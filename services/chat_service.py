import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel
import inspect

from clients.base_client import Message as StandardMessage
from clients.factory import get_client
from services import auth_service
from llm.llm_client import llm_clients

logger = logging.getLogger(__name__)
message_cache: Dict[str, str] = {}
conversations: Dict[str, List[Dict[str, str]]] = {}

class ChatMessage(BaseModel):
    message: Optional[str] = None
    chatId: str
    modelName: str
    provider: str
    startDate: str
    endDate: str
    enableCaching: bool
    conversation: List[Dict[str, Any]]
    originalMessages: Optional[List[Dict[str, Any]]] = None
    imageProcessing: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None

async def _normalize_stream(result):
    """
    Normalize either an async generator OR a coroutine resolving to an async-iterable
    into a unified async generator interface.
    """
    if inspect.isasyncgen(result):
        async for x in result:
            yield x
        return

    obj = await result
    if inspect.isasyncgen(obj) or hasattr(obj, "__aiter__"):
        async for x in obj:
            yield x
        return

    if isinstance(obj, str):
        yield obj
        return
    if hasattr(obj, "__iter__"):
        for x in obj:
            yield x
        return

    yield str(obj)

async def process_chat_request(req: ChatMessage, user_id: str, backend: str):
    llm_client = llm_clients.get(req.provider)

    if not llm_client:
        raise HTTPException(status_code=400, detail=f"Invalid provider '{req.provider}' specified.")

    if req.modelName not in llm_client.get_available_models():
        raise HTTPException(status_code=400, detail=f"Model '{req.modelName}' is not available for provider '{req.provider}'.")

    token = auth_service.get_token_for_user(user_id)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")

    cache_key = f"{token}_{req.chatId}_{req.startDate}_{req.endDate}"
    
    try:
        end_date_dt = datetime.strptime(req.endDate, '%Y-%m-%d').date()
        today_dt = datetime.now(timezone.utc).date()
        is_historical_date = end_date_dt < today_dt
    except ValueError:
        logger.warning(f"Could not parse endDate '{req.endDate}'. Disabling cache for this request.")
        is_historical_date = False

    use_in_memory_cache = req.enableCaching and is_historical_date

    if use_in_memory_cache and cache_key in message_cache:
        logger.info(f"Cache HIT for conversation key: {cache_key}. Using cached messages.")
        original_messages_structured = json.loads(message_cache[cache_key])
        message_count = len(original_messages_structured)
    else:
        if not is_historical_date:
            logger.info(f"Date range includes today. Bypassing in-memory cache for key: {cache_key}")
        elif not req.enableCaching:
            logger.info(f"User disabled caching for this request. Bypassing in-memory cache for key: {cache_key}")
        else:
            logger.info(f"Cache MISS for conversation key: {cache_key}. Fetching messages.")
        
        chat_client = get_client(backend)
        
        get_messages_kwargs = {
            "user_identifier": user_id,
            "chat_id": req.chatId,
            "start_date_str": req.startDate,
            "end_date_str": req.endDate,
            "enable_caching": req.enableCaching,
            "timezone_str": req.timezone,
            "image_processing_settings": req.imageProcessing,
        }

        messages_list: List[StandardMessage] = await chat_client.get_messages(**get_messages_kwargs)
        if not messages_list:
            async def empty_message_stream():
                yield f"data: {json.dumps({'type': 'content', 'chunk': 'No messages found in the selected date range. Please select a different range.'})}\n\n"
            return empty_message_stream()
        
        original_messages_structured = _format_messages_for_llm(messages_list)
        message_count = len(messages_list)
        
        if use_in_memory_cache:
            logger.info(f"Storing result in in-memory cache for key: {cache_key}")
            message_cache[cache_key] = json.dumps(original_messages_structured)

    current_conversation = list(req.conversation)
    
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Found {message_count} messages. Summarizing...'})}\n\n"
        
        try:
            stream = _normalize_stream(
                llm_client.call_conversational(
                    req.modelName,
                    current_conversation,
                    original_messages_structured
                )
            )
            async for chunk in stream:
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Unhandled error in conversational streaming generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'An unexpected error occurred: {e}'})}\n\n"

    return stream_generator()

def _format_messages_for_llm(messages: List[StandardMessage]) -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = []
    in_thread = False
    transcript_lines: List[str] = []
    image_parts_in_order: List[Dict[str, Any]] = []
    image_seq = 0

    for msg in messages:
        is_reply = msg.thread_id is not None

        if is_reply and not in_thread:
            transcript_lines.append("\n--- Thread Started ---")
            in_thread = True
        elif not is_reply and in_thread:
            transcript_lines.append("--- Thread Ended ---\n")
            in_thread = False

        prefix = "    " if is_reply else ""
        header = f"{prefix}[{msg.author.name} at {msg.timestamp}]:"
        if msg.text:
            transcript_lines.append(f"{header} {msg.text}")
        else:
            transcript_lines.append(f"{header}")

        if msg.attachments:
            for attachment in msg.attachments:
                image_seq += 1
                transcript_lines.append(
                    f"{prefix}(Image #{image_seq}: {attachment.mime_type}; author={msg.author.name}; at={msg.timestamp})"
                )
                caption_text = f"[Image #{image_seq}] author={msg.author.name}; at={msg.timestamp}; thread={'yes' if msg.thread_id else 'no'}"
                image_parts_in_order.append({
                    "type": "text",
                    "text": caption_text
                })
                image_parts_in_order.append({
                    "type": "image",
                    "id": f"img-{image_seq}",
                    "meta": {
                        "author": msg.author.name,
                        "timestamp": str(msg.timestamp),
                        "thread": bool(msg.thread_id),
                        "caption": f"Image #{image_seq} from {msg.author.name} at {msg.timestamp}"
                    },
                    "source": {
                        "type": "base64",
                        "media_type": attachment.mime_type,
                        "data": attachment.data,
                    },
                })

    if in_thread:
        transcript_lines.append("--- Thread Ended ---")

    if image_seq > 0:
        transcript_lines.append("")
        transcript_lines.append("Image Index:")
        for p in image_parts_in_order:
            if p.get("type") == "image":
                idx = (p.get("id") or "").replace("img-", "")
                meta = p.get("meta") or {}
                author = meta.get("author", "unknown")
                ts = meta.get("timestamp", "unknown")
                transcript_lines.append(f"  - Image #{idx}: author={author}; at={ts}")

    full_text = "Context: Chat History (Local Day)\n" + "\n".join(transcript_lines)
    parts.append({"type": "text", "text": full_text})
    parts.extend(image_parts_in_order)

    return [{"role": "user", "content": parts}]

def clear_chat_cache(token: str):
    keys_to_delete = [key for key in message_cache if key.startswith(token)]
    for key in keys_to_delete:
        del message_cache[key]
        logger.info(f"Removed message cache for key: {key}")

def clear_conversation_history(token: str):
    """Clears the conversation history for a given session token."""
    if token in conversations:
        del conversations[token]
        logger.info(f"Removed conversation history for token: {token}")