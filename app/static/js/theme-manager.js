// Dark Mode Theme Manager
// Handles theme switching, persistence, and system preference detection

class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        this.init();
    }

    init() {
        // Apply initial theme
        this.applyTheme(this.currentTheme);

        // Create theme toggle button
        this.createToggleButton();

        // Listen for system theme changes
        this.watchSystemTheme();

        console.log('[Theme] Initialized with theme:', this.currentTheme);
    }

    getSystemTheme() {
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    getStoredTheme() {
        // Get theme from localStorage
        return localStorage.getItem('theme');
    }

    setStoredTheme(theme) {
        // Save theme to localStorage
        localStorage.setItem('theme', theme);
    }

    applyTheme(theme) {
        // Apply theme to document
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        this.setStoredTheme(theme);

        // Update toggle button icon
        this.updateToggleIcon();

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));

        console.log('[Theme] Applied theme:', theme);
    }

    toggleTheme() {
        // Toggle between light and dark
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);

        // Track analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'theme_toggle', {
                event_category: 'engagement',
                event_label: newTheme
            });
        }
    }

    createToggleButton() {
        // Create floating theme toggle button
        const button = document.createElement('button');
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'Toggle dark mode');
        button.setAttribute('title', 'Toggle dark mode');

        // Add icon
        this.toggleButton = button;
        this.updateToggleIcon();

        // Add click handler
        button.addEventListener('click', () => this.toggleTheme());

        // Add to page
        document.body.appendChild(button);
    }

    updateToggleIcon() {
        if (!this.toggleButton) return;

        // Update icon based on current theme
        if (this.currentTheme === 'dark') {
            this.toggleButton.innerHTML = '☀️'; // Sun for light mode
            this.toggleButton.setAttribute('title', 'Switch to light mode');
        } else {
            this.toggleButton.innerHTML = '🌙'; // Moon for dark mode
            this.toggleButton.setAttribute('title', 'Switch to dark mode');
        }
    }

    watchSystemTheme() {
        // Watch for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

            darkModeQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('theme')) {
                    const newTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(newTheme);
                    console.log('[Theme] System theme changed to:', newTheme);
                }
            });
        }
    }

    // Public API
    setTheme(theme) {
        if (theme === 'light' || theme === 'dark') {
            this.applyTheme(theme);
        }
    }

    getTheme() {
        return this.currentTheme;
    }

    resetToSystem() {
        // Clear stored preference and use system theme
        localStorage.removeItem('theme');
        const systemTheme = this.getSystemTheme();
        this.applyTheme(systemTheme);
        console.log('[Theme] Reset to system theme:', systemTheme);
    }
}

// Initialize theme manager
let themeManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        themeManager = new ThemeManager();
    });
} else {
    themeManager = new ThemeManager();
}

// Export for use in other scripts
window.themeManager = themeManager;

// Keyboard shortcut: Ctrl/Cmd + Shift + D to toggle theme
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        if (window.themeManager) {
            window.themeManager.toggleTheme();
        }
    }
});
