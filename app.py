
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import uvicorn
import google.generativeai as genai
from google.generativeai.types import generation_types
from fastapi import FastAPI, HTTPException, Query, Request, APIRouter
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Local imports from our new structure
from clients.factory import get_client
from clients.base_client import Message as StandardMessage

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
AVAILABLE_MODELS: Dict[str, List[str]] = {
    "google_ai": [],
    "lm_studio": []
}
LM_STUDIO_URL = None
GOOGLE_AI_CONFIG = {}
LM_STUDIO_CONFIG = {}
DEPRECATED_GOOGLE_MODELS = {"gemini-1.0-pro-vision-latest"}

# --- AI Model Initialization & Calling Logic (Restored from original file) ---

async def initialize_google_ai_models():
    global AVAILABLE_MODELS, GOOGLE_AI_CONFIG
    if not GOOGLE_AI_CONFIG.get('api_key'):
        logger.warning("Google AI API key not configured. Models will be unavailable.")
        AVAILABLE_MODELS["google_ai"] = []
        return
    try:
        logger.info("Asynchronously listing Google AI models...")
        models_iterator = await asyncio.to_thread(genai.list_models)
        supported_models = []
        for m in models_iterator:
            model_name = m.name.replace("models/", "")
            if 'generateContent' in m.supported_generation_methods and model_name not in DEPRECATED_GOOGLE_MODELS:
                supported_models.append(model_name)
        AVAILABLE_MODELS["google_ai"] = sorted(supported_models)
        logger.info(f"Discovered usable Google AI models: {AVAILABLE_MODELS['google_ai']}")
    except Exception as e:
        logger.error(f"Failed to list models from Google AI: {e}", exc_info=True)
        AVAILABLE_MODELS["google_ai"] = []

async def initialize_lm_studio_models():
    global LM_STUDIO_URL, AVAILABLE_MODELS, LM_STUDIO_CONFIG
    if not LM_STUDIO_CONFIG or not LM_STUDIO_CONFIG.get('url'):
        logger.warning("LM Studio URL not configured. Models will not be available.")
        AVAILABLE_MODELS["lm_studio"] = []
        return

    LM_STUDIO_URL = LM_STUDIO_CONFIG['url']
    models_url = LM_STUDIO_URL.replace('/v1/chat/completions', '/v1/models')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            logger.info(f"Fetching LM Studio models from: {models_url}")
            response = await client.get(models_url)
            response.raise_for_status()
            models_data = response.json()
            model_ids = [model['id'] for model in models_data.get('data', []) if 'id' in model]
            AVAILABLE_MODELS["lm_studio"] = sorted(list(set(model_ids)))
            if AVAILABLE_MODELS["lm_studio"]:
                logger.info(f"Discovered LM Studio models: {AVAILABLE_MODELS['lm_studio']}")
            else:
                logger.warning("LM Studio query successful but no models found.")
    except Exception as e:
        logger.error(f"Failed to fetch LM Studio models from {models_url}: {e}", exc_info=True)
        AVAILABLE_MODELS["lm_studio"] = []

