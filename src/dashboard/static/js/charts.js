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
 * @returns {string} Formatted HTML tooltip
 */
function createEnhancedTooltip(data) {
    const parts = [];

    if (data.name) {
        parts.push(`<b>${data.name}</b>`);
    }

    if (data.x !== undefined) {
        parts.push(`Date: ${data.x}`);
    }

    if (data.y !== undefined) {
        parts.push(`Value: ${data.y}`);
    }

    if (data.customdata) {
        // Add custom data fields
        Object.entries(data.customdata).forEach(([key, value]) => {
            parts.push(`${key}: ${value}`);
        });
    }

    return parts.join('<br>');
}

/**
 * Apply semantic colors to trend chart data
 * @param {Array} weeks - Array of week labels
 * @param {Object} createdData - Created items by week
 * @param {Object} resolvedData - Resolved items by week
 * @returns {Array} Array of Plotly trace objects
 */
function getTrendChartTraces(weeks, createdData, resolvedData) {
    const netDifference = weeks.map(w => (createdData[w] || 0) - (resolvedData[w] || 0));

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
            hovertemplate: '<b>Created</b><br>' +
                          'Week: %{x}<br>' +
                          'Count: %{y}<br>' +
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
            hovertemplate: '<b>Resolved</b><br>' +
                          'Week: %{x}<br>' +
                          'Count: %{y}<br>' +
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
            hovertemplate: '<b>Net Change</b><br>' +
                          'Week: %{x}<br>' +
                          'Difference: %{y}<br>' +
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
    const { x, y, names, colors, title, xLabel, yLabel, customData } = params;

    const data = [{
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
        hovertemplate: '<b>%{text}</b><br>' +
                      (xLabel || 'Category') + ': %{x}<br>' +
                      (yLabel || 'Value') + ': %{y}<br>' +
                      '<extra></extra>',
        customdata: customData
    }];

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

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CHART_COLORS,
        getChartColors,
        getChartLayout,
        getChartConfig,
        createEnhancedTooltip,
        getTrendChartTraces,
        createBarChart,
        createLineChart,
        createPieChart,
        addChartClickHandler,
        updateChart
    };
}
