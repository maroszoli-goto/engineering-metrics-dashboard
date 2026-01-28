/**
 * Loading States Utility
 *
 * Manages loading indicators, skeleton screens, and progress bars.
 *
 * Usage:
 *   loading.show(element);               // Show spinner in element
 *   loading.hide(element);               // Hide spinner
 *   loading.showSkeleton(element);       // Show skeleton screen
 *   loading.showProgress(element, 45);   // Show progress bar at 45%
 *   loading.fullscreen('Loading...');    // Fullscreen loading overlay
 */

(function (window) {
    'use strict';

    /**
     * Show loading spinner in element
     *
     * @param {HTMLElement|string} target - Element or selector
     * @param {Object} options - Loading options
     */
    function showLoading(target, options = {}) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        // Create overlay if it doesn't exist
        let overlay = element.querySelector('.loading-container-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-container-overlay';
            overlay.innerHTML = `
                <div class="spinner-with-label">
                    <div class="spinner ${options.size ? 'spinner-' + options.size : ''}"></div>
                    ${options.label ? `<div class="spinner-label">${escapeHtml(options.label)}</div>` : ''}
                </div>
            `;

            // Add loading-container class to element if not present
            if (!element.classList.contains('loading-container')) {
                element.classList.add('loading-container');
            }

            element.appendChild(overlay);
        }

        // Show overlay
        setTimeout(() => {
            overlay.classList.add('active');
        }, 10);

        return overlay;
    }

    /**
     * Hide loading spinner
     *
     * @param {HTMLElement|string} target - Element or selector
     */
    function hideLoading(target) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        const overlay = element.querySelector('.loading-container-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    /**
     * Show fullscreen loading overlay
     *
     * @param {string} label - Loading message
     * @returns {HTMLElement} Overlay element
     */
    function showFullscreen(label = 'Loading...') {
        let overlay = document.getElementById('fullscreen-loading-overlay');

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'fullscreen-loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="spinner-with-label">
                    <div class="spinner spinner-large"></div>
                    <div class="spinner-label">${escapeHtml(label)}</div>
                </div>
            `;
            document.body.appendChild(overlay);
        } else {
            // Update label if overlay already exists
            const labelEl = overlay.querySelector('.spinner-label');
            if (labelEl) {
                labelEl.textContent = label;
            }
        }

        // Show overlay
        setTimeout(() => {
            overlay.classList.add('active');
        }, 10);

        return overlay;
    }

    /**
     * Hide fullscreen loading overlay
     */
    function hideFullscreen() {
        const overlay = document.getElementById('fullscreen-loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    /**
     * Show skeleton screen
     *
     * @param {HTMLElement|string} target - Element or selector
     * @param {string} type - Skeleton type (card, table, chart)
     */
    function showSkeleton(target, type = 'card') {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        // Hide existing content
        const content = element.children;
        Array.from(content).forEach(child => {
            child.classList.add('loading-hide');
        });

        // Create skeleton based on type
        let skeletonHTML = '';

        switch (type) {
            case 'card':
                skeletonHTML = `
                    <div class="skeleton-card">
                        <div class="skeleton-card-header">
                            <div class="skeleton skeleton-card-avatar"></div>
                            <div class="skeleton skeleton-text skeleton-text-medium"></div>
                        </div>
                        <div class="skeleton-card-content">
                            <div class="skeleton skeleton-text skeleton-text-long"></div>
                            <div class="skeleton skeleton-text skeleton-text-medium"></div>
                            <div class="skeleton skeleton-text skeleton-text-short"></div>
                        </div>
                    </div>
                `;
                break;

            case 'table':
                skeletonHTML = `
                    <div class="skeleton-table">
                        ${Array(5).fill(0).map(() => `
                            <div class="skeleton-table-row">
                                <div class="skeleton skeleton-table-cell"></div>
                                <div class="skeleton skeleton-table-cell"></div>
                                <div class="skeleton skeleton-table-cell"></div>
                            </div>
                        `).join('')}
                    </div>
                `;
                break;

            case 'chart':
                skeletonHTML = `<div class="skeleton skeleton-chart"></div>`;
                break;

            default:
                skeletonHTML = `
                    <div class="skeleton skeleton-text skeleton-text-long"></div>
                    <div class="skeleton skeleton-text skeleton-text-medium"></div>
                    <div class="skeleton skeleton-text skeleton-text-short"></div>
                `;
        }

        // Add skeleton
        const skeletonWrapper = document.createElement('div');
        skeletonWrapper.className = 'skeleton-wrapper loading-show';
        skeletonWrapper.innerHTML = skeletonHTML;
        element.appendChild(skeletonWrapper);

        return skeletonWrapper;
    }

    /**
     * Hide skeleton screen
     *
     * @param {HTMLElement|string} target - Element or selector
     */
    function hideSkeleton(target) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        // Remove skeleton
        const skeleton = element.querySelector('.skeleton-wrapper');
        if (skeleton) {
            skeleton.remove();
        }

        // Show hidden content
        const content = element.children;
        Array.from(content).forEach(child => {
            child.classList.remove('loading-hide');
        });
    }

    /**
     * Show progress bar
     *
     * @param {HTMLElement|string} target - Element or selector
     * @param {number} progress - Progress percentage (0-100), or -1 for indeterminate
     * @param {string} label - Optional label
     */
    function showProgress(target, progress = -1, label = '') {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        // Create progress bar if it doesn't exist
        let progressWrapper = element.querySelector('.progress-wrapper');
        if (!progressWrapper) {
            progressWrapper = document.createElement('div');
            progressWrapper.className = 'progress-wrapper';
            progressWrapper.innerHTML = `
                ${label ? `
                    <div class="progress-label">
                        <span class="progress-text">${escapeHtml(label)}</span>
                        <span class="progress-percentage"></span>
                    </div>
                ` : ''}
                <div class="progress-bar ${progress < 0 ? 'progress-bar-indeterminate' : ''}">
                    <div class="progress-bar-fill" style="width: 0%"></div>
                </div>
            `;
            element.appendChild(progressWrapper);
        }

        // Update progress
        const fill = progressWrapper.querySelector('.progress-bar-fill');
        const percentage = progressWrapper.querySelector('.progress-percentage');

        if (progress >= 0 && progress <= 100) {
            // Determinate progress
            progressWrapper.querySelector('.progress-bar').classList.remove('progress-bar-indeterminate');
            fill.style.width = progress + '%';
            if (percentage) {
                percentage.textContent = Math.round(progress) + '%';
            }
        } else {
            // Indeterminate progress
            progressWrapper.querySelector('.progress-bar').classList.add('progress-bar-indeterminate');
            if (percentage) {
                percentage.textContent = '';
            }
        }

        return progressWrapper;
    }

    /**
     * Hide progress bar
     *
     * @param {HTMLElement|string} target - Element or selector
     */
    function hideProgress(target) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;

        const progressWrapper = element.querySelector('.progress-wrapper');
        if (progressWrapper) {
            progressWrapper.remove();
        }
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
    const loading = {
        /**
         * Show loading spinner in element
         */
        show: showLoading,

        /**
         * Hide loading spinner
         */
        hide: hideLoading,

        /**
         * Show fullscreen loading overlay
         */
        fullscreen: showFullscreen,

        /**
         * Hide fullscreen loading overlay
         */
        hideFullscreen: hideFullscreen,

        /**
         * Show skeleton screen
         */
        showSkeleton: showSkeleton,

        /**
         * Hide skeleton screen
         */
        hideSkeleton: hideSkeleton,

        /**
         * Show progress bar
         */
        showProgress: showProgress,

        /**
         * Hide progress bar
         */
        hideProgress: hideProgress
    };

    // Expose to global scope
    window.loading = loading;

})(window);
