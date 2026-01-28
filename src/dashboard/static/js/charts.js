// Chart color constants and utilities for Team Metrics Dashboard

// Semantic color system for consistent chart styling
const CHART_COLORS = {
    // Semantic colors for created/resolved patterns
    CREATED: '#e74c3c',      // Red - items added/created
    RESOLVED: '#2ecc71',     // Green - items completed/closed
    NET: '#3498db',          // Blue - difference/net change

    // Team identity colors
    TEAM_PRIMARY: '#3498db',     // Blue
    TEAM_SECONDARY: '#9b59b6',   // Purple

    // Activity type colors
    PRS: '#3498db',          // Blue
    REVIEWS: '#9b59b6',      // Purple
    COMMITS: '#27ae60',      // Green
    JIRA_COMPLETED: '#f39c12',  // Orange
    JIRA_WIP: '#e74c3c',     // Red

    // Status colors
    SUCCESS: '#27ae60',      // Green
    WARNING: '#f39c12',      // Orange
    DANGER: '#e74c3c',       // Red
    INFO: '#3498db',         // Blue

    // Pie chart palette (diverse colors)
    PIE_PALETTE: ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
};

/**
 * Get theme-aware background and grid colors for Plotly charts
 * @returns {Object} Colors object for chart styling
 */
function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        paper_bgcolor: isDark ? '#2d2d2d' : '#ffffff',
        plot_bgcolor: isDark ? '#2d2d2d' : '#ffffff',
        font_color: isDark ? '#e0e0e0' : '#2c3e50',
        grid_color: isDark ? '#444' : '#ecf0f1'
    };
}

/**
 * Get standard layout configuration for Plotly charts
 * @param {Object} customConfig - Custom configuration to merge
 * @returns {Object} Complete layout configuration
 */
function getChartLayout(customConfig = {}) {
    const colors = getChartColors();
    const defaultConfig = {
        paper_bgcolor: colors.paper_bgcolor,
        plot_bgcolor: colors.plot_bgcolor,
        font: { color: colors.font_color, size: 12 },
        xaxis: {
            gridcolor: colors.grid_color,
            color: colors.font_color,
            showgrid: true,
            zeroline: true
        },
        yaxis: {
            gridcolor: colors.grid_color,
            color: colors.font_color,
            showgrid: true,
            zeroline: true
        },
        // Enhanced interactivity
        hovermode: 'closest',
        hoverlabel: {
            bgcolor: colors.paper_bgcolor,
            bordercolor: colors.grid_color,
            font: {
                color: colors.font_color,
                size: 13
            }
        },
        // Margins
        margin: { l: 60, r: 30, t: 30, b: 60 },
        // Animation
        transition: {
            duration: 500,
            easing: 'cubic-in-out'
        }
    };

    // Deep merge custom config with defaults
    return Object.assign({}, defaultConfig, customConfig);
}

/**
 * Get standard configuration for Plotly charts (includes responsive and interaction settings)
 * @returns {Object} Plotly configuration object
 */
function getChartConfig() {
    return {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        toImageButtonOptions: {
            format: 'png',
            filename: 'team_metrics_chart',
            height: 800,
            width: 1200,
            scale: 2
        }
    };
}

/**
 * Create enhanced tooltip text with rich formatting
 * @param {Object} data - Data point information
 * @param {Object} options - Tooltip options
 * @returns {string} Formatted HTML tooltip
 */
