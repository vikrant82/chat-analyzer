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

let tomSelectInstance = null;

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
const switchServiceButton = document.getElementById('switchServiceButton');
const cacheChatsToggle = document.getElementById('cacheChatsToggle');
const switchServiceModal = document.getElementById('switchServiceModal');
const switchServiceOptions = document.getElementById('switchServiceOptions');
const cancelSwitchButton = document.getElementById('cancelSwitchButton');
const chatSectionTitle = document.getElementById('chatSectionTitle');
const conversationalChatSection = document.getElementById('conversationalChatSection');
const chatWindow = document.getElementById('chatWindow');
const chatInput = document.getElementById('chatInput');
const sendChatButton = document.getElementById('sendChatButton');
const clearChatButton = document.getElementById('clearChatButton');
const startChatButton = document.getElementById('startChatButton');
const initialQuestion = document.getElementById('initialQuestion');

// --- Utility Functions ---
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
}

function updateStartChatButtonState() {
    if (!startChatButton) return;
    const validChatSelected = tomSelectInstance && tomSelectInstance.getValue() !== "";
    const validModelSelected = modelSelect && modelSelect.value && !modelSelect.options[modelSelect.selectedIndex]?.disabled;
    const baseRequirementsMet = appState.chatListStatus[appState.activeBackend] === 'loaded' && appState.modelsLoaded && validChatSelected && validModelSelected;
    startChatButton.disabled = !baseRequirementsMet;
    if (initialQuestion) {
        initialQuestion.disabled = !baseRequirementsMet;
    }
}

