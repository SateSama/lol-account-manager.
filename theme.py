"""Couleurs et petits utilitaires visuels (thème sombre « hextech » : fond bleu nuit, accents or)."""
from __future__ import annotations

import zlib

BG = "#0e1116"          # fond de la fenêtre
CARD = "#161a22"        # cartes (comptes, réglages)
CARD_HOVER = "#1c212b"
BORDER = "#262c38"
FIELD = "#0b0e13"       # champs de saisie
TEXT = "#e8eaf0"
MUTED = "#8b93a3"
ACCENT = "#c8aa6e"      # or League of Legends
ACCENT_HOVER = "#dcc088"
ON_ACCENT = "#1a1306"   # texte sur fond or
DANGER = "#e5636b"
DANGER_HOVER = "#3a1f23"
OK = "#4cc38a"

# Couleur du texte du rang, par palier
TIER_COLORS = {
    "IRON": "#8a8580", "BRONZE": "#b4764a", "SILVER": "#a9b4c0", "GOLD": "#e3b341",
    "PLATINUM": "#4fb3a9", "EMERALD": "#3fbf7f", "DIAMOND": "#6c8cf0",
    "MASTER": "#b266e0", "GRANDMASTER": "#e5636b", "CHALLENGER": "#66d3f0",
}

# Couleurs des pastilles d'initiale (une par compte, stable d'un lancement à l'autre)
AVATARS = ["#3b6fd4", "#8a4fd6", "#c2478b", "#d9734a", "#2f9e8f", "#6a8f2a", "#b8892b", "#4a7fa8"]


def avatar_color(key: str) -> str:
    return AVATARS[zlib.crc32(key.encode("utf-8")) % len(AVATARS)]


def initial(label: str) -> str:
    label = label.strip()
    return label[:1].upper() if label else "?"
