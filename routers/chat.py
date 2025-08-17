import logging
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse

from services.chat_service import ChatMessage, process_chat_request
from services import auth_service, chat_service
from llm.llm_client import LLMManager
from clients.factory import get_client

logger = logging.getLogger(__name__)

router = APIRouter()

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

@router.get("/models")
async def get_models(llm_manager: LLMManager = Depends(get_llm_manager)):
    all_models = []
    default_model_info = {}

    for provider, client in llm_manager.clients.items():
        models = client.get_available_models()
        for model_name in models:
            all_models.append({"provider": provider, "model": model_name})
        
        default_model = client.get_default_model()
        if default_model and default_model in models:
            default_model_info = {"provider": provider, "model": default_model}

    if not all_models:
        raise HTTPException(status_code=500, detail="No AI models configured or loaded successfully.")

    return {"models": all_models, "default_model_info": default_model_info}

@router.get("/chats")
async def get_all_chats(user_id: str = Depends(auth_service.get_current_user_id), backend: str = Query(...)):
    try:
        client = get_client(backend)
        return await client.get_chats(user_id)
    except Exception as e:
        logger.error(f"Failed to get chats for {backend}: {e}", exc_info=True)
        if "401" in str(e) or "authoriz" in str(e).lower():
            raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(
    req: ChatMessage,
    user_id: str = Depends(auth_service.get_current_user_id),
    backend: str = Query(...),
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    stream_generator = await process_chat_request(req, user_id, backend, llm_manager)
    return StreamingResponse(stream_generator, media_type="text/event-stream")

@router.post("/clear-session")
async def clear_session(user_id: str = Depends(auth_service.get_current_user_id), backend: str = Query(...)):
    token = auth_service.get_token_for_user(user_id, backend)
    if not token:
        raise HTTPException(status_code=401, detail="Could not find session token for user.")
    
    chat_service.clear_chat_cache(token)
    chat_service.clear_conversation_history(token)
        
    return {"status": "success", "message": "Session data cleared."}
