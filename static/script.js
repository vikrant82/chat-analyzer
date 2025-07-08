// --- Global State & Configuration ---
const appState = {
    isProcessing: false,
    activeBackend: null,
    userIdentifiers: { telegram: null, webex: null }, // This will now be used for internal state, not for API calls
    sessionToken: null,
    activeSection: 'login',
    modelsLoaded: false,
    chatListStatus: { telegram: 'unloaded', webex: 'unloaded' }, // 'unloaded', 'loading', 'loaded'
    analysisMode: 'summary',
};
const CACHE_CHATS_KEY = 'chat_analyzer_cache_chats_enabled';

// Namespaced Local Storage Keys
const ACTIVE_BACKEND_KEY = 'chat_analyzer_active_backend';
const getUserIdKey = (backend) => `chat_analyzer_${backend}_user_id`; // Kept for Webex which doesn't use tokens
const SESSION_TOKEN_KEY = 'chat_analyzer_session_token';

const config = {
    timeouts: {
        verify: 180000, summary: 180000, loadChats: 30000,
        logout: 15000, login: 30000, loadModels: 20000,
    }
};

let tomSelectInstance = null;
let litepickerInstance = null;

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
const getSummaryButton = document.getElementById('getSummaryButton');
const logoutButton = document.getElementById('logoutButton');
const switchServiceButton = document.getElementById('switchServiceButton');
const askQuestionToggle = document.getElementById('askQuestionToggle');
const cacheChatsToggle = document.getElementById('cacheChatsToggle');
const questionInputContainer = document.getElementById('questionInputContainer');
const questionInput = document.getElementById('questionInput');
const questionError = document.getElementById('questionError');
const switchServiceModal = document.getElementById('switchServiceModal');
const switchServiceOptions = document.getElementById('switchServiceOptions');
const cancelSwitchButton = document.getElementById('cancelSwitchButton');
const chatSectionTitle = document.getElementById('chatSectionTitle');

// Elements for the new in-page results
const resultsContainer = document.getElementById('resultsContainer');
const summaryContent = document.getElementById('summaryContent');
const summaryMeta = document.getElementById('summaryMeta');
const resultsTitle = document.getElementById('resultsTitle');


// --- Utility Functions (Unchanged) ---
function setLoadingState(buttonElement, isLoading, loadingText = 'Processing...') { /* ... */ }
function clearErrors() { /* ... */ }
function updateSummaryButtonState() { /* ... */ }
async function makeApiRequest(url, options, timeoutDuration, elementToLoad = null, loadingText = 'Processing...') { /* ... */ }

// --- Re-add full utility functions for completeness ---
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
    if (questionError) questionError.textContent = '';
}

function updateSummaryButtonState() {
    let isEnabled = false;
    const validChatSelected = tomSelectInstance && tomSelectInstance.getValue() !== "";
    const validModelSelected = modelSelect && modelSelect.value && !modelSelect.options[modelSelect.selectedIndex]?.disabled;
    const baseRequirementsMet = appState.chatListStatus[appState.activeBackend] === 'loaded' && appState.modelsLoaded && validChatSelected && validModelSelected;

    if (baseRequirementsMet) {
        if (askQuestionToggle && askQuestionToggle.checked) {
            isEnabled = questionInput && questionInput.value.trim() !== '';
        } else {
            isEnabled = true;
        }
    }
    if (getSummaryButton) {
        getSummaryButton.disabled = !isEnabled;
        getSummaryButton.textContent = (askQuestionToggle && askQuestionToggle.checked) ? 'Get Answer' : 'Get Summary';
    }
}

async function makeApiRequest(url, options, timeoutDuration, elementToLoad = null, loadingText = 'Processing...') {
    if (appState.isProcessing && elementToLoad && elementToLoad.disabled) {
        throw new Error('Operation already in progress.');
    }
    appState.isProcessing = true;
    if (elementToLoad) setLoadingState(elementToLoad, true, loadingText);

    // Add the Authorization header if a token exists
    if (appState.sessionToken) {
        if (!options.headers) {
            options.headers = {};
        }
        options.headers['Authorization'] = `Bearer ${appState.sessionToken}`;
    }

    const controller = new AbortController();
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
        appState.isProcessing = false;
        if (elementToLoad) setLoadingState(elementToLoad, false);
    }
}


