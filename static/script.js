// --- Global State & Configuration ---
const appState = {
    isProcessing: false,
    activeBackend: null,
    userIdentifiers: { telegram: null, webex: null },
    activeSection: 'login',
    modelsLoaded: false,
    chatListStatus: { telegram: 'unloaded', webex: 'unloaded' }, // 'unloaded', 'loading', 'loaded'
    analysisMode: 'summary',
};
const CACHE_CHATS_KEY = 'chat_analyzer_cache_chats_enabled';

// Namespaced Local Storage Keys
const ACTIVE_BACKEND_KEY = 'chat_analyzer_active_backend';
const getUserIdKey = (backend) => `chat_analyzer_${backend}_user_id`;

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
const startDateInput = document.getElementById('startDate');
const endDateInput = document.getElementById('endDate');
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
function setDefaultDates() { /* ... */ }
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

function setDefaultDates() {
    if (startDateInput && endDateInput) {
        const today = new Date();
        const todayString = today.toISOString().slice(0, 10);
        // Only set the dates if they are empty, to avoid overwriting user selections
        if (!startDateInput.value) {
            startDateInput.value = todayString;
        }
        if (!endDateInput.value) {
            endDateInput.value = todayString;
        }
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
    const validChatSelected = chatSelect && chatSelect.value && !chatSelect.options[chatSelect.selectedIndex]?.disabled;
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
    const storedUserId = localStorage.getItem(getUserIdKey(newBackend));
    if (storedUserId) {
        try {
            await makeApiRequest(`/api/session-status?backend=${newBackend}&user_id=${encodeURIComponent(storedUserId)}`, {method: 'GET'}, 10000);
            
            appState.activeBackend = newBackend;
            appState.userIdentifiers[newBackend] = storedUserId;
            localStorage.setItem(ACTIVE_BACKEND_KEY, newBackend);
            
            // Do not reset chat list if already loaded for this backend
            if (appState.chatListStatus[newBackend] !== 'loaded') {
                 if (chatSelect) chatSelect.innerHTML = '<option value="" disabled selected>Loading chats...</option>';
                 if (lastUpdatedTime) lastUpdatedTime.textContent = '';
            }
            
            showSection('chat');
            return;
        } catch (error) {
            localStorage.removeItem(getUserIdKey(newBackend));
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
        if (data.status === 'success') {
            const userId = data.user_identifier;
            appState.userIdentifiers.telegram = userId;
            appState.activeBackend = 'telegram';
            localStorage.setItem(getUserIdKey('telegram'), userId);
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
    const userId = appState.userIdentifiers[backend];

    if (backend && userId) {
        await makeApiRequest('/api/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ backend, userId }) }, config.timeouts.logout, logoutButton);
        localStorage.removeItem(getUserIdKey(backend));
        appState.userIdentifiers[backend] = null;
        appState.chatListStatus[backend] = 'unloaded'; // Reset chat loading status
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
    if (!backend) return;
    const userId = appState.userIdentifiers[backend];
    if (!userId) {
        if (chatLoadingError) chatLoadingError.textContent = "No user session active.";
        return;
    };
    appState.chatListStatus[backend] = 'loading';
    updateSummaryButtonState();
    try {
        const data = await makeApiRequest(`/api/chats?backend=${backend}&user_id=${encodeURIComponent(userId)}`, { method: 'GET' }, config.timeouts.loadChats, refreshChatsLink, 'Refreshing...');
        if (chatSelect) chatSelect.innerHTML = '';
        if (data && data.length > 0) {
            data.forEach(chat => {
                const option = document.createElement('option');
                option.value = chat.id;
                option.textContent = `${chat.title} (${chat.type})`;
                if (chatSelect) chatSelect.appendChild(option);
            });
            if (chatSelect) chatSelect.disabled = false;
            appState.chatListStatus[backend] = 'loaded';
            if(lastUpdatedTime) lastUpdatedTime.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        } else {
            if (chatSelect) chatSelect.innerHTML = '<option disabled selected>No chats found</option>';
            appState.chatListStatus[backend] = 'loaded'; // Loaded, but empty
        }
    } catch(error) {
        if (chatLoadingError) chatLoadingError.textContent = error.message || 'Failed to load chats.';
        appState.chatListStatus[backend] = 'unloaded'; // Allow retry on failure
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
        const addOptions = (models, groupLabel) => {
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
        };
        addOptions(data.google_ai_models, "Google AI Models");
        addOptions(data.lm_studio_models, "LM Studio Models");
        
        if (modelSelect && modelSelect.options.length > 0) {
            modelSelect.disabled = false;
            appState.modelsLoaded = true;
            const defaultGoogle = data.default_models?.google_ai;
            const defaultLmStudio = data.default_models?.lm_studio;
            if (defaultGoogle && modelSelect.querySelector(`option[value="${defaultGoogle}"]`)) {
                modelSelect.value = defaultGoogle;
            } else if (defaultLmStudio && modelSelect.querySelector(`option[value="${defaultLmStudio}"]`)) {
                modelSelect.value = defaultLmStudio;
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
    if (cacheChatsToggle) {
        localStorage.setItem(CACHE_CHATS_KEY, cacheChatsToggle.checked ? 'true' : 'false');
    }
    const requestBody = {
        backend: appState.activeBackend,
        userId: appState.userIdentifiers[appState.activeBackend],
        chatId: chatSelect.value,
        startDate: startDateInput.value,
        endDate: endDateInput.value,
        modelName: modelSelect.value,
        question: askQuestionToggle.checked ? questionInput.value.trim() : null,
        enableCaching: cacheChatsToggle ? cacheChatsToggle.checked : true
    };
    
    try {
        const data = await makeApiRequest('/api/summary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) }, config.timeouts.summary, getSummaryButton);
        if (data.status.startsWith('success')) {
            resultsTitle.textContent = requestBody.question ? 'Answer' : 'Summary';
            summaryContent.innerHTML = marked.parse(data.summary.ai_summary);
            summaryMeta.textContent = `Based on ${data.summary.num_messages} message(s).`;
            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
             if (dateError) dateError.textContent = data.message || 'Failed to get results.';
        }
    } catch (error) {
        if (dateError) dateError.textContent = error.message || 'Failed to get summary.';
    }
}

async function checkSessionOnLoad() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('backend') === 'webex' && params.get('status') === 'success') {
        const webexUserId = params.get('user_id'); 
        if(webexUserId) {
            appState.activeBackend = 'webex';
            appState.userIdentifiers.webex = webexUserId;
            localStorage.setItem(getUserIdKey('webex'), webexUserId);
            localStorage.setItem(ACTIVE_BACKEND_KEY, 'webex');
            window.history.replaceState({}, document.title, "/");
            showSection('chat');
            return;
        }
    }
    const lastActiveBackend = localStorage.getItem(ACTIVE_BACKEND_KEY);
    if (lastActiveBackend) {
        const lastActiveUserId = localStorage.getItem(getUserIdKey(lastActiveBackend));
        if (lastActiveUserId) {
            try {
                await makeApiRequest(`/api/session-status?backend=${lastActiveBackend}&user_id=${encodeURIComponent(lastActiveUserId)}`, {method: 'GET'}, 10000);
                appState.activeBackend = lastActiveBackend;
                appState.userIdentifiers.telegram = localStorage.getItem(getUserIdKey('telegram'));
                appState.userIdentifiers.webex = localStorage.getItem(getUserIdKey('webex'));
                showSection('chat');
                return;
            } catch (error) {
                localStorage.removeItem(getUserIdKey(lastActiveBackend));
                localStorage.removeItem(ACTIVE_BACKEND_KEY);
            }
        }
    }
    appState.activeBackend = 'telegram';
    showSection('login');
}

document.addEventListener('DOMContentLoaded', () => {
    // Set default dates only once on initial load.
    setDefaultDates();

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

    if (chatSelect) chatSelect.addEventListener('change', updateSummaryButtonState);
    if (modelSelect) modelSelect.addEventListener('change', updateSummaryButtonState);
    if (questionInput) questionInput.addEventListener('input', updateSummaryButtonState);
    
    checkSessionOnLoad();
});