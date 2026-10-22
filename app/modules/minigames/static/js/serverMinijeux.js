// Gestion de la page "Serveur minijeux"
// Endpoints attendus (voir routes.py du blueprint serverMinijeux) :
//   GET  <LISTE_URL>
//   POST <SWITCH_URL>   { name: "<minijeu>" }  -> réponse en streaming text/plain
// LISTE_URL et SWITCH_URL sont injectées globalement par Jinja2 (voir minigames.html).

document.addEventListener("DOMContentLoaded", () => {
  const grid = document.getElementById("minijeux-grid");
  const currentNameEl = document.getElementById("minijeux-current-name");
  const consoleEl = document.getElementById("minijeux-console");
  const stateEl = document.getElementById("minijeux-state");

  let minigames = [];
  let currentGame = null;
  let switching = false;

  init();

  async function init() {
    stateEl.textContent = "Chargement des minijeux…";
    try {
      const res = await fetch(LISTE_URL);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur inconnue");

      minigames = data.minigames || [];
      currentGame = data.current || null;
      stateEl.textContent = "";
      renderCurrent();
      renderGrid();
    } catch (err) {
      stateEl.textContent = `Impossible de contacter la VM du serveur minijeux : ${err.message}`;
      stateEl.classList.add("minijeux-server__error");
    }
  }

  function renderCurrent() {
    currentNameEl.textContent = currentGame || "Aucun minijeu actif détecté";
  }

  function renderGrid() {
    grid.innerHTML = "";
    minigames.forEach((game) => {
      const card = document.createElement("div");
      card.className = "minijeux-card" + (game.name === currentGame ? " minijeux-card--active" : "");

      const name = document.createElement("div");
      name.className = "minijeux-card__name";
      name.textContent = game.name;

      const version = document.createElement("span");
      version.className = "minijeux-card__version";
      version.textContent = `MC ${game.minecraft_version}`;

      const isActive = game.name === currentGame;

      const btn = document.createElement("button");
      btn.className = "minijeux-card__btn" + (isActive ? " minijeux-card__btn--reload" : "");
      btn.textContent = isActive ? "Reload" : "Activer";
      btn.disabled = switching;
      btn.addEventListener("click", () => switchGame(game.name));

      card.append(name, version, btn);
      grid.appendChild(card);
    });
  }

  async function switchGame(name) {
    if (switching) return;
    switching = true;
    renderGrid();

    consoleEl.textContent = "";
    consoleEl.classList.add("minijeux-console--visible");
    appendConsole(`==> Démarrage du switch vers "${name}"…\n`);

    let output = "";
    try {
      const res = await fetch(SWITCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });

      if (!res.body) {
        // Fallback si le streaming n'est pas supporté par le navigateur
        const text = await res.text();
        output += text;
        appendConsole(text);
      } else {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          output += chunk;
          appendConsole(chunk);
        }
      }

      // Les erreurs arrivent dans le flux (HTTP 200) : seul le message final « [OK] Switch terminé » confirme le switch.
      if (res.ok && output.includes("[OK] Switch terminé")) {
        currentGame = name;
        renderCurrent();
      }
    } catch (err) {
      appendConsole(`\n[ERREUR] ${err.message}\n`);
    } finally {
      switching = false;
      renderGrid();
    }
  }

  function appendConsole(text) {
    consoleEl.textContent += text;
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }
});