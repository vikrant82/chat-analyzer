/**
 * Choices.js Wrapper
 * 
 * Provides a consistent interface for Choices.js dropdowns with
 * built-in Android compatibility and simplified event handling.
 */

class ChoicesWrapper {
    constructor(element, options = {}) {
        if (!element) {
            throw new Error('ChoicesWrapper requires a valid DOM element');
        }

        this.element = element;
        this.eventHandlers = [];
        
        // Default options optimized for mobile compatibility
        const defaultOptions = {
            searchEnabled: true,
            itemSelectText: '',
            shouldSort: false,
            removeItemButton: false
        };

        // Create Choices.js instance
        this.instance = new Choices(element, {
            ...defaultOptions,
            ...options
        });
    }

    /**
     * Register onChange handler that works across all browsers
     * Automatically handles Android compatibility by listening to multiple events
     */
    onChange(callback) {
        // Events to listen for (Android compatibility)
        const eventTypes = ['change', 'addItem', 'choice'];
        
        eventTypes.forEach(eventType => {
            this.element.addEventListener(eventType, callback);
            this.eventHandlers.push({ eventType, callback });
        });
        
        return this; // Allow chaining
    }

    /**
     * Register a handler for when an item is removed
     */
    onRemove(callback) {
        this.element.addEventListener('removeItem', callback);
        this.eventHandlers.push({ eventType: 'removeItem', callback });
        return this;
    }

    /**
     * Get the currently selected value
     * @param {boolean} valueOnly - If true, returns just the value (not the object)
     */
    getValue(valueOnly = false) {
        return this.instance.getValue(valueOnly);
    }

    /**
     * Set choices programmatically
     */
    setChoices(choices, value = 'value', label = 'label', replaceChoices = false) {
        return this.instance.setChoices(choices, value, label, replaceChoices);
    }

    /**
     * Set value by value
     */
    setChoiceByValue(value) {
        return this.instance.setChoiceByValue(value);
    }

    /**
     * Clear all choices
     */
    clearChoices() {
        this.instance.clearChoices();
        return this;
    }

    /**
     * Clear selected value(s)
     */
    clearStore() {
        this.instance.clearStore();
        return this;
    }

    /**
     * Enable the dropdown
     */
    enable() {
        this.instance.enable();
        return this;
    }

    /**
     * Disable the dropdown
     */
    disable() {
        this.instance.disable();
        return this;
    }

    /**
     * Check if dropdown is disabled
     */
    isDisabled() {
        return this.instance._isSelectElement && this.element.disabled;
    }

    /**
     * Remove a choice by value
     */
    removeActiveItemsByValue(value) {
        this.instance.removeActiveItemsByValue(value);
        return this;
    }

    /**
     * Show loading state
     */
    showLoadingText(text = 'Loading...') {
        this.clearStore();
        this.setChoices([{ value: '', label: text, disabled: true }], 'value', 'label', true);
        return this;
    }

    /**
     * Show error state
     */
    showErrorText(text = 'Failed to load') {
        this.clearStore();
        this.setChoices([{ value: '', label: text, disabled: true }], 'value', 'label', true);
        this.enable(); // Enable so user can try refresh
        return this;
    }

    /**
     * Show empty state
     */
    showEmptyText(text = 'No items found') {
        this.clearStore();
        this.setChoices([{ value: '', label: text, disabled: true }], 'value', 'label', true);
        return this;
    }

    /**
     * Populate with grouped choices (for Reddit subreddits, etc.)
     */
    setGroupedChoices(groupedData) {
        const choices = Object.keys(groupedData)
            .filter(group => groupedData[group].length > 0)
            .map(group => ({
                label: group,
                choices: groupedData[group]
            }));
        
        this.setChoices(choices, 'value', 'label', false);
        return this;
    }

    /**
     * Clean up event listeners and destroy instance
     */
    destroy() {
        // Remove all registered event handlers
        this.eventHandlers.forEach(({ eventType, callback }) => {
            this.element.removeEventListener(eventType, callback);
        });
        this.eventHandlers = [];

        // Destroy Choices.js instance
        if (this.instance) {
            this.instance.destroy();
            this.instance = null;
        }
    }

    /**
     * Get the underlying Choices.js instance
     * (Use sparingly - prefer wrapper methods)
     */
    getRawInstance() {
        return this.instance;
    }
}

/**
 * Factory function for creating ChoicesWrapper instances
 */
export function createChoices(element, options = {}) {
    return new ChoicesWrapper(element, options);
}

/**
 * Export the class as well for advanced use cases
 */
export { ChoicesWrapper };