function createEnhancedTooltip(data, options = {}) {
    const parts = [];

    // Title/Name
    if (data.name) {
        parts.push(`<b>${data.name}</b>`);
    }

    // Primary metric
    if (data.x !== undefined && data.y !== undefined) {
        parts.push(`${options.xLabel || 'Date'}: ${data.x}`);
        parts.push(`${options.yLabel || 'Value'}: ${data.y}`);
    }

    // Trend indicator
    if (data.trend !== undefined) {
        const arrow = data.trend > 0 ? '↑' : data.trend < 0 ? '↓' : '→';
        const color = data.trend > 0 ? '#27ae60' : data.trend < 0 ? '#e74c3c' : '#7f8c8d';
        const percentage = Math.abs(data.trend).toFixed(1);
        parts.push(`<span style="color: ${color}">${arrow} ${percentage}% vs previous</span>`);
    }

    // Additional metrics
    if (data.customdata) {
        if (typeof data.customdata === 'object' && !Array.isArray(data.customdata)) {
            // Object with named fields
            Object.entries(data.customdata).forEach(([key, value]) => {
                parts.push(`${key}: ${value}`);
            });
        } else if (Array.isArray(data.customdata)) {
            // Array with custom labels
            data.customdata.forEach((value, index) => {
                const label = options.customLabels && options.customLabels[index];
                if (label) {
                    parts.push(`${label}: ${value}`);
                }
            });
        }
    }

    // Context info (e.g., "Click to see details")
    if (options.clickable) {
        parts.push('<i style="color: #7f8c8d; font-size: 11px;">Click for details</i>');
    }

    return parts.join('<br>');
}

/**
 * Format number with trend indicator
 * @param {number} value - Current value
 * @param {number} previousValue - Previous value for comparison
 * @returns {string} Formatted string with trend
 */
function formatWithTrend(value, previousValue) {
    if (previousValue === undefined || previousValue === null || previousValue === 0) {
        return value.toString();
    }
    const change = ((value - previousValue) / previousValue) * 100;
    const arrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';
    const color = change > 0 ? '#27ae60' : change < 0 ? '#e74c3c' : '#7f8c8d';
    return `${value} <span style="color: ${color}">${arrow} ${Math.abs(change).toFixed(1)}%</span>`;
}

/**
 * Apply semantic colors to trend chart data with enhanced tooltips
 * @param {Array} weeks - Array of week labels
 * @param {Object} createdData - Created items by week
 * @param {Object} resolvedData - Resolved items by week
 * @param {Object} options - Additional options (cumulative data, etc.)
 * @returns {Array} Array of Plotly trace objects
 */
function getTrendChartTraces(weeks, createdData, resolvedData, options = {}) {
    const netDifference = weeks.map(w => (createdData[w] || 0) - (resolvedData[w] || 0));

    // Calculate running totals for context
    let createdTotal = 0;
    let resolvedTotal = 0;
    const runningTotals = weeks.map(w => {
        createdTotal += (createdData[w] || 0);
        resolvedTotal += (resolvedData[w] || 0);
        return { created: createdTotal, resolved: resolvedTotal, net: createdTotal - resolvedTotal };
    });

    return [
        {
            x: weeks,
            y: weeks.map(w => createdData[w] || 0),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Created',
            line: { color: CHART_COLORS.CREATED, width: 2 },
            marker: { color: CHART_COLORS.CREATED, size: 6 },
            xaxis: 'x',
            yaxis: 'y',
            customdata: weeks.map((w, i) => [runningTotals[i].created, runningTotals[i].net]),
            hovertemplate: '<b>Created</b><br>' +
                          'Week: %{x}<br>' +
                          'Count: %{y}<br>' +
                          'Running Total: %{customdata[0]}<br>' +
                          'Net Backlog: %{customdata[1]}<br>' +
                          '<extra></extra>'
        },
        {
            x: weeks,
            y: weeks.map(w => resolvedData[w] || 0),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Resolved',
            line: { color: CHART_COLORS.RESOLVED, width: 2 },
            marker: { color: CHART_COLORS.RESOLVED, size: 6 },
            xaxis: 'x',
            yaxis: 'y',
            customdata: weeks.map((w, i) => [runningTotals[i].resolved, runningTotals[i].net]),
            hovertemplate: '<b>Resolved</b><br>' +
                          'Week: %{x}<br>' +
                          'Count: %{y}<br>' +
                          'Running Total: %{customdata[0]}<br>' +
                          'Net Backlog: %{customdata[1]}<br>' +
                          '<extra></extra>'
        },
        {
            x: weeks,
            y: netDifference,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Net (Created - Resolved)',
            line: { color: CHART_COLORS.NET, width: 2 },
            marker: { color: CHART_COLORS.NET, size: 6 },
            xaxis: 'x2',
            yaxis: 'y2',
            customdata: weeks.map((w, i) => [
                createdData[w] || 0,
                resolvedData[w] || 0,
                runningTotals[i].net
            ]),
            hovertemplate: '<b>Net Change</b><br>' +
                          'Week: %{x}<br>' +
                          'Net: %{y}<br>' +
                          'Created: %{customdata[0]}<br>' +
                          'Resolved: %{customdata[1]}<br>' +
                          'Cumulative Backlog: %{customdata[2]}<br>' +
                          '<extra></extra>'
        }
    ];
}

