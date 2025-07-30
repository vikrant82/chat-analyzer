// --- Global State & Configuration ---
const appState = {
    isProcessing: {
        login: false,
        chats: false,
        analysis: false,
        session: false,
    },
    chatLoadController: null,
    activeBackend: null, // 'telegram' or 'webex'
    sessionTokens: { telegram: null, webex: null }, // The single source of truth for auth
    activeSection: 'login',
    modelsLoaded: false,
    chatListStatus: { telegram: 'unloaded', webex: 'unloaded' },
    conversation: [], // Holds the current chat history {role, content}
};
const CACHE_CHATS_KEY = 'chat_analyzer_cache_chats_enabled';

// Namespaced Local Storage Keys
const ACTIVE_BACKEND_KEY = 'chat_analyzer_active_backend';
const getSessionTokenKey = (backend) => `chat_analyzer_${backend}_session_token`;

const config = {
    timeouts: {
        verify: 180000, summary: 180000, loadChats: 30000,
        logout: 15000, login: 30000, loadModels: 20000,
    }
};


// --- DOM Elements ---
const loginSection = document.getElementById('loginSection');
const verificationSection = document.getElementById('verificationSection');
const chatSection = document.getElementById('chatSection');
const backendSelect = document.getElementById('backendSelect');
const telegramLoginForm = document.getElementById('telegramLoginForm');
const webexLoginContainer = document.getElementById('webexLoginContainer');
const webexLoginButton = document.getElementById('webexLoginButton');
const phoneInput = document.getElementById('phone');
const loginSubmitButton = document.getElementById('loginSubmitButton');
const loginError = document.getElementById('loginError');
const verificationCodeInput = document.getElementById('verificationCode');
const passwordField = document.getElementById('passwordField');
const passwordInput = document.getElementById('password');
const verifyButton = document.getElementById('verifyButton');
const verificationError = document.getElementById('verificationError');
const chatSelect = document.getElementById('chatSelect');
const modelSelect = document.getElementById('modelSelect');
const modelError = document.getElementById('modelError');
const dateError = document.getElementById('dateError');
const chatLoadingError = document.getElementById('chatLoadingError');
const refreshChatsLink = document.getElementById('refreshChatsLink');
const lastUpdatedTime = document.getElementById('lastUpdatedTime');
const logoutButton = document.getElementById('logoutButton');
const cacheChatsToggle = document.getElementById('cacheChatsToggle');
const chatSectionTitle = document.getElementById('chatSectionTitle');
const backendSelectMain = document.getElementById('backendSelect-main');
const conversationalChatSection = document.getElementById('conversationalChatSection');
const chatWindow = document.getElementById('chatWindow');
const chatInput = document.getElementById('chatInput');
const sendChatButton = document.getElementById('sendChatButton');
const clearChatButton = document.getElementById('clearChatButton');
const startChatButton = document.getElementById('startChatButton');
const initialQuestion = document.getElementById('initialQuestion');
const initialQuestionGroup = document.getElementById('initialQuestionGroup');
const toggleQuestionCheckbox = document.getElementById('toggleQuestionCheckbox');
const downloadChatButton = document.getElementById('downloadChatButton');
const downloadFormat = document.getElementById('downloadFormat');
const botManagementSection = document.getElementById('botManagementSection');
const manageBotsButton = document.getElementById('manageBotsButton');
const backToChatsButton = document.getElementById('backToChatsButton');
const botManagementTitle = document.getElementById('botManagementTitle');
const botNameInput = document.getElementById('botName');
const botIdInput = document.getElementById('botId');
const botTokenInput = document.getElementById('botToken');
const webhookUrlInput = document.getElementById('webhookUrl');
const registerBotButton = document.getElementById('registerBotButton');
const botManagementError = document.getElementById('botManagementError');
const registeredBotsList = document.getElementById('registeredBotsList');
const welcomeMessage = document.getElementById('welcomeMessage');
const toggleLhsButton = document.getElementById('toggleLhsButton');
const mainContainer = document.querySelector('.main-container');
const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
const themeCheckbox = document.getElementById('theme-checkbox');
const imageSettings = document.getElementById('imageSettings');
const imageProcessingToggle = document.getElementById('imageProcessingToggle');
const maxImageSize = document.getElementById('maxImageSize');

