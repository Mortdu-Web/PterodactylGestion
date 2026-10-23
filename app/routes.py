"""
Blueprint « serverhub » : gestion des serveurs de jeu (Minecraft, Palworld, ...) via Pterodactyl.

Routes HTML (relatives à URL_PREFIX)
  GET  /                              → hub (liste des serveurs)
  GET  /<server_id>                   → détail d'un serveur (redirige vers le module « minigames »
                                        si c'est le serveur minijeux, sinon 404)

Routes API JSON
  GET  /api/getServers                → liste + ressources live
  GET  /api/servers/<id>              → infos statiques + game_info
  GET  /api/servers/<id>/resources    → métriques live
  POST /api/servers/<id>/power        → start/stop/restart/kill
  GET  /api/servers/<id>/allocations  → allocations réseau
  GET  /api/servers/<id>/backups      → liste des sauvegardes
  POST /api/servers/<id>/backups      → créer une sauvegarde
  POST /api/start, /api/stop          → (legacy)
"""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from .backend.manager import ServerManager
from .config import Config
from .helpers import api_route, require_auth

bp = Blueprint("serverhub", __name__, static_folder="static", static_url_path="/static")

_ALLOWED_SIGNALS = {"start", "stop", "restart", "kill"}


# ══════════════════════════════════════════════════════════════
#  PAGES HTML
# ══════════════════════════════════════════════════════════════

@bp.route("/")
@require_auth("admin", "ServersUses-Access")
def hub():
    """Hub principal : liste de tous les serveurs (Minecraft, Palworld, ...)."""
    return render_template("hub.html")


@bp.route("/<server_id>")
@require_auth("admin", "ServersUses-Access")
def server_detail(server_id: str):
    """Page de détail d'un serveur.

    Cas particulier : le serveur « minijeux » a sa propre page de gestion (switch de map + power),
    donc on redirige dessus au lieu d'afficher une page de détail générique.
    """
    if Config.MINIGAME_VM_PTERODACTYL_ID and server_id == Config.MINIGAME_VM_PTERODACTYL_ID:
        return redirect(url_for("minigames.page"))

    # TODO: page de détail générique pas encore implémentée
    abort(404)


# ══════════════════════════════════════════════════════════════
#  API — HUB
# ══════════════════════════════════════════════════════════════

@bp.get("/api/getServers")
@require_auth("admin", "ServersUses-Access")
@api_route
def get_servers():
    return jsonify(ServerManager.get_servers())


# ══════════════════════════════════════════════════════════════
#  API — SERVEUR UNIQUE
# ══════════════════════════════════════════════════════════════

@bp.get("/api/servers/<server_id>")
@require_auth("admin", "ServersUses-Access")
@api_route
def get_server_info(server_id: str):
    return jsonify(ServerManager.get_server(server_id).get_info())


@bp.get("/api/servers/<server_id>/resources")
@require_auth("admin", "ServersUses-Access")
@api_route
def get_server_resources(server_id: str):
    return jsonify(ServerManager.get_server(server_id).get_resources())


@bp.post("/api/servers/<server_id>/power")
@require_auth("admin", "ServersUses-Access")
@api_route
def power_server(server_id: str):
    """Body attendu : {"signal": "start" | "stop" | "restart" | "kill"}"""
    body = request.get_json(silent=True) or {}
    signal = body.get("signal")
    if signal not in _ALLOWED_SIGNALS:
        raise ValueError(f"Signal invalide, attendu l'un de {sorted(_ALLOWED_SIGNALS)}")

    server = ServerManager.get_server(server_id)
    getattr(server, signal)()  # server.start() / .stop() / .restart() / .kill()
    return jsonify({"success": True, "error": None})


@bp.get("/api/servers/<server_id>/allocations")
@require_auth("admin", "ServersUses-Access")
@api_route
def get_server_allocations(server_id: str):
    return jsonify(ServerManager.get_server(server_id).get_allocations())


@bp.get("/api/servers/<server_id>/backups")
@require_auth("admin", "ServersUses-Access")
@api_route
def get_server_backups(server_id: str):
    return jsonify(ServerManager.get_server(server_id).get_backups())


@bp.post("/api/servers/<server_id>/backups")
@require_auth("admin", "ServersUses-Access")
@api_route
def create_server_backup(server_id: str):
    return jsonify(ServerManager.get_server(server_id).create_backup())


# ══════════════════════════════════════════════════════════════
#  API — LEGACY
#  Remplaçables par /api/servers/<id>/power (c'est ce qu'utilisent déjà les cartes).
# ══════════════════════════════════════════════════════════════

@bp.post("/api/start")
@require_auth("admin", "ServersUses-Access")
@api_route
def start_server():
    server_id = (request.get_json(silent=True) or {}).get("id")
    if not server_id:
        abort(400)
    ServerManager.get_server(server_id).start()
    return jsonify({"success": True, "error": None})


@bp.post("/api/stop")
@require_auth("admin", "ServersUses-Access")
@api_route
def stop_server():
    server_id = (request.get_json(silent=True) or {}).get("id")
    if not server_id:
        abort(400)
    ServerManager.get_server(server_id).stop()
    return jsonify({"success": True, "error": None})
