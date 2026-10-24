# server-hub — gestion des serveurs de jeu (Pterodactyl)

## Lancer en local (sans authentification)
```bash
pip install -r requirements.txt      # sans auth-client
cp .env.example .env                 # AUTH_ENABLED=false et URL_PREFIX= (vide) ; renseigner PTERODACTYL_*
flask --app wsgi run --debug --port 5000
```
Accueil : `http://localhost:5000/` (ou `http://localhost:5000<URL_PREFIX>/` si un préfixe est défini).

## Production (avec authentification)
```bash
pip install -r requirements-auth.txt   # ajoute auth-client
# .env : AUTH_ENABLED=true + variables AUTH_* + URL_PREFIX=/serverhub
```
`AUTH_REQUIRED_ROLES` restreint l'accès à certains rôles Keycloak (vide = tout utilisateur connecté).
Toutes les pages et toutes les routes API sont protégées (elles pilotent des serveurs et lancent des commandes SSH).

## Structure
```
wsgi.py                  point d'entrée (gunicorn / flask)
app/
  __init__.py            create_app : préfixe d'URL, proxy, enregistrement des modules
  config.py              lecture du .env
  helpers.py             require_auth / require_access, api_route (erreurs -> JSON), make_blueprint
  pterodactyl.py         client du panel (py-dactyl) : seul fichier à adapter pour changer de panel
  registry.py            découverte des modules (modules/<slug>/routes.py)
  routes.py              blueprint « serverhub » : hub + API JSON (/api/...)
  backend/
    manager.py           ServerManager (liste, accès à un serveur)
    modeles/             ServerInterface, MinecraftServer, PalworldServer, GenericServer, ServerFactory
  templates/             base.html, hub.html
  static/                site.css (variables), serverhub.css, server-cards/*.css,
                         js/ : hub.js, urls.js, ServerCardBase.js + une carte par type (web components)
  modules/<slug>/        un dossier par page de gestion dédiée (voir ci-dessous)
```

## Routes (relatives à `URL_PREFIX`)
- `/` : hub (recherche, filtres, cartes par type de serveur)
- `/<server_id>` : détail d'un serveur (redirige vers le module minijeux pour ce serveur, sinon 404)
- `/api/getServers` : liste + ressources live
- `/api/servers/<id>` (+ `/resources`, `/allocations`, `/backups` en GET ; `/power` et `/backups` en POST)
- `/minecraft/minigames/` : gestion du serveur minijeux (module `minigames`)
  - `/minecraft/minigames/api/liste`, `/minecraft/minigames/api/switch` (POST, réponse en streaming)

## Ajouter un type de serveur
1. `app/backend/modeles/XxxServer.py` : classe héritant de `ServerInterface` (`EGG_NAMES` + `get_game_info`).
2. L'ajouter à `_SERVER_CLASSES` dans `ServerFactory.py`.
3. Front : `static/js/xxxServerCard.js` (copier `palworldServerCard.js`, 3 lignes), `static/css/server-cards/xxxServerCard.css`,
   et une section dans `hub.html` / `hub.js` (`sections` + `tagMap`).

## Ajouter un module (page dédiée)
Créer `app/modules/<slug>/` avec :
- `__init__.py` (vide) ;
- `routes.py` : un blueprint `bp = make_blueprint("<slug>", __name__, __file__)` nommé comme le dossier, et optionnellement
  `URL_PATH = "/chemin"` (défaut : `/<slug>`), à ajouter à `URL_PREFIX` ;
- `templates/<slug>/` (les pages étendent `base.html`) et `static/` si besoin.

Il est enregistré seul au redémarrage. Copier `modules/minigames/` comme modèle.

## Module minijeux
Le switch de map se fait en SSH sur la VM Wings (`changeMap.sh`, via `sudo` restreint à ce seul script, voir
`MINIGAME_VM_*` dans `.env.example`). Le minijeu actif est mémorisé dans `/data/current_minigame.json` (volume Docker).

La clé privée SSH est montée dans le conteneur en lecture seule. Le conteneur tourne avec l'uid **10001** :
```bash
mkdir -p secrets
cp ~/.ssh/minigame_deploy secrets/minigame_ssh_key
chmod 400 secrets/minigame_ssh_key          # chmod AVANT chown : après, l'utilisateur de l'hôte n'a plus la main
sudo chown 10001 secrets/minigame_ssh_key
stat -c '%F' secrets/minigame_ssh_key       # doit afficher « regular file »
```
(`MINIGAME_VM_SSH_KEY_HOST_PATH` dans le `.env` pointe vers ce fichier.)

⚠️ Le dossier `secrets/` n'est pas versionné : à refaire après chaque nouveau `git clone`, **avant** `docker compose up`.
La clé est fournie au conteneur comme secret Docker : si le fichier manque, `docker compose up` s'arrête avec une erreur.

Dépannage : `[Errno 21] Is a directory` = ancien montage créé par Docker. `docker compose down`, `sudo rm -rf secrets/minigame_ssh_key`,
puis recopier la clé comme ci-dessus.

## Docker
```bash
cp .env.example .env                 # renseigner PORT, SECRET_KEY, PTERODACTYL_*, MINIGAME_VM_*
docker network create web            # une seule fois (réseau partagé avec le reverse proxy / l'auth)
docker compose up -d --build
```
En production (auth activée) : `WITH_AUTH=true docker compose up -d --build` avec `AUTH_ENABLED=true` dans le `.env`.

gunicorn tourne avec **1 worker et 8 threads** (`GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`) : un switch de
minijeu dure plusieurs minutes en streaming, et le verrou « un seul switch à la fois » est en mémoire.
