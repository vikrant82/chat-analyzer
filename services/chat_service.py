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
from llm.llm_client import LLMManager
from ai.base_llm import LLMError

logger = logging.getLogger(__name__)
message_cache: Dict[str, str] = {}
conversations: Dict[str, List[Dict[str, str]]] = {}

class ChatMessage(BaseModel):
    message: Optional[str] = None
    chatId: str
    modelName: str
    provider: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
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

async def process_chat_request(req: ChatMessage, user_id: str, backend: str, llm_manager: LLMManager):
    token = auth_service.get_token_for_user(user_id, backend)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")

    # Simplified cache key for Reddit, as it doesn't use dates
    if backend == 'reddit':
        cache_key = f"{token}_{req.chatId}"
    else:
        cache_key = f"{token}_{req.chatId}_{req.startDate}_{req.endDate}"

    is_historical_date = False
    if req.endDate and backend != 'reddit':
        try:
            end_date_dt = datetime.strptime(req.endDate, '%Y-%m-%d').date()
            today_dt = datetime.now(timezone.utc).date()
            is_historical_date = end_date_dt < today_dt
        except (ValueError, TypeError):
            logger.warning(f"Could not parse endDate '{req.endDate}'. Disabling cache for this request.")
            is_historical_date = False

    use_in_memory_cache = req.enableCaching and (is_historical_date or backend == 'reddit')

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
        
        is_multimodal = llm_manager.is_multimodal(req.provider, req.modelName)
        original_messages_structured = _format_messages_for_llm(messages_list, is_multimodal)
        message_count = len(messages_list)
        
        if use_in_memory_cache:
            logger.info(f"Storing result in in-memory cache for key: {cache_key}")
            message_cache[cache_key] = json.dumps(original_messages_structured)

    current_conversation = list(req.conversation)
    
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Found {message_count} messages. Summarizing...'})}\n\n"
        
        try:
            stream = await llm_manager.call_conversational(
                req.provider,
                req.modelName,
                current_conversation,
                original_messages_structured
            )
            async for chunk in _normalize_stream(stream):
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
        except LLMError as e:
            logger.error(f"LLM-specific error during streaming: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            logger.error(f"Unhandled error in conversational streaming generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'An unexpected error occurred: {e}'})}\n\n"

    return stream_generator()

def _format_messages_for_llm(messages: List[StandardMessage], is_multimodal: bool) -> List[Dict[str, Any]]:
    """
    Formats a list of messages for the LLM, handling both flat and threaded conversations.
    If parent_id is present, it builds and formats a hierarchical tree.
    Otherwise, it formats a flat list with simple thread indicators.
    """
    # Check if any message has a parent_id to determine the formatting strategy
    is_threaded_conversation = any(msg.parent_id is not None for msg in messages)

    if is_threaded_conversation:
        return _format_threaded_conversation(messages, is_multimodal)
    else:
        return _format_flat_conversation(messages, is_multimodal)


def _format_flat_conversation(messages: List[StandardMessage], is_multimodal: bool) -> List[Dict[str, Any]]:
    """Handles formatting for services without deep threading (e.g., Webex, old Telegram)."""
    parts: List[Dict[str, Any]] = []
    transcript_lines: List[str] = []
    image_parts_in_order: List[Dict[str, Any]] = []
    image_seq = 0
    current_thread_id = None

    for i, msg in enumerate(messages):
        is_reply = msg.thread_id is not None
        
        # Determine the thread_id of the previous message for state change detection
        prev_thread_id = messages[i-1].thread_id if i > 0 else None

        # --- Thread State Logic ---
        # 1. Entering a new thread
        if is_reply and msg.thread_id != prev_thread_id:
            # If we were in a different thread, close it first.
            if prev_thread_id is not None:
                 transcript_lines.append("--- Thread Ended ---\n")
            transcript_lines.append("\n--- Thread Started ---")
        
        # 2. Exiting a thread
        elif not is_reply and prev_thread_id is not None:
            transcript_lines.append("--- Thread Ended ---\n")
        
        # --- Message Formatting ---
        prefix = "    " if is_reply else ""
        header = f"{prefix}[{msg.author.name} at {msg.timestamp}]:"
        
        if msg.text:
            transcript_lines.append(f"{header} {msg.text}")
        else:
            transcript_lines.append(header)

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

    # After the loop, if the very last message was in a thread, close it.
    if messages and messages[-1].thread_id is not None:
        transcript_lines.append("--- Thread Ended ---\n")

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
    if is_multimodal:
        parts.extend(image_parts_in_order)

    return [{"role": "user", "content": parts}]