// --- Core Application Logic ---

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
    appState.activeSection = sectionName;
    clearErrors();
    if (resultsContainer) resultsContainer.style.display = 'none'; // Hide results when switching sections

    const sectionToShow = document.getElementById(sectionName + 'Section');
    if (sectionToShow) {
        sectionToShow.classList.add('active');
    }

    if (sectionName === 'chat') {
        if (!appState.activeBackend) {
            showSection('login');
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
    } else if (sectionName === 'login') {
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
    // Webex uses the old flow, Telegram uses the new token flow
    if (newBackend === 'webex') {
        const storedUserId = localStorage.getItem(getUserIdKey(newBackend));
        if (storedUserId) {
            try {
                // This Webex endpoint doesn't use the token, so we call it directly
                await fetch(`/api/session-status?backend=webex&user_id=${encodeURIComponent(storedUserId)}`, { method: 'GET' });
                appState.activeBackend = newBackend;
                appState.userIdentifiers.webex = storedUserId;
                localStorage.setItem(ACTIVE_BACKEND_KEY, newBackend);
                showSection('chat');
                return;
            } catch (error) {
                localStorage.removeItem(getUserIdKey(newBackend));
            }
        }
    } else if (newBackend === 'telegram' && appState.sessionToken) {
        try {
            // The token is sent via the header in makeApiRequest
            await makeApiRequest(`/api/session-status?backend=telegram`, { method: 'GET' }, 10000);
            appState.activeBackend = newBackend;
            localStorage.setItem(ACTIVE_BACKEND_KEY, newBackend);
            showSection('chat');
            return;
        } catch (error) {
            // Token is invalid, clear it and go to login
            appState.sessionToken = null;
            localStorage.removeItem(SESSION_TOKEN_KEY);
        }
    }

    appState.activeBackend = newBackend;
    showSection('login');
}

async function handleLogin() {
    clearErrors();
    const selectedBackend = backendSelect.value;
    appState.activeBackend = selectedBackend;

    if (selectedBackend === 'telegram') {
        const phoneVal = phoneInput.value.trim();
        if (!phoneVal) { 
            loginError.textContent = 'Phone number is required.';
            return; 
        }
        appState.userIdentifiers.telegram = phoneVal;
        try {
            await makeApiRequest(`/api/telegram/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: phoneVal }) }, config.timeouts.login, loginSubmitButton);
            showSection('verification');
        } catch (error) { 
            loginError.textContent = error.message || 'Login failed.';
        }
    } else if (selectedBackend === 'webex') {
        setLoadingState(webexLoginButton, true, 'Redirecting...');
        window.location.href = '/api/webex/login';
    }
}

async function handleVerify() {
    const code = verificationCodeInput.value.trim();
    const password = passwordInput.value;
    const phone = appState.userIdentifiers.telegram;
    
    try {
        const data = await makeApiRequest(`/api/telegram/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone, code, password }) }, config.timeouts.verify, verifyButton);
        if (data.status === 'success' && data.token) {
            appState.sessionToken = data.token;
            appState.activeBackend = 'telegram';
            localStorage.setItem(SESSION_TOKEN_KEY, data.token);
            localStorage.setItem(ACTIVE_BACKEND_KEY, 'telegram');
            showSection('chat');
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

    if (backend) {
        // The backend is now a query parameter, and the body is empty
        const url = `/api/logout?backend=${backend}`;
        // For Webex, we also need to add the user_id to the query
        const finalUrl = backend === 'webex' 
            ? `${url}&user_id=${encodeURIComponent(appState.userIdentifiers.webex)}`
            : url;

        await makeApiRequest(finalUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }, config.timeouts.logout, logoutButton);
        
        if (backend === 'telegram') {
            localStorage.removeItem(SESSION_TOKEN_KEY);
            appState.sessionToken = null;
        } else if (backend === 'webex') {
            localStorage.removeItem(getUserIdKey('webex'));
            appState.userIdentifiers.webex = null;
        }

        appState.chatListStatus[backend] = 'unloaded';
        if (tomSelectInstance) {
            tomSelectInstance.clear();
            tomSelectInstance.clearOptions();
            tomSelectInstance.settings.placeholder = 'Select or search for a chat...';
            tomSelectInstance.refreshOptions(false);
            tomSelectInstance.disable();
        }
    }
    
    const otherBackend = backend === 'telegram' ? 'webex' : 'telegram';
    const otherUserId = localStorage.getItem(getUserIdKey(otherBackend));

    if (otherUserId) {
        appState.activeBackend = otherBackend;
        localStorage.setItem(ACTIVE_BACKEND_KEY, otherBackend);
        checkSessionOnLoad();
    } else {
        appState.activeBackend = 'telegram';
        localStorage.removeItem(ACTIVE_BACKEND_KEY);
        showSection('login');
    }
}

