import { appState, config } from './state.js';
import { makeApiRequest } from './api.js';
import {
    chatLoadingError, lastUpdatedTime, refreshChatsLink, modelError, modelSelect,
    updateStartChatButtonState, getChoicesInstance, setLoadingState, chatWindow,
    sendChatButton, downloadChatButton, downloadFormat, maxImageSize, imageProcessingToggle,
    cacheChatsToggle, formatDate
} from './ui.js';
import { handleFullLogout } from './auth.js';
import { initializeRedditPostChoices, getPostChoicesInstance, handleRedditChatSelection } from './reddit.js';

export async function handleLoadChats() {
    const backend = appState.activeBackend;
    const choicesInstance = getChoicesInstance();
    const chatSelect = document.getElementById('chatSelect');
    
    // Remove previous listener to avoid duplicates
    const redditListener = appState.redditListener;
    if (redditListener) {
        chatSelect.removeEventListener('change', redditListener);
    }

    if (backend === 'reddit') {
        initializeRedditPostChoices();
        const newRedditListener = handleRedditChatSelection;
        chatSelect.addEventListener('change', newRedditListener);
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
    const cachedChatsJSON = sessionStorage.getItem(cacheKey);

    const populateChoices = (chats, source = 'new') => {
        choicesInstance.clearStore();
        if (chats && chats.length > 0) {
            if (appState.activeBackend === 'reddit') {
                const groupedChats = {
                    'Subscribed': [],
                    'Popular': [],
                    'My Posts': []
                };
                chats.forEach(chat => {
                    if (chat.title.startsWith('Subreddit:')) {
                        groupedChats['Subscribed'].push({ value: chat.id, label: chat.title.replace('Subreddit: ', '') });
                    } else if (chat.title.startsWith('Popular:')) {
                        groupedChats['Popular'].push({ value: chat.id, label: chat.title.replace('Popular: ', '') });
                    } else if (chat.title.startsWith('My Post:')) {
                        groupedChats['My Posts'].push({ value: chat.id, label: chat.title.replace('My Post: ', '') });
                    }
                });

                const choices = Object.keys(groupedChats).map(group => {
                    return {
                        label: group,
                        choices: groupedChats[group]
                    };
                });
                choicesInstance.setChoices(choices, 'value', 'label', false);

            } else {
                const chatOptions = chats.map(chat => ({
                    value: chat.id,
                    label: `${chat.title} (${chat.type})`
                }));
                choicesInstance.setChoices(chatOptions, 'value', 'label', false);
            }
        } else {
            const label = source === 'cached' ? 'No chats found (cached)' : 'No chats found';
            choicesInstance.setChoices([{ value: '', label: label, disabled: true }], 'value', 'label', true);
        }
        choicesInstance.enable();
    };

    if (cachedChatsJSON) {
        const cachedChats = JSON.parse(cachedChatsJSON);
        populateChoices(cachedChats, 'cached');
        appState.chatListStatus[backend] = 'loaded';
        if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: (cached)`;
        updateStartChatButtonState();
        return;
    }

    appState.chatListStatus[backend] = 'loading';
    choicesInstance.disable();
    choicesInstance.clearStore();
    choicesInstance.setChoices([{ value: '', label: 'Refreshing...', disabled: true }], 'value', 'label', true);
    updateStartChatButtonState();

    try {
        const url = `/api/chats?backend=${backend}`;
        const data = await makeApiRequest(url, { method: 'GET' }, config.timeouts.loadChats, refreshChatsLink, 'Refreshing...', 'chats');
        
        const chats = Array.isArray(data) ? data : (data.chats || []);
        sessionStorage.setItem(cacheKey, JSON.stringify(chats));
        
        populateChoices(chats, 'new');
        if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        appState.chatListStatus[backend] = 'loaded';

    } catch(error) {
        if (chatLoadingError) chatLoadingError.textContent = error.message || 'Failed to load chats.';
        choicesInstance.setChoices([{ value: '', label: 'Failed to load. Click "Refresh List".', disabled: true }], 'value', 'label', true);
        choicesInstance.enable();
        appState.chatListStatus[backend] = 'unloaded';
    } finally {
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
    chatWindow.scrollTop = chatWindow.scrollHeight;

    setLoadingState(sendChatButton, true);
    appState.chatRequestController = new AbortController();
    let fullResponseText = '';

    try {
        const selectedModel = modelSelect.value;
        if (!selectedModel || !selectedModel.includes('_PROVIDER_SEPARATOR_')) {
            throw new Error("Invalid model selection.");
        }
        const [provider, modelName] = selectedModel.split('_PROVIDER_SEPARATOR_');

        const datePicker = document.getElementById('dateRangePicker')._flatpickr;
        const requestBody = {
            chatId: chatId,
            provider: provider,
            modelName: modelName,
            startDate: datePicker.selectedDates[0] ? formatDate(datePicker.selectedDates[0]) : null,
            endDate: datePicker.selectedDates[1] ? formatDate(datePicker.selectedDates[1]) : null,
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
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }
                
            }
        }
        
        if (fullResponseText) {
            appState.conversation.push({ role: 'model', content: fullResponseText });
            
            // Add the regenerate button now that the stream is complete
            const regenerateButton = document.createElement('button');
            regenerateButton.classList.add('regenerate-button');
            regenerateButton.textContent = 'Regenerate';
            regenerateButton.addEventListener('click', () => regenerateLastMessage());
            aiMessageElem.appendChild(regenerateButton);

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
        const requestBody = {
            chatId: appState.currentChatId || getChoicesInstance().getValue(true),
            startDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[0]),
            endDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[1]),
            enableCaching: cacheChatsToggle.checked,
            format: downloadFormat.value,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            // Ensure downloads include images by default with sane caps
            imageProcessing: {
                enabled: true,
                max_size_bytes: parseInt(maxImageSize.value || "5") * 1024 * 1024,
                // let backend defaults handle allowed types; send empty to not restrict unless user configured
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
    // Remove the last AI message from the chat window
    const lastAiMessage = chatWindow.querySelector('.chat-message.ai-message:last-child');
    if (lastAiMessage) {
        lastAiMessage.remove();
    }
    
    // Remove the last AI message from the conversation array
    if (appState.conversation.length > 0 && appState.conversation[appState.conversation.length - 1].role === 'model') {
        appState.conversation.pop();
    }
    
    // Find the last user message
    let lastUserMessage = null;
    for (let i = appState.conversation.length - 1; i >= 0; i--) {
        if (appState.conversation[i].role === 'user') {
            lastUserMessage = appState.conversation[i].content;
            break;
        }
    }
    
    // Call the chat API with the last user message
    if (lastUserMessage) {
        await callChatApi(lastUserMessage, appState.currentChatId);
    }
}
