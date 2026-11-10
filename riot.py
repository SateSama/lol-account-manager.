"""Lancement du Riot Client et saisie automatique des identifiants.

On ne touche jamais au jeu lui-même : on ferme/relance le client Riot,
puis on tape l'identifiant et le mot de passe dans sa fenêtre de connexion.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Callable

import pyautogui
import pygetwindow
import pyperclip

NO_WINDOW = 0x08000000  # empêche l'ouverture d'une console noire

RIOT_PROCESSES = [
    "RiotClientServices.exe",
    "RiotClientUx.exe",
    "RiotClientUxRender.exe",
    "RiotClientCrashHandler.exe",
    "LeagueClient.exe",
    "LeagueClientUx.exe",
    "LeagueClientUxRender.exe",
]
GAME_PROCESS = "League of Legends.exe"      # la partie elle-même (existe seulement pendant un match)
LEAGUE_CLIENT = "LeagueClientUx.exe"          # le client LoL (salon, file d'attente...)
DEFAULT_CLIENT = r"C:\Riot Games\Riot Client\RiotClientServices.exe"
SESSION_FILE = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Riot Games" / "Riot Client" / "Data" / "RiotGamesPrivateSettings.yaml"
)

StatusCallback = Callable[[str], None]


class RiotError(Exception):
    pass


def find_client() -> str:
    """Chemin de RiotClientServices.exe (lu dans le fichier d'installation de Riot)."""
    installs = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Riot Games" / "RiotClientInstalls.json"
    try:
        data = json.loads(installs.read_text(encoding="utf-8"))
        for key in ("rc_live", "rc_default"):
            path = data.get(key)
            if path and Path(path).exists():
                return path
    except (OSError, ValueError):
        pass
    if Path(DEFAULT_CLIENT).exists():
        return DEFAULT_CLIENT
    raise RiotError("Riot Client introuvable. Est-ce que League of Legends est installé ?")


def _is_running(process: str) -> bool:
    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process}", "/NH"],
        capture_output=True, text=True, creationflags=NO_WINDOW,
    ).stdout
    return process.lower() in out.lower()


def _kill_client() -> None:
    for process in RIOT_PROCESSES:
        subprocess.run(["taskkill", "/F", "/IM", process],
                       capture_output=True, creationflags=NO_WINDOW)
    # Laisse le temps à Windows de libérer les fichiers.
    for _ in range(20):
        if not _is_running("RiotClientServices.exe"):
            break
        time.sleep(0.25)


def _clear_session() -> None:
    """Supprime la session « Rester connecté » pour forcer l'écran de connexion."""
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _launch_league(client: str) -> None:
    """Demande au Riot Client de lancer League of Legends (au démarrage, ou une 2e fois si besoin)."""
    subprocess.Popen(
        [client, "--launch-product=league_of_legends", "--launch-patchline=live"],
        creationflags=NO_WINDOW,
    )


