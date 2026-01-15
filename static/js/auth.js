import { appState, config, ACTIVE_BACKEND_KEY, getSessionTokenKey } from './state.js';
import { makeApiRequest } from './api.js';
import {
    loginError, verificationError, phoneInput, loginSubmitButton, webexLoginButton,
    verificationCodeInput, passwordInput, passwordField, showSection, clearErrors,
    setLoadingState, telegramLoginForm, webexLoginContainer, imageSettings,
    backendSelect, getChoicesInstance, chatWindow, conversationalChatSection,
    welcomeMessage, logoutButton, backendSelectMain
} from './ui.js';

export function handleBackendChange() {
    const redditLoginContainer = document.getElementById('redditLoginContainer');
    if (backendSelect && telegramLoginForm && webexLoginContainer && redditLoginContainer) {
        const selectedBackend = backendSelect.value;
        telegramLoginForm.style.display = selectedBackend === 'telegram' ? 'block' : 'none';
        webexLoginContainer.style.display = selectedBackend === 'webex' ? 'block' : 'none';
        redditLoginContainer.style.display = selectedBackend === 'reddit' ? 'block' : 'none';
    }
    // Also handle the main backend selector
    if(backendSelectMain) {
        imageSettings.style.display = 'block';
    }
}

export async function switchService(newBackend) {
    if (appState.activeBackend === newBackend) return;

    clearErrors();

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
        window.showSection('chatSection');
    } else {
        window.showSection('loginSection');
    }
}

export async function handleLogin() {
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
            window.showSection('verificationSection');
        } catch (error) { 
            loginError.textContent = error.message || 'Login failed.';
        }
    } else { // Handles Webex and Reddit
        const button = selectedBackend === 'webex' ? webexLoginButton : document.getElementById('redditLoginButton');
        setLoadingState(button, true, 'Redirecting...');
        try {
            const data = await makeApiRequest(url, { method: 'POST' }, config.timeouts.login, button, 'login');
            if (data.url) {
                window.location.href = data.url;
            } else {
                loginError.textContent = 'Could not get login redirect URL.';
                setLoadingState(button, false);
            }
        } catch (error) {
            loginError.textContent = error.message || 'Login failed.';
            setLoadingState(button, false);
        }
    }
}

export async function handleVerify() {
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
            window.showSection('chatSection');
        } else if (data.status === 'password_required') {
            passwordField.style.display = 'block';
            verificationError.textContent = 'Password required for 2FA.';
        }
    } catch (error) { 
        verificationError.textContent = error.message || 'Verification failed.';
    }
}

export async function handleFullLogout() {
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
        sessionStorage.removeItem(`${backend}-chats`);
        appState.sessionTokens[backend] = null;
        appState.chatListStatus[backend] = 'unloaded';
    }
    appState.conversation = [];

    const availableBackends = ['telegram', 'webex', 'reddit'];
    const remainingBackends = availableBackends.filter(b => b !== backend);
    let switched = false;
    for (const nextBackend of remainingBackends) {
        if (localStorage.getItem(getSessionTokenKey(nextBackend))) {
            switchService(nextBackend);
            switched = true;
            break;
        }
    }

    if (!switched) {
        localStorage.removeItem(ACTIVE_BACKEND_KEY);
        appState.activeBackend = null;
        window.showSection('loginSection');
    }
    
    const choicesInstance = getChoicesInstance();
    if (choicesInstance) {
        choicesInstance.clearStore();
        choicesInstance.disable();
    }
}

export async function checkSessionOnLoad() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const backend = params.get('backend');

    if (token && backend) {
        appState.sessionTokens[backend] = token;
        appState.activeBackend = backend;
        localStorage.setItem(getSessionTokenKey(backend), token);
        localStorage.setItem(ACTIVE_BACKEND_KEY, backend);
        window.history.replaceState({}, document.title, "/");
        window.showSection('chatSection');
        return;
    }
    
    appState.sessionTokens.telegram = localStorage.getItem(getSessionTokenKey('telegram'));
    appState.sessionTokens.webex = localStorage.getItem(getSessionTokenKey('webex'));
    appState.sessionTokens.reddit = localStorage.getItem(getSessionTokenKey('reddit'));
    const lastBackend = localStorage.getItem(ACTIVE_BACKEND_KEY);

    if (lastBackend && appState.sessionTokens[lastBackend]) {
        appState.activeBackend = lastBackend;
        try {
            await makeApiRequest(`/api/session-status?backend=${lastBackend}`, { method: 'GET' }, 10000, null, 'session');
            window.showSection('chatSection');
            return;
        } catch (error) {
            console.error(`Session check failed for ${lastBackend}:`, error);
            localStorage.removeItem(getSessionTokenKey(lastBackend));
            appState.sessionTokens[lastBackend] = null;
            
            const availableBackends = ['telegram', 'webex', 'reddit'];
            const remainingBackends = availableBackends.filter(b => b !== lastBackend);
            for (const nextBackend of remainingBackends) {
                if (appState.sessionTokens[nextBackend]) {
                    switchService(nextBackend);
                    return;
                }
            }
        }
    }

    window.showSection('loginSection');
}
