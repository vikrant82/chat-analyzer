import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from bot_manager import BotManager
from clients.bot_factory import get_bot_client
from services import auth_service, bot_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bot Management & Webhooks"])

# This is a temporary solution for dependency management.
# In a larger app, consider a more robust dependency injection pattern.
bot_manager = BotManager()

# --- Pydantic Models ---
class BotRegistrationRequest(BaseModel):
    name: str
    token: str
    bot_id: str
    webhook_url: Optional[str] = None

# --- Bot Management Endpoints ---

@router.post("/{backend}/bots")
async def register_bot(backend: str, req: BotRegistrationRequest, user_id: str = Depends(auth_service.get_current_user_id)):
    try:
        bot_manager.register_bot(backend, req.name, req.token, req.bot_id)
        if req.webhook_url:
            bot_client = get_bot_client(backend, req.token)
            if backend == "webex":
                webhook_name = f"Chat Analyzer - {req.name}"
                # The webhook path is now defined in this router, so we can construct it
                target_url = f"{req.webhook_url.rstrip('/')}/api/bots/webex/webhook"
                await bot_client.create_webhook(
                    webhook_name=webhook_name,
                    target_url=target_url,
                    resource="messages",
                    event="created",
                    filter_str="mentionedPeople=me"
                )
            elif backend == "telegram":
                target_url = f"{req.webhook_url.rstrip('/')}/api/bots/telegram/webhook/{req.token}"
                await bot_client.set_webhook(target_url)
            return {"status": "success", "message": f"Bot '{req.name}' registered and webhook created."}
        return {"status": "success", "message": f"Bot '{req.name}' registered for {backend}."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register bot: {e}")

@router.get("/{backend}/bots")
async def get_bots(backend: str, user_id: str = Depends(auth_service.get_current_user_id)):
    return bot_manager.get_bots(backend)

@router.delete("/{backend}/bots/{bot_name}")
async def delete_bot(backend: str, bot_name: str, user_id: str = Depends(auth_service.get_current_user_id)):
    try:
        bot_manager.delete_bot(backend, bot_name)
        return {"status": "success", "message": f"Bot '{bot_name}' deleted."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {e}")

# --- Bot Webhook Endpoints ---

@router.post("/bots/webex/webhook")
async def webex_webhook(req: Request):
    try:
        webhook_data = await req.json()
        logger.info(f"Received Webex webhook: {webhook_data}")
        result = await bot_service.handle_webex_webhook(webhook_data)
        return result
    except Exception as e:
        logger.error(f"Error processing Webex webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@router.post("/bots/telegram/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, req: Request):
    try:
        webhook_data = await req.json()
        logger.info(f"Received Telegram webhook for bot token: {bot_token[:5]}...")
        result = await bot_service.handle_telegram_webhook(bot_manager, bot_token, webhook_data)
        
        # The service layer returns a tuple of (response_dict, status_code) on error
        if isinstance(result, tuple):
            response_data, status_code = result
            raise HTTPException(status_code=status_code, detail=response_data.get("detail"))
            
        return result
    except HTTPException:
        raise # Re-raise HTTPException to let FastAPI handle it
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}
