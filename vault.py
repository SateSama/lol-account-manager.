"""Coffre chiffré pour les comptes. Tout reste en local, rien n'est envoyé nulle part.

Format du fichier : 16 octets de sel + jeton Fernet (AES-128-CBC + HMAC).
La clé est dérivée du mot de passe maître avec scrypt.
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "LolAccountManager"
VAULT_FILE = APP_DIR / "vault.bin"


class WrongPassword(Exception):
    pass


@dataclass
class Account:
    label: str
    username: str
    password: str
    note: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    riot_id: str = ""      # « Nom#TAG », pour afficher le rang (facultatif)
    region: str = "EUW"    # serveur du compte (voir stats.REGIONS)
    rank: dict = field(default_factory=dict)  # dernier rang connu (voir stats.RankInfo.to_dict)


def _derive_key(master: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1)
    return base64.urlsafe_b64encode(kdf.derive(master.encode("utf-8")))


class Vault:
    def __init__(self) -> None:
        self.accounts: list[Account] = []
        self._salt: bytes = b""
        self._fernet: Fernet | None = None

    @staticmethod
    def exists() -> bool:
        return VAULT_FILE.exists()

    def create(self, master: str) -> None:
        self._salt = os.urandom(16)
        self._fernet = Fernet(_derive_key(master, self._salt))
        self.accounts = []
        self.save()

    def unlock(self, master: str) -> None:
        raw = VAULT_FILE.read_bytes()
        self._salt, token = raw[:16], raw[16:]
        fernet = Fernet(_derive_key(master, self._salt))
        try:
            data = json.loads(fernet.decrypt(token))
        except InvalidToken as exc:
            raise WrongPassword from exc
        self._fernet = fernet
        # On ignore les champs qu'on ne connaît pas : un coffre enregistré par une version plus récente
        # (ou plus ancienne) de l'appli s'ouvre quand même, au lieu de faire planter le démarrage.
        known = {f.name for f in fields(Account)}
        self.accounts = [Account(**{k: v for k, v in item.items() if k in known}) for item in data]

    def save(self) -> None:
        assert self._fernet is not None
        APP_DIR.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([asdict(a) for a in self.accounts]).encode("utf-8")
        tmp = VAULT_FILE.with_suffix(".tmp")
        tmp.write_bytes(self._salt + self._fernet.encrypt(payload))
        tmp.replace(VAULT_FILE)  # écriture atomique : pas de coffre à moitié écrit

    def upsert(self, account: Account) -> None:
        for i, existing in enumerate(self.accounts):
            if existing.id == account.id:
                self.accounts[i] = account
                break
        else:
            self.accounts.append(account)
        self.save()

    def delete(self, account_id: str) -> None:
        self.accounts = [a for a in self.accounts if a.id != account_id]
        self.save()
