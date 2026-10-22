from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .registry import register_modules
from .routes import bp as serverhub_bp


def create_app() -> Flask:
    # static_folder=None : les fichiers communs sont servis par le blueprint « serverhub »,
    # et chaque module sert les siens (<slug>.static), tous sous URL_PREFIX.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    if Config.BEHIND_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    app.register_blueprint(serverhub_bp, url_prefix=Config.URL_PREFIX or None)
    register_modules(app)

    return app
