import { appState } from './state.js';
import { getPostChoicesInstance } from './reddit.js';
import { buttonStateManager } from './buttonStateManager.js';
import { createChoices } from './choicesWrapper.js';
import { toast } from './toast.js';

// Re-export toast for convenience
export { toast };

// --- DOM Elements ---
export const loginSection = document.getElementById('loginSection');
export const verificationSection = document.getElementById('verificationSection');
export const chatSection = document.getElementById('chatSection');
export const backendSelect = document.getElementById('backendSelect');
export const telegramLoginForm = document.getElementById('telegramLoginForm');
export const webexLoginContainer = document.getElementById('webexLoginContainer');
export const webexLoginButton = document.getElementById('webexLoginButton');
export const phoneInput = document.getElementById('phone');
export const loginSubmitButton = document.getElementById('loginSubmitButton');
export const loginError = document.getElementById('loginError');
export const verificationCodeInput = document.getElementById('verificationCode');
export const passwordField = document.getElementById('passwordField');
export const passwordInput = document.getElementById('password');
export const verifyButton = document.getElementById('verifyButton');
export const verificationError = document.getElementById('verificationError');
export const chatSelect = document.getElementById('chatSelect');
export const modelSelect = document.getElementById('modelSelect');
export const modelError = document.getElementById('modelError');
export const dateError = document.getElementById('dateError');
export const chatLoadingError = document.getElementById('chatLoadingError');
export const refreshChatsLink = document.getElementById('refreshChatsLink');
export const lastUpdatedTime = document.getElementById('lastUpdatedTime');
export const logoutButton = document.getElementById('logoutButton');
export const cacheChatsToggle = document.getElementById('cacheChatsToggle');
export const chatSectionTitle = document.getElementById('chatSectionTitle');
export const backendSelectMain = document.getElementById('backendSelect-main');
export const conversationalChatSection = document.getElementById('conversationalChatSection');
export const chatWindow = document.getElementById('chatWindow');
export const chatInput = document.getElementById('chatInput');
export const sendChatButton = document.getElementById('sendChatButton');
export const clearChatButton = document.getElementById('clearChatButton');
export const startChatButton = document.getElementById('startChatButton');
export const initialQuestion = document.getElementById('initialQuestion');
export const initialQuestionGroup = document.getElementById('initialQuestionGroup');
export const toggleQuestionCheckbox = document.getElementById('toggleQuestionCheckbox');
export const downloadChatButton = document.getElementById('downloadChatButton');
export const downloadFormat = document.getElementById('downloadFormat');
export const downloadHelp = document.getElementById('downloadHelp');
export const botManagementSection = document.getElementById('botManagementSection');
export const manageBotsButton = document.getElementById('manageBotsButton');
export const backToChatsButton = document.getElementById('backToChatsButton');
export const botManagementTitle = document.getElementById('botManagementTitle');
export const botNameInput = document.getElementById('botName');
export const botIdInput = document.getElementById('botId');
export const botTokenInput = document.getElementById('botToken');
export const webhookUrlInput = document.getElementById('webhookUrl');
export const registerBotButton = document.getElementById('registerBotButton');
export const botManagementError = document.getElementById('botManagementError');
export const registeredBotsList = document.getElementById('registeredBotsList');
export const welcomeMessage = document.getElementById('welcomeMessage');
export const toggleLhsButton = document.getElementById('toggleLhsButton');
export const mainContainer = document.querySelector('.main-container');
export const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
export const themeCheckbox = document.getElementById('theme-checkbox');
export const imageSettings = document.getElementById('imageSettings');
export const imageProcessingToggle = document.getElementById('imageProcessingToggle');
export const maxImageSize = document.getElementById('maxImageSize');
export const redditWorkflowGroup = document.getElementById('redditWorkflowGroup');
export const redditSubredditGroup = document.getElementById('redditSubredditGroup');
export const redditUrlGroup = document.getElementById('redditUrlGroup');
export const workflowSubreddit = document.getElementById('workflowSubreddit');
export const workflowUrl = document.getElementById('workflowUrl');


let choicesInstance = null;
let flatpickrInstance = null;

export function initializeChoices() {
    if (chatSelect) {
        choicesInstance = createChoices(chatSelect, {
            itemSelectText: '',
            removeItemButton: true,
            searchPlaceholderValue: "Search for a chat...",
        });
        choicesInstance.disable();
    }
}

