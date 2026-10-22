"""
server_factory.py — Fabrique d'instances ServerInterface selon le type d'egg Pterodactyl.

Pour enregistrer un nouveau type de serveur, ajoutez sa classe dans _SERVER_CLASSES.
L'ordre compte : la première classe dont EGG_NAMES matche le nom de l'egg est utilisée.
"""

from .ServerInterface import ServerInterface
from .MinecraftServer import MinecraftServer
from .PalworldServer import PalworldServer
from .GenericServer import GenericServer
from app.pterodactyl import PterodactylClientWrapper as Client

_SERVER_CLASSES: list[type[ServerInterface]] = [
    MinecraftServer,
    PalworldServer,
]


def _get_egg_name(identifier: str) -> str:
    raw = Client.get_server(identifier)
    attrs = raw if isinstance(raw, dict) and "identifier" in raw else raw.get("attributes", raw)
    relationships = attrs.get("relationships", {})
    egg_attrs = relationships.get("egg", {}).get("attributes", {})
    return (egg_attrs.get("name") or "").lower()


def create_server(identifier: str, egg_name: str | None = None) -> ServerInterface:
    """Instancie la sous-classe de ServerInterface adaptée au serveur `identifier`.

    Si `egg_name` est déjà connu (ex: récupéré lors d'un listing précédent), on
    évite un appel API supplémentaire en le passant directement.
    """
    egg_name = (egg_name if egg_name is not None else _get_egg_name(identifier)).lower()

    for server_class in _SERVER_CLASSES:
        if any(name in egg_name for name in server_class.EGG_NAMES):
            return server_class(identifier)

    return GenericServer(identifier)