/**
 * Create a bar chart with enhanced tooltips
 * @param {Object} params - Chart parameters
 * @returns {Object} Plotly data and layout
 */
function createBarChart(params) {
    const { x, y, names, colors, title, xLabel, yLabel, customData, tooltipExtra } = params;

    // Calculate percentages and ranks if multiple bars
    let hovertemplate = '<b>%{text}</b><br>' +
                       (xLabel || 'Category') + ': %{x}<br>' +
                       (yLabel || 'Value') + ': %{y}<br>';

    // Add percentage of total if data available
    if (y && y.length > 0) {
        const total = y.reduce((sum, val) => sum + val, 0);
        const percentages = y.map(val => ((val / total) * 100).toFixed(1));

        // Add percentages to customdata
        const enhancedCustomData = y.map((val, i) => {
            const base = customData && customData[i] ? customData[i] : [];
            return Array.isArray(base) ? [...base, percentages[i]] : [base, percentages[i]];
        });

        hovertemplate += 'Percentage: %{customdata[' + (customData ? customData[0]?.length || 0 : 0) + ']}%<br>';

        // Add rank
        const sorted = [...y].sort((a, b) => b - a);
        const ranks = y.map(val => sorted.indexOf(val) + 1);
        hovertemplate += 'Rank: ' + ranks.map((r, i) => i === '%{pointNumber}' ? r : '').filter(Boolean)[0] + '<br>';

        data = [{
            x: x,
            y: y,
            type: 'bar',
            marker: {
                color: colors || CHART_COLORS.TEAM_PRIMARY,
                line: {
                    color: getChartColors().grid_color,
                    width: 1
                }
            },
            text: names || x,
            hovertemplate: hovertemplate + '<extra></extra>',
            customdata: enhancedCustomData
        }];
    } else {
        data = [{
            x: x,
            y: y,
            type: 'bar',
            marker: {
                color: colors || CHART_COLORS.TEAM_PRIMARY,
                line: {
                    color: getChartColors().grid_color,
                    width: 1
                }
            },
            text: names || x,
            hovertemplate: hovertemplate + '<extra></extra>',
            customdata: customData
        }];
    }

    const layout = getChartLayout({
        title: title,
        xaxis: { title: xLabel },
        yaxis: { title: yLabel },
        showlegend: false
    });

    return { data, layout, config: getChartConfig() };
}

/**
 * Create a line chart with enhanced tooltips
 * @param {Object} params - Chart parameters
 * @returns {Object} Plotly data and layout
 */
function createLineChart(params) {
    const { traces, title, xLabel, yLabel } = params;

    const data = traces.map(trace => ({
        x: trace.x,
        y: trace.y,
        type: 'scatter',
        mode: 'lines+markers',
        name: trace.name,
        line: {
            color: trace.color || CHART_COLORS.TEAM_PRIMARY,
            width: 2
        },
        marker: {
            color: trace.color || CHART_COLORS.TEAM_PRIMARY,
            size: 6
        },
        hovertemplate: '<b>' + trace.name + '</b><br>' +
                      (xLabel || 'X') + ': %{x}<br>' +
                      (yLabel || 'Y') + ': %{y}<br>' +
                      '<extra></extra>'
    }));

    const layout = getChartLayout({
        title: title,
        xaxis: { title: xLabel },
        yaxis: { title: yLabel },
        showlegend: traces.length > 1
    });

    return { data, layout, config: getChartConfig() };
}

