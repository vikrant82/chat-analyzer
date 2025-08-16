import asyncpraw
import os
import json
from datetime import datetime, timezone
from asyncpraw.models import MoreComments
from typing import List, Dict, Any, Optional

from clients.base_client import ChatClient, User, Chat, Message, Attachment

SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

def get_reddit_session_file(username: str) -> str:
    safe_username = ''.join(filter(str.isalnum, username))
    return os.path.join(SESSION_DIR, f'reddit_session_{safe_username}.json')

class RedditClient(ChatClient):
    """
    A client for interacting with Reddit as a chat service.
    """

    def __init__(self, config: Dict[str, Any]):
        self.reddit = asyncpraw.Reddit(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=config["redirect_uri"],
            user_agent=config["user_agent"],
        )
        # self.auth_details is removed, we use files now.

    async def login(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates the authorization URL for the user to visit.
        """
        scopes = ["identity", "read", "history", "subscribe", "vote", "mysubreddits"]
        auth_url = self.reddit.auth.url(scopes=scopes, state="...", implicit=False)
        return {"status": "redirect", "url": auth_url}

    async def verify(self, auth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Completes the login/verification process using the code from the callback.
        """
        code = auth_details.get("code")
        if not code:
            raise ValueError("Authorization code not provided.")

        # Exchange the code for a refresh token
        refresh_token = await self.reddit.auth.authorize(code)
        
        # Now that we are authorized, get the username to create the session file
        temp_reddit_instance = asyncpraw.Reddit(
            client_id=self.reddit.config.client_id,
            client_secret=self.reddit.config.client_secret,
            refresh_token=refresh_token,
            user_agent=self.reddit.config.user_agent,
        )
        redditor = await temp_reddit_instance.user.me()
        username = redditor.name if redditor else "Unknown"

        if username == "Unknown":
            raise Exception("Could not determine Reddit username.")

        session_file = get_reddit_session_file(username)
        with open(session_file, 'w') as f:
            json.dump({"refresh_token": refresh_token}, f)

        return {"status": "success", "user_id": username, "token": refresh_token}

    async def logout(self, user_identifier: str) -> None:
        """
        Logs the user out and cleans up the session.
        """
        session_file = get_reddit_session_file(user_identifier)
        if os.path.exists(session_file):
            os.remove(session_file)

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        """
        Fetches a structured list of subscribed subreddits, popular posts,
        and user's own posts for the hybrid dropdown.
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        session_file = get_reddit_session_file(user_identifier)
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        refresh_token = session_data.get("refresh_token")
        
        # Create a new authorized instance for this user
        reddit_user_instance = asyncpraw.Reddit(
            client_id=self.reddit.config.client_id,
            client_secret=self.reddit.config.client_secret,
            refresh_token=refresh_token,
            user_agent=self.reddit.config.user_agent,
        )

        chats = []

        # 1. Get subscribed subreddits
        try:
            async for sub in reddit_user_instance.user.subreddits(limit=200):
                chats.append(Chat(id=f"sub_{sub.display_name}", title=f"Subreddit: {sub.display_name}", type="subreddit"))
        except Exception as e:
            print(f"Could not fetch subscribed subreddits: {e}")


        # 2. Get popular posts
        try:
            popular_subreddit = await reddit_user_instance.subreddit("popular")
            async for submission in popular_subreddit.hot(limit=10):
                chats.append(Chat(id=submission.id, title=f"Popular: {submission.title}", type="post"))
        except Exception as e:
            print(f"Could not fetch popular posts: {e}")

        # 3. Get user's own recent posts
        try:
            user = await reddit_user_instance.user.me()
            if user:
                async for submission in user.submissions.new(limit=10):
                    chats.append(Chat(id=submission.id, title=f"My Post: {submission.title}", type="post"))
        except Exception as e:
            print(f"Could not fetch user's own posts: {e}")

        return chats

    async def get_posts_for_subreddit(self, user_identifier: str, subreddit_name: str) -> List[Chat]:
        """
        Fetches the top posts for a given subreddit.
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        session_file = get_reddit_session_file(user_identifier)
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        refresh_token = session_data.get("refresh_token")
        reddit_user_instance = asyncpraw.Reddit(
            client_id=self.reddit.config.client_id,
            client_secret=self.reddit.config.client_secret,
            refresh_token=refresh_token,
            user_agent=self.reddit.config.user_agent,
        )

        chats = []
        subreddit = await reddit_user_instance.subreddit(subreddit_name)
        async for submission in subreddit.hot(limit=50):
            chats.append(Chat(id=submission.id, title=submission.title, type="post"))
        
        return chats

    async def get_messages(self, user_identifier: str, chat_id: str, start_date_str: str, end_date_str: str, enable_caching: bool = True, image_processing_settings: Optional[Dict[str, Any]] = None, timezone_str: Optional[str] = None) -> List[Message]:
        """
        Fetches a post and its entire comment tree as a list of messages,
        with pre-formatted indentation for threading.
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        session_file = get_reddit_session_file(user_identifier)
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        refresh_token = session_data.get("refresh_token")
        reddit_user_instance = asyncpraw.Reddit(
            client_id=self.reddit.config.client_id,
            client_secret=self.reddit.config.client_secret,
            refresh_token=refresh_token,
            user_agent=self.reddit.config.user_agent,
        )

        submission = await reddit_user_instance.submission(id=chat_id)
        messages: List[Message] = []

        # Set comment sort before fetching
        submission.comment_sort = "best"
        
        # 1. Add the post itself as the first message
        post_author = submission.author
        post_author_id = getattr(post_author, "id", "0") if post_author else "0"
        post_author_name = getattr(post_author, "name", "[deleted]") if post_author else "[deleted]"
        
        post_text = submission.title
        if submission.selftext:
            post_text = f"{submission.title}\n\n{submission.selftext}"

        messages.append(Message(
            id=submission.id,
            text=post_text,
            author=User(id=post_author_id, name=post_author_name),
            timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
            thread_id=None,
        ))

        # 2. Fetch and process all comments
        try:
            # Limit the expansion of "more comments" to prevent excessive API calls
            await submission.comments.replace_more(limit=32)
        except Exception as e:
            print(f"Error replacing 'more' comments: {e}")

        # Use a recursive helper function to traverse the comment tree
        def _process_comment_tree(comment_list, depth=0):
            for comment in comment_list:
                if isinstance(comment, MoreComments):
                    continue

                comment_author = comment.author
                comment_author_id = getattr(comment_author, "id", "0") if comment_author else "0"
                comment_author_name = getattr(comment_author, "name", "[deleted]") if comment_author else "[deleted]"

                # Pre-format the text with indentation
                indent = "    " * depth
                text = f"{indent}{comment.body}"

                messages.append(Message(
                    id=comment.id,
                    text=text,
                    author=User(id=comment_author_id, name=comment_author_name),
                    timestamp=datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                    thread_id=submission.id, # All comments belong to the same submission thread
                ))
                
                # Recurse through replies
                if hasattr(comment, 'replies') and comment.replies:
                    _process_comment_tree(comment.replies, depth + 1)
        
        _process_comment_tree(submission.comments)

        return messages

    async def is_session_valid(self, user_identifier: str) -> bool:
        """
        Checks if the current session for the user is still active and authorized.
        """
        session_file = get_reddit_session_file(user_identifier)
        if not os.path.exists(session_file):
            return False
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            return "refresh_token" in session_data
        except (json.JSONDecodeError, IOError):
            return False