async function handleLoadChats() {
    const backend = appState.activeBackend;
    if (!backend || !tomSelectInstance) return;
    
    // Authorization is now handled by the token in the header for Telegram
    if (backend === 'telegram' && !appState.sessionToken) {
         if (chatLoadingError) chatLoadingError.textContent = "No user session active.";
        return;
    }
    // Webex still needs the user ID
    if (backend === 'webex' && !appState.userIdentifiers.webex) {
         if (chatLoadingError) chatLoadingError.textContent = "No user session active.";
        return;
    }

    appState.chatListStatus[backend] = 'loading';
    tomSelectInstance.clear();
    tomSelectInstance.clearOptions();
    tomSelectInstance.settings.placeholder = 'Refreshing...';
    tomSelectInstance.refreshOptions(false);
    tomSelectInstance.disable();
    updateSummaryButtonState();

    try {
        // The user_id is no longer needed for Telegram, it's derived from the token on the backend
        const url = backend === 'webex' 
            ? `/api/chats?backend=webex&user_id=${encodeURIComponent(appState.userIdentifiers.webex)}`
            : `/api/chats?backend=telegram`;

        const data = await makeApiRequest(url, { method: 'GET' }, config.timeouts.loadChats, refreshChatsLink, 'Refreshing...');
        
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
        updateSummaryButtonState();
    }
}

async function loadModels() {
    appState.modelsLoaded = false;
    updateSummaryButtonState();
    if (modelError) modelError.textContent = '';
    if (modelSelect) {
        modelSelect.innerHTML = '<option value="" disabled selected>Loading models...</option>';
        modelSelect.disabled = true;
    }
    try {
        const data = await makeApiRequest('/api/models', { method: 'GET' }, config.timeouts.loadModels);
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
            // Set default model if available
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
        updateSummaryButtonState();
    }
}

async function handleGetSummary() {
    if (resultsContainer) resultsContainer.style.display = 'none';
    clearErrors();

    // --- Step 1: Prepare the analysis (fetch messages) ---
    // The backend is now a query parameter, not part of the body
    const prepareRequestBody = {
        chatId: tomSelectInstance.getValue(),
        startDate: litepickerInstance.getStartDate().toJSDate().toISOString().slice(0, 10),
        endDate: litepickerInstance.getEndDate().toJSDate().toISOString().slice(0, 10),
        enableCaching: cacheChatsToggle ? cacheChatsToggle.checked : true
    };

    let prepareData;
    try {
        let url = `/api/prepare-analysis?backend=${appState.activeBackend}`;
        if (appState.activeBackend === 'webex') {
            url += `&user_id=${encodeURIComponent(appState.userIdentifiers.webex)}`;
        }
        prepareData = await makeApiRequest(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prepareRequestBody)
        }, config.timeouts.summary, getSummaryButton, 'Fetching Messages...');
    } catch (error) {
        if (dateError) dateError.textContent = error.message || 'Failed to fetch messages.';
        return;
    }

    const { num_messages, text_to_process } = prepareData;

    if (num_messages === 0) {
        resultsTitle.textContent = 'Result';
        summaryContent.textContent = 'No text messages found in this period.';
        summaryMeta.textContent = `Based on 0 message(s).`;
        resultsContainer.style.display = 'block';
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    // --- Step 2: Execute the analysis (call AI and stream response) ---
    const analyzeRequestBody = {
        modelName: modelSelect.value,
        textToProcess: text_to_process,
        startDate: prepareRequestBody.startDate,
        endDate: prepareRequestBody.endDate,
        question: askQuestionToggle.checked ? questionInput.value.trim() : null
    };

    // Prepare UI for streaming
    resultsTitle.textContent = analyzeRequestBody.question ? 'Answer' : 'Summary';
    summaryMeta.textContent = `Analyzing ${num_messages} message(s)...`;
    summaryContent.innerHTML = '';
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setLoadingState(getSummaryButton, true, `Analyzing ${num_messages} message(s)...`);

    let fullResponseText = '';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(analyzeRequestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Analysis failed: ${errorText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullResponseText += chunk;
            summaryContent.innerHTML = marked.parse(fullResponseText);
        }

        summaryMeta.textContent = `Based on ${num_messages} message(s).`;

    } catch (error) {
        summaryContent.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
    } finally {
        setLoadingState(getSummaryButton, false);
    }
}


