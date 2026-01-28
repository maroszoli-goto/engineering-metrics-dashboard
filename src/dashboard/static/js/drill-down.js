/**
 * Chart Drill-Down System
 *
 * Enables click-to-expand functionality for charts with detailed views.
 * Shows modal/slide-out panels with additional context and data.
 *
 * Usage:
 *   enableDrillDown('chart-id', {
 *       type: 'team-members',
 *       data: teamData
 *   });
 */

(function() {
    'use strict';

    // Modal container singleton
    let modalContainer = null;
    let currentModal = null;

    /**
     * Initialize modal container
     */
    function initModalContainer() {
        if (modalContainer) return;

        modalContainer = document.createElement('div');
        modalContainer.id = 'drill-down-modal-container';
        modalContainer.className = 'drill-down-modal-overlay';
        modalContainer.style.display = 'none';
        document.body.appendChild(modalContainer);

        // Close on overlay click
        modalContainer.addEventListener('click', function(e) {
            if (e.target === modalContainer) {
                closeModal();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && currentModal) {
                closeModal();
            }
        });
    }

    /**
     * Show drill-down modal
     * @param {Object} config - Modal configuration
     */
    function showModal(config) {
        initModalContainer();

        const { title, content, type, data } = config;

        // Create modal HTML
        const modalHTML = `
            <div class="drill-down-modal">
                <div class="drill-down-modal-header">
                    <h3>${title}</h3>
                    <button class="drill-down-modal-close" aria-label="Close modal">&times;</button>
                </div>
                <div class="drill-down-modal-body">
                    ${content || generateContent(type, data)}
                </div>
            </div>
        `;

        modalContainer.innerHTML = modalHTML;
        modalContainer.style.display = 'flex';
        currentModal = modalContainer.querySelector('.drill-down-modal');

        // Add close button handler
        const closeBtn = modalContainer.querySelector('.drill-down-modal-close');
        closeBtn.addEventListener('click', closeModal);

        // Focus trap
        currentModal.focus();
    }

    /**
     * Close modal
     */
    function closeModal() {
        if (modalContainer) {
            modalContainer.style.display = 'none';
            modalContainer.innerHTML = '';
            currentModal = null;
        }
    }

    /**
     * Generate content based on drill-down type
     * @param {string} type - Content type
     * @param {Object} data - Data to display
     * @returns {string} HTML content
     */
    function generateContent(type, data) {
        switch (type) {
            case 'team-members':
                return generateTeamMembersView(data);
            case 'pr-details':
                return generatePRDetailsView(data);
            case 'dora-breakdown':
                return generateDORABreakdownView(data);
            case 'release-details':
                return generateReleaseDetailsView(data);
            case 'trend-details':
                return generateTrendDetailsView(data);
            default:
                return `<p>Details for ${data.label || 'item'}</p>`;
        }
    }

    /**
     * Generate team members breakdown view
     * @param {Object} data - Team data
     * @returns {string} HTML content
     */
    function generateTeamMembersView(data) {
        const { teamName, members } = data;

        let html = `<div class="drill-down-section">`;
        html += `<p class="drill-down-subtitle">Individual contributor breakdown for ${teamName}</p>`;

        if (!members || members.length === 0) {
            html += `<p class="drill-down-empty">No member data available</p>`;
        } else {
            html += `<table class="drill-down-table">
                <thead>
                    <tr>
                        <th>Member</th>
                        <th>PRs</th>
                        <th>Reviews</th>
                        <th>Commits</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>`;

            members.forEach(member => {
                html += `
                    <tr>
                        <td><a href="/person/${member.username}">${member.name}</a></td>
                        <td>${member.prs || 0}</td>
                        <td>${member.reviews || 0}</td>
                        <td>${member.commits || 0}</td>
                        <td><span class="score-badge">${member.score ? member.score.toFixed(1) : 'N/A'}</span></td>
                    </tr>`;
            });

            html += `</tbody></table>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Generate PR details view
     * @param {Object} data - PR data
     * @returns {string} HTML content
     */
    function generatePRDetailsView(data) {
        const { username, prs } = data;

        let html = `<div class="drill-down-section">`;
        html += `<p class="drill-down-subtitle">Pull requests by ${username}</p>`;

        if (!prs || prs.length === 0) {
            html += `<p class="drill-down-empty">No pull requests in this period</p>`;
        } else {
            html += `<div class="drill-down-pr-list">`;

            prs.forEach(pr => {
                const statusIcon = pr.merged ? '✓' : pr.closed ? '✕' : '○';
                const statusClass = pr.merged ? 'merged' : pr.closed ? 'closed' : 'open';

                html += `
                    <div class="drill-down-pr-item">
                        <div class="pr-status ${statusClass}">${statusIcon}</div>
                        <div class="pr-details">
                            <a href="${pr.url}" target="_blank" class="pr-title">${pr.title}</a>
                            <div class="pr-meta">
                                <span>Created: ${formatDate(pr.created)}</span>
                                ${pr.merged ? `<span>Merged: ${formatDate(pr.merged_at)}</span>` : ''}
                                <span>+${pr.additions} -${pr.deletions}</span>
                            </div>
                        </div>
                    </div>`;
            });

            html += `</div>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Generate DORA metrics breakdown view
     * @param {Object} data - DORA metrics data
     * @returns {string} HTML content
     */
    function generateDORABreakdownView(data) {
        const { metric, value, breakdown } = data;

        let html = `<div class="drill-down-section">`;
        html += `<p class="drill-down-subtitle">${metric} Breakdown</p>`;

        html += `<div class="drill-down-metric-card">
            <div class="metric-value">${value}</div>
            <div class="metric-label">${metric}</div>
        </div>`;

        if (breakdown) {
            html += `<div class="drill-down-breakdown">`;
            html += `<h4>Contributing Factors:</h4>`;
            html += `<ul class="breakdown-list">`;

            breakdown.forEach(item => {
                html += `<li>${item.label}: <strong>${item.value}</strong></li>`;
            });

            html += `</ul></div>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Generate release details view
     * @param {Object} data - Release data
     * @returns {string} HTML content
     */
    function generateReleaseDetailsView(data) {
        const { release, prs, issues } = data;

        let html = `<div class="drill-down-section">`;
        html += `<p class="drill-down-subtitle">Release: ${release.name}</p>`;

        html += `<div class="drill-down-stats">
            <div class="stat-item">
                <div class="stat-value">${release.date}</div>
                <div class="stat-label">Release Date</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${prs ? prs.length : 0}</div>
                <div class="stat-label">Pull Requests</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${issues ? issues.length : 0}</div>
                <div class="stat-label">Issues</div>
            </div>
        </div>`;

        if (prs && prs.length > 0) {
            html += `<h4>Pull Requests:</h4>`;
            html += `<ul class="drill-down-list">`;
            prs.forEach(pr => {
                html += `<li><a href="${pr.url}" target="_blank">${pr.title}</a></li>`;
            });
            html += `</ul>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Generate trend details view
     * @param {Object} data - Trend data
     * @returns {string} HTML content
     */
    function generateTrendDetailsView(data) {
        const { week, created, resolved, details } = data;

        let html = `<div class="drill-down-section">`;
        html += `<p class="drill-down-subtitle">Week: ${week}</p>`;

        html += `<div class="drill-down-stats">
            <div class="stat-item created">
                <div class="stat-value">${created}</div>
                <div class="stat-label">Created</div>
            </div>
            <div class="stat-item resolved">
                <div class="stat-value">${resolved}</div>
                <div class="stat-label">Resolved</div>
            </div>
            <div class="stat-item net">
                <div class="stat-value">${created - resolved}</div>
                <div class="stat-label">Net Change</div>
            </div>
        </div>`;

        if (details && details.length > 0) {
            html += `<h4>Items:</h4>`;
            html += `<ul class="drill-down-list">`;
            details.forEach(item => {
                html += `<li>
                    <span class="item-key">${item.key}</span>
                    <span class="item-title">${item.title}</span>
                    <span class="item-status">${item.status}</span>
                </li>`;
            });
            html += `</ul>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Format date for display
     * @param {string|Date} date - Date to format
     * @returns {string} Formatted date
     */
    function formatDate(date) {
        if (!date) return 'N/A';
        const d = new Date(date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    /**
     * Enable drill-down for a chart
     * @param {string} chartId - Chart element ID
     * @param {Object} config - Drill-down configuration
     */
    function enableDrillDown(chartId, config) {
        const chartElement = document.getElementById(chartId);
        if (!chartElement) {
            console.warn(`Chart element not found: ${chartId}`);
            return;
        }

        // Add click handler
        chartElement.on('plotly_click', function(data) {
            const point = data.points[0];

            // Build modal config based on point data
            const modalConfig = {
                title: config.titleTemplate ?
                       config.titleTemplate(point) :
                       `Details for ${point.label || point.x}`,
                type: config.type,
                data: config.dataExtractor ?
                      config.dataExtractor(point) :
                      { label: point.label || point.x, value: point.y }
            };

            showModal(modalConfig);
        });

        // Add cursor pointer on hover
        chartElement.on('plotly_hover', function() {
            chartElement.style.cursor = 'pointer';
        });

        chartElement.on('plotly_unhover', function() {
            chartElement.style.cursor = 'default';
        });
    }

    // Export to global scope
    window.DrillDown = {
        enable: enableDrillDown,
        showModal: showModal,
        closeModal: closeModal
    };

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initModalContainer);
    } else {
        initModalContainer();
    }
})();
