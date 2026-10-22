import os

try:  # chargement optionnel du .env en local (en Docker, c'est compose qui injecte les variables)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


def _list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    # Route racine derrière le reverse proxy (ex. /serverhub). Vide = à la racine.
    URL_PREFIX = os.getenv("URL_PREFIX", "").rstrip("/")
    PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:5000").rstrip("/")
    BEHIND_PROXY = _bool("BEHIND_PROXY", False)

    # Dossier des données persistantes de l'application (volume Docker monté sur /data).
    DATA_DIR = os.getenv("DATA_DIR", "data")

    # Panel Pterodactyl : URL du panel + clé d'API « client » (ptlc_...).
    PTERODACTYL_URL = os.getenv("PTERODACTYL_URL", "").rstrip("/")
    PTERODACTYL_API_KEY = os.getenv("PTERODACTYL_API_KEY", "")

    # Module « minijeux » (serveur Minecraft distant, voir app/modules/minigames).
    MINIGAME_VM_PTERODACTYL_ID = os.getenv("MINIGAME_VM_PTERODACTYL_ID", "")
    MINIGAME_VM_HOST = os.getenv("MINIGAME_VM_HOST", "")
    MINIGAME_VM_PORT = int(os.getenv("MINIGAME_VM_PORT") or 22)
    MINIGAME_VM_USER = os.getenv("MINIGAME_VM_USER", "")
    MINIGAME_VM_SSH_KEY_PATH = os.getenv("MINIGAME_VM_SSH_KEY_PATH", "")
    MINIGAME_VM_SCRIPT_PATH = os.getenv("MINIGAME_VM_SCRIPT_PATH", "")
    MINIGAME_VM_JSON_PATH = os.getenv("MINIGAME_VM_JSON_PATH", "")

    # Authentification via le paquet auth_client (service d'auth séparé).
    # Désactivée par défaut pour pouvoir développer en local sans le service.
    AUTH_ENABLED = _bool("AUTH_ENABLED", False)
    AUTH_INTERNAL_URL = os.getenv("AUTH_INTERNAL_URL", "")
    AUTH_PUBLIC_URL = os.getenv("AUTH_PUBLIC_URL", "")
    # Rôles Keycloak autorisés à gérer les serveurs (séparés par des virgules ; un seul suffit).
    # Vide = tout utilisateur authentifié.
    AUTH_REQUIRED_ROLES = _list("AUTH_REQUIRED_ROLES")

    SESSION_COOKIE_NAME = "site_session"
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_MINUTES", "480")) * 60