export function getChoicesInstance() {
    return choicesInstance;
}

export function getFlatpickrInstance() {
    return flatpickrInstance;
}

export function setLoadingState(buttonElement, isLoading, loadingText = 'Processing...') {
    if (!buttonElement) return;

    if (buttonElement.id === 'sendChatButton') {
        if (isLoading) {
            buttonElement.dataset.originalText = buttonElement.textContent;
            buttonElement.textContent = 'Stop';
            buttonElement.disabled = false; // Keep it enabled to be clickable
            buttonElement.classList.add('stop-button');
        } else {
            buttonElement.textContent = buttonElement.dataset.originalText || 'Send';
            buttonElement.disabled = false;
            buttonElement.classList.remove('stop-button');
            delete buttonElement.dataset.originalText;
        }
    } else {
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
}

export function clearErrors() {
    if (loginError) loginError.textContent = '';
    if (verificationError) verificationError.textContent = '';
    if (dateError) dateError.textContent = '';
    if (chatLoadingError) chatLoadingError.textContent = '';
    if (modelError) modelError.textContent = '';
    if (botManagementError) botManagementError.textContent = '';
}

export function updateRedditWorkflowUI() {
    const chatSelectGroup = document.getElementById('chatSelectGroup');
    const dateRangeGroup = document.getElementById('dateRangeGroup');
    const redditPostSelectGroup = document.getElementById('redditPostSelectGroup');

    if (appState.activeBackend !== 'reddit') {
        redditWorkflowGroup.style.display = 'none';
        redditSubredditGroup.style.display = 'none';
        redditUrlGroup.style.display = 'none';
        if (chatSelectGroup) chatSelectGroup.style.display = 'block';
        if (dateRangeGroup) dateRangeGroup.style.display = 'block';
        if (redditPostSelectGroup) redditPostSelectGroup.style.display = 'none';
        return;
    }
    
    redditWorkflowGroup.style.display = 'block';
    const selectedWorkflow = document.querySelector('input[name="reddit-workflow"]:checked').value;

    if (selectedWorkflow === 'subreddit') {
        if (chatSelectGroup) chatSelectGroup.style.display = 'block';
        if (redditSubredditGroup) redditSubredditGroup.style.display = 'block';
        if (redditUrlGroup) redditUrlGroup.style.display = 'none';
        if (dateRangeGroup) dateRangeGroup.style.display = 'none';
    } else { // url
        if (chatSelectGroup) chatSelectGroup.style.display = 'none';
        if (redditSubredditGroup) redditSubredditGroup.style.display = 'none';
        if (redditUrlGroup) redditUrlGroup.style.display = 'block';
        if (dateRangeGroup) dateRangeGroup.style.display = 'none';
    }
    updateStartChatButtonState();
}


/**
 * Initialize the button state manager with required elements and instances
 * Call this after DOM is loaded and instances are created
 */
export function initializeButtonStateManager() {
    buttonStateManager.initialize(
        {
            startChatButton,
            downloadChatButton,
            initialQuestion,
            toggleQuestionCheckbox
        },
        {
            flatpickr: flatpickrInstance,
            choices: choicesInstance,
            postChoices: getPostChoicesInstance()
        }
    );
}

/**
 * Update button states based on current form state
 * Delegates to buttonStateManager for centralized validation logic
 */
export function updateStartChatButtonState() {
    // Update the post choices instance in case it changed
    buttonStateManager.instances.postChoices = getPostChoicesInstance();
    
    // Trigger update
    buttonStateManager.update();
}

export function initializeFlatpickr() {
    const dateRangePicker = document.getElementById('dateRangePicker');
    flatpickrInstance = flatpickr(dateRangePicker, {
        mode: "range",
        dateFormat: "Y-m-d",
        defaultDate: ["today", "today"],
        onChange: function(selectedDates, dateStr, instance) {
            updateStartChatButtonState();
        }
    });
    
    // Initialize button state manager after instances are created
    initializeButtonStateManager();
    
    // Ensure the button state is updated after initialization
    // Use a small delay to ensure the instance is fully ready on mobile
    setTimeout(() => {
        updateStartChatButtonState();
    }, 100);
}

export function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
    });

    const sectionToShow = document.getElementById(sectionName);
    if (sectionToShow) {
        sectionToShow.classList.add('active');
    }
    
    appState.activeSection = sectionName;
    clearErrors();
}

export function formatDate(date) {
    if (!date) return null;
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}
