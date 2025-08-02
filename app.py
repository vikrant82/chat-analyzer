import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple
import asyncio
import base64
import textwrap
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, APIRouter, Depends, Header
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
from io import BytesIO

# Local imports from our new structure
from clients.factory import get_client
from clients.bot_factory import get_bot_client
from clients.base_client import Message as StandardMessage
from clients.telegram_bot_client_impl import TelegramBotClient
from ai.factory import get_all_llm_clients
from bot_manager import BotManager

# --- Basic Setup & Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Global Configuration & State ---
llm_clients = {}
config = {}
conversations: Dict[str, List[Dict[str, str]]] = {}
message_cache: Dict[str, str] = {}
chat_modes: Dict[int, str] = {} # Tracks the mode for each chat_id
session_tokens: Dict[str, Dict[str, str]] = {}
SESSIONS_FILE = "sessions/app_sessions.json"
bot_manager = BotManager()

def _save_app_sessions():
    """Saves the current session_tokens dictionary to the file system."""
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(session_tokens, f)

def _load_app_sessions():
    """Loads session_tokens from the file system if the file exists."""
    global session_tokens
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                session_tokens = json.load(f)
            logger.info(f"Successfully loaded {len(session_tokens)} app sessions.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load app sessions from {SESSIONS_FILE}: {e}")
            session_tokens = {}
    else:
        logger.info("No app session file found. Starting with empty sessions.")
        session_tokens = {}

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    message: Optional[str] = None # Can be empty on first call
    chatId: str
    modelName: str
    provider: str
    startDate: str
    endDate: str
    enableCaching: bool
    conversation: List[Dict[str, Any]] # Can now contain complex content
    originalMessages: Optional[List[Dict[str, Any]]] = None # To hold the structured message data
    imageProcessing: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None

class DownloadRequest(BaseModel):
    chatId: str
    startDate: str
    endDate: str
    enableCaching: bool
    format: str  # 'pdf' or 'txt'

class BotRegistrationRequest(BaseModel):
    name: str
    token: str
    bot_id: str
    webhook_url: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing...")
    _load_app_sessions()
    global llm_clients, config
    try:
        with open('config.json', 'r') as f:
            config.update(json.load(f))
        google_ai_config = config.get('google_ai', {})
        openai_compatible_configs = config.get('openai_compatible', [])
        llm_clients = get_all_llm_clients(google_ai_config, openai_compatible_configs)
        
        initialization_tasks = [client.initialize_models() for client in llm_clients.values()]
        await asyncio.gather(*initialization_tasks)

    except FileNotFoundError:
        logger.error("config.json not found!")
    
    yield
    logger.info("Application shutdown.")

