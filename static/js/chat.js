import { appState, config } from './state.js';
import { makeApiRequest } from './api.js';
import {
    chatLoadingError, lastUpdatedTime, refreshChatsLink, modelError, modelSelect,
    updateStartChatButtonState, getChoicesInstance, getFlatpickrInstance, setLoadingState, chatWindow,
    sendChatButton, downloadChatButton, downloadFormat, maxImageSize, imageProcessingToggle,
    cacheChatsToggle, formatDate
} from './ui.js';
import { handleFullLogout } from './auth.js';
import { initializeRedditPostChoices, getPostChoicesInstance, handleRedditChatSelection } from './reddit.js';

/**
 * Smart auto-scroll: Only scrolls to bottom if user is already near the bottom
 * This prevents interrupting users who are reading earlier messages during streaming
 */
function smartAutoScroll() {
    if (!chatWindow) return;
    
    const threshold = 150; // pixels from bottom to consider "at bottom"
    const distanceFromBottom = chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight;
    
    // Only auto-scroll if user is already near the bottom
    if (distanceFromBottom < threshold) {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
}

/**
 * Initialize scroll-to-bottom button functionality
 */
export function initializeScrollToBottom() {
    const scrollToBottomButton = document.getElementById('scrollToBottomButton');
    if (!scrollToBottomButton || !chatWindow) return;
    
    const threshold = 150; // Same threshold as smartAutoScroll
    
    // Show/hide button based on scroll position
    function updateScrollButton() {
        const distanceFromBottom = chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight;
        
        if (distanceFromBottom > threshold) {
            scrollToBottomButton.style.display = 'flex';
        } else {
            scrollToBottomButton.style.display = 'none';
        }
    }
    
    // Listen to scroll events
    chatWindow.addEventListener('scroll', updateScrollButton);
    
    // Handle button click
    scrollToBottomButton.addEventListener('click', () => {
        chatWindow.scrollTo({
            top: chatWindow.scrollHeight,
            behavior: 'smooth'
        });
    });
}

export async function handleLoadChats(loadMore = false) {
    const backend = appState.activeBackend;
    const choicesInstance = getChoicesInstance();
    const chatSelect = document.getElementById('chatSelect');
    const loadMoreButton = document.getElementById('loadMoreChatsButton');
    
    // Remove previous listener to avoid duplicates
    const redditListener = appState.redditListener;
    if (redditListener) {
        chatSelect.removeEventListener('addItem', redditListener);
    }

    if (backend === 'reddit') {
        initializeRedditPostChoices();
        const newRedditListener = handleRedditChatSelection;
        // Use Choices.js-specific event for Android compatibility
        chatSelect.addEventListener('addItem', newRedditListener);
        appState.redditListener = newRedditListener;
    } else {
        const redditPostSelectGroup = document.getElementById('redditPostSelectGroup');
        if (redditPostSelectGroup) {
            redditPostSelectGroup.style.display = 'none';
        }
    }
    if (!backend || !choicesInstance || !appState.sessionTokens[backend]) {
        if (chatLoadingError) chatLoadingError.textContent = "No active session.";
        return;
    }

    const cacheKey = `${backend}-chats`;
    const cursorKey = `${backend}-chats-cursor`;

    // Helper to populate choices (append or replace)
    const populateChoices = (chats, append = false, source = 'new') => {
        if (!append) {
            choicesInstance.clearStore();
        }
        
        if (chats && chats.length > 0) {
            if (appState.activeBackend === 'reddit') {
                // Group Reddit chats by category
                const groupedChats = {
                    'Favorites': [],
                    'Subscribed': [],
                    'Popular': [],
                    'My Posts': []
                };
                
                chats.forEach(chat => {
                    if (chat.title.startsWith('⭐ Subreddit:')) {
                        groupedChats['Favorites'].push({ 
                            value: chat.id, 
                            label: chat.title.replace('⭐ Subreddit: ', '⭐ ') 
                        });
                    } else if (chat.title.startsWith('Subreddit:')) {
                        groupedChats['Subscribed'].push({ 
                            value: chat.id, 
                            label: chat.title.replace('Subreddit: ', '') 
                        });
                    } else if (chat.title.startsWith('Popular:')) {
                        groupedChats['Popular'].push({ 
                            value: chat.id, 
                            label: chat.title.replace('Popular: ', '') 
                        });
                    } else if (chat.title.startsWith('My Post:')) {
                        groupedChats['My Posts'].push({ 
                            value: chat.id, 
                            label: chat.title.replace('My Post: ', '') 
                        });
                    }
                });

                // Use wrapper's grouped choices method
                choicesInstance.setGroupedChoices(groupedChats);
            } else {
                // Telegram or Webex
                const chatOptions = chats.map(chat => ({
                    value: chat.id,
                    label: `${chat.title} (${chat.type})`
                }));
                choicesInstance.setChoices(chatOptions, 'value', 'label', append);
            }
        } else if (!append) {
            // Use wrapper's empty state method
            const label = source === 'cached' ? 'No chats found (cached)' : 'No chats found';
            choicesInstance.showEmptyText(label);
        }
        
        choicesInstance.enable();
    };

    // Helper to update "Load More" button visibility
    const updateLoadMoreButton = (nextCursor) => {
        if (loadMoreButton) {
            if (nextCursor && backend === 'webex') {
                loadMoreButton.style.display = 'inline-block';
                loadMoreButton.disabled = false;
            } else {
                loadMoreButton.style.display = 'none';
            }
        }
    };

    // If not loading more, check session cache first
    if (!loadMore) {
        const cachedChatsJSON = sessionStorage.getItem(cacheKey);
        if (cachedChatsJSON) {
            const cachedData = JSON.parse(cachedChatsJSON);
            const chats = Array.isArray(cachedData) ? cachedData : (cachedData.chats || cachedData);
            const cachedCursor = sessionStorage.getItem(cursorKey);
            
            populateChoices(chats, false, 'cached');
            updateLoadMoreButton(cachedCursor);
            appState.chatListStatus[backend] = 'loaded';
            if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: (cached)`;
            updateStartChatButtonState();
            return;
        }
    }

    appState.chatListStatus[backend] = 'loading';
    
    if (!loadMore) {
        choicesInstance.disable();
        choicesInstance.showLoadingText('Refreshing...');
    }
    
    if (loadMoreButton && loadMore) {
        loadMoreButton.disabled = true;
        loadMoreButton.textContent = 'Loading...';
    }
    
    updateStartChatButtonState();

    try {
        // Build URL with pagination params
        const cursor = loadMore ? sessionStorage.getItem(cursorKey) : null;
        let url = `/api/chats?backend=${backend}&limit=50`;
        if (cursor) {
            url += `&cursor=${encodeURIComponent(cursor)}`;
        }
        
        const data = await makeApiRequest(url, { method: 'GET' }, config.timeouts.loadChats, loadMore ? null : refreshChatsLink, 'Refreshing...', 'chats');
        
        const chats = data.chats || [];
        const nextCursor = data.next_cursor;
        
        // Update cache
        if (loadMore && backend === 'webex') {
            // Append to existing cached chats
            const existingJSON = sessionStorage.getItem(cacheKey);
            const existingChats = existingJSON ? (JSON.parse(existingJSON).chats || JSON.parse(existingJSON)) : [];
            const allChats = [...existingChats, ...chats];
            sessionStorage.setItem(cacheKey, JSON.stringify({ chats: allChats }));
        } else {
            sessionStorage.setItem(cacheKey, JSON.stringify({ chats }));
        }
        
        // Store cursor for next pagination request
        if (nextCursor) {
            sessionStorage.setItem(cursorKey, nextCursor);
        } else {
            sessionStorage.removeItem(cursorKey);
        }
        
        populateChoices(chats, loadMore, 'new');
        updateLoadMoreButton(nextCursor);
        
        if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        appState.chatListStatus[backend] = 'loaded';

    } catch(error) {
        if (chatLoadingError) chatLoadingError.textContent = error.message || 'Failed to load chats.';
        if (!loadMore) {
            choicesInstance.showErrorText('Failed to load. Click "Refresh List".');
        }
        appState.chatListStatus[backend] = 'unloaded';
    } finally {
        if (loadMoreButton) {
            loadMoreButton.textContent = 'Load More';
            // Only re-enable if there's still a cursor
            if (sessionStorage.getItem(cursorKey)) {
                loadMoreButton.disabled = false;
            }
        }
        updateStartChatButtonState();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // This logic is now handled by the main start chat button
});

export async function loadModels() {
    appState.modelsLoaded = false;
    updateStartChatButtonState();
    if (modelError) modelError.textContent = '';
    if (modelSelect) {
        modelSelect.innerHTML = '<option value="" disabled selected>Loading models...</option>';
        modelSelect.disabled = true;
    }
    try {
        const data = await makeApiRequest('/api/models', { method: 'GET' }, config.timeouts.loadModels, null, 'login');
        if (modelSelect) modelSelect.innerHTML = '';

        const modelsByProvider = data.models.reduce((acc, { provider, model }) => {
            if (!acc[provider]) {
                acc[provider] = [];
            }
            acc[provider].push(model);
            return acc;
        }, {});

        for (const provider in modelsByProvider) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = provider.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            
            modelsByProvider[provider].forEach(modelName => {
                const option = document.createElement('option');
                // Use a unique separator to avoid conflicts with model names
                option.value = `${provider}_PROVIDER_SEPARATOR_${modelName}`;
                option.textContent = modelName;
                optgroup.appendChild(option);
            });
            modelSelect.appendChild(optgroup);
        }

        if (modelSelect && modelSelect.options.length > 0) {
            modelSelect.disabled = false;
            appState.modelsLoaded = true;
            const defaultModelInfo = data.default_model_info;
            if (defaultModelInfo && defaultModelInfo.provider && defaultModelInfo.model) {
                const defaultValue = `${defaultModelInfo.provider}_PROVIDER_SEPARATOR_${defaultModelInfo.model}`;
                if (modelSelect.querySelector(`option[value="${defaultValue}"]`)) {
                    modelSelect.value = defaultValue;
                }
            }
        } else {
            if (modelError) modelError.textContent = 'No AI models available.';
        }
    } catch (error) {
        if (modelError) modelError.textContent = 'Failed to load AI models.';
    } finally {
        updateStartChatButtonState();
    }
}

export async function callChatApi(message = null, chatId = null) {
    if (appState.chatRequestController) {
        appState.chatRequestController.abort();
        return;
    }
    
    if (chatId) {
        appState.currentChatId = chatId;
    }

    if (!appState.sessionTokens[appState.activeBackend]) {
        alert("Session expired. Please log in again.");
        handleFullLogout();
        return;
    }

    const lastAiMessage = chatWindow.querySelector('.chat-message.ai-message:last-child');
    if (lastAiMessage) {
        const existingButton = lastAiMessage.querySelector('.regenerate-button');
        if (existingButton) {
            existingButton.remove();
        }
    }


    const aiMessageElem = document.createElement('div');
    aiMessageElem.classList.add('chat-message', 'ai-message');

    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');
    messageContent.innerHTML = '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>';
    aiMessageElem.appendChild(messageContent);
    
    chatWindow.appendChild(aiMessageElem);
    smartAutoScroll(); // Only scroll if user is at bottom

    setLoadingState(sendChatButton, true);
    appState.chatRequestController = new AbortController();
    let fullResponseText = '';

    try {
        const selectedModel = modelSelect.value;
        if (!selectedModel || !selectedModel.includes('_PROVIDER_SEPARATOR_')) {
            throw new Error("Invalid model selection.");
        }
        const [provider, modelName] = selectedModel.split('_PROVIDER_SEPARATOR_');

        const datePicker = getFlatpickrInstance();
        const requestBody = {
            chatId: chatId,
            provider: provider,
            modelName: modelName,
            startDate: datePicker && datePicker.selectedDates[0] ? formatDate(datePicker.selectedDates[0]) : null,
            endDate: datePicker && datePicker.selectedDates[1] ? formatDate(datePicker.selectedDates[1]) : null,
            enableCaching: cacheChatsToggle.checked,
            conversation: appState.conversation,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            imageProcessing: {
                enabled: imageProcessingToggle.checked,
                max_size_bytes: parseInt(maxImageSize.value) * 1024 * 1024,
            }
        };
        
        if (message) {
            requestBody.message = message;
        }

        const url = `/api/chat?backend=${appState.activeBackend}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${appState.sessionTokens[appState.activeBackend]}`
            },
            body: JSON.stringify(requestBody),
            signal: appState.chatRequestController.signal
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Request failed: ${errorText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        messageContent.innerHTML = '';

        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    if (data.type === 'status') {
                        messageContent.innerHTML = `<p><em>${data.message}</em></p>`;
                    } else if (data.type === 'content') {
                        fullResponseText += data.chunk;
                        messageContent.innerHTML = marked.parse(fullResponseText, { breaks: true, gfm: true });
                    } else if (data.type === 'error') {
                        fullResponseText = `<p style="color: red;"><strong>Error:</strong> ${data.message}</p>`;
                        messageContent.innerHTML = fullResponseText;
                        break;
                    }
                    smartAutoScroll(); // Only scroll if user is at bottom
                }
                
            }
        }
        
        if (fullResponseText) {
            appState.conversation.push({ role: 'model', content: fullResponseText });
            aiMessageElem.dataset.markdown = fullResponseText;
            
            // Add the regenerate button now that the stream is complete
            const regenerateButton = document.createElement('button');
            regenerateButton.classList.add('regenerate-button');
            regenerateButton.textContent = 'Regenerate';
            regenerateButton.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                await regenerateLastMessage();
            });
            aiMessageElem.appendChild(regenerateButton);

            const copyButton = document.createElement('button');
            copyButton.classList.add('copy-button');
            copyButton.textContent = 'Copy';
            copyButton.addEventListener('click', (e) => {
                const messageElement = e.target.closest('.ai-message');
                const markdownText = messageElement.dataset.markdown;
                navigator.clipboard.writeText(markdownText).then(() => {
                    copyButton.textContent = 'Copied!';
                    setTimeout(() => {
                        copyButton.textContent = 'Copy';
                    }, 2000);
                });
            });
            aiMessageElem.appendChild(copyButton);
        }

    } catch (error) {
        if (error.name !== 'AbortError') {
            aiMessageElem.querySelector('.message-content').innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
        } else {
            if (aiMessageElem.querySelector('.message-content').innerHTML.trim() === '') {
                 aiMessageElem.remove();
            }
        }
    } finally {
        setLoadingState(sendChatButton, false);
        appState.chatRequestController = null;
    }
}

export async function handleDownloadChat() {
    if (!appState.sessionTokens[appState.activeBackend]) {
        alert("Session expired. Please log in again.");
        handleFullLogout();
        return;
    }

    setLoadingState(downloadChatButton, true, 'Downloading...');
    try {
        const datePicker = getFlatpickrInstance();
        const requestBody = {
            chatId: appState.currentChatId || getChoicesInstance().getValue(true),
            startDate: datePicker && datePicker.selectedDates[0] ? formatDate(datePicker.selectedDates[0]) : null,
            endDate: datePicker && datePicker.selectedDates[1] ? formatDate(datePicker.selectedDates[1]) : null,
            enableCaching: cacheChatsToggle.checked,
            format: downloadFormat.value,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            imageProcessing: {
                enabled: imageProcessingToggle.checked,
                max_size_bytes: parseInt(maxImageSize.value || "5") * 1024 * 1024,
            }
        };

        const response = await fetch(`/api/download?backend=${appState.activeBackend}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${appState.sessionTokens[appState.activeBackend]}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Download failed: ${errorText}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'chat.txt'; // default
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch.length > 1) {
                filename = filenameMatch[1];
            }
        }
        
        a.setAttribute('download', filename);
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (error) {
        alert(error.message);
    } finally {
        setLoadingState(downloadChatButton, false);
    }
}

export async function regenerateLastMessage() {
    try {
        console.log('Regenerating last message...');
        console.log('Current conversation state:', appState.conversation);
        console.log('Current chat ID:', appState.currentChatId);
        
        // Validate we have an active chat session
        if (!appState.currentChatId) {
            alert('No active chat session. Please start a new chat.');
            return;
        }
        
        // First, find the last user message BEFORE removing anything
        let lastUserMessage = null;
        for (let i = appState.conversation.length - 1; i >= 0; i--) {
            if (appState.conversation[i].role === 'user') {
                lastUserMessage = appState.conversation[i].content;
                break;
            }
        }
        
        console.log('Last user message found:', lastUserMessage);
        
        // If no user message found, this might be the initial automatic summary
        // In this case, we can regenerate by calling the API with no message (gets a fresh summary)
        const isInitialSummary = !lastUserMessage && appState.conversation.length > 0;
        
        if (!lastUserMessage && !isInitialSummary) {
            alert('No message to regenerate. The conversation appears to be empty.');
            return;
        }
        
        // Remove the last AI message from the chat window
        const lastAiMessage = chatWindow.querySelector('.chat-message.ai-message:last-child');
        if (lastAiMessage) {
            lastAiMessage.remove();
        }
        
        // Remove the last AI message from the conversation array
        if (appState.conversation.length > 0 && appState.conversation[appState.conversation.length - 1].role === 'model') {
            appState.conversation.pop();
        }
        
        // Call the chat API
        // If there's a user message, regenerate that response
        // If this is an initial summary (no user message), call without message parameter to get a fresh summary
        if (isInitialSummary) {
            console.log('Regenerating initial summary...');
            await callChatApi(null, appState.currentChatId);
        } else {
            console.log('Regenerating response to user message:', lastUserMessage);
            await callChatApi(lastUserMessage, appState.currentChatId);
        }
        
    } catch (error) {
        console.error('Error in regenerateLastMessage:', error);
        alert(`Failed to regenerate message: ${error.message}`);
    }
}