def clear_chat_cache(token: str):
    keys_to_delete = [key for key in message_cache if key.startswith(token)]
    for key in keys_to_delete:
        del message_cache[key]
        logger.info(f"Removed message cache for key: {key}")

def _format_threaded_conversation(messages: List[StandardMessage], is_multimodal: bool) -> List[Dict[str, Any]]:
    """Handles formatting for services with n-level threading (e.g., Reddit)."""
    parts: List[Dict[str, Any]] = []
    transcript_lines: List[str] = []
    image_parts_in_order: List[Dict[str, Any]] = []
    image_seq = 0

    message_map = {msg.id: msg for msg in messages}
    children_map = {msg.id: [] for msg in messages}
    root_messages = []

    for msg in messages:
        if msg.parent_id and msg.parent_id in message_map:
            children_map[msg.parent_id].append(msg)
        else:
            root_messages.append(msg)
            
    root_messages.sort(key=lambda m: m.timestamp)

    def format_message_text(msg: StandardMessage, depth: int, image_parts: list) -> str:
        nonlocal image_seq
        
        # Indentation for tree structure
        indent = "    " * depth
        # Prefix for replies to improve readability
        line_prefix = "| " if depth > 0 else ""
        
        header = f"{indent}[{msg.author.name} at {msg.timestamp}]:"
        
        text_content = msg.text or ""
        # Prepend each line of the message text with the prefix
        
        if text_content:
            body = "\n".join([f"{indent}{line_prefix}{line}" for line in text_content.splitlines()])
            full_text = f"{header}\n{body}"
        else:
            full_text = header

        # Handle attachments
        if msg.attachments:
            attachment_lines = []
            for attachment in msg.attachments:
                image_seq += 1
                attachment_lines.append(f"{indent}{line_prefix}(Image #{image_seq}: {attachment.mime_type})")
                caption_text = f"[Image #{image_seq}] author={msg.author.name}; at={msg.timestamp}; thread_depth={depth}"
                image_parts.append({
                    "type": "text",
                    "text": caption_text
                })
                image_parts.append({
                    "type": "image",
                    "id": f"img-{image_seq}",
                    "meta": {
                        "author": msg.author.name,
                        "timestamp": str(msg.timestamp),
                        "thread_depth": depth,
                        "caption": f"Image #{image_seq} from {msg.author.name} at {msg.timestamp}"
                    },
                    "source": {
                        "type": "base64",
                        "media_type": attachment.mime_type,
                        "data": attachment.data,
                    },
                })
            full_text += "\n" + "\n".join(attachment_lines)
            
        return full_text

    def traverse_and_format(message_id: str, depth: int, output_list: List[str], image_parts: list):
        msg = message_map.get(message_id)
        if not msg: return
        
        output_list.append(format_message_text(msg, depth, image_parts))
        
        sorted_children = sorted(children_map.get(message_id, []), key=lambda m: m.timestamp)
        for child_msg in sorted_children:
            traverse_and_format(child_msg.id, depth + 1, output_list, image_parts)

    # Process root messages
    for root_msg in root_messages:
        thread_lines = []
        if root_msg.parent_id is None:
             # This is a main post, start a new thread
            transcript_lines.append("\n--- Thread Started ---")
            traverse_and_format(root_msg.id, 0, thread_lines, image_parts_in_order)
            transcript_lines.extend(thread_lines)
            transcript_lines.append("--- Thread Ended ---")
        else:
            # This is an orphan comment, treat it as its own thread
            transcript_lines.append("\n--- Thread Started (Orphaned) ---")
            traverse_and_format(root_msg.id, 0, thread_lines, image_parts_in_order)
            transcript_lines.extend(thread_lines)
            transcript_lines.append("--- Thread Ended (Orphaned) ---")


    # This part remains the same: construct the final payload
    if image_seq > 0:
        transcript_lines.append("")
        transcript_lines.append("Image Index:")
        # ... (image index generation) ...

    full_text = "Context: Chat History (Local Day)\n" + "\n".join(transcript_lines)
    parts.append({"type": "text", "text": full_text})
    if is_multimodal:
        parts.extend(image_parts_in_order)

    return [{"role": "user", "content": parts}]

def clear_conversation_history(token: str):
    """Clears the conversation history for a given session token."""
    if token in conversations:
        del conversations[token]
        logger.info(f"Removed conversation history for token: {token}")
