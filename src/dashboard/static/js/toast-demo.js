/**
 * Toast Notification Demo
 *
 * Demonstrates all toast notification types and features.
 * This file is optional and can be included on specific pages for testing.
 */

(function() {
    'use strict';

    /**
     * Show demo toasts with all types
     */
    function showDemoToasts() {
        setTimeout(() => {
            toast.info('Welcome to Team Metrics Dashboard', {
                description: 'All metrics are up to date'
            });
        }, 500);

        setTimeout(() => {
            toast.success('Data collection completed', {
                description: '1,234 metrics collected successfully'
            });
        }, 2000);

        setTimeout(() => {
            toast.warning('Cache is 2 hours old', {
                description: 'Consider reloading for latest data'
            });
        }, 3500);

        // Error doesn't auto-dismiss
        setTimeout(() => {
            toast.error('GitHub rate limit exceeded', {
                description: 'Retry in 15 minutes'
            });
        }, 5000);
    }

    /**
     * Show loading toast example
     */
    function showLoadingExample() {
        const loadingToast = toast.loading('Collecting metrics from GitHub...');

        // Simulate async operation
        setTimeout(() => {
            toast.dismiss(loadingToast);
            toast.success('Collection completed', {
                description: '156 PRs processed'
            });
        }, 3000);
    }

    /**
     * Clear all toasts
     */
    function clearToasts() {
        toast.clear();
        toast.info('All notifications cleared');
    }

    // Export demo functions
    window.toastDemo = {
        showAll: showDemoToasts,
        showLoading: showLoadingExample,
        clear: clearToasts
    };

    // Add demo buttons to page if #toast-demo-controls exists
    document.addEventListener('DOMContentLoaded', function() {
        const controls = document.getElementById('toast-demo-controls');
        if (!controls) return;

        controls.innerHTML = `
            <div style="padding: 20px; background: var(--bg-secondary); border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Toast Notification Demo</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="toast.success('Success message')" class="btn-primary">
                        Success
                    </button>
                    <button onclick="toast.error('Error message')" class="btn-secondary">
                        Error
                    </button>
                    <button onclick="toast.warning('Warning message')" class="btn-secondary">
                        Warning
                    </button>
                    <button onclick="toast.info('Info message')" class="btn-secondary">
                        Info
                    </button>
                    <button onclick="toastDemo.showLoading()" class="btn-secondary">
                        Loading
                    </button>
                    <button onclick="toastDemo.showAll()" class="btn-secondary">
                        Show All Types
                    </button>
                    <button onclick="toast.clear()" class="btn-secondary">
                        Clear All
                    </button>
                </div>
            </div>
        `;
    });
})();