// --- Utility Functions ---
function formatDate(date) {
    if (!date) return null;
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function setLoadingState(buttonElement, isLoading, loadingText = 'Processing...') {
    if (!buttonElement) return;
    if (isLoading) {
        buttonElement.dataset.originalText = buttonElement.textContent;
        buttonElement.textContent = loadingText;
        buttonElement.disabled = true;
    } else {
        if (buttonElement.dataset.originalText) {
            buttonElement.textContent = buttonElement.dataset.originalText;
        }
        buttonElement.disabled = false;
        delete buttonElement.dataset.originalText;
    }
}

function clearErrors() {
    if (loginError) loginError.textContent = '';
    if (verificationError) verificationError.textContent = '';
    if (dateError) dateError.textContent = '';
    if (chatLoadingError) chatLoadingError.textContent = '';
    if (modelError) modelError.textContent = '';
    if (botManagementError) botManagementError.textContent = '';
}

let choicesInstance = null;

function updateStartChatButtonState() {
    if (!startChatButton) return;
    const validChatSelected = choicesInstance && choicesInstance.getValue(true) != null && choicesInstance.getValue(true) !== "";
    const validModelSelected = modelSelect && modelSelect.value && !modelSelect.options[modelSelect.selectedIndex]?.disabled;
    const baseRequirementsMet = appState.chatListStatus[appState.activeBackend] === 'loaded' && appState.modelsLoaded && validChatSelected && validModelSelected;
    startChatButton.disabled = !baseRequirementsMet;
    if (downloadChatButton) {
        downloadChatButton.disabled = !validChatSelected;
    }
    if (initialQuestion) {
        initialQuestion.disabled = !baseRequirementsMet;
    }
}

function initializeFlatpickr() {
    const dateRangePicker = document.getElementById('dateRangePicker');
    flatpickr(dateRangePicker, {
        mode: "range",
        dateFormat: "Y-m-d",
        defaultDate: ["today", "today"],
        onChange: function(selectedDates, dateStr, instance) {
            updateStartChatButtonState();
        }
    });
}

async function makeApiRequest(url, options, timeoutDuration, elementToLoad = null, loadingText = 'Processing...', operationType = 'login') {
    if (appState.isProcessing[operationType]) {
        throw new Error('Operation already in progress.');
    }
    appState.isProcessing[operationType] = true;
    if (elementToLoad) setLoadingState(elementToLoad, true, loadingText);

    const token = appState.sessionTokens[appState.activeBackend];
    if (token) {
        if (!options.headers) {
            options.headers = {};
        }
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    if (operationType === 'chats') {
        appState.chatLoadController = controller;
    }
    const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);
    options.signal = controller.signal;

    try {
        const response = await fetch(url, options);
        clearTimeout(timeoutId);
        if (!response.ok) {
            let errorDetail = `Request failed with status ${response.status}`;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || JSON.stringify(errorData);
            } catch (e) {
                errorDetail = response.statusText || errorDetail;
            }
            throw new Error(`API Error (${response.status}): ${errorDetail}`);
        }
        const contentType = response.headers.get("content-type");
        if (response.status === 204 || !contentType || !contentType.includes("application/json")) {
            return {};
        }
        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error(`Request timed out.`);
        }
        throw error;
    } finally {
        appState.isProcessing[operationType] = false;
        if (elementToLoad) setLoadingState(elementToLoad, false);
    }
}


