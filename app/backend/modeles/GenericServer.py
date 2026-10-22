"""
generic_server.py — Fallback utilisé quand aucun type de serveur connu ne matche
l'egg Pterodactyl. Permet au panel de fonctionner (lister, démarrer, backup, ...)
même pour un jeu qui n'a pas encore sa propre classe dédiée.
"""

from .ServerInterface import ServerInterface


class GenericServer(ServerInterface):
    """Serveur générique : aucune info spécifique au jeu n'est extraite."""

    EGG_NAMES: list[str] = []  # jamais matché directement, sert de fallback

    def get_game_info(self, environment: dict) -> dict:
        return {}