import { appState } from './state.js';

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

let choicesInstance = null;

export function initializeChoices() {
    if (chatSelect) {
        choicesInstance = new Choices(chatSelect, {
            searchEnabled: true,
            itemSelectText: '',
            removeItemButton: true,
            shouldSort: false,
            searchPlaceholderValue: "Search for a chat...",
        });
        choicesInstance.disable();
    }
}

export function getChoicesInstance() {
    return choicesInstance;
}

export function setLoadingState(buttonElement, isLoading, loadingText = 'Processing...') {
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

export function clearErrors() {
    if (loginError) loginError.textContent = '';
    if (verificationError) verificationError.textContent = '';
    if (dateError) dateError.textContent = '';
    if (chatLoadingError) chatLoadingError.textContent = '';
    if (modelError) modelError.textContent = '';
    if (botManagementError) botManagementError.textContent = '';
}

export function updateStartChatButtonState() {
    if (!startChatButton) return;
    const datePicker = document.getElementById('dateRangePicker');
    const validDateSelected = datePicker && datePicker._flatpickr && datePicker._flatpickr.selectedDates.length === 2;
    const validChatSelected = choicesInstance && choicesInstance.getValue(true) != null && choicesInstance.getValue(true) !== "";
    const validModelSelected = modelSelect && modelSelect.value && !modelSelect.options[modelSelect.selectedIndex]?.disabled;
    
    const coreRequirementsMet = appState.chatListStatus[appState.activeBackend] === 'loaded' && appState.modelsLoaded && validChatSelected && validModelSelected && validDateSelected;

    const questionToggled = toggleQuestionCheckbox && toggleQuestionCheckbox.checked;
    const questionText = initialQuestion && initialQuestion.value.trim();
    const questionRequirementMet = !questionToggled || (questionToggled && questionText !== '');

    startChatButton.disabled = !coreRequirementsMet || !questionRequirementMet;

    if (downloadChatButton) {
        downloadChatButton.disabled = !validChatSelected || !validDateSelected;
    }
    
    if (initialQuestion) {
        initialQuestion.disabled = !coreRequirementsMet;
    }
}

export function initializeFlatpickr() {
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