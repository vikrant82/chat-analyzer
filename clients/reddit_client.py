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
import asyncprawcore

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
    A helper class to fetch and process images from URLs with connection pooling and concurrency control.
    """
    def __init__(self, image_processing_settings: Optional[Dict[str, Any]] = None, global_max_concurrent: int = 20, user_agent: str = "ChatAnalyzer/1.0"):
        self.enabled = image_processing_settings and image_processing_settings.get('enabled')
        # Use per-request setting if provided, otherwise use global config
        self.max_concurrent_downloads = (
            image_processing_settings.get('max_concurrent_downloads', global_max_concurrent) 
            if image_processing_settings 
            else global_max_concurrent
        )
        
        # Configure HTTP client with connection pooling limits and timeouts
        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        )
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=5.0
        )
        
        headers = {"User-Agent": user_agent}
        self.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers)

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
        """
        Download and encode images with concurrency control to prevent connection pool exhaustion.
        """
        if not urls:
            return []
        
        import asyncio
        
        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_single_image(url: str) -> Optional[Attachment]:
            """Download a single image with semaphore-based rate limiting."""
            async with semaphore:
                try:
                    response = await self.http_client.get(url)
                    response.raise_for_status()
                    content_type = response.headers.get('content-type', 'application/octet-stream')
                    if 'image' in content_type:
                        data = base64.b64encode(response.content).decode('utf-8')
                        return Attachment(mime_type=content_type, data=data)
                except httpx.PoolTimeout:
                    print(f"Connection pool timeout while downloading {url}. Too many concurrent downloads.")
                    return None
                except httpx.TimeoutException as e:
                    print(f"Request timeout while downloading {url}: {e}")
                    return None
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    print(f"Failed to download image from {url}: {e}")
                    return None
        
        # Download all images in parallel with concurrency control
        results = await asyncio.gather(
            *[download_single_image(url) for url in urls],
            return_exceptions=True
        )
        
        # Filter out None values and exceptions
        attachments: List[Attachment] = [
            result for result in results
            if result is not None and not isinstance(result, Exception) and isinstance(result, Attachment)
        ]
        
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
        
        # Load configuration for limits and sorting
        self.subreddit_limit = config.get("subreddit_limit", 200)
        self.popular_posts_limit = config.get("popular_posts_limit", 10)
        self.user_posts_limit = config.get("user_posts_limit", 10)
        self.subreddit_posts_limit = config.get("subreddit_posts_limit", 50)
        self.default_sort = config.get("default_sort", "hot")
        self.default_time_filter = config.get("default_time_filter", "week")
        self.subreddit_sort = config.get("subreddit_sort", "subscribers")  # alphabetical, subscribers, activity
        self.show_favorites = config.get("show_favorites", True)
        self.favorites_limit = config.get("favorites_limit", 50)
        
        # Load image download configuration
        self.max_concurrent_image_downloads = config.get("max_concurrent_image_downloads", 20)

    async def _get_reddit_instance(self, user_identifier: str) -> asyncpraw.Reddit:
        """
        Returns an authenticated asyncpraw.Reddit instance for the given user.
        """
        refresh_token = self.session_manager.get_token(user_identifier)
        if not refresh_token:
            raise Exception("Could not find refresh token for user.")
        return asyncpraw.Reddit(**self.reddit_config, refresh_token=refresh_token)

    async def _fetch_posts_with_sort(self, subreddit, sort_method: str = None, time_filter: str = None, limit: int = 50) -> List:
        """
        Helper method to fetch posts from a subreddit with specified sorting and time filter.
        
        Args:
            subreddit: The subreddit object to fetch from
            sort_method: One of "hot", "new", "top", "controversial", "rising" (defaults to self.default_sort)
            time_filter: One of "hour", "day", "week", "month", "year", "all" (only used for "top" and "controversial")
            limit: Maximum number of posts to fetch
            
        Returns:
            List of submission objects
        """
        if sort_method is None:
            sort_method = self.default_sort
        if time_filter is None:
            time_filter = self.default_time_filter
            
        posts = []
        
        try:
            if sort_method == "hot":
                async for submission in subreddit.hot(limit=limit):
                    posts.append(submission)
            elif sort_method == "new":
                async for submission in subreddit.new(limit=limit):
                    posts.append(submission)
            elif sort_method == "top":
                async for submission in subreddit.top(time_filter=time_filter, limit=limit):
                    posts.append(submission)
            elif sort_method == "controversial":
                async for submission in subreddit.controversial(time_filter=time_filter, limit=limit):
                    posts.append(submission)
            elif sort_method == "rising":
                async for submission in subreddit.rising(limit=limit):
                    posts.append(submission)
            else:
                # Default to hot if invalid sort method
                async for submission in subreddit.hot(limit=limit):
                    posts.append(submission)
        except Exception as e:
            print(f"Error fetching posts with sort={sort_method}, time_filter={time_filter}: {e}")
            
        return posts

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

    async def get_favorite_subreddits(self, user_identifier: str) -> List[Chat]:
        """
        Fetches user's favorited subreddits and returns them with a star icon.
        
        Args:
            user_identifier: The Reddit username
            
        Returns:
            List of Chat objects for favorited subreddits with ⭐ prefix
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        reddit_user_instance = await self._get_reddit_instance(user_identifier)
        
        favorites = []
        
        try:
            favorites_with_metadata = []
            count = 0
            
            # Iterate through ALL subreddits to find favorites (not limited by subreddit_limit)
            # We use None to fetch all subscriptions, then limit how many favorites we DISPLAY
            async for sub in reddit_user_instance.user.subreddits(limit=None):
                # Check if this subreddit is favorited
                is_favorited = getattr(sub, 'user_has_favorited', False)
                
                if is_favorited:
                    try:
                        # Get subscriber count and activity indicator
                        subscribers = getattr(sub, 'subscribers', 0) or 0
                        active_users = getattr(sub, 'active_user_count', 0) or 0
                        
                        favorites_with_metadata.append({
                            'subreddit': sub,
                            'name': sub.display_name,
                            'subscribers': subscribers,
                            'active_users': active_users
                        })
                        
                        count += 1
                        if count >= self.favorites_limit:
                            break
                    except Exception as e:
                        # If metadata fetch fails, still add the favorite
                        favorites_with_metadata.append({
                            'subreddit': sub,
                            'name': sub.display_name,
                            'subscribers': 0,
                            'active_users': 0
                        })
                        count += 1
                        if count >= self.favorites_limit:
                            break
            
            # Sort favorites based on configuration (same as regular subreddits)
            if self.subreddit_sort == "alphabetical":
                favorites_with_metadata.sort(key=lambda x: x['name'].lower())
            elif self.subreddit_sort == "subscribers":
                favorites_with_metadata.sort(key=lambda x: x['subscribers'], reverse=True)
            elif self.subreddit_sort == "activity":
                favorites_with_metadata.sort(key=lambda x: x['active_users'], reverse=True)
            else:
                # Default to subscribers if invalid option
                favorites_with_metadata.sort(key=lambda x: x['subscribers'], reverse=True)
            
            # Build chat list with star icon and member counts
            for sub_data in favorites_with_metadata:
                # Format subscriber count (K, M notation)
                subscribers = sub_data['subscribers']
                if subscribers >= 1_000_000:
                    sub_display = f"{subscribers / 1_000_000:.1f}M"
                elif subscribers >= 1_000:
                    sub_display = f"{subscribers / 1_000:.1f}K"
                else:
                    sub_display = str(subscribers)
                
                # Add star emoji prefix for favorites
                title = f"⭐ Subreddit: {sub_data['name']} [{sub_display} members]"
                favorites.append(Chat(id=f"sub_{sub_data['name']}", title=title, type="subreddit"))
                
        except asyncprawcore.exceptions.ResponseException as e:
            if e.response.status_code == 400:
                print(f"Reddit session invalid for user {user_identifier}: {e}")
                await self.logout(user_identifier)
                raise ValueError("Reddit session expired or invalid. Please log in again.")
            raise e
        except Exception as e:
            print(f"Could not fetch favorite subreddits: {e}")
        
        return favorites

    async def get_chats(self, user_identifier: str) -> List[Chat]:
        """
        Fetches a structured list of favorited subreddits, subscribed subreddits, 
        popular posts, and user's own posts for the hybrid dropdown.
        
        Favorites appear first with a ⭐ icon if show_favorites is enabled.
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        reddit_user_instance = await self._get_reddit_instance(user_identifier)

        chats = []
        favorite_subreddit_names = set()

        try:
            # 0. Get favorite subreddits first (if enabled)
            if self.show_favorites:
                try:
                    favorites = await self.get_favorite_subreddits(user_identifier)
                    chats.extend(favorites)
                    # Track favorite names to avoid duplicates in regular list
                    for fav in favorites:
                        # Extract subreddit name from id (format: "sub_subredditname")
                        if fav.id.startswith("sub_"):
                            favorite_subreddit_names.add(fav.id.replace("sub_", ""))
                except Exception as e:
                    # If get_favorite_subreddits raised ValueError (session invalid), re-raise it
                    if "session expired" in str(e).lower():
                        raise e
                    print(f"Could not fetch favorite subreddits: {e}")

            # 1. Get subscribed subreddits with smart sorting (excluding favorites)
            try:
                subreddits_with_metadata = []
                async for sub in reddit_user_instance.user.subreddits(limit=self.subreddit_limit):
                    # Skip if already shown in favorites
                    if sub.display_name in favorite_subreddit_names:
                        continue
                        
                    # Fetch subreddit details for sorting metadata
                    try:
                        # Get subscriber count and activity indicator
                        subscribers = getattr(sub, 'subscribers', 0) or 0
                        active_users = getattr(sub, 'active_user_count', 0) or 0
                        
                        subreddits_with_metadata.append({
                            'subreddit': sub,
                            'name': sub.display_name,
                            'subscribers': subscribers,
                            'active_users': active_users
                        })
                    except Exception as e:
                        # If metadata fetch fails, still add the subreddit
                        subreddits_with_metadata.append({
                            'subreddit': sub,
                            'name': sub.display_name,
                            'subscribers': 0,
                            'active_users': 0
                        })
                
                # Sort subreddits based on configuration
                if self.subreddit_sort == "alphabetical":
                    subreddits_with_metadata.sort(key=lambda x: x['name'].lower())
                elif self.subreddit_sort == "subscribers":
                    subreddits_with_metadata.sort(key=lambda x: x['subscribers'], reverse=True)
                elif self.subreddit_sort == "activity":
                    subreddits_with_metadata.sort(key=lambda x: x['active_users'], reverse=True)
                else:
                    # Default to subscribers if invalid option
                    subreddits_with_metadata.sort(key=lambda x: x['subscribers'], reverse=True)
                
                # Build chat list with rich metadata
                for sub_data in subreddits_with_metadata:
                    # Format subscriber count (K, M notation)
                    subscribers = sub_data['subscribers']
                    if subscribers >= 1_000_000:
                        sub_display = f"{subscribers / 1_000_000:.1f}M"
                    elif subscribers >= 1_000:
                        sub_display = f"{subscribers / 1_000:.1f}K"
                    else:
                        sub_display = str(subscribers)
                    
                    title = f"Subreddit: {sub_data['name']} [{sub_display} members]"
                    chats.append(Chat(id=f"sub_{sub_data['name']}", title=title, type="subreddit"))
                    
            except asyncprawcore.exceptions.ResponseException as e:
                if e.response.status_code == 400:
                    print(f"Reddit session invalid during subreddits fetch for user {user_identifier}: {e}")
                    await self.logout(user_identifier)
                    raise ValueError("Reddit session expired or invalid. Please log in again.")
                raise e
            except Exception as e:
                print(f"Could not fetch subscribed subreddits: {e}")


            # 2. Get popular posts using configured sort method
            try:
                popular_subreddit = await reddit_user_instance.subreddit("popular")
                popular_posts = await self._fetch_posts_with_sort(
                    popular_subreddit, 
                    sort_method=self.default_sort,
                    time_filter=self.default_time_filter,
                    limit=self.popular_posts_limit
                )
                for submission in popular_posts:
                    # Add score and comment count for better context
                    chats.append(Chat(
                        id=submission.id, 
                        title=f"Popular: {submission.title} [{submission.score}⬆ {submission.num_comments}💬]", 
                        type="post"
                    ))
            except asyncprawcore.exceptions.ResponseException as e:
                if e.response.status_code == 400:
                    print(f"Reddit session invalid during popular posts fetch for user {user_identifier}: {e}")
                    await self.logout(user_identifier)
                    raise ValueError("Reddit session expired or invalid. Please log in again.")
                raise e
            except Exception as e:
                print(f"Could not fetch popular posts: {e}")

            # 3. Get user's own recent posts (always sorted by new)
            try:
                user = await reddit_user_instance.user.me()
                if user:
                    count = 0
                    async for submission in user.submissions.new(limit=self.user_posts_limit):
                        chats.append(Chat(
                            id=submission.id, 
                            title=f"My Post: {submission.title} [{submission.score}⬆ {submission.num_comments}💬]", 
                            type="post"
                        ))
                        count += 1
            except asyncprawcore.exceptions.ResponseException as e:
                if e.response.status_code == 400:
                    print(f"Reddit session invalid during user posts fetch for user {user_identifier}: {e}")
                    await self.logout(user_identifier)
                    raise ValueError("Reddit session expired or invalid. Please log in again.")
                raise e
            except Exception as e:
                print(f"Could not fetch user's own posts: {e}")
        
        except asyncprawcore.exceptions.ResponseException as e:
             if e.response.status_code == 400:
                print(f"Reddit session invalid for user {user_identifier}: {e}")
                await self.logout(user_identifier)
                raise ValueError("Reddit session expired or invalid. Please log in again.")
             raise e

        return chats

    async def get_posts_for_subreddit(self, user_identifier: str, subreddit_name: str, sort_method: str = None, time_filter: str = None) -> List[Chat]:
        """
        Fetches posts for a given subreddit with configurable sorting.
        
        Args:
            user_identifier: The user ID
            subreddit_name: Name of the subreddit
            sort_method: Optional override for sort method (hot, new, top, controversial, rising)
            time_filter: Optional override for time filter (hour, day, week, month, year, all)
            
        Returns:
            List of Chat objects representing posts with metadata
        """
        if not await self.is_session_valid(user_identifier):
            raise Exception("User session is not valid.")

        reddit_user_instance = await self._get_reddit_instance(user_identifier)

        chats = []
        try:
            subreddit = await reddit_user_instance.subreddit(subreddit_name)
            
            # Use configured defaults if not overridden
            posts = await self._fetch_posts_with_sort(
                subreddit,
                sort_method=sort_method,
                time_filter=time_filter,
                limit=self.subreddit_posts_limit
            )
            
            for submission in posts:
                # Calculate engagement score for better insights
                engagement_ratio = submission.num_comments / max(submission.score, 1)
                
                # Add rich metadata to help users identify interesting posts
                title_with_metadata = (
                    f"{submission.title} "
                    f"[{submission.score}⬆ {submission.num_comments}💬 "
                    f"by u/{submission.author.name if submission.author else '[deleted]'}]"
                )
                
                chats.append(Chat(
                    id=submission.id, 
                    title=title_with_metadata,
                    type="post"
                ))
        except asyncprawcore.exceptions.ResponseException as e:
            if e.response.status_code == 400:
                print(f"Reddit session invalid for user {user_identifier}: {e}")
                await self.logout(user_identifier)
                raise ValueError("Reddit session expired or invalid. Please log in again.")
            raise e
        
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

        try:
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

            image_fetcher = ImageFetcher(
                image_processing_settings, 
                self.max_concurrent_image_downloads,
                user_agent=self.reddit_config.get("user_agent", "ChatAnalyzer/1.0")
            )
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
            
        except asyncprawcore.exceptions.ResponseException as e:
            if e.response.status_code == 400:
                print(f"Reddit session invalid for user {user_identifier}: {e}")
                await self.logout(user_identifier)
                raise ValueError("Reddit session expired or invalid. Please log in again.")
            raise e

    async def is_session_valid(self, user_identifier: str) -> bool:
        """
        Checks if the current session for the user is still active and authorized.
        """
        return self.session_manager.get_token(user_identifier) is not None