# --- FastAPI App Initialization ---
app = FastAPI(title="Multi-Backend Chat Analyzer", version="2.1.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware)

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# ===================================================================
# API ROUTERS
# ===================================================================
router_telegram = APIRouter(prefix="/api/telegram", tags=["Telegram"])
router_webex = APIRouter(prefix="/api/webex", tags=["Webex"])
router_api = APIRouter(prefix="/api", tags=["Generic API"])
router_bot = APIRouter(prefix="/api/bot", tags=["Bot Webhooks"])

# ===================================================================
# Telegram Authentication Endpoints
# ===================================================================
class TelegramLoginRequest(BaseModel):
    phone: str

class TelegramVerifyRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None

@router_telegram.post("/verify")
async def telegram_verify(req: TelegramVerifyRequest):
    try:
        client = get_client("telegram")
        verification_result = await client.verify(req.dict())
        
        if verification_result.get("status") == "success":
            user_id = verification_result["user_identifier"]
            token = secrets.token_urlsafe(32)
            session_tokens[token] = {"user_id": user_id, "backend": "telegram"}
            _save_app_sessions()
            return {"status": "success", "token": token}
            
        return verification_result
    except Exception as e:
        logger.error(f"Telegram verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# ===================================================================
# Webex Authentication Endpoints
# ===================================================================
@router_webex.get("/callback")
async def webex_callback(code: str, request: Request):
    client = get_client("webex")
    try:
        response = await client.verify({"code": code})
        user_id = response.get("user_identifier")
        if not user_id:
            raise Exception("Verification did not return a user identifier.")
        
        token = secrets.token_urlsafe(32)
        session_tokens[token] = {"user_id": user_id, "backend": "webex"}
        _save_app_sessions()
        
        base_url = str(request.base_url).rstrip('/')
        redirect_url = f"{base_url}?token={token}&backend=webex"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Webex callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Webex authentication failed: {e}")

# ===================================================================
# Generic Endpoints (Post-Authentication)
# ===================================================================
async def get_current_user_id(authorization: str = Header(...)) -> str:
    """
    Dependency that handles unified token-based authentication.
    """
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme.")
    
    session_data = session_tokens.get(token)
    if not session_data or "user_id" not in session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return session_data["user_id"]

@router_api.post("/login")
async def unified_login(req: Request, backend: str = Query(...)):
    client = get_client(backend)
    try:
        if backend == 'telegram':
            body = await req.json()
            return await client.login(body)
        else:
            response = await client.login({})
            if response.get("status") == "redirect_required":
                return response
            raise HTTPException(status_code=500, detail=f"Failed to get {backend} auth URL.")
    except Exception as e:
        logger.error(f"{backend} login failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router_api.get("/models")
async def get_models():
    all_models = []
    default_model_info = {}

    for provider, client in llm_clients.items():
        models = client.get_available_models()
        for model_name in models:
            all_models.append({"provider": provider, "model": model_name})
        
        default_model = client.get_default_model()
        if default_model and default_model in models:
            default_model_info = {"provider": provider, "model": default_model}

    if not all_models:
        raise HTTPException(status_code=500, detail="No AI models configured or loaded successfully.")

    return {"models": all_models, "default_model_info": default_model_info}

@router_api.get("/session-status")
async def get_session_status(user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    client = get_client(backend)
    is_valid = await client.is_session_valid(user_id)
    if is_valid:
        return {"status": "authorized"}
    else:
        token_to_remove = next((token for token, data in session_tokens.items() if data.get("user_id") == user_id), None)
        if token_to_remove:
            keys_to_delete = [key for key in message_cache if key.startswith(token_to_remove)]
            for key in keys_to_delete:
                del message_cache[key]
                logger.info(f"Cleaned up message cache for invalid session: {key}")

            if token_to_remove in conversations:
                del conversations[token_to_remove]
                logger.info(f"Cleaned up conversation history for invalid session: {token_to_remove}")
                
            if token_to_remove in session_tokens:
                del session_tokens[token_to_remove]
                logger.info(f"Removed invalid session token: {token_to_remove}")
            _save_app_sessions()

        raise HTTPException(status_code=401, detail="Session not valid or expired.")

@router_api.get("/chats")
async def get_all_chats(user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    try:
        client = get_client(backend)
        return await client.get_chats(user_id)
    except Exception as e:
        logger.error(f"Failed to get chats for {backend}: {e}", exc_info=True)
        if "401" in str(e) or "authoriz" in str(e).lower():
            raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
        raise HTTPException(status_code=500, detail=str(e))

class LogoutRequest(BaseModel):
    pass # No body needed now, backend comes from query param

@router_api.post("/chat")
async def chat(req: ChatMessage, user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    llm_client = llm_clients.get(req.provider)

    if not llm_client:
        raise HTTPException(status_code=400, detail=f"Invalid provider '{req.provider}' specified.")

    if req.modelName not in llm_client.get_available_models():
        raise HTTPException(status_code=400, detail=f"Model '{req.modelName}' is not available for provider '{req.provider}'.")

    token = next((t for t, data in session_tokens.items() if data.get("user_id") == user_id), None)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")

    cache_key = f"{token}_{req.chatId}_{req.startDate}_{req.endDate}"
    
    # --- Cache Invalidation for Today's Date ---
    # Parse end date and compare with today's date to decide if caching is safe.
    try:
        end_date_dt = datetime.strptime(req.endDate, '%Y-%m-%d').date()
        today_dt = datetime.now(timezone.utc).date()
        is_historical_date = end_date_dt < today_dt
    except ValueError:
        logger.warning(f"Could not parse endDate '{req.endDate}'. Disabling cache for this request.")
        is_historical_date = False

    # The in-memory cache is only used if the user enabled it AND the date range is in the past.
    use_in_memory_cache = req.enableCaching and is_historical_date

    if use_in_memory_cache and cache_key in message_cache:
        logger.info(f"Cache HIT for conversation key: {cache_key}. Using cached messages.")
        original_messages_structured = json.loads(message_cache[cache_key])
        # This is an approximation, but good enough for the UI
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
        }
        if backend == 'webex':
            get_messages_kwargs["image_processing_settings"] = req.imageProcessing

        messages_list: List[StandardMessage] = await chat_client.get_messages(**get_messages_kwargs)
        if not messages_list:
            async def empty_message_stream():
                yield f"data: {json.dumps({'type': 'content', 'chunk': 'No messages found in the selected date range. Please select a different range.'})}\n\n"
            return StreamingResponse(empty_message_stream(), media_type="text/event-stream")
        
        original_messages_structured = _format_messages_for_llm(messages_list)
        message_count = len(messages_list)
        
        # Only cache the result if the date range does not include today and the user has enabled caching
        if use_in_memory_cache:
            logger.info(f"Storing result in in-memory cache for key: {cache_key}")
            message_cache[cache_key] = json.dumps(original_messages_structured)

    current_conversation = list(req.conversation)
    
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Found {message_count} messages. Summarizing...'})}\n\n"
        
        try:
            # Dont try to fix this error
            stream = llm_client.call_conversational(
                req.modelName,
                current_conversation,
                original_messages_structured
            )
            # Dont try to fix this error
            async for chunk in stream:
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Unhandled error in conversational streaming generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'An unexpected error occurred: {e}'})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

def _format_messages_for_llm(messages: List[StandardMessage]) -> List[Dict[str, Any]]:
    """
    Formats a list of StandardMessage objects into a structured format for the LLM,
    handling text, attachments, and threading context.
    """
    formatted_parts = []
    in_thread = False
    
    for msg in messages:
        is_reply = msg.thread_id is not None
        
        # --- Handle Thread Markers ---
        if is_reply and not in_thread:
            formatted_parts.append({"type": "text", "text": "\n--- Thread Started ---"})
            in_thread = True
        elif not is_reply and in_thread:
            formatted_parts.append({"type": "text", "text": "--- Thread Ended ---\n"})
            in_thread = False

        # --- Construct the Message Content ---
        message_content = []
        
        # Add a text part for the author and timestamp header
        prefix = "    " if is_reply else ""
        header = f"{prefix}[{msg.author.name} at {msg.timestamp}]:"
        message_content.append({"type": "text", "text": header})

        # Add the main text of the message, if it exists
        if msg.text:
            message_content.append({"type": "text", "text": f" {msg.text}"})

        # Add any image attachments
        if msg.attachments:
            for attachment in msg.attachments:
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": attachment.mime_type,
                        "data": attachment.data,
                    },
                })
        
        # The role is always 'user' as this represents the chat history
        formatted_parts.append({"role": "user", "content": message_content})

    # If the last message was in a thread, close it
    if in_thread:
        formatted_parts.append({"type": "text", "text": "--- Thread Ended ---"})
        
    # This is a simplification. We need to combine consecutive text parts for some models.
    # For now, we will return the list of parts and let the LLM client handle it.
    # A better approach would be to create a single "user" message with multiple content parts.
    
    final_messages = []
    current_user_parts = []

    for part in formatted_parts:
        if part.get('role') == 'user':
            if current_user_parts:
                 # Combine consecutive text parts within a single user message
                combined_text = "".join(p['text'] for p in current_user_parts if p['type'] == 'text')
                final_content = [{"type": "text", "text": combined_text}]
                # Add images
                final_content.extend([p for p in current_user_parts if p['type'] == 'image'])
                final_messages.append({"role": "user", "content": final_content})

            current_user_parts = part['content']
        elif part['type'] == 'text': # Thread markers
             current_user_parts.append(part)


    # Add the last user message
    if current_user_parts:
        combined_text = "".join(p['text'] for p in current_user_parts if p['type'] == 'text')
        final_content = [{"type": "text", "text": combined_text}]
        final_content.extend([p for p in current_user_parts if p['type'] == 'image'])
        final_messages.append({"role": "user", "content": final_content})

    return final_messages


