/**
 * Gestion du Thème (Mode Clair / Mode Sombre) pour l'Application de Parking
 * Bujumbura International University (BIU)
 */

(function () {
    // 1. Initialisation immédiate pour éviter le scintillement (FOUT)
    const STORAGE_KEY = 'bjm_parking_theme';
    const savedTheme = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme ? savedTheme : (prefersDark ? 'dark' : 'light');

    document.documentElement.setAttribute('data-bs-theme', initialTheme);

    function updateToggleIcon(theme) {
        const icon = document.getElementById('themeToggleIcon');
        const btn = document.getElementById('themeToggleBtn');
        if (!icon) return;

        if (theme === 'dark') {
            icon.className = 'fa-solid fa-sun text-warning';
            if (btn) {
                btn.setAttribute('aria-label', 'Activer le mode clair');
                btn.setAttribute('title', 'Activer le mode clair');
            }
        } else {
            icon.className = 'fa-solid fa-moon text-secondary';
            if (btn) {
                btn.setAttribute('aria-label', 'Activer le mode sombre');
                btn.setAttribute('title', 'Activer le mode sombre');
            }
        }
    }

    // 2. Bascule dynamique au clic
    window.toggleAppTheme = function () {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-bs-theme', nextTheme);
        localStorage.setItem(STORAGE_KEY, nextTheme);
        updateToggleIcon(nextTheme);
    };

    // 3. Mise à jour des icônes après chargement du DOM
    document.addEventListener('DOMContentLoaded', function () {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        updateToggleIcon(currentTheme);

        const btn = document.getElementById('themeToggleBtn');
        if (btn) {
            btn.addEventListener('click', window.toggleAppTheme);
        }
    });
})();
