import asyncpraw
import os
import json
import re
import httpx
import base64
import mimetypes
from datetime import datetime, timezone
from asyncpraw.models import MoreComments
from typing import List, Dict, Any, Optional

from clients.base_client import ChatClient, User, Chat, Message, Attachment

SESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

class RedditSessionManager:
    """
    Manages Reddit session data (e.g., refresh tokens).
    """
    @staticmethod
    def _get_session_file(username: str) -> str:
        safe_username = ''.join(filter(str.isalnum, username))
        return os.path.join(SESSION_DIR, f'reddit_session_{safe_username}.json')

    def save_token(self, username: str, refresh_token: str):
        session_file = self._get_session_file(username)
        with open(session_file, 'w') as f:
            json.dump({"refresh_token": refresh_token}, f)

    def get_token(self, username: str) -> Optional[str]:
        session_file = self._get_session_file(username)
        if not os.path.exists(session_file):
            return None
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            return session_data.get("refresh_token")
        except (json.JSONDecodeError, IOError):
            return None

    def delete_session(self, username: str):
        session_file = self._get_session_file(username)
        if os.path.exists(session_file):
            os.remove(session_file)

class ImageFetcher:
    """
    A helper class to fetch and process images from URLs.
    """
    def __init__(self, image_processing_settings: Optional[Dict[str, Any]] = None):
        self.enabled = image_processing_settings and image_processing_settings.get('enabled')

    async def fetch_images_from_text(self, text: str) -> List[Attachment]:
        if not self.enabled or not text:
            return []
        
        image_urls = set(re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|gif))', text))
        return await self._download_and_encode(image_urls)

    async def fetch_submission_images(self, submission) -> List[Attachment]:
        if not self.enabled:
            return []

        image_urls = set()
        # 1. Direct image link
        link_type, _ = mimetypes.guess_type(submission.url)
        if link_type and 'image' in link_type:
            image_urls.add(submission.url)

        # 2. Gallery images
        if getattr(submission, 'is_gallery', False):
            media_meta = getattr(submission, 'media_metadata', {})
            if media_meta:
                for media_id, meta in media_meta.items():
                    if meta.get('e') == 'Image':
                        url = meta.get('s', {}).get('u')
                        if url:
                            import html
                            image_urls.add(html.unescape(url))
        
        return await self._download_and_encode(image_urls)

    async def _download_and_encode(self, urls: set) -> List[Attachment]:
        attachments = []
        async with httpx.AsyncClient() as client:
            for url in urls:
                try:
                    response = await client.get(url, timeout=10.0)
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', 'application/octet-stream')
                    if 'image' in content_type:
                        data = base64.b64encode(response.content).decode('utf-8')
                        attachments.append(Attachment(mime_type=content_type, data=data))
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    print(f"Failed to download image from {url}: {e}")
        return attachments

class RedditClient(ChatClient):
    """
    A client for interacting with Reddit as a chat service.
    """

    def __init__(self, config: Dict[str, Any]):
        self.reddit_config = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "user_agent": config["user_agent"],
        }
        self.reddit = asyncpraw.Reddit(**self.reddit_config)
        self.session_manager = RedditSessionManager()

    async def _get_reddit_instance(self, user_identifier: str) -> asyncpraw.Reddit:
        """
        Returns an authenticated asyncpraw.Reddit instance for the given user.
        """
        refresh_token = self.session_manager.get_token(user_identifier)
        if not refresh_token:
            raise Exception("Could not find refresh token for user.")
        return asyncpraw.Reddit(**self.reddit_config, refresh_token=refresh_token)

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
        if not refresh_token:
            raise ValueError("Could not get refresh token from authorization code.")
        
        # Now that we are authorized, get the username to create the session file
        temp_reddit_instance = asyncpraw.Reddit(
            **self.reddit_config,
            refresh_token=refresh_token
        )
        redditor = await temp_reddit_instance.user.me()
        username = redditor.name if redditor else "Unknown"

        if username == "Unknown":
            raise Exception("Could not determine Reddit username.")

        self.session_manager.save_token(username, refresh_token)

        return {"status": "success", "user_id": username, "token": refresh_token}

    async def logout(self, user_identifier: str) -> None:
        """
        Logs the user out and cleans up the session.
        """
        self.session_manager.delete_session(user_identifier)

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        """
        Fetches a structured list of subscribed subreddits, popular posts,
        and user's own posts for the hybrid dropdown.
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        reddit_user_instance = await self._get_reddit_instance(user_identifier)

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

        reddit_user_instance = await self._get_reddit_instance(user_identifier)

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

        # Check if chat_id is a URL and extract the submission ID
        submission_id = chat_id
        if "reddit.com" in chat_id:
            # It's a URL, so we must extract the ID
            url_match = re.search(r'comments/([a-zA-Z0-9]+)', chat_id)
            if url_match:
                submission_id = url_match.group(1)
            else:
                # If it looks like a URL but we can't parse it, raise an error
                raise ValueError("Invalid Reddit URL format. Could not extract submission ID.")

        reddit_user_instance = await self._get_reddit_instance(user_identifier)

        submission = await reddit_user_instance.submission(id=submission_id)
        messages: List[Message] = []

        # Set comment sort before fetching
        submission.comment_sort = "best"
        await submission.load()
        
        # 1. Add the post itself as the first message
        post_author = submission.author
        post_author_id = getattr(post_author, "id", "0") if post_author else "0"
        post_author_name = getattr(post_author, "name", "[deleted]") if post_author else "[deleted]"
        
        post_text = submission.title
        if submission.selftext:
            post_text = f"{submission.title}\n\n{submission.selftext}"

        image_fetcher = ImageFetcher(image_processing_settings)
        submission_attachments = await image_fetcher.fetch_submission_images(submission)
        text_attachments = await image_fetcher.fetch_images_from_text(post_text)
        attachments = submission_attachments + text_attachments

        messages.append(Message(
            id=submission.id,
            text=post_text,
            author=User(id=post_author_id, name=post_author_name),
            timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
            thread_id=None,
            attachments=attachments,
        ))

        # 2. Fetch and process all comments
        try:
            # Limit the expansion of "more comments" to prevent excessive API calls
            await submission.comments.replace_more(limit=32)
        except Exception as e:
            print(f"Error replacing 'more' comments: {e}")

        # Use a recursive helper function to traverse the comment tree
        async def _process_comment_tree(comment_list, parent_id):
            for comment in comment_list:
                if isinstance(comment, MoreComments):
                    continue

                comment_author = comment.author
                comment_author_id = getattr(comment_author, "id", "0") if comment_author else "0"
                comment_author_name = getattr(comment_author, "name", "[deleted]") if comment_author else "[deleted]"

                comment_attachments = await image_fetcher.fetch_images_from_text(comment.body)

                messages.append(Message(
                    id=comment.id,
                    text=comment.body,
                    author=User(id=comment_author_id, name=comment_author_name),
                    timestamp=datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                    thread_id=submission.id, # All comments belong to the same submission thread
                    parent_id=parent_id,
                    attachments=comment_attachments,
                ))

                # Recurse through replies
                if hasattr(comment, 'replies') and comment.replies:
                    await _process_comment_tree(comment.replies, parent_id=comment.id)

        await _process_comment_tree(submission.comments, parent_id=submission.id)

        return messages

    async def is_session_valid(self, user_identifier: str) -> bool:
        """
        Checks if the current session for the user is still active and authorized.
        """
        return self.session_manager.get_token(user_identifier) is not None
