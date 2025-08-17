import logging
from typing import List
from clients.base_client import Chat

from clients.reddit_client import RedditClient
from llm.llm_client import LLMManager

logger = logging.getLogger(__name__)

async def get_posts_for_subreddit(client: RedditClient, user_id: str, subreddit: str) -> List[Chat]:
    """
    Gets the posts for a given subreddit.
    """
    return await client.get_posts_for_subreddit(user_id, subreddit)
