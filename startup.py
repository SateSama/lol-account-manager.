"""Lancement automatique au démarrage de Windows (clé « Run » de l'utilisateur, sans droits admin)."""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "LolAccountManager"


def _command() -> str:
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):  # version .exe (PyInstaller)
        return f'"{exe}"'
    pythonw = exe.with_name("pythonw.exe")  # pythonw : pas de fenêtre console noire
    runner = pythonw if pythonw.exists() else exe
    script = Path(__file__).with_name("main.py").resolve()
    return f'"{runner}" "{script}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def set_enabled(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
