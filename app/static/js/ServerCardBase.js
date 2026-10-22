import { hubUrl } from './urls.js';

/**
 * Carte serveur commune. Chaque type (minecraft, palworld, generic) hérite de cette classe
 * et ne définit que `cssClass` (classe CSS racine, voir static/css/server-cards/).
 */
export class ServerCardBase extends HTMLElement {
    get cssClass() { return 'generic-server-card'; }

    connectedCallback() {

        const serverID  = this.getAttribute('serverID')  || null;
        const name      = this.getAttribute('name')      || null;
        const status    = this.getAttribute('status')    || null;
        const cpuUsed   = parseFloat(this.getAttribute('cpuUsed'))   || 0.0;
        const ramUsed   = parseFloat(this.getAttribute('ramUsed'))   || 0.0;
        const ramLimit  = parseFloat(this.getAttribute('ramLimit'))  || 0.0;
        const diskUsed  = parseFloat(this.getAttribute('diskUsed'))  || 0.0;
        const diskLimit = parseFloat(this.getAttribute('diskLimit')) || 0.0;

        const isOnline = status === 'running' || status === 'starting';

        // Pourcentages pour les barres
        const ramPct  = ramLimit  > 0 ? Math.min((ramUsed  / ramLimit)  * 100, 100) : 0;
        const diskPct = diskLimit > 0 ? Math.min((diskUsed / diskLimit) * 100, 100) : 0;
        const cpuPct  = Math.min(cpuUsed, 100);

        // Label status traduit
        const statusLabels = {
            running:  'En ligne',
            offline:  'Hors ligne',
            starting: 'Démarrage',
            stopping: 'Arrêt…',
        };
        const statusLabel = statusLabels[status] || 'Inconnu';

        // Formatage Mo → Go si besoin
        const fmt = (mo) => mo >= 1024 ? `${(mo / 1024).toFixed(1)} Go` : `${mo} Mo`;

        this.innerHTML = `
            <div class="${this.cssClass}">

                <div class="server-main-infos">
                    <div class="name">${this._escapeHtml(name)}</div>
                    <div class="server-id">${this._escapeHtml(serverID)}</div>
                    <div class="status-badge ${status || 'offline'}">
                        <span class="status-dot"></span>
                        ${statusLabel}
                    </div>
                </div>

                <div class="server-infos">

                    <div class="resource-row">
                        <div class="resource-label">
                            <span>CPU</span>
                            <span>${isOnline ? cpuUsed.toFixed(1) + '%' : '—'}</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill ${cpuPct > 80 ? 'alert' : cpuPct > 60 ? 'warn' : ''}"
                                 style="width: ${isOnline ? cpuPct : 0}%"></div>
                        </div>
                    </div>

                    <div class="resource-row">
                        <div class="resource-label">
                            <span>RAM</span>
                            <span>${isOnline ? `${fmt(ramUsed)} / ${fmt(ramLimit)}` : '—'}</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill ${ramPct > 80 ? 'alert' : ramPct > 60 ? 'warn' : ''}"
                                 style="width: ${isOnline ? ramPct : 0}%"></div>
                        </div>
                    </div>

                    <div class="resource-row">
                        <div class="resource-label">
                            <span>DISQUE</span>
                            <span>${isOnline ? `${fmt(diskUsed)} / ${fmt(diskLimit)}` : '—'}</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill ${diskPct > 80 ? 'alert' : diskPct > 60 ? 'warn' : ''}"
                                 style="width: ${isOnline ? diskPct : 0}%"></div>
                        </div>
                    </div>

                </div>

                <div class="buttons">
                    ${status === 'running'
                        ? `<button class="stop-button"    data-id="${this._escapeHtml(serverID)}">■ Stop</button>`
                        : `<button class="start-button"   data-id="${this._escapeHtml(serverID)}">▶ Démarrer</button>`
                    }
                    <button class="details-button" data-id="${this._escapeHtml(serverID)}">Détails</button>
                </div>

            </div>
        `;

        this._attachEventListeners(serverID);
    }

    /**
     * Échappe les caractères HTML pour éviter les injections XSS
     */
    _escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Attache les event listeners aux boutons
     */
    _attachEventListeners(serverID) {
        // ── Bouton Start ──
        const startBtn = this.querySelector('.start-button');
        if (startBtn) {
            startBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this._handlePowerAction(startBtn, 'start', serverID);
            });
        }

        // ── Bouton Stop ──
        const stopBtn = this.querySelector('.stop-button');
        if (stopBtn) {
            stopBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this._handlePowerAction(stopBtn, 'stop', serverID);
            });
        }

        // ── Bouton Détails ──
        const detailsBtn = this.querySelector('.details-button');
        if (detailsBtn) {
            detailsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = hubUrl(encodeURIComponent(serverID));
            });
        }
    }

    /**
     * Gère les actions de contrôle d'alimentation (start/stop/restart/kill)
     */
    async _handlePowerAction(button, signal, serverID) {
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '…';

        try {
            const response = await fetch(hubUrl(`api/servers/${encodeURIComponent(serverID)}/power`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ signal }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP ${response.status}`);
            }

            // Succès — attendre un peu avant de réactualiser
            await new Promise(resolve => setTimeout(resolve, 1000));
            this._notifyRefresh();

        } catch (error) {
            console.error(`Power action error (${signal}):`, error);
            // Restaurer le bouton en cas d'erreur
            button.disabled = false;
            button.textContent = originalText;
            this._showToast(`Erreur: ${error.message}`, 'error');
        }
    }

    /**
     * Envoie un événement personnalisé pour demander un refresh au parent
     */
    _notifyRefresh() {
        this.dispatchEvent(new CustomEvent('server-action-complete', {
            bubbles: true,
            composed: true,
        }));
    }

    /**
     * Affiche une notification toast (à implémenter dans le parent)
     */
    _showToast(message, type = 'info') {
        this.dispatchEvent(new CustomEvent('show-toast', {
            bubbles: true,
            composed: true,
            detail: { message, type },
        }));
    }
}

