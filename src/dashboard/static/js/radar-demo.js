/**
 * Radar Chart Demo
 *
 * Demonstrates radar/spider chart usage for multi-dimensional comparisons.
 * Shows examples for team performance, DORA metrics, and custom dimensions.
 */

(function() {
    'use strict';

    /**
     * Generate sample team member data
     * @param {number} count - Number of members
     * @returns {Array} Array of member objects with scores
     */
    function generateSampleTeamData(count = 5) {
        const names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry'];
        const members = [];

        for (let i = 0; i < Math.min(count, names.length); i++) {
            members.push({
                name: names[i],
                prs_score: 60 + Math.random() * 40,
                reviews_score: 50 + Math.random() * 50,
                commits_score: 55 + Math.random() * 45,
                merge_rate_score: 70 + Math.random() * 30,
                cycle_time_score: 60 + Math.random() * 40,
                dora_score: 65 + Math.random() * 35
            });
        }

        return members;
    }

    /**
     * Generate sample DORA metrics data
     * @param {number} count - Number of teams
     * @returns {Array} Array of team objects with DORA scores
     */
    function generateSampleDORAData(count = 3) {
        const teamNames = ['Backend Team', 'Frontend Team', 'Mobile Team', 'DevOps Team'];
        const teams = [];

        for (let i = 0; i < Math.min(count, teamNames.length); i++) {
            teams.push({
                name: teamNames[i],
                deployment_frequency_score: 50 + Math.random() * 50,
                lead_time_score: 60 + Math.random() * 40,
                cfr_score: 70 + Math.random() * 30,
                mttr_score: 65 + Math.random() * 35
            });
        }

        return teams;
    }

    /**
     * Render team comparison radar chart
     * @param {string} elementId - Container element ID
     * @param {Object} options - Chart options
     */
    function renderTeamRadar(elementId, options = {}) {
        const { memberCount = 5, title } = options;

        const members = generateSampleTeamData(memberCount);

        const { data, layout, config } = createTeamRadarChart({
            members: members,
            title: title || 'Team Performance Comparison'
        });

        Plotly.newPlot(elementId, data, layout, config);
    }

    /**
     * Render DORA metrics radar chart
     * @param {string} elementId - Container element ID
     * @param {Object} options - Chart options
     */
    function renderDORARadar(elementId, options = {}) {
        const { teamCount = 3, title } = options;

        const teams = generateSampleDORAData(teamCount);

        const { data, layout, config } = createDORARadarChart({
            teams: teams,
            title: title || 'DORA Metrics Comparison'
        });

        Plotly.newPlot(elementId, data, layout, config);
    }

    /**
     * Render custom radar chart
     * @param {string} elementId - Container element ID
     * @param {Object} options - Chart options
     */
    function renderCustomRadar(elementId, options = {}) {
        const categories = options.categories || [
            'Speed', 'Quality', 'Collaboration',
            'Innovation', 'Documentation', 'Testing'
        ];

        const series = options.series || [
            {
                name: 'Current Sprint',
                values: [85, 90, 75, 70, 80, 88],
                color: '#3498db'
            },
            {
                name: 'Previous Sprint',
                values: [75, 85, 70, 65, 75, 80],
                color: '#95a5a6'
            }
        ];

        const { data, layout, config } = createRadarChart({
            categories: categories,
            series: series,
            title: options.title || 'Sprint Comparison',
            maxValue: 100,
            fillOpacity: 0.2
        });

        Plotly.newPlot(elementId, data, layout, config);
    }

    /**
     * Add interactive controls for radar charts
     */
    function addRadarControls() {
        const controls = document.getElementById('radar-controls');
        if (!controls) return;

        controls.innerHTML = `
            <div style="padding: 20px; background: var(--bg-secondary); border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Radar Chart Controls</h3>

                <div style="margin-bottom: 20px;">
                    <h4>Team Performance Comparison</h4>
                    <div style="display: flex; gap: 20px; align-items: center; margin-top: 10px;">
                        <div>
                            <label for="member-count" style="display: block; margin-bottom: 5px;">Number of Members:</label>
                            <input type="number" id="member-count" min="2" max="8" value="5"
                                   style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary); width: 80px;">
                        </div>
                        <div style="padding-top: 20px;">
                            <button id="update-team-radar" class="btn-primary"
                                    style="padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 4px; cursor: pointer;">
                                Update Team Chart
                            </button>
                        </div>
                    </div>
                    <div id="team-radar-chart" style="margin-top: 20px;"></div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h4>DORA Metrics Comparison</h4>
                    <div style="display: flex; gap: 20px; align-items: center; margin-top: 10px;">
                        <div>
                            <label for="team-count" style="display: block; margin-bottom: 5px;">Number of Teams:</label>
                            <input type="number" id="team-count" min="2" max="4" value="3"
                                   style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary); width: 80px;">
                        </div>
                        <div style="padding-top: 20px;">
                            <button id="update-dora-radar" class="btn-primary"
                                    style="padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 4px; cursor: pointer;">
                                Update DORA Chart
                            </button>
                        </div>
                    </div>
                    <div id="dora-radar-chart" style="margin-top: 20px;"></div>
                </div>

                <div>
                    <h4>Custom Dimensions</h4>
                    <div id="custom-radar-chart" style="margin-top: 20px;"></div>
                </div>
            </div>
        `;

        // Add event listeners
        document.getElementById('update-team-radar').addEventListener('click', function() {
            const count = parseInt(document.getElementById('member-count').value);
            renderTeamRadar('team-radar-chart', { memberCount: count });
        });

        document.getElementById('update-dora-radar').addEventListener('click', function() {
            const count = parseInt(document.getElementById('team-count').value);
            renderDORARadar('dora-radar-chart', { teamCount: count });
        });

        // Render initial charts
        renderTeamRadar('team-radar-chart', { memberCount: 5 });
        renderDORARadar('dora-radar-chart', { teamCount: 3 });
        renderCustomRadar('custom-radar-chart');
    }

    /**
     * Example: Before/After comparison
     */
    function renderBeforeAfterComparison(elementId) {
        const categories = [
            'Deployment Freq',
            'Lead Time',
            'Code Quality',
            'Test Coverage',
            'Bug Rate',
            'Team Velocity'
        ];

        const series = [
            {
                name: 'Before Improvements',
                values: [40, 50, 60, 55, 45, 50],
                color: '#e74c3c'
            },
            {
                name: 'After Improvements',
                values: [75, 80, 85, 90, 80, 85],
                color: '#2ecc71'
            }
        ];

        const { data, layout, config } = createRadarChart({
            categories: categories,
            series: series,
            title: 'Process Improvement Impact',
            maxValue: 100,
            fillOpacity: 0.25
        });

        Plotly.newPlot(elementId, data, layout, config);
    }

    /**
     * Example: Skill assessment radar
     */
    function renderSkillAssessment(elementId) {
        const categories = [
            'Frontend',
            'Backend',
            'DevOps',
            'Testing',
            'Security',
            'Architecture',
            'Communication',
            'Leadership'
        ];

        const series = [
            {
                name: 'Developer A',
                values: [90, 70, 60, 75, 65, 70, 85, 80],
                color: '#3498db'
            },
            {
                name: 'Developer B',
                values: [70, 90, 85, 80, 80, 75, 70, 65],
                color: '#9b59b6'
            }
        ];

        const { data, layout, config } = createRadarChart({
            categories: categories,
            series: series,
            title: 'Skills Assessment',
            maxValue: 100,
            fillOpacity: 0.15
        });

        Plotly.newPlot(elementId, data, layout, config);
    }

    // Export demo functions
    window.RadarDemo = {
        renderTeam: renderTeamRadar,
        renderDORA: renderDORARadar,
        renderCustom: renderCustomRadar,
        renderBeforeAfter: renderBeforeAfterComparison,
        renderSkills: renderSkillAssessment,
        addControls: addRadarControls,
        generateTeamData: generateSampleTeamData,
        generateDORAData: generateSampleDORAData
    };

    // Auto-initialize if demo elements exist
    document.addEventListener('DOMContentLoaded', function() {
        if (document.getElementById('radar-controls')) {
            addRadarControls();
        }
    });
})();
