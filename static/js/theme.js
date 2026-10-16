/**
 * ============================================================================
 * GESTION GLOBALE DU THÈME (MODE CLAIR / MODE SOMBRE)
 * Application Officielle de Gestion de Parking - Mairie de Bujumbura
 * ============================================================================
 * Caractéristiques :
 * - Anti-FOUC (Zéro scintillement visuel)
 * - Persistance via localStorage ('bjm_parking_theme')
 * - Application synchrone sur documentElement et body (data-bs-theme & data-theme)
 * - Écoute des préférences système OS (prefers-color-scheme)
 * - Synchronisation multi-boutons (Barre supérieure, barre mobile, etc.)
 * - Émission de l'événement personnalisé 'themeChanged'
 * ============================================================================
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'bjm_parking_theme';

    /**
     * Récupère le thème actuellement enregistré ou la préférence système OS
     * @returns {'light' | 'dark'}
     */
    function getPreferredTheme() {
        const storedTheme = localStorage.getItem(STORAGE_KEY);
        if (storedTheme === 'dark' || storedTheme === 'light') {
            return storedTheme;
        }
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    }

    /**
     * Applique le thème aux balises racine (html) et corps (body)
     * @param {'light' | 'dark'} theme
     */
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);

        if (document.body) {
            document.body.setAttribute('data-bs-theme', theme);
            document.body.setAttribute('data-theme', theme);
        }

        updateAllToggleButtons(theme);

        // Déclenchement d'un événement personnalisé pour les graphiques (Chart.js) ou widgets
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: theme }
        }));
    }

    /**
     * Met à jour les icônes et les attributs d'accessibilité de tous les boutons toggle
     * @param {'light' | 'dark'} theme
     */
    function updateAllToggleButtons(theme) {
        const buttons = document.querySelectorAll('.theme-toggle-btn, [data-action="toggle-theme"]');
        const isDark = (theme === 'dark');

        buttons.forEach(btn => {
            btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
            const label = isDark ? 'Activer le mode clair' : 'Activer le mode sombre';
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);

            const icon = btn.querySelector('.theme-icon, i');
            if (icon) {
                if (isDark) {
                    icon.className = 'fa-solid fa-sun text-warning';
                } else {
                    icon.className = 'fa-solid fa-moon text-secondary';
                }
            }
        });
    }

    /**
     * Fonction globale pour basculer de thème
     */
    window.toggleAppTheme = function () {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';

        localStorage.setItem(STORAGE_KEY, nextTheme);
        applyTheme(nextTheme);
    };

    // 1. Application immédiate au chargement du script
    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme);

    // 2. Écouteur des changements de préférence au niveau du système d'exploitation
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
            // N'écrase pas si l'utilisateur a fait un choix explicite manuel
            if (!localStorage.getItem(STORAGE_KEY)) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    // 3. Liaison des événements au chargement complet du DOM
    document.addEventListener('DOMContentLoaded', function () {
        const currentTheme = getPreferredTheme();
        applyTheme(currentTheme);

        // Attachement de l'événement clic à tous les boutons de basculement présents
        const buttons = document.querySelectorAll('.theme-toggle-btn, [data-action="toggle-theme"]');
        buttons.forEach(btn => {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                window.toggleAppTheme();
            });
        });
    });
})();
