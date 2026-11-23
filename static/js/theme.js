/**
 * Global Theme Manager: Light / Dark Mode
 * Brand: CourseRecommender AI
 * Project: Intelligent Course Recommendation System
 */

(function () {
    const STORAGE_KEY = 'course_recommender_theme';

    /**
     * Resolves the current theme from localStorage or defaults to 'light'.
     * @returns {string} 'light' or 'dark'
     */
    function getStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'light';
        } catch (e) {
            return 'light';
        }
    }

    /**
     * Applies the theme to <html> and updates all toggle buttons.
     * @param {string} theme - 'light' or 'dark'
     */
    function applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.documentElement.classList.add('dark-mode');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            document.documentElement.classList.remove('dark-mode');
        }
        updateToggleButtons(theme);
    }

    /**
     * Updates all theme toggle buttons across the page to match the current theme.
     * @param {string} theme - 'light' or 'dark'
     */
    function updateToggleButtons(theme) {
        const toggleButtons = document.querySelectorAll('.global-theme-toggle, .btn-theme-toggle, .btn-auth-theme');
        toggleButtons.forEach(btn => {
            const moonIcon = btn.querySelector('.theme-icon-moon, .bi-moon-stars-fill, .bi-moon-stars');
            const sunIcon = btn.querySelector('.theme-icon-sun, .bi-sun-fill, .bi-sun');

            if (theme === 'dark') {
                btn.setAttribute('title', 'Switch to Light Mode');
                btn.setAttribute('aria-label', 'Switch to Light Mode');
                if (moonIcon && sunIcon) {
                    moonIcon.classList.add('d-none');
                    sunIcon.classList.remove('d-none');
                } else if (moonIcon) {
                    moonIcon.className = 'bi bi-sun-fill text-warning theme-icon-sun';
                }
            } else {
                btn.setAttribute('title', 'Switch to Dark Mode');
                btn.setAttribute('aria-label', 'Switch to Dark Mode');
                if (moonIcon && sunIcon) {
                    moonIcon.classList.remove('d-none');
                    sunIcon.classList.add('d-none');
                } else if (sunIcon) {
                    sunIcon.className = 'bi bi-moon-stars-fill theme-icon-moon';
                }
            }
        });
    }

    /**
     * Toggles between 'light' and 'dark' and persists the preference.
     */
    function toggleTheme() {
        const currentTheme = getStoredTheme();
        const newTheme = (currentTheme === 'dark') ? 'light' : 'dark';
        try {
            localStorage.setItem(STORAGE_KEY, newTheme);
        } catch (e) {
            console.warn('Unable to persist theme to localStorage', e);
        }
        applyTheme(newTheme);
    }

    // Public API
    window.ThemeManager = {
        getTheme: getStoredTheme,
        setTheme: function (theme) {
            try {
                localStorage.setItem(STORAGE_KEY, theme);
            } catch (e) {}
            applyTheme(theme);
        },
        toggleTheme: toggleTheme
    };

    // Attach listeners and sync on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        const currentTheme = getStoredTheme();
        applyTheme(currentTheme);

        // Event delegation for all theme toggle buttons
        document.body.addEventListener('click', (e) => {
            const toggleBtn = e.target.closest('.global-theme-toggle, .btn-theme-toggle, .btn-auth-theme');
            if (toggleBtn) {
                e.preventDefault();
                toggleTheme();
            }
        });
    });
})();
