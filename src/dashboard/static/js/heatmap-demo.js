/**
 * Contribution Heatmap Demo
 *
 * Demonstrates GitHub-style contribution heatmap usage.
 * This file shows example usage and can be included on pages for testing.
 */

(function() {
    'use strict';

    /**
     * Generate sample daily contribution data
     * @param {number} weeks - Number of weeks of data
     * @returns {Object} Daily data { 'YYYY-MM-DD': count }
     */
    function generateSampleData(weeks = 12) {
        const dailyData = {};
        const today = new Date();

        for (let i = 0; i < weeks * 7; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];

            // Random contribution count (weighted toward weekdays)
            const dayOfWeek = date.getDay();
            const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
            const maxContributions = isWeekend ? 5 : 15;

            dailyData[dateStr] = Math.floor(Math.random() * maxContributions);
        }

        return dailyData;
    }

    /**
     * Render heatmap example
     * @param {string} elementId - Container element ID
     * @param {Object} options - Heatmap options
     */
    function renderHeatmapExample(elementId, options = {}) {
        const {
            weeks = 12,
            colorScale = 'green',
            title = 'Contribution Activity (Last 12 Weeks)'
        } = options;

        // Generate sample data
        const dailyData = generateSampleData(weeks);

        // Create heatmap
        const { data, layout, config } = createContributionHeatmap({
            dailyData: dailyData,
            title: title,
            colorScale: colorScale
        });

        // Render with Plotly
        Plotly.newPlot(elementId, data, layout, config);
    }

    /**
     * Example: Multiple heatmaps with different color schemes
     */
    function renderMultipleHeatmaps() {
        const container = document.getElementById('heatmap-examples');
        if (!container) return;

        const colorSchemes = [
            { name: 'Green (GitHub Style)', scale: 'green' },
            { name: 'Blue', scale: 'blue' },
            { name: 'Purple', scale: 'purple' },
            { name: 'Orange', scale: 'orange' }
        ];

        container.innerHTML = '';

        colorSchemes.forEach((scheme, index) => {
            const div = document.createElement('div');
            div.style.marginBottom = '30px';

            const title = document.createElement('h4');
            title.textContent = scheme.name;
            title.style.marginBottom = '10px';

            const chartDiv = document.createElement('div');
            chartDiv.id = `heatmap-${index}`;

            div.appendChild(title);
            div.appendChild(chartDiv);
            container.appendChild(div);

            renderHeatmapExample(chartDiv.id, {
                weeks: 12,
                colorScale: scheme.scale,
                title: `${scheme.name} - Last 12 Weeks`
            });
        });
    }

    /**
     * Example: Real data integration
     * This shows how to integrate with actual backend data
     */
    function renderRealDataHeatmap(elementId, username) {
        // In a real implementation, fetch data from backend:
        // fetch(`/api/person/${username}/daily-activity?weeks=12`)
        //     .then(response => response.json())
        //     .then(data => {
        //         const { data, layout, config } = createContributionHeatmap({
        //             dailyData: data.daily_contributions,
        //             title: `${username}'s Activity`,
        //             colorScale: 'green'
        //         });
        //         Plotly.newPlot(elementId, data, layout, config);
        //     });

        // For demo, use sample data
        renderHeatmapExample(elementId, {
            title: `${username}'s Activity`
        });
    }

    /**
     * Add interactive controls for heatmap
     */
    function addHeatmapControls() {
        const controls = document.getElementById('heatmap-controls');
        if (!controls) return;

        controls.innerHTML = `
            <div style="padding: 20px; background: var(--bg-secondary); border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Contribution Heatmap Controls</h3>
                <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px;">
                    <div>
                        <label for="weeks-select" style="display: block; margin-bottom: 5px;">Weeks to Display:</label>
                        <select id="weeks-select" style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                            <option value="4">4 weeks</option>
                            <option value="8">8 weeks</option>
                            <option value="12" selected>12 weeks</option>
                            <option value="26">26 weeks (6 months)</option>
                            <option value="52">52 weeks (1 year)</option>
                        </select>
                    </div>
                    <div>
                        <label for="color-select" style="display: block; margin-bottom: 5px;">Color Scheme:</label>
                        <select id="color-select" style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                            <option value="green" selected>Green (GitHub)</option>
                            <option value="blue">Blue</option>
                            <option value="purple">Purple</option>
                            <option value="orange">Orange</option>
                        </select>
                    </div>
                    <div style="display: flex; align-items: flex-end;">
                        <button id="update-heatmap" class="btn-primary" style="padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Update Heatmap
                        </button>
                    </div>
                </div>
                <div id="demo-heatmap" style="margin-top: 20px;"></div>
            </div>
        `;

        // Add event listener
        document.getElementById('update-heatmap').addEventListener('click', function() {
            const weeks = parseInt(document.getElementById('weeks-select').value);
            const colorScale = document.getElementById('color-select').value;

            renderHeatmapExample('demo-heatmap', {
                weeks: weeks,
                colorScale: colorScale,
                title: `Contribution Activity (Last ${weeks} Weeks)`
            });
        });

        // Render initial heatmap
        renderHeatmapExample('demo-heatmap', {
            weeks: 12,
            colorScale: 'green'
        });
    }

    // Export demo functions
    window.HeatmapDemo = {
        render: renderHeatmapExample,
        renderMultiple: renderMultipleHeatmaps,
        renderReal: renderRealDataHeatmap,
        addControls: addHeatmapControls,
        generateData: generateSampleData
    };

    // Auto-initialize if demo elements exist
    document.addEventListener('DOMContentLoaded', function() {
        if (document.getElementById('heatmap-controls')) {
            addHeatmapControls();
        }
        if (document.getElementById('heatmap-examples')) {
            renderMultipleHeatmaps();
        }
    });
})();
