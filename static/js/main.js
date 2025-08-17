import { appState, CACHE_CHATS_KEY, IMAGE_PROCESSING_ENABLED_KEY, MAX_IMAGE_SIZE_KEY, config } from './state.js';
import { makeApiRequest } from './api.js';
import {
    initializeChoices, initializeFlatpickr, updateStartChatButtonState, showSection, getChoicesInstance,
    startChatButton, dateError, chatWindow, initialQuestion, sendChatButton, chatInput,
    clearChatButton, welcomeMessage, toggleQuestionCheckbox, initialQuestionGroup,
    cacheChatsToggle, imageProcessingToggle, maxImageSize, backendSelect,
    loginSubmitButton, webexLoginButton, verifyButton, logoutButton, refreshChatsLink,
    modelSelect, backendSelectMain, downloadChatButton, manageBotsButton, backToChatsButton,
    registerBotButton, toggleLhsButton, mainContainer, mobileMenuOverlay, themeCheckbox,
    conversationalChatSection, downloadHelp, chatSectionTitle, botManagementTitle,
    workflowSubreddit, workflowUrl, updateRedditWorkflowUI
} from './ui.js';
import { handleLogin, handleVerify, handleFullLogout, checkSessionOnLoad, handleBackendChange, switchService } from './auth.js';
import { handleLoadChats, callChatApi, handleDownloadChat, loadModels } from './chat.js';
import { handleRegisterBot, loadBots } from './bot.js';
import { getPostChoicesInstance } from './reddit.js';

const RECENT_CHATS_KEY = 'chat_analyzer_recent_chats';
const MAX_RECENT_CHATS = 10;

