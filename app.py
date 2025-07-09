import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, APIRouter, Depends, Header
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import AsyncGenerator

# Local imports from our new structure
from clients.factory import get_client
from clients.base_client import Message as StandardMessage
from ai.factory import get_all_llm_clients

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
conversations: Dict[str, List[Dict[str, str]]] = {}
message_cache: Dict[str, str] = {}
session_tokens: Dict[str, str] = {}
SESSIONS_FILE = "sessions/app_sessions.json"

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
    startDate: str
    endDate: str
    enableCaching: bool
    conversation: List[Dict[str, str]]
    originalMessages: Optional[str] = None # This is no longer sent from the client, but kept for compatibility

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing...")
    _load_app_sessions()
    global llm_clients
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
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
router_telegram = APIRouter(prefix="/api/telegram", tags=["Telegram Authentication"])
router_webex = APIRouter(prefix="/api/webex", tags=["Webex Authentication"])
router_api = APIRouter(prefix="/api", tags=["Generic API"])

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
            session_tokens[token] = user_id
            _save_app_sessions()
            return {"status": "success", "token": token}
            
        return verification_result
    except Exception as e:
        logger.error(f"Telegram verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# ===================================================================
# Webex Authentication Endpoints
# ===================================================================
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

@router_webex.get("/callback")
async def webex_callback(code: str, request: Request):
    client = get_client("webex")
    try:
        response = await client.verify({"code": code})
        user_id = response.get("user_identifier")
        if not user_id:
            raise Exception("Verification did not return a user identifier.")
        
        token = secrets.token_urlsafe(32)
        session_tokens[token] = user_id
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
    
    user_id = session_tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return user_id

@router_api.get("/models")
async def get_models():
    all_models = {}
    default_models = {}
    
    for provider, client in llm_clients.items():
        models = client.get_available_models()
        all_models[f"{provider}_models"] = models
        
        default_model = client.get_default_model()
        if default_model and default_model in models:
            default_models[provider] = default_model
        else:
            default_models[provider] = None

    if not any(all_models.values()):
        raise HTTPException(status_code=500, detail="No AI models configured or loaded successfully.")

    return {**all_models, "default_models": default_models}

@router_api.get("/session-status")
async def get_session_status(user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    client = get_client(backend)
    is_valid = await client.is_session_valid(user_id)
    if is_valid:
        return {"status": "authorized"}
    else:
        token_to_remove = next((token for token, uid in session_tokens.items() if uid == user_id), None)
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
    llm_client = None
    for provider, client in llm_clients.items():
        if req.modelName in client.get_available_models():
            llm_client = client
            break
    
    if not llm_client:
        raise HTTPException(status_code=400, detail=f"Selected model '{req.modelName}' is not available.")

    token = next((t for t, uid in session_tokens.items() if uid == user_id), None)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")

    cache_key = f"{token}_{req.chatId}_{req.startDate}_{req.endDate}"

    if cache_key not in message_cache:
        logger.info(f"Cache MISS for conversation key: {cache_key}. Fetching messages.")
        chat_client = get_client(backend)
        messages_list: List[StandardMessage] = await chat_client.get_messages(
            user_id, req.chatId, req.startDate, req.endDate, enable_caching=req.enableCaching
        )
        if not messages_list:
            async def empty_message_stream():
                yield "No messages found in the selected date range. Please select a different range."
            return StreamingResponse(empty_message_stream(), media_type="text/event-stream")
        
        original_messages = "\n\n".join([f"[{m.author.name} at {m.timestamp}]: {m.text}" for m in messages_list])
        message_cache[cache_key] = original_messages
        message_count = len(messages_list)
    else:
        logger.info(f"Cache HIT for conversation key: {cache_key}. Using cached messages.")
        original_messages = message_cache[cache_key]
        message_count = len(original_messages.split('\n\n'))

    current_conversation = list(req.conversation)
    
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Found {message_count} messages. Summarizing...'})}\n\n"
        
        try:
            stream = llm_client.call_conversational(
                req.modelName,
                current_conversation,
                original_messages
            )
            async for chunk in stream:
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Unhandled error in conversational streaming generator: {e}", exc_info=True)
            yield f"\n\n**Fatal Error:** An unexpected error occurred during the analysis stream. Please check the server logs."

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@router_api.post("/clear-session")
async def clear_session(user_id: str = Depends(get_current_user_id)):
    token = next((t for t, uid in session_tokens.items() if uid == user_id), None)
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
    token_to_remove = next((token for token, uid in session_tokens.items() if uid == user_id), None)

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
# Frontend Serving and App Registration
# ===================================================================
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

app.include_router(router_telegram) # Keep for /verify
app.include_router(router_webex) # Keep for /callback
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
