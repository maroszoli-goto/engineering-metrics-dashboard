// Theme Toggle Functionality
// Load saved theme preference or default to light mode
const currentTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', currentTheme);

// Update button text based on current theme
function updateButtonText() {
    const theme = document.documentElement.getAttribute('data-theme');

    // Update standalone theme toggle button (if exists)
    const button = document.querySelector('.theme-toggle');
    if (button) {
        button.textContent = theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
    }

    // Update theme toggle in hamburger menu
    const menuButton = document.querySelector('.theme-toggle-menu');
    if (menuButton) {
        const icon = menuButton.querySelector('.theme-icon');
        const text = menuButton.querySelector('.theme-text');
        if (icon && text) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
            text.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
        }
    }
}

// Toggle theme function
function toggleTheme() {
    const theme = document.documentElement.getAttribute('data-theme');
    const newTheme = theme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update button text
    updateButtonText();

    // Update Plotly charts if they exist
    updatePlotlyTheme(newTheme);
}

// Update Plotly chart themes
function updatePlotlyTheme(theme) {
    const isDark = theme === 'dark';

    const layout = {
        paper_bgcolor: isDark ? '#2d2d2d' : '#ffffff',
        plot_bgcolor: isDark ? '#2d2d2d' : '#ffffff',
        font: {
            color: isDark ? '#e0e0e0' : '#2c3e50'
        },
        xaxis: {
            gridcolor: isDark ? '#444' : '#ecf0f1',
            color: isDark ? '#e0e0e0' : '#2c3e50'
        },
        yaxis: {
            gridcolor: isDark ? '#444' : '#ecf0f1',
            color: isDark ? '#e0e0e0' : '#2c3e50'
        }
    };

    // Update all Plotly charts on the page
    const plotlyDivs = document.querySelectorAll('[id$="-comparison"], [id^="throughput-"]');
    plotlyDivs.forEach(div => {
        if (div.data) {  // Check if it's a Plotly chart
            Plotly.relayout(div.id, layout);
        }
    });
}

// Initialize button text on page load
document.addEventListener('DOMContentLoaded', function() {
    updateButtonText();
});

// Cache reload functionality
function reloadCache() {
    const btn = document.getElementById('reload-btn');
    const icon = document.getElementById('reload-icon');
    const text = document.getElementById('reload-text');

    // Disable button and show loading state
    btn.disabled = true;
    btn.style.opacity = '0.6';
    btn.style.cursor = 'not-allowed';
    icon.textContent = '⏳';
    text.textContent = 'Reloading...';

    // Show loading toast
    const loadingToast = toast.loading('Reloading metrics cache...');

    // Get current URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const range = urlParams.get('range') || '90d';
    const env = urlParams.get('env') || 'prod';

    fetch(`/api/reload-cache?range=${range}&env=${env}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // Dismiss loading toast
        toast.dismiss(loadingToast);

        if (data.status === 'success') {
            toast.success('Cache reloaded successfully', {
                description: 'Page will refresh in a moment...'
            });
            // Reload page after short delay to show success message
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            toast.error('Failed to reload cache', {
                description: data.message || 'Unknown error occurred'
            });

            // Reset button state
            resetReloadButton(btn, icon, text);
        }
    })
    .catch(error => {
        // Dismiss loading toast
        toast.dismiss(loadingToast);

        toast.error('Network error', {
            description: 'Please check your connection and try again'
        });

        // Reset button state
        resetReloadButton(btn, icon, text);
    });
}

// Helper function to reset reload button state
function resetReloadButton(btn, icon, text) {
    btn.disabled = false;
    btn.style.opacity = '1';
    btn.style.cursor = 'pointer';
    icon.textContent = '🔄';
    text.textContent = 'Reload Data';
}
