"""Emblèmes de rang pour les cartes (LoL et Valorant).

Les emblèmes sont dessinés par le programme (aucun téléchargement). Pour utiliser les illustrations de
ton choix, dépose des PNG dans un dossier « icons » à côté du programme, nommés :
  LoL      : iron.png, bronze.png, silver.png, gold.png, platinum.png, emerald.png, diamond.png,
             master.png, grandmaster.png, challenger.png
  Valorant : valo_iron.png, valo_bronze.png, valo_silver.png, valo_gold.png, valo_platinum.png,
             valo_diamond.png, valo_ascendant.png, valo_immortal.png, valo_radiant.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw

import theme

SIZE = 36          # taille affichée (pixels)
_SCALE = 6         # dessin 6 fois plus grand puis réduit : bords lissés
_cache: dict[tuple[str, str], ctk.CTkImage] = {}

LOL_TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
VALO_TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "ASCENDANT", "IMMORTAL", "RADIANT"]
VALO_NAMES_FR = {"IRON": "Fer", "BRONZE": "Bronze", "SILVER": "Argent", "GOLD": "Or", "PLATINUM": "Platine",
                 "DIAMOND": "Diamant", "ASCENDANT": "Ascendant", "IMMORTAL": "Immortel", "RADIANT": "Radiant"}
VALO_TOP = {"RADIANT"}  # pas de division (1 à 3)

_COLORS = {**theme.TIER_COLORS, **theme.VALO_COLORS}


def _icons_dir() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "icons"


def _hex(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _draw(tier: str, game: str) -> Image.Image:
    """Emblème : écusson hexagonal à la couleur du rang, avec chevrons (le nombre monte avec le rang)."""
    s = SIZE * _SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = _hex(_COLORS.get(tier, theme.MUTED))
    dark = _mix(color, _hex(theme.BG), 0.78)
    tiers = VALO_TIERS if game == "valo" else LOL_TIERS
    rank = tiers.index(tier) if tier in tiers else -1
    cx, cy = s / 2, s / 2

    def hexagon(radius: float) -> list[tuple[float, float]]:
        import math
        return [(cx + radius * math.cos(math.radians(60 * i - 90)), cy + radius * math.sin(math.radians(60 * i - 90)))
                for i in range(6)]

    d.polygon(hexagon(s * 0.46), fill=dark + (255,), outline=color + (255,), width=max(2, s // 22))
    if rank < 0:  # non classé : écusson vide
        d.line([(cx - s * 0.16, cy), (cx + s * 0.16, cy)], fill=_hex(theme.MUTED) + (255,), width=s // 14)
        return img.resize((SIZE, SIZE), Image.LANCZOS)

    chevrons = 1 + rank * 3 // (len(tiers) - 1)  # 1 chevron pour le rang le plus bas, 4 pour le plus haut
    width = max(2, s // 16)
    top = cy - s * 0.17 - (chevrons - 1) * s * 0.07
    for i in range(chevrons):
        y = top + i * s * 0.14
        d.line([(cx - s * 0.2, y), (cx, y + s * 0.13), (cx + s * 0.2, y)], fill=color + (255,), width=width, joint="curve")
    if rank >= len(tiers) - 3:  # rangs les plus hauts : un éclat au sommet
        d.polygon([(cx, s * 0.09), (cx + s * 0.05, s * 0.2), (cx - s * 0.05, s * 0.2)], fill=color + (255,))
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def icon(tier: str, game: str = "lol") -> ctk.CTkImage:
    """Emblème du rang (`tier` en majuscules ; vide = non classé). `game` : « lol » ou « valo »."""
    tier = tier.upper()
    key = (game, tier)
    if key not in _cache:
        name = ("valo_" if game == "valo" else "") + (tier.lower() or "unranked")
        custom = _icons_dir() / f"{name}.png"
        image = None
        if custom.is_file():
            try:
                image = Image.open(custom).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
            except OSError:
                image = None
        if image is None:
            image = _draw(tier, game)
        _cache[key] = ctk.CTkImage(light_image=image, dark_image=image, size=(SIZE, SIZE))
    return _cache[key]
