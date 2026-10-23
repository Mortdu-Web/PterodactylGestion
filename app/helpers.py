import logging
from functools import wraps
from pathlib import Path

import requests
from flask import Blueprint, jsonify

from .config import Config

log = logging.getLogger(__name__)

# Usage dans les routes : @require_auth()  ou  @require_auth("role")  ou  @require_auth("a", "b", mode="all")
if Config.AUTH_ENABLED:
    from auth_client import require_auth
else:

    def require_auth(*roles: str, mode: str = "any"):
        """Auth desactivee (dev local) : ne controle rien."""

        def decorator(view):
            return view

        return decorator



def api_route(f):
    """Décorateur : transforme les exceptions (Pterodactyl, réseau...) en réponses JSON propres."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 502
            log.warning("Pterodactyl HTTP error %s: %s", status, e)
            return jsonify({"error": str(e)}), status
        except requests.ConnectionError:
            log.error("Cannot reach Pterodactyl panel")
            return jsonify({"error": "Panel injoignable"}), 502
        except requests.Timeout:
            return jsonify({"error": "Timeout panel"}), 504
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception:
            log.exception("Unexpected error in serverhub route")
            return jsonify({"error": "Erreur interne serveur"}), 500

    return wrapper


class ModuleBlueprint(Blueprint):
    def get_templates_path(self, filename: str) -> str:
        """Les gabarits d'un module vivent dans modules/<slug>/templates/<slug>/."""
        return f"{self.name}/{filename}"


def make_blueprint(name: str, import_name: str, file: str) -> ModuleBlueprint:
    """Blueprint d'un module : templates/ et static/ du dossier du module, s'ils existent.
    Le préfixe d'URL est appliqué à l'enregistrement, voir registry.py."""
    base = Path(file).parent
    return ModuleBlueprint(
        name,
        import_name,
        template_folder=str(base / "templates") if (base / "templates").is_dir() else None,
        static_folder=str(base / "static") if (base / "static").is_dir() else None,
        static_url_path="/static",
    )
