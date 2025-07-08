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
# This will store our secure session tokens: { "token": "user_id" }
# In a real production app, this should be a persistent store like Redis.
session_tokens: Dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing...")
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

@router_telegram.post("/login")
async def telegram_login(req: TelegramLoginRequest):
    try:
        client = get_client("telegram")
        return await client.login(req.dict())
    except Exception as e:
        logger.error(f"Telegram login failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router_telegram.post("/verify")
async def telegram_verify(req: TelegramVerifyRequest):
    try:
        client = get_client("telegram")
        verification_result = await client.verify(req.dict())
        
        if verification_result.get("status") == "success":
            user_id = verification_result["user_identifier"]
            # Generate a secure, URL-safe token
            token = secrets.token_urlsafe(32)
            # Store the mapping from token to the actual user_id (phone number)
            session_tokens[token] = user_id
            # Return the token to the client instead of the raw user_id
            return {"status": "success", "token": token}
            
        return verification_result
    except Exception as e:
        logger.error(f"Telegram verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# ===================================================================
# Webex Authentication Endpoints
# ===================================================================
@router_webex.get("/login")
async def webex_login():
    client = get_client("webex")
    response = await client.login({})
    if response.get("status") == "redirect_required":
        return RedirectResponse(url=response["url"])
    raise HTTPException(status_code=500, detail="Failed to get Webex auth URL.")

@router_webex.get("/callback")
async def webex_callback(code: str, request: Request):
    client = get_client("webex")
    try:
        response = await client.verify({"code": code})
        user_id = response.get("user_identifier")
        if not user_id:
            raise Exception("Verification did not return a user identifier.")
        
        base_url = str(request.base_url).rstrip('/')
        redirect_url = f"{base_url}?backend=webex&status=success&user_id={user_id}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Webex callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Webex authentication failed: {e}")

# ===================================================================
# Generic Endpoints (Post-Authentication)
# ===================================================================
async def get_current_user_id(
    backend: str = Query(...),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Dependency that handles both token (Telegram) and direct user_id (Webex) auth.
    """
    if backend == "telegram":
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required for Telegram.")
        
        scheme, _, token = authorization.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization scheme for Telegram.")
        
        telegram_user_id = session_tokens.get(token)
        if not telegram_user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired Telegram token.")
        return telegram_user_id
        
    elif backend == "webex":
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id query parameter is required for Webex.")
        return user_id
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid backend specified: {backend}")

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
        # If the server-side session is invalid, also remove the token if it's a telegram session
        if backend == "telegram":
            token_to_remove = next((token for token, uid in session_tokens.items() if uid == user_id), None)
            if token_to_remove:
                del session_tokens[token_to_remove]
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

class PrepareAnalysisRequest(BaseModel):
    chatId: str
    startDate: str
    endDate: str
    enableCaching: Optional[bool] = True

class AnalyzeRequest(BaseModel):
    modelName: str
    textToProcess: str
    startDate: str
    endDate: str
    question: Optional[str] = None

class LogoutRequest(BaseModel):
    pass # No body needed now, backend comes from query param

@router_api.post("/prepare-analysis")
async def prepare_analysis(req: PrepareAnalysisRequest, user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    client = get_client(backend)
    messages: List[StandardMessage] = await client.get_messages(
        user_id, req.chatId, req.startDate, req.endDate, enable_caching=req.enableCaching if req.enableCaching is not None else True
    )
    
    if not messages:
        return {"num_messages": 0, "text_to_process": ""}

    text_to_process = "\n\n".join([f"[{m.author.name} at {m.timestamp}]: {m.text}" for m in messages])
    
    return {
        "num_messages": len(messages),
        "text_to_process": text_to_process
    }

@router_api.post("/analyze")
async def analyze_text_stream(req: AnalyzeRequest):
    selected_provider = None
    client = None

    for provider, llm_client in llm_clients.items():
        if req.modelName in llm_client.get_available_models():
            selected_provider = provider
            client = llm_client
            break

    if not client:
        async def error_generator():
            yield f"Error: Selected model '{req.modelName}' is not available."
        return StreamingResponse(error_generator(), media_type="text/plain", status_code=400)

    async def stream_generator():
        try:
            stream = client.call_streaming(
                req.modelName, req.textToProcess, req.startDate, req.endDate, req.question
            )
            async for chunk in stream:
                yield chunk
        except Exception as e:
            logger.error(f"Unhandled error in streaming generator for model {req.modelName}: {e}", exc_info=True)
            yield f"\n\n**Fatal Error:** An unexpected error occurred during the analysis stream. Please check the server logs."

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
    
@router_api.post("/logout")
async def logout(user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    # Invalidate the token if it's a telegram logout
    if backend == "telegram":
        token_to_remove = next((token for token, uid in session_tokens.items() if uid == user_id), None)
        if token_to_remove in session_tokens:
            del session_tokens[token_to_remove]

    # Log out from the client service
    client = get_client(backend)
    await client.logout(user_id)
    
    return {"status": "success", "message": "Logout successful."}

# ===================================================================
# Frontend Serving and App Registration
# ===================================================================
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

app.include_router(router_telegram)
app.include_router(router_webex)
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