// --- Core Application Logic ---

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
    });

    const sectionToShow = document.getElementById(sectionName);
    if (sectionToShow) {
        sectionToShow.classList.add('active');
    }
    
    appState.activeSection = sectionName;
    clearErrors();

    if (sectionName === 'chatSection') {
        if (!appState.activeBackend) {
            showSection('loginSection');
            return;
        }
        if (chatSectionTitle) {
            chatSectionTitle.textContent = `Analyze Chats (${appState.activeBackend.charAt(0).toUpperCase() + appState.activeBackend.slice(1)})`;
        }
        if (backendSelectMain) {
            backendSelectMain.value = appState.activeBackend;
        }
        handleBackendChange(); // Ensure UI elements like image settings are correctly shown/hidden
        if (!appState.modelsLoaded) {
            loadModels();
        }
        if (appState.chatListStatus[appState.activeBackend] === 'unloaded') {
            handleLoadChats();
        }
    } else if (sectionName === 'botManagementSection') {
        if (!appState.activeBackend) {
            showSection('loginSection');
            return;
        }
        botManagementTitle.textContent = `Manage Bots (${appState.activeBackend.charAt(0).toUpperCase() + appState.activeBackend.slice(1)})`;
        // Show/hide botId field based on backend
        const botIdRow = document.getElementById('botIdRow');
        if (botIdRow) {
            botIdRow.style.display = appState.activeBackend === 'webex' ? '' : 'none';
        }
        loadBots();
    } else if (sectionName === 'loginSection') {
        if (backendSelect) {
            backendSelect.value = appState.activeBackend || 'telegram';
        }
        handleBackendChange();
    }
}

function handleBackendChange() {
    if (backendSelect && telegramLoginForm && webexLoginContainer) {
        const selectedBackend = backendSelect.value;
        telegramLoginForm.style.display = selectedBackend === 'telegram' ? 'block' : 'none';
        webexLoginContainer.style.display = selectedBackend === 'webex' ? 'block' : 'none';
    }
    // Also handle the main backend selector
    if(backendSelectMain) {
        const selectedBackend = backendSelectMain.value;
        imageSettings.style.display = selectedBackend === 'webex' ? 'block' : 'none';
    }
}

async function switchService(newBackend) {
    if (appState.activeBackend === newBackend) return;

    if (appState.chatLoadController) {
        appState.chatLoadController.abort();
    }

    appState.chatListStatus[newBackend] = 'unloaded';
    appState.activeBackend = newBackend;
    localStorage.setItem(ACTIVE_BACKEND_KEY, newBackend);
    
    appState.conversation = [];
    if (chatWindow) chatWindow.innerHTML = '';
    if (conversationalChatSection) conversationalChatSection.style.display = 'none';
    if (welcomeMessage) welcomeMessage.style.display = 'block';

    const token = localStorage.getItem(getSessionTokenKey(newBackend));
    if (token) {
        appState.sessionTokens[newBackend] = token;
        showSection('chatSection');
    } else {
        showSection('loginSection');
    }
}

async function handleLogin() {
    clearErrors();
    const selectedBackend = backendSelect.value;
    appState.activeBackend = selectedBackend;
    localStorage.setItem(ACTIVE_BACKEND_KEY, selectedBackend);

    const url = `/api/login?backend=${selectedBackend}`;
    
    if (selectedBackend === 'telegram') {
        const phoneVal = phoneInput.value.trim();
        if (!phoneVal) { 
            loginError.textContent = 'Phone number is required.';
            return; 
        }
        try {
            await makeApiRequest(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: phoneVal }) }, config.timeouts.login, loginSubmitButton, 'login');
            showSection('verificationSection');
        } catch (error) { 
            loginError.textContent = error.message || 'Login failed.';
        }
    } else {
        setLoadingState(webexLoginButton, true, 'Redirecting...');
        try {
            const data = await makeApiRequest(url, { method: 'POST' }, config.timeouts.login, webexLoginButton, 'login');
            if (data.url) {
                window.location.href = data.url;
            } else {
                loginError.textContent = 'Could not get login redirect URL.';
                setLoadingState(webexLoginButton, false);
            }
        } catch (error) {
            loginError.textContent = error.message || 'Login failed.';
            setLoadingState(webexLoginButton, false);
        }
    }
}

