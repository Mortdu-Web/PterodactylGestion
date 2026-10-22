// URL de la racine du hub (ex. "/serverhub/", ou "/" en local sans préfixe).
// window.SERVERHUB est injecté par Jinja2 dans hub.html, ce qui évite tout chemin codé en dur
// (le hub vit derrière le reverse proxy, sous URL_PREFIX).
export const hubUrl = (path = "") => `${window.SERVERHUB.base}${path}`;