async def _call_google_ai(
    model_name: str,
    text_to_summarize: str,
    start_date_str: str,
    end_date_str: str,
    question: Optional[str] = None
) -> str:
    if model_name not in AVAILABLE_MODELS.get("google_ai", []):
        logger.error(f"Attempted to use unconfigured or filtered Google AI model: {model_name}")
        raise HTTPException(status_code=400, detail=f"Invalid, unavailable, or filtered Google AI model selected: {model_name}")

    logger.info(f"Sending {len(text_to_summarize)} chars to Google AI ({model_name}) for {'question answering' if question else 'summarization'}...")
    try:
        full_model_name = f"models/{model_name}"
        model = genai.GenerativeModel(full_model_name)
        generation_config = genai.types.GenerationConfig(temperature=0.7, top_p=0.9, top_k=40)
        safety_settings = {} 

        if question:
            prompt = f"""You are a helpful assistant. Based ONLY on the following chat log excerpts from {start_date_str} to {end_date_str}, answer the user's question accurately. If the answer cannot be determined from the provided text, explicitly state that the information is not available in the chat log for the given period. Do not make up information or answer based on external knowledge. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate.

--- CHAT LOG START ---
{text_to_summarize}
--- CHAT LOG END ---

User's Question: {question}

Answer:"""
            logger.debug(f"Google AI Question Prompt (first 100 chars): {prompt[:100]}...")
        else:
            prompt = f"""You are a helpful assistant that summarizes chat conversations concisely. For group conversations, you summarize them under various categories. If the chat messages are related to shopping deals, categorize them into appropriate item categories, highlighting best deals and include the links for the deals if present in the messages. The messages are from the period between {start_date_str} and {end_date_str}. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate.

--- CHAT LOG START ---
{text_to_summarize}
--- CHAT LOG END ---

Summary:"""
            logger.debug(f"Google AI Summary Prompt (first 100 chars): {prompt[:100]}...")


        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        try:
            result_text = response.text.strip()
            if not result_text:
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason = response.prompt_feedback.block_reason.name
                     logger.warning(f"Google AI response blocked ({model_name}) due to safety settings: {block_reason}")
                     raise HTTPException(status_code=400, detail=f"Content blocked by safety filter: {block_reason}. Cannot generate result.")
                 elif response.candidates and response.candidates[0].finish_reason != generation_types.FinishReason.STOP:
                      finish_reason = response.candidates[0].finish_reason.name
                      logger.warning(f"Google AI generation stopped unexpectedly ({model_name}): {finish_reason}")
                      raise HTTPException(status_code=500, detail=f"AI generation failed with reason: {finish_reason}")
                 else:
                      logger.warning(f"Google AI ({model_name}) returned an empty result without explicit blocking.")
                      result_text = "The AI model returned an empty result."
            return result_text
        except ValueError as val_err: 
             block_reason_str = "Unknown"
             try: 
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason_str = response.prompt_feedback.block_reason.name
             except Exception: pass
             logger.error(f"Google AI Value Error ({model_name}, likely prompt blocked: {block_reason_str}): {val_err}", exc_info=True)
             raise HTTPException(status_code=400, detail=f"Content blocked by safety filter ({block_reason_str}) or invalid request. Cannot generate result.")
        except generation_types.StopCandidateException as stop_ex: 
            finish_reason = "Unknown"
            if hasattr(stop_ex, 'finish_reason') and stop_ex.finish_reason: 
                 finish_reason = stop_ex.finish_reason.name
            logger.warning(f"Google AI generation stopped unexpectedly ({model_name}): {finish_reason}", exc_info=True)
            try: 
                partial_result = response.text.strip() if response.text else ""
                if partial_result:
                    logger.warning("Using potentially incomplete result due to stop reason.")
                    return partial_result + f"\n\n[Note: Result may be incomplete due to generation stopping early ({finish_reason})]"
            except Exception:
                pass 
            raise HTTPException(status_code=500, detail=f"AI generation stopped unexpectedly ({finish_reason}).")


    except generation_types.BlockedPromptException as bpe:
        logger.error(f"Google AI API Error ({model_name}): Prompt Blocked - {bpe}", exc_info=True)
        raise HTTPException(status_code=400, detail="Content blocked by safety filter before generation. Cannot generate result.")
    except Exception as e:
        if "model" in str(e).lower() and "not found" in str(e).lower(): 
            logger.error(f"Google AI API reported model '{model_name}' not found: {e}", exc_info=True)
            raise HTTPException(status_code=404, detail=f"The selected Google AI model ('{model_name}') was not found by the API.")
        logger.error(f"Error calling Google AI ({model_name}) or processing its response: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to get result from Google AI service ({model_name}).")