def _break_long_words(text: str, max_len: int) -> str:
    """Inserts spaces into words longer than max_len to allow for line breaking."""
    words = text.split(' ')
    new_words = []
    for word in words:
        if len(word) > max_len:
            # This is a simple way to break long words.
            # It's not perfect but should prevent the FPDF error.
            new_words.append(' '.join(textwrap.wrap(word, max_len, break_long_words=True)))
        else:
            new_words.append(word)
    return ' '.join(new_words)

def _create_pdf(text: str, chat_id: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Chat History: {chat_id}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    safe_text = _break_long_words(text.encode('latin-1', 'replace').decode('latin-1'), 80)
    pdf.multi_cell(0, 5, safe_text)
    
    pdf_bytes = pdf.output(dest='S')
    output = BytesIO(pdf_bytes)
    output.seek(0)
    return output

@router_api.post("/download")
async def download_chat(req: DownloadRequest, user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    chat_client = get_client(backend)
    messages_list: List[StandardMessage] = await chat_client.get_messages(
        user_id, req.chatId, req.startDate, req.endDate, enable_caching=req.enableCaching
    )

    if not messages_list:
        raise HTTPException(status_code=404, detail="No messages found in the selected date range.")

    # Format messages with thread context
    formatted_parts = []
    in_thread = False
    for i, msg in enumerate(messages_list):
        is_reply = msg.thread_id is not None
        
        # Check if a thread is starting
        if is_reply and not in_thread:
            formatted_parts.append("\n--- Thread Started ---")
            in_thread = True
        
        # Check if a thread is ending
        if not is_reply and in_thread:
            formatted_parts.append("--- Thread Ended ---\n")
            in_thread = False

        # Format the message itself
        prefix = "    " if is_reply else ""
        text_content = msg.text or ""
        if msg.attachments:
            text_content += f" (Image Attachment: {', '.join([att.mime_type for att in msg.attachments])})"
        
        formatted_parts.append(f"{prefix}[{msg.author.name} at {msg.timestamp}]: {text_content}")

    # If the last message was in a thread, close it
    if in_thread:
        formatted_parts.append("--- Thread Ended ---")

    chat_history = "\n".join(formatted_parts)
    
    if req.format == "pdf":
        pdf_buffer = _create_pdf(chat_history, req.chatId)
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.pdf\""})
    else: # txt
        return StreamingResponse(
            iter([chat_history.encode('utf-8')]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.txt\""}
        )

