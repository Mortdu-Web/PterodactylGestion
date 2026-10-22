import { hubUrl } from "./urls.js";

// ════════════════════════════════════════════════════════════
// Gestion du hub des serveurs — Minecraft, Palworld, Generic...
// ════════════════════════════════════════════════════════════

const refreshBtn = document.getElementById("refresh-btn");
const searchInput = document.getElementById("search-input");
const filterButtons = document.querySelectorAll(".mc-filter");
const toastsContainer = document.getElementById("toasts");

// Sections par type
const sections = {
  minecraft: {
    grid: document.getElementById("minecraft-grid"),
    empty: document.getElementById("minecraft-empty"),
    count: document.getElementById("minecraft-count"),
    section: document.getElementById("minecraft-section"),
  },
  palworld: {
    grid: document.getElementById("palworld-grid"),
    empty: document.getElementById("palworld-empty"),
    count: document.getElementById("palworld-count"),
    section: document.getElementById("palworld-section"),
  },
  generic: {
    grid: document.getElementById("generic-grid"),
    empty: document.getElementById("generic-empty"),
    count: document.getElementById("generic-count"),
    section: document.getElementById("generic-section"),
  },
};

const emptyStateGlobal = document.getElementById("empty-state-global");

let allServers = []; // Cache des données serveurs
let currentFilter = "all";
let searchTerm = "";

/**
 * Récupère tous les serveurs depuis le backend via <hub>/api/getServers
 */
async function fetchAllServers() {
  try {
    const response = await fetch(hubUrl("api/getServers"));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    allServers = await response.json();
    renderServers();
  } catch (error) {
    console.error("Erreur lors du chargement des serveurs:", error);
    showToast("Erreur lors du chargement des serveurs", "error");
  }
}

/**
 * Retourne le Web Component tag name pour un type de serveur
 */
function getComponentTag(type) {
  const tagMap = {
    minecraft: "minecraft-server-card",
    palworld: "palworld-server-card",
    generic: "generic-server-card",
  };
  return tagMap[type] || "generic-server-card";
}

/**
 * Filtre les serveurs selon les critères actuels
 */
function getFilteredServers() {
  return allServers.filter(server => {
    // Filtre par status
    if (currentFilter !== "all" && server.status !== currentFilter) {
      return false;
    }

    // Filtre par recherche
    const searchLower = searchTerm.toLowerCase();
    if (
      !server.name.toLowerCase().includes(searchLower) &&
      !server.id.toLowerCase().includes(searchLower)
    ) {
      return false;
    }

    return true;
  });
}

/**
 * Groupe les serveurs par type
 */
function groupServersByType(servers) {
  const grouped = {
    minecraft: [],
    palworld: [],
    generic: [],
  };

  servers.forEach(server => {
    const type = server.type || "generic";
    if (type in grouped) {
      grouped[type].push(server);
    } else {
      grouped.generic.push(server);
    }
  });

  return grouped;
}

/**
 * Affiche les cartes serveur filtrées et groupées par type
 */
function renderServers() {
  const filtered = getFilteredServers();
  const grouped = groupServersByType(filtered);

  let hasAnyServers = false;

  // Render chaque section
  Object.entries(sections).forEach(([type, section]) => {
    const servers = grouped[type];
    const count = servers.length;

    if (count === 0) {
      section.grid.innerHTML = "";
      section.empty.classList.remove("hidden");
      section.section.classList.add("hidden");
    } else {
      section.empty.classList.add("hidden");
      section.section.classList.remove("hidden");
      hasAnyServers = true;

      const tag = getComponentTag(type);
      section.grid.innerHTML = servers.map(server => `
        <${tag}
          serverID="${escapeHtml(server.id)}"
          name="${escapeHtml(server.name)}"
          type="${escapeHtml(server.type ?? '')}"
          status="${escapeHtml(server.status ?? '')}"
          cpuUsed="${parseFloat(server.cpuUsed ?? 0).toFixed(2)}"
          ramUsed="${parseFloat(server.ramUsed ?? 0).toFixed(2)}"
          ramLimit="${parseFloat(server.ramLimit ?? 0).toFixed(2)}"
          diskUsed="${parseFloat(server.diskUsed ?? 0).toFixed(2)}"
          diskLimit="${parseFloat(server.diskLimit ?? 0).toFixed(2)}"
        ></${tag}>
      `).join('');

      section.count.textContent = count;
    }
  });

  // Afficher/cacher l'état vide global
  if (hasAnyServers) {
    emptyStateGlobal.classList.add("hidden");
  } else {
    emptyStateGlobal.classList.remove("hidden");
  }
}

/**
 * Échappe les caractères HTML (XSS protection)
 */
function escapeHtml(text) {
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
 * Affiche un toast (notification)
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `mc-toast mc-toast--${type}`;
  toast.textContent = message;
  toastsContainer.appendChild(toast);

  // Supprimer le toast après 4 secondes
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// ════════════════════════════════════════════════════════════
//  EVENT LISTENERS
// ════════════════════════════════════════════════════════════

// Actualiser les données
refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshBtn.classList.add("loading");
  await fetchAllServers();
  refreshBtn.disabled = false;
  refreshBtn.classList.remove("loading");
  showToast("Serveurs actualisés", "success");
});

// Recherche en temps réel
searchInput.addEventListener("input", (e) => {
  searchTerm = e.target.value;
  renderServers();
});

// Filtres par status
filterButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    // Retirer la classe active de tous les boutons
    filterButtons.forEach(b => b.classList.remove("active"));
    // Ajouter la classe active au bouton cliqué
    btn.classList.add("active");
    // Mettre à jour le filtre
    currentFilter = btn.dataset.filter;
    renderServers();
  });
});

// Événement personnalisé : quand une action (start/stop) se termine
document.addEventListener('server-action-complete', async () => {
  // Attendre 2 secondes avant d'actualiser (laisser le serveur changer d'état)
  await new Promise(resolve => setTimeout(resolve, 2000));
  await fetchAllServers();
  showToast("État des serveurs actualisé", "success");
});

// Événement personnalisé : quand une carte veut afficher un toast
document.addEventListener('show-toast', (e) => {
  showToast(e.detail.message, e.detail.type || 'info');
});

// ════════════════════════════════════════════════════════════
//  INITIALISATION
// ════════════════════════════════════════════════════════════

// Charger les serveurs au démarrage
fetchAllServers();

// Actualiser les données toutes les 30 secondes
setInterval(fetchAllServers, 30000);
