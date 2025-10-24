/**
 * Toast Notification System
 * 
 * Provides beautiful toast notifications for user feedback
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.initialize();
    }

    initialize() {
        // Create container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms (0 for no auto-dismiss)
     * @param {string} title - Optional title
     */
    show(message, type = 'info', duration = 3000, title = null) {
        const toast = this.createToast(message, type, title);
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
        });

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                this.dismiss(toast);
            }, duration);
        }

        return toast;
    }

    createToast(message, type, title) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            info: 'i',
            warning: '!'
        };

        const titles = {
            success: title || 'Success',
            error: title || 'Error',
            info: title || 'Info',
            warning: title || 'Warning'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                <div class="toast-title">${titles[type]}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Close">×</button>
        `;

        // Add close button functionality
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.dismiss(toast));

        return toast;
    }

    dismiss(toast) {
        toast.classList.add('removing');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300); // Match animation duration
    }

    dismissAll() {
        this.toasts.forEach(toast => this.dismiss(toast));
    }

    // Convenience methods
    success(message, title = null, duration = 3000) {
        return this.show(message, 'success', duration, title);
    }

    error(message, title = null, duration = 5000) {
        return this.show(message, 'error', duration, title);
    }

    info(message, title = null, duration = 3000) {
        return this.show(message, 'info', duration, title);
    }

    warning(message, title = null, duration = 4000) {
        return this.show(message, 'warning', duration, title);
    }
}

// Create singleton instance
export const toast = new ToastManager();

// For debugging in console
if (typeof window !== 'undefined') {
    window._toast = toast;
}