async function checkSessionOnLoad() {
    const params = new URLSearchParams(window.location.search);
    // Handle Webex OAuth callback
    if (params.get('backend') === 'webex' && params.get('status') === 'success') {
        const webexUserId = params.get('user_id'); 
        if(webexUserId) {
            appState.activeBackend = 'webex';
            appState.userIdentifiers.webex = webexUserId;
            localStorage.setItem(getUserIdKey('webex'), webexUserId);
            localStorage.setItem(ACTIVE_BACKEND_KEY, 'webex');
            // Clear any old Telegram token
            localStorage.removeItem(SESSION_TOKEN_KEY);
            appState.sessionToken = null;
            window.history.replaceState({}, document.title, "/");
            showSection('chat');
            return;
        }
    }

    const lastActiveBackend = localStorage.getItem(ACTIVE_BACKEND_KEY);
    const sessionToken = localStorage.getItem(SESSION_TOKEN_KEY);
    const webexUserId = localStorage.getItem(getUserIdKey('webex'));

    if (lastActiveBackend === 'telegram' && sessionToken) {
        appState.sessionToken = sessionToken;
        try {
            // The token is automatically sent in the header by makeApiRequest
            await makeApiRequest(`/api/session-status?backend=telegram`, { method: 'GET' }, 10000);
            appState.activeBackend = 'telegram';
            showSection('chat');
            return;
        } catch (error) {
            // Token is invalid
            localStorage.removeItem(SESSION_TOKEN_KEY);
            appState.sessionToken = null;
        }
    } else if (lastActiveBackend === 'webex' && webexUserId) {
         try {
            // Webex doesn't use the token auth
            await fetch(`/api/session-status?backend=webex&user_id=${encodeURIComponent(webexUserId)}`, { method: 'GET' });
            appState.activeBackend = 'webex';
            appState.userIdentifiers.webex = webexUserId;
            showSection('chat');
            return;
        } catch (error) {
            localStorage.removeItem(getUserIdKey('webex'));
        }
    }

    // If no valid session is found, default to the login screen
    appState.activeBackend = 'telegram';
    localStorage.removeItem(ACTIVE_BACKEND_KEY);
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem(getUserIdKey('webex'));
    showSection('login');
}

document.addEventListener('DOMContentLoaded', () => {
    if (chatSelect) {
        tomSelectInstance = new TomSelect(chatSelect, {
            create: false,
            placeholder: 'Select or search for a chat...',
            theme: 'bootstrap5'
        });
        tomSelectInstance.disable(); // Start as disabled until chats are loaded
        tomSelectInstance.on('change', updateSummaryButtonState);
    }
    
    litepickerInstance = new Litepicker({
        element: document.getElementById('dateRangePicker'),
        singleMode: false,
        format: 'YYYY-MM-DD',
        plugins: ['ranges'],
        ranges: {
            'Today': [new Date(), new Date()],
            'Last 7 Days': (() => {
                const end = new Date();
                const start = new Date();
                start.setDate(end.getDate() - 6);
                return [start, end];
            })(),
            'Last 30 Days': (() => {
                const end = new Date();
                const start = new Date();
                start.setDate(end.getDate() - 29);
                return [start, end];
            })(),
            'This Month': (() => {
                const start = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
                const end = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0);
                return [start, end];
            })(),
        },
        setup: (picker) => {
            picker.setDateRange(new Date(), new Date());
        },
    });


    // Restore cacheChatsToggle state from localStorage (default enabled)
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
    if (getSummaryButton) getSummaryButton.addEventListener('click', handleGetSummary);
    
    if (askQuestionToggle) {
        askQuestionToggle.addEventListener('change', (e) => {
            appState.analysisMode = e.target.checked ? 'question' : 'summary';
            if (questionInputContainer) {
                questionInputContainer.style.display = e.target.checked ? 'block' : 'none';
            }
            updateSummaryButtonState();
        });
    }

    if (modelSelect) modelSelect.addEventListener('change', updateSummaryButtonState);
    if (questionInput) questionInput.addEventListener('input', updateSummaryButtonState);
    
    checkSessionOnLoad();
});