def _wait_until_running(process: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_running(process):
            return True
        time.sleep(2)
    return False


def ensure_league_launched(on_status: StatusCallback = lambda _msg: None, *,
                           timeout: float = 180.0, retry_every: float = 8.0) -> bool:
    """Juste après la connexion : ouvre le client LoL tout de suite.

    On redemande le lancement au Riot Client dès que possible, puis toutes les `retry_every` secondes
    jusqu'à ce que le client soit ouvert (ça couvre aussi le temps d'un code de double authentification).
    Renvoie True si le client est ouvert. (La partie elle-même ne démarre que quand tu lances une file.)
    """
    if _is_running(LEAGUE_CLIENT):
        return True
    try:
        client = find_client()
    except RiotError:
        return False
    on_status("Lancement de League of Legends…")
    deadline = time.time() + timeout
    clicks = 0
    while time.time() < deadline:
        # Le bouton « Jouer » n'existe qu'une fois connecté : on laisse d'abord le temps à la connexion.
        if _wait_until_running(LEAGUE_CLIENT, 6):
            return True
        if clicks < 4 and _click_play():
            clicks += 1
            on_status("Clic sur « Jouer »…")
        else:
            try:
                _launch_league(client)
            except OSError:
                return False
        if _wait_until_running(LEAGUE_CLIENT, retry_every):
            return True
        on_status("En attente de League of Legends (code de double authentification ?)…")
    return False


def _wait_for_window(timeout: float):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for win in pygetwindow.getWindowsWithTitle("Riot Client"):
            try:
                # On ignore les petites fenêtres temporaires (écran de démarrage)
                if win.title.strip() == "Riot Client" and win.width > 500 and win.height > 300:
                    return win
            except Exception:
                continue  # la fenêtre a disparu entre-temps
        time.sleep(0.5)
    raise RiotError("La fenêtre du Riot Client n'est pas apparue à temps.")


# Position des champs en fraction de la fenêtre (x, y), mesurée sur le Riot Client actuel.
# Si les clics tombent à côté après une mise à jour de Riot, ajuste ces deux valeurs.
USERNAME_POS = (200, 258)
PASSWORD_POS = (200, 322)


# Bouton « Jouer » du Riot Client (onglet League of Legends) : distance depuis le coin BAS-gauche
# de la fenêtre, mesurée sur le Riot Client actuel. Ajuste si le clic tombe à côté après une mise à jour.
PLAY_FROM_LEFT = 227
PLAY_FROM_BOTTOM = 68


def _click_play() -> bool:
    """Clique sur le bouton « Jouer » du Riot Client. Renvoie False si la fenêtre est introuvable."""
    try:
        window = _wait_for_window(3)
        left, top, height = max(window.left, 0), max(window.top, 0), window.height
        pyautogui.click(left + PLAY_FROM_LEFT, top + height - PLAY_FROM_BOTTOM)
        return True
    except Exception:
        return False


def _click_in_window(window, pos: tuple[int, int]) -> None:
    """Clique à `pos` pixels du coin haut-gauche de la fenêtre.

    Le panneau de connexion du Riot Client a une taille fixe collée en haut à gauche :
    les distances ne changent pas quand on redimensionne la fenêtre.
    """
    try:
        left, top = window.left, window.top
    except Exception:
        window = _wait_for_window(10)  # handle périmé : on récupère la fenêtre actuelle
        left, top = window.left, window.top
    # Fenêtre maximisée ou coordonnées négatives : on reste dans l'écran
    left, top = max(left, 0), max(top, 0)
    pyautogui.click(left + pos[0], top + pos[1])


def _paste(text: str, pause: float) -> None:
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(pause)


def login(
    username: str,
    password: str,
    on_status: StatusCallback = lambda _msg: None,
    *,
    startup_timeout: float = 45.0,
    render_delay: float = 3.0,
    key_pause: float = 0.4,
) -> None:
    """Ferme le client, le relance et saisit les identifiants.

    render_delay : attente après l'apparition de la fenêtre, le temps que le
    formulaire s'affiche. Augmente-le si la saisie part trop tôt.
    """
    client = find_client()
    if _is_running(GAME_PROCESS):
        raise RiotError("Une partie est en cours : ferme-la avant de changer de compte.")

    on_status("Fermeture du client Riot…")
    _kill_client()
    _clear_session()

    on_status("Lancement du client Riot…")
    _launch_league(client)

    on_status("Attente de la fenêtre de connexion…")
    _wait_for_window(startup_timeout)
    time.sleep(render_delay)
    # Le Riot Client recrée parfois sa fenêtre au démarrage : on la retrouve juste avant d'écrire.
    window = _wait_for_window(15)

    on_status("Saisie des identifiants…")
    try:
        if window.isMinimized:
            window.restore()
        window.activate()
    except Exception:
        pass  # Windows refuse parfois le focus ; le clic ci-dessous le prend de force
    time.sleep(0.5)

    try:
        # On clique dans les champs : c'est ce qui donne vraiment le focus au Riot Client
        # (sinon les touches partent dans la fenêtre de notre appli).
        _click_in_window(window, USERNAME_POS)
        time.sleep(key_pause)
        pyautogui.hotkey("ctrl", "a")
        _paste(username, key_pause)

        # Tab plutôt qu'un second clic : le clic sur le champ mot de passe ne changeait pas le focus
        pyautogui.press("tab")
        time.sleep(key_pause)
        pyautogui.hotkey("ctrl", "a")
        _paste(password, key_pause)
        pyautogui.press("enter")
    finally:
        pyperclip.copy("")  # ne laisse jamais le mot de passe dans le presse-papiers

    on_status("Connexion envoyée ✔")
