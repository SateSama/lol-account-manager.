"""« Se souvenir sur ce PC » : évite de retaper le mot de passe maître à chaque lancement.

Le mot de passe maître est protégé par Windows (DPAPI) : il n'est lisible que par TON
compte Windows, sur CE PC. Le fichier copié sur un autre PC ou un autre compte est inutilisable.
Compromis : quelqu'un qui ouvre ta session Windows peut lancer l'appli sans mot de passe.
Le bouton « Verrouiller » de l'appli supprime ce souvenir.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from vault import APP_DIR

REMEMBER_FILE = APP_DIR / "remember.bin"
_ENTROPY = b"LolAccountManager.remember.v1"  # lie le blob à cette appli


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]


def _make_blob(data: bytes) -> tuple[_Blob, ctypes.Array]:
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.c_void_p)), buf  # buf doit rester vivant


def _call(func_name: str, data: bytes) -> bytes:
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    blob_in, _keep1 = _make_blob(data)
    blob_ent, _keep2 = _make_blob(_ENTROPY)
    blob_out = _Blob()
    func = getattr(crypt32, func_name)  # CryptProtectData ou CryptUnprotectData (même signature)
    ok = func(ctypes.byref(blob_in), None, ctypes.byref(blob_ent), None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError(f"{func_name} a échoué")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _protect(data: bytes) -> bytes:
    return _call("CryptProtectData", data)


def _unprotect(data: bytes) -> bytes:
    return _call("CryptUnprotectData", data)


def is_enabled() -> bool:
    return REMEMBER_FILE.exists()


def save(master: str) -> None:
    """Mémorise le mot de passe maître (chiffré par Windows). Sans effet hors Windows."""
    if sys.platform != "win32":
        return
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = REMEMBER_FILE.with_suffix(".tmp")
    tmp.write_bytes(_protect(master.encode("utf-8")))
    tmp.replace(REMEMBER_FILE)


def load() -> str | None:
    """Renvoie le mot de passe mémorisé, ou None s'il n'y en a pas / s'il est illisible."""
    if sys.platform != "win32" or not REMEMBER_FILE.exists():
        return None
    try:
        return _unprotect(REMEMBER_FILE.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def forget() -> None:
    try:
        Path(REMEMBER_FILE).unlink(missing_ok=True)
    except OSError:
        pass
