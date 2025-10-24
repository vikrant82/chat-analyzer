/**
 * Button State Manager
 * 
 * Centralized logic for determining when buttons should be enabled/disabled.
 * Uses validator pattern for clear, testable, and maintainable state checks.
 */

import { appState } from './state.js';

class ButtonStateManager {
    constructor() {
        this.elements = {
            startChatButton: null,
            downloadChatButton: null,
            initialQuestion: null,
            toggleQuestionCheckbox: null
        };
        
        this.instances = {
            flatpickr: null,
            choices: null,
            postChoices: null
        };
    }

    /**
     * Initialize with required DOM elements and library instances
     */
    initialize(elements, instances) {
        this.elements = { ...this.elements, ...elements };
        this.instances = { ...this.instances, ...instances };
    }

    /**
     * Validator: Check if valid date range is selected
     */
    isDateRangeValid() {
        const { flatpickr } = this.instances;
        return flatpickr && 
               flatpickr.selectedDates && 
               flatpickr.selectedDates.length === 2;
    }

    /**
     * Validator: Check if valid chat is selected (handles all backends)
     */
    isChatSelected() {
        const { choices, postChoices } = this.instances;
        
        if (appState.activeBackend === 'reddit') {
            const selectedWorkflow = document.querySelector('input[name="reddit-workflow"]:checked')?.value;
            
            if (selectedWorkflow === 'subreddit') {
                // Both subreddit and post must be selected
                const subredditSelected = choices && choices.getValue(true);
                const postSelected = postChoices && postChoices.getValue(true);
                return !!(subredditSelected && postSelected);
            } else if (selectedWorkflow === 'url') {
                // Valid Reddit URL must be entered
                const redditUrlInput = document.getElementById('redditUrlInput');
                const url = redditUrlInput ? redditUrlInput.value.trim() : '';
                return url.includes('comments/');
            }
            return false;
        } else {
            // Telegram or Webex
            const chatId = choices && choices.getValue(true);
            return chatId != null && chatId !== "";
        }
    }

    /**
     * Validator: Check if valid model is selected
     */
    isModelSelected() {
        const modelSelect = document.getElementById('modelSelect');
        if (!modelSelect) return false;
        
        const hasValue = modelSelect.value && modelSelect.value !== '';
        const notDisabled = modelSelect.options[modelSelect.selectedIndex] && 
                           !modelSelect.options[modelSelect.selectedIndex].disabled;
        return hasValue && notDisabled;
    }

    /**
     * Validator: Check if chats are loaded
     */
    areChatsLoaded() {
        return appState.chatListStatus[appState.activeBackend] === 'loaded';
    }

    /**
     * Validator: Check if models are loaded
     */
    areModelsLoaded() {
        return appState.modelsLoaded;
    }

    /**
     * Validator: Check if optional question field is valid
     */
    isQuestionValid() {
        const { toggleQuestionCheckbox, initialQuestion } = this.elements;
        
        if (!toggleQuestionCheckbox || !initialQuestion) return true;
        
        const isToggled = toggleQuestionCheckbox.checked;
        if (!isToggled) return true;
        
        const hasText = initialQuestion.value.trim() !== '';
        return hasText;
    }

    /**
     * Check if core requirements are met for starting a chat
     */
    canStartChat() {
        // Basic requirements for all backends
        let requirements = [
            this.areChatsLoaded(),
            this.areModelsLoaded(),
            this.isChatSelected(),
            this.isModelSelected(),
            this.isQuestionValid()
        ];

        // Date selection only required for non-Reddit backends
        if (appState.activeBackend !== 'reddit') {
            requirements.push(this.isDateRangeValid());
        }

        return requirements.every(check => check === true);
    }

    /**
     * Check if download is allowed
     */
    canDownload() {
        let requirements = [this.isChatSelected()];
        
        // Date selection required for non-Reddit backends
        if (appState.activeBackend !== 'reddit') {
            requirements.push(this.isDateRangeValid());
        }
        
        return requirements.every(check => check === true);
    }

    /**
     * Main update function - call this whenever state changes
     */
    update() {
        const { startChatButton, downloadChatButton, initialQuestion } = this.elements;
        
        // Update Start Chat button
        if (startChatButton) {
            startChatButton.disabled = !this.canStartChat();
        }
        
        // Update Download Chat button
        if (downloadChatButton) {
            downloadChatButton.disabled = !this.canDownload();
        }
        
        // Update initial question textarea
        if (initialQuestion) {
            const coreReqsMet = this.areChatsLoaded() && 
                               this.areModelsLoaded() && 
                               this.isChatSelected() && 
                               this.isModelSelected();
            
            // Add date requirement for non-Reddit
            const dateReqMet = appState.activeBackend === 'reddit' || this.isDateRangeValid();
            
            initialQuestion.disabled = !(coreReqsMet && dateReqMet);
        }
    }

    /**
     * Debug helper: Get validation status
     */
    getValidationStatus() {
        return {
            chatsLoaded: this.areChatsLoaded(),
            modelsLoaded: this.areModelsLoaded(),
            chatSelected: this.isChatSelected(),
            modelSelected: this.isModelSelected(),
            dateRangeValid: this.isDateRangeValid(),
            questionValid: this.isQuestionValid(),
            canStartChat: this.canStartChat(),
            canDownload: this.canDownload()
        };
    }
}

// Create singleton instance
export const buttonStateManager = new ButtonStateManager();

// For debugging in console
if (typeof window !== 'undefined') {
    window._buttonStateManager = buttonStateManager;
}

