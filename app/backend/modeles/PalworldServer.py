"""
palworld_server.py — Spécificités des serveurs Palworld.
"""

from .ServerInterface import ServerInterface


class PalworldServer(ServerInterface):
    """Serveur Palworld."""

    EGG_NAMES = ["palworld"]

    # Adaptez ces clés aux variables d'environnement réelles de votre egg
    # (visibles dans Pterodactyl > Startup > Variables).
    def get_game_info(self, environment: dict) -> dict:
        return {
            "server_name": environment.get("SERVER_NAME"),
            "server_password": environment.get("SERVER_PASSWORD"),
            "admin_password": environment.get("ADMIN_PASSWORD"),
            "max_players": environment.get("MAX_PLAYERS") or environment.get("PLAYERS"),
            "community_server": environment.get("COMMUNITY"),
            "multithread_enabled": environment.get("MULTITHREAD_ENABLED"),
        }