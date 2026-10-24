"""
RemoteMinigameService
======================
Gère la connexion SSH vers la VM qui héberge le serveur Minecraft "minijeux".

Deux opérations :
  - list_minigames()      : lit Minigames.json sur la VM distante (via SFTP)
  - switch_game_stream()  : exécute changeMap.sh <nom> (via sudo, droit
                             restreint à ce seul script) sur la VM et yield
                             la sortie ligne par ligne (générateur), pour
                             pouvoir la streamer en direct au navigateur.

Variables attendues dans le .env / config.py :
  MINIGAME_VM_HOST         adresse IP (ou hostname) de la VM Wings
  MINIGAME_VM_PORT         port SSH (22 par défaut)
  MINIGAME_VM_USER         utilisateur SSH dédié (ex: minigame-deploy)
  MINIGAME_VM_SSH_KEY_PATH chemin vers la clé privée SSH (sur la machine Flask)
  MINIGAME_VM_SCRIPT_PATH  chemin absolu de changeMap.sh sur la VM
                           (ex: /var/lib/pterodactyl/volumes/<uuid>/src/changeMap.sh)
  MINIGAME_VM_JSON_PATH    chemin absolu de Minigames.json sur la VM
                           (ex: /var/lib/pterodactyl/volumes/<uuid>/src/Minigames.json)
"""

import json
import os
import shlex
import time

import paramiko

from app.config import Config



class RemoteMinigameServiceError(Exception):
    """Erreur levée en cas de problème de connexion ou d'exécution distante."""


class RemoteMinigameService:
    def __init__(self):
        self.host = Config.MINIGAME_VM_HOST
        self.port = int(Config.MINIGAME_VM_PORT or 22)
        self.user = Config.MINIGAME_VM_USER
        self.key_path = Config.MINIGAME_VM_SSH_KEY_PATH
        self.script_path = Config.MINIGAME_VM_SCRIPT_PATH
        self.json_path = Config.MINIGAME_VM_JSON_PATH

    # ------------------------------------------------------------------ #
    # Connexion
    # ------------------------------------------------------------------ #
    def _connect(self) -> paramiko.SSHClient:
        # Vérification explicite : si le fichier n'existait pas sur l'hôte au démarrage de Docker,
        # Docker crée un DOSSIER à sa place (erreur paramiko « [Errno 21] Is a directory »).
        if not os.path.isfile(self.key_path):
            if os.path.isdir(self.key_path):
                detail = "est un dossier (le fichier n'existait pas sur l'hôte au démarrage de Docker)"
            else:
                detail = "est introuvable"
            raise RemoteMinigameServiceError(
                f"Clé SSH {self.key_path} {detail}. Voir « Module minijeux » dans le README."
            )
        client = paramiko.SSHClient()
        # À affiner si tu veux vérifier l'empreinte de la VM plutôt que
        # l'accepter automatiquement (recommandé en prod : load_host_keys).
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                key_filename=self.key_path,
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            raise RemoteMinigameServiceError(
                f"Connexion SSH impossible vers {self.host}:{self.port} — {exc}"
            ) from exc
        return client

    # ------------------------------------------------------------------ #
    # Lecture de la liste des minijeux
    # ------------------------------------------------------------------ #
    def list_minigames(self) -> list[dict]:
        client = self._connect()
        try:
            sftp = client.open_sftp()
            try:
                with sftp.open(self.json_path, "r") as remote_file:
                    raw = remote_file.read()
            finally:
                sftp.close()
        except FileNotFoundError as exc:
            raise RemoteMinigameServiceError(
                f"Minigames.json introuvable sur la VM ({self.json_path})"
            ) from exc
        finally:
            client.close()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RemoteMinigameServiceError("Minigames.json distant invalide") from exc

    # ------------------------------------------------------------------ #
    # Switch de minijeu (streaming de la sortie du script)
    # ------------------------------------------------------------------ #
    def switch_game_stream(self, game_name: str, timeout: int = 600):
        """
        Générateur : yield des morceaux de texte au fur et à mesure que
        changeMap.sh les affiche sur la VM distante.
        Lève RemoteMinigameServiceError si le script échoue ou dépasse `timeout` secondes.
        """
        client = self._connect()
        try:
            # Le script doit tourner en root sur l'hôte Wings pour pouvoir écrire
            # dans le volume Pterodactyl. Le compte SSH dédié (minigame-deploy)
            # n'a le droit d'exécuter QUE ce script via une règle NOPASSWD dans
            # /etc/sudoers.d/ — voir INTEGRATION.md.
            # `sudo -n` : n'attend jamais de mot de passe. Si la règle sudoers ne
            # correspond pas, la commande échoue tout de suite au lieu de bloquer.
            command = f"sudo -n {shlex.quote(self.script_path)} {shlex.quote(game_name)}"
            stdin, stdout, _stderr = client.exec_command(command, get_pty=True)
            stdin.close()

            channel = stdout.channel
            deadline = time.monotonic() + timeout
            while True:
                if channel.recv_ready():
                    chunk = channel.recv(4096)
                    if chunk:
                        yield chunk.decode("utf-8", errors="replace")
                    continue
                if channel.exit_status_ready() or channel.closed:
                    # Vider ce qu'il reste dans le tampon (résumé final du script)
                    while channel.recv_ready():
                        yield channel.recv(4096).decode("utf-8", errors="replace")
                    break
                if time.monotonic() > deadline:
                    channel.close()
                    raise RemoteMinigameServiceError(
                        f"Le script n'a pas terminé après {timeout}s, il a été interrompu"
                    )
                time.sleep(0.1)

            exit_status = channel.recv_exit_status()
            if exit_status != 0:
                raise RemoteMinigameServiceError(
                    f"Le script a échoué (code de sortie {exit_status})"
                )
        finally:
            client.close()
