(function() {
    const root = document.documentElement;
    const body = document.body;
    const toggle = document.getElementById('themeToggle');
    const STORAGE_KEY = 'ui-theme';

    function applyTheme(theme) {
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {}
        if (toggle) {
            toggle.innerHTML = theme === 'dark' 
                ? '<i class="fas fa-sun"></i>' 
                : '<i class="fas fa-moon"></i>';
        }
    }

    function initTheme() {
        let saved = null;
        try {
            saved = localStorage.getItem(STORAGE_KEY);
        } catch (e) {}
        if (saved === 'light' || saved === 'dark') {
            applyTheme(saved);
            return;
        }
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(prefersDark ? 'dark' : 'light');
    }

    if (toggle) {
        toggle.addEventListener('click', function() {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            applyTheme(isDark ? 'light' : 'dark');
        });
    }

    // Initialize
    initTheme();
})();