async function handleVerify() {
    const code = verificationCodeInput.value.trim();
    const password = passwordInput.value;
    const phone = phoneInput.value.trim();
    
    try {
        const data = await makeApiRequest(`/api/telegram/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone, code, password }) }, config.timeouts.verify, verifyButton, 'login');
        if (data.status === 'success' && data.token) {
            appState.sessionTokens.telegram = data.token;
            appState.activeBackend = 'telegram';
            localStorage.setItem(getSessionTokenKey('telegram'), data.token);
            localStorage.setItem(ACTIVE_BACKEND_KEY, 'telegram');
            showSection('chatSection');
        } else if (data.status === 'password_required') {
            passwordField.style.display = 'block';
            verificationError.textContent = 'Password required for 2FA.';
        }
    } catch (error) { 
        verificationError.textContent = error.message || 'Verification failed.';
    }
}

async function handleFullLogout() {
    const backend = appState.activeBackend;

    if (backend && appState.sessionTokens[backend]) {
        try {
            const url = `/api/logout?backend=${backend}`;
            await makeApiRequest(url, { method: 'POST' }, config.timeouts.logout, logoutButton, 'login');
        } catch (error) {
            console.error("Logout failed, proceeding with client-side cleanup:", error);
        }
    }
    
    if (backend) {
        localStorage.removeItem(getSessionTokenKey(backend));
        appState.sessionTokens[backend] = null;
        appState.chatListStatus[backend] = 'unloaded';
    }
    appState.conversation = [];

    const otherBackend = backend === 'telegram' ? 'webex' : 'telegram';
    if (localStorage.getItem(getSessionTokenKey(otherBackend))) {
        switchService(otherBackend);
    } else {
        localStorage.removeItem(ACTIVE_BACKEND_KEY);
        appState.activeBackend = null;
        showSection('loginSection');
    }
    
    if (choicesInstance) {
        choicesInstance.clearStore();
        choicesInstance.disable();
    }
}

async function handleLoadChats() {
    const backend = appState.activeBackend;
    if (!backend || !choicesInstance || !appState.sessionTokens[backend]) {
        if (chatLoadingError) chatLoadingError.textContent = "No active session.";
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
        
        choicesInstance.clearStore();
        if (data && data.length > 0) {
            const chatOptions = data.map(chat => ({
                value: chat.id,
                label: `${chat.title} (${chat.type})`
            }));
            choicesInstance.setChoices(chatOptions, 'value', 'label', false);
            choicesInstance.enable();
            if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        } else {
            choicesInstance.setChoices([{ value: '', label: 'No chats found', disabled: true }], 'value', 'label', true);
        }
        appState.chatListStatus[backend] = 'loaded';

    } catch(error) {
        if (chatLoadingError) chatLoadingError.textContent = error.message || 'Failed to load chats.';
        choicesInstance.setChoices([{ value: '', label: 'Failed to load. Click "Refresh List".', disabled: true }], 'value', 'label', true);
        appState.chatListStatus[backend] = 'unloaded';
    } finally {
        updateStartChatButtonState();
    }
}

async function loadModels() {
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

async function callChatApi(message = null) {
    if (!appState.sessionTokens[appState.activeBackend]) {
        alert("Session expired. Please log in again.");
        handleFullLogout();
        return;
    }
    const aiMessageElem = document.createElement('div');
    aiMessageElem.classList.add('chat-message', 'ai-message');
    aiMessageElem.innerHTML = '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>';
    chatWindow.appendChild(aiMessageElem);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    setLoadingState(sendChatButton, true, '...');
    
    let fullResponseText = '';
    try {
        const selectedModel = modelSelect.value;
        if (!selectedModel || !selectedModel.includes('_PROVIDER_SEPARATOR_')) {
            throw new Error("Invalid model selection.");
        }
        const [provider, modelName] = selectedModel.split('_PROVIDER_SEPARATOR_');

        const requestBody = {
            chatId: choicesInstance.getValue(true),
            provider: provider,
            modelName: modelName,
            startDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[0]),
            endDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[1]),
            enableCaching: cacheChatsToggle.checked,
            conversation: appState.conversation,
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
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Request failed: ${errorText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        aiMessageElem.innerHTML = ''; 

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
                        aiMessageElem.innerHTML = `<p><em>${data.message}</em></p>`;
                    } else if (data.type === 'content') {
                        fullResponseText += data.chunk;
                        aiMessageElem.innerHTML = marked.parse(fullResponseText, { breaks: true, gfm: true });
                    }
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }
            }
        }
        
        appState.conversation.push({ role: 'model', content: fullResponseText });

    } catch (error) {
        aiMessageElem.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
    } finally {
        setLoadingState(sendChatButton, false);
    }
}


async function checkSessionOnLoad() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const backend = params.get('backend');

    if (token && backend) {
        appState.sessionTokens[backend] = token;
        appState.activeBackend = backend;
        localStorage.setItem(getSessionTokenKey(backend), token);
        localStorage.setItem(ACTIVE_BACKEND_KEY, backend);
        window.history.replaceState({}, document.title, "/");
        showSection('chatSection');
        return;
    }
    
    appState.sessionTokens.telegram = localStorage.getItem(getSessionTokenKey('telegram'));
    appState.sessionTokens.webex = localStorage.getItem(getSessionTokenKey('webex'));
    const lastBackend = localStorage.getItem(ACTIVE_BACKEND_KEY);

    if (lastBackend && appState.sessionTokens[lastBackend]) {
        appState.activeBackend = lastBackend;
        try {
            await makeApiRequest(`/api/session-status?backend=${lastBackend}`, { method: 'GET' }, 10000, null, 'session');
            showSection('chatSection');
            return;
        } catch (error) {
            console.error(`Session check failed for ${lastBackend}:`, error);
            localStorage.removeItem(getSessionTokenKey(lastBackend));
            appState.sessionTokens[lastBackend] = null;
            const otherBackend = lastBackend === 'telegram' ? 'webex' : 'telegram';
            if (appState.sessionTokens[otherBackend]) {
                switchService(otherBackend);
                return;
            }
        }
    }

    showSection('loginSection');
}

async function handleDownloadChat() {
    if (!appState.sessionTokens[appState.activeBackend]) {
        alert("Session expired. Please log in again.");
        handleFullLogout();
        return;
    }

    setLoadingState(downloadChatButton, true, 'Downloading...');
    try {
        const requestBody = {
            chatId: choicesInstance.getValue(true),
            startDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[0]),
            endDate: formatDate(document.getElementById('dateRangePicker')._flatpickr.selectedDates[1]),
            enableCaching: cacheChatsToggle.checked,
            format: downloadFormat.value
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

document.addEventListener('DOMContentLoaded', () => {
    function closeMobileMenu() {
        if (mainContainer.classList.contains('mobile-menu-open')) {
            mainContainer.classList.remove('mobile-menu-open');
            toggleLhsButton.innerHTML = '&#9776;';
        }
    }

    if (startChatButton) {
        startChatButton.addEventListener('click', () => {
            closeMobileMenu();
            if (appState.conversation.length > 0) {
                if (!confirm("You have an ongoing conversation. Starting a new chat will clear the current conversation. Continue?")) {
                    return;
                }
                appState.conversation = [];
                chatWindow.innerHTML = '';
            }
            const question = initialQuestion.value.trim();
            if (question) {
                appState.conversation.push({ role: 'user', content: question });
                const userMessageElem = document.createElement('div');
                userMessageElem.classList.add('chat-message', 'user-message');
                userMessageElem.textContent = question;
                chatWindow.appendChild(userMessageElem);
                initialQuestion.value = '';
            }

            const chatColumn = document.getElementById('conversationalChatSection');
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }
            if (chatColumn) {
                chatColumn.style.display = 'flex';
                startChatButton.disabled = true;
                if (initialQuestion) {
                    initialQuestion.style.display = 'none';
                }
                callChatApi(question);
            }
        });
    }

    if (sendChatButton) {
        sendChatButton.addEventListener('click', () => {
            const message = chatInput.value.trim();
            if (message) {
                appState.conversation.push({ role: 'user', content: message });
                const userMessageElem = document.createElement('div');
                userMessageElem.classList.add('chat-message', 'user-message');
                userMessageElem.textContent = message;
                chatWindow.appendChild(userMessageElem);
                chatInput.value = '';
                chatWindow.scrollTop = chatWindow.scrollHeight;
                callChatApi(message);
            }
        });
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatButton.click();
            }
        });
    }

    if (clearChatButton) {
        clearChatButton.addEventListener('click', async () => {
            if (appState.sessionTokens[appState.activeBackend]) {
                try {
                    await makeApiRequest('/api/clear-session', { method: 'POST' }, config.timeouts.logout, clearChatButton, 'session');
                } catch (error) {
                    console.error("Failed to clear session on server:", error);
                }
            }
            
            appState.conversation = [];
            chatWindow.innerHTML = '';
            const chatColumn = document.getElementById('conversationalChatSection');
            if (chatColumn) {
                chatColumn.style.display = 'none';
            }
            if(welcomeMessage) {
                welcomeMessage.style.display = 'block';
            }
            if (initialQuestion) {
                initialQuestion.style.display = 'block';
            }
            updateStartChatButtonState();
        });
    }
    
    if (chatSelect) {
        choicesInstance = new Choices(chatSelect, {
            searchEnabled: true,
            itemSelectText: '',
            removeItemButton: true,
            shouldSort: false,
            searchPlaceholderValue: "Search for a chat...",
        });
        choicesInstance.disable();
        chatSelect.addEventListener('change', () => {
            appState.conversation = [];
            if (chatWindow) chatWindow.innerHTML = '';
            if (conversationalChatSection) conversationalChatSection.style.display = 'none';
            if (welcomeMessage) {
                welcomeMessage.style.display = 'block';
            }
            if (initialQuestion) {
                initialQuestion.style.display = 'block';
                initialQuestion.value = '';
            }
            updateStartChatButtonState();
        });
    }
    
    initializeFlatpickr();

    if (cacheChatsToggle) {
        const saved = localStorage.getItem(CACHE_CHATS_KEY);
        cacheChatsToggle.checked = saved === null ? true : saved === 'true';
        cacheChatsToggle.addEventListener('change', () => {
            localStorage.setItem(CACHE_CHATS_KEY, cacheChatsToggle.checked ? 'true' : 'false');
        });
    }

    if (toggleQuestionCheckbox && initialQuestionGroup) {
        toggleQuestionCheckbox.addEventListener('change', () => {
            initialQuestionGroup.style.display = toggleQuestionCheckbox.checked ? 'block' : 'none';
        });
    }

    if (backendSelect) backendSelect.addEventListener('change', handleBackendChange);
    if (backendSelectMain) backendSelectMain.addEventListener('change', handleBackendChange);
    if (loginSubmitButton) loginSubmitButton.addEventListener('click', handleLogin);
    if (webexLoginButton) webexLoginButton.addEventListener('click', handleLogin);
    if (verifyButton) verifyButton.addEventListener('click', handleVerify);
    if (logoutButton) logoutButton.addEventListener('click', handleFullLogout);
    if (refreshChatsLink) refreshChatsLink.addEventListener('click', handleLoadChats);
    
    if (modelSelect) modelSelect.addEventListener('change', updateStartChatButtonState);
    if (backendSelectMain) {
        backendSelectMain.addEventListener('change', () => {
            const newBackend = backendSelectMain.value;
            if (newBackend !== appState.activeBackend) {
                if (confirm('Are you sure you want to switch services? This will clear your current session and chat list.')) {
                    switchService(newBackend);
                } else {
                    // Reset dropdown to the original value if user cancels
                    backendSelectMain.value = appState.activeBackend;
                }
            }
        });
    }
    if (downloadChatButton) downloadChatButton.addEventListener('click', handleDownloadChat);
    
    checkSessionOnLoad();

    if (manageBotsButton) manageBotsButton.addEventListener('click', () => showSection('botManagementSection'));
    if (backToChatsButton) backToChatsButton.addEventListener('click', () => showSection('chatSection'));
    if (registerBotButton) registerBotButton.addEventListener('click', handleRegisterBot);
    function updateToggleButton() {
        const isMobile = window.innerWidth <= 1024;
        if (isMobile) {
            // On mobile, the button is for opening/closing the slide-out menu
            if (mainContainer.classList.contains('mobile-menu-open')) {
                toggleLhsButton.innerHTML = '&times;'; // "X" to close
                toggleLhsButton.title = 'Close menu';
            } else {
                toggleLhsButton.innerHTML = '&#9776;'; // Hamburger
                toggleLhsButton.title = 'Open menu';
            }
        } else {
            // On desktop, the button is for collapsing/expanding the sidebar
            if (mainContainer.classList.contains('lhs-collapsed')) {
                toggleLhsButton.innerHTML = '&rarr;'; // Right arrow
                toggleLhsButton.title = 'Show sidebar';
            } else {
                toggleLhsButton.innerHTML = '&larr;'; // Left arrow
                toggleLhsButton.title = 'Hide sidebar';
            }
        }
    }
    if (toggleLhsButton && mainContainer) {
        toggleLhsButton.addEventListener('click', () => {
            const isMobile = window.innerWidth <= 1024;
            if (isMobile) {
                mainContainer.classList.toggle('mobile-menu-open');
            } else {
                mainContainer.classList.toggle('lhs-collapsed');
            }
            updateToggleButton(); // Update icon after action
        });

        window.addEventListener('resize', updateToggleButton); // Update on resize
        updateToggleButton(); // Initial state
    }

    if(mobileMenuOverlay) {
        mobileMenuOverlay.addEventListener('click', closeMobileMenu);
    }

    if (themeCheckbox) {
        themeCheckbox.addEventListener('change', () => {
            if (themeCheckbox.checked) {
                document.body.classList.add('dark-theme');
                localStorage.setItem('theme', 'dark-theme');
            } else {
                document.body.classList.remove('dark-theme');
                localStorage.setItem('theme', 'light-theme');
            }
        });

        // Apply saved theme on load
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark-theme') {
            document.body.classList.add('dark-theme');
            themeCheckbox.checked = true;
        }
    }
});

// --- Bot Management ---
async function loadBots() {
    if (!appState.activeBackend) return;
    registeredBotsList.innerHTML = '<tr><td colspan="2">Loading...</td></tr>';
    try {
        const bots = await makeApiRequest(`/api/${appState.activeBackend}/bots`, { method: 'GET' }, config.timeouts.loadChats);
        registeredBotsList.innerHTML = '';
        if (bots.length > 0) {
            bots.forEach(bot => {
                const row = registeredBotsList.insertRow();
                const nameCell = row.insertCell(0);
                const actionCell = row.insertCell(1);
                nameCell.textContent = bot.name;
                
                const deleteButton = document.createElement('button');
                deleteButton.textContent = '🗑️'; // Use a trash can emoji for a smaller button
                deleteButton.classList.add('delete-bot-button');
                deleteButton.title = `Delete ${bot.name}`;
                deleteButton.onclick = () => handleDeleteBot(bot.name);
                actionCell.appendChild(deleteButton);
            });
        } else {
            registeredBotsList.innerHTML = '<tr><td colspan="2">No bots registered for this service.</td></tr>';
        }
    } catch (error) {
        registeredBotsList.innerHTML = `<tr><td colspan="2" class="error-message">Error loading bots: ${error.message}</td></tr>`;
    }
}

async function handleRegisterBot() {
    clearErrors();
    const name = botNameInput.value.trim();
    const bot_id = botIdInput.value.trim();
    const token = botTokenInput.value.trim();
    const webhook_url = webhookUrlInput.value.trim();

    if (appState.activeBackend === 'webex' && (!name || !token || !bot_id)) {
        botManagementError.textContent = 'Bot Name, Bot ID, and Token are required for Webex bots.';
        return;
    }
    
    if (appState.activeBackend === 'telegram' && (!name || !token)) {
        botManagementError.textContent = 'Bot Name and Token are required for Telegram bots.';
        return;
    }

    try {
        const payload = { name, token, bot_id: bot_id || 'telegram_bot' }; // Provide a dummy bot_id for telegram
        if (webhook_url) {
            payload.webhook_url = webhook_url;
        }
        await makeApiRequest(`/api/${appState.activeBackend}/bots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }, config.timeouts.login, registerBotButton);
        
        botNameInput.value = '';
        botIdInput.value = '';
        botTokenInput.value = '';
        webhookUrlInput.value = '';
        loadBots();
    } catch (error) {
        botManagementError.textContent = error.message || 'Failed to register bot.';
    }
}

async function handleDeleteBot(botName) {
    if (!confirm(`Are you sure you want to delete the bot "${botName}"?`)) {
        return;
    }
    try {
        await makeApiRequest(`/api/${appState.activeBackend}/bots/${botName}`, { method: 'DELETE' }, config.timeouts.login);
        loadBots();
    } catch (error) {
        botManagementError.textContent = error.message || 'Failed to delete bot.';
    }
}
