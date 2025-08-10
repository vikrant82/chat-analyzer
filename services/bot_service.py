import base64
import inspect
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from clients.base_client import Message as StandardMessage
from clients.bot_factory import get_bot_client
from clients.factory import get_client
from clients.telegram_bot_client import TelegramBotClient
from llm.llm_client import LLMManager
from services import auth_service
from services.chat_service import _format_messages_for_llm

# --- Logging ---
logger = logging.getLogger(__name__)

# --- State ---
conversations: Dict[str, List[Dict[str, str]]] = {}
chat_modes: Dict[int, str] = {}

# This is a temporary solution. In a real app, this should be handled
# by a proper dependency injection system or by passing config explicitly.
config = {}
llm_manager: Optional[LLMManager] = None

# --- Streaming Normalizer ---
async def _normalize_stream(result):
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

# --- Webex Specific Helpers ---

def _find_bot_in_config(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mentioned_ids_encoded = webhook_data.get('data', {}).get('mentionedPeople', [])
    if not mentioned_ids_encoded:
        logger.info("Webhook received, but no one was mentioned.")
        return None

    webex_bots = config.get('bots', {}).get('webex', [])
    decoded_mentioned_uuids = set()
    for encoded_id in mentioned_ids_encoded:
        try:
            padded_id = encoded_id + '=' * (-len(encoded_id) % 4)
            decoded_uri = base64.urlsafe_b64decode(padded_id).decode('utf-8')
            decoded_mentioned_uuids.add(decoded_uri.split('/')[-1])
        except Exception as e:
            logger.warning(f"Could not decode a mentioned ID: {encoded_id}, Error: {e}")
            continue
    
    for bot in webex_bots:
        try:
            padded_stored_id = bot['bot_id'] + '=' * (-len(bot['bot_id']) % 4)
            decoded_stored_id = base64.urlsafe_b64decode(padded_stored_id).decode('utf-8')
            stored_uuid = decoded_stored_id.split('/')[-1]
            if stored_uuid in decoded_mentioned_uuids:
                logger.info(f"Webhook matched registered bot: {bot['name']}")
                return bot
        except Exception as e:
            logger.warning(f"Could not process a stored bot_id: {bot['bot_id']}, Error: {e}")
            continue
    
    logger.info("Webhook received, but no matching registered bot was found.")
    return None

async def _get_bot_and_message_details(webhook_data: Dict[str, Any]) -> Optional[Tuple[Any, str, Optional[str]]]:
    bot_config = _find_bot_in_config(webhook_data)
    if not bot_config:
        return None

    bot_client = get_bot_client("webex", bot_config['token'])
    message_id = webhook_data['data']['id']
    message_details = await bot_client.get_messages(id=message_id)
    if not message_details:
        return None

    message_text = message_details[0].get('text', '').strip()
    room_id = message_details[0].get('roomId')
    return bot_client, message_text, room_id

async def _process_webex_bot_command(bot_client: Any, webex_client: Any, active_user_id: str, room_id: str, message_text: str):
    days_match = re.search(r"last (\d+) days", message_text, re.IGNORECASE)
    
    end_date = datetime.now(timezone.utc)
    if days_match:
        num_days = int(days_match.group(1))
        start_date = end_date - timedelta(days=num_days)
        query = re.sub(r"\s*last \d+ days\s*", "", message_text, flags=re.IGNORECASE).strip()
    else:
        start_date = end_date - timedelta(days=1)
        query = message_text

    if not query:
        query = "Provide a concise summary of the conversation."

    logger.info(f"Bot using user '{active_user_id}' to fetch history for room {room_id}")
    
    try:
        messages_list = await webex_client.get_messages(
            active_user_id, room_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), enable_caching=False
        )
        
        if not messages_list:
            bot_client.post_message(room_id=room_id, text="No messages found in the specified date range.")
            return

        formatted_messages_structured = _format_messages_for_llm(messages_list)

        if not llm_manager:
            raise Exception("LLMManager not initialized.")
        
        # For bot commands, we can simplify by using the first available provider and its default model.
        llm_provider = next(iter(llm_manager.clients))
        llm_client = llm_manager.get_client(llm_provider)
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        conversation_history = [{"role": "user", "content": query}]
        stream = _normalize_stream(
            await llm_manager.call_conversational(
                llm_provider, model_name, conversation_history, formatted_messages_structured
            )
        )

        ai_response = ""
        async for chunk in stream:
            ai_response += chunk
        
        bot_client.post_message(room_id=room_id, text=ai_response)

    except Exception as e:
        logger.error(f"Bot failed to process message: {e}", exc_info=True)
        error_message = "I encountered an error trying to process your request. Please check the server logs."
        bot_client.post_message(room_id=room_id, text=error_message)

