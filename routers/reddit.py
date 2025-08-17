import logging
from fastapi import APIRouter, Depends, HTTPException

from services import auth_service, reddit_service
from clients.factory import get_client
from clients.reddit_client import RedditClient

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/reddit/posts")
async def get_reddit_posts(subreddit: str, user_id: str = Depends(auth_service.get_current_user_id)):
    try:
        client = get_client("reddit")
        if isinstance(client, RedditClient):
            return await reddit_service.get_posts_for_subreddit(client, user_id, subreddit)
        else:
            raise HTTPException(status_code=400, detail="The configured backend is not Reddit.")
    except Exception as e:
        logger.error(f"Failed to get posts for subreddit {subreddit}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
