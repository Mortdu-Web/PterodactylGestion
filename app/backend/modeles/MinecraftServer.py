"""
minecraft_server.py — Spécificités des serveurs Minecraft.
"""

from .ServerInterface import ServerInterface


class MinecraftServer(ServerInterface):
    """Serveur Minecraft (eggs vanilla, Paper, Forge, Fabric, etc.)."""

    EGG_NAMES = ["minecraft", "paper", "spigot", "forge", "fabric", "vanilla"]

    # Adaptez ces clés aux variables d'environnement réelles de votre egg
    # (visibles dans Pterodactyl > Startup > Variables).
    def get_game_info(self, environment: dict) -> dict:
        return {
            "version": environment.get("MINECRAFT_VERSION") or environment.get("VERSION"),
            "server_type": environment.get("SERVER_TYPE") or environment.get("TYPE"),
            "jar_file": environment.get("SERVER_JARFILE"),
            "difficulty": environment.get("DIFFICULTY"),
            "max_players": environment.get("MAX_PLAYERS"),
            "whitelist_enabled": environment.get("WHITELIST"),
            "pvp": environment.get("PVP"),
        }