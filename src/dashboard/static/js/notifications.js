/**
 * Toast Notification System
 *
 * A lightweight, dependency-free toast notification system for user feedback.
 *
 * Usage:
 *   toast.success('Data refreshed successfully');
 *   toast.error('Failed to load data');
 *   toast.warning('Cache is older than 2 hours');
 *   toast.info('Using cached data');
 *
 * Features:
 * - Auto-dismiss after 5 seconds (configurable)
 * - Stack multiple toasts
 * - Smooth animations
 * - Accessible (ARIA live regions)
 * - Theme-aware (respects dark mode)
 */

(function (window) {
    'use strict';

    // Toast configuration
    const TOAST_DURATION = 5000; // 5 seconds
    const TOAST_ANIMATION_DURATION = 300; // 0.3 seconds
    const MAX_TOASTS = 5; // Maximum visible toasts

    // Toast container reference
    let toastContainer = null;

    /**
     * Initialize toast container
     */
    function initToastContainer() {
        if (toastContainer) {
            return toastContainer;
        }

        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container';
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.setAttribute('aria-atomic', 'false');
        document.body.appendChild(toastContainer);

        return toastContainer;
    }

    /**
     * Create a toast element
     *
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, warning, info)
     * @param {Object} options - Additional options
     * @returns {HTMLElement} Toast element
     */
    function createToast(message, type, options = {}) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

        // Icon mapping
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        const icon = icons[type] || 'ℹ';

        // Build toast HTML
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                <div class="toast-message">${escapeHtml(message)}</div>
                ${options.description ? `<div class="toast-description">${escapeHtml(options.description)}</div>` : ''}
            </div>
            <button class="toast-close" aria-label="Close notification" type="button">×</button>
        `;

        // Add close button handler
        const closeButton = toast.querySelector('.toast-close');
        closeButton.addEventListener('click', () => {
            dismissToast(toast);
        });

        return toast;
    }

    /**
     * Show a toast notification
     *
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, warning, info)
     * @param {Object} options - Additional options
     */
    function showToast(message, type, options = {}) {
        const container = initToastContainer();

        // Remove oldest toast if at max capacity
        const existingToasts = container.querySelectorAll('.toast');
        if (existingToasts.length >= MAX_TOASTS) {
            dismissToast(existingToasts[0]);
        }

        // Create and add toast
        const toast = createToast(message, type, options);
        container.appendChild(toast);

        // Trigger enter animation
        setTimeout(() => {
            toast.classList.add('toast-show');
        }, 10);

        // Auto-dismiss
        const duration = options.duration !== undefined ? options.duration : TOAST_DURATION;
        if (duration > 0) {
            setTimeout(() => {
                dismissToast(toast);
            }, duration);
        }

        return toast;
    }

    /**
     * Dismiss a toast
     *
     * @param {HTMLElement} toast - Toast element to dismiss
     */
    function dismissToast(toast) {
        if (!toast || !toast.parentNode) {
            return;
        }

        // Trigger exit animation
        toast.classList.remove('toast-show');
        toast.classList.add('toast-hide');

        // Remove from DOM after animation
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, TOAST_ANIMATION_DURATION);
    }

    /**
     * Clear all toasts
     */
    function clearAllToasts() {
        const container = initToastContainer();
        const toasts = container.querySelectorAll('.toast');
        toasts.forEach(dismissToast);
    }

    /**
     * Escape HTML to prevent XSS
     *
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public API
    const toast = {
        /**
         * Show a success toast
         *
         * @param {string} message - Success message
         * @param {Object} options - Additional options
         */
        success: function (message, options = {}) {
            return showToast(message, 'success', options);
        },

        /**
         * Show an error toast
         *
         * @param {string} message - Error message
         * @param {Object} options - Additional options
         */
        error: function (message, options = {}) {
            return showToast(message, 'error', { duration: 0, ...options }); // Errors don't auto-dismiss
        },

        /**
         * Show a warning toast
         *
         * @param {string} message - Warning message
         * @param {Object} options - Additional options
         */
        warning: function (message, options = {}) {
            return showToast(message, 'warning', { duration: 7000, ...options }); // Warnings last longer
        },

        /**
         * Show an info toast
         *
         * @param {string} message - Info message
         * @param {Object} options - Additional options
         */
        info: function (message, options = {}) {
            return showToast(message, 'info', options);
        },

        /**
         * Show a loading toast (persists until dismissed)
         *
         * @param {string} message - Loading message
         * @returns {HTMLElement} Toast element (call dismissToast to remove)
         */
        loading: function (message) {
            const toast = showToast(message, 'info', { duration: 0 });
            toast.classList.add('toast-loading');
            // Add spinner
            const icon = toast.querySelector('.toast-icon');
            icon.innerHTML = '<div class="toast-spinner"></div>';
            return toast;
        },

        /**
         * Dismiss a specific toast
         *
         * @param {HTMLElement} toast - Toast element to dismiss
         */
        dismiss: dismissToast,

        /**
         * Clear all toasts
         */
        clear: clearAllToasts
    };

    // Expose to global scope
    window.toast = toast;

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToastContainer);
    } else {
        initToastContainer();
    }

})(window);