/**
 * Create a pie chart with enhanced tooltips
 * @param {Object} params - Chart parameters
 * @returns {Object} Plotly data and layout
 */
function createPieChart(params) {
    const { labels, values, title, colors } = params;

    const data = [{
        labels: labels,
        values: values,
        type: 'pie',
        marker: {
            colors: colors || CHART_COLORS.PIE_PALETTE
        },
        hovertemplate: '<b>%{label}</b><br>' +
                      'Count: %{value}<br>' +
                      'Percentage: %{percent}<br>' +
                      '<extra></extra>',
        textinfo: 'label+percent',
        textposition: 'auto'
    }];

    const layout = getChartLayout({
        title: title,
        showlegend: true,
        legend: {
            orientation: 'v',
            x: 1.05,
            y: 0.5
        }
    });

    return { data, layout, config: getChartConfig() };
}

/**
 * Create a GitHub-style contribution heatmap
 * @param {Object} params - Heatmap parameters
 * @returns {Object} Plotly data and layout
 */
function createContributionHeatmap(params) {
    const { dailyData, title, startDate, endDate, colorScale } = params;

    // Convert daily data to week grid (7 rows x N columns)
    // dailyData should be: { 'YYYY-MM-DD': count, ... }

    const start = startDate ? new Date(startDate) : getDateWeeksAgo(12);
    const end = endDate ? new Date(endDate) : new Date();

    // Build week grid
    const weeks = [];
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    // Initialize grid: 7 days x N weeks
    const grid = Array(7).fill(null).map(() => []);
    const dateLabels = Array(7).fill(null).map(() => []);
    const customData = Array(7).fill(null).map(() => []);

    // Start from the first Sunday before or on start date
    const currentDate = new Date(start);
    const dayOfWeek = currentDate.getDay();
    currentDate.setDate(currentDate.getDate() - dayOfWeek);

    let weekCount = 0;
    const maxWeeks = 53; // Max weeks to display

    while (currentDate <= end && weekCount < maxWeeks) {
        // Process one week (Sunday to Saturday)
        for (let day = 0; day < 7; day++) {
            const dateStr = formatDateISO(currentDate);
            const count = dailyData[dateStr] || 0;

            grid[day][weekCount] = count;
            dateLabels[day][weekCount] = dateStr;
            customData[day][weekCount] = {
                date: formatDateShort(currentDate),
                count: count,
                day: dayLabels[day]
            };

            currentDate.setDate(currentDate.getDate() + 1);
        }
        weekCount++;
    }

    // Create x-axis labels (month names)
    const xLabels = [];
    const monthDate = new Date(start);
    monthDate.setDate(monthDate.getDate() - monthDate.getDay()); // Start from Sunday

    for (let i = 0; i < weekCount; i++) {
        const month = monthDate.toLocaleDateString('en-US', { month: 'short' });
        xLabels.push(i % 4 === 0 ? month : ''); // Show month every 4 weeks
        monthDate.setDate(monthDate.getDate() + 7);
    }

    // Determine color scale
    const maxValue = Math.max(...grid.flat());
    const colors = getHeatmapColorScale(colorScale, maxValue);

    const data = [{
        z: grid,
        x: xLabels,
        y: dayLabels,
        type: 'heatmap',
        colorscale: colors,
        showscale: true,
        hovertemplate: '<b>%{customdata.date}</b><br>' +
                      '%{customdata.day}<br>' +
                      'Contributions: %{z}<br>' +
                      '<extra></extra>',
        customdata: customData,
        colorbar: {
            title: 'Activity',
            titleside: 'right',
            tickmode: 'linear',
            tick0: 0,
            dtick: Math.ceil(maxValue / 4) || 1,
            len: 0.5,
            thickness: 15
        }
    }];

    const layout = getChartLayout({
        title: title || 'Contribution Activity',
        xaxis: {
            side: 'top',
            showgrid: false,
            zeroline: false,
            fixedrange: true
        },
        yaxis: {
            showgrid: false,
            zeroline: false,
            autorange: 'reversed',
            fixedrange: true
        },
        height: 200,
        margin: { l: 50, r: 50, t: 40, b: 20 }
    });

    return { data, layout, config: { ...getChartConfig(), displayModeBar: false } };
}

