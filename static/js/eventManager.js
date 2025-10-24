/**
 * Centralized Event Listener Management
 * 
 * Prevents duplicate event listeners, provides cleanup mechanism,
 * and helps debug event-related issues.
 */

class EventManager {
    constructor() {
        // Map structure: 'context:elementId:eventType' -> { element, event, handler }
        this.listeners = new Map();
    }

    /**
     * Register an event listener with automatic duplicate prevention
     * @param {HTMLElement} element - DOM element to attach listener to
     * @param {string} eventType - Event type (e.g., 'click', 'change')
     * @param {Function} handler - Event handler function
     * @param {string} context - Context for grouping (e.g., 'reddit', 'telegram', 'global')
     */
    register(element, eventType, handler, context = 'global') {
        if (!element || !element.id) {
            console.warn('EventManager: Element must have an ID for tracking');
            // Fall back to direct registration for elements without IDs
            element.addEventListener(eventType, handler);
            return;
        }

        const key = `${context}:${element.id}:${eventType}`;
        
        // Remove old listener if it exists to prevent duplicates
        if (this.listeners.has(key)) {
            const old = this.listeners.get(key);
            old.element.removeEventListener(old.event, old.handler);
        }
        
        // Register new listener
        element.addEventListener(eventType, handler);
        this.listeners.set(key, { element, event: eventType, handler, context });
    }

    /**
     * Register multiple event types for the same element and handler
     * Useful for Android compatibility (e.g., 'change', 'addItem', 'choice')
     */
    registerMultiple(element, eventTypes, handler, context = 'global') {
        eventTypes.forEach(eventType => {
            this.register(element, eventType, handler, context);
        });
    }

    /**
     * Remove specific listener
     */
    remove(element, eventType, context = 'global') {
        if (!element || !element.id) return;
        
        const key = `${context}:${element.id}:${eventType}`;
        if (this.listeners.has(key)) {
            const { element, event, handler } = this.listeners.get(key);
            element.removeEventListener(event, handler);
            this.listeners.delete(key);
        }
    }

    /**
     * Clean up all listeners for a given context
     * Useful when switching backends or navigating between sections
     */
    cleanup(context) {
        const keysToDelete = [];
        
        for (const [key, { element, event, handler, context: listenerContext }] of this.listeners) {
            if (listenerContext === context) {
                element.removeEventListener(event, handler);
                keysToDelete.push(key);
            }
        }
        
        keysToDelete.forEach(key => this.listeners.delete(key));
    }

    /**
     * Clean up all listeners (use on app shutdown or full reset)
     */
    cleanupAll() {
        for (const { element, event, handler } of this.listeners.values()) {
            element.removeEventListener(event, handler);
        }
        this.listeners.clear();
    }

    /**
     * Debug helper: Get all registered listeners
     */
    getActiveListeners() {
        return Array.from(this.listeners.keys());
    }

    /**
     * Debug helper: Count listeners by context
     */
    countByContext() {
        const counts = {};
        for (const { context } of this.listeners.values()) {
            counts[context] = (counts[context] || 0) + 1;
        }
        return counts;
    }
}

// Create singleton instance
export const eventManager = new EventManager();

// For debugging in console
if (typeof window !== 'undefined') {
    window._eventManager = eventManager;
}