function loadRecentChats() {
    const allRecentChats = JSON.parse(localStorage.getItem(RECENT_CHATS_KEY)) || [];
    const recentChats = allRecentChats.filter(s => s.backend === appState.activeBackend);
    const recentChatsContainer = document.getElementById('recentChats');
    const recentChatsList = document.getElementById('recentChatsList');

    if (recentChatsContainer && recentChatsList) {
        if (recentChats.length > 0) {
            recentChatsList.innerHTML = '';
            recentChats.forEach(session => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <a href="#" class="recent-chat-name">${session.chat.label}</a>
                    <button class="go-button">Go</button>
                `;
                
                li.querySelector('.recent-chat-name').addEventListener('click', (e) => {
                    e.preventDefault();
                    restoreSession(session);
                });

                li.querySelector('.go-button').addEventListener('click', (e) => {
                    e.preventDefault();
                    restoreSession(session);
                    startChatButton.click();
                });

                recentChatsList.appendChild(li);
            });
            recentChatsContainer.style.display = 'block';
        } else {
            recentChatsContainer.style.display = 'none';
        }
    }
}

function restoreSession(session) {
    const choices = getChoicesInstance();
    if (choices) {
        choices.setChoiceByValue(session.chat.value);
    }
    modelSelect.value = session.model;
    const datePickerEl = document.getElementById('dateRangePicker');
    if (datePickerEl && datePickerEl._flatpickr) {
        const datePicker = datePickerEl._flatpickr;
        datePicker.setDate([session.startDate, session.endDate], false);
    }
    cacheChatsToggle.checked = session.caching;
    imageProcessingToggle.checked = session.imageProcessing.enabled;
    maxImageSize.value = session.imageProcessing.maxSizeMb;
    toggleQuestionCheckbox.checked = !!session.question;
    initialQuestionGroup.style.display = session.question ? 'block' : 'none';
    initialQuestion.value = session.question || '';
}

function addChatToRecents(session) {
    let recentChats = JSON.parse(localStorage.getItem(RECENT_CHATS_KEY)) || [];
    // Filter out existing chat for the same backend
    recentChats = recentChats.filter(s => !(s.chat.value === session.chat.value && s.backend === session.backend));
    recentChats.unshift(session);
    // This MAX_RECENT_CHATS is now global, not per-backend. This is a design choice.
    if (recentChats.length > MAX_RECENT_CHATS * 2) { // Allow more to store for all backends
        recentChats.pop();
    }
    localStorage.setItem(RECENT_CHATS_KEY, JSON.stringify(recentChats));
    loadRecentChats();
}

function getChatParameters() {
    const datePickerEl = document.getElementById('dateRangePicker');
    const datePickerInstance = datePickerEl ? datePickerEl._flatpickr : null;
    let selectedChat, chatId;

    if (appState.activeBackend === 'reddit') {
        if (workflowUrl.checked) {
            const redditUrlInput = document.getElementById('redditUrlInput');
            const redditUrl = redditUrlInput ? redditUrlInput.value.trim() : '';
            if (!redditUrl) {
                dateError.textContent = 'Please enter a valid Reddit Post URL.';
                return null;
            }
            selectedChat = { value: redditUrl, label: `URL: ${redditUrl}` };
            chatId = redditUrl;
        } else { // Subreddit workflow
            selectedChat = getChoicesInstance().getValue();
            const postChoices = getPostChoicesInstance();
            chatId = postChoices ? postChoices.getValue(true) : null;
        }
    } else {
        selectedChat = getChoicesInstance().getValue();
        chatId = selectedChat ? selectedChat.value : null;
    }

    if (!chatId && selectedChat) {
        chatId = selectedChat.value;
    }
    
    if (!selectedChat && chatId) {
        selectedChat = { value: chatId, label: `ID: ${chatId}` };
    }

    if (!chatId) {
        dateError.textContent = 'Please select a chat to analyze.';
        return null;
    }

    return {
        chatId,
        selectedChat,
        datePickerInstance
    };
}

function showSectionWithLogic(sectionName) {
    showSection(sectionName);
    if (sectionName === 'chatSection') {
        if (!appState.activeBackend) {
            showSectionWithLogic('loginSection');
            return;
        }
        if (chatSectionTitle) {
            chatSectionTitle.textContent = `Analyze Chats (${appState.activeBackend.charAt(0).toUpperCase() + appState.activeBackend.slice(1)})`;
        }
        if (backendSelectMain) {
            backendSelectMain.value = appState.activeBackend;
        }
        handleBackendChange(); // Ensure UI elements like image settings are correctly shown/hidden
        updateRedditWorkflowUI();
        if (!appState.modelsLoaded) {
            loadModels();
        }
        if (appState.chatListStatus[appState.activeBackend] === 'unloaded') {
            handleLoadChats();
        }
        loadRecentChats();
    } else if (sectionName === 'botManagementSection') {
        if (!appState.activeBackend) {
            showSectionWithLogic('loginSection');
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

// Override the showSection function in the auth module
window.showSection = showSectionWithLogic;


document.addEventListener('DOMContentLoaded', () => {

    function closeMobileMenu() {
        if (mainContainer.classList.contains('mobile-menu-open')) {
            mainContainer.classList.remove('mobile-menu-open');
            toggleLhsButton.innerHTML = '&#9776;';
        }
    }

    if (startChatButton) {
        startChatButton.addEventListener('click', () => {
            // Defensive check to prevent state corruption
            if (!Array.isArray(appState.conversation)) {
                appState.conversation = [];
            }
            const datePickerEl = document.getElementById('dateRangePicker');
            const datePickerInstance = datePickerEl ? datePickerEl._flatpickr : null;

            if (!datePickerInstance) {
                dateError.textContent = 'Date picker not initialized.';
                return;
            }
            if (!datePickerInstance.selectedDates) {
                dateError.textContent = 'Date selection not available.';
                return;
            }
            if (datePickerInstance.selectedDates.length !== 2 && !(appState.activeBackend === 'reddit' && workflowUrl.checked)) {
                dateError.textContent = 'Please select a valid date range.';
                return;
            }
            dateError.textContent = '';
            
            const params = getChatParameters();
            if (!params) {
                return;
            }
            const { chatId, selectedChat } = params;

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

            const sessionSnapshot = {
                backend: appState.activeBackend,
                chat: {
                    value: selectedChat.value,
                    label: selectedChat.label
                },
                model: modelSelect.value,
                startDate: datePickerInstance.selectedDates[0] ? datePickerInstance.selectedDates[0].toISOString() : null,
                endDate: datePickerInstance.selectedDates[1] ? datePickerInstance.selectedDates[1].toISOString() : null,
                caching: cacheChatsToggle.checked,
                imageProcessing: {
                    enabled: imageProcessingToggle.checked,
                    maxSizeMb: maxImageSize.value
                },
                question: initialQuestion.value.trim()
            };
            addChatToRecents(sessionSnapshot);

            const chatColumn = document.getElementById('conversationalChatSection');
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }
            if (chatColumn) {
                chatColumn.style.display = 'flex';
                startChatButton.disabled = true;
                if (initialQuestionGroup) {
                    initialQuestionGroup.style.display = 'none';
                }
                callChatApi(question, chatId);
            }
        });
    }

    if (sendChatButton) {
        sendChatButton.addEventListener('click', () => {
            if (appState.chatRequestController) {
                callChatApi(); // This will trigger the abort logic
                return;
            }
            const message = chatInput.value.trim();
            if (message) {
                appState.conversation.push({ role: 'user', content: message });
                const userMessageElem = document.createElement('div');
                userMessageElem.classList.add('chat-message', 'user-message');
                userMessageElem.textContent = message;
                chatWindow.appendChild(userMessageElem);
                chatInput.value = '';
                chatWindow.scrollTop = chatWindow.scrollHeight;
                callChatApi(message, null); // No chatId needed for follow-up
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
                    const url = `/api/clear-session?backend=${appState.activeBackend}`;
                    await makeApiRequest(url, { method: 'POST' }, config.timeouts.logout, clearChatButton, 'session');
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
            if (toggleQuestionCheckbox) {
                toggleQuestionCheckbox.checked = false;
            }
            if (initialQuestionGroup) {
                initialQuestionGroup.style.display = 'none';
            }
            updateStartChatButtonState();
        });
    }
    
    initializeChoices();
    const chatSelect = document.getElementById('chatSelect');
    if (chatSelect) {
        chatSelect.addEventListener('change', () => {
            appState.conversation = [];
            if (chatWindow) chatWindow.innerHTML = '';
            if (conversationalChatSection) conversationalChatSection.style.display = 'none';
            if (welcomeMessage) {
                welcomeMessage.style.display = 'block';
            }
            if (toggleQuestionCheckbox) {
                toggleQuestionCheckbox.checked = false;
            }
            if (initialQuestionGroup) {
                initialQuestionGroup.style.display = 'none';
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
            updateStartChatButtonState();
        });
    }

    if (imageProcessingToggle) {
        const savedEnabled = localStorage.getItem(IMAGE_PROCESSING_ENABLED_KEY);
        imageProcessingToggle.checked = savedEnabled === null ? false : savedEnabled === 'true';
        imageProcessingToggle.addEventListener('change', () => {
            localStorage.setItem(IMAGE_PROCESSING_ENABLED_KEY, imageProcessingToggle.checked);
            updateStartChatButtonState();
        });
    }

    if (maxImageSize) {
        const savedSize = localStorage.getItem(MAX_IMAGE_SIZE_KEY);
        maxImageSize.value = savedSize === null ? '5' : savedSize;
        maxImageSize.addEventListener('change', () => {
            localStorage.setItem(MAX_IMAGE_SIZE_KEY, maxImageSize.value);
            updateStartChatButtonState();
        });
    }

    if (toggleQuestionCheckbox && initialQuestionGroup) {
        toggleQuestionCheckbox.addEventListener('change', () => {
            initialQuestionGroup.style.display = toggleQuestionCheckbox.checked ? 'block' : 'none';
            updateStartChatButtonState();
        });
    }

    if (initialQuestion) {
        initialQuestion.addEventListener('input', updateStartChatButtonState);
    }

    const redditUrlInput = document.getElementById('redditUrlInput');
    if (redditUrlInput) {
        redditUrlInput.addEventListener('input', updateStartChatButtonState);
    }

    if (workflowSubreddit) workflowSubreddit.addEventListener('change', updateRedditWorkflowUI);
    if (workflowUrl) workflowUrl.addEventListener('change', updateRedditWorkflowUI);

    if (backendSelect) backendSelect.addEventListener('change', handleBackendChange);
    if (backendSelectMain) backendSelectMain.addEventListener('change', handleBackendChange);
    if (loginSubmitButton) loginSubmitButton.addEventListener('click', handleLogin);
    if (webexLoginButton) webexLoginButton.addEventListener('click', handleLogin);
    const redditLoginButton = document.getElementById('redditLoginButton');
    if (redditLoginButton) redditLoginButton.addEventListener('click', handleLogin);
    if (verifyButton) verifyButton.addEventListener('click', handleVerify);
    if (logoutButton) logoutButton.addEventListener('click', handleFullLogout);
    if (refreshChatsLink) {
        refreshChatsLink.addEventListener('click', (e) => {
            e.preventDefault();
            const backend = appState.activeBackend;
            if (backend) {
                const cacheKey = `${backend}-chats`;
                sessionStorage.removeItem(cacheKey);
            }
            handleLoadChats();
        });
    }
    
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

    // Ensure download formats include html and zip if dropdown exists
    if (downloadFormat) {
        const ensureOption = (val, label) => {
            if (![...downloadFormat.options].some(o => o.value === val)) {
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = label;
                downloadFormat.appendChild(opt);
            }
        };
        ensureOption('txt', 'Text (.txt)');
        ensureOption('pdf', 'PDF (.pdf)');
        ensureOption('html', 'HTML (.html)');
        ensureOption('zip', 'Bundle (.zip)');

        // Small, crisp UX note about image exports
        if (downloadHelp) {
            const updateHelp = () => {
                const val = downloadFormat.value;
                if (val === 'html') {
                    downloadHelp.textContent = 'HTML export includes images inline (self‑contained file).';
                } else if (val === 'zip') {
                    downloadHelp.textContent = 'ZIP export includes transcript, images/, HTML, and a manifest.json.';
                } else if (val === 'pdf') {
                    downloadHelp.textContent = 'PDF export is text‑only.';
                } else {
                    downloadHelp.textContent = 'Text export is text‑only. Use HTML or ZIP to include images.';
                }
            };
            // initialize and bind changes
            updateHelp();
            downloadFormat.addEventListener('change', updateHelp);
        }
    }
    
    checkSessionOnLoad();

    if (manageBotsButton) manageBotsButton.addEventListener('click', () => {
        showSectionWithLogic('botManagementSection');
    });
    if (backToChatsButton) backToChatsButton.addEventListener('click', () => showSectionWithLogic('chatSection'));
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
        const flatpickrTheme = document.getElementById('flatpickr-theme');

        const applyTheme = (isDark) => {
            if (isDark) {
                document.body.classList.add('dark-theme');
                if (flatpickrTheme) flatpickrTheme.disabled = false;
                localStorage.setItem('theme', 'dark-theme');
            } else {
                document.body.classList.remove('dark-theme');
                if (flatpickrTheme) flatpickrTheme.disabled = true;
                localStorage.setItem('theme', 'light-theme');
            }
        };

        themeCheckbox.addEventListener('change', () => {
            applyTheme(themeCheckbox.checked);
        });

        // Apply saved theme on load
        const savedTheme = localStorage.getItem('theme');
        const isDark = savedTheme === 'dark-theme';
        themeCheckbox.checked = isDark;
        applyTheme(isDark);
    }
});