@router_api.post("/clear-session")
async def clear_session(user_id: str = Depends(get_current_user_id)):
    token = next((t for t, data in session_tokens.items() if data.get("user_id") == user_id), None)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")
    
    keys_to_delete = [key for key in message_cache if key.startswith(token)]
    for key in keys_to_delete:
        del message_cache[key]
        logger.info(f"Removed message cache for key: {key}")

    if token in conversations:
        del conversations[token]
        logger.info(f"Removed conversation history for token: {token}")
        
    return {"status": "success", "message": "Session data cleared."}

@router_api.post("/logout")
async def logout(user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    token_to_remove = next((token for token, data in session_tokens.items() if data.get("user_id") == user_id), None)

    if token_to_remove:
        keys_to_delete = [key for key in message_cache if key.startswith(token_to_remove)]
        for key in keys_to_delete:
            del message_cache[key]
            logger.info(f"Removed message cache for key: {key}")

        if token_to_remove in conversations:
            del conversations[token_to_remove]
            logger.info(f"Removed conversation history for token: {token_to_remove}")
            
        if token_to_remove in session_tokens:
            del session_tokens[token_to_remove]
            logger.info(f"Removed session token: {token_to_remove}")
        _save_app_sessions()

    client = get_client(backend)
    await client.logout(user_id)
    
    return {"status": "success", "message": "Logout successful."}

# ===================================================================
# Bot Management Endpoints
# ===================================================================
@router_webex.post("/bots", tags=["Bot Management"])
async def register_webex_bot(req: BotRegistrationRequest, user_id: str = Depends(get_current_user_id)):
    try:
        bot_manager.register_bot("webex", req.name, req.token, req.bot_id)
        if req.webhook_url:
            bot_client = get_bot_client("webex", req.token)
            webhook_name = f"Chat Analyzer - {req.name}"
            target_url = f"{req.webhook_url.rstrip('/')}/api/bot/webex/webhook"
            await bot_client.create_webhook(
                webhook_name=webhook_name,
                target_url=target_url,
                resource="messages",
                event="created",
                filter_str="mentionedPeople=me"
            )
            return {"status": "success", "message": f"Bot '{req.name}' registered and webhook created."}
        return {"status": "success", "message": f"Bot '{req.name}' registered for webex."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register bot: {e}")

@router_webex.get("/bots", tags=["Bot Management"])
async def get_webex_bots(user_id: str = Depends(get_current_user_id)):
    return bot_manager.get_bots("webex")

@router_webex.delete("/bots/{bot_name}", tags=["Bot Management"])
async def delete_webex_bot(bot_name: str, user_id: str = Depends(get_current_user_id)):
    try:
        bot_manager.delete_bot("webex", bot_name)
        return {"status": "success", "message": f"Bot '{bot_name}' deleted."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {e}")

@router_telegram.post("/bots", tags=["Bot Management"])
async def register_telegram_bot(req: BotRegistrationRequest, user_id: str = Depends(get_current_user_id)):
    try:
        bot_manager.register_bot("telegram", req.name, req.token, req.bot_id)
        if req.webhook_url:
            bot_client = get_bot_client("telegram", req.token)
            target_url = f"{req.webhook_url.rstrip('/')}/api/bot/telegram/webhook/{req.token}"
            await bot_client.set_webhook(target_url)
            return {"status": "success", "message": f"Bot '{req.name}' registered and webhook set."}
        return {"status": "success", "message": f"Bot '{req.name}' registered for telegram."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register bot: {e}")

@router_telegram.get("/bots", tags=["Bot Management"])
async def get_telegram_bots(user_id: str = Depends(get_current_user_id)):
    return bot_manager.get_bots("telegram")

@router_telegram.delete("/bots/{bot_name}", tags=["Bot Management"])
async def delete_telegram_bot(bot_name: str, user_id: str = Depends(get_current_user_id)):
    try:
        bot_manager.delete_bot("telegram", bot_name)
        return {"status": "success", "message": f"Bot '{bot_name}' deleted."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {e}")

# ===================================================================
# Bot Webhook Endpoints
# ===================================================================
def _find_bot_in_config(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helper function to find the mentioned bot in the global config."""
    mentioned_ids_encoded = webhook_data.get('data', {}).get('mentionedPeople', [])
    if not mentioned_ids_encoded:
        logger.info("Webhook received, but no one was mentioned.")
        return None

    webex_bots = config.get('bots', {}).get('webex', [])

    # Decode all mentioned IDs from Base64
    decoded_mentioned_uuids = set()
    for encoded_id in mentioned_ids_encoded:
        try:
            padded_id = encoded_id + '=' * (-len(encoded_id) % 4)
            decoded_uri = base64.urlsafe_b64decode(padded_id).decode('utf-8')
            decoded_mentioned_uuids.add(decoded_uri.split('/')[-1])
        except Exception as e:
            logger.warning(f"Could not decode a mentioned ID: {encoded_id}, Error: {e}")
            continue

    # Find the first registered bot that matches one of the decoded mentioned IDs
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

async def _find_active_user_session(backend: str) -> Optional[str]:
    client = get_client(backend)
    for token, session_data in session_tokens.items():
        if session_data.get("backend") == backend:
            user_id_to_check = session_data.get("user_id")
            if user_id_to_check and await client.is_session_valid(user_id_to_check):
                return user_id_to_check
    return None

async def _process_bot_command(bot_client: Any, webex_client: Any, active_user_id: str, room_id: str, message_text: str):
    import re
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

        llm_provider = next(iter(llm_clients))
        llm_client = llm_clients[llm_provider]
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        conversation_history = [{"role": "user", "content": query}]
        stream = await llm_client.call_conversational(model_name, conversation_history, formatted_messages_structured)

        ai_response = ""
        async for chunk in stream:
            ai_response += chunk
        
        bot_client.post_message(room_id=room_id, text=ai_response)

    except Exception as e:
        logger.error(f"Bot failed to process message: {e}", exc_info=True)
        error_message = "I encountered an error trying to process your request. Please check the server logs."
        bot_client.post_message(room_id=room_id, text=error_message)

async def _handle_ai_mode(bot_client: Any, user_chat_id: int, message_text: str):
    """Handles direct interaction with the AI in a conversational manner."""
    try:
        conversation_key = f"telegram_bot_{user_chat_id}"
        
        # Retrieve or initialize the conversation history
        history = conversations.get(conversation_key, [])
        
        # Add the new user message
        history.append({"role": "user", "content": message_text})
        
        # Ensure the history doesn't grow too large (e.g., keep last 20 messages)
        if len(history) > 20:
            history = history[-20:]

        # Get a default LLM client
        llm_provider = next(iter(llm_clients))
        llm_client = llm_clients[llm_provider]
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        # Call the conversational endpoint without providing original_messages
        # Dont try to fix this error
        stream = llm_client.call_conversational(model_name, history, None)

        ai_response = ""
        # Dont try to fix this error
        async for chunk in stream:
            ai_response += chunk
        
        # Add the AI's full response to the history
        history.append({"role": "assistant", "content": ai_response})
        
        # Store the updated history
        conversations[conversation_key] = history
        
        # Send the response to the user
        await bot_client.send_message(user_chat_id, ai_response)

    except Exception as e:
        logger.error(f"Error in AI mode: {e}", exc_info=True)
        error_message = "I encountered an error in AI mode. Please try again."
        await bot_client.send_message(user_chat_id, error_message)

async def _handle_summarizer_mode(bot_client: Any, telegram_client: Any, active_user_id: str, user_chat_id: int, bot_id: int, message_text: str):
    """Handles the original chat summarization logic."""
    import re
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
            active_user_id,
            str(bot_id),
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            enable_caching=False
        )
        
        if not messages_list:
            await bot_client.send_message(user_chat_id, "No messages found in the specified date range.")
            return

        formatted_messages_structured = _format_messages_for_llm(messages_list)

        llm_provider = next(iter(llm_clients))
        llm_client = llm_clients[llm_provider]
        model_name = llm_client.get_default_model()
        if not model_name:
            raise Exception("No default AI model configured for the bot.")

        conversation_history = [{"role": "user", "content": query}]
        # Dont try to fix this error
        stream = llm_client.call_conversational(model_name, conversation_history, formatted_messages_structured)

        ai_response = ""
        # Dont try to fix this error
        async for chunk in stream:
            ai_response += chunk
        
        await bot_client.send_message(user_chat_id, ai_response)

    except Exception as e:
        logger.error(f"Bot failed to process message: {e}", exc_info=True)
        error_message = "I encountered an error trying to process your request. Please check the server logs."
        await bot_client.send_message(user_chat_id, error_message)

async def _process_telegram_bot_command(bot_client: Any, telegram_client: Any, active_user_id: str, user_chat_id: int, bot_id: int, message_text: str):
    """
    Acts as a dispatcher for Telegram bot commands.
    Handles mode switching and delegates to the appropriate handler.
    """
    if message_text.strip() == '/aimode':
        current_mode = chat_modes.get(user_chat_id, 'summarizer')
        if current_mode == 'summarizer':
            chat_modes[user_chat_id] = 'aimode'
            await bot_client.send_message(user_chat_id, "AI mode enabled. I will now respond directly. Send /aimode again to switch back.")
        else:
            chat_modes[user_chat_id] = 'summarizer'
            # Also clear conversation history for this chat
            conversation_key = f"telegram_bot_{user_chat_id}"
            if conversation_key in conversations:
                del conversations[conversation_key]
                logger.info(f"Cleared conversation history for chat {user_chat_id} upon switching to summarizer mode.")
            await bot_client.send_message(user_chat_id, "Summarizer mode enabled.")
        return

    # Delegate to the correct handler based on the current mode
    current_mode = chat_modes.get(user_chat_id, 'summarizer')
    if current_mode == 'aimode':
        await _handle_ai_mode(bot_client, user_chat_id, message_text)
    else:
        await _handle_summarizer_mode(bot_client, telegram_client, active_user_id, user_chat_id, bot_id, message_text)

@router_bot.post("/webex/webhook")
async def webex_webhook(req: Request):
    try:
        webhook_data = await req.json()
        logger.info(f"Received Webex webhook: {webhook_data}")

        if webhook_data.get('resource') != 'messages' or webhook_data.get('event') != 'created':
            return {"status": "ignored", "reason": "Not a new message event."}

        details = await _get_bot_and_message_details(webhook_data)
        if not details:
            return {"status": "ignored", "reason": "Could not retrieve bot or message details."}
        
        bot_client, message_text, room_id = details
        if not room_id:
            logger.error("Could not determine room_id from webhook payload.")
            return {"status": "error", "detail": "Missing room_id."}

        active_user_id = await _find_active_user_session("webex")
        if not active_user_id:
            bot_client.post_message(room_id=room_id, text="No active Webex user session found to process this request.")
            return {"status": "error", "detail": "No active Webex session."}

        webex_client = get_client("webex")
        await _process_bot_command(bot_client, webex_client, active_user_id, room_id, message_text)

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Webex webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@router_bot.post("/telegram/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, req: Request):
    try:
        bot_config = bot_manager.get_bot_by_token("telegram", bot_token)
        if not bot_config:
            logger.error(f"Received webhook for unknown bot token: {bot_token}")
            raise HTTPException(status_code=404, detail="Bot not found")

        webhook_data = await req.json()
        logger.info(f"Received Telegram webhook for bot {bot_config['name']}: {webhook_data}")

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
        if not active_user_id:
            # Need a bot client to respond, even if there's no user session
            temp_bot_client = get_bot_client("telegram", bot_token)
            await temp_bot_client.send_message(chat_id, "No active Telegram user session found to process this request.")
            return {"status": "error", "detail": "No active Telegram session."}

        telegram_client = get_client("telegram")
        bot_client = get_bot_client("telegram", bot_token)
        
        bot_info = await bot_client.get_me()
        bot_id = bot_info.get("id")

        if not bot_id:
            logger.error(f"Could not determine bot_id for token {bot_token}")
            # Optionally, send a message back to the user
            await bot_client.send_message(chat_id, "There was an internal error identifying the bot. Please contact an administrator.")
            return {"status": "error", "detail": "Could not identify bot."}

        # In group chats, only respond if mentioned or replied to.
        chat_type = message.get('chat', {}).get('type')
        if chat_type in ['group', 'supergroup']:
            bot_username = bot_info.get("username")
            is_mentioned = bot_username and f"@{bot_username}" in message_text
            is_reply = 'reply_to_message' in message

            if not is_mentioned and not is_reply:
                logger.info(f"Ignoring message in group {chat_id} because bot was not mentioned or replied to.")
                return {"status": "ignored", "reason": "Bot not addressed in group"}

        # We need to pass the specific TelegramBotClient to the processing function
        # as it has methods not on the unified client, like send_message.
        # A better long-term fix is to unify all required methods.
        if hasattr(bot_client, '_client') and isinstance(bot_client._client, TelegramBotClient):
            specific_bot_client = bot_client._client
        else:
            # Fallback or error if the structure is not as expected
            raise Exception("Could not retrieve specific TelegramBotClient from UnifiedBotClient")

        await _process_telegram_bot_command(specific_bot_client, telegram_client, active_user_id, chat_id, bot_id, message_text)

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

# ===================================================================
# Frontend Serving and App Registration
# ===================================================================
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

app.include_router(router_telegram)
app.include_router(router_webex)
app.include_router(router_bot)
app.include_router(router_api)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_flag = os.getenv("RELOAD", "false").lower() == "true"
    
    if reload_flag:
        logger.info(f"Server starting on {host}:{port} with RELOAD enabled.")
    else:
        logger.info(f"Server starting on {host}:{port} (Reload disabled).")
        
    uvicorn.run("app:app", host=host, port=port, reload=reload_flag)
