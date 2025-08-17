import { appState, config } from './state.js';
import { makeApiRequest } from './api.js';
import { updateStartChatButtonState } from './ui.js';

let postChoicesInstance = null;

export async function handleRedditChatSelection(event) {
    const redditPostSelectGroup = document.getElementById('redditPostSelectGroup');
    const redditUrlGroup = document.getElementById('redditUrlGroup');
    if (appState.activeBackend !== 'reddit') {
        if (redditPostSelectGroup) redditPostSelectGroup.style.display = 'none';
        if (redditUrlGroup) redditUrlGroup.style.display = 'none';
        return;
    }

    if (!event.detail.value.startsWith('sub_')) {
        if (redditPostSelectGroup) redditPostSelectGroup.style.display = 'none';
        return;
    }

    const subreddit = event.detail.value.replace('sub_', '');
    redditPostSelectGroup.style.display = 'block';
    postChoicesInstance.clearStore();
    postChoicesInstance.setChoices([{ value: '', label: 'Loading posts...', disabled: true }], 'value', 'label', true);

    try {
        const url = `/api/reddit/posts?subreddit=${subreddit}`;
        const posts = await makeApiRequest(url, { method: 'GET' }, config.timeouts.loadChats, null, 'chats');
        if (posts && posts.length > 0) {
            const postOptions = posts.map(post => ({
                value: post.id,
                label: post.title
            }));
            postChoicesInstance.setChoices(postOptions, 'value', 'label', false);
        } else {
            postChoicesInstance.setChoices([{ value: '', label: 'No posts found.', disabled: true }], 'value', 'label', true);
        }
    } catch (error) {
        document.getElementById('redditPostError').textContent = 'Failed to load posts.';
    } finally {
        updateStartChatButtonState();
    }
}

export function initializeRedditPostChoices() {
    const postSelect = document.getElementById('redditPostSelect');
    if (postSelect && !postChoicesInstance) {
        postChoicesInstance = new Choices(postSelect, {
            searchEnabled: true,
            itemSelectText: 'Select',
            shouldSort: false,
        });
        // Add event listener to update button state when a post is selected
        postSelect.addEventListener('change', updateStartChatButtonState);
    }
    const subredditSelect = document.getElementById('chatSelect');
    if (subredditSelect) {
        subredditSelect.addEventListener('change', updateStartChatButtonState);
    }
}

export function getPostChoicesInstance() {
    return postChoicesInstance;
}