function initializeDateRangePicker() {
    const dateRangePicker = $('#dateRangePicker');
    dateRangePicker.daterangepicker({
        startDate: moment(),
        endDate: moment(),
        ranges: {
            'Last 2 Days': [moment().subtract(1, 'days'), moment()],
            'Last 3 Days': [moment().subtract(2, 'days'), moment()],
            'Last 4 Days': [moment().subtract(3, 'days'), moment()],
            'Last Week': [moment().subtract(6, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last 2 Months': [moment().subtract(2, 'month').startOf('month'), moment()]
        }
    });

    dateRangePicker.on('apply.daterangepicker', function(ev, picker) {
        updateStartChatButtonState();
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
        if (!appState.modelsLoaded) {
            loadModels();
        }
        if (appState.chatListStatus[appState.activeBackend] === 'unloaded') {
            handleLoadChats();
        }
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
}

function openSwitchServiceModal() {
    if (!switchServiceOptions || !switchServiceModal) return;
    switchServiceOptions.innerHTML = '';
    const otherBackend = appState.activeBackend === 'telegram' ? 'webex' : 'telegram';
    
    const button = document.createElement('button');
    button.textContent = `Switch to ${otherBackend.charAt(0).toUpperCase() + otherBackend.slice(1)}`;
    button.onclick = () => {
        switchService(otherBackend);
        switchServiceModal.style.display = 'none';
    };
    switchServiceOptions.appendChild(button);
    switchServiceModal.style.display = 'block';
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
    
    if (tomSelectInstance) {
        tomSelectInstance.clear();
        tomSelectInstance.clearOptions();
        tomSelectInstance.settings.placeholder = 'Select or search for a chat...';
        tomSelectInstance.refreshOptions(false);
        tomSelectInstance.disable();
    }
}

async function handleLoadChats() {
    const backend = appState.activeBackend;
    if (!backend || !tomSelectInstance || !appState.sessionTokens[backend]) {
        if (chatLoadingError) chatLoadingError.textContent = "No active session.";
        return;
    }

    appState.chatListStatus[backend] = 'loading';
    tomSelectInstance.clear();
    tomSelectInstance.clearOptions();
    tomSelectInstance.settings.placeholder = 'Refreshing...';
    tomSelectInstance.refreshOptions(false);
    tomSelectInstance.disable();
    updateStartChatButtonState();

    try {
        const url = `/api/chats?backend=${backend}`;
        const data = await makeApiRequest(url, { method: 'GET' }, config.timeouts.loadChats, refreshChatsLink, 'Refreshing...', 'chats');
        
        if (data && data.length > 0) {
            data.forEach(chat => {
                tomSelectInstance.addOption({
                    value: chat.id,
                    text: `${chat.title} (${chat.type})`
                });
            });
            tomSelectInstance.settings.placeholder = 'Select or search for a chat...';
            tomSelectInstance.enable();
            if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        } else {
            tomSelectInstance.settings.placeholder = 'No chats found';
        }
        appState.chatListStatus[backend] = 'loaded';
        tomSelectInstance.refreshOptions(false);

    } catch(error) {
        if (chatLoadingError) chatLoadingError.textContent = error.message || 'Failed to load chats.';
        tomSelectInstance.settings.placeholder = 'Failed to load. Click "Refresh List".';
        tomSelectInstance.refreshOptions(false);
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
        Object.keys(data).forEach(key => {
            if (key.endsWith('_models')) {
                const models = data[key];
                const providerName = key.replace('_models', '').replace('_', ' ');
                const groupLabel = providerName.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
                
                if (models && models.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = groupLabel;
                    models.forEach(modelName => {
                        const option = document.createElement('option');
                        option.value = modelName;
                        option.textContent = modelName;
                        optgroup.appendChild(option);
                    });
                    if (modelSelect) modelSelect.appendChild(optgroup);
                }
            }
        });

        if (modelSelect && modelSelect.options.length > 0) {
            modelSelect.disabled = false;
            appState.modelsLoaded = true;
            const defaultModels = data.default_models || {};
            const firstDefault = Object.values(defaultModels).find(model => model && modelSelect.querySelector(`option[value="${model}"]`));
            if (firstDefault) {
                modelSelect.value = firstDefault;
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
        const requestBody = {
            chatId: tomSelectInstance.getValue(),
            modelName: modelSelect.value,
            startDate: $('#dateRangePicker').data('daterangepicker').startDate.format('YYYY-MM-DD'),
            endDate: $('#dateRangePicker').data('daterangepicker').endDate.format('YYYY-MM-DD'),
            enableCaching: cacheChatsToggle.checked,
            conversation: appState.conversation,
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

document.addEventListener('DOMContentLoaded', () => {
    if (startChatButton) {
        startChatButton.addEventListener('click', () => {
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
            if (chatColumn) {
                chatColumn.style.display = 'block';
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
            if (initialQuestion) {
                initialQuestion.style.display = 'block';
            }
            updateStartChatButtonState();
        });
    }
    
    if (chatSelect) {
        tomSelectInstance = new TomSelect(chatSelect, {
            create: false,
            placeholder: 'Select or search for a chat...',
            theme: 'bootstrap5'
        });
        tomSelectInstance.disable();
        tomSelectInstance.on('change',() => {
            appState.conversation = [];
            if (chatWindow) chatWindow.innerHTML = '';
            if (conversationalChatSection) conversationalChatSection.style.display = 'none';
            if (initialQuestion) {
                initialQuestion.style.display = 'block';
                initialQuestion.value = '';
            }
            updateStartChatButtonState();
        });
    }
    
    initializeDateRangePicker();

    if (cacheChatsToggle) {
        const saved = localStorage.getItem(CACHE_CHATS_KEY);
        cacheChatsToggle.checked = saved === null ? true : saved === 'true';
        cacheChatsToggle.addEventListener('change', () => {
            localStorage.setItem(CACHE_CHATS_KEY, cacheChatsToggle.checked ? 'true' : 'false');
        });
    }

    if (backendSelect) backendSelect.addEventListener('change', handleBackendChange);
    if (loginSubmitButton) loginSubmitButton.addEventListener('click', handleLogin);
    if (webexLoginButton) webexLoginButton.addEventListener('click', handleLogin);
    if (verifyButton) verifyButton.addEventListener('click', handleVerify);
    if (logoutButton) logoutButton.addEventListener('click', handleFullLogout);
    if (switchServiceButton) switchServiceButton.addEventListener('click', openSwitchServiceModal);
    if (cancelSwitchButton) cancelSwitchButton.addEventListener('click', () => switchServiceModal.style.display = 'none');
    if (refreshChatsLink) refreshChatsLink.addEventListener('click', handleLoadChats);
    
    if (modelSelect) modelSelect.addEventListener('change', updateStartChatButtonState);
    
    checkSessionOnLoad();
});
