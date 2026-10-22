"""Découverte des modules : un dossier modules/<slug>/ contenant routes.py (blueprint `bp` nommé <slug>).

Le chemin d'URL du module est `URL_PATH` (défini dans routes.py), ou /<slug> par défaut ; il vient
s'ajouter à URL_PREFIX.
"""
from importlib import import_module
from pathlib import Path

from .config import Config

MODULES_DIR = Path(__file__).parent / "modules"


def register_modules(app) -> None:
    for routes in sorted(MODULES_DIR.glob("*/routes.py")):
        slug = routes.parent.name
        module = import_module(f"app.modules.{slug}.routes")
        if module.bp.name != slug:
            raise RuntimeError(f"Le blueprint de {slug!r} doit s'appeler {slug!r} (et non {module.bp.name!r})")
        path = getattr(module, "URL_PATH", f"/{slug}")
        app.register_blueprint(module.bp, url_prefix=f"{Config.URL_PREFIX}{path}")