/**
 * Get heatmap color scale
 * @param {string} type - Color scale type (green, blue, purple)
 * @param {number} maxValue - Maximum value for scaling
 * @returns {Array} Plotly color scale
 */
function getHeatmapColorScale(type = 'green', maxValue) {
    const scales = {
        green: [
            [0, '#ebedf0'],
            [0.25, '#9be9a8'],
            [0.5, '#40c463'],
            [0.75, '#30a14e'],
            [1, '#216e39']
        ],
        blue: [
            [0, '#ebedf0'],
            [0.25, '#9ecae1'],
            [0.5, '#4292c6'],
            [0.75, '#2171b5'],
            [1, '#084594']
        ],
        purple: [
            [0, '#ebedf0'],
            [0.25, '#c994c7'],
            [0.5, '#df65b0'],
            [0.75, '#dd1c77'],
            [1, '#980043']
        ],
        orange: [
            [0, '#ebedf0'],
            [0.25, '#fdae6b'],
            [0.5, '#fd8d3c'],
            [0.75, '#e6550d'],
            [1, '#a63603']
        ]
    };

    return scales[type] || scales.green;
}

/**
 * Get date N weeks ago
 * @param {number} weeks - Number of weeks
 * @returns {Date} Date object
 */
function getDateWeeksAgo(weeks) {
    const date = new Date();
    date.setDate(date.getDate() - (weeks * 7));
    return date;
}

/**
 * Format date as ISO string (YYYY-MM-DD)
 * @param {Date} date - Date object
 * @returns {string} ISO date string
 */
function formatDateISO(date) {
    return date.toISOString().split('T')[0];
}

/**
 * Format date for display (MMM DD)
 * @param {Date} date - Date object
 * @returns {string} Formatted date
 */
function formatDateShort(date) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Add click event handler to chart for drill-down
 * @param {string} elementId - Chart element ID
 * @param {Function} callback - Callback function(pointData)
 */
function addChartClickHandler(elementId, callback) {
    const element = document.getElementById(elementId);
    if (element) {
        element.on('plotly_click', function(data) {
            const point = data.points[0];
            callback({
                x: point.x,
                y: point.y,
                label: point.label,
                customdata: point.customdata
            });
        });
    }
}

/**
 * Update chart with smooth animation
 * @param {string} elementId - Chart element ID
 * @param {Object} newData - New data to display
 * @param {Object} newLayout - New layout (optional)
 */
function updateChart(elementId, newData, newLayout = {}) {
    Plotly.animate(elementId, {
        data: newData,
        layout: newLayout
    }, {
        transition: {
            duration: 500,
            easing: 'cubic-in-out'
        },
        frame: {
            duration: 500
        }
    });
}

/**
 * Create DORA metrics tooltip with performance context
 * @param {Object} metrics - DORA metrics object
 * @returns {string} HTML tooltip content
 */