# --- Telegram Specific Helpers ---

async def _handle_ai_mode(bot_client: Any, user_chat_id: int, message_text: str):
    try:
        conversation_key = f"telegram_bot_{user_chat_id}"
        history = conversations.get(conversation_key, [])
        history.append({"role": "user", "content": message_text})
        
        if len(history) > 20:
            history = history[-20:]

        if not llm_manager:
            raise Exception("LLMManager not initialized.")

        llm_provider = next(iter(llm_manager.clients))
        llm_client = llm_manager.get_client(llm_provider)
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        stream = _normalize_stream(
            await llm_manager.call_conversational(llm_provider, model_name, history, None)
        )

        ai_response = ""
        async for chunk in stream:
            ai_response += chunk
        
        history.append({"role": "assistant", "content": ai_response})
        conversations[conversation_key] = history
        
        await bot_client.send_message(user_chat_id, ai_response)

    except Exception as e:
        logger.error(f"Error in AI mode: {e}", exc_info=True)
        error_message = "I encountered an error in AI mode. Please try again."
        await bot_client.send_message(user_chat_id, error_message)

async def _handle_summarizer_mode(bot_client: Any, telegram_client: Any, active_user_id: str, user_chat_id: int, bot_id: int, message_text: str):
    days_match = re.search(r"last (\d+) days", message_text, re.IGNORECASE)
    
    end_date = datetime.now(timezone.utc)
    if days_match:
        num_days = int(days_match.group(1))
        start_date = end_date - timedelta(days=num_days)
        query = re.sub(r"\s*last \d+ days\s*", "", message_text, flags=re.IGNORECASE).strip()
    else:
        start_date = end_date - timedelta(days=5)
        query = message_text

    if not query:
        query = "Provide a concise summary of the conversation."

    logger.info(f"Bot {bot_id} using user '{active_user_id}' to fetch history for chat with user {user_chat_id}")
    
    try:
        messages_list = await telegram_client.get_messages(
            active_user_id, str(bot_id), start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), enable_caching=False
        )
        
        if not messages_list:
            await bot_client.send_message(user_chat_id, "No messages found in the specified date range.")
            return

        formatted_messages_structured = _format_messages_for_llm(messages_list)

        if not llm_manager:
            raise Exception("LLMManager not initialized.")
            
        llm_provider = next(iter(llm_manager.clients))
        llm_client = llm_manager.get_client(llm_provider)
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        conversation_history = [{"role": "user", "content": query}]
        stream = _normalize_stream(
            await llm_manager.call_conversational(
                llm_provider, model_name, conversation_history, formatted_messages_structured
            )
        )

        ai_response = ""
        async for chunk in stream:
            ai_response += chunk
        
        await bot_client.send_message(user_chat_id, ai_response)

    except Exception as e:
        logger.error(f"Bot failed to process message: {e}", exc_info=True)
        error_message = "I encountered an error trying to process your request. Please check the server logs."
        await bot_client.send_message(user_chat_id, error_message)

async def _process_telegram_bot_command(bot_client: Any, telegram_client: Any, active_user_id: str, user_chat_id: int, bot_id: int, message_text: str):
    if message_text.strip() == '/aimode':
        current_mode = chat_modes.get(user_chat_id, 'summarizer')
        if current_mode == 'summarizer':
            chat_modes[user_chat_id] = 'aimode'
            await bot_client.send_message(user_chat_id, "AI mode enabled. I will now respond directly. Send /aimode again to switch back.")
        else:
            chat_modes[user_chat_id] = 'summarizer'
            conversation_key = f"telegram_bot_{user_chat_id}"
            if conversation_key in conversations:
                del conversations[conversation_key]
                logger.info(f"Cleared conversation history for chat {user_chat_id} upon switching to summarizer mode.")
            await bot_client.send_message(user_chat_id, "Summarizer mode enabled.")
        return

    current_mode = chat_modes.get(user_chat_id, 'summarizer')
    if current_mode == 'aimode':
        await _handle_ai_mode(bot_client, user_chat_id, message_text)
    else:
        await _handle_summarizer_mode(bot_client, telegram_client, active_user_id, user_chat_id, bot_id, message_text)

