# -*- coding: utf-8 -*-
"""Config visual + settings (sem dependencias da UI)."""

import json
import os

from .paths import IMAGES_DIR, SETTINGS_FILE


class Config:
    CARD_WIDTH = 260
    CARD_HEIGHT = 340
    CARD_PADDING = 14
    LOGO_SIZE = 80
    SIDEBAR_WIDTH = 380

    BG_PRIMARY = "#0a0a14"
    BG_SECONDARY = "#111122"
    BG_CARD = "#1a1a2e"
    BG_CARD_HOVER = "#252548"
    BG_SIDEBAR = "#0d0b1f"
    ACCENT = "#7c4dff"
    ACCENT_GLOW = "#b048ff"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#8888bb"
    BORDER = "#2a2545"


DEFAULT_SETTINGS = {
    "favorites": ["Netflix", "YouTube", "Spotify"],
    "custom_streamings": {},
    "search_history": [],
    "current_tab": "all",
    "language": "pt-br",
    "pad_nexus": {},
    "pad_remote": {},
    "pad_sensitivity": 12,
    "pad_scroll": 8,
    "card_colors": {},
    "custom_urls": {},
    "resolution_mode": "fullscreen",
    "window_width": 1920,
    "window_height": 1080,
    "embedded_browser": True,
    "pad_device_guid": "",
    "pad_deadzone": 22,
    "pad_profiles": {},
    "pad_profile_active": 1,
    "pad_per_device": {},
    "sound_volume": 10,
    "nav_sound": True,
    "sound_default": 70,
    "kb_layout": "us",
    "notif_seen_update": "",
    "update_seen": "",
    "external_games": {},
    "platform_games": {},
    "platform_ignored": [],
    "browser_profile_dir": "",
    "view_modes": {},
    "game_favorites": [],
    "pro_license": "",
    "pro_license_info": {},
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_SETTINGS, **data}
                merged.setdefault("custom_streamings", {})
                merged.setdefault("external_games", {})
                merged.setdefault("platform_games", {})
                merged.setdefault("platform_ignored", [])
                merged.setdefault("view_modes", {})
                merged.setdefault("favorites", DEFAULT_SETTINGS["favorites"])
                merged.setdefault("search_history", [])
                return merged
        except:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


# Abas visiveis na barra superior (aba Home foi removida)
TABS = ["favorites", "movies", "music", "videos", "all", "games",
        "gamefavorites"]

# Modos de exibicao estilo Windows Explorer (por aba, salvos em view_modes).
# cards = carrossel atual | grid = grade | list = lista | details = detalhes
VIEW_MODES = ("cards", "grid", "list", "details")
VIEW_MODE_ICONS = {"cards": "\u25A6", "grid": "\u25A3",
                   "list": "\u2630", "details": "\u25A4"}
VIEW_TAB_DEFAULT = {"all": "grid"}


def view_mode_default(tab):
    return VIEW_TAB_DEFAULT.get(tab, "cards")


def ensure_images_dir():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