function createDORATooltip(metrics) {
    const parts = [];

    if (metrics.deploymentFrequency !== undefined) {
        const level = metrics.deploymentFrequency > 7 ? 'Elite' :
                     metrics.deploymentFrequency > 1 ? 'High' :
                     metrics.deploymentFrequency > 0.25 ? 'Medium' : 'Low';
        parts.push(`<b>Deployment Frequency</b>`);
        parts.push(`${metrics.deploymentFrequency.toFixed(2)} per week`);
        parts.push(`<span style="color: ${getDORAColor(level)}">Performance: ${level}</span>`);
        parts.push('');
    }

    if (metrics.leadTime !== undefined) {
        const hours = metrics.leadTime;
        const level = hours < 24 ? 'Elite' :
                     hours < 168 ? 'High' :
                     hours < 720 ? 'Medium' : 'Low';
        parts.push(`<b>Lead Time for Changes</b>`);
        parts.push(`${hours.toFixed(1)} hours`);
        parts.push(`<span style="color: ${getDORAColor(level)}">Performance: ${level}</span>`);
        parts.push('');
    }

    if (metrics.changeFailureRate !== undefined) {
        const rate = metrics.changeFailureRate;
        const level = rate < 15 ? 'Elite' :
                     rate < 20 ? 'High' :
                     rate < 30 ? 'Medium' : 'Low';
        parts.push(`<b>Change Failure Rate</b>`);
        parts.push(`${rate.toFixed(1)}%`);
        parts.push(`<span style="color: ${getDORAColor(level)}">Performance: ${level}</span>`);
        parts.push('');
    }

    if (metrics.mttr !== undefined) {
        const hours = metrics.mttr;
        const level = hours < 1 ? 'Elite' :
                     hours < 24 ? 'High' :
                     hours < 168 ? 'Medium' : 'Low';
        parts.push(`<b>Mean Time to Recover</b>`);
        parts.push(`${hours.toFixed(1)} hours`);
        parts.push(`<span style="color: ${getDORAColor(level)}">Performance: ${level}</span>`);
    }

    return parts.join('<br>');
}

/**
 * Get color for DORA performance level
 * @param {string} level - Performance level (Elite, High, Medium, Low)
 * @returns {string} Color hex code
 */
function getDORAColor(level) {
    switch (level) {
        case 'Elite': return '#27ae60';
        case 'High': return '#2ecc71';
        case 'Medium': return '#f39c12';
        case 'Low': return '#e74c3c';
        default: return '#7f8c8d';
    }
}

/**
 * Create performance comparison tooltip
 * @param {Object} params - Parameters (name, value, teamAverage, topPerformer)
 * @returns {string} HTML tooltip content
 */
function createPerformanceTooltip(params) {
    const { name, value, teamAverage, topPerformer } = params;
    const parts = [];

    parts.push(`<b>${name}</b>`);
    parts.push(`Value: ${value}`);

    if (teamAverage !== undefined) {
        const vsAverage = ((value - teamAverage) / teamAverage) * 100;
        const arrow = vsAverage > 0 ? '↑' : vsAverage < 0 ? '↓' : '→';
        const color = vsAverage > 0 ? '#27ae60' : vsAverage < 0 ? '#e74c3c' : '#7f8c8d';
        parts.push(`Team Average: ${teamAverage.toFixed(1)}`);
        parts.push(`<span style="color: ${color}">${arrow} ${Math.abs(vsAverage).toFixed(1)}% vs average</span>`);
    }

    if (topPerformer !== undefined) {
        const vsTop = ((value - topPerformer) / topPerformer) * 100;
        parts.push(`Top Performer: ${topPerformer.toFixed(1)}`);
        if (Math.abs(vsTop) < 1) {
            parts.push(`<span style="color: #27ae60">🏆 Top Performer!</span>`);
        } else {
            parts.push(`Gap to top: ${Math.abs(vsTop).toFixed(1)}%`);
        }
    }

    return parts.join('<br>');
}

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CHART_COLORS,
        getChartColors,
        getChartLayout,
        getChartConfig,
        createEnhancedTooltip,
        formatWithTrend,
        getTrendChartTraces,
        createBarChart,
        createLineChart,
        createPieChart,
        createContributionHeatmap,
        getHeatmapColorScale,
        addChartClickHandler,
        updateChart,
        createDORATooltip,
        getDORAColor,
        createPerformanceTooltip
    };
}
