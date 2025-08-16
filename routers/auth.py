from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from clients.factory import get_client
from services import auth_service

router = APIRouter()

class TelegramLoginRequest(BaseModel):
    phone: str

class TelegramVerifyRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None

class LogoutRequest(BaseModel):
    pass

@router.post("/telegram/verify")
async def telegram_verify(req: TelegramVerifyRequest):
    try:
        client = get_client("telegram")
        verification_result = await client.verify(req.dict())
        
        if verification_result.get("status") == "success":
            user_id = verification_result["user_identifier"]
            token = auth_service.create_session(user_id, "telegram")
            return {"status": "success", "token": token}
            
        return verification_result
    except Exception as e:
        # Assuming logger is available or passed in a real app
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/webex/callback")
async def webex_callback(code: str, request: Request):
    client = get_client("webex")
    try:
        response = await client.verify({"code": code})
        user_id = response.get("user_identifier")
        if not user_id:
            raise Exception("Verification did not return a user identifier.")
        
        token = auth_service.create_session(user_id, "webex")
        
        base_url = str(request.base_url).rstrip('/')
        redirect_url = f"{base_url}?token={token}&backend=webex"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webex authentication failed: {e}")

@router.get("/auth/callback/reddit")
async def reddit_callback(code: str, request: Request):
    client = get_client("reddit")
    try:
        # The user_id is not known yet, so we pass a temporary one.
        # The verify method will return the actual username.
        response = await client.verify({"code": code, "user_id": "temp_user"})
        user_id = response.get("user_id")
        if not user_id:
            raise Exception("Verification did not return a user identifier.")
        
        token = auth_service.create_session(user_id, "reddit")
        
        base_url = str(request.base_url).rstrip('/')
        redirect_url = f"{base_url}?token={token}&backend=reddit"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Reddit authentication failed: {e}")

@router.post("/login")
async def unified_login(req: Request, backend: str = Query(...)):
    client = get_client(backend)
    try:
        if backend == 'telegram':
            body = await req.json()
            return await client.login(body)
        else: # Handles Webex and Reddit
            response = await client.login({})
            if response.get("status") in ["redirect", "redirect_required"]:
                return response
            raise HTTPException(status_code=500, detail=f"Failed to get {backend} auth URL.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session-status")
async def get_session_status(user_id: str = Depends(auth_service.get_current_user_id), backend: str = Query(...)):
    client = get_client(backend)
    is_valid = await client.is_session_valid(user_id)
    if is_valid:
        return {"status": "authorized"}
    else:
        token_to_remove = auth_service.get_token_for_user(user_id, backend)
        if token_to_remove:
            # This part needs careful handling of shared state (message_cache, conversations)
            # For now, just deleting the session token
            auth_service.delete_session_by_token(token_to_remove)
        raise HTTPException(status_code=401, detail="Session not valid or expired.")

@router.post("/logout")
async def logout(user_id: str = Depends(auth_service.get_current_user_id), backend: str = Query(...)):
    token_to_remove = auth_service.get_token_for_user(user_id, backend)
    if token_to_remove:
        # Again, needs careful state management for cache and conversations
        auth_service.delete_session_by_token(token_to_remove)

    client = get_client(backend)
    await client.logout(user_id)
    
    return {"status": "success", "message": "Logout successful."}
