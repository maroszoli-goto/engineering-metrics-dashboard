/**
 * User Preferences System
 *
 * Manages user preferences for dashboard customization.
 * Stores preferences in localStorage for persistence.
 *
 * Preferences include:
 * - Default date range (30d, 90d, etc.)
 * - Default environment (prod, uat)
 * - Default team view
 * - Visible metrics (show/hide)
 * - Dashboard card order
 * - Chart preferences (colors, types)
 */

(function() {
    'use strict';

    // Preference keys
    const STORAGE_KEY = 'team_metrics_preferences';

    // Default preferences
    const DEFAULT_PREFERENCES = {
        // View preferences
        defaultDateRange: '90d',
        defaultEnvironment: 'prod',
        defaultTeamView: null,  // null = overview
        defaultLandingPage: '/',  // '/', '/comparison', '/team/X', etc.

        // Metric visibility
        visibleMetrics: {
            github: true,
            jira: true,
            dora: true,
            performance: true,
            trends: true
        },

        // Chart preferences
        chartPreferences: {
            defaultChartType: 'bar',  // bar, line, pie
            showTrendLines: true,
            showAverageLines: true,
            colorScheme: 'default',  // default, colorblind, high-contrast
            animationSpeed: 'normal'  // fast, normal, slow, none
        },

        // Dashboard layout
        dashboardLayout: {
            cardOrder: [],  // Empty = default order
            compactMode: false,
            showBreadcrumbs: true
        },

        // Table preferences
        tablePreferences: {
            defaultSortColumn: 'performance_score',
            defaultSortOrder: 'desc',
            rowsPerPage: 10
        },

        // Notification preferences
        notifications: {
            showToasts: true,
            toastDuration: 4000,
            showLoadingIndicators: true
        },

        // Accessibility
        accessibility: {
            reduceMotion: false,
            highContrast: false,
            largeText: false
        },

        // Advanced
        advanced: {
            enableExperimentalFeatures: false,
            debugMode: false
        }
    };

    /**
     * Load preferences from localStorage
     * @returns {Object} User preferences
     */
    function loadPreferences() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Merge with defaults to handle new preferences
                return deepMerge(DEFAULT_PREFERENCES, parsed);
            }
        } catch (e) {
            console.warn('Failed to load preferences:', e);
        }
        return { ...DEFAULT_PREFERENCES };
    }

    /**
     * Save preferences to localStorage
     * @param {Object} preferences - Preferences to save
     */
    function savePreferences(preferences) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
            return true;
        } catch (e) {
            console.error('Failed to save preferences:', e);
            toast.error('Failed to save preferences');
            return false;
        }
    }

    /**
     * Get a specific preference value
     * @param {string} path - Dot-notation path (e.g., 'chartPreferences.colorScheme')
     * @returns {any} Preference value
     */
    function getPreference(path) {
        const prefs = loadPreferences();
        return getNestedValue(prefs, path);
    }

    /**
     * Set a specific preference value
     * @param {string} path - Dot-notation path
     * @param {any} value - Value to set
     */
    function setPreference(path, value) {
        const prefs = loadPreferences();
        setNestedValue(prefs, path, value);
        return savePreferences(prefs);
    }

    /**
     * Reset preferences to defaults
     */
    function resetPreferences() {
        if (confirm('Reset all preferences to defaults?')) {
            savePreferences(DEFAULT_PREFERENCES);
            toast.success('Preferences reset to defaults');
            return true;
        }
        return false;
    }

    /**
     * Export preferences as JSON
     * @returns {string} JSON string of preferences
     */
    function exportPreferences() {
        const prefs = loadPreferences();
        return JSON.stringify(prefs, null, 2);
    }

    /**
     * Import preferences from JSON
     * @param {string} json - JSON string
     */
    function importPreferences(json) {
        try {
            const parsed = JSON.parse(json);
            if (savePreferences(parsed)) {
                toast.success('Preferences imported successfully');
                return true;
            }
        } catch (e) {
            toast.error('Invalid preferences file');
            return false;
        }
    }

    /**
     * Apply preferences to current page
     */
    function applyPreferences() {
        const prefs = loadPreferences();

        // Apply accessibility preferences
        if (prefs.accessibility.reduceMotion) {
            document.documentElement.style.setProperty('--transition-speed', '0s');
        }
        if (prefs.accessibility.highContrast) {
            document.documentElement.setAttribute('data-contrast', 'high');
        }
        if (prefs.accessibility.largeText) {
            document.documentElement.style.fontSize = '18px';
        }

        // Apply chart preferences
        if (prefs.chartPreferences.animationSpeed === 'none') {
            document.documentElement.style.setProperty('--animation-duration', '0s');
        }

        // Fire event for other components to listen to
        document.dispatchEvent(new CustomEvent('preferencesApplied', { detail: prefs }));
    }

    /**
     * Deep merge two objects
     * @param {Object} target - Target object
     * @param {Object} source - Source object
     * @returns {Object} Merged object
     */
    function deepMerge(target, source) {
        const result = { ...target };
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = deepMerge(target[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        return result;
    }

    /**
     * Get nested value from object using dot notation
     * @param {Object} obj - Object to query
     * @param {string} path - Dot-notation path
     * @returns {any} Value at path
     */
    function getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    /**
     * Set nested value in object using dot notation
     * @param {Object} obj - Object to modify
     * @param {string} path - Dot-notation path
     * @param {any} value - Value to set
     */
    function setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((current, key) => {
            if (!current[key]) current[key] = {};
            return current[key];
        }, obj);
        target[lastKey] = value;
    }

    /**
     * Check if default date range should be applied
     * @returns {boolean} True if should redirect with preferences
     */
    function shouldApplyDefaultDateRange() {
        const urlParams = new URLSearchParams(window.location.search);
        const hasRangeParam = urlParams.has('range');
        const hasEnvParam = urlParams.has('env');

        // Only apply defaults if no params present
        return !hasRangeParam && !hasEnvParam;
    }

    /**
     * Apply default date range and environment if not in URL
     */
    function applyDefaultParams() {
        if (!shouldApplyDefaultDateRange()) return;

        const prefs = loadPreferences();
        const defaultRange = prefs.defaultDateRange;
        const defaultEnv = prefs.defaultEnvironment;

        // Check if defaults differ from current (or missing)
        const urlParams = new URLSearchParams(window.location.search);
        const currentRange = urlParams.get('range');
        const currentEnv = urlParams.get('env');

        if (currentRange !== defaultRange || currentEnv !== defaultEnv) {
            urlParams.set('range', defaultRange);
            urlParams.set('env', defaultEnv);

            // Redirect with defaults
            const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
            window.location.href = newUrl;
        }
    }

    /**
     * Show preferences modal
     */
    function showPreferencesModal() {
        const prefs = loadPreferences();

        const modalHTML = `
            <div class="preferences-modal-overlay">
                <div class="preferences-modal">
                    <div class="preferences-modal-header">
                        <h2>⚙️ Preferences</h2>
                        <button class="preferences-modal-close" aria-label="Close">&times;</button>
                    </div>
                    <div class="preferences-modal-body">
                        ${generatePreferencesForm(prefs)}
                    </div>
                    <div class="preferences-modal-footer">
                        <button id="save-preferences" class="btn-primary">Save</button>
                        <button id="reset-preferences" class="btn-secondary">Reset to Defaults</button>
                        <button id="export-preferences" class="btn-secondary">Export</button>
                        <button id="import-preferences" class="btn-secondary">Import</button>
                        <button id="cancel-preferences" class="btn-secondary">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container.firstElementChild);

        attachPreferencesHandlers();
    }

    /**
     * Generate preferences form HTML
     * @param {Object} prefs - Current preferences
     * @returns {string} HTML string
     */
    function generatePreferencesForm(prefs) {
        return `
            <div class="preferences-section">
                <h3>View Preferences</h3>
                <div class="preference-item">
                    <label for="pref-date-range">Default Date Range:</label>
                    <select id="pref-date-range">
                        <option value="30d" ${prefs.defaultDateRange === '30d' ? 'selected' : ''}>30 days</option>
                        <option value="60d" ${prefs.defaultDateRange === '60d' ? 'selected' : ''}>60 days</option>
                        <option value="90d" ${prefs.defaultDateRange === '90d' ? 'selected' : ''}>90 days</option>
                        <option value="180d" ${prefs.defaultDateRange === '180d' ? 'selected' : ''}>180 days</option>
                        <option value="365d" ${prefs.defaultDateRange === '365d' ? 'selected' : ''}>365 days</option>
                    </select>
                </div>
                <div class="preference-item">
                    <label for="pref-environment">Default Environment:</label>
                    <select id="pref-environment">
                        <option value="prod" ${prefs.defaultEnvironment === 'prod' ? 'selected' : ''}>Production</option>
                        <option value="uat" ${prefs.defaultEnvironment === 'uat' ? 'selected' : ''}>UAT</option>
                    </select>
                </div>
            </div>

            <div class="preferences-section">
                <h3>Metric Visibility</h3>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-metric-github" ${prefs.visibleMetrics.github ? 'checked' : ''}> GitHub Metrics</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-metric-jira" ${prefs.visibleMetrics.jira ? 'checked' : ''}> Jira Metrics</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-metric-dora" ${prefs.visibleMetrics.dora ? 'checked' : ''}> DORA Metrics</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-metric-performance" ${prefs.visibleMetrics.performance ? 'checked' : ''}> Performance Score</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-metric-trends" ${prefs.visibleMetrics.trends ? 'checked' : ''}> Trend Charts</label>
                </div>
            </div>

            <div class="preferences-section">
                <h3>Chart Preferences</h3>
                <div class="preference-item">
                    <label for="pref-color-scheme">Color Scheme:</label>
                    <select id="pref-color-scheme">
                        <option value="default" ${prefs.chartPreferences.colorScheme === 'default' ? 'selected' : ''}>Default</option>
                        <option value="colorblind" ${prefs.chartPreferences.colorScheme === 'colorblind' ? 'selected' : ''}>Colorblind Safe</option>
                        <option value="high-contrast" ${prefs.chartPreferences.colorScheme === 'high-contrast' ? 'selected' : ''}>High Contrast</option>
                    </select>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-trend-lines" ${prefs.chartPreferences.showTrendLines ? 'checked' : ''}> Show Trend Lines</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-average-lines" ${prefs.chartPreferences.showAverageLines ? 'checked' : ''}> Show Average Lines</label>
                </div>
            </div>

            <div class="preferences-section">
                <h3>Notifications</h3>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-show-toasts" ${prefs.notifications.showToasts ? 'checked' : ''}> Show Toast Notifications</label>
                </div>
            </div>

            <div class="preferences-section">
                <h3>Accessibility</h3>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-reduce-motion" ${prefs.accessibility.reduceMotion ? 'checked' : ''}> Reduce Motion</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-high-contrast" ${prefs.accessibility.highContrast ? 'checked' : ''}> High Contrast</label>
                </div>
                <div class="preference-item">
                    <label><input type="checkbox" id="pref-large-text" ${prefs.accessibility.largeText ? 'checked' : ''}> Large Text</label>
                </div>
            </div>
        `;
    }

    /**
     * Attach event handlers to preferences modal
     */
    function attachPreferencesHandlers() {
        const overlay = document.querySelector('.preferences-modal-overlay');
        const closeBtn = document.querySelector('.preferences-modal-close');
        const saveBtn = document.getElementById('save-preferences');
        const resetBtn = document.getElementById('reset-preferences');
        const exportBtn = document.getElementById('export-preferences');
        const importBtn = document.getElementById('import-preferences');
        const cancelBtn = document.getElementById('cancel-preferences');

        const closeModal = () => overlay.remove();

        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });

        saveBtn.addEventListener('click', () => {
            const newPrefs = gatherPreferencesFromForm();
            if (savePreferences(newPrefs)) {
                toast.success('Preferences saved successfully');
                applyPreferences();
                closeModal();
                // Reload if date range or env changed
                if (window.location.search) {
                    window.location.reload();
                }
            }
        });

        resetBtn.addEventListener('click', () => {
            if (resetPreferences()) {
                closeModal();
                window.location.reload();
            }
        });

        exportBtn.addEventListener('click', () => {
            const json = exportPreferences();
            downloadFile('preferences.json', json);
            toast.success('Preferences exported');
        });

        importBtn.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        if (importPreferences(event.target.result)) {
                            closeModal();
                            window.location.reload();
                        }
                    };
                    reader.readAsText(file);
                }
            };
            input.click();
        });
    }

    /**
     * Gather preferences from form inputs
     * @returns {Object} Preferences object
     */
    function gatherPreferencesFromForm() {
        const prefs = loadPreferences();

        // View preferences
        prefs.defaultDateRange = document.getElementById('pref-date-range').value;
        prefs.defaultEnvironment = document.getElementById('pref-environment').value;

        // Metric visibility
        prefs.visibleMetrics.github = document.getElementById('pref-metric-github').checked;
        prefs.visibleMetrics.jira = document.getElementById('pref-metric-jira').checked;
        prefs.visibleMetrics.dora = document.getElementById('pref-metric-dora').checked;
        prefs.visibleMetrics.performance = document.getElementById('pref-metric-performance').checked;
        prefs.visibleMetrics.trends = document.getElementById('pref-metric-trends').checked;

        // Chart preferences
        prefs.chartPreferences.colorScheme = document.getElementById('pref-color-scheme').value;
        prefs.chartPreferences.showTrendLines = document.getElementById('pref-trend-lines').checked;
        prefs.chartPreferences.showAverageLines = document.getElementById('pref-average-lines').checked;

        // Notifications
        prefs.notifications.showToasts = document.getElementById('pref-show-toasts').checked;

        // Accessibility
        prefs.accessibility.reduceMotion = document.getElementById('pref-reduce-motion').checked;
        prefs.accessibility.highContrast = document.getElementById('pref-high-contrast').checked;
        prefs.accessibility.largeText = document.getElementById('pref-large-text').checked;

        return prefs;
    }

    /**
     * Download file helper
     * @param {string} filename - Filename
     * @param {string} content - File content
     */
    function downloadFile(filename, content) {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Export to global scope
    window.Preferences = {
        load: loadPreferences,
        save: savePreferences,
        get: getPreference,
        set: setPreference,
        reset: resetPreferences,
        export: exportPreferences,
        import: importPreferences,
        apply: applyPreferences,
        showModal: showPreferencesModal
    };

    // Auto-apply preferences on page load
    document.addEventListener('DOMContentLoaded', function() {
        applyPreferences();
        // Note: applyDefaultParams disabled by default to avoid breaking existing bookmarks
        // Uncomment if you want auto-redirect to default params:
        // applyDefaultParams();
    });
})();
