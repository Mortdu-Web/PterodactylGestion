"""
manager.py — Point d'entrée haut niveau utilisé par le frontend.

Remplace l'ancienne classe API monolithique : au lieu de tout formater ici,
on délègue à l'instance ServerInterface correspondante (MinecraftServer,
PalworldServer, ...), obtenue via server_factory.create_server().
"""

from app.pterodactyl import PterodactylClientWrapper as Client
from .modeles.ServerFactory import create_server
from .modeles.ServerInterface import ServerInterface


class ServerManager:

    # ──────────────────────────────────────────────
    #  Liste de tous les serveurs (page d'accueil)
    # ──────────────────────────────────────────────
    @staticmethod
    def get_servers() -> list[dict]:
        """Retourne tous les serveurs avec leurs métriques live.

        Format de chaque élément :
        {
            "id"        : str
            "name"      : str
            "type"      : str   — "minecraft" | "palworld" | "generic" | ...
            "ramLimit"  : int   — en MB
            "diskLimit" : int   — en MB
            "status"    : str   — "running" | "stopped" | "starting" | "stopping" | "offline"
            "cpuUsed"   : float — en %
            "ramUsed"   : float — en MB
            "diskUsed"  : float — en MB
        }
        """
        result = []
        for data_dict in Client.list_servers():
            attrs = data_dict.get("attributes", {})
            limits = attrs.get("limits", {})
            srv_id = attrs.get("identifier")

            # L'egg est déjà dans le listing (relationships.egg) : inutile de le redemander à l'API.
            egg_name = attrs.get("relationships", {}).get("egg", {}).get("attributes", {}).get("name")
            server = create_server(srv_id, egg_name=egg_name or None)
            live = server.get_live_status()

            result.append({
                "id": srv_id,
                "name": attrs.get("name"),
                "type": server.type_name(),
                "ramLimit": limits.get("memory"),
                "diskLimit": limits.get("disk"),
                "status": live["status"],
                "cpuUsed": live["cpu_used"],
                "ramUsed": live["ram_used"],
                "diskUsed": live["disk_used"],
            })

        return result

    # ──────────────────────────────────────────────
    #  Accès à un serveur précis
    # ──────────────────────────────────────────────
    @staticmethod
    def get_server(identifier: str) -> ServerInterface:
        """Retourne l'instance (MinecraftServer, PalworldServer, ...) correspondant
        à `identifier`. Toutes les opérations (get_info, start, create_backup, ...)
        se font ensuite directement sur cette instance.
        """
        return create_server(identifier)