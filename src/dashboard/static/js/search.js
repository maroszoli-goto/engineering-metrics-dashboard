/**
 * Global Search Functionality
 *
 * Provides instant search across teams, persons, and releases.
 * Keyboard shortcut: Cmd/Ctrl + K
 *
 * Usage:
 *   Automatically initialized on page load.
 *   Press Cmd/Ctrl + K to open search modal.
 */

(function (window) {
    'use strict';

    // Search data cache
    let searchData = {
        teams: [],
        persons: [],
        releases: []
    };

    // Search state
    let searchModal = null;
    let searchInput = null;
    let searchResults = null;
    let selectedIndex = -1;
    let currentResults = [];

    /**
     * Initialize search functionality
     */
    function initSearch() {
        createSearchModal();
        loadSearchData();
        bindKeyboardShortcut();
    }

    /**
     * Create search modal
     */
    function createSearchModal() {
        // Create modal HTML
        const modal = document.createElement('div');
        modal.id = 'search-modal';
        modal.className = 'search-modal';
        modal.innerHTML = `
            <div class="search-modal-backdrop"></div>
            <div class="search-modal-content">
                <div class="search-header">
                    <input
                        type="text"
                        id="search-input"
                        class="search-input"
                        placeholder="Search teams, persons, releases..."
                        autocomplete="off"
                        autocorrect="off"
                        spellcheck="false"
                    >
                    <button class="search-close" aria-label="Close search">×</button>
                </div>
                <div class="search-body">
                    <div id="search-results" class="search-results">
                        <div class="search-empty">
                            <div class="search-empty-icon">🔍</div>
                            <div class="search-empty-text">Start typing to search...</div>
                            <div class="search-hint">
                                <kbd>↑</kbd> <kbd>↓</kbd> to navigate &nbsp;·&nbsp;
                                <kbd>Enter</kbd> to select &nbsp;·&nbsp;
                                <kbd>Esc</kbd> to close
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Store references
        searchModal = modal;
        searchInput = document.getElementById('search-input');
        searchResults = document.getElementById('search-results');

        // Bind events
        bindSearchEvents();
    }

    /**
     * Bind search modal events
     */
    function bindSearchEvents() {
        // Close on backdrop click
        const backdrop = searchModal.querySelector('.search-modal-backdrop');
        backdrop.addEventListener('click', closeSearch);

        // Close button
        const closeBtn = searchModal.querySelector('.search-close');
        closeBtn.addEventListener('click', closeSearch);

        // Search input
        searchInput.addEventListener('input', handleSearchInput);
        searchInput.addEventListener('keydown', handleSearchKeydown);

        // Esc key to close
        searchModal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeSearch();
            }
        });
    }

    /**
     * Bind global keyboard shortcut (Cmd/Ctrl + K)
     */
    function bindKeyboardShortcut() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                openSearch();
            }
        });
    }

    /**
     * Load search data from page or API
     */
    function loadSearchData() {
        // Try to load from global window object first
        if (window.searchIndexData) {
            searchData = window.searchIndexData;
            return;
        }

        // Otherwise, fetch from API
        fetch('/api/search/index')
            .then(response => response.json())
            .then(data => {
                searchData = data;
            })
            .catch(error => {
                console.warn('Search index not available:', error);
                // Fallback: extract from page
                extractSearchDataFromPage();
            });
    }

    /**
     * Extract search data from current page
     */
    function extractSearchDataFromPage() {
        // Extract team links
        const teamLinks = document.querySelectorAll('a[href^="/team/"]');
        searchData.teams = Array.from(teamLinks).map(link => {
            const href = link.getAttribute('href');
            const match = href.match(/\/team\/([^\/]+)/);
            return {
                name: link.textContent.trim(),
                url: href,
                slug: match ? match[1] : ''
            };
        });

        // Extract person links
        const personLinks = document.querySelectorAll('a[href^="/person/"]');
        searchData.persons = Array.from(personLinks).map(link => {
            const href = link.getAttribute('href');
            const match = href.match(/\/person\/([^\/]+)/);
            return {
                name: link.textContent.trim(),
                url: href,
                username: match ? match[1] : ''
            };
        });

        // Remove duplicates
        searchData.teams = Array.from(new Set(searchData.teams.map(t => t.url)))
            .map(url => searchData.teams.find(t => t.url === url));

        searchData.persons = Array.from(new Set(searchData.persons.map(p => p.url)))
            .map(url => searchData.persons.find(p => p.url === url));
    }

    /**
     * Open search modal
     */
    function openSearch() {
        searchModal.classList.add('active');
        searchInput.focus();
        selectedIndex = -1;

        // Clear previous search
        searchInput.value = '';
        showEmptyState();
    }

    /**
     * Close search modal
     */
    function closeSearch() {
        searchModal.classList.remove('active');
        searchInput.value = '';
        showEmptyState();
    }

    /**
     * Handle search input
     */
    function handleSearchInput(e) {
        const query = e.target.value.trim();

        if (query.length === 0) {
            showEmptyState();
            return;
        }

        // Perform search
        const results = performSearch(query);
        displayResults(results);
    }

    /**
     * Handle keyboard navigation in search
     */
    function handleSearchKeydown(e) {
        if (currentResults.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
                updateSelection();
                break;

            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection();
                break;

            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < currentResults.length) {
                    navigateToResult(currentResults[selectedIndex]);
                }
                break;
        }
    }

    /**
     * Perform search across all data
     */
    function performSearch(query) {
        const lowerQuery = query.toLowerCase();
        const results = [];

        // Search teams
        searchData.teams.forEach(team => {
            if (team.name.toLowerCase().includes(lowerQuery) ||
                team.slug.toLowerCase().includes(lowerQuery)) {
                results.push({
                    type: 'team',
                    title: team.name,
                    subtitle: 'Team',
                    icon: '👥',
                    url: team.url
                });
            }
        });

        // Search persons
        searchData.persons.forEach(person => {
            if (person.name.toLowerCase().includes(lowerQuery) ||
                person.username.toLowerCase().includes(lowerQuery)) {
                results.push({
                    type: 'person',
                    title: person.name,
                    subtitle: 'Person',
                    icon: '👤',
                    url: person.url
                });
            }
        });

        // Limit results
        return results.slice(0, 10);
    }

    /**
     * Display search results
     */
    function displayResults(results) {
        currentResults = results;
        selectedIndex = -1;

        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="search-empty">
                    <div class="search-empty-icon">🔍</div>
                    <div class="search-empty-text">No results found</div>
                </div>
            `;
            return;
        }

        const html = results.map((result, index) => `
            <div class="search-result-item" data-index="${index}">
                <div class="search-result-icon">${result.icon}</div>
                <div class="search-result-content">
                    <div class="search-result-title">${escapeHtml(result.title)}</div>
                    <div class="search-result-subtitle">${escapeHtml(result.subtitle)}</div>
                </div>
            </div>
        `).join('');

        searchResults.innerHTML = html;

        // Bind click events
        searchResults.querySelectorAll('.search-result-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                navigateToResult(results[index]);
            });
        });
    }

    /**
     * Show empty state
     */
    function showEmptyState() {
        currentResults = [];
        selectedIndex = -1;
        searchResults.innerHTML = `
            <div class="search-empty">
                <div class="search-empty-icon">🔍</div>
                <div class="search-empty-text">Start typing to search...</div>
                <div class="search-hint">
                    <kbd>↑</kbd> <kbd>↓</kbd> to navigate &nbsp;·&nbsp;
                    <kbd>Enter</kbd> to select &nbsp;·&nbsp;
                    <kbd>Esc</kbd> to close
                </div>
            </div>
        `;
    }

    /**
     * Update visual selection
     */
    function updateSelection() {
        const items = searchResults.querySelectorAll('.search-result-item');
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    /**
     * Navigate to selected result
     */
    function navigateToResult(result) {
        closeSearch();
        window.location.href = result.url;
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSearch);
    } else {
        initSearch();
    }

    // Expose to global scope
    window.search = {
        open: openSearch,
        close: closeSearch
    };

})(window);
