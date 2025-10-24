import { appState, config } from './state.js';
import { makeApiRequest } from './api.js';
import { updateStartChatButtonState } from './ui.js';
import { createChoices } from './choicesWrapper.js';

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
    
    // Use wrapper methods for cleaner code
    postChoicesInstance.showLoadingText('Loading posts...');

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
            postChoicesInstance.showEmptyText('No posts found.');
        }
    } catch (error) {
        const errorElement = document.getElementById('redditPostError');
        if (errorElement) {
            errorElement.textContent = 'Failed to load posts.';
        }
        postChoicesInstance.showErrorText('Failed to load. Try again.');
    } finally {
        updateStartChatButtonState();
    }
}

export function initializeRedditPostChoices() {
    const postSelect = document.getElementById('redditPostSelect');
    if (postSelect && !postChoicesInstance) {
        // Use ChoicesWrapper for automatic Android compatibility
        postChoicesInstance = createChoices(postSelect, {
            itemSelectText: 'Select',
        });
        
        // Register onChange handler (automatically handles all events for Android)
        postChoicesInstance.onChange(updateStartChatButtonState);
    }
    
    // Note: subredditSelect event listeners are now managed by eventManager in main.js
}

export function getPostChoicesInstance() {
    return postChoicesInstance;
}
