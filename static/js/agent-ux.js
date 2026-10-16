/**
 * ============================================================================
 * ERGONOMIE AGENT DE TERRAIN & VALIDATION EN TEMPS RÉEL
 * Régie des Parkings Publics - Mairie de Bujumbura
 * ============================================================================
 * Fonctionnalités :
 * 1. Formatage en direct des plaques d'immatriculation (Majuscules, espacement)
 * 2. Validation instantanée visuelle (Feedback temps réel sans rechargement)
 * 3. Calculateur de rendu de monnaie en BIF pour agent de guichet
 * 4. Auto-génération des attributs data-label pour tables responsives mobile
 * ============================================================================
 */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // ------------------------------------------------------------------------
    // 1. FORMATAGE ET VALIDATION EN TEMPS RÉEL DES PLAQUES D'IMMATRICULATION
    // ------------------------------------------------------------------------
    const plateInputs = document.querySelectorAll('input[name="plate_number"], input#id_plate_number, input[name="q"]');

    plateInputs.forEach(input => {
        // Détection et création du conteneur de feedback visuel en temps réel
        let feedbackEl = input.parentElement.querySelector('.live-plate-feedback');
        if (!feedbackEl && input.name === 'plate_number') {
            feedbackEl = document.createElement('div');
            feedbackEl.className = 'live-plate-feedback small mt-2 d-none';
            input.parentElement.appendChild(feedbackEl);
        }

        input.addEventListener('input', function () {
            // Nettoyage : Majuscules automatiques et suppression des espaces superflus
            const start = this.selectionStart;
            const end = this.selectionEnd;
            const originalVal = this.value;
            const cleanedVal = originalVal.toUpperCase();

            if (originalVal !== cleanedVal) {
                this.value = cleanedVal;
                this.setSelectionRange(start, end);
            }

            // Validation visuelle en direct si c'est le champ d'enregistrement
            if (feedbackEl) {
                const val = this.value.trim();
                if (val.length === 0) {
                    feedbackEl.className = 'live-plate-feedback small mt-2 d-none';
                    input.classList.remove('is-valid', 'is-invalid');
                } else if (val.length < 3) {
                    feedbackEl.className = 'live-plate-feedback small mt-2 text-danger fw-semibold';
                    feedbackEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation me-1"></i> Immatriculation trop courte (min. 3 caractères)';
                    input.classList.add('is-invalid');
                    input.classList.remove('is-valid');
                } else {
                    feedbackEl.className = 'live-plate-feedback small mt-2 text-success fw-semibold';
                    feedbackEl.innerHTML = `<i class="fa-solid fa-circle-check me-1"></i> Format valide : <span class="badge bg-dark text-white font-monospace ms-1">${val}</span>`;
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                }
            }
        });
    });

    // ------------------------------------------------------------------------
    // 2. CALCULATEUR INSTANTANÉ DE MONNAIE À RENDRE EN BIF (GUICHET / SORTIE)
    // ------------------------------------------------------------------------
    const amountDueElement = document.querySelector('[data-amount-due]');
    const amountPaidInput = document.querySelector('input[name="amount_paid"], #id_amount_paid');

    if (amountDueElement && amountPaidInput) {
        const amountDue = parseFloat(amountDueElement.getAttribute('data-amount-due')) || 0;
        
        // Création du bloc d'affichage de la monnaie
        const changeBox = document.createElement('div');
        changeBox.className = 'change-calculator-box mt-3 d-flex justify-content-between align-items-center';
        changeBox.innerHTML = `
            <div>
                <span class="small fw-semibold text-muted d-block">Monnaie à rendre au conducteur :</span>
                <span class="fs-5 fw-bold text-success" id="changeAmountDisplay">0 BIF</span>
            </div>
            <div id="changeStatusBadge">
                <span class="badge bg-secondary">En attente</span>
            </div>
        `;
        amountPaidInput.parentElement.parentElement.appendChild(changeBox);

        function updateChange() {
            const paid = parseFloat(amountPaidInput.value) || 0;
            const diff = paid - amountDue;
            const display = document.getElementById('changeAmountDisplay');
            const badge = document.getElementById('changeStatusBadge');

            if (paid <= 0) {
                display.innerText = '0 BIF';
                display.className = 'fs-5 fw-bold text-muted';
                badge.innerHTML = '<span class="badge bg-secondary">En attente</span>';
            } else if (diff < 0) {
                display.innerText = `Reste dû : ${Math.abs(diff).toLocaleString('fr-FR')} BIF`;
                display.className = 'fs-5 fw-bold text-danger';
                badge.innerHTML = '<span class="badge bg-danger">Montant insuffisant</span>';
            } else if (diff === 0) {
                display.innerText = 'Compte exact (0 BIF)';
                display.className = 'fs-5 fw-bold text-success';
                badge.innerHTML = '<span class="badge bg-success">Compte exact</span>';
            } else {
                display.innerText = `+ ${diff.toLocaleString('fr-FR')} BIF`;
                display.className = 'fs-5 fw-bold text-success';
                badge.innerHTML = '<span class="badge bg-success">À rendre</span>';
            }
        }

        amountPaidInput.addEventListener('input', updateChange);
        updateChange();
    }

    // ------------------------------------------------------------------------
    // 3. AUTO-COMPLÉTION DES ATTRIBUTS data-label POUR LES TABLES MOBILE
    // ------------------------------------------------------------------------
    const mobileTables = document.querySelectorAll('.table-mobile-cards');
    mobileTables.forEach(table => {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim());
        if (headers.length > 0) {
            table.querySelectorAll('tbody tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, idx) => {
                    if (!cell.getAttribute('data-label') && headers[idx]) {
                        cell.setAttribute('data-label', headers[idx]);
                    }
                });
            });
        }
    });
});
