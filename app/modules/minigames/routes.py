"""
Module « minijeux » : gestion du serveur Minecraft « minijeux » distant.

Page HTML (relative à URL_PREFIX + URL_PATH)
  GET  /minecraft/minigames/            -> page de gestion

API
  GET  /minecraft/minigames/api/liste   -> liste des minijeux + minijeu actif
  POST /minecraft/minigames/api/switch  -> stop -> switch (SSH) -> start,
                                           réponse en streaming (text/plain)
"""
import json
import threading
import time
from pathlib import Path

from flask import Response, jsonify, render_template, request, stream_with_context

from app.config import Config
from app.helpers import make_blueprint, require_access
from app.pterodactyl import PterodactylClientWrapper

from .backend.RemoteMinigameService import RemoteMinigameService, RemoteMinigameServiceError

bp = make_blueprint("minigames", __name__, __file__)
URL_PATH = "/minecraft/minigames"

# États Pterodactyl attendus après un power signal (voir get_utilization()).
_STATE_OFFLINE = "offline"
_STATE_RUNNING = "running"

# Délais de polling pour attendre la fin d'un arrêt/démarrage.
_POLL_INTERVAL_SECONDS = 2
_STOP_TIMEOUT_SECONDS = 90
_START_TIMEOUT_SECONDS = 120

# Un seul switch à la fois (gunicorn tourne avec 1 worker et plusieurs threads, voir Dockerfile).
_switch_lock = threading.Lock()


def _current_game_file() -> Path:
    # Dernier minijeu activé : le script distant ne le renseigne pas, on le garde côté application.
    # DATA_DIR est un volume Docker (/data), il survit donc aux redéploiements du conteneur.
    return Path(Config.DATA_DIR) / "current_minigame.json"


def _read_current_game():
    try:
        return json.loads(_current_game_file().read_text(encoding="utf-8")).get("name")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_current_game(name):
    path = _current_game_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": name}), encoding="utf-8")


class PowerActionTimeoutError(Exception):
    """Le serveur n'a pas atteint l'état attendu dans le délai imparti."""


def _get_server_state() -> str | None:
    """Lit le current_state depuis get_utilization()."""
    utilization = PterodactylClientWrapper.get_utilization(Config.MINIGAME_VM_PTERODACTYL_ID)
    attributes = utilization.get("attributes", utilization) if isinstance(utilization, dict) else {}
    return attributes.get("current_state")


def _wait_for_state(target_state: str, timeout: int):
    """
    Générateur : poll l'état du serveur toutes les _POLL_INTERVAL_SECONDS et yield une ligne de
    statut à chaque changement. Lève PowerActionTimeoutError si le délai est dépassé.
    """
    elapsed = 0
    last_state = None
    while elapsed < timeout:
        state = _get_server_state()
        if state != last_state:
            yield f"    état actuel : {state}\n"
            last_state = state
        if state == target_state:
            return
        time.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS

    raise PowerActionTimeoutError(
        f"Le serveur n'a pas atteint l'état '{target_state}' après {timeout}s "
        f"(dernier état observé : {last_state})"
    )


@bp.route("/")
@require_access()
def page():
    return render_template(bp.get_templates_path("minigames.html"))


@bp.route("/api/liste")
@require_access()
def api_liste_minijeux():
    service = RemoteMinigameService()
    try:
        minigames = service.list_minigames()
    except RemoteMinigameServiceError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"minigames": minigames, "current": _read_current_game()})


@bp.route("/api/switch", methods=["POST"])
@require_access()
def api_switch_minijeu():
    payload = request.get_json(silent=True) or {}
    game_name = (payload.get("name") or "").strip()
    if not game_name:
        return jsonify({"error": "Paramètre 'name' manquant"}), 400

    service = RemoteMinigameService()

    def generate():
        if not _switch_lock.acquire(blocking=False):
            yield "[ERREUR] Un switch est déjà en cours, réessaie dans un instant.\n"
            return
        try:
            # 1. Arrêt du serveur
            yield "==> Arrêt du serveur en cours...\n"
            PterodactylClientWrapper.send_power_action(Config.MINIGAME_VM_PTERODACTYL_ID, "stop")
            yield from _wait_for_state(_STATE_OFFLINE, _STOP_TIMEOUT_SECONDS)
            yield "==> Serveur arrêté.\n\n"

            # 2. Switch de map (SSH + sudo changeMap.sh sur la VM Wings)
            yield f"==> Switch vers le minijeu \"{game_name}\"...\n"
            for chunk in service.switch_game_stream(game_name):
                yield chunk
            _write_current_game(game_name)
            yield "\n"

            # 3. Redémarrage du serveur
            yield "==> Redémarrage du serveur...\n"
            PterodactylClientWrapper.send_power_action(Config.MINIGAME_VM_PTERODACTYL_ID, "start")
            yield from _wait_for_state(_STATE_RUNNING, _START_TIMEOUT_SECONDS)

            yield "\n[OK] Switch terminé, serveur relancé avec succès.\n"
        except (PowerActionTimeoutError, RemoteMinigameServiceError) as exc:
            yield f"\n[ERREUR] {exc}\n"
        except Exception as exc:  # noqa: BLE001
            yield f"\n[ERREUR] Erreur inattendue : {exc}\n"
        finally:
            _switch_lock.release()

    # X-Accel-Buffering: no -> nginx ne met pas la réponse en mémoire tampon, la console s'affiche en direct.
    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
