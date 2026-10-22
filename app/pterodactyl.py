"""Client du panel Pterodactyl (API « client », via py-dactyl).

C'est le seul fichier à adapter pour changer de panel ou de bibliothèque : tout le reste de l'application
passe par `PterodactylClientWrapper`. Les listes sont renvoyées « à plat » (liste d'objets
`{"attributes": {...}}`), les objets uniques sous forme de dict d'attributs.
"""
from functools import lru_cache

from pydactyl import PterodactylClient

from .config import Config


@lru_cache(maxsize=1)
def _servers():
    return PterodactylClient(Config.PTERODACTYL_URL, Config.PTERODACTYL_API_KEY).client.servers


class PterodactylClientWrapper:
    @staticmethod
    def list_servers() -> list[dict]:
        """Tous les serveurs accessibles à la clé d'API, avec leur egg (relationships.egg)."""
        items: list[dict] = []
        for page in _servers().list_servers(includes=("egg",), params={"per_page": 100}):
            items.extend(page.data)
        return items

    @staticmethod
    def get_server(identifier: str) -> dict:
        return _servers().get_server(identifier, includes=("egg",))

    @staticmethod
    def get_utilization(identifier: str) -> dict:
        return _servers().get_server_utilization(identifier)

    @staticmethod
    def list_variables(identifier: str) -> list[dict]:
        return _servers().startup.list_variables(identifier).get("data", [])

    @staticmethod
    def list_allocations(identifier: str) -> list[dict]:
        return _servers().network.list_allocations(identifier).get("data", [])

    @staticmethod
    def list_backups(identifier: str) -> list[dict]:
        return _servers().backups.list_backups(identifier).get("data", [])

    @staticmethod
    def create_backup(identifier: str) -> dict:
        return _servers().backups.create_backup(identifier)

    @staticmethod
    def send_power_action(identifier: str, signal: str) -> None:
        _servers().send_power_action(identifier, signal)

    @staticmethod
    def get_websocket_client(identifier: str):
        return _servers().get_websocket_client(identifier)
