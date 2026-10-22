"""
server_interface.py — Contrat commun à tout type de serveur géré par le panel.
"""

from abc import ABC, abstractmethod

from app.pterodactyl import PterodactylClientWrapper as Client


class ServerInterface(ABC):
    """Classe de base pour tout type de serveur (Minecraft, Palworld, ...).

    Pour ajouter un nouveau type de serveur :
        1. Créer un fichier `xxx_server.py` avec une classe héritant de ServerInterface.
        2. Définir l'attribut de classe EGG_NAMES : liste de sous-chaînes (en minuscule)
           permettant de reconnaître ce type via le nom de l'egg Pterodactyl.
        3. Implémenter get_game_info(environment) qui extrait les infos spécifiques
           au jeu depuis les variables d'environnement du serveur.
        4. Ajouter la classe dans la liste _SERVER_CLASSES de server_factory.py.

    Tout le reste (récupération des métriques, backups, allocations, power actions...)
    est déjà géré ici et n'a normalement pas besoin d'être surchargé.
    """

    # À surcharger dans chaque sous-classe : sous-chaînes (minuscules) du nom d'egg
    # Pterodactyl qui identifient ce type de serveur (ex: ["minecraft", "paper"]).
    EGG_NAMES: list[str] = []

    def __init__(self, identifier: str):
        self.identifier = identifier

    # ──────────────────────────────────────────────
    #  Infos statiques
    # ──────────────────────────────────────────────
    def get_info(self) -> dict:
        """Infos statiques formatées du serveur, incluant les infos spécifiques au jeu.

        Format retourné :
        {
            "id", "uuid", "name", "description", "node",
            "sftp_host", "sftp_port", "status", "type",
            "egg": {"name", "docker_image"},
            "environment": {...},
            "limits": {"cpu", "memory", "disk", "swap", "io"},
            "game_info": {...},   # spécifique à la sous-classe
        }
        """
        raw = Client.get_server(self.identifier)
        attrs = raw if isinstance(raw, dict) and "identifier" in raw else raw.get("attributes", raw)
        limits = attrs.get("limits", {})
        sftp = attrs.get("sftp_details", {})

        relationships = attrs.get("relationships", {})
        egg_attrs = relationships.get("egg", {}).get("attributes", {})

        environment = self._get_environment()

        try:
            status = Client.get_utilization(self.identifier).get("current_state", "stopped")
        except Exception:
            status = "stopped"

        return {
            "id": attrs.get("identifier"),
            "uuid": attrs.get("uuid"),
            "name": attrs.get("name"),
            "description": attrs.get("description") or None,
            "node": None,  # Nécessite l'API admin pour l'obtenir
            "sftp_host": sftp.get("ip"),
            "sftp_port": sftp.get("port"),
            "status": status,
            "type": self.type_name(),
            "egg": {
                "name": egg_attrs.get("name"),
                "docker_image": egg_attrs.get("docker_image"),
            },
            "environment": environment,
            "limits": {
                "cpu": limits.get("cpu", 0),
                "memory": limits.get("memory", 0),
                "disk": limits.get("disk", 0),
                "swap": limits.get("swap", 0),
                "io": limits.get("io", 0),
            },
            "game_info": self.get_game_info(environment),
        }

    def _get_environment(self) -> dict:
        env_raw = Client.list_variables(self.identifier)
        return {
            item["attributes"]["env_variable"]: item["attributes"]["server_value"]
            for item in env_raw
            if "attributes" in item
        }

    # ──────────────────────────────────────────────
    #  Métriques live
    # ──────────────────────────────────────────────
    def get_resources(self) -> dict:
        """Métriques live formatées (cpu, mémoire, disque, réseau, uptime)."""
        raw = Client.get_utilization(self.identifier)
        resources = raw.get("resources", {})

        try:
            srv_attrs = Client.get_server(self.identifier)
            attrs = srv_attrs if "limits" in srv_attrs else srv_attrs.get("attributes", {})
            limits = attrs.get("limits", {})
            mem_limit_mb = limits.get("memory", 0)
            disk_limit_mb = limits.get("disk", 0)
        except Exception:
            mem_limit_mb = disk_limit_mb = 0

        network = resources.get("network", {})

        return {
            "cpu_percent": round(resources.get("cpu_absolute", 0), 2),
            "memory_bytes": resources.get("memory_bytes", 0),
            "memory_limit_bytes": mem_limit_mb * 1_048_576,
            "disk_bytes": resources.get("disk_bytes", 0),
            "disk_limit_bytes": disk_limit_mb * 1_048_576,
            "uptime_seconds": resources.get("uptime", 0) // 1000,  # ms → s
            "network_rx_bytes": network.get("rx_bytes", 0),
            "network_tx_bytes": network.get("tx_bytes", 0),
        }

    def get_live_status(self) -> dict:
        """Version allégée de get_resources(), utilisée pour le listing (page d'accueil)."""
        try:
            stats = Client.get_utilization(self.identifier)
            resources = stats.get("resources", {})
            return {
                "status": stats.get("current_state", "offline"),
                "cpu_used": round(resources.get("cpu_absolute", 0), 2),
                "ram_used": round(resources.get("memory_bytes", 0) / 1_048_576, 2),
                "disk_used": round(resources.get("disk_bytes", 0) / 1_048_576, 2),
            }
        except Exception as e:
            print(f"[{self.type_name()}:{self.identifier}] Stats indisponibles: {e}")
            return {"status": "offline", "cpu_used": 0, "ram_used": 0, "disk_used": 0}

    # ──────────────────────────────────────────────
    #  Allocations réseau
    # ──────────────────────────────────────────────
    def get_allocations(self) -> list[dict]:
        raw = Client.list_allocations(self.identifier)
        result = []
        for item in raw:
            a = item.get("attributes", {})
            result.append({
                "id": a.get("id"),
                "ip": a.get("ip"),
                "port": a.get("port"),
                "alias": a.get("alias") or None,
                "is_default": a.get("is_default", False),
            })
        return result

    # ──────────────────────────────────────────────
    #  Sauvegardes
    # ──────────────────────────────────────────────
    def get_backups(self) -> list[dict]:
        raw = Client.list_backups(self.identifier)
        result = []
        for item in raw:
            b = item.get("attributes", {})
            result.append({
                "uuid": b.get("uuid"),
                "name": b.get("name"),
                "size_bytes": b.get("bytes", 0),
                "created_at": b.get("created_at"),
                "is_successful": b.get("is_successful", False),
            })
        result.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return result

    def create_backup(self) -> dict:
        raw = Client.create_backup(self.identifier)
        b = raw.get("attributes", raw) if isinstance(raw, dict) else {}
        return {
            "uuid": b.get("uuid"),
            "name": b.get("name"),
            "size_bytes": b.get("bytes", 0),
            "created_at": b.get("created_at"),
            "is_successful": b.get("is_successful", False),
        }

    # ──────────────────────────────────────────────
    #  Contrôle alimentation
    # ──────────────────────────────────────────────
    def start(self) -> None:
        Client.send_power_action(self.identifier, "start")

    def stop(self) -> None:
        Client.send_power_action(self.identifier, "stop")

    def restart(self) -> None:
        Client.send_power_action(self.identifier, "restart")

    def kill(self) -> None:
        Client.send_power_action(self.identifier, "kill")

    # ──────────────────────────────────────────────
    #  WebSocket console
    # ──────────────────────────────────────────────
    def get_websocket_client(self):
        """Retourne un WebsocketClient pydactyl (non connecté)."""
        return Client.get_websocket_client(self.identifier)

    # ──────────────────────────────────────────────
    #  Identité du type de serveur
    # ──────────────────────────────────────────────
    @classmethod
    def type_name(cls) -> str:
        """Nom court du type de serveur, ex: 'minecraft', 'palworld'."""
        return cls.__name__.replace("Server", "").lower()

    # ──────────────────────────────────────────────
    #  À implémenter par chaque sous-classe
    # ──────────────────────────────────────────────
    @abstractmethod
    def get_game_info(self, environment: dict) -> dict:
        """Extrait les infos spécifiques au jeu depuis les variables d'environnement
        (ex: version, difficulté, whitelist pour Minecraft ; mot de passe, mods pour
        Palworld). Doit être implémentée par chaque sous-classe.
        """
        raise NotImplementedError