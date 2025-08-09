import json
import logging
import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Local imports from our new structure
from bot_manager import BotManager
from services import auth_service, bot_service
from routers import downloads, auth, chat, bots
from llm.llm_client import initialize_llm_clients

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
config = {}
bot_manager = BotManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing...")
    auth_service.load_app_sessions()
    global config
    try:
        with open('config.json', 'r') as f:
            config.update(json.load(f))
    except FileNotFoundError:
        logger.error("config.json not found!")

    await initialize_llm_clients()
    bot_service.initialize_bot_service(config)
    
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


# ===================================================================
# Frontend Serving and App Registration
# ===================================================================
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(downloads.router, prefix="/api", tags=["Downloads"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(bots.router, prefix="/api")


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_flag = os.getenv("RELOAD", "false").lower() == "true"
    
    if reload_flag:
        logger.info(f"Server starting on {host}:{port} with RELOAD enabled.")
    else:
        logger.info(f"Server starting on {host}:{port} (Reload disabled).")
        
    uvicorn.run("app:app", host=host, port=port, reload=reload_flag)