async def _call_lm_studio(
    model_name: str,
    text_to_summarize: str,
    start_date_str: str,
    end_date_str: str,
    question: Optional[str] = None
) -> str:
    if model_name not in AVAILABLE_MODELS.get("lm_studio", []):
        logger.error(f"Attempted to use unconfigured LM Studio model: {model_name}")
        raise HTTPException(status_code=400, detail=f"Invalid or unconfigured LM Studio model selected: {model_name}")
    
    if not LM_STUDIO_URL: 
         logger.error(f"LM Studio URL not available/configured when trying to call model {model_name}")
         raise HTTPException(status_code=500, detail="LM Studio provider URL not configured on the server.")

    chat_completions_url = LM_STUDIO_URL

    logger.info(f"Sending {len(text_to_summarize)} chars to LM Studio ({model_name} at {chat_completions_url}) for {'question answering' if question else 'summarization'}...")
    try:
        system_content = ""
        user_content = ""
        if question:
            system_content = "You are a helpful assistant. Based ONLY on the following chat log, answer the user's question. If the answer is not in the log, say so. Do not make up information. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate."
            user_content = f"Chat log from {start_date_str} to {end_date_str}:\n---\n{text_to_summarize}\n---\n\nUser Question: {question}"
            logger.debug(f"LM Studio Question Prompt (User content starts): {user_content[:100]}...")
        else:
            system_content = "You are a helpful assistant that summarizes chat conversations concisely. For group conversations, you summarize them under various categories. If the chat messages are related to shopping deals, categorize them into appropriate item categories, and highlighting best deals and include the links for the deals. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate."
            user_content = f"Please summarize the following chat messages between {start_date_str} and {end_date_str}:\n\n---\n{text_to_summarize}\n---"
            logger.debug(f"LM Studio Summary Prompt (User content starts): {user_content[:100]}...")

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "system", "content": "/nothink"}, 
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 1024, 
            "temperature": 0.7, 
            "stream": False
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client: 
            response = await client.post(chat_completions_url, json=payload)
            response.raise_for_status()
            result = response.json()

        result_text = ""
        if 'choices' in result and isinstance(result['choices'], list) and len(result['choices']) > 0:
            first_choice = result['choices'][0]
            if 'message' in first_choice and isinstance(first_choice['message'], dict):
                if 'content' in first_choice['message']:
                    result_text = str(first_choice['message']['content']).strip()

        if not result_text:
             logger.warning(f"LM Studio response ({model_name}) did not contain content in the expected format. Result: %s", result)
             result_text = "The AI model returned an empty or improperly formatted result."

        return result_text

    except httpx.TimeoutException:
        logger.error(f"Request to LM Studio ({model_name}) timed out.")
        raise HTTPException(status_code=504, detail=f"Request to language model ({model_name}) timed out.")
    except httpx.RequestError as e:
         logger.error(f"Could not connect to LM Studio ({model_name}) at {chat_completions_url}: {e}", exc_info=True)
         raise HTTPException(status_code=503, detail=f"Could not connect to language model service (LM Studio).")
    except httpx.HTTPStatusError as e:
         logger.error(f"LM Studio service ({model_name}) returned error {e.response.status_code}: {e.response.text}", exc_info=True)
         raise HTTPException(status_code=502, detail=f"Language model service ({model_name}) error: {e.response.status_code}.")
    except (KeyError, IndexError, Exception) as e: 
        logger.error(f"Error processing LM Studio ({model_name}) response or other unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process request via LM Studio ({model_name}).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing...")
    global GOOGLE_AI_CONFIG, LM_STUDIO_CONFIG
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        GOOGLE_AI_CONFIG = config.get('google_ai', {})
        LM_STUDIO_CONFIG = config.get('lm_studio', {})
        if GOOGLE_AI_CONFIG.get('api_key'):
            genai.configure(api_key=GOOGLE_AI_CONFIG['api_key'])
    except FileNotFoundError:
        logger.error("config.json not found!")
    
    await asyncio.gather(
        initialize_google_ai_models(),
        initialize_lm_studio_models()
    )
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
        return await client.verify(req.dict())
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
@router_api.get("/models")
async def get_models():
    if not AVAILABLE_MODELS["google_ai"] and not AVAILABLE_MODELS["lm_studio"]:
         raise HTTPException(status_code=500, detail="No AI models configured or loaded successfully.")

    # Determine the default model for each provider
    default_google = GOOGLE_AI_CONFIG.get("default_model")
    default_lm_studio = LM_STUDIO_CONFIG.get("default_model")
    
    # A default is only valid if it's in the list of available models
    valid_default_google = default_google if default_google in AVAILABLE_MODELS["google_ai"] else None
    valid_default_lm_studio = default_lm_studio if default_lm_studio in AVAILABLE_MODELS["lm_studio"] else None

    return {
        "google_ai_models": AVAILABLE_MODELS["google_ai"],
        "lm_studio_models": AVAILABLE_MODELS["lm_studio"],
        "default_models": {
            "google_ai": valid_default_google,
            "lm_studio": valid_default_lm_studio
        }
    }

@router_api.get("/session-status")
async def get_session_status(backend: str, user_id: str):
    client = get_client(backend)
    is_valid = await client.is_session_valid(user_id)
    if is_valid:
        return {"status": "authorized"}
    else:
        raise HTTPException(status_code=401, detail="Session not valid or expired.")

@router_api.get("/chats")
async def get_all_chats(backend: str, user_id: str):
    try:
        client = get_client(backend)
        return await client.get_chats(user_id)
    except Exception as e:
        logger.error(f"Failed to get chats for {backend}: {e}", exc_info=True)
        if "401" in str(e) or "authoriz" in str(e).lower():
            raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
        raise HTTPException(status_code=500, detail=str(e))

class PrepareAnalysisRequest(BaseModel):
    backend: str
    userId: str
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

@router_api.post("/prepare-analysis")
async def prepare_analysis(req: PrepareAnalysisRequest):
    client = get_client(req.backend)
    messages: List[StandardMessage] = await client.get_messages(
        req.userId, req.chatId, req.startDate, req.endDate, enable_caching=req.enableCaching
    )
    
    if not messages:
        return {"num_messages": 0, "text_to_process": ""}

    text_to_process = "\n\n".join([f"[{m.author.name} at {m.timestamp}]: {m.text}" for m in messages])
    
    return {
        "num_messages": len(messages),
        "text_to_process": text_to_process
    }

@router_api.post("/analyze")
async def analyze_text(req: AnalyzeRequest):
    selected_provider = None
    if req.modelName in AVAILABLE_MODELS.get("google_ai", []):
        selected_provider = "google_ai"
    elif req.modelName in AVAILABLE_MODELS.get("lm_studio", []):
        selected_provider = "lm_studio"
    else:
        raise HTTPException(status_code=400, detail=f"Selected model '{req.modelName}' is not available.")

    ai_result = ""
    try:
        if selected_provider == 'google_ai':
            ai_result = await _call_google_ai(req.modelName, req.textToProcess, req.startDate, req.endDate, req.question)
        elif selected_provider == 'lm_studio':
            ai_result = await _call_lm_studio(req.modelName, req.textToProcess, req.startDate, req.endDate, req.question)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"AI call failed for model {req.modelName}: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"Failed to get response from AI service: {e}")
        raise e

    return {"ai_summary": ai_result}
    
@router_api.post("/logout")
async def logout(req: dict):
    backend = req.get("backend")
    user_id = req.get("userId")
    if not all([backend, user_id]):
        raise HTTPException(status_code=400, detail="Backend and userId are required.")
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
