"""Couleurs et petits utilitaires visuels : thème sombre sobre (gris anthracite, un seul accent clair)."""
from __future__ import annotations

FONT = "Segoe UI"       # police de Windows ; ailleurs, Tk retombe sur sa police par défaut

BG = "#101113"          # fond de la fenêtre
CARD = "#16181b"        # cartes (comptes, fenêtres)
CARD_HOVER = "#1d2024"
BORDER = "#25282d"
FIELD = "#0d0e10"       # champs de saisie
AVATAR = "#202328"      # fond de la pastille d'initiale
TEXT = "#ececee"
MUTED = "#80858f"
ACCENT = "#e8eaee"      # boutons principaux : clair sur fond sombre
ACCENT_HOVER = "#ffffff"
ON_ACCENT = "#101113"   # texte sur fond clair
DANGER = "#df6b71"
DANGER_HOVER = "#2a1b1d"
OK = "#5bb98c"

# Couleur du texte du rang, par palier (seule touche de couleur de l'interface)
TIER_COLORS = {
    "IRON": "#8a8580", "BRONZE": "#b4764a", "SILVER": "#a9b4c0", "GOLD": "#e3b341",
    "PLATINUM": "#4fb3a9", "EMERALD": "#3fbf7f", "DIAMOND": "#6c8cf0",
    "MASTER": "#b266e0", "GRANDMASTER": "#e5636b", "CHALLENGER": "#66d3f0",
}


def initial(label: str) -> str:
    label = label.strip()
    return label[:1].upper() if label else "?"
