"""Lecture du compte connecté dans le client League of Legends, sans clé API.

Le client LoL ouvre une petite API réservée à ton PC (127.0.0.1, port et mot de passe différents à chaque
lancement). On la lit en lecture seule pour récupérer le Riot ID et le rang du compte connecté.
Rien ne sort de ton PC. Ça ne marche que si le client LoL est ouvert et connecté.
"""
from __future__ import annotations

import base64
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

from stats import QUEUES, TIERS_FR, RankInfo

NO_WINDOW = 0x08000000  # pas de console noire qui clignote


class LcuError(Exception):
    pass


@dataclass(frozen=True)
class Connection:
    port: int
    token: str


def find_connection() -> Connection | None:
    """Port et mot de passe du client LoL ouvert (lus dans sa ligne de commande). None s'il est fermé."""
    if sys.platform != "win32":
        return None
    command = "(Get-CimInstance Win32_Process -Filter \"Name='LeagueClientUx.exe'\").CommandLine"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                             capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    port = re.search(r"--app-port=(\d+)", out)
    token = re.search(r"--remoting-auth-token=([\w-]+)", out)
    return Connection(int(port.group(1)), token.group(1)) if port and token else None


# Le client utilise un certificat signé par Riot, que Windows ne connaît pas : on n'accepte ce
# certificat que pour 127.0.0.1 (jamais pour internet).
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE
_OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL))


def _get(conn: Connection, path: str):
    auth = base64.b64encode(f"riot:{conn.token}".encode()).decode()
    request = urllib.request.Request(f"https://127.0.0.1:{conn.port}{path}",
                                     headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    try:
        with _OPENER.open(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise LcuError(str(exc)) from exc


def read_riot_id(conn: Connection) -> str:
    """Riot ID (Nom#TAG) du compte connecté. Lève LcuError si le client n'est pas encore connecté."""
    summoner = _get(conn, "/lol-summoner/v1/current-summoner")
    name, tag = summoner.get("gameName"), summoner.get("tagLine")
    if not (name and tag):
        raise LcuError("compte pas encore prêt")
    return f"{name}#{tag}"


def read_rank(conn: Connection) -> RankInfo | None:
    """Rang du compte connecté (Solo/Duo, sinon Flex). None s'il n'est pas classé."""
    queue_map = _get(conn, "/lol-ranked/v1/current-ranked-stats").get("queueMap") or {}
    for queue_type, queue_name in QUEUES:
        entry = queue_map.get(queue_type) or {}
        tier = str(entry.get("tier", "")).upper()
        if tier in TIERS_FR:
            return RankInfo(tier, str(entry.get("division", "")), int(entry.get("leaguePoints", 0)),
                            int(entry.get("wins", 0)), int(entry.get("losses", 0)), queue_name)
    return None


def wait_for_account(
    before: Connection | None,
    cancel: Callable[[], bool] = lambda: False,
    timeout: float = 300.0,
    interval: float = 3.0,
    unranked_grace: float = 30.0,
) -> tuple[str, RankInfo | None] | None:
    """Attend que le client LoL relancé soit connecté, puis renvoie (Riot ID, rang).

    `before` : connexion du client ouvert avant le changement de compte. On l'ignore : le but est de
    lire le NOUVEAU compte, jamais l'ancien. Renvoie None si rien n'est lu à temps ou si `cancel()`.
    Si le rang reste vide `unranked_grace` secondes, le compte est considéré comme non classé.
    """
    deadline = time.time() + timeout
    riot_id: str | None = None
    ready_since: float | None = None
    while time.time() < deadline and not cancel():
        conn = find_connection()
        if conn is not None and conn != before:
            try:
                riot_id = riot_id or read_riot_id(conn)
                info = read_rank(conn)
                if info is not None:
                    return riot_id, info
                ready_since = ready_since or time.time()
                if time.time() - ready_since > unranked_grace:
                    return riot_id, None
            except LcuError:
                pass  # le client démarre encore : on réessaie
        time.sleep(interval)
    return None
