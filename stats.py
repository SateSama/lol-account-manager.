"""Rang et winrate d'un compte, via l'API officielle de Riot (Account-v1 puis League-v4).

Seuls le Riot ID (Nom#TAG) et ta clé API sont envoyés à Riot. L'identifiant de connexion
et le mot de passe des comptes ne quittent jamais le PC.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date

from vault import APP_DIR

SETTINGS_FILE = APP_DIR / "settings.json"

# nom affiché -> (serveur, routage régional utilisé par Account-v1)
REGIONS: dict[str, tuple[str, str]] = {
    "EUW": ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "TR": ("tr1", "europe"),
    "RU": ("ru", "europe"),
    "NA": ("na1", "americas"),
    "BR": ("br1", "americas"),
    "LAN": ("la1", "americas"),
    "LAS": ("la2", "americas"),
    "KR": ("kr", "asia"),
    "JP": ("jp1", "asia"),
    "OCE": ("oc1", "americas"),
}
DEFAULT_REGION = "EUW"

TIERS_FR = {
    "IRON": "Fer", "BRONZE": "Bronze", "SILVER": "Argent", "GOLD": "Or", "PLATINUM": "Platine",
    "EMERALD": "Émeraude", "DIAMOND": "Diamant", "MASTER": "Maître",
    "GRANDMASTER": "Grand Maître", "CHALLENGER": "Challenger",
}
APEX_TIERS = {"MASTER", "GRANDMASTER", "CHALLENGER"}  # pas de division (I à IV)
QUEUES = (("RANKED_SOLO_5x5", "Solo/Duo"), ("RANKED_FLEX_SR", "Flex"))


class StatsError(Exception):
    """Erreur lisible à afficher telle quelle. `fatal` : inutile d'interroger les autres comptes."""

    def __init__(self, message: str, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal


@dataclass
class RankInfo:
    tier: str
    division: str
    lp: int
    wins: int
    losses: int
    queue: str

    @property
    def games(self) -> int:
        return self.wins + self.losses

    @property
    def winrate(self) -> int:
        return round(100 * self.wins / self.games) if self.games else 0

    def rank_text(self) -> str:
        name = TIERS_FR.get(self.tier, self.tier.title())
        if self.tier not in APEX_TIERS:
            name += f" {self.division}"
        return f"{name} · {self.lp} LP"

    def winrate_text(self) -> str:
        return f"{self.winrate} % ({self.wins}V {self.losses}D)"

    def to_dict(self) -> dict:
        """Version enregistrable dans le coffre (dernier rang connu), datée d'aujourd'hui."""
        return {**asdict(self), "updated": date.today().isoformat()}

    @classmethod
    def from_dict(cls, data: dict) -> "RankInfo":
        return cls(str(data["tier"]), str(data.get("division", "")), int(data.get("lp", 0)),
                   int(data.get("wins", 0)), int(data.get("losses", 0)), str(data.get("queue", "")))


def age_text(updated: str | None) -> str:
    """« hier », « il y a 3 j »... Chaîne vide si c'est d'aujourd'hui ou si la date est illisible."""
    try:
        days = (date.today() - date.fromisoformat(updated or "")).days
    except ValueError:
        return ""
    if days <= 0:
        return ""
    return "hier" if days == 1 else f"il y a {days} j"


# ---------------------------------------------------------------- clé API (réglages locaux)
def load_key() -> str:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("riot_api_key", "").strip()
    except (OSError, ValueError):
        return ""


def save_key(key: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"riot_api_key": key.strip()}), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


# ---------------------------------------------------------------- appels à l'API
_puuid_cache: dict[tuple[str, str], str] = {}  # (riot_id, région) -> puuid : évite un appel par actualisation


def _get(url: str, key: str, not_found: str = "Introuvable"):
    request = urllib.request.Request(url, headers={"X-Riot-Token": key, "User-Agent": "LolAccountManager"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise StatsError("Clé API refusée ou expirée", fatal=True) from exc
        if exc.code == 404:
            raise StatsError(not_found) from exc
        if exc.code == 429:
            raise StatsError("Trop de requêtes, réessaie dans un instant", fatal=True) from exc
        raise StatsError(f"Erreur Riot ({exc.code})") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise StatsError("Pas de connexion à Riot", fatal=True) from exc
    except ValueError as exc:
        raise StatsError("Réponse de Riot illisible") from exc


def parse_riot_id(riot_id: str) -> tuple[str, str]:
    name, sep, tag = riot_id.strip().rpartition("#")
    if not (sep and name.strip() and tag.strip()):
        raise StatsError("Riot ID invalide (format Nom#TAG)")
    return name.strip(), tag.strip()


def fetch_rank(riot_id: str, region: str, key: str) -> RankInfo | None:
    """Rang du compte (Solo/Duo, sinon Flex). None si le compte n'est pas classé."""
    platform, routing = REGIONS.get(region, REGIONS[DEFAULT_REGION])
    name, tag = parse_riot_id(riot_id)

    puuid = _puuid_cache.get((riot_id, region))
    if puuid is None:
        account = _get(
            f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
            f"{urllib.parse.quote(name, safe='')}/{urllib.parse.quote(tag, safe='')}",
            key, not_found="Riot ID introuvable (vérifie Nom#TAG et le serveur)",
        )
        puuid = account["puuid"]
        _puuid_cache[(riot_id, region)] = puuid

    entries = _get(
        f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{urllib.parse.quote(puuid, safe='')}",
        key,
    )
    for queue_type, queue_name in QUEUES:
        for entry in entries:
            if entry.get("queueType") == queue_type:
                return RankInfo(entry["tier"], entry.get("rank", ""), entry.get("leaguePoints", 0),
                                entry.get("wins", 0), entry.get("losses", 0), queue_name)
    return None