# --- Main Service Functions ---

async def _find_active_user_session(backend: str) -> Optional[str]:
    # This is a placeholder and needs a proper implementation.
    # It should iterate through active sessions and find a valid one for the given backend.
    # For now, we'll return a hardcoded value for development, but this is NOT production-ready.
    # A real implementation would look something like:
    # return auth_service.find_active_backend_session(backend)
    active_sessions = auth_service.get_all_active_sessions()
    for token, session_data in active_sessions.items():
        if session_data.get("backend") == backend:
            # We should probably also check if the token is still valid
            # with the client, but for now this is a good approximation.
            return session_data.get("user_id")
    return None

async def handle_webex_webhook(webhook_data: Dict[str, Any]):
    if webhook_data.get('resource') != 'messages' or webhook_data.get('event') != 'created':
        logger.info("Ignoring Webex event because it's not a new message.")
        return {"status": "ignored", "reason": "Not a new message event."}

    details = await _get_bot_and_message_details(webhook_data)
    if not details:
        logger.warning("Could not retrieve bot or message details from Webex webhook.")
        return {"status": "ignored", "reason": "Could not retrieve bot or message details."}
    
    bot_client, message_text, room_id = details
    if not room_id:
        logger.error("Could not determine room_id from Webex webhook payload.")
        return {"status": "error", "detail": "Missing room_id."}

    active_user_id = await _find_active_user_session("webex")
    if not active_user_id:
        bot_client.post_message(room_id=room_id, text="No active Webex user session found to process this request.")
        logger.warning("No active Webex session found for bot request.")
        return {"status": "error", "detail": "No active Webex session."}

    webex_client = get_client("webex")
    await _process_webex_bot_command(bot_client, webex_client, active_user_id, room_id, message_text)
    return {"status": "processed"}

async def handle_telegram_webhook(bot_manager, bot_token: str, webhook_data: Dict[str, Any]):
    bot_config = bot_manager.get_bot_by_token("telegram", bot_token)
    if not bot_config:
        logger.error(f"Received webhook for unknown bot token: {bot_token}")
        return {"status": "error", "detail": "Bot not found"}, 404

    message = webhook_data.get('message')
    if not message:
        logger.info("Telegram webhook received without a message object.")
        return {"status": "ignored", "reason": "Not a message event."}

    chat_id = message.get('chat', {}).get('id')
    message_text = message.get('text', '').strip()

    if not chat_id or not message_text:
        logger.info("Telegram webhook message is missing chat_id or text.")
        return {"status": "ignored", "reason": "Missing chat_id or text."}

    active_user_id = await _find_active_user_session("telegram")
    bot_client = get_bot_client("telegram", bot_token) # Get bot client early for error reporting

    if not active_user_id:
        await bot_client.send_message(chat_id, "No active Telegram user session found to process this request.")
        logger.warning("No active Telegram session found for bot request.")
        return {"status": "error", "detail": "No active Telegram session."}

    telegram_client = get_client("telegram")
    
    bot_info = await bot_client.get_me()
    bot_id = bot_info.get("id")

    if not bot_id:
        logger.error(f"Could not determine bot_id for token {bot_token}")
        await bot_client.send_message(chat_id, "There was an internal error identifying the bot. Please contact an administrator.")
        return {"status": "error", "detail": "Could not identify bot."}

    chat_type = message.get('chat', {}).get('type')
    if chat_type in ['group', 'supergroup']:
        bot_username = bot_info.get("username")
        is_mentioned = bot_username and f"@{bot_username}" in message_text
        is_reply = 'reply_to_message' in message

        if not is_mentioned and not is_reply:
            logger.info(f"Ignoring message in group {chat_id} because bot was not mentioned or replied to.")
            return {"status": "ignored", "reason": "Bot not addressed in group"}

    if hasattr(bot_client, '_client') and isinstance(bot_client._client, TelegramBotClient):
        specific_bot_client = bot_client._client
    else:
        raise Exception("Could not retrieve specific TelegramBotClient from UnifiedBotClient")

    await _process_telegram_bot_command(specific_bot_client, telegram_client, active_user_id, chat_id, bot_id, message_text)
    return {"status": "processed"}

def initialize_bot_service(app_config: Dict[str, Any], manager: LLMManager):
    """
    Initializes the bot service with the global application config and the LLMManager.
    """
    global config, llm_manager
    config.update(app_config)
    llm_manager = manager
    logger.info("Bot service initialized with application config and LLMManager.")