# -*- coding: utf-8 -*-
import os as _os
import sys as _sys
# Sem console (pythonw.exe): esconde banner do pygame, evita crash em print
# e grava erros nao tratados em nexus_error.log
_os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
if _sys.stdout is None:
    _sys.stdout = open(_os.devnull, "w")
if _sys.stderr is None:
    _sys.stderr = open(_os.devnull, "w")


def _nexus_excepthook(exc_type, exc_value, exc_tb):
    try:
        import traceback as _tb
        import datetime as _dt
        base = _os.path.dirname(_os.path.realpath(_sys.argv[0] or "."))
        with open(_os.path.join(base, "nexus_error.log"), "a", encoding="utf-8") as f:
            f.write(_dt.datetime.now().isoformat() + " UNCAUGHT\n")
            _tb.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass


if (_sys.executable or "").lower().endswith("pythonw.exe"):
    _sys.excepthook = _nexus_excepthook

import tkinter as tk
import tkinter.ttk as tk_ttk
from tkinter import messagebox, filedialog, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageFilter
from shutil import copy2
import shutil
import webbrowser
import json
import os
import re
import sys
import sqlite3
import subprocess
import threading
import time
import random
import ctypes
import urllib.parse
import winreg
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    import pygame
    import pygame.joystick
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import webview as _pywebview  # noqa: F401  (navegador embutido)
    WEBVIEW_AVAILABLE = True
except ImportError:
    _pywebview = None
    WEBVIEW_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
IMAGES_DIR = os.path.join(BASE_DIR, "streaming_images")
DATABASE_FILE = os.path.join(BASE_DIR, "nexus.db")
NEXUS_BROWSER_FILE = os.path.join(BASE_DIR, "nexus_browser.py")
NEXUS_BROWSER_EXE = os.path.join(BASE_DIR, "nexus_browser.exe")


def nexus_profile_dir():
    """Perfil do navegador embutido (logins, cookies, senhas)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "Nexus", "browser_profile")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def browser_profile_size():
    total = 0
    try:
        for dirpath, _dirnames, files in os.walk(nexus_profile_dir()):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def browser_running():
    return any(p.poll() is None for p in BROWSER_PROCS)


def clear_browser_profile():
    """Apaga logins/cookies/cache do navegador embutido. False se em uso."""
    if browser_running():
        return False
    try:
        shutil.rmtree(nexus_profile_dir(), ignore_errors=True)
        os.makedirs(nexus_profile_dir(), exist_ok=True)
        return True
    except Exception:
        return False


BROWSER_PROCS = []


# ===================== CONFIG =====================
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


# ===================== STREAMINGS DB =====================
STREAMINGS_DB = {
    "Netflix": {"url": "https://www.netflix.com", "category": "Filmes", "icon": "\U0001F3AC", "color": "#E50914",
                "deep_link": "netflix://watch/{id}", "url_template": "https://www.netflix.com/title/{id}",
                "top_content": [{"id": "81345507", "title": "Stranger Things"}, {"id": "80175798", "title": "The Witcher"}, {"id": "80234375", "title": "Dahmer"}]},
    "YouTube": {"url": "https://www.youtube.com", "category": "Videos", "icon": "\U0001F509", "color": "#FF0000",
                "deep_link": "youtube://watch?v={id}", "url_template": "https://www.youtube.com/watch?v={id}",
                "top_content": [{"id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up"}, {"id": "M7FIvfx5J10", "title": "Minecraft Trailer"}, {"id": "kJQP7kiw5Fk", "title": "Despacito"}]},
    "Spotify": {"url": "https://www.spotify.com", "category": "Musica", "icon": "\U0001F3B5", "color": "#1DB954",
                "deep_link": "", "url_template": "https://open.spotify.com",
                "top_content": [{"id": "", "title": "Top Hits"}, {"id": "", "title": "Discover Weekly"}, {"id": "", "title": "Release Radar"}]},
    "Disney+": {"url": "https://www.disneyplus.com", "category": "Filmes", "icon": "\U0001F3AD", "color": "#113CCF",
                "deep_link": "disneyplus://title/{id}", "url_template": "https://www.disneyplus.com/video/{id}",
                "top_content": [{"id": "4uTZvR2F8zEJ", "title": "The Mandalorian"}, {"id": "2XmJZ2k4nQ1P", "title": "Loki"}, {"id": "3yQJmXk9tR5W", "title": "Deadpool & Wolverine"}]},
    "Amazon Prime": {"url": "https://www.primevideo.com", "category": "Filmes", "icon": "\U0001F4E6", "color": "#00A8E1",
                     "deep_link": "primevideo://detail/{id}", "url_template": "https://www.primevideo.com/dp/{id}",
                     "top_content": [{"id": "tt17402904", "title": "The Boys"}, {"id": "tt17276090", "title": "Fallout"}, {"id": "tt15398776", "title": "Reacher"}]},
    "HBO Max": {"url": "https://www.max.com", "category": "Filmes", "icon": "\U0001F4FA", "color": "#B01CDE",
                "deep_link": "hbomax://title/{id}", "url_template": "https://www.max.com/title/{id}",
                "top_content": [{"id": "tt0903747", "title": "Breaking Bad"}, {"id": "tt28404886", "title": "The Last of Us"}, {"id": "tt33594241", "title": "House of the Dragon"}]},
    "Twitch": {"url": "https://www.twitch.tv", "category": "Videos", "icon": "\U0001F6A8", "color": "#9146FF",
               "deep_link": "twitch://stream/{id}", "url_template": "https://www.twitch.tv/{id}",
               "top_content": [{"id": "shroud", "title": "shroud"}, {"id": "xQc", "title": "xQc"}, {"id": "ironmouse", "title": "ironmouse"}]},
    "Crunchyroll": {"url": "https://www.crunchyroll.com", "category": "Filmes", "icon": "\U0001F310", "color": "#F47521",
                    "deep_link": "", "url_template": "https://www.crunchyroll.com/series/{id}",
                    "top_content": [{"id": "", "title": "One Piece"}, {"id": "", "title": "Jujutsu Kaisen"}, {"id": "", "title": "Demon Slayer"}]},
    "Dailymotion": {"url": "https://www.dailymotion.com", "category": "Videos", "icon": "\U0001F4F1", "color": "#0066DC",
                    "deep_link": "", "url_template": "https://www.dailymotion.com/video/{id}",
                    "top_content": [{"id": "", "title": "Trending"}, {"id": "", "title": "News"}, {"id": "", "title": "Sports"}]},
    "Bandcamp": {"url": "https://www.bandcamp.com", "category": "Musica", "icon": "\U0001F3BA", "color": "#629AA9",
                 "deep_link": "", "url_template": "https://bandcamp.com",
                 "top_content": [{"id": "", "title": "New Releases"}, {"id": "", "title": "Best Sellers"}, {"id": "", "title": "Staff Picks"}]},
    "SoundCloud": {"url": "https://www.soundcloud.com", "category": "Musica", "icon": "\U0001F3B6", "color": "#FF5500",
                   "deep_link": "", "url_template": "https://soundcloud.com/{id}",
                   "top_content": [{"id": "", "title": "Top 50"}, {"id": "", "title": "New & Hot"}, {"id": "", "title": "Chill"}]},
    "Pluto TV": {"url": "https://pluto.tv", "category": "Filmes", "icon": "\U0001F52A", "color": "#2B2B2B",
                 "deep_link": "", "url_template": "https://pluto.tv",
                 "top_content": [{"id": "", "title": "Live TV"}, {"id": "", "title": "Movies"}, {"id": "", "title": "Entertainment"}]},
    "Apple TV": {"url": "https://tv.apple.com", "category": "Filmes", "icon": "\U0001F3AC", "color": "#555555",
                 "deep_link": "tv://{id}", "url_template": "https://tv.apple.com/show/{id}",
                 "top_content": [{"id": "", "title": "Ted Lasso"}, {"id": "", "title": "Severance"}, {"id": "", "title": "The Morning Show"}]},
    "Peacock": {"url": "https://www.peacocktv.com", "category": "Filmes", "icon": "\U0001F985", "color": "#000000",
                "deep_link": "", "url_template": "https://www.peacocktv.com/{id}",
                "top_content": [{"id": "", "title": "The Office"}, {"id": "", "title": "Poker Face"}, {"id": "", "title": "Twisted Metal"}]},
    "Paramount+": {"url": "https://www.paramountplus.com", "category": "Filmes", "icon": "\u2B50", "color": "#0064FF",
                   "deep_link": "", "url_template": "https://www.paramountplus.com/{id}",
                   "top_content": [{"id": "", "title": "Star Trek"}, {"id": "", "title": "Yellowjackets"}, {"id": "", "title": "1883"}]},
    "Discovery+": {"url": "https://www.discoveryplus.com", "category": "Filmes", "icon": "\U0001F30D", "color": "#0A0A0A",
                   "deep_link": "", "url_template": "https://www.discoveryplus.com/{id}",
                   "top_content": [{"id": "", "title": "Planet Earth"}, {"id": "", "title": "Deadliest Catch"}, {"id": "", "title": "Gold Rush"}]},
    "Globoplay": {"url": "https://globoplay.globo.com", "category": "Filmes", "icon": "\U0001F3AC", "color": "#E41E2C",
                  "deep_link": "", "url_template": "https://globoplay.globo.com/{id}",
                  "top_content": [{"id": "", "title": "Big Brother Brasil"}, {"id": "", "title": "Cidade Invisivel"}, {"id": "", "title": "Todas as Mulheres"}]},
    "Vix": {"url": "https://www.vix.com", "category": "Filmes", "icon": "\U0001F3AC", "color": "#E30613",
            "deep_link": "", "url_template": "https://www.vix.com/{id}",
            "top_content": [{"id": "", "title": "La Reina del Sur"}, {"id": "", "title": "El Señor de los Cielos"}, {"id": "", "title": "Secretos de Familia"}]},
    "Curiosity Stream": {"url": "https://curiositystream.com", "category": "Filmes", "icon": "\U0001F52D", "color": "#1A1A2E",
                         "deep_link": "", "url_template": "https://curiositystream.com/{id}",
                         "top_content": [{"id": "", "title": "Deep Planet"}, {"id": "", "title": "Ancient Earth"}, {"id": "", "title": "Breakthrough"}]},
    "MUBI": {"url": "https://mubi.com", "category": "Filmes", "icon": "\U0001F3AC", "color": "#000000",
             "deep_link": "", "url_template": "https://mubi.com/films/{id}",
             "top_content": [{"id": "", "title": "Film of the Day"}, {"id": "", "title": "Cult Classics"}, {"id": "", "title": "New Releases"}]},
    "Shudder": {"url": "https://www.shudder.com", "category": "Filmes", "icon": "\U0001F47B", "color": "#FF3333",
                "deep_link": "", "url_template": "https://www.shudder.com/{id}",
                "top_content": [{"id": "", "title": "The Last Drive-In"}, {"id": "", "title": "Creepshow"}, {"id": "", "title": "Late Night with the Devil"}]},
    "BritBox": {"url": "https://www.britbox.com", "category": "Filmes", "icon": "\U0001F1EC\U0001F1E7", "color": "#2C3E50",
                "deep_link": "", "url_template": "https://www.britbox.com/{id}",
                "top_content": [{"id": "", "title": "Doctor Who"}, {"id": "", "title": "Broadchurch"}, {"id": "", "title": "Downton Abbey"}]},
    "Tubi": {"url": "https://tubitv.com", "category": "Filmes", "icon": "\U0001F4FA", "color": "#FA382F",
             "deep_link": "", "url_template": "https://tubitv.com/{id}",
             "top_content": [{"id": "", "title": "Free Movies"}, {"id": "", "title": "TV Shows"}, {"id": "", "title": "Anime"}]},
    "Plex": {"url": "https://www.plex.tv", "category": "Filmes", "icon": "\U0001F3AC", "color": "#EBAF00",
             "deep_link": "", "url_template": "https://app.plex.tv/{id}",
             "top_content": [{"id": "", "title": "Live TV"}, {"id": "", "title": "Free Movies"}, {"id": "", "title": "My Library"}]},
    "Kodi": {"url": "https://kodi.tv", "category": "Videos", "icon": "\U0001F3AC", "color": "#17B2E7",
             "deep_link": "", "url_template": "https://kodi.tv/{id}",
             "top_content": [{"id": "", "title": "Add-ons"}, {"id": "", "title": "Movies"}, {"id": "", "title": "TV Shows"}]},
    "Jellyfin": {"url": "https://jellyfin.org", "category": "Videos", "icon": "\U0001F3AC", "color": "#9B59B6",
                 "deep_link": "", "url_template": "https://jellyfin.org/{id}",
                 "top_content": [{"id": "", "title": "Movies"}, {"id": "", "title": "TV Shows"}, {"id": "", "title": "Music"}]},
    "Mixer": {"url": "https://mixer.com", "category": "Videos", "icon": "\U0001F6A8", "color": "#0024AF",
              "deep_link": "", "url_template": "https://mixer.com/{id}",
              "top_content": [{"id": "", "title": "Trending"}, {"id": "", "title": "Gaming"}, {"id": "", "title": "Creative"}]},
    "Vimeo": {"url": "https://vimeo.com", "category": "Videos", "icon": "\U0001F3AC", "color": "#1AB7EA",
              "deep_link": "", "url_template": "https://vimeo.com/{id}",
              "top_content": [{"id": "", "title": "Staff Picks"}, {"id": "", "title": "Best of the Year"}, {"id": "", "title": "Categories"}]},
    "Rumble": {"url": "https://rumble.com", "category": "Videos", "icon": "\U0001F4FA", "color": "#85C7DE",
               "deep_link": "", "url_template": "https://rumble.com/{id}",
               "top_content": [{"id": "", "title": "Trending"}, {"id": "", "title": "News"}, {"id": "", "title": "Sports"}]},
    "Tidal": {"url": "https://tidal.com", "category": "Musica", "icon": "\U0001F3B5", "color": "#000000",
              "deep_link": "", "url_template": "https://tidal.com/{id}",
              "top_content": [{"id": "", "title": "Tidal Rising"}, {"id": "", "title": "HiFi Playlists"}, {"id": "", "title": "New Releases"}]},
    "Deezer": {"url": "https://www.deezer.com", "category": "Musica", "icon": "\U0001F3B5", "color": "#A238FF",
               "deep_link": "", "url_template": "https://deezer.com/{id}",
               "top_content": [{"id": "", "title": "Editorial"}, {"id": "", "title": "Podcasts"}, {"id": "", "title": "New Releases"}]},
    "Mixcloud": {"url": "https://www.mixcloud.com", "category": "Musica", "icon": "\U0001F3B5", "color": "#5000E5",
                 "deep_link": "", "url_template": "https://mixcloud.com/{id}",
                 "top_content": [{"id": "", "title": "Trending"}, {"id": "", "title": "Fresh Mixes"}, {"id": "", "title": "Live Sets"}]},
}


# ===================== SETTINGS =====================
DEFAULT_SETTINGS = {
    "favorites": ["Netflix", "YouTube", "Spotify"],
    "custom_streamings": {},
    "search_history": [],
    "current_tab": "all",
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
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_SETTINGS, **data}
                merged.setdefault("custom_streamings", {})
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
TABS = ["favorites", "movies", "music", "videos", "all"]


def ensure_images_dir():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)


# ===================== DATABASE =====================
class NexusDB:
    def __init__(self, db_path=DATABASE_FILE):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            content_title TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS stats (
            service_name TEXT PRIMARY KEY,
            total_watches INTEGER DEFAULT 0,
            last_watched DATETIME
        )''')
        conn.commit()
        conn.close()

    def add_history(self, service_name, content_title="Home"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO history (service_name, content_title) VALUES (?, ?)",
                  (service_name, content_title))
        c.execute("""INSERT INTO stats (service_name, total_watches, last_watched)
                     VALUES (?, 1, CURRENT_TIMESTAMP)
                     ON CONFLICT(service_name) DO UPDATE SET
                     total_watches = total_watches + 1,
                     last_watched = CURRENT_TIMESTAMP""",
                  (service_name,))
        conn.commit()
        conn.close()

    def get_recent_history(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT service_name, content_title, timestamp FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = [{"service": r[0], "title": r[1], "time": r[2]} for r in c.fetchall()]
        conn.close()
        return rows

    def get_top_services(self, limit=6):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT service_name, total_watches FROM stats ORDER BY total_watches DESC LIMIT ?", (limit,))
        rows = [{"service": r[0], "watches": r[1]} for r in c.fetchall()]
        conn.close()
        return rows


# ===================== DEEP LINK OPENER =====================
class StreamingOpener:
    def __init__(self, settings=None):
        self.all_services = {**STREAMINGS_DB}
        self.settings = settings if settings is not None else {}

    def effective_url(self, service_name):
        settings = self.settings or {}
        over = settings.get("custom_urls", {}).get(service_name)
        if over:
            return over
        info = self.all_services.get(service_name)
        if info is None:
            info = settings.get("custom_streamings", {}).get(service_name, {})
        return info.get("url", "#")

    def open_content(self, service_name, content_id=None):
        settings = self.settings or {}
        over = settings.get("custom_urls", {}).get(service_name)
        if over:
            url = over.replace("{id}", content_id) if content_id else over
            webbrowser.open(url)
            return
        info = self.all_services.get(service_name)
        if info is None:
            info = settings.get("custom_streamings", {}).get(service_name, {})
        url = info.get("url", "#")

        if content_id and info.get("deep_link"):
            deep = info["deep_link"].replace("{id}", content_id)
            try:
                subprocess.Popen(["cmd", "/c", "start", "", deep], shell=False)
                return
            except:
                pass

        if content_id and info.get("url_template"):
            url = info["url_template"].replace("{id}", content_id)

        webbrowser.open(url)


# ===================== APP LAUNCHER =====================
# Palavras-chave para localizar o app instalado de cada streaming (UWP/atalho/exe)
APP_KEYWORDS = {
    "Netflix": ["netflix"],
    "YouTube": ["youtube"],
    "Spotify": ["spotify"],
    "Disney+": ["disney"],
    "Amazon Prime": ["primevideo", "prime video"],
    "HBO Max": ["hbo"],
    "Twitch": ["twitch"],
    "Crunchyroll": ["crunchyroll"],
    "Dailymotion": ["dailymotion"],
    "Bandcamp": ["bandcamp"],
    "SoundCloud": ["soundcloud"],
    "Pluto TV": ["pluto"],
    "Apple TV": ["apple tv", "appletv"],
    "Peacock": ["peacock"],
    "Paramount+": ["paramount"],
    "Discovery+": ["discovery"],
    "Globoplay": ["globoplay"],
    "Vix": ["vix"],
    "Curiosity Stream": ["curiosity"],
    "MUBI": ["mubi"],
    "Shudder": ["shudder"],
    "BritBox": ["britbox"],
    "Tubi": ["tubi"],
    "Plex": ["plex"],
    "Kodi": ["kodi"],
    "Jellyfin": ["jellyfin"],
    "Mixer": ["mixer"],
    "Vimeo": ["vimeo"],
    "Rumble": ["rumble"],
    "Tidal": ["tidal"],
    "Deezer": ["deezer"],
    "Mixcloud": ["mixcloud"],
}

# Executaveis conhecidos (registro App Paths + PATH)
APP_EXES = {
    "Spotify": ["spotify.exe"],
    "Kodi": ["kodi.exe"],
    "Plex": ["plex.exe", "plexhtpc.exe"],
    "Jellyfin": ["jellyfinmediaplayer.exe"],
    "Deezer": ["deezer.exe"],
    "Tidal": ["tidal.exe"],
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def app_keywords(name):
    if name in APP_KEYWORDS:
        return APP_KEYWORDS[name]
    return [tok for tok in re.split(r"[^a-z0-9]+", name.lower()) if len(tok) >= 2]


def find_uwp_app(keywords):
    """Localiza app UWP/MS Store. Retorna (package_family, app_id) ou None."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-AppxPackage | Select-Object Name,PackageFamilyName,InstallLocation | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=25,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return None
    try:
        data = json.loads((out.stdout or "").strip() or "[]")
    except Exception:
        return None
    if isinstance(data, dict):
        data = [data]
    norms = [_norm(k) for k in keywords if _norm(k)]
    for pkg in data:
        try:
            hay = _norm(f"{pkg.get('Name', '')} {pkg.get('PackageFamilyName', '')}")
            if any(kw and kw in hay for kw in norms):
                loc = pkg.get("InstallLocation") or ""
                return pkg.get("PackageFamilyName"), _uwp_app_id(loc)
        except Exception:
            continue
    return None


def _uwp_app_id(install_location):
    try:
        root = ET.parse(os.path.join(install_location, "AppxManifest.xml")).getroot()
        for el in root.iter():
            if el.tag.endswith("}Application") or el.tag == "Application":
                if el.get("Id"):
                    return el.get("Id")
    except Exception:
        pass
    return "App"


def launch_uwp(pfn, app_id):
    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{pfn}!{app_id}"])


def find_startmenu_app(keywords):
    """Procura atalho .lnk no Menu Iniciar. Retorna o caminho ou None."""
    roots = [
        os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]
    norms = [_norm(k) for k in keywords if _norm(k)]
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for f in sorted(files):
                if not f.lower().endswith(".lnk"):
                    continue
                stem = _norm(os.path.splitext(f)[0])
                if "uninstall" in stem or "uninstal" in stem:
                    continue
                if any(kw and kw in stem for kw in norms):
                    return os.path.join(dirpath, f)
    return None


def find_exe_app(exes):
    """Registro App Paths + PATH. Retorna o caminho ou None."""
    for exe in exes:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(
                            hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\\" + exe,
                            0, winreg.KEY_READ | view) as k:
                        path, _ = winreg.QueryValueEx(k, "")
                        if path and os.path.exists(path):
                            return path
                except OSError:
                    pass
        found = shutil.which(exe)
        if found:
            return found
    return None


def open_app_for_service(name):
    """Tenta abrir o app instalado. Retorna True se abriu, False se nao achou."""
    kws = app_keywords(name)
    try:
        uwp = find_uwp_app(kws)
        if uwp and uwp[0]:
            launch_uwp(*uwp)
            return True
    except Exception:
        pass
    try:
        lnk = find_startmenu_app(kws)
        if lnk:
            os.startfile(lnk)
            return True
    except Exception:
        pass
    try:
        exe = find_exe_app(APP_EXES.get(name, []))
        if exe:
            os.startfile(exe)
            return True
    except Exception:
        pass
    return False


def open_store_search(name):
    try:
        os.startfile("ms-windows-store://search/?query=" + urllib.parse.quote(name))
    except Exception:
        pass


# ===================== NAVEGADOR EMBUTIDO =====================
# O botao Site abre o servico numa janela do proprio Nexus (pywebview +
# Edge WebView2) em vez do navegador externo. Roda como processo separado
# para nao travar o loop do tkinter.
def browser_available():
    if os.path.exists(NEXUS_BROWSER_EXE):
        return True  # release .exe: navegador ja compilado
    return bool(WEBVIEW_AVAILABLE) and os.path.exists(NEXUS_BROWSER_FILE)


def python_for_browser():
    """Interpretador para o processo do navegador (o atual primeiro)."""
    exe = sys.executable or ""
    if exe and os.path.exists(exe):
        return exe
    for cand in (r"D:\Download\Python312\pythonw.exe",
                 r"D:\Download\Python312\python.exe"):
        if os.path.exists(cand):
            return cand
    return None


def open_in_nexus_browser(url, title="Nexus", pad_label=""):
    """Abre a URL no navegador embutido. Retorna o Popen ou None."""
    if not browser_available():
        return None
    try:
        scheme = urllib.parse.urlparse(url).scheme.lower()
    except Exception:
        scheme = ""
    if scheme not in ("http", "https"):
        return None  # WebView2 nao aceita outros esquemas -> navegador externo
    if os.path.exists(NEXUS_BROWSER_EXE):
        try:
            return subprocess.Popen(
                [NEXUS_BROWSER_EXE, url, title, pad_label or ""],
                creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            return None
    if getattr(sys, "frozen", False):
        return None  # .exe sem o navegador junto: cai p/ navegador externo
    exe = python_for_browser()
    if exe is None:
        return None
    try:
        return subprocess.Popen(
            [exe, NEXUS_BROWSER_FILE, url, title, pad_label or ""],
            creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return None


# ===================== INSTALACAO AUTOMATICA (winget/Store) =====================
# Servicos com pacote confirmado via winget nesta maquina:
# servico -> (fonte, id do pacote). Quem nao esta aqui cai na busca da Store.
INSTALL_MAP = {
    "Spotify": ("winget", "Spotify.Spotify"),
    "Kodi": ("msstore", "9NBLGGH4T892"),
    "Deezer": ("msstore", "9NBLGGH6J7VV"),
    "Tidal": ("msstore", "9NNCB5BS59PH"),
    "Plex": ("msstore", "XPFM11Z0W10R7G"),
}


def try_install_service(name, status_cb=None):
    """Baixa e instala o app do servico via winget. Retorna True se instalou."""
    mapping = INSTALL_MAP.get(name)
    if not mapping:
        return False
    source, pkg_id = mapping
    if status_cb is not None:
        try:
            status_cb("dlg_installing")
        except Exception:
            pass
    try:
        proc = subprocess.run(
            ["winget", "install", "--id", pkg_id, "-e", "--source", source,
             "--silent", "--disable-interactivity",
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=900,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return proc.returncode == 0
    except Exception:
        return False


# ===================== BORDERLESS FULLSCREEN (apps externos) =====================
# Forca a janela do app aberto a tela cheia sem bordas (modo big picture).
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_EX_DLGMODALFRAME = 0x00000001
WS_EX_WINDOWEDGE = 0x00000100
WS_EX_CLIENTEDGE = 0x00000200
WS_EX_STATICEDGE = 0x00020000
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

try:
    _user32 = ctypes.windll.user32
    _EnumWindows = _user32.EnumWindows
    _EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p),
                             ctypes.c_void_p]
    _EnumWindows.restype = ctypes.c_bool
    _IsWindowVisible = _user32.IsWindowVisible
    _IsWindowVisible.argtypes = [ctypes.c_void_p]
    _IsWindowVisible.restype = ctypes.c_bool
    _GetWindowTextW = _user32.GetWindowTextW
    _GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    _GetWindowTextW.restype = ctypes.c_int
    _GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
    _GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    _GetWindowThreadProcessId.restype = ctypes.c_ulong
    _GetWindowLongPtrW = _user32.GetWindowLongPtrW
    _GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _GetWindowLongPtrW.restype = ctypes.c_void_p
    _SetWindowLongPtrW = _user32.SetWindowLongPtrW
    _SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    _SetWindowLongPtrW.restype = ctypes.c_void_p
    _SetWindowPos = _user32.SetWindowPos
    _SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    _SetWindowPos.restype = ctypes.c_bool
    _GetForegroundWindow = _user32.GetForegroundWindow
    _GetForegroundWindow.restype = ctypes.c_void_p
    _IsWindow = _user32.IsWindow
    _IsWindow.argtypes = [ctypes.c_void_p]
    _IsWindow.restype = ctypes.c_bool
    _MonitorFromWindow = _user32.MonitorFromWindow
    _MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    _MonitorFromWindow.restype = ctypes.c_void_p
    _GetMonitorInfoW = _user32.GetMonitorInfoW
    _WIN32_OK = True
except Exception:
    _WIN32_OK = False


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", _RECT),
                ("rcWork", _RECT), ("dwFlags", ctypes.c_ulong)]


def _top_level_windows():
    """[(hwnd, pid, titulo)] das janelas visiveis de outros processos."""
    out = []
    if not _WIN32_OK:
        return out
    try:
        mine = os.getpid()

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(hwnd, _lparam):
            try:
                if not _IsWindowVisible(hwnd):
                    return True
                buf = ctypes.create_unicode_buffer(256)
                if _GetWindowTextW(hwnd, buf, 256) <= 0:
                    return True
                pid = ctypes.c_ulong()
                _GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != mine:
                    out.append((hwnd, pid.value, buf.value))
            except Exception:
                pass
            return True

        _EnumWindows(_cb, None)
    except Exception:
        pass
    return out


def _monitor_rect(hwnd=None):
    """Retangulo do monitor (x, y, w, h). Cai para a tela primaria."""
    if _WIN32_OK and hwnd:
        try:
            mon = _MonitorFromWindow(hwnd, 1)
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if _GetMonitorInfoW(mon, ctypes.byref(mi)):
                r = mi.rcMonitor
                return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        except Exception:
            pass
    try:
        g = ctypes.windll.user32.GetSystemMetrics
        return (0, 0, g(0), g(1))
    except Exception:
        return (0, 0, 1920, 1080)


def force_borderless_fullscreen(hwnd, monitor_hwnd=None):
    """Tira bordas e estica a janela p/ tela cheia. Best-effort por app."""
    if not _WIN32_OK or not hwnd:
        return False
    try:
        style = _GetWindowLongPtrW(hwnd, GWL_STYLE)
        style = int(style) & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        _SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        exstyle = _GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        exstyle = int(exstyle) & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE
                                   | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE)
        _SetWindowLongPtrW(hwnd, GWL_EXSTYLE, exstyle)
        x, y, w, h = _monitor_rect(monitor_hwnd)
        return bool(_SetWindowPos(hwnd, None, x, y, w, h,
                                  SWP_FRAMECHANGED | SWP_SHOWWINDOW))
    except Exception:
        return False


def _hwnd_alive(hwnd):
    try:
        return bool(_WIN32_OK and hwnd and _IsWindow(hwnd))
    except Exception:
        return False


def bring_to_front(hwnd):
    try:
        if _WIN32_OK and hwnd:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def _set_cursor_pos(x, y):
    try:
        if _WIN32_OK:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            return True
    except Exception:
        pass
    return False


def foreground_hwnd():
    try:
        if _WIN32_OK:
            return _GetForegroundWindow()
    except Exception:
        pass
    return None


# ===================== FOCUS MANAGER =====================
class FocusManager:
    def __init__(self):
        self.focused_row = 0
        self.focused_col = 0

    def reset(self):
        self.focused_row = 0
        self.focused_col = 0


# ===================== VIRTUAL INPUT (SendInput) =====================
# Traduz o controle em teclado/mouse virtuais para comandar o app aberto.
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
WHEEL_DELTA = 120

VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_F = 0x46
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_BACK = 0x08
VK_VOL_DOWN = 0xAE
VK_VOL_UP = 0xAF


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT_UNION)]


_SendInput = ctypes.windll.user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint


def tap_key(vk):
    for flags in (0, KEYEVENTF_KEYUP):
        inp = _INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ii.ki = _KEYBDINPUT(vk, 0, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def key_down(vk):
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ii.ki = _KEYBDINPUT(vk, 0, 0, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def key_up(vk):
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ii.ki = _KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def type_text(root, text):
    """Tecla texto de verdade na janela em foco (teclado virtual global).
    Letras/numeros vao por VK; simbolos via Ctrl+V (a prova de layout ABNT)."""
    for ch in text:
        try:
            if "a" <= ch <= "z" or "A" <= ch <= "Z":
                upper = ch.isupper()
                if upper:
                    key_down(VK_SHIFT)
                tap_key(ord(ch.upper()))
                if upper:
                    key_up(VK_SHIFT)
            elif "0" <= ch <= "9":
                tap_key(ord(ch))
            elif ch == " ":
                tap_key(VK_SPACE)
            elif ch == "\n":
                tap_key(VK_RETURN)
            else:
                root.clipboard_clear()
                root.clipboard_append(ch)
                root.update_idletasks()
                key_down(VK_CONTROL)
                tap_key(0x56)  # V
                key_up(VK_CONTROL)
                time.sleep(0.02)
        except Exception:
            pass


def mouse_move(dx, dy):
    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.ii.mi = _MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def mouse_click(right=False):
    down, up = ((MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP) if right
                else (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP))
    for flags in (down, up):
        inp = _INPUT()
        inp.type = INPUT_MOUSE
        inp.ii.mi = _MOUSEINPUT(0, 0, 0, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def mouse_wheel(v_notches=0, h_notches=0):
    """Rolagem: v>0 sobe, h>0 para a direita (em encaixes de 120)."""
    for flags, n in ((MOUSEEVENTF_WHEEL, int(v_notches)),
                     (MOUSEEVENTF_HWHEEL, int(h_notches))):
        if not n:
            continue
        inp = _INPUT()
        inp.type = INPUT_MOUSE
        inp.ii.mi = _MOUSEINPUT(0, 0, n * WHEEL_DELTA, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def stick_response(v, deadzone=0.22):
    """Resposta linear a partir da zona morta: reage na hora, sem rampa lenta."""
    a = abs(v)
    if a < deadzone:
        return 0.0
    return (1.0 if v > 0 else -1.0) * (a - deadzone) / (1.0 - deadzone)


# Processos para detectar que o app foi fechado (saida automatica do remoto).
# So nomes confiaveis: se o processo nunca aparecer, nao ha saida automatica
# (o usuario sai com Back+Start).
REMOTE_WATCH = {
    "Netflix": ["netflix.exe"],
    "Spotify": ["spotify.exe"],
    "Kodi": ["kodi.exe"],
    "Plex": ["plex.exe", "plexhtpc.exe"],
    "Jellyfin": ["jellyfinmediaplayer.exe"],
    "Deezer": ["deezer.exe"],
    "Tidal": ["tidal.exe"],
}

# Navegadores observados quando o remoto abre via opcao Site
BROWSER_WATCH = ["chrome.exe", "msedge.exe", "firefox.exe", "opera.exe",
                 "opera_gx.exe", "brave.exe", "vivaldi.exe"]


# ===================== PAD MAPPING =====================
# Botoes LOGICOS (posicao fisica, padrao SDL): south = botao de baixo,
# east = direita, west = esquerda, north = cima. Valem para Xbox,
# PlayStation, Switch e genericos — o indice fisico (raw) de cada controle
# e resolvido por controle via SDL (pygame._sdl2.controller).
LOGICAL_BUTTONS = ("south", "east", "west", "north", "lb", "rb",
                   "back", "start", "guide", "l3", "r3")

# Tabela raw padrao (Xbox / ordem classica). Indices salvos antigos usam ela.
XBOX_RAW = {"south": 0, "east": 1, "west": 2, "north": 3, "lb": 4,
            "rb": 5, "back": 6, "start": 7, "l3": 8, "r3": 9}
XBOX_POSITIONAL = {v: k for k, v in XBOX_RAW.items()}

# Nomes por layout (mesma posicao fisica, nome de cada familia).
PAD_LAYOUT_NAMES = {
    "xbox": {"south": "A", "east": "B", "west": "X", "north": "Y",
             "lb": "LB", "rb": "RB", "back": "Back", "start": "Start",
             "guide": "Guide", "l3": "L3", "r3": "R3"},
    "playstation": {"south": "\u2715", "east": "\u25CB", "west": "\u25A1",
                    "north": "\u25B3", "lb": "L1", "rb": "R1",
                    "back": "Share", "start": "Options", "guide": "PS",
                    "l3": "L3", "r3": "R3"},
    "switch": {"south": "B", "east": "A", "west": "Y", "north": "X",
               "lb": "L", "rb": "R", "back": "-", "start": "+",
               "guide": "Home", "l3": "L3", "r3": "R3"},
    "generic": {},
}
PAD_LAYOUT_LABEL = {"xbox": "Xbox", "playstation": "PlayStation",
                    "switch": "Switch", "generic": "Gen\u00E9rico"}


def detect_pad_layout(name):
    """Identifica a familia do controle pelo nome (Xbox/PlayStation/Switch)."""
    n = (name or "").lower()
    ps_keys = ("dualshock", "dualsense", "dual shock", "playstation",
               "wireless controller", "sony")
    if any(k in n for k in ("xbox", "xinput", "microsoft")):
        return "xbox"
    if any(k in n for k in ps_keys) or re.search(r"\bps[345]\b", n):
        return "playstation"
    if any(k in n for k in ("switch", "joy-con", "joycon", "pro controller")):
        return "switch"
    return "generic"


def normalize_pad_value(value):
    """Valor salvo (indice antigo ou logico novo) -> nome logico."""
    if isinstance(value, str):
        if value in LOGICAL_BUTTONS:
            return value
        if value.startswith("raw"):
            return value
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value in XBOX_POSITIONAL:
            return XBOX_POSITIONAL[value]
        return "raw%d" % value
    return "raw?"


def parse_sdl_mapping(mapping):
    """Dict do SDL (ex. {'a': 'b0', 'dpup': 'h0.1'}) -> {logico: raw}."""
    out = {}
    try:
        items = mapping.items() if hasattr(mapping, "items") else []
    except Exception:
        return out
    sdl_to_logical = {"a": "south", "b": "east", "x": "west", "y": "north",
                      "back": "back", "guide": "guide", "start": "start",
                      "leftstick": "l3", "rightstick": "r3",
                      "leftshoulder": "lb", "rightshoulder": "rb"}
    for sdl_key, target in items:
        logical = sdl_to_logical.get(str(sdl_key).lower())
        if logical is None or not isinstance(target, str):
            continue
        m = re.match(r"b(\d+)$", target.strip().lower())
        if m:
            out[logical] = int(m.group(1))
    return out

# Acao -> botao. Usuario pode trocar em Configuracoes > Gamepad.
DEFAULT_NEXUS_MAP = {"select": 0, "back": 1, "cards": 2,
                     "sidebar": 3, "tab_prev": 4, "tab_next": 5}
DEFAULT_REMOTE_MAP = {"click_left": 0, "back": 1, "click_right": 2,
                      "fullscreen": 3, "vol_down": 4, "vol_up": 5,
                      "space": 8, "enter": 9}
NEXUS_ACTION_ORDER = ["select", "back", "cards", "sidebar", "tab_prev", "tab_next"]
REMOTE_ACTION_ORDER = ["click_left", "click_right", "enter", "back",
                       "space", "fullscreen", "vol_down", "vol_up"]
DEFAULT_PAD_SENSITIVITY = 12
DEFAULT_PAD_SCROLL = 8


def invert_map(m):
    return {v: k for k, v in m.items() if isinstance(v, int)}


def pad_logical_label(logical, layout="xbox", raw=None):
    """Nome do botao na familia do controle ativo (A vs. X vs. B...)."""
    name = PAD_LAYOUT_NAMES.get(layout, {}).get(logical)
    if name:
        return name
    if raw is not None:
        return "B%d" % raw
    return str(logical)


def pad_button_name(btn_id, layout="xbox"):
    logical = normalize_pad_value(btn_id)
    raw = btn_id if isinstance(btn_id, int) else XBOX_RAW.get(logical)
    return pad_logical_label(logical, layout, raw)


# ===================== GAMEPAD =====================
class GamepadManager:
    def __init__(self, app):
        self.app = app
        self.joystick = None
        self.controller = None  # pygame._sdl2.controller (mapeamento SDL)
        self.devices = []  # [{index, name, guid, layout}]
        self.active_index = 0
        self.logical_to_raw = dict(XBOX_RAW)
        self.raw_to_logical = {v: k for k, v in XBOX_RAW.items()}
        self.dpad_sources = []  # [('hat', idx) ou ('btn', (r...))] do D-pad
        self.running = False
        self.prev_buttons = {}
        self.prev_logical = {}
        self.hat_prev = (0, 0)
        self.hat_debounce = {}
        self.stick_nav_dir = (0, 0)
        self.stick_nav_next = 0.0
        self._poll_ticks = 0
        self._last_count = -1
        # Modo remoto: controle comanda o app aberto em vez do Nexus
        self.remote_active = False
        self.remote_service = None
        self.remote_wheel_acc = [0.0, 0.0]
        self.remote_watch_seen = False
        self.remote_watch_missed = 0
        self.remote_watch_count = 0
        self.remote_watch_list = []
        self.remote_hwnd = None
        self.remote_enter_time = 0.0
        self.remote_off = [0.0, 0.0, 0.0, 0.0]
        self.remote_cal = []
        if PYGAME_AVAILABLE:
            try:
                pygame.init()
                pygame.joystick.init()
                self.running = True
                self.refresh_devices()
                self.app.root.after(50, self.poll)
            except:
                pass

    # ---------- dispositivos ----------
    def refresh_devices(self):
        """Re-enumera controles (hot-plug). Mantem o escolhido ou o salvo."""
        lst = []
        try:
            for i in range(pygame.joystick.get_count()):
                try:
                    js = pygame.joystick.Joystick(i)
                    name = js.get_name()
                except Exception:
                    continue
                try:
                    guid = js.get_guid()
                except Exception:
                    guid = ""
                lst.append({"index": i, "name": name or "Controle %d" % (i + 1),
                            "guid": guid or "",
                            "layout": detect_pad_layout(name)})
        except Exception:
            pass
        self.devices = lst
        want_guid = ""
        try:
            want_guid = self.app.settings.get("pad_device_guid", "") or ""
        except Exception:
            pass
        pick = 0
        if want_guid:
            for pos, d in enumerate(lst):
                if d["guid"] == want_guid:
                    pick = pos
                    break
        if self.joystick is not None:
            try:
                cur_name = self.joystick.get_name()
                for pos, d in enumerate(lst):
                    if d["name"] == cur_name and (not want_guid or d["guid"] == want_guid):
                        pick = pos
                        break
            except Exception:
                pass
        if lst:
            self.attach(lst[min(pick, len(lst) - 1)]["index"])
        else:
            self._detach()

    def _detach(self):
        try:
            if self.joystick is not None:
                self.joystick.quit()
        except Exception:
            pass
        self.joystick = None
        self.controller = None
        self.logical_to_raw = dict(XBOX_RAW)
        self.raw_to_logical = {v: k for k, v in XBOX_RAW.items()}
        self.dpad_sources = []
        self.prev_buttons = {}
        self.prev_logical = {}

    def attach(self, index):
        """Troca para o controle `index` (indice pygame)."""
        self._detach()
        try:
            js = pygame.joystick.Joystick(index)
            js.init()
        except Exception:
            return False
        self.joystick = js
        self.active_index = index
        table = parse_sdl_mapping(self._sdl_mapping(js))
        if table:
            self.logical_to_raw = table
            self.raw_to_logical = {v: k for k, v in table.items()}
        self.dpad_sources = self._dpad_sources(js)
        self.prev_buttons = {}
        self.prev_logical = {}
        self.remote_cal = []
        self.remote_off = [0.0, 0.0, 0.0, 0.0]
        return True

    @staticmethod
    def _sdl_mapping(js):
        try:
            from pygame._sdl2 import controller as _ctl
            try:
                _ctl.init()  # subsistema gamecontroller (pygame.init nao cobre)
            except Exception:
                pass
            ctl = _ctl.Controller.from_joystick(js)
            return ctl.get_mapping()
        except Exception:
            return {}

    def _dpad_sources(self, js):
        """De onde ler o D-pad: botoes ou hat (varia por controle)."""
        try:
            from pygame._sdl2 import controller as _ctl
            try:
                _ctl.init()
            except Exception:
                pass
            ctl = _ctl.Controller.from_joystick(js)
            mapping = ctl.get_mapping() or {}
            btns = {}
            hat = None
            for key in ("dpup", "dpdown", "dpleft", "dpright"):
                tgt = str(mapping.get(key, "")).strip().lower()
                m = re.match(r"b(\d+)$", tgt)
                if m:
                    btns[key] = int(m.group(1))
                    continue
                m = re.match(r"h(\d+)\.(\d+)$", tgt)
                if m:
                    hat = int(m.group(1))
            if len(btns) == 4:
                return [("btn", (btns["dpleft"], btns["dpright"],
                                 btns["dpup"], btns["dpdown"]))]
            if hat is not None:
                return [("hat", hat)]
        except Exception:
            pass
        return [("hat", 0)]

    def select_device(self, pos):
        """Escolhe o controle pela posicao na lista. Persiste por GUID."""
        if not self.devices or pos < 0 or pos >= len(self.devices):
            return False
        d = self.devices[pos]
        if not self.attach(d["index"]):
            return False
        try:
            self.app.settings["pad_device_guid"] = d["guid"]
            save_settings(self.app.settings)
        except Exception:
            pass
        return True

    @property
    def layout(self):
        if not self.devices:
            return "xbox"
        for d in self.devices:
            try:
                if self.joystick is not None and d["name"] == self.joystick.get_name():
                    return d["layout"]
            except Exception:
                pass
        return self.devices[0]["layout"] if self.devices else "xbox"

    def device_label(self):
        if self.joystick is None or not self.devices:
            return ""
        try:
            name = self.joystick.get_name()
        except Exception:
            return ""
        tag = PAD_LAYOUT_LABEL.get(self.layout, "")
        return "%s (%s)" % (name, tag) if tag else name

    def connection_info(self):
        """'Cabo' se o pygame reporta wired; senao nivel de bateria."""
        if self.joystick is None:
            return ""
        try:
            power = self.joystick.get_power_level()
        except Exception:
            return ""
        mapping = {"wired": "pad_conn_wired", "empty": "pad_batt_empty",
                   "low": "pad_batt_low", "medium": "pad_batt_mid",
                   "full": "pad_batt_full", "max": "pad_batt_full"}
        key = mapping.get(str(power).lower())
        if not key:
            return ""
        try:
            return t(key, self.app.lang)
        except Exception:
            return ""

    # ---------- leitura logica ----------
    def logical_for_raw(self, raw):
        return self.raw_to_logical.get(raw, "raw%d" % raw)

    def raw_for_logical(self, logical):
        if logical in self.logical_to_raw:
            return self.logical_to_raw[logical]
        m = re.match(r"raw(\d+)$", str(logical))
        if m:
            return int(m.group(1))
        return XBOX_RAW.get(logical)

    def _pressed_raw(self):
        """Conjunto de indices raw pressionados (qualquer controle)."""
        out = set()
        js = self.joystick
        if js is None:
            return out
        try:
            n = js.get_numbuttons()
        except Exception:
            return out
        for i in range(n):
            try:
                if js.get_button(i):
                    out.add(i)
            except Exception:
                pass
        return out

    def pressed_logical(self):
        return {self.logical_for_raw(i) for i in self._pressed_raw()}

    def read_dpad(self):
        """D-pad como (x, y): funciona via hat ou via botoes."""
        js = self.joystick
        if js is None:
            return (0, 0)
        for kind, ref in self.dpad_sources or [("hat", 0)]:
            try:
                if kind == "hat":
                    if js.get_numhats() > ref:
                        h = js.get_hat(ref)
                        if h != (0, 0):
                            return (h[0], h[1])
                else:
                    left, right, up, down = ref
                    x = (1 if js.get_button(right) else 0) - (1 if js.get_button(left) else 0)
                    y = (1 if js.get_button(up) else 0) - (1 if js.get_button(down) else 0)
                    if x or y:
                        return (x, y)
            except Exception:
                pass
        return (0, 0)

    def _maybe_hotplug(self):
        try:
            count = pygame.joystick.get_count()
        except Exception:
            return
        if count != self._last_count:
            self._last_count = count
            try:
                alive = self.joystick is not None and self.joystick.get_init()
            except Exception:
                alive = False
            if count == 0 or not alive:
                self.refresh_devices()
                try:
                    if (self.app.pad_window is not None
                            and not self.app.pad_window.closed):
                        self.app.pad_window.refresh_device_bar()
                except Exception:
                    pass

    def _stick_axes(self):
        """Eixos (lx, ly, rx, ry) com seguranca para qualquer controle."""
        js = self.joystick
        if js is None:
            return 0.0, 0.0, 0.0, 0.0
        try:
            na = js.get_numaxes()
            lx = js.get_axis(0) if na > 0 else 0.0
            ly = js.get_axis(1) if na > 1 else 0.0
            if na >= 4:
                rx, ry = js.get_axis(2), js.get_axis(3)
            else:
                rx = ry = 0.0
        except Exception:
            lx = ly = rx = ry = 0.0
        return lx, ly, rx, ry

    def _menu_deadzone(self):
        try:
            return max(0.45, float(self.app.pad_deadzone()))
        except Exception:
            return 0.45

    def _stick_nav_dir(self):
        """Direcao do analogico esquerdo p/ navegar nos menus (ou (0,0))."""
        lx, ly, _rx, _ry = self._stick_axes()
        dz = self._menu_deadzone()
        if abs(lx) < dz and abs(ly) < dz:
            return (0, 0)
        if abs(lx) >= abs(ly):
            return (1 if lx > 0 else -1, 0)
        return (0, -1 if ly > 0 else 1)

    def _stick_nav_action(self, ndir):
        """Mesmos alvos do D-pad: dialogos, janela de controles e cards."""
        top = top_modal(self.app)
        if isinstance(top, OpenTargetDialog):
            top.move()
        elif isinstance(top, NexusMenuWindow):
            top.on_hat(ndir)
        elif isinstance(top, NexusKeyboard):
            top.on_hat(ndir)
        elif isinstance(top, NexusTextDialog):
            pass
        else:
            pw = self.app.pad_window
            if (pw is not None and not pw.closed
                    and self.app.pad_capture is None):
                if ndir == (0, 1):
                    pw.move_focus(-1)
                elif ndir == (0, -1):
                    pw.move_focus(1)
                else:
                    pw.sens_or_move(ndir)
            elif ndir == (0, 1):
                self.app._nav("up")
                self.app.warp_to_focus()
            elif ndir == (0, -1):
                self.app._nav("down")
                self.app.warp_to_focus()
            elif ndir == (-1, 0):
                self.app._nav("left")
                self.app.warp_to_focus()
            elif ndir == (1, 0):
                self.app._nav("right")
                self.app.warp_to_focus()

    def _poll_menu_sticks(self):
        """Analogicos nos menus: esquerdo navega (com repeticao),
        direito move o mouse como no modo remoto."""
        try:
            dz = float(self.app.pad_deadzone())
        except Exception:
            dz = 0.22
        lx, ly, rx, ry = self._stick_axes()
        now = time.time()
        ndir = (0, 0)
        if abs(lx) >= self._menu_deadzone() or abs(ly) >= self._menu_deadzone():
            if abs(lx) >= abs(ly):
                ndir = (1 if lx > 0 else -1, 0)
            else:
                ndir = (0, -1 if ly > 0 else 1)
        if ndir != (0, 0):
            if ndir != self.stick_nav_dir:
                self.stick_nav_dir = ndir
                self.stick_nav_next = now
            if now >= self.stick_nav_next:
                self.stick_nav_next = now + 0.22
                self._stick_nav_action(ndir)
        else:
            self.stick_nav_dir = (0, 0)
        nx = stick_response(rx, deadzone=dz)
        ny = stick_response(ry, deadzone=dz)
        if nx != 0.0 or ny != 0.0:
            try:
                sens = float(self.app.pad_sensitivity())
            except Exception:
                sens = float(DEFAULT_PAD_SENSITIVITY)
            mouse_move(sens * nx, sens * ny)

    def poll(self):
        if not self.running:
            return
        try:
            self._poll_ticks += 1
            for ev in pygame.event.get():
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._maybe_hotplug()
                    break
            if self._poll_ticks % 60 == 0:
                self._maybe_hotplug()
        except Exception:
            pass
        if not self.joystick:
            self.app.root.after(500, self.poll)
            return
        if self.remote_active:
            self._poll_remote()
            self.app.root.after(16, self.poll)
            return
        try:
            hat = self.read_dpad()
            now = time.time()
            if hat != (0, 0):
                if hat not in self.hat_debounce or (now - self.hat_debounce[hat]) > 0.15:
                    self.hat_debounce[hat] = now
                    top = top_modal(self.app)
                    if isinstance(top, OpenTargetDialog):
                        top.move()
                    elif isinstance(top, NexusMenuWindow):
                        top.on_hat(hat)
                    elif isinstance(top, NexusKeyboard):
                        top.on_hat(hat)
                    elif isinstance(top, NexusTextDialog):
                        pass
                    else:
                        pw = self.app.pad_window
                        if (pw is not None and not pw.closed
                                and self.app.pad_capture is None):
                            if hat == (0, 1):
                                pw.move_focus(-1)
                            elif hat == (0, -1):
                                pw.move_focus(1)
                            else:
                                pw.sens_or_move(hat)
                        elif hat == (0, 1):
                            self.app._nav("up")
                            self.app.warp_to_focus()
                        elif hat == (0, -1):
                            self.app._nav("down")
                            self.app.warp_to_focus()
                        elif hat == (-1, 0):
                            self.app._nav("left")
                            self.app.warp_to_focus()
                        elif hat == (1, 0):
                            self.app._nav("right")
                            self.app.warp_to_focus()
            else:
                self.hat_debounce.clear()

            self._poll_menu_sticks()

            pressed = self._pressed_raw()
            for old_id in list(self.prev_buttons):
                if old_id not in pressed:
                    self.prev_buttons[old_id] = False
            for btn_id in sorted(pressed):
                if self.prev_buttons.get(btn_id, False):
                    continue
                self.prev_buttons[btn_id] = True
                logical = self.logical_for_raw(btn_id)
                is_confirm = (logical == "south")
                is_cancel = (logical == "east")
                top = top_modal(self.app)
                if isinstance(top, OpenTargetDialog):
                    if is_confirm:
                        top.confirm()
                    elif is_cancel:
                        top.cancel()
                elif isinstance(top, (NexusMenuWindow, NexusTextDialog)):
                    if is_confirm:
                        top.confirm()
                    elif is_cancel:
                        top.close()
                elif isinstance(top, NexusKeyboard):
                    if is_confirm:
                        top.press_focused()
                    elif is_cancel:
                        top.close()
                elif self.app.pad_capture is not None:
                    if is_cancel:
                        self.app.cancel_pad_capture()
                    else:
                        self.app.finish_pad_capture(logical)
                else:
                    pw = self.app.pad_window
                    if pw is not None and not pw.closed:
                        if is_confirm:
                            pw.activate_focused()
                        elif is_cancel:
                            pw.close()
                    else:
                        action = self.app.nexus_action_for(logical)
                        if action == "select":
                            self.app.select_current()
                        elif action == "back":
                            self.app.go_back()
                        elif action == "cards":
                            self.app.go_to_cards()
                        elif action == "sidebar":
                            self.app.toggle_sidebar()
                        elif action == "tab_prev":
                            self.app.tab_prev()
                        elif action == "tab_next":
                            self.app.tab_next()
        except:
            pass
        self.app.root.after(16, self.poll)

    def _poll_remote(self):
        """Controle vira controle remoto do app em foco (teclado/mouse virtual)."""
        js = self.joystick
        try:
            for ev in pygame.event.get():
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._maybe_hotplug()
                    break
            hat = self.read_dpad()
            now = time.time()
            if hat != (0, 0):
                if hat not in self.hat_debounce or (now - self.hat_debounce[hat]) > 0.15:
                    self.hat_debounce[hat] = now
                    if hat == (0, 1):
                        tap_key(VK_UP)
                    elif hat == (0, -1):
                        tap_key(VK_DOWN)
                    elif hat == (-1, 0):
                        tap_key(VK_LEFT)
                    elif hat == (1, 0):
                        tap_key(VK_RIGHT)
            else:
                self.hat_debounce.clear()

            try:
                na = js.get_numaxes()
                lx = js.get_axis(0) if na > 0 else 0.0
                ly = js.get_axis(1) if na > 1 else 0.0
                # Analógico direito = eixos 2,3. Eixos 4,5 (quando existem)
                # sao os GATILHOS (repouso em -1): ler eles puxa o mouse p/ cima.
                if na >= 4:
                    rx, ry = js.get_axis(2), js.get_axis(3)
                else:
                    rx = ry = 0.0
            except Exception:
                lx = ly = rx = ry = 0.0
            # Calibracao: media do repouso nas primeiras leituras estaveis
            if self.remote_cal is not None:
                self.remote_cal.append((lx, ly, rx, ry))
                if len(self.remote_cal) >= 8:
                    ok = True
                    off = []
                    for i in range(4):
                        vals = [s[i] for s in self.remote_cal]
                        if max(vals) - min(vals) > 0.3:
                            ok = False
                        off.append(sum(vals) / len(vals))
                    if ok or len(self.remote_cal) >= 40:
                        self.remote_off = off
                        self.remote_cal = None
                lx = ly = rx = ry = 0.0
            else:
                lx -= self.remote_off[0]
                ly -= self.remote_off[1]
                rx -= self.remote_off[2]
                ry -= self.remote_off[3]
            self._remote_stick_scroll(lx, ly)
            self._remote_stick_mouse(rx, ry)

            # Back + Start juntos = sair do modo remoto (logico: vale p/
            # Xbox, PlayStation, Switch e genericos). Fixo, antes de tudo.
            try:
                pressed_now = self._pressed_raw()
                back_raw = self.raw_for_logical("back")
                start_raw = self.raw_for_logical("start")
                if (back_raw is not None and start_raw is not None
                        and back_raw in pressed_now and start_raw in pressed_now):
                    for i in (back_raw, start_raw):
                        self.prev_buttons[i] = True
                    self.app.exit_remote_mode()
                    return
            except Exception:
                pass

            for btn_id in list(self.prev_buttons):
                if btn_id not in pressed_now:
                    self.prev_buttons[btn_id] = False
            for btn_id in sorted(pressed_now):
                if self.prev_buttons.get(btn_id, False):
                    continue
                self.prev_buttons[btn_id] = True
                logical = self.logical_for_raw(btn_id)
                top = top_modal(self.app)
                if isinstance(top, NexusKeyboard):
                    if logical == "south":
                        top.press_focused()
                    elif logical == "east":
                        top.close()
                elif self.app.pad_capture is not None:
                    if logical == "east":
                        self.app.cancel_pad_capture()
                    else:
                        self.app.finish_pad_capture(logical)
                else:
                    action = self.app.remote_action_for(logical)
                    if action == "click_left":
                        if self.app.browser_nav_active():
                            tap_key(VK_RETURN)  # modo console: A abre o quadro
                        else:
                            mouse_click(right=False)
                    elif action == "click_right":
                        mouse_click(right=True)
                    elif action == "enter":
                        tap_key(VK_RETURN)
                    elif action == "back":
                        tap_key(VK_ESCAPE)
                    elif action == "space":
                        tap_key(VK_SPACE)
                    elif action == "fullscreen":
                        tap_key(VK_F)
                    elif action == "vol_down":
                        tap_key(VK_VOL_DOWN)
                    elif action == "vol_up":
                        tap_key(VK_VOL_UP)
            self._remote_watch_tick()
        except Exception:
            pass

    def _remote_stick_scroll(self, x, y):
        """Analogico esquerdo = rolagem da pagina (vertical + horizontal)."""
        try:
            dz = self.app.pad_deadzone()
        except Exception:
            dz = 0.22
        nx = stick_response(x, deadzone=dz)
        ny = stick_response(y, deadzone=dz)
        if nx == 0.0 and ny == 0.0:
            return
        try:
            rate = self.app.pad_scroll()
        except Exception:
            rate = float(DEFAULT_PAD_SCROLL)
        step = rate * 0.016  # ~16ms por poll
        self.remote_wheel_acc[0] += nx * step
        self.remote_wheel_acc[1] += -ny * step  # cima = rolar p/ cima
        for i, is_vert in ((0, False), (1, True)):
            n = int(self.remote_wheel_acc[i])
            if n:
                self.remote_wheel_acc[i] -= n
                if is_vert:
                    mouse_wheel(v_notches=n)
                else:
                    mouse_wheel(h_notches=n)

    def _remote_stick_mouse(self, x, y):
        try:
            dz = self.app.pad_deadzone()
        except Exception:
            dz = 0.22
        nx = stick_response(x, deadzone=dz)
        ny = stick_response(y, deadzone=dz)
        if nx == 0.0 and ny == 0.0:
            return
        try:
            sens = self.app.pad_sensitivity()
        except Exception:
            sens = float(DEFAULT_PAD_SENSITIVITY)
        mouse_move(sens * nx, sens * ny)

    def _remote_watch_tick(self):
        # Caminho rapido: janela do app rastreada (IsWindow e barato).
        # Fecha -> volta ao Nexus em ~0,5s em vez de ~6s do tasklist.
        hwnd = getattr(self, "remote_hwnd", None)
        if hwnd:
            self.remote_watch_count += 1
            if self.remote_watch_count < 15:  # ~250ms
                return
            self.remote_watch_count = 0
            if _hwnd_alive(hwnd):
                self.remote_watch_seen = True
                self.remote_watch_missed = 0
                return
            self.remote_watch_missed += 1
            if self.remote_watch_seen and self.remote_watch_missed >= 2:
                self.app.exit_remote_mode()
            elif self.remote_watch_missed >= 8:
                self.remote_hwnd = None  # janela sumiu: volta ao tasklist
            return
        exes = getattr(self, "remote_watch_list", None)
        if exes is None:
            exes = REMOTE_WATCH.get(self.remote_service or "", [])
        if not exes:
            return
        self.remote_watch_count += 1
        if self.remote_watch_count < 45:  # ~0,75s
            return
        self.remote_watch_count = 0
        alive = any(self._process_alive(exe) for exe in exes)
        if alive:
            self.remote_watch_seen = True
            self.remote_watch_missed = 0
        elif self.remote_watch_seen:
            self.remote_watch_missed += 1
            if self.remote_watch_missed >= 2:
                self.app.exit_remote_mode()

    @staticmethod
    def _process_alive(exe_name):
        try:
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW)
            want = exe_name.lower()
            for line in (out.stdout or "").splitlines():
                if line.split('","')[0].strip('"').lower() == want:
                    return True
        except Exception:
            pass
        return False

    def stop(self):
        self.running = False
        if PYGAME_AVAILABLE:
            try:
                pygame.quit()
            except:
                pass


# ===================== TRANSLATIONS =====================
TRANSLATIONS = {
    "pt-br": {
        "app_title": "Nexus - Big Picture",
        "tab_home": "Home",
        "tab_favorites": "Favoritos",
        "tab_movies": "Filmes",
        "tab_music": "Musica",
        "tab_videos": "Videos",
        "tab_all": "Todos",
        "sidebar_history": "Historico",
        "sidebar_favorites": "Favoritos",
        "sidebar_settings": "Configuracoes",
        "sidebar_add": "Adicionar",
        "sidebar_close": "Fechar",
        "settings_theme": "Trocar Tema",
        "settings_resolution": "Resolucao",
        "settings_gamepad": "Controles",
        "settings_language": "Idioma",
        "settings_clear_cache": "Limpar logins e cache",
        "cache_confirm": "Apagar logins, cookies e senhas salvos no navegador do Nexus? (%.1f MB)",
        "cache_clear_yes": "Apagar tudo",
        "cache_cleared": "Logins, cookies e cache apagados.",
        "cache_in_use": "Feche o navegador do Nexus antes de limpar.",
        "sidebar_keyboard": "Teclado virtual",
        "kb_title": "Teclado",
        "kb_hint": "Analogico/setas movem \u2022 confirmar tecla \u2022 B fecha",
        "kb_space": "espaco",
        "kb_ok": "OK",
        "settings_title": "Configuracoes",
        "theme_title": "Cor de Destaque",
        "theme_close": "Fechar",
        "res_title": "Resolucao",
        "res_fullscreen": "Tela Cheia",
        "res_windowed": "Janela (1200x800)",
        "res_close": "Fechar",
        "gamepad_connected": "Conectado",
        "gamepad_none": "Nenhum gamepad detectado",
        "gamepad_info": "Conecte um controle USB/Bluetooth e reinicie o app.",
        "gamepad_controls": "\n\nA: Selecionar | B: Voltar\nD-Pad: Navegar\nStart: Menu | LB/RB: Abas\n\nNo app/site (remoto):\nSetas: navegar | A: clique esq. | B: Voltar\nX: clique dir. | Y: Tela cheia | LB/RB: Volume\nAnalogico dir.: mouse | R3: Enter | L3: Espaco\nAnalogico esq.: rolagem\nBack+Start: sair do remoto",
        "lang_title": "Idioma",
        "lang_portuguese": "Portugues (BR)",
        "lang_english": "English",
        "lang_close": "Fechar",
        "history_title": "Historico",
        "history_empty": "Nenhum historico ainda",
        "add_title": "Adicionar Streaming",
        "add_name": "Nome:",
        "add_url": "URL:",
        "add_category": "Categoria:",
        "add_emoji": "Emoji:",
        "add_logo": "Logo:",
        "add_submit": "Adicionar",
        "add_back": "Voltar",
        "add_warning": "Nome e URL sao obrigatorios!",
        "add_success": "adicionado!",
        "ctx_open": "Abrir",
        "ctx_remove_fav": "Remover Favorito",
        "ctx_add_fav": "Adicionar Favorito",
        "ctx_change_logo": "Trocar Logo",
        "ctx_delete": "Excluir",
        "ctx_copy_url": "Copiar URL",
        "dlg_how": "Como deseja abrir?",
        "dlg_site": "\U0001F310 Site",
        "dlg_app": "\U0001F4F1 App",
        "dlg_searching": "\U0001F50D Procurando app instalado...",
        "dlg_hint": "A: Confirmar  |  B: Voltar",
        "dlg_remote": "O controle passa a comandar o site/app. Back + Start volta ao Nexus.",
        "dlg_opening_nexus": "\U0001F310 Abrindo no Nexus...",
        "dlg_installing": "\u2B07 Baixando e instalando o app...",
        "dlg_config": "\u2699 Configuracoes",
        "dlg_back": "\u2190 Voltar",
        "dlg_color": "\U0001F3A8 Cor do fundo",
        "dlg_color_reset": "\u21BA Cor padrao",
        "dlg_url": "\U0001F517 Editar link",
        "dlg_url_title": "Editar link",
        "dlg_url_prompt": "URL do streaming:",
        "msg_warning": "Aviso",
        "msg_success": "Sucesso",
        "quit_title": "Sair do Nexus",
        "quit_question": "Deseja realmente sair do aplicativo?",
        "quit_yes": "Sim, sair",
        "quit_no": "Nao, ficar",
        "pad_none": "Nenhum controle detectado",
        "pad_hint": "Clique ou use as setas + A. B fecha. B cancela a troca.",
        "pad_nexus_sec": "\U0001F3AE No Nexus",
        "pad_remote_sec": "\U0001F4F1 Nos Apps (remoto)",
        "pad_reset": "Restaurar padrao",
        "pad_device": "Controle em uso:",
        "pad_rescan": "Atualizar lista",
        "pad_deadzone": "Zona morta do analogico:",
        "pad_conn_wired": "\U0001F50C Cabo (latencia minima)",
        "pad_batt_empty": "\U0001FAAB Bateria esgotando (sem fio)",
        "pad_batt_low": "\U0001FAAB Bateria baixa (sem fio)",
        "pad_batt_mid": "\U0001FAAB Bateria media (sem fio)",
        "pad_batt_full": "\U0001FAAB Bateria cheia (sem fio)",
        "pad_press": "Pressione um botao do controle... (B/Esc cancela)",
        "pad_sens": "Sensibilidade do cursor:",
        "pad_scroll": "Rolagem do analogico:",
        "pad_fixed_dpad": "D-pad: setas (fixo)  •  X no dialogo = ir p/ cards  •  Analogico esq.: navegar, dir.: mouse",
        "pad_fixed_remote": "Fixos no remoto: D-pad = setas, analogico esq. = rolagem, analogico dir. = mouse, Back + Start = sair.",
        "pad_a_select": "Selecionar",
        "pad_a_back": "Voltar",
        "pad_a_cards": "Ir para os cards",
        "pad_a_sidebar": "Menu lateral",
        "pad_a_tab_prev": "Aba anterior",
        "pad_a_tab_next": "Proxima aba",
        "pad_a_click_left": "Clique esquerdo",
        "pad_a_click_right": "Clique direito",
        "pad_a_enter": "Enter",
        "pad_a_space": "Espaco (play/pause)",
        "pad_a_fullscreen": "Tela cheia",
        "pad_a_vol_down": "Volume -",
        "pad_a_vol_up": "Volume +",
        "delete_confirm": "Remover",
        "delete_question": "Remover para sempre?",
        "welcome": "Bem-vindo!",
        "recent": "Recentes",
        "your_favorites": "Seus Favoritos",
        "search_placeholder": "Pesquisar streaming...",
        "day_monday": "Segunda-feira",
        "day_tuesday": "Terca-feira",
        "day_wednesday": "Quarta-feira",
        "day_thursday": "Quinta-feira",
        "day_friday": "Sexta-feira",
        "day_saturday": "Sabado",
        "day_sunday": "Domingo",
    },
    "en": {
        "app_title": "Nexus - Big Picture",
        "tab_home": "Home",
        "tab_favorites": "Favorites",
        "tab_movies": "Movies",
        "tab_music": "Music",
        "tab_videos": "Videos",
        "tab_all": "All",
        "sidebar_history": "History",
        "sidebar_favorites": "Favorites",
        "sidebar_settings": "Settings",
        "sidebar_add": "Add Streaming",
        "sidebar_close": "Close",
        "settings_theme": "Change Theme",
        "settings_resolution": "Resolution",
        "settings_gamepad": "Controllers",
        "settings_language": "Language",
        "settings_clear_cache": "Clear logins and cache",
        "cache_confirm": "Delete saved logins, cookies and passwords in the Nexus browser? (%.1f MB)",
        "cache_clear_yes": "Delete everything",
        "cache_cleared": "Logins, cookies and cache cleared.",
        "cache_in_use": "Close the Nexus browser before clearing.",
        "sidebar_keyboard": "Virtual keyboard",
        "kb_title": "Keyboard",
        "kb_hint": "Stick/arrows move \u2022 confirm types \u2022 B closes",
        "kb_space": "space",
        "kb_ok": "OK",
        "settings_title": "Settings",
        "theme_title": "Accent Color",
        "theme_close": "Close",
        "res_title": "Resolution",
        "res_fullscreen": "Fullscreen",
        "res_windowed": "Window (1200x800)",
        "res_close": "Close",
        "gamepad_connected": "Connected",
        "gamepad_none": "No gamepad detected",
        "gamepad_info": "Connect a USB/Bluetooth controller and restart the app.",
        "gamepad_controls": "\n\nA: Select | B: Back\nD-Pad: Navigate\nStart: Menu | LB/RB: Tabs\n\nIn app/site (remote):\nArrows: navigate | A: left click | B: Back\nX: right click | Y: Fullscreen | LB/RB: Volume\nRight stick: mouse | R3: Enter | L3: Space\nLeft stick: scroll\nBack+Start: exit remote",
        "lang_title": "Language",
        "lang_portuguese": "Portugues (BR)",
        "lang_english": "English",
        "lang_close": "Close",
        "history_title": "History",
        "history_empty": "No history yet",
        "add_title": "Add Streaming",
        "add_name": "Name:",
        "add_url": "URL:",
        "add_category": "Category:",
        "add_emoji": "Emoji:",
        "add_logo": "Logo:",
        "add_submit": "Add",
        "add_back": "Back",
        "add_warning": "Name and URL are required!",
        "add_success": "added!",
        "ctx_open": "Open",
        "ctx_remove_fav": "Remove Favorite",
        "ctx_add_fav": "Add Favorite",
        "ctx_change_logo": "Change Logo",
        "ctx_delete": "Delete",
        "ctx_copy_url": "Copy URL",
        "dlg_how": "How do you want to open it?",
        "dlg_site": "\U0001F310 Website",
        "dlg_app": "\U0001F4F1 App",
        "dlg_searching": "\U0001F50D Looking for the installed app...",
        "dlg_hint": "A: Confirm  |  B: Back",
        "dlg_remote": "The gamepad will drive the website/app. Back + Start returns to Nexus.",
        "dlg_opening_nexus": "\U0001F310 Opening in Nexus...",
        "dlg_installing": "\u2B07 Downloading and installing the app...",
        "dlg_config": "\u2699 Settings",
        "dlg_back": "\u2190 Back",
        "dlg_color": "\U0001F3A8 Card color",
        "dlg_color_reset": "\u21BA Default color",
        "dlg_url": "\U0001F517 Edit link",
        "dlg_url_title": "Edit link",
        "dlg_url_prompt": "Streaming URL:",
        "msg_warning": "Warning",
        "msg_success": "Success",
        "quit_title": "Exit Nexus",
        "quit_question": "Do you really want to exit the app?",
        "quit_yes": "Yes, exit",
        "quit_no": "No, stay",
        "pad_none": "No gamepad detected",
        "pad_hint": "Click or use arrows + A. B closes. B cancels remapping.",
        "pad_nexus_sec": "\U0001F3AE In Nexus",
        "pad_remote_sec": "\U0001F4F1 In Apps (remote)",
        "pad_reset": "Reset defaults",
        "pad_device": "Active controller:",
        "pad_rescan": "Refresh list",
        "pad_deadzone": "Stick deadzone:",
        "pad_conn_wired": "\U0001F50C Wired (lowest latency)",
        "pad_batt_empty": "\U0001FAAB Battery critical (wireless)",
        "pad_batt_low": "\U0001FAAB Battery low (wireless)",
        "pad_batt_mid": "\U0001FAAB Battery medium (wireless)",
        "pad_batt_full": "\U0001FAAB Battery full (wireless)",
        "pad_press": "Press a gamepad button... (B/Esc cancels)",
        "pad_sens": "Cursor sensitivity:",
        "pad_scroll": "Stick scroll:",
        "pad_fixed_dpad": "D-pad: arrows (fixed)  •  X in dialog = go to cards  •  Left stick: navigate, right: mouse",
        "pad_fixed_remote": "Fixed in remote: D-pad = arrows, left stick = scroll, right stick = mouse, Back + Start = exit.",
        "pad_a_select": "Select",
        "pad_a_back": "Back",
        "pad_a_cards": "Go to cards",
        "pad_a_sidebar": "Sidebar",
        "pad_a_tab_prev": "Previous tab",
        "pad_a_tab_next": "Next tab",
        "pad_a_click_left": "Left click",
        "pad_a_click_right": "Right click",
        "pad_a_enter": "Enter",
        "pad_a_space": "Space (play/pause)",
        "pad_a_fullscreen": "Fullscreen",
        "pad_a_vol_down": "Volume -",
        "pad_a_vol_up": "Volume +",
        "delete_confirm": "Delete",
        "delete_question": "Delete forever?",
        "welcome": "Welcome!",
        "recent": "Recent",
        "your_favorites": "Your Favorites",
        "search_placeholder": "Search streaming...",
        "day_monday": "Monday",
        "day_tuesday": "Tuesday",
        "day_wednesday": "Wednesday",
        "day_thursday": "Thursday",
        "day_friday": "Friday",
        "day_saturday": "Saturday",
        "day_sunday": "Sunday",
    },
}


def t(key, lang="pt-br"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["pt-br"]).get(key, key)


# Presets de cor do fundo do card (nome, hex)
CARD_COLOR_PRESETS = [
    ("Netflix", "#E50914"), ("YouTube", "#FF0000"), ("Spotify", "#1DB954"),
    ("Disney+", "#113CCF"), ("Prime", "#00A8E1"), ("Twitch", "#9146FF"),
    ("Nexus", "#7c4dff"), ("Ciano", "#00bcd4"), ("Verde", "#00c853"),
    ("Amarelo", "#ffd600"), ("Rosa", "#ff4081"), ("Laranja", "#ff6d00"),
    ("Vermelho", "#e94560"), ("Azul", "#0d47a1"), ("Preto", "#000000"),
    ("Cinza", "#424242"),
]


def _log_dark_result(tag, hwnd, hrs):
    try:
        base = os.path.dirname(os.path.realpath(sys.argv[0] or "."))
        with open(os.path.join(base, "nexus_error.log"), "a", encoding="utf-8") as f:
            f.write(f"DARK {tag} hwnd={hwnd:#x} hrs="
                    f"{[hex(h) if h is not None else None for h in hrs]}\n")
    except Exception:
        pass


def _apply_dark_title(widget, tag="win"):
    # Barra de titulo escura na JANELA CERTA (pelo HWND dela, nao
    # pela janela em foco no momento, que podia ser outro programa).
    # Tenta attr 20 e 19; depois forca o redesenho da moldura, senao o
    # Windows pode ignorar o atributo aplicado antes da janela abrir.
    # So registra log se o attr 20 falhar (para diagnostico).
    try:
        hwnd = int(widget.winfo_id())
        hrs = []
        v = ctypes.c_int(1)
        for attr in (20, 19):
            try:
                hrs.append(ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)))
            except Exception:
                hrs.append(None)
        try:
            _set_pos = ctypes.windll.user32.SetWindowPos
            _set_pos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                 ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            _set_pos.restype = ctypes.c_bool
            _set_pos(hwnd, 0, 0, 0, 0, 0, 0x37)
        except Exception:
            pass
        if hrs and hrs[0] != 0:
            _log_dark_result(tag, hwnd, hrs)
    except Exception:
        pass


def _apply_dark_title_later(widget, delay=150, tag="win"):
    try:
        widget.after(delay, lambda: _apply_dark_title(widget, tag))
    except Exception:
        pass


# ===================== OPEN TARGET DIALOG =====================
class OpenTargetDialog:
    """Janela Site x App. Mouse, teclado e controle: A confirma, B cancela."""

    def __init__(self, app, name):
        self.app = app
        self.name = name
        self.mode = "main"
        self.focus_idx = 0
        self.busy = False
        self.closed = False
        self.thread_result = None
        self.born = time.time()
        self.options = []  # [(botao, comando)] da vista atual

        lang = app.lang
        win = tk.Toplevel(app.root)
        self.win = win
        win.title(name)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        self.win_w, self.win_h = 480, 360
        _apply_dark_title(win, "carddlg")
        _apply_dark_title_later(win, tag="carddlg")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - self.win_w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - self.win_h) // 2
        except Exception:
            x, y = 200, 150
        win.geometry(f"{self.win_w}x{self.win_h}+{max(0, x)}+{max(0, y)}")

        tk.Label(win, text=f"\u25C6 {name}", font=("Segoe UI", 20, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 wraplength=self.win_w - 40).pack(pady=(22, 4))
        self.sub = tk.Label(win, text=t("dlg_how", lang), font=("Segoe UI", 13),
                            fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.sub.pack(pady=(0, 16))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)

        self.status = tk.Label(win, text="", font=("Segoe UI", 12),
                               fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.status.pack(pady=(4, 0))
        tk.Label(win, text=t("dlg_remote", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                 wraplength=self.win_w - 40, justify="center").pack(pady=(8, 0))
        tk.Label(win, text=t("dlg_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(side="bottom", pady=14)

        win.bind("<Left>", lambda e: self.move_prev())
        win.bind("<Right>", lambda e: self.move_next())
        win.bind("<Up>", lambda e: self.move_prev())
        win.bind("<Down>", lambda e: self.move_next())
        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<space>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.cancel())
        win.protocol("WM_DELETE_WINDOW", self.cancel)
        win.grab_set()

        self.show_main()

    def _reg(self, btn, command):
        idx = len(self.options)
        self.options.append((btn, command))
        btn.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        return btn

    def _click(self, idx):
        self.set_focus(idx)
        self.confirm()

    def _resize(self, h):
        self.win_h = h
        try:
            self.win.geometry(f"{self.win_w}x{h}+{self.win.winfo_x()}+{self.win.winfo_y()}")
        except Exception:
            pass

    def show_main(self):
        if self.closed:
            return
        self.mode = "main"
        self.busy = False
        lang = self.app.lang
        self._resize(360)
        try:
            self.sub.configure(text=t("dlg_how", lang))
            self.status.configure(text="")
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        row = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        row.pack()
        for i, (key, cmd) in enumerate((("dlg_site", self._do_site),
                                        ("dlg_app", self._do_app))):
            b = tk.Button(row, text=t(key, lang), font=("Segoe UI", 16, "bold"),
                          width=11, height=2, relief="flat", bd=0, cursor="hand2",
                          command=lambda idx=i: self._click(idx))
            b.grid(row=0, column=i, padx=12)
            self._reg(b, cmd)
        cfg = tk.Button(self.body, text=t("dlg_config", lang), font=("Segoe UI", 14),
                        relief="flat", bd=0, cursor="hand2",
                        command=lambda: self._click(2))
        cfg.pack(fill="x", padx=52, pady=(14, 0))
        self._reg(cfg, self.show_edit)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def show_edit(self):
        if self.closed or self.busy:
            return
        self.mode = "edit"
        lang = self.app.lang
        name = self.name
        self._resize(620)
        try:
            self.sub.configure(text=t("dlg_config", lang))
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        favs = self.app.settings.get("favorites", [])
        rows = [
            ((f"\u2716 {t('ctx_remove_fav', lang)}" if name in favs
              else f"\u2B50 {t('ctx_add_fav', lang)}"), self._edit_fav),
            (t("dlg_color", lang), self._edit_color),
            (t("dlg_color_reset", lang), self._edit_color_reset),
            (t("dlg_url", lang), self._edit_url),
            (f"\U0001F5BC {t('ctx_change_logo', lang)}", self._edit_logo),
            (f"\U0001F4CB {t('ctx_copy_url', lang)}", self._edit_copy_url),
            (f"\U0001F5D1 {t('ctx_delete', lang)}", self._edit_delete),
            (t("dlg_back", lang), self.show_main),
        ]
        for i, (text, cmd) in enumerate(rows):
            b = tk.Button(self.body, text=text, font=("Segoe UI", 13),
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          padx=18, command=lambda idx=i: self._click(idx))
            b.pack(fill="x", padx=40, pady=2)
            self._reg(b, cmd)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def _alive(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def _after_refresh(self, rebuild=True):
        # Acoes que dao refresh_ui destroem esta janela (filha do root)
        if not self._alive():
            self._close()
            return False
        if rebuild:
            if self.mode == "edit":
                self.show_edit()
            else:
                self.show_main()
        return True

    def _edit_fav(self):
        self.app.toggle_favorite(self.name)
        self._after_refresh()

    def _edit_color(self):
        menu = NexusMenuWindow(self.app, t("dlg_color", self.app.lang), [],
                               icon="\U0001F3A8", width=480, cols=4)
        opts = []
        for label, color in CARD_COLOR_PRESETS:
            opts.append((label,
                         lambda col=color: self._pick_card_color(menu, col),
                         {"bg": color,
                          "fg": "black" if color == "#ffd600" else "white",
                          "activebackground": color, "width": 8}))
        opts.append((t("sidebar_close", self.app.lang), menu.close, {"width": 8}))
        menu.set_options(opts, opt_font=10)

    def _pick_card_color(self, menu, color):
        try:
            menu.close()
        except Exception:
            pass
        self.app.set_card_color(self.name, color)
        self._after_refresh(rebuild=False)
        if self._alive() and self.mode == "edit":
            self.show_edit()

    def _edit_color_reset(self):
        self.app.reset_card_color(self.name)
        self._after_refresh()

    def _edit_url(self):
        try:
            current = self.app.opener.effective_url(self.name)
        except Exception:
            current = ""
        NexusTextDialog(self.app, t("dlg_url_title", self.app.lang),
                        t("dlg_url_prompt", self.app.lang), current,
                        lambda url: self._finish_url(url))

    def _finish_url(self, url):
        if url:
            self.app.edit_card_url(self.name, url)

    def _edit_logo(self):
        self.app.change_logo(self.name)
        self._after_refresh()

    def _edit_copy_url(self):
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(self.app.opener.effective_url(self.name))
        except Exception:
            pass

    def _edit_delete(self):
        self.app.delete_streaming(self.name)
        try:
            alive = self.name in self.app.get_all_services()
        except Exception:
            alive = False
        if not alive or not self._alive():
            self._close()
        elif self.mode == "edit":
            self.show_edit()

    def _paint(self):
        for i, (b, _cmd) in enumerate(self.options):
            if i == self.focus_idx:
                b.configure(bg=Config.ACCENT, fg="white",
                            highlightbackground=Config.ACCENT_GLOW, highlightthickness=2)
            else:
                b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                            highlightbackground=Config.BORDER, highlightthickness=1)

    def set_focus(self, idx):
        if self.closed or not self.options:
            return
        self.focus_idx = idx % len(self.options)
        self._paint()

    def move(self, direction=None):
        self.move_next()

    def move_prev(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx - 1) % len(self.options)
        self._paint()

    def move_next(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx + 1) % len(self.options)
        self._paint()

    def confirm(self):
        if self.closed or self.busy or not self.options:
            return
        _btn, cmd = self.options[self.focus_idx]
        try:
            cmd()
        except Exception:
            pass

    def cancel(self):
        if self.closed:
            return
        if self.mode == "edit" and not self.busy:
            self.show_main()
        else:
            self._close()

    def _close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.open_dialog is self:
                self.app.open_dialog = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass

    def _do_site(self):
        url = self.app.opener.effective_url(self.name)
        proc = None
        if self.app.settings.get("embedded_browser", True):
            try:
                self.status.configure(text=t("dlg_opening_nexus", self.app.lang))
            except Exception:
                pass
            try:
                pad_label = self.app.current_pad_label()
            except Exception:
                pad_label = ""
            proc = open_in_nexus_browser(url, self.name, pad_label)
        try:
            self.app.db.add_history(self.name)
        except Exception:
            pass
        if proc is not None:
            # Transicao como se fosse o mesmo app: splash no estilo Nexus
            # enquanto o navegador abre; o remoto (e o minimizar) entram
            # quando a janela ja existe.
            BROWSER_PROCS.append(proc)
            try:
                splash = self.app.show_transition_splash(self.name)
            except Exception:
                splash = None
            svc = self.name
            born = time.time()
            self._close()
            try:
                self.app.root.after(
                    900, lambda: self.app.enter_site_remote(proc, svc, splash, born))
            except Exception:
                self.app.enter_site_remote(proc, svc, splash, born)
            return
        try:
            self.app.opener.open_content(self.name)
            # Entra no remoto ANTES de fechar (mesmo motivo do App):
            # minimiza com o dialogo junto e o foco vai p/ o navegador.
            self.app.enter_remote_mode(self.name, watch=BROWSER_WATCH)
        finally:
            self._close()

    def _install_status(self, key):
        try:
            if self.closed:
                return
            self.status.configure(text=t(key, self.app.lang))
        except Exception:
            pass

    def _do_app(self):
        self.busy = True
        try:
            self.status.configure(text=t("dlg_searching", self.app.lang))
        except Exception:
            pass
        threading.Thread(target=self._app_thread, daemon=True).start()
        self._schedule_check()

    def _app_thread(self):
        try:
            if open_app_for_service(self.name):
                self.thread_result = "app"
                return
            # Nao achou instalado: tenta baixar/instalar sozinho via winget.
            if try_install_service(
                    self.name,
                    status_cb=lambda key: self.app.root.after(
                        0, self._install_status, key)):
                try:
                    if open_app_for_service(self.name):
                        self.thread_result = "app"
                        return
                except Exception:
                    pass
            self.thread_result = "store"
            try:
                open_store_search(self.name)
            except Exception:
                pass
        except Exception:
            try:
                open_store_search(self.name)
            except Exception:
                pass
            self.thread_result = "store"

    def _schedule_check(self):
        try:
            self.app.root.after(120, self._check_result)
        except Exception:
            pass

    def _check_result(self):
        if self.closed:
            return
        if self.thread_result is None:
            self._schedule_check()
            return
        try:
            self.app.db.add_history(self.name)
        except Exception:
            pass
        opened = self.thread_result
        svc = self.name
        if opened == "app":
            # Entra no remoto ANTES de fechar o dialogo: o Nexus minimiza
            # (com o dialogo junto) e o foco vai p/ o app, nunca de volta
            # ao Nexus — sem isso o <FocusIn> mataria o remoto na hora.
            self.app.enter_remote_mode(svc)
            # Tenta deixar o app em tela cheia sem bordas (big picture).
            try:
                before = [hw for hw, _p, _t in _top_level_windows()]
            except Exception:
                before = []
            try:
                self.app.root.after(
                    2500, lambda: self.app.borderless_new_app(before))
            except Exception:
                pass
        self._close()


# ===================== NEXUS TEXT DIALOG =====================
class NexusTextDialog:
    """Pequeno editor de texto estilo Nexus (mouse + teclado + controle)."""

    def __init__(self, app, title, prompt, initial, on_done):
        self.app = app
        self.closed = False
        self.born = time.time()
        self.on_done = on_done
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(title)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        w, h = 480, 250
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        except Exception:
            x, y = 200, 150
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        _apply_dark_title(win, "textdlg")
        _apply_dark_title_later(win, tag="textdlg")

        tk.Label(win, text=f"\U0001F517 {title}", font=("Segoe UI", 18, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR).pack(pady=(18, 4))
        tk.Label(win, text=prompt, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(pady=(0, 8))
        self.entry = tk.Entry(win, font=("Segoe UI", 13), bg=Config.BG_CARD,
                              fg=Config.TEXT_PRIMARY, insertbackground=Config.ACCENT,
                              relief="flat", bd=0, highlightbackground=Config.BORDER,
                              highlightthickness=1)
        self.entry.pack(fill="x", padx=36, ipady=8)
        app.bind_keyboard_popup(self.entry)
        if initial:
            self.entry.insert(0, initial)
            self.entry.select_range(0, "end")

        row = tk.Frame(win, bg=Config.BG_SIDEBAR)
        row.pack(pady=16)
        tk.Button(row, text="OK", font=("Segoe UI", 13, "bold"),
                  bg=Config.ACCENT, fg="white", relief="flat", bd=0,
                  cursor="hand2", padx=36, pady=6,
                  command=self.confirm).pack(side="left", padx=8)
        tk.Button(row, text="\u2328", font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY, relief="flat", bd=0,
                  cursor="hand2", padx=14, pady=6,
                  command=lambda: self.app.open_keyboard(self.entry)).pack(side="left", padx=8)
        tk.Button(row, text=t("sidebar_close", lang), font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY, relief="flat", bd=0,
                  cursor="hand2", padx=24, pady=6,
                  command=self.close).pack(side="left", padx=8)

        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        win.grab_set()
        try:
            self.entry.focus_set()
            app.active_menu = self
        except Exception:
            pass

    def on_hat(self, hat):
        return

    def confirm(self):
        if self.closed:
            return
        try:
            result = self.entry.get().strip()
        except Exception:
            result = ""
        cb = self.on_done
        self.close()
        try:
            if result:
                cb(result)
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.active_menu is self:
                self.app.active_menu = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# ===================== NEXUS VIRTUAL KEYBOARD =====================
def sniff_numeric_entry(entry):
    """Conteudo com cara de numero (porta, ano, telefone...) -> numérico."""
    try:
        txt = (entry.get() or "").strip()
    except Exception:
        return False
    return bool(txt) and re.match(r"^[\d\s\.\,\+\-\(\)/:]+$", txt) is not None


class NexusKeyboard:
    """Teclado virtual p/ controle: analogico/setas movem o cursor,
    confirmar tecla. Tecla de verdade onde o foco estiver (Nexus e browser).
    Sem grab: o foco pode ficar no campo de login do site."""

    ROWS = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", "\u232B"],
        ["\u21E7", "Z", "X", "C", "V", "B", "N", "M", ",", "."],
        ["@", "-", "_", "/", ":"],
    ]

    ROWS_NUM = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        [".", "0", "\u232B"],
    ]

    def __init__(self, app, entry=None, numeric=False):
        self.app = app
        self.entry = entry
        self.closed = False
        self.born = time.time()
        self.shift = False
        self.numeric = bool(numeric)
        self.cur = [0, 0]
        self.cells = []
        try:
            self.target_hwnd = foreground_hwnd()
        except Exception:
            self.target_hwnd = None
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(t("kb_title", lang))
        win.configure(bg=Config.BG_SIDEBAR)
        win.resizable(False, False)
        win.update_idletasks()
        try:
            w = 620
            x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
            y = app.root.winfo_y() + app.root.winfo_height() - 480
        except Exception:
            x, y = 200, 150
        win.geometry(f"{w}x430+{max(0, x)}+{max(0, y)}")
        _apply_dark_title(win, "kbd")

        tk.Label(win, text=f"\u2328 {t('kb_title', lang)}",
                 font=("Segoe UI", 16, "bold"), fg=Config.ACCENT,
                 bg=Config.BG_SIDEBAR).pack(pady=(12, 6))
        tk.Label(win, text=t("kb_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(pady=(0, 6))

        self.grid_frame = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.grid_frame.pack()
        self._build_keys()

        bottom = tk.Frame(win, bg=Config.BG_SIDEBAR)
        bottom.pack(pady=(8, 10))
        self.mode_btn = tk.Button(bottom, text="123", font=("Segoe UI", 13, "bold"),
                                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                  relief="flat", bd=0, cursor="hand2",
                                  padx=24, pady=6, command=self.toggle_mode)
        self.mode_btn.pack(side="left", padx=8)
        tk.Button(bottom, text=t("kb_space", lang), font=("Segoe UI", 13, "bold"),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY, relief="flat",
                  bd=0, cursor="hand2", padx=60, pady=6,
                  command=lambda: self.press_key(" ")).pack(side="left", padx=8)
        tk.Button(bottom, text=t("kb_ok", lang), font=("Segoe UI", 13, "bold"),
                  bg=Config.ACCENT, fg="white", relief="flat",
                  bd=0, cursor="hand2", padx=40, pady=6,
                  command=self.close).pack(side="left", padx=8)

        self._paint()
        self._paint_mode_btn()
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        app.kb_window = self

    def _rows(self):
        return self.ROWS_NUM if self.numeric else self.ROWS

    def _build_keys(self):
        try:
            for w in self.grid_frame.winfo_children():
                w.destroy()
        except Exception:
            pass
        self.cells = []
        rows = self._rows()
        for r, keys in enumerate(rows):
            row_cells = []
            for c, key in enumerate(keys):
                wide = 8 if self.numeric else 4
                b = tk.Button(self.grid_frame, font=("Segoe UI", 16 if self.numeric else 14, "bold"),
                              relief="flat", bd=0, cursor="hand2",
                              width=wide, height=1,
                              command=lambda rr=r, cc=c: self._click(rr, cc))
                b.grid(row=r, column=c, padx=4, pady=4)
                b.bind("<Enter>", lambda e, rr=r, cc=c: self.set_cursor(rr, cc))
                row_cells.append((key, b))
            self.cells.append(row_cells)
        self.cur = [0, 0]
        self._paint()

    def toggle_mode(self):
        if self.closed:
            return
        self.numeric = not self.numeric
        self.shift = False
        self._build_keys()
        self._paint_mode_btn()

    def _paint_mode_btn(self):
        try:
            self.mode_btn.configure(text="ABC" if self.numeric else "123")
        except Exception:
            pass

    def _disp(self, key):
        if len(key) == 1 and key.isalpha():
            return key.upper() if self.shift else key.lower()
        if key == "\u21E7":
            return "\u21E7●" if self.shift else "\u21E7"
        return key

    def _paint(self):
        for r, row in enumerate(self.cells):
            for c, (key, b) in enumerate(row):
                focused = (self.cur == [r, c])
                b.configure(text=self._disp(key))
                if focused:
                    b.configure(bg=Config.ACCENT, fg="white",
                                highlightbackground=Config.ACCENT_GLOW,
                                highlightthickness=2)
                else:
                    b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                highlightbackground=Config.BORDER,
                                highlightthickness=1)

    def set_cursor(self, r, c):
        if self.closed:
            return
        r = max(0, min(r, len(self.cells) - 1))
        c = max(0, min(c, len(self.cells[r]) - 1))
        self.cur = [r, c]
        self._paint()

    def on_hat(self, hat):
        if self.closed:
            return
        r, c = self.cur
        if hat == (0, 1):
            r -= 1
        elif hat == (0, -1):
            r += 1
        elif hat == (-1, 0):
            c -= 1
        elif hat == (1, 0):
            c += 1
        else:
            return
        r %= len(self.cells)
        c %= len(self.cells[r])
        self.set_cursor(r, c)

    def _click(self, r, c):
        self.set_cursor(r, c)
        self.press_focused()

    def press_focused(self):
        if self.closed:
            return
        try:
            key = self.cells[self.cur[0]][self.cur[1]][0]
        except Exception:
            return
        self.press_key(key)

    def press_key(self, key):
        if self.closed:
            return
        if key == "\u21E7":
            self.shift = not self.shift
            self._paint()
            return
        if key == "\u232B":
            self._erase()
            return
        ch = key.upper() if (len(key) == 1 and key.isalpha() and self.shift) else key
        if len(key) == 1 and key.isalpha() and not self.shift:
            ch = key.lower()
        try:
            ent = self.entry
            if ent is not None and ent.winfo_exists():
                ent.insert(tk.INSERT, ch)
                return
        except Exception:
            pass
        self._type_global(ch)

    def _erase(self):
        try:
            ent = self.entry
            if ent is not None and ent.winfo_exists():
                pos = ent.index(tk.INSERT)
                if pos > 0:
                    ent.delete(pos - 1)
                return
        except Exception:
            pass
        self._type_global_key(VK_BACK)

    def _own_hwnd(self):
        try:
            return int(self.win.winfo_id())
        except Exception:
            return None

    def _type_global(self, text):
        try:
            hw = foreground_hwnd()
            if not hw or hw == self._own_hwnd():
                hw = self.target_hwnd
            if hw:
                bring_to_front(hw)
                time.sleep(0.05)
            type_text(self.app.root, text)
        except Exception:
            pass

    def _type_global_key(self, vk):
        try:
            hw = foreground_hwnd()
            if not hw or hw == self._own_hwnd():
                hw = self.target_hwnd
            if hw:
                bring_to_front(hw)
                time.sleep(0.05)
            tap_key(vk)
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.kb_window is self:
                self.app.kb_window = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


def top_modal(app):
    """A janela modal mais nova ainda aberta (dialogo, menu, texto, teclado)."""
    cands = []
    try:
        d = app.open_dialog
        if d is not None and not d.closed:
            cands.append(d)
        m = app.active_menu
        if m is not None and not m.closed:
            cands.append(m)
        k = getattr(app, "kb_window", None)
        if k is not None and not k.closed:
            cands.append(k)
    except Exception:
        pass
    if not cands:
        return None
    return max(cands, key=lambda w: getattr(w, "born", 0))


# ===================== GAMEPAD CONFIG WINDOW =====================
class GamepadConfigWindow:
    """Janela estilo Nexus: mostra e remapeia os botoes (Nexus x Apps)."""

    def __init__(self, app):
        self.app = app
        self.closed = False
        self.capture_token = 0
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(t("settings_gamepad", lang))
        win.configure(bg=Config.BG_PRIMARY)
        win.transient(app.root)
        win.resizable(False, False)
        w, h = 560, 780
        _apply_dark_title(win, "padwin")
        _apply_dark_title_later(win, tag="padwin")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        except Exception:
            x, y = 200, 100
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        outer = tk.Canvas(win, bg=Config.BG_PRIMARY, highlightthickness=0, bd=0)
        outer.pack(side="left", fill="both", expand=True)
        self.scroll_canvas = outer
        sb = tk_ttk.Scrollbar(win, orient="vertical", command=outer.yview,
                              style="Accent.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        outer.configure(yscrollcommand=sb.set)
        self.body = tk.Frame(outer, bg=Config.BG_PRIMARY)
        outer.create_window((0, 0), window=self.body, anchor="nw", tags="inner")
        self.body.bind("<Configure>", lambda e: outer.configure(
            scrollregion=outer.bbox("all")))
        outer.bind("<Configure>", lambda e: outer.itemconfig("inner", width=e.width))

        try:
            gp = app.gamepad
            if PYGAME_AVAILABLE and gp and gp.joystick:
                status = f"\u2713 {gp.joystick.get_name()}"
            else:
                status = t("pad_none", lang)
        except Exception:
            status = t("pad_none", lang)
        tk.Label(self.body, text=f"\U0001F3AE {t('settings_gamepad', lang)}",
                 font=("Segoe UI", 22, "bold"), fg=Config.ACCENT,
                 bg=Config.BG_PRIMARY).pack(pady=(18, 2))
        tk.Label(self.body, text=status, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(self.body, text=t("pad_hint", lang), font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(pady=(0, 6))

        self.device_bar = tk.Frame(self.body, bg=Config.BG_PRIMARY)
        self.device_bar.pack(fill="x", padx=24, pady=(0, 4))
        self.device_items = []
        self.refresh_device_bar()

        self.capture_lbl = tk.Label(self.body, text="", font=("Segoe UI", 13, "bold"),
                                    fg=Config.ACCENT_GLOW, bg=Config.BG_PRIMARY)
        self.capture_lbl.pack(pady=(0, 4))

        self.rows_frame = tk.Frame(self.body, bg=Config.BG_PRIMARY)
        self.rows_frame.pack(fill="x", padx=24)
        self.focus_items = []
        self.pad_focus = 0
        self.refresh()

        win.bind("<Escape>", lambda e: self.on_escape())
        win.bind("<Up>", lambda e: self.move_focus(-1))
        win.bind("<Down>", lambda e: self.move_focus(1))
        win.bind("<Return>", lambda e: self.activate_focused())
        win.bind("<KP_Enter>", lambda e: self.activate_focused())
        win.protocol("WM_DELETE_WINDOW", self.close)
        app.pad_window = self

    def refresh_device_bar(self):
        """Barra de selecao: um botao por controle + atualizar."""
        if self.closed:
            return
        try:
            for w in self.device_bar.winfo_children():
                w.destroy()
        except Exception:
            return
        self.device_items = []
        lang = self.app.lang
        try:
            devices = self.app.pad_devices()
        except Exception:
            devices = []
        tk.Label(self.device_bar, text=t("pad_device", lang), font=("Segoe UI", 13, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY).pack(anchor="w")
        if not devices:
            tk.Label(self.device_bar, text=t("pad_none", lang), font=("Segoe UI", 12),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(anchor="w")
        try:
            gp = self.app.gamepad
            active_name = gp.joystick.get_name() if gp and gp.joystick else None
            conn = gp.connection_info() if gp else ""
        except Exception:
            active_name, conn = None, ""
        for pos, d in enumerate(devices):
            tag = PAD_LAYOUT_LABEL.get(d.get("layout", "generic"), "")
            text = d["name"] + (" [%s]" % tag if tag else "")
            if d["name"] == active_name:
                text = "\u2713 " + text + ("  \u2022  " + conn if conn else "")
            b = tk.Button(self.device_bar, text=text, font=("Segoe UI", 12),
                          fg="white" if d["name"] == active_name else Config.TEXT_PRIMARY,
                          bg=Config.ACCENT if d["name"] == active_name else Config.BG_CARD,
                          activebackground=Config.ACCENT, activeforeground="white",
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          command=lambda p=pos: self._pick_device(p))
            b.pack(fill="x", pady=2)
            self.device_items.append(b)
        rb = tk.Button(self.device_bar, text="\u21BB " + t("pad_rescan", lang),
                       font=("Segoe UI", 12), fg=Config.TEXT_SECONDARY,
                       bg=Config.BG_CARD, relief="flat", cursor="hand2",
                       command=lambda: self._rescan_devices())
        rb.pack(anchor="e", pady=(4, 0))
        self.device_items.append(rb)

    def _pick_device(self, pos):
        try:
            self.app.select_pad_device(pos)
        except Exception:
            pass
        self.refresh_device_bar()
        self.refresh()

    def _rescan_devices(self):
        try:
            gp = self.app.gamepad
            if gp is not None:
                gp.refresh_devices()
        except Exception:
            pass
        self.refresh_device_bar()
        self.refresh()

    def _section(self, title_key, section, order, base_map, settings_key, extra=None):
        lang = self.app.lang
        tk.Label(self.rows_frame, text=t(title_key, lang), font=("Segoe UI", 16, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY, anchor="w").pack(
                     fill="x", pady=(14, 2))
        tk.Frame(self.rows_frame, bg=Config.ACCENT, height=2, width=120).pack(anchor="w")
        try:
            merged = dict(base_map)
            merged.update(self.app.settings.get(settings_key, {}))
        except Exception:
            merged = dict(base_map)
        for action in order:
            btn = merged.get(action)
            row = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            row.pack(fill="x", pady=2)
            try:
                gp = self.app.gamepad
                layout = gp.layout if gp else "xbox"
                logical = normalize_pad_value(btn)
                raw = gp.raw_for_logical(logical) if gp else None
                if not isinstance(raw, int):
                    raw = btn if isinstance(btn, int) else None
                label = pad_logical_label(logical, layout, raw)
            except Exception:
                label = "?"
            tk.Label(row, text=label,
                     font=("Segoe UI", 12, "bold"), fg="white", bg=Config.ACCENT,
                     width=5, relief="flat", bd=0).pack(side="left", padx=(0, 10))
            b = tk.Button(row, text=t(f"pad_a_{action}", lang), font=("Segoe UI", 13),
                          fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                          activebackground=Config.BG_CARD_HOVER,
                          activeforeground=Config.TEXT_PRIMARY,
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          command=lambda s=section, a=action: self.app.start_pad_capture(s, a))
            b.pack(side="left", fill="x", expand=True)
            self.focus_items.append(("action", b, section, action))
        if extra == "sensitivity":
            srow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            srow.pack(fill="x", pady=(8, 0))
            sens_lbl = tk.Label(srow, text=t("pad_sens", lang), font=("Segoe UI", 13),
                                fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            sens_lbl.pack(side="left")
            self.focus_items.append(("sens", sens_lbl))
            self.sens_var = tk.IntVar(value=int(self.app.pad_sensitivity()))
            sc = tk.Scale(srow, from_=4, to=30, orient="horizontal", length=220,
                          showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                          troughcolor=Config.BG_CARD, highlightthickness=0,
                          activebackground=Config.ACCENT, variable=self.sens_var)
            sc.pack(side="right")
            sc.bind("<ButtonRelease-1>", lambda e: self._save_sens())
            scrow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            scrow.pack(fill="x", pady=(4, 0))
            scroll_lbl = tk.Label(scrow, text=t("pad_scroll", lang), font=("Segoe UI", 13),
                                  fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            scroll_lbl.pack(side="left")
            self.focus_items.append(("scroll", scroll_lbl))
            self.scroll_var = tk.IntVar(value=int(self.app.pad_scroll()))
            sc2 = tk.Scale(scrow, from_=2, to=20, orient="horizontal", length=220,
                           showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                           troughcolor=Config.BG_CARD, highlightthickness=0,
                           activebackground=Config.ACCENT, variable=self.scroll_var)
            sc2.pack(side="right")
            sc2.bind("<ButtonRelease-1>", lambda e: self._save_sens())
            dzrow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            dzrow.pack(fill="x", pady=(4, 0))
            dead_lbl = tk.Label(dzrow, text=t("pad_deadzone", lang), font=("Segoe UI", 13),
                                fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            dead_lbl.pack(side="left")
            self.focus_items.append(("dead", dead_lbl))
            try:
                dz_val = int(self.app.settings.get("pad_deadzone", 22))
            except Exception:
                dz_val = 22
            self.dead_var = tk.IntVar(value=min(40, max(5, dz_val)))
            sc3 = tk.Scale(dzrow, from_=5, to=40, orient="horizontal", length=220,
                           showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                           troughcolor=Config.BG_CARD, highlightthickness=0,
                           activebackground=Config.ACCENT, variable=self.dead_var)
            sc3.pack(side="right")
            sc3.bind("<ButtonRelease-1>", lambda e: self._save_sens())
        reset_btn = tk.Button(self.rows_frame, text=t("pad_reset", lang), font=("Segoe UI", 12),
                              fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, relief="flat",
                              cursor="hand2", padx=16, pady=4,
                              command=lambda: self._reset(settings_key))
        reset_btn.pack(anchor="e", pady=(6, 0))
        self.focus_items.append(("reset", reset_btn, settings_key))

    def _save_sens(self):
        try:
            self.app.settings["pad_sensitivity"] = int(self.sens_var.get())
            self.app.settings["pad_scroll"] = int(self.scroll_var.get())
            self.app.settings["pad_deadzone"] = int(self.dead_var.get())
            save_settings(self.app.settings)
        except Exception:
            pass

    def _reset(self, settings_key):
        try:
            self.app.settings[settings_key] = {}
            save_settings(self.app.settings)
        except Exception:
            pass
        self.refresh()

    def refresh(self):
        if self.closed:
            return
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.focus_items = []
        self._section("pad_nexus_sec", "nexus", NEXUS_ACTION_ORDER,
                      DEFAULT_NEXUS_MAP, "pad_nexus")
        tk.Label(self.rows_frame, text=t("pad_fixed_dpad", self.app.lang),
                 font=("Segoe UI", 11), fg=Config.TEXT_SECONDARY,
                 bg=Config.BG_PRIMARY, anchor="w").pack(fill="x", pady=(4, 0))
        self._section("pad_remote_sec", "remote", REMOTE_ACTION_ORDER,
                      DEFAULT_REMOTE_MAP, "pad_remote", extra="sensitivity")
        tk.Label(self.rows_frame, text=t("pad_fixed_remote", self.app.lang),
                 font=("Segoe UI", 11), fg=Config.TEXT_SECONDARY,
                 bg=Config.BG_PRIMARY, anchor="w", justify="left",
                 wraplength=500).pack(fill="x", pady=(4, 10))
        # Scroll com o mouse em QUALQUER ponto da janela (refresh recria linhas)
        self.app._bind_wheel_tree(self.win, self._on_wheel)
        if self.pad_focus >= len(self.focus_items):
            self.pad_focus = 0
        self._paint_focus()
        self.on_capture_end()

    def move_focus(self, d):
        if self.closed or not self.focus_items:
            return
        self.pad_focus = (self.pad_focus + d) % len(self.focus_items)
        self._paint_focus()
        self._ensure_focus_visible()

    def _ensure_focus_visible(self):
        if self.closed or not self.focus_items:
            return
        try:
            widget = self.focus_items[self.pad_focus][1]
            self.scroll_canvas.update_idletasks()
            widget.update_idletasks()
            ch = self.scroll_canvas.winfo_height()
            total = self.body.winfo_height()
            if total <= 0 or ch <= 0 or total <= ch:
                return
            wy = widget.winfo_rooty() - self.scroll_canvas.winfo_rooty()
            wh = widget.winfo_height()
            first, _ = self.scroll_canvas.yview()
            if wy < 0:
                self.scroll_canvas.yview_moveto(max(0.0, first + wy / total))
            elif wy + wh > ch:
                self.scroll_canvas.yview_moveto(min(1.0, first + (wy + wh - ch) / total))
        except Exception:
            pass

    def sens_or_move(self, hat):
        """Esquerda/direita nos ajustes altera; senao navega."""
        if self.closed or not self.focus_items:
            return
        item = self.focus_items[self.pad_focus]
        if item[0] in ("sens", "scroll", "dead"):
            self.adjust_sens(-1 if hat == (-1, 0) else 1)
        else:
            self.move_focus(-1 if hat == (-1, 0) else 1)

    def _paint_focus(self):
        for i, item in enumerate(self.focus_items):
            kind, widget = item[0], item[1]
            focused = (i == self.pad_focus)
            try:
                if kind in ("sens", "scroll", "dead"):
                    widget.configure(fg=Config.ACCENT_GLOW if focused else Config.TEXT_PRIMARY)
                elif focused:
                    widget.configure(bg=Config.ACCENT, fg="white")
                elif kind == "reset":
                    widget.configure(bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY)
                else:
                    widget.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY)
            except Exception:
                pass

    def activate_focused(self):
        if self.closed or not self.focus_items:
            return
        item = self.focus_items[self.pad_focus]
        try:
            if item[0] == "action":
                self.app.start_pad_capture(item[2], item[3])
            elif item[0] == "reset":
                self._reset(item[2])
        except Exception:
            pass

    def adjust_sens(self, d):
        if self.closed or not self.focus_items:
            return
        try:
            kind = self.focus_items[self.pad_focus][0]
            if kind == "scroll":
                v = min(20, max(2, int(self.scroll_var.get()) + d))
                self.scroll_var.set(v)
            elif kind == "dead":
                v = min(40, max(5, int(self.dead_var.get()) + d))
                self.dead_var.set(v)
            else:
                v = min(30, max(4, int(self.sens_var.get()) + d))
                self.sens_var.set(v)
            self._save_sens()
        except Exception:
            pass

    def close_via_pad(self):
        if self.closed:
            return
        try:
            if self.app.pad_capture is not None:
                self.app.cancel_pad_capture()
            else:
                self.close()
        except Exception:
            pass

    def on_escape(self):
        self.close_via_pad()

    def _on_wheel(self, event):
        try:
            if event.delta > 0 and self.app._at_top(self.scroll_canvas):
                return "break"
            if event.delta < 0 and self.app._at_bottom(self.scroll_canvas):
                return "break"
            self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def on_capture_start(self):
        if self.closed:
            return
        self.capture_token += 1
        token = self.capture_token
        self.capture_lbl.configure(text=t("pad_press", self.app.lang))
        try:
            self.win.after(12000, lambda: self._capture_timeout(token))
        except Exception:
            pass

    def _capture_timeout(self, token):
        if not self.closed and token == self.capture_token:
            self.app.cancel_pad_capture()

    def on_capture_end(self):
        if self.closed:
            return
        try:
            self.capture_lbl.configure(text="")
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.app.cancel_pad_capture()
        except Exception:
            pass
        try:
            if self.app.pad_window is self:
                self.app.pad_window = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# ===================== NEXUS MENU WINDOW =====================
class NexusMenuWindow:
    """Janela padrao Nexus: titulo + opcoes navegaveis.
    Mouse, teclado e controle: setas movem, A confirma, B fecha."""

    def __init__(self, app, title, options=(), subtitle="", icon="\u25C6",
                 width=440, cols=1, opt_font=14):
        self.app = app
        self.closed = False
        self.born = time.time()
        self.focus_idx = 0
        self.cols = max(1, cols)
        self.options = []
        self.btns = []
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(title)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        self.win_w = width
        _apply_dark_title(win, "menuwin")
        _apply_dark_title_later(win, tag="menuwin")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - width) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - 400) // 2
        except Exception:
            x, y = 200, 150
        self.win_x, self.win_y = max(0, x), max(0, y)

        tk.Label(win, text=f"{icon} {title}", font=("Segoe UI", 22, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 wraplength=width - 40).pack(pady=(20, 4))
        self.sub = tk.Label(win, text=subtitle, font=("Segoe UI", 13),
                            fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                            wraplength=width - 40, justify="center")
        self.sub.pack(pady=(0, 12))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)
        self.set_options(options, opt_font=opt_font)

        tk.Label(win, text=t("dlg_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(side="bottom", pady=14)

        win.bind("<Up>", lambda e: self.move(0, -1))
        win.bind("<Down>", lambda e: self.move(0, 1))
        win.bind("<Left>", lambda e: self.move(-1, 0))
        win.bind("<Right>", lambda e: self.move(1, 0))
        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<space>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        win.grab_set()
        try:
            app.active_menu = self
        except Exception:
            pass

    def set_options(self, options, opt_font=14):
        if self.closed:
            return
        for w in self.body.winfo_children():
            w.destroy()
        self.options = list(options)
        self.btns = []
        self.focus_idx = 0
        for i, opt in enumerate(self.options):
            label, cmd = opt[0], opt[1]
            style = opt[2] if len(opt) > 2 else {}
            b = tk.Button(self.body, text=label, font=("Segoe UI", opt_font, "bold"),
                          relief="flat", bd=0, cursor="hand2",
                          highlightthickness=3,
                          command=lambda idx=i: (self.set_focus(idx), self.confirm()))
            b.configure(bg=style.get("bg", Config.BG_CARD),
                        fg=style.get("fg", Config.TEXT_PRIMARY),
                        activebackground=style.get("activebackground", Config.BG_CARD_HOVER),
                        activeforeground=style.get("fg", Config.TEXT_PRIMARY))
            if self.cols == 1:
                b.configure(anchor="w", padx=18)
                b.pack(fill="x", padx=40, pady=3)
            else:
                b.configure(width=style.get("width", 10))
                b.grid(row=i // self.cols, column=i % self.cols, padx=4, pady=4)
            b.bind("<Enter>", lambda e, idx=i: self.set_focus(idx))
            self.btns.append(b)
        rows = (len(self.options) + self.cols - 1) // max(1, self.cols)
        h = 250 + rows * (56 if self.cols > 1 else 52)
        try:
            self.win.geometry(f"{self.win_w}x{h}+{self.win_x}+{self.win_y}")
        except Exception:
            pass
        self._paint()
        try:
            if self.btns:
                self.btns[0].focus_set()
        except Exception:
            pass

    def _paint(self):
        for i, b in enumerate(self.btns):
            try:
                opt = self.options[i]
                style = opt[2] if len(opt) > 2 else {}
                plain = style.get("bg", Config.BG_CARD) == Config.BG_CARD
                if i == self.focus_idx:
                    b.configure(highlightbackground="white",
                                highlightcolor="white")
                    if plain:
                        b.configure(bg=Config.ACCENT, fg="white")
                else:
                    b.configure(highlightbackground=Config.BORDER,
                                highlightcolor=Config.BORDER)
                    if plain:
                        b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY)
                    else:
                        b.configure(bg=style.get("bg", Config.BG_CARD),
                                    fg=style.get("fg", Config.TEXT_PRIMARY))
            except Exception:
                pass

    def set_focus(self, idx):
        if self.closed or not self.btns:
            return
        self.focus_idx = idx % len(self.btns)
        self._paint()

    def on_hat(self, hat):
        if hat == (0, 1):
            self.move(0, -1)
        elif hat == (0, -1):
            self.move(0, 1)
        elif hat == (-1, 0):
            self.move(-1, 0)
        elif hat == (1, 0):
            self.move(1, 0)

    def move(self, dh, dv):
        if self.closed or not self.btns:
            return
        n = len(self.btns)
        if self.cols == 1:
            d = dv if dv != 0 else dh
            self.focus_idx = min(n - 1, max(0, self.focus_idx + d))
        else:
            r, c = divmod(self.focus_idx, self.cols)
            r = min((n - 1) // self.cols, max(0, r + dv))
            c = min(self.cols - 1, max(0, c + dh))
            self.focus_idx = min(n - 1, r * self.cols + c)
        self._paint()

    def confirm(self):
        if self.closed or not self.options:
            return
        try:
            self.options[self.focus_idx][1]()
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.active_menu is self:
                self.app.active_menu = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# ===================== MAIN APP =====================
class BigPictureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexus - Big Picture")
        self.root.configure(bg=Config.BG_PRIMARY)
        self.root.geometry("1920x1080")
        self._set_dark_title_bar()
        self._set_app_icon()
        # Reaplica ao mostrar/restaurar (o atributo pre-mapeamento pode ser ignorado)
        try:
            self.root.after(300, self._set_dark_title_bar)
            self.root.bind("<Map>", lambda e: self._set_dark_title_bar())
        except Exception:
            pass

        self.settings = load_settings()
        ensure_images_dir()
        self.db = NexusDB()
        self.opener = StreamingOpener(self.settings)
        self.photo_cache = {}
        self.current_tab = "all"
        self.sidebar_visible = False
        self.sidebar_menu_index = 0
        self.focus_tab = 0
        self.focus_mgr = FocusManager()
        self.nav_level = "tabs"
        self.sections = []
        self.card_index = {}
        self.all_cards = []
        self.card_widgets = []
        self.carousel_cards = []
        self.open_dialog = None
        self.active_menu = None
        self.pad_capture = None
        self.pad_window = None
        self.kb_window = None
        self.browser_remote = None
        self.lang = self.settings.get("language", "pt-br")

        self.build_ui()
        self.setup_keybinds()
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.confirm_quit)
        except Exception:
            pass
        self.gamepad = GamepadManager(self)
        self.update_clock()

    def _set_app_icon(self):
        # Logo_mini na barra de tarefas/titulo (vale p/ todas as janelas).
        # iconbitmap (.ico nativo) + iconphoto: cobre barra, Alt+Tab e titulo.
        try:
            ico = os.path.join(BASE_DIR, "logo_nexus", "Nexus.ico")
            if os.path.exists(ico):
                try:
                    self.root.iconbitmap(default=ico)
                except Exception:
                    pass
            from PIL import Image as _Img, ImageTk as _ImgTk
            p = os.path.join(BASE_DIR, "logo_nexus", "Logo_mini.png")
            if os.path.exists(p):
                img = _Img.open(p).convert("RGBA")
                img.thumbnail((64, 64), _Img.LANCZOS)
                self.icon_photo = _ImgTk.PhotoImage(img)
                # Passar o NOME (str): o objeto cru quebra o parse de args do Tcl.
                # Tenta ate confirmar que fixou (consulta nao-vazia).
                for _try in range(3):
                    try:
                        self.root.iconphoto(True, str(self.icon_photo))
                        if self.root.tk.call("wm", "iconphoto", self.root._w):
                            break
                    except Exception:
                        pass
                    try:
                        time.sleep(0.05)
                    except Exception:
                        pass
        except Exception:
            pass

    def _set_dark_title_bar(self):
        _apply_dark_title(self.root, "root")

    def _style_scrollbars(self):
        style = tk_ttk.Style()
        style.theme_use("default")
        style.configure("Accent.Vertical.TScrollbar",
                        background=Config.ACCENT,
                        troughcolor=Config.BG_PRIMARY,
                        arrowcolor=Config.BG_PRIMARY,
                        bordercolor=Config.BG_PRIMARY,
                        lightcolor=Config.BG_PRIMARY,
                        darkcolor=Config.BG_PRIMARY,
                        relief="flat",
                        borderwidth=0)
        style.map("Accent.Vertical.TScrollbar",
                  background=[("active", Config.ACCENT_GLOW)])

    def load_photo(self, filepath, size=Config.LOGO_SIZE):
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            key = filepath + str(size)
            if key in self.photo_cache:
                return self.photo_cache[key]
            pil_img = Image.open(filepath)
            pil_img.thumbnail((size, size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            self.photo_cache[key] = photo
            return photo
        except:
            return None

    def get_logo(self, name):
        custom = self.settings.get("custom_streamings", {})
        if name in custom and "image" in custom[name]:
            img_path = custom[name]["image"]
            if img_path and os.path.exists(img_path):
                return self.load_photo(img_path)
        # Variantes do nome de arquivo: exato, minusculo e normalizado
        # ("Amazon Prime" -> Amazon_Prime, "Paramount+" -> Paramount_Plus)
        normalized = name.replace(" ", "_").replace("+", "_Plus")
        seen = set()
        candidates = []
        for variant in (name, normalized):
            for form in (variant, variant.lower()):
                if form not in seen:
                    seen.add(form)
                    candidates.append(form)
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp"]:
            for base in candidates:
                p = os.path.join(IMAGES_DIR, base + "_logo" + ext)
                if os.path.exists(p):
                    return self.load_photo(p)
        return None

    def get_all_services(self):
        hidden = set(self.settings.get("hidden_streamings", []))
        overrides = self.settings.get("custom_urls", {})
        all_s = {}
        for k, v in STREAMINGS_DB.items():
            if k not in hidden:
                if k in overrides:
                    v = {**v, "url": overrides[k]}
                all_s[k] = v
        for k, v in self.settings.get("custom_streamings", {}).items():
            if k not in hidden:
                all_s[k] = v
        return all_s

    def set_card_color(self, name, hex_color):
        colors = self.settings.get("card_colors", {})
        colors[name] = hex_color
        self.settings["card_colors"] = colors
        save_settings(self.settings)
        self.refresh_ui()

    def reset_card_color(self, name):
        colors = self.settings.get("card_colors", {})
        if name in colors:
            del colors[name]
            self.settings["card_colors"] = colors
            save_settings(self.settings)
            self.refresh_ui()

    def edit_card_url(self, name, url):
        url = (url or "").strip()
        if not url:
            return False
        custom = self.settings.get("custom_streamings", {})
        if name in custom:
            custom[name]["url"] = url
            self.settings["custom_streamings"] = custom
        else:
            urls = self.settings.get("custom_urls", {})
            urls[name] = url
            self.settings["custom_urls"] = urls
        save_settings(self.settings)
        return True

    # ===================== BUILD UI =====================
    def build_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        self.root.configure(bg=Config.BG_PRIMARY)

        self.main_frame = tk.Frame(self.root, bg=Config.BG_PRIMARY)
        self.main_frame.pack(fill="both", expand=True)

        self.build_top_bar()
        self.build_content_area()
        self.build_bottom_tabs()
        self.build_sidebar()
        self.build_qa_overlay()

        self.render_tab(self.current_tab)

    def build_top_bar(self):
        bar = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR, height=70)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        logo = tk.Label(bar, text="\u25C6 NEXUS", font=("Segoe UI", 24, "bold"),
                        fg=Config.ACCENT, bg=Config.BG_SIDEBAR)
        logo.pack(side="left", padx=30)

        self.nav_frame = tk.Frame(bar, bg=Config.BG_SIDEBAR)
        self.nav_frame.pack(side="left", padx=40)

        self.nav_buttons = {}
        tabs = [
            (t("tab_favorites", self.lang), "favorites"),
            (t("tab_movies", self.lang), "movies"),
            (t("tab_music", self.lang), "music"),
            (t("tab_videos", self.lang), "videos"),
            (t("tab_all", self.lang), "all"),
        ]
        for idx, (text, tid) in enumerate(tabs):
            btn = tk.Button(self.nav_frame, text=text, font=("Segoe UI", 13),
                            bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                            activebackground=Config.ACCENT, activeforeground="white",
                            relief="flat", cursor="hand2", bd=0,
                            command=lambda t=tid: self.switch_tab(t))
            btn.pack(side="left", padx=4)
            btn.bind("<Enter>", lambda e, i=idx: self.sync_focus_to_tab(i))
            self.nav_buttons[tid] = btn

        right = tk.Frame(bar, bg=Config.BG_SIDEBAR)
        right.pack(side="right", padx=20)

        self.clock_label = tk.Label(right, font=("Segoe UI", 13),
                                    fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.clock_label.pack(side="left", padx=10)

        qa_btn = tk.Button(right, text="\u2630", font=("Segoe UI", 18),
                           bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                           activebackground=Config.ACCENT, relief="flat",
                           cursor="hand2", command=self.toggle_sidebar, bd=0)
        qa_btn.pack(side="left", padx=10)

        # Botoes de janela discretos: minimizar e fechar (F11 alterna tela cheia)
        min_btn = tk.Button(right, text="\u2013", font=("Segoe UI", 12),
                            bg=Config.BG_SIDEBAR, fg="#4a4a6a",
                            activebackground=Config.BG_CARD_HOVER,
                            activeforeground=Config.TEXT_PRIMARY,
                            relief="flat", cursor="hand2", bd=0,
                            padx=10, pady=2, command=self.minimize_app)
        min_btn.pack(side="left", padx=2)
        min_btn.bind("<Enter>", lambda e: min_btn.configure(fg=Config.TEXT_PRIMARY))
        min_btn.bind("<Leave>", lambda e: min_btn.configure(fg="#4a4a6a"))
        close_btn = tk.Button(right, text="\u2715", font=("Segoe UI", 12),
                              bg=Config.BG_SIDEBAR, fg="#4a4a6a",
                              activebackground="#e94560",
                              activeforeground="white",
                              relief="flat", cursor="hand2", bd=0,
                              padx=10, pady=2, command=self.confirm_quit)
        close_btn.pack(side="left", padx=2)
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#e94560"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#4a4a6a"))

        # Arrastar a janela pelo cursor nas areas livres da barra superior
        for w in (bar, logo, self.nav_frame, right, self.clock_label):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        try:
            if self.root.attributes("-fullscreen"):
                return
            self._drag_offset = (event.x_root - self.root.winfo_x(),
                                 event.y_root - self.root.winfo_y())
        except Exception:
            pass

    def _drag_move(self, event):
        try:
            if self.root.attributes("-fullscreen"):
                return
            dx, dy = getattr(self, "_drag_offset", (0, 0))
            self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
        except Exception:
            pass

    def build_content_area(self):
        self.content_frame = tk.Frame(self.main_frame, bg=Config.BG_PRIMARY)
        self.content_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.content_frame, bg=Config.BG_PRIMARY,
                                highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self._style_scrollbars()
        self.scrollbar = tk_ttk.Scrollbar(self.content_frame, orient="vertical",
                                          command=self.canvas.yview,
                                          style="Accent.Vertical.TScrollbar")
        self.scrollbar.pack(side="right", fill="y", padx=(0, 2))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame = tk.Frame(self.canvas, bg=Config.BG_PRIMARY)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame,
                                                        anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self.canvas_window, width=e.width))

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scroll_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.config(takefocus=True)

        self.root.bind("<MouseWheel>", self._on_mousewheel_global)

    def build_bottom_tabs(self):
        pass

    def build_sidebar(self):
        self.sidebar = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR,
                                width=Config.SIDEBAR_WIDTH)
        self.sidebar.place(x=-Config.SIDEBAR_WIDTH, y=0, relheight=1)
        self.sidebar.pack_propagate(False)
        self.sidebar_visible = False

        header = tk.Frame(self.sidebar, bg=Config.BG_SIDEBAR)
        header.pack(fill="x", padx=0, pady=(25, 0))

        tk.Label(header, text="\u25C6 NEXUS", font=("Segoe UI", 26, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR).pack(padx=25, anchor="w")

        self.sidebar_time = tk.Label(header, font=("Segoe UI", 44, "bold"),
                                     fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR)
        self.sidebar_time.pack(pady=(8, 2), padx=25, anchor="w")

        self.sidebar_date = tk.Label(header, font=("Segoe UI", 14),
                                     fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.sidebar_date.pack(pady=(0, 20), padx=25, anchor="w")

        weekday = self._get_translated_weekday()
        now = datetime.now()
        self.sidebar_date.config(text=f"{weekday}, {now.strftime('%d/%m/%Y')}")

        tk.Frame(self.sidebar, bg=Config.BORDER, height=1).pack(fill="x", padx=25)

        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=Config.BG_SIDEBAR,
                                        highlightthickness=0, bd=0)

        self.sidebar_scrollbar = tk_ttk.Scrollbar(self.sidebar, orient="vertical",
                                                  command=self.sidebar_canvas.yview,
                                                  style="Accent.Vertical.TScrollbar")
        self.sidebar_scroll_frame = tk.Frame(self.sidebar_canvas, bg=Config.BG_SIDEBAR)

        self.sidebar_scroll_frame.bind(
            "<Configure>", lambda e: self.sidebar_canvas.configure(
                scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_scroll_frame,
                                          anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_scrollbar.pack(side="right", fill="y", padx=(0, 2))

        self.sidebar_btns = []
        self.sidebar_items = []

        tk.Label(self.sidebar_scroll_frame, text=t("sidebar_settings", self.lang),
                 font=("Segoe UI", 13, "bold"), fg=Config.TEXT_PRIMARY,
                 bg=Config.BG_SIDEBAR, anchor="w").pack(pady=(0, 8), padx=25, fill="x")

        settings_items = [
            (t("settings_theme", self.lang), self.open_theme_picker, "\U0001F3A8"),
            (t("settings_resolution", self.lang), self.open_resolution, "\U0001F5A9"),
            (t("settings_gamepad", self.lang), self.show_gamepad_info, "\U0001F3AE"),
            (t("settings_language", self.lang), self.open_language_picker, "\U0001F310"),
            (t("sidebar_keyboard", self.lang), self.open_keyboard_sidebar, "\u2328"),
            (t("settings_clear_cache", self.lang), self.confirm_clear_browser_profile, "\U0001F9F9"),
        ]

        for text, cmd, icon in settings_items:
            btn = tk.Button(self.sidebar_scroll_frame, text=f"  {icon}  {text}",
                            font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                            fg=Config.TEXT_SECONDARY, activebackground=Config.ACCENT,
                            activeforeground="white", relief="flat", anchor="w",
                            cursor="hand2", bd=0, padx=20, pady=10, command=cmd)
            btn.pack(fill="x", padx=15, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
            self.sidebar_btns.append(btn)
            self.sidebar_items.append((text, cmd))

        tk.Frame(self.sidebar_scroll_frame, bg=Config.BORDER, height=1).pack(
            fill="x", padx=25, pady=(15, 10))

        add_btn = tk.Button(self.sidebar_scroll_frame,
                            text=f"  \U0001F4FA  {t('sidebar_add', self.lang)}",
                            font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                            fg=Config.TEXT_SECONDARY, activebackground=Config.ACCENT,
                            activeforeground="white", relief="flat", anchor="w",
                            cursor="hand2", bd=0, padx=20, pady=10,
                            command=self.render_add_streaming)
        add_btn.pack(fill="x", padx=15, pady=2)
        add_btn.bind("<Enter>", lambda e, b=add_btn: b.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY))
        add_btn.bind("<Leave>", lambda e, b=add_btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
        self.sidebar_btns.append(add_btn)
        self.sidebar_items.append((t("sidebar_add", self.lang), self.render_add_streaming))

        close_btn = tk.Button(self.sidebar_scroll_frame,
                              text=f"  \u2715  {t('sidebar_close', self.lang)}",
                              font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                              fg=Config.TEXT_SECONDARY, activebackground="#e94560",
                              activeforeground="white", relief="flat", anchor="w",
                              cursor="hand2", bd=0, padx=20, pady=10,
                              command=self.toggle_sidebar)
        close_btn.pack(fill="x", padx=15, pady=(2, 20))
        close_btn.bind("<Enter>", lambda e, b=close_btn: b.configure(bg="#e94560", fg="white"))
        close_btn.bind("<Leave>", lambda e, b=close_btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
        self.sidebar_btns.append(close_btn)
        self.sidebar_items.append((t("sidebar_close", self.lang), self.toggle_sidebar))
        # Scroll com o mouse em QUALQUER ponto da sidebar
        self._bind_wheel_tree(self.sidebar, self._on_sidebar_wheel)

    def build_qa_overlay(self):
        self.dim_overlay = tk.Frame(self.root, bg="#000000")
        self.dim_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.dim_overlay.place_forget()
        self.dim_overlay.lower(self.main_frame)
        self.dim_overlay.bind("<Button-1>", lambda e: self.close_qa())

        self.qa_frame = tk.Frame(self.root, bg=Config.BG_SIDEBAR,
                                  highlightbackground=Config.ACCENT, highlightthickness=2)
        self.qa_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.qa_frame.place_forget()

    # ===================== KEYBINDS =====================
    def setup_keybinds(self):
        self.root.bind("<Escape>", lambda e: self.go_back())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<F5>", lambda e: self.refresh_ui())
        self.root.bind("<Left>", lambda e: self._nav_keys("left"))
        self.root.bind("<Right>", lambda e: self._nav_keys("right"))
        self.root.bind("<Up>", lambda e: self._nav_keys("up"))
        self.root.bind("<Down>", lambda e: self._nav_keys("down"))
        self.root.bind("<Return>", lambda e: self.select_current())
        self.root.bind("<space>", lambda e: self.select_current())
        self.root.bind("<Control-q>", lambda e: self.toggle_sidebar())
        self.root.bind("<y>", lambda e: self.toggle_sidebar())
        self.root.bind("<Y>", lambda e: self.toggle_sidebar())
        self.root.bind("<x>", lambda e: self.go_to_cards())
        self.root.bind("<X>", lambda e: self.go_to_cards())
        self.root.bind("<FocusIn>", lambda e: self._on_focus_in())

    # ===================== NAVIGATION =====================
    def _nav_keys(self, direction):
        self._nav(direction)
        self.warp_to_focus()

    def _at_top(self, canvas):
        try:
            return canvas.yview()[0] <= 0.0
        except Exception:
            return True

    def _at_bottom(self, canvas):
        try:
            return canvas.yview()[1] >= 1.0
        except Exception:
            return True

    def _on_mousewheel(self, event):
        if event.delta > 0 and self._at_top(self.canvas):
            return
        if event.delta < 0 and self._at_bottom(self.canvas):
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_global(self, event):
        if not self.sidebar_visible:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_wheel_tree(self, widget, handler):
        """Liga o scroll do mouse no widget E em todos os filhos (o evento
        nao propaga ao pai no tkinter, entao cada um precisa do proprio bind)."""
        try:
            widget.bind("<MouseWheel>", handler)
            for child in widget.winfo_children():
                self._bind_wheel_tree(child, handler)
        except Exception:
            pass

    def _on_sidebar_wheel(self, event):
        try:
            if event.delta > 0 and self._at_top(self.sidebar_canvas):
                return "break"
            if event.delta < 0 and self._at_bottom(self.sidebar_canvas):
                return "break"
            self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def _nav(self, direction):
        if self.sidebar_visible:
            if direction == "up":
                new_idx = max(0, self.sidebar_menu_index - 1)
            elif direction == "down":
                new_idx = min(len(self.sidebar_items) - 1, self.sidebar_menu_index + 1)
            else:
                return
            if new_idx == self.sidebar_menu_index:
                return  # no limite: para, sem update/scroll
            self.sidebar_menu_index = new_idx
            self.update_sidebar_focus()
            return
        if direction == "up":
            self._dpad_up()
        elif direction == "down":
            self._dpad_down()
        elif direction == "left":
            self._dpad_left()
        elif direction == "right":
            self._dpad_right()

    def _dpad_up(self):
        # Eixo vertical: troca de carrossel (linha). Nunca seleciona titulos/abas.
        # Retorna True se algo mudou; no limite, para (sem update/scroll).
        if self.nav_level == "tabs":
            return False
        sec = self.sections[self.focus_mgr.focused_row]
        if sec["canvas"] is None:
            cols = sec["visible_count"]
            total = len(sec["names"])
            if total > cols:
                new_col = self.focus_mgr.focused_col - cols
                if new_col >= 0:
                    self.focus_mgr.focused_col = new_col
                    self.update_all_focus()
                    return True
        if self.focus_mgr.focused_row > 0:
            self.focus_mgr.focused_row -= 1
            self._clamp_focused_col()
            self.update_all_focus()
            return True
        return False

    def _dpad_down(self):
        # Eixo vertical: troca de carrossel (linha).
        if self.nav_level == "tabs":
            if not self.sections:
                return False
            self.nav_level = "items"
            self.focus_mgr.focused_row = 0
            self.focus_mgr.focused_col = 0
            sec = self.sections[0]
            if sec["canvas"] is not None:
                sec["scroll_offset"] = 0
                self._update_carousel_scroll(sec)
            self.update_all_focus()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        if sec["canvas"] is None:
            cols = sec["visible_count"]
            total = len(sec["names"])
            if total > cols:
                new_col = self.focus_mgr.focused_col + cols
                if new_col < total:
                    self.focus_mgr.focused_col = new_col
                    self.update_all_focus()
                    return True
        if self.focus_mgr.focused_row < len(self.sections) - 1:
            self.focus_mgr.focused_row += 1
            self._clamp_focused_col()
            sec2 = self.sections[self.focus_mgr.focused_row]
            if sec2["canvas"] is not None:
                sec2["scroll_offset"] = 0
                self._update_carousel_scroll(sec2)
            self.update_all_focus()
            return True
        return False

    def _dpad_left(self):
        # Eixo horizontal: troca de card, 1 por 1. Nunca muda de linha/secao.
        if self.nav_level == "tabs":
            if self.focus_tab <= 0:
                return False
            self.focus_tab -= 1
            self.update_tab_highlight()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        col = self.focus_mgr.focused_col
        if col > 0:
            self.focus_mgr.focused_col -= 1
        elif sec["canvas"] is not None and sec["scroll_offset"] > 0:
            sec["scroll_offset"] -= 1
            self._update_carousel_scroll(sec)
        else:
            return False
        self.update_all_focus()
        return True

    def _dpad_right(self):
        # Eixo horizontal: troca de card, 1 por 1. Nunca muda de linha/secao.
        if self.nav_level == "tabs":
            tabs = TABS
            if self.focus_tab >= len(tabs) - 1:
                return False
            self.focus_tab += 1
            self.update_tab_highlight()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        total = len(sec["names"])
        col = self.focus_mgr.focused_col
        if sec["canvas"] is not None:
            start, end, _ = self._get_visible_range(sec)
            max_vis = end - start
            if col < max_vis - 1 and col < total - 1:
                self.focus_mgr.focused_col += 1
            elif end < total:
                sec["scroll_offset"] += 1
                self._update_carousel_scroll(sec)
            else:
                return False
        else:
            if col < total - 1:
                self.focus_mgr.focused_col += 1
            else:
                return False
        self.update_all_focus()
        return True

    def _clamp_focused_col(self):
        sec = self.sections[self.focus_mgr.focused_row]
        total = len(sec["names"])
        if sec["canvas"] is not None:
            vis = min(sec["visible_count"], total)
            self.focus_mgr.focused_col = min(self.focus_mgr.focused_col, vis - 1)
        else:
            self.focus_mgr.focused_col = min(self.focus_mgr.focused_col, total - 1)

    def _get_visible_range(self, sec):
        offset = sec["scroll_offset"]
        total = len(sec["names"])
        vis = min(sec["visible_count"], total)
        return offset, offset + vis, total

    def _get_sec_total(self, sec):
        return len(sec["names"])

    def select_current(self):
        if self.open_dialog is not None:
            return
        if self.sidebar_visible:
            if 0 <= self.sidebar_menu_index < len(self.sidebar_items):
                self.sidebar_items[self.sidebar_menu_index][1]()
            return
        if self.nav_level == "tabs":
            tabs = TABS
            if self.focus_tab < len(tabs):
                self.switch_tab(tabs[self.focus_tab])
        elif self.nav_level == "items":
            sec = self.sections[self.focus_mgr.focused_row]
            if sec["canvas"] is None:
                name_idx = self.focus_mgr.focused_col
            else:
                name_idx = sec["scroll_offset"] + self.focus_mgr.focused_col
            if 0 <= name_idx < len(sec["names"]):
                name = sec["names"][name_idx]
                self.ask_open_target(name)

    def go_back(self):
        if self.sidebar_visible:
            self.toggle_sidebar()
        elif hasattr(self, 'qa_visible') and self.qa_visible:
            self.close_qa()
        elif self.nav_level == "items":
            self.nav_level = "tabs"
            self.update_all_focus()

    def go_to_cards(self):
        # Botao X do controle: foca direto no primeiro card da aba atual
        if self.sidebar_visible:
            self.toggle_sidebar()
        if hasattr(self, 'qa_visible') and self.qa_visible:
            self.close_qa()
        if not self.sections:
            return
        self.nav_level = "items"
        self.focus_mgr.focused_row = 0
        self.focus_mgr.focused_col = 0
        sec = self.sections[0]
        if sec["canvas"] is not None:
            sec["scroll_offset"] = 0
            self._update_carousel_scroll(sec)
        self.update_all_focus()
        self.warp_to_focus()

    def _update_carousel_scroll(self, sec):
        canvas = sec["canvas"]
        if canvas is None:
            return
        inner = sec["inner_frame"]
        inner.update_idletasks()
        offset = sec["scroll_offset"]
        children = inner.winfo_children()
        if offset < len(children):
            widget = children[offset]
            widget.update_idletasks()
            x = widget.winfo_x()
            scroll_region = canvas.cget("scrollregion")
            if scroll_region:
                total_w = int(scroll_region.split()[2])
                if total_w > 0:
                    canvas.xview_moveto(x / total_w)

    def _scroll_to_section(self, section_idx):
        if section_idx < len(self.sections):
            sec = self.sections[section_idx]
            widget = sec["title_widget"]
            self.canvas.update_idletasks()
            y = widget.winfo_rooty() - self.canvas.winfo_rooty()
            canvas_h = self.canvas.winfo_height()
            total_h = self.scroll_frame.winfo_height()
            if total_h > 0:
                scroll_pos = max(0, (y - canvas_h // 3)) / total_h
                self.canvas.yview_moveto(min(1.0, scroll_pos))

    def _scroll_to_card(self, sec, abs_idx):
        # Grade (ex. aba Todos): rola o canvas principal ate o card focado
        if abs_idx < 0 or abs_idx >= len(sec["widgets"]):
            return
        widget = sec["widgets"][abs_idx]
        self.canvas.update_idletasks()
        widget.update_idletasks()
        canvas_h = self.canvas.winfo_height()
        total_h = self.scroll_frame.winfo_height()
        if total_h <= 0 or canvas_h <= 0 or total_h <= canvas_h:
            return
        wy = widget.winfo_rooty() - self.canvas.winfo_rooty()
        wh = widget.winfo_height()
        try:
            first, _ = self.canvas.yview()
        except:
            return
        margin = 15
        if wy < margin:
            self.canvas.yview_moveto(max(0.0, first + (wy - margin) / total_h))
        elif wy + wh > canvas_h - margin:
            self.canvas.yview_moveto(min(1.0, first + (wy + wh - canvas_h + margin) / total_h))

    def update_all_focus(self):
        self.update_tab_highlight()
        for i, sec in enumerate(self.sections):
            sec["title_widget"].configure(fg=Config.TEXT_PRIMARY)
            sec["line_widget"].configure(width=120)
            for j, w in enumerate(sec["widgets"]):
                if sec["canvas"] is not None:
                    # Carrossel: focused_col e relativo a janela visivel
                    is_focused = (self.nav_level == "items" and i == self.focus_mgr.focused_row
                                  and (j - sec["scroll_offset"]) == self.focus_mgr.focused_col)
                else:
                    is_focused = (self.nav_level == "items" and i == self.focus_mgr.focused_row
                                  and j == self.focus_mgr.focused_col)
                if is_focused:
                    w.configure(bg=Config.BG_CARD_HOVER,
                                highlightbackground=Config.ACCENT, highlightthickness=3)
                else:
                    w.configure(bg=Config.BG_CARD,
                                highlightbackground=Config.BORDER, highlightthickness=1)
        if self.nav_level == "items" and self.focus_mgr.focused_row < len(self.sections):
            sec = self.sections[self.focus_mgr.focused_row]
            if sec["canvas"] is None:
                self._scroll_to_card(sec, self.focus_mgr.focused_col)
            else:
                self._scroll_to_section(self.focus_mgr.focused_row)

    def update_sidebar_focus(self):
        for i, btn in enumerate(self.sidebar_btns):
            if i == self.sidebar_menu_index:
                btn.configure(bg=Config.ACCENT, fg="white")
            else:
                btn.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY)
        if self.sidebar_menu_index < len(self.sidebar_btns):
            btn = self.sidebar_btns[self.sidebar_menu_index]
            self.sidebar_canvas.update_idletasks()
            y = btn.winfo_y()
            h = btn.winfo_height()
            canvas_h = self.sidebar_canvas.winfo_height()
            total_h = self.sidebar_scroll_frame.winfo_height()
            if total_h > canvas_h:
                scroll_pos = max(0, (y - canvas_h // 3)) / total_h
                self.sidebar_canvas.yview_moveto(min(1.0, scroll_pos))

    def switch_tab(self, tab):
        tabs = TABS
        self.current_tab = tab
        self.focus_mgr.reset()
        self.nav_level = "tabs"
        if tab in tabs:
            self.focus_tab = tabs.index(tab)
        self.render_tab(tab)

    def tab_prev(self):
        tabs = TABS
        idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
        self.switch_tab(tabs[(idx - 1) % len(tabs)])
        self.warp_to_focus()

    def tab_next(self):
        tabs = TABS
        idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
        self.switch_tab(tabs[(idx + 1) % len(tabs)])
        self.warp_to_focus()

    def update_tab_highlight(self):
        tabs = TABS
        for tid, btn in self.nav_buttons.items():
            idx = tabs.index(tid) if tid in tabs else -1
            is_focused = self.nav_level == "tabs" and idx == self.focus_tab
            if tid == self.current_tab:
                btn.configure(bg=Config.ACCENT, fg="white", font=("Segoe UI", 13, "bold"))
            elif is_focused:
                btn.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY, font=("Segoe UI", 13, "bold"))
            else:
                btn.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY, font=("Segoe UI", 13))

    # ===================== RENDER =====================
    def render_tab(self, tab):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.all_cards = []
        self.card_widgets = []
        self.sections = []
        self.card_index = {}
        if tab == "home":
            # Legado: aba Home foi removida, mostra Todos
            tab = "all"
            self.current_tab = "all"
        self.update_tab_highlight()

        if tab == "favorites":
            self.render_section("Meus Favoritos", self.settings.get("favorites", []))
        elif tab == "movies":
            self.render_category("Filmes")
        elif tab == "music":
            self.render_category("Musica")
        elif tab == "videos":
            self.render_category("Videos")
        else:
            all_names = list(self.get_all_services().keys())
            self.render_grid("Todos os Streamings", all_names)

        self.update_all_focus()

    def render_category(self, category):
        all_s = self.get_all_services()
        items = [n for n, info in all_s.items() if info.get("category") == category]
        self.render_section(category, items)

    def render_section(self, title, names):
        if not names:
            return

        section = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        section.pack(fill="x", padx=30, pady=(20, 5))

        title_lbl = tk.Label(section, text=title, font=("Segoe UI", 20, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
        title_lbl.pack(anchor="w")

        line = tk.Frame(section, bg=Config.ACCENT, height=3, width=120)
        line.pack(anchor="w", pady=(5, 15))

        carousel_outer = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        carousel_outer.pack(fill="x", pady=(0, 10))

        arrow_bg = Config.BG_SIDEBAR
        arrow_fg = Config.ACCENT
        arrow_hover = Config.ACCENT_GLOW

        left_btn = tk.Button(carousel_outer, text="\u25C0", font=("Segoe UI", 20),
                             bg=arrow_bg, fg=arrow_fg, relief="flat", bd=0,
                             cursor="hand2", activebackground=arrow_hover,
                             activeforeground="white", width=4, height=3)
        left_btn.pack(side="left", fill="y")

        carousel_canvas = tk.Canvas(carousel_outer, bg=Config.BG_PRIMARY,
                                    highlightthickness=0, bd=0, height=Config.CARD_HEIGHT + 20)
        carousel_canvas.pack(side="left", fill="both", expand=True)

        right_btn = tk.Button(carousel_outer, text="\u25B6", font=("Segoe UI", 20),
                              bg=arrow_bg, fg=arrow_fg, relief="flat", bd=0,
                              cursor="hand2", activebackground=arrow_hover,
                              activeforeground="white", width=4, height=3)
        right_btn.pack(side="right", fill="y")

        for b in [left_btn, right_btn]:
            b.bind("<Enter>", lambda e, btn=b: btn.configure(fg=arrow_hover))
            b.bind("<Leave>", lambda e, btn=b: btn.configure(fg=arrow_fg))

        inner_frame = tk.Frame(carousel_canvas, bg=Config.BG_PRIMARY)
        carousel_canvas.create_window((0, 0), window=inner_frame, anchor="nw", tags="inner")

        sec = {
            "title_widget": title_lbl,
            "line_widget": line,
            "canvas": carousel_canvas,
            "inner_frame": inner_frame,
            "left_btn": left_btn,
            "right_btn": right_btn,
            "names": list(names),
            "widgets": [],
            "scroll_offset": 0,
            "visible_count": 4,
        }

        def _sync_focus_after_manual_scroll():
            if (self.nav_level == "items" and self.sections
                    and self.focus_mgr.focused_row < len(self.sections)
                    and self.sections[self.focus_mgr.focused_row] is sec):
                self._clamp_focused_col()
                self.update_all_focus()

        def scroll_left():
            if sec["scroll_offset"] > 0:
                sec["scroll_offset"] -= 1
                self._update_carousel_scroll(sec)
                _sync_focus_after_manual_scroll()

        def scroll_right():
            _, end, total = self._get_visible_range(sec)
            if end < total:
                sec["scroll_offset"] += 1
                self._update_carousel_scroll(sec)
                _sync_focus_after_manual_scroll()

        left_btn.configure(command=scroll_left)
        right_btn.configure(command=scroll_right)

        for i, name in enumerate(names):
            card = self.create_card(inner_frame, name)
            card.grid(row=0, column=i, padx=7, pady=5, sticky="nsew")
            inner_frame.columnconfigure(i, weight=0)
            sec["widgets"].append(card)
            self.card_index[card] = (len(self.sections), i)

        self.sections.append(sec)

        inner_frame.update_idletasks()
        total_width = inner_frame.winfo_reqwidth()
        carousel_canvas.configure(scrollregion=(0, 0, total_width, Config.CARD_HEIGHT + 20))

        def on_canvas_configure(e):
            carousel_canvas.itemconfig("inner", width=max(e.width, total_width))
        carousel_canvas.bind("<Configure>", on_canvas_configure)

        def _section_mousewheel(event):
            carousel_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        carousel_canvas.bind("<MouseWheel>", _section_mousewheel)
        inner_frame.bind("<MouseWheel>", _section_mousewheel)

    def render_grid(self, title, names):
        if not names:
            return

        section = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        section.pack(fill="x", padx=30, pady=(20, 5))

        title_lbl = tk.Label(section, text=title, font=("Segoe UI", 20, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
        title_lbl.pack(anchor="w")

        line = tk.Frame(section, bg=Config.ACCENT, height=3, width=120)
        line.pack(anchor="w", pady=(5, 15))

        grid_frame = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        grid_frame.pack(fill="x", padx=30, pady=(0, 10))

        sec_widgets = []
        for i, name in enumerate(names):
            card = self.create_card(grid_frame, name)
            card.grid(row=i // 5, column=i % 5, padx=7, pady=5, sticky="nsew")
            sec_widgets.append(card)
            self.card_index[card] = (len(self.sections), i)

        for c in range(5):
            grid_frame.columnconfigure(c, weight=1)

        self.sections.append({
            "title_widget": title_lbl,
            "line_widget": line,
            "canvas": None,
            "inner_frame": grid_frame,
            "left_btn": None,
            "right_btn": None,
            "names": list(names),
            "widgets": sec_widgets,
            "scroll_offset": 0,
            "visible_count": 5,
        })

    def create_card(self, parent, name):
        info = self.get_all_services().get(name, {})
        icon = info.get("icon", "\U0001F4F0")
        url = info.get("url", "#")
        category = info.get("category", "")
        color = self.settings.get("card_colors", {}).get(name, info.get("color", Config.ACCENT))

        card = tk.Frame(parent, bg=Config.BG_CARD, relief="flat",
                        highlightbackground=Config.BORDER, highlightthickness=1,
                        cursor="hand2", width=Config.CARD_WIDTH, height=Config.CARD_HEIGHT)
        card.pack_propagate(False)

        top_area = tk.Frame(card, bg=color, height=160)
        top_area.pack(fill="x")
        top_area.pack_propagate(False)

        photo = self.get_logo(name)
        if photo:
            lbl = tk.Label(top_area, image=photo, bg=color, cursor="hand2")
            lbl.image = photo
            lbl.pack(expand=True)
        else:
            lbl = tk.Label(top_area, text=icon, font=("Segoe UI Emoji", 48),
                     bg=color, fg="white", cursor="hand2")
            lbl.pack(expand=True)

        info_area = tk.Frame(card, bg=Config.BG_CARD)
        info_area.pack(fill="both", expand=True, padx=12, pady=(10, 8))

        name_lbl = tk.Label(info_area, text=name, font=("Segoe UI", 14, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD, cursor="hand2",
                 wraplength=Config.CARD_WIDTH - 24)
        name_lbl.pack(anchor="w")

        cat_lbl = tk.Label(info_area, text=category.upper(), font=("Segoe UI", 9),
                 fg=Config.ACCENT, bg=Config.BG_CARD, cursor="hand2")
        cat_lbl.pack(anchor="w", pady=(2, 0))

        top_content = info.get("top_content", [])
        if top_content:
            for tc in top_content[:2]:
                tk.Label(info_area, text=f"\u25B8 {tc['title']}", font=("Segoe UI", 9),
                         fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, cursor="hand2",
                         anchor="w").pack(anchor="w", pady=(4, 0))

        if name in self.settings.get("favorites", []):
            tk.Label(card, text="\u2B50", font=("Segoe UI", 10),
                     fg="#ffd700", bg=Config.BG_CARD).place(relx=0.92, rely=0.03, anchor="ne")

        def on_click(e, n=name):
            self.on_card_click(n)

        def on_ctx(e, n=name):
            self.show_context_menu(e, n)

        def on_enter(e, c=card):
            c.configure(bg=Config.BG_CARD_HOVER, highlightbackground=Config.ACCENT, highlightthickness=2)
            self.sync_focus_to_card(c)

        def on_leave(e, c=card):
            c.configure(bg=Config.BG_CARD, highlightbackground=Config.BORDER, highlightthickness=1)

        card.bind("<Button-1>", on_click)
        card.bind("<Button-3>", on_ctx)
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        top_area.bind("<Button-1>", on_click)
        top_area.bind("<Button-3>", on_ctx)
        top_area.bind("<Enter>", on_enter)
        top_area.bind("<Leave>", on_leave)

        lbl.bind("<Button-1>", on_click)
        lbl.bind("<Button-3>", on_ctx)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)

        info_area.bind("<Button-1>", on_click)
        info_area.bind("<Button-3>", on_ctx)
        info_area.bind("<Enter>", on_enter)
        info_area.bind("<Leave>", on_leave)

        name_lbl.bind("<Button-1>", on_click)
        name_lbl.bind("<Button-3>", on_ctx)
        name_lbl.bind("<Enter>", on_enter)
        name_lbl.bind("<Leave>", on_leave)

        cat_lbl.bind("<Button-1>", on_click)
        cat_lbl.bind("<Button-3>", on_ctx)
        cat_lbl.bind("<Enter>", on_enter)
        cat_lbl.bind("<Leave>", on_leave)

        return card

    def sync_focus_to_tab(self, idx):
        """Mouse sobre a aba vira o foco oficial (confirmar segue a seta)."""
        try:
            self.nav_level = "tabs"
            self.focus_tab = idx
            self.update_all_focus()
        except Exception:
            pass

    def warp_to_focus(self):
        """Cursor do mouse vai para o item focado: cursor e foco viram
        UMA selecao so. So quando o Nexus esta em primeiro plano e sem
        modal/remoto (nunca puxa o cursor do usuario a toa)."""
        try:
            gp = self.gamepad
            if not gp or not gp.running or gp.joystick is None:
                return
            if gp.remote_active:
                return
            if top_modal(self) is not None:
                return
            if self.nexus_hwnd() != foreground_hwnd():
                return
            w = None
            if self.nav_level == "tabs":
                tids = list(self.nav_buttons.keys())
                if 0 <= self.focus_tab < len(tids):
                    w = self.nav_buttons[tids[self.focus_tab]]
            elif self.nav_level == "items" and self.sections:
                row = min(self.focus_mgr.focused_row, len(self.sections) - 1)
                sec = self.sections[row]
                if sec.get("canvas") is None:
                    j = self.focus_mgr.focused_col
                else:
                    j = sec.get("scroll_offset", 0) + self.focus_mgr.focused_col
                widgets = sec.get("widgets", [])
                if 0 <= j < len(widgets):
                    w = widgets[j]
            if w is None:
                return
            try:
                if not w.winfo_exists():
                    return
                w.update_idletasks()
                x = w.winfo_rootx() + w.winfo_width() // 2
                y = w.winfo_rooty() + w.winfo_height() // 2
            except Exception:
                return
            _set_cursor_pos(x, y)
        except Exception:
            pass

    def sync_focus_to_card(self, card):
        """Mouse/seta sobre o card vira o foco oficial: o confirmar do
        controle abre ONDE a seta esta, nao a selecao antiga."""
        try:
            pos = self.card_index.get(card)
            if not pos:
                return
            row, col = pos
            if row >= len(self.sections):
                return
            sec = self.sections[row]
            if sec.get("canvas") is not None:
                col = col - sec.get("scroll_offset", 0)
            if col < 0:
                return
            self.nav_level = "items"
            self.focus_mgr.focused_row = row
            self.focus_mgr.focused_col = col
            self.update_all_focus()
        except Exception:
            pass

    def on_card_click(self, name):
        self.ask_open_target(name)

    def ask_open_target(self, name):
        if self.open_dialog is not None and not self.open_dialog.closed:
            return
        self.open_dialog = OpenTargetDialog(self, name)

    def _pad_lookup(self, base_map, settings_key, btn_or_logical):
        try:
            gp = self.gamepad
            if isinstance(btn_or_logical, str):
                logical = btn_or_logical
            elif gp is not None:
                logical = gp.logical_for_raw(btn_or_logical)
            else:
                logical = normalize_pad_value(btn_or_logical)
            merged = dict(base_map)
            merged.update(self.settings.get(settings_key, {}))
            for action, val in merged.items():
                if normalize_pad_value(val) == logical:
                    return action
        except Exception:
            pass
        return None

    def nexus_action_for(self, btn_or_logical):
        return self._pad_lookup(DEFAULT_NEXUS_MAP, "pad_nexus", btn_or_logical)

    def remote_action_for(self, btn_or_logical):
        return self._pad_lookup(DEFAULT_REMOTE_MAP, "pad_remote", btn_or_logical)

    def pad_sensitivity(self):
        try:
            return min(30.0, max(4.0, float(self.settings.get(
                "pad_sensitivity", DEFAULT_PAD_SENSITIVITY))))
        except Exception:
            return float(DEFAULT_PAD_SENSITIVITY)

    def pad_scroll(self):
        """Encaixes de scroll por segundo com o analogico todo p/ o lado."""
        try:
            return min(20.0, max(2.0, float(self.settings.get(
                "pad_scroll", DEFAULT_PAD_SCROLL))))
        except Exception:
            return float(DEFAULT_PAD_SCROLL)

    def pad_deadzone(self):
        """Zona morta dos analogicos (0.05-0.40). Maior = melhor p/ BT com drift."""
        try:
            return min(0.40, max(0.05, float(self.settings.get(
                "pad_deadzone", 22)) / 100.0))
        except Exception:
            return 0.22

    def pad_devices(self):
        try:
            gp = self.gamepad
            return list(gp.devices) if gp else []
        except Exception:
            return []

    def current_pad_label(self):
        try:
            gp = self.gamepad
            return gp.device_label() if gp else ""
        except Exception:
            return ""

    def current_pad_layout(self):
        try:
            gp = self.gamepad
            return gp.layout if gp else "xbox"
        except Exception:
            return "xbox"

    def select_pad_device(self, pos):
        try:
            gp = self.gamepad
            if gp is None:
                return False
            ok = gp.select_device(pos)
            if ok and self.pad_window is not None and not self.pad_window.closed:
                self.pad_window.refresh()
            return ok
        except Exception:
            return False

    def start_pad_capture(self, section, action):
        self.pad_capture = {"section": section, "action": action}
        if self.pad_window is not None:
            self.pad_window.on_capture_start()

    def cancel_pad_capture(self):
        self.pad_capture = None
        if self.pad_window is not None:
            self.pad_window.on_capture_end()

    def finish_pad_capture(self, btn_or_logical):
        cap = self.pad_capture
        if not cap:
            return
        self.pad_capture = None
        section, action = cap["section"], cap["action"]
        key = "pad_nexus" if section == "nexus" else "pad_remote"
        base = DEFAULT_NEXUS_MAP if section == "nexus" else DEFAULT_REMOTE_MAP
        try:
            logical = (btn_or_logical if isinstance(btn_or_logical, str)
                       else normalize_pad_value(btn_or_logical))
            cur = dict(base)
            cur.update(self.settings.get(key, {}))
            for a, b in list(cur.items()):
                if a != action and normalize_pad_value(b) == logical:
                    old = normalize_pad_value(cur.get(action))
                    if old in LOGICAL_BUTTONS or str(old).startswith("raw"):
                        cur[a] = old  # troca: o dono antigo fica com o botao livre
                    else:
                        del cur[a]
            cur[action] = logical
            self.settings[key] = cur
            save_settings(self.settings)
        except Exception:
            pass
        if self.pad_window is not None:
            self.pad_window.on_capture_end()

    def enter_remote_mode(self, service, watch=None):
        """O controle passa a comandar o app/site aberto. So com controle ligado."""
        try:
            gp = self.gamepad
            if not gp or not gp.running:
                return
            gp.remote_active = True
            gp.remote_service = service
            gp.remote_watch_list = list(watch) if watch else list(REMOTE_WATCH.get(service, []))
            gp.remote_wheel_acc = [0.0, 0.0]
            gp.remote_watch_seen = False
            gp.remote_watch_missed = 0
            gp.remote_watch_count = 0
            gp.remote_hwnd = None
            gp.remote_enter_time = time.time()
            gp.remote_off = [0.0, 0.0, 0.0, 0.0]
            gp.remote_cal = []
            gp.hat_debounce.clear()
            gp.prev_buttons.clear()
            self.root.iconify()
        except Exception:
            pass

    def exit_remote_mode(self):
        # O navegador embutido e parte do Nexus: fecha junto (Back+Start
        # ou retorno). Apps externos (Spotify etc.) continuam abertos.
        for proc in list(BROWSER_PROCS):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
            try:
                BROWSER_PROCS.remove(proc)
            except Exception:
                pass
        try:
            self.browser_remote = None
        except Exception:
            pass
        try:
            gp = self.gamepad
            if gp:
                gp.remote_active = False
                gp.remote_service = None
                gp.remote_wheel_acc = [0.0, 0.0]
                gp.hat_debounce.clear()
                gp.prev_buttons.clear()
        except Exception:
            pass
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.update_idletasks()
        except Exception:
            pass

    def nexus_hwnd(self):
        try:
            return self.root.winfo_id()
        except Exception:
            return None

    def show_transition_splash(self, service):
        """Tela preta 'Nexus - servico' na transicao (efeito app unico)."""
        try:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.configure(bg="#000000")
            w, h = 520, 220
            win.update_idletasks()
            try:
                x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
            except Exception:
                x, y = 200, 150
            win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
            tk.Label(win, text="\u25C6 %s" % service, font=("Segoe UI", 24, "bold"),
                     fg=Config.ACCENT, bg="#000000").pack(expand=True)
            tk.Label(win, text=t("dlg_opening_nexus", self.lang), font=("Segoe UI", 13),
                     fg=Config.TEXT_SECONDARY, bg="#000000").pack(pady=(0, 24))
            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass
            return win
        except Exception:
            return None

    def enter_site_remote(self, proc, service, splash, born):
        try:
            if splash is not None:
                splash.destroy()
        except Exception:
            pass
        try:
            alive = proc.poll() is None
        except Exception:
            alive = False
        if alive:
            self.enter_remote_mode(service, watch=[])
            self.browser_remote = service
            self.monitor_browser_process(proc, service)
        else:
            try:
                self.opener.open_content(service)
            except Exception:
                pass
            self.enter_remote_mode(service, watch=BROWSER_WATCH)

    def borderless_new_app(self, before, tries=0):
        """Converte a janela nova do app externo p/ fullscreen sem bordas."""
        try:
            gp = self.gamepad
            if not gp or not gp.remote_active:
                return
        except Exception:
            return
        try:
            before_set = set(before)
            for hwnd, _pid, _title in _top_level_windows():
                if hwnd not in before_set:
                    if force_borderless_fullscreen(hwnd, self.nexus_hwnd()):
                        try:
                            gp.remote_hwnd = hwnd  # vigia rapida: volta em ~0,5s
                            gp.remote_watch_seen = True
                            gp.remote_watch_missed = 0
                        except Exception:
                            pass
                        return
        except Exception:
            pass
        if tries < 4:
            try:
                self.root.after(2500, lambda: self.borderless_new_app(before, tries + 1))
            except Exception:
                pass

    def browser_nav_active(self):
        """Remoto comandando o navegador embutido (modo console nos quadros)."""
        try:
            gp = self.gamepad
            return bool(gp and gp.remote_active
                        and getattr(self, "browser_remote", None)
                        and any(p.poll() is None for p in BROWSER_PROCS))
        except Exception:
            return False

    def monitor_browser_process(self, proc, service):
        """Sai do remoto quando o navegador embutido fechar. Se ele morrer
        rapido (<5s, ex. WebView2 indisponivel), cai para o navegador externo."""
        born = time.time()

        def _watch():
            try:
                proc.wait(timeout=6000)
            except Exception:
                pass
            try:
                self.root.after(0, self._browser_closed, proc, service, born)
            except Exception:
                pass

        threading.Thread(target=_watch, daemon=True).start()

    def _browser_closed(self, proc, service, born):
        try:
            if proc in BROWSER_PROCS:
                BROWSER_PROCS.remove(proc)
        except Exception:
            pass
        try:
            if getattr(self, "browser_remote", None) == service:
                self.browser_remote = None
        except Exception:
            pass
        try:
            elapsed = time.time() - born
        except Exception:
            elapsed = 999.0
        gp = getattr(self, "gamepad", None)
        still_remote = bool(gp and gp.remote_active
                            and gp.remote_service == service)
        if elapsed < 5.0:
            try:
                self.opener.open_content(service)
            except Exception:
                pass
            if still_remote:
                try:
                    gp.remote_watch_list = list(BROWSER_WATCH)
                    gp.remote_enter_time = time.time()
                except Exception:
                    pass
            else:
                self.enter_remote_mode(service, watch=BROWSER_WATCH)
            return
        if still_remote:
            self.exit_remote_mode()

    def _on_focus_in(self):
        # Usuario voltou ao Nexus (Alt+Tab/clique): sai do modo remoto.
        # Ignora o foco dos primeiros 2s (restos da troca dialogo->app).
        try:
            gp = self.gamepad
            if gp and gp.remote_active:
                if time.time() - getattr(gp, "remote_enter_time", 0) < 2.0:
                    return
                self.exit_remote_mode()
        except Exception:
            pass

    # ===================== CONTEXT MENU =====================
    def show_context_menu(self, event, name):
        menu = tk.Menu(self.root, tearoff=0, bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                        activebackground=Config.ACCENT, activeforeground="white",
                        font=("Segoe UI", 12), bd=0)
        menu.add_command(label=f"\u25B6 {t('ctx_open', self.lang)}", command=lambda: self.on_card_click(name))
        if name in self.settings.get("favorites", []):
            menu.add_command(label=f"\u2716 {t('ctx_remove_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
        else:
            menu.add_command(label=f"\u2B50 {t('ctx_add_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
        menu.add_separator()
        menu.add_command(label=f"\U0001F5BC {t('ctx_change_logo', self.lang)}", command=lambda: self.change_logo(name))
        menu.add_separator()
        menu.add_command(label=f"\U0001F5D1 {t('ctx_delete', self.lang)}", command=lambda: self.delete_streaming(name))
        menu.add_command(label=f"\U0001F4CB {t('ctx_copy_url', self.lang)}",
                         command=lambda: self.root.clipboard_append(
                             self.get_all_services().get(name, {}).get("url", "")))
        menu.tk_popup(event.x_root, event.y_root)

    def toggle_favorite(self, name):
        favs = self.settings.get("favorites", [])
        if name in favs:
            favs.remove(name)
        else:
            favs.append(name)
        self.settings["favorites"] = favs
        save_settings(self.settings)
        self.refresh_ui()

    def delete_streaming(self, name):
        def _yes(menu):
            custom = self.settings.get("custom_streamings", {})
            if name in custom:
                del custom[name]
                self.settings["custom_streamings"] = custom
            else:
                hidden = self.settings.get("hidden_streamings", [])
                if name not in hidden:
                    hidden.append(name)
                self.settings["hidden_streamings"] = hidden
            favs = self.settings.get("favorites", [])
            if name in favs:
                favs.remove(name)
                self.settings["favorites"] = favs
            save_settings(self.settings)
            self.refresh_ui()
            menu.close()

        menu = NexusMenuWindow(self, t("delete_confirm", self.lang), [],
                               subtitle=f"{t('delete_question', self.lang)} '{name}'?",
                               icon="\U0001F5D1", width=460)
        menu.set_options([(t("ctx_delete", self.lang),
                           lambda: _yes(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def show_info_message(self, title, message):
        menu = NexusMenuWindow(self, title, [], subtitle=message,
                               icon="\u2139", width=440)
        menu.set_options([(t("sidebar_close", self.lang), menu.close)])

    def change_logo(self, name):
        filepath = filedialog.askopenfilename(
            title=f"Logo de {name}",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.ico"), ("Todas", "*.*")])
        if filepath:
            ext = os.path.splitext(filepath)[1].lower()
            dest = os.path.join(IMAGES_DIR, f"{name}_logo{ext}")
            try:
                copy2(filepath, dest)
            except:
                dest = filepath
            custom = self.settings.get("custom_streamings", {})
            if name not in custom:
                custom[name] = {}
            custom[name]["image"] = dest
            self.settings["custom_streamings"] = custom
            save_settings(self.settings)
            self.refresh_ui()

    # ===================== SIDEBAR =====================
    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.close_sidebar()
        else:
            self.open_sidebar()

    def open_sidebar(self):
        self.sidebar_visible = True
        self.sidebar_menu_index = 0
        now = datetime.now()
        self.sidebar_time.config(text=now.strftime("%H:%M"))
        self.sidebar_date.config(text=now.strftime("%A, %d/%m/%Y"))
        self.sidebar.place(x=0, y=0, relheight=1)
        self.sidebar.lift()
        self.update_sidebar_focus()

    def close_sidebar(self):
        self.sidebar_visible = False
        self.sidebar.place(x=-Config.SIDEBAR_WIDTH, y=0, relheight=1)

    def show_gamepad_info(self):
        self.close_sidebar()
        if self.pad_window is not None and not self.pad_window.closed:
            try:
                self.pad_window.win.lift()
            except Exception:
                pass
            return
        GamepadConfigWindow(self)

    def open_keyboard_sidebar(self):
        self.close_sidebar()
        self.open_keyboard()

    def open_keyboard(self, entry=None, mode="auto"):
        try:
            kb = self.kb_window
            if kb is not None and not kb.closed:
                try:
                    kb.win.lift()
                except Exception:
                    pass
                return
        except Exception:
            pass
        numeric = False
        if mode == "numeric":
            numeric = True
        elif mode != "text":
            numeric = sniff_numeric_entry(entry)
        NexusKeyboard(self, entry, numeric=numeric)

    def bind_keyboard_popup(self, entry, mode="auto"):
        """Clique no campo abre o teclado sozinho (letras ou numerico)."""
        try:
            entry.kb_mode = mode
            entry.bind("<Button-1>",
                       lambda e, ent=entry: self._entry_clicked(ent), add="+")
        except Exception:
            pass

    def _entry_clicked(self, entry):
        try:
            if self.kb_window is not None and not self.kb_window.closed:
                return
            mode = getattr(entry, "kb_mode", "auto") or "auto"
            self.open_keyboard(entry, mode=mode)
        except Exception:
            pass

    def confirm_clear_browser_profile(self):
        self.close_sidebar()
        if browser_running():
            self.show_info_message(t("msg_warning", self.lang),
                                   t("cache_in_use", self.lang))
            return
        try:
            size_mb = browser_profile_size() / 1048576.0
        except Exception:
            size_mb = 0.0
        menu = NexusMenuWindow(self, t("settings_clear_cache", self.lang), [],
                               subtitle=t("cache_confirm", self.lang) % size_mb,
                               icon="\U0001F9F9", width=480)
        menu.set_options([(t("cache_clear_yes", self.lang),
                           lambda: self.do_clear_browser_profile(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def do_clear_browser_profile(self, menu):
        ok = clear_browser_profile()
        try:
            menu.close()
        except Exception:
            pass
        self.show_info_message(
            t("msg_success", self.lang) if ok else t("msg_warning", self.lang),
            t("cache_cleared", self.lang) if ok else t("cache_in_use", self.lang))

    # ===================== ADD STREAMING =====================
    def render_add_streaming(self):
        self.close_sidebar()
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.all_cards = []
        self.card_widgets = []

        tk.Label(self.scroll_frame, text=f"\U0001F4FA {t('add_title', self.lang)}",
                 font=("Segoe UI", 26, "bold"), fg=Config.TEXT_PRIMARY,
                 bg=Config.BG_PRIMARY).pack(pady=(40, 30))

        form = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        form.pack()

        labels = [t("add_name", self.lang), t("add_url", self.lang),
                  t("add_category", self.lang), t("add_emoji", self.lang),
                  t("add_logo", self.lang)]
        defaults = ["Meu Streaming", "https://", "Filmes", "\U0001F4F0", ""]
        self.add_entries = {}

        for i, (label, default) in enumerate(zip(labels, defaults)):
            tk.Label(form, text=label, font=("Segoe UI", 14),
                     fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY).grid(
                row=i, column=0, sticky="w", pady=10, padx=(0, 15))
            if label == t("add_logo", self.lang):
                bf = tk.Frame(form, bg=Config.BG_PRIMARY)
                bf.grid(row=i, column=1, sticky="w")
                e = tk.Entry(bf, font=("Segoe UI", 12), width=25,
                             bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                             insertbackground=Config.ACCENT, bd=0,
                             highlightbackground=Config.BORDER, highlightthickness=1)
                e.pack(side="left")
                tk.Button(bf, text="...", font=("Segoe UI", 12),
                          bg=Config.ACCENT, fg="white", relief="flat", cursor="hand2",
                          command=lambda ent=e: self.browse_image(ent), padx=8).pack(side="left", padx=5)
                self.add_entries[label] = e
                self.bind_keyboard_popup(e, mode="text")
            else:
                e = tk.Entry(form, font=("Segoe UI", 14), width=30,
                             bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                             insertbackground=Config.ACCENT, bd=0,
                             highlightbackground=Config.BORDER, highlightthickness=1)
                e.grid(row=i, column=1, pady=10)
                e.insert(0, default)
                self.add_entries[label] = e
                self.bind_keyboard_popup(e)
                tk.Button(form, text="\u2328", font=("Segoe UI", 12),
                          bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY,
                          relief="flat", bd=0, cursor="hand2", padx=8,
                          command=lambda ent=e: self.open_keyboard(ent)).grid(
                    row=i, column=2, padx=(8, 0))

        tk.Button(form, text=f"{t('add_submit', self.lang)} \u2192", font=("Segoe UI", 15, "bold"),
                  bg=Config.ACCENT, fg="white", activebackground=Config.ACCENT_GLOW,
                  relief="flat", cursor="hand2", command=self.add_new_streaming,
                  padx=30, pady=10).grid(row=len(labels), column=0, columnspan=2, pady=30)

        tk.Button(self.scroll_frame, text=f"\u2190 {t('add_back', self.lang)}", font=("Segoe UI", 14),
                  bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY, relief="flat",
                  cursor="hand2", command=lambda: self.switch_tab(self.current_tab),
                  padx=20, pady=8).pack(pady=10)

    def browse_image(self, entry):
        fp = filedialog.askopenfilename(
            title="Escolher logo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.ico"), ("Todas", "*.*")])
        if fp:
            entry.delete(0, "end")
            entry.insert(0, fp)

    def add_new_streaming(self):
        name = self.add_entries.get(t("add_name", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        url = self.add_entries.get(t("add_url", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        cat = self.add_entries.get(t("add_category", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        icon = self.add_entries.get(t("add_emoji", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        img = self.add_entries.get(t("add_logo", self.lang), type("x", (), {"get": lambda: ""})).get().strip()

        if not name or not url:
            self.show_info_message(t("msg_warning", self.lang), t("add_warning", self.lang))
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        custom = self.settings.get("custom_streamings", {})
        data = {"url": url, "category": cat or "Filmes", "icon": icon or "\U0001F4F0",
                "color": Config.ACCENT, "deep_link": "", "url_template": url,
                "top_content": []}
        if img and os.path.exists(img):
            ext = os.path.splitext(img)[1].lower()
            dest = os.path.join(IMAGES_DIR, f"{name}_logo{ext}")
            try:
                copy2(img, dest)
                data["image"] = dest
            except:
                data["image"] = img
        custom[name] = data
        self.settings["custom_streamings"] = custom
        if name not in self.settings.get("favorites", []):
            self.settings["favorites"].append(name)
        save_settings(self.settings)
        self.show_info_message(t("msg_success", self.lang), f'"{name}" {t("add_success", self.lang)}')
        self.refresh_ui()

    # ===================== QA OVERLAY =====================
    def close_qa(self):
        self.qa_visible = False
        self.dim_overlay.place_forget()
        self.qa_frame.place_forget()

    # ===================== RESOLUTION =====================
    def open_resolution(self):
        self.close_sidebar()
        menu = NexusMenuWindow(self, t("res_title", self.lang),
                               [], icon="\U0001F5A9")
        cur = self.settings.get("resolution_mode", "fullscreen")
        options = [
            (t("res_fullscreen", self.lang), "fullscreen"),
            ("1920x1080", "1920x1080"),
            ("1400x900", "1400x900"),
            ("1280x720", "1280x720"),
            (t("res_windowed", self.lang), "windowed"),
        ]
        opts = [((("\u2713 " if mode == cur else "") + text),
                 lambda m=mode: self.set_resolution(m, menu)) for text, mode in options]
        opts.append((t("res_close", self.lang), menu.close))
        menu.set_options(opts)

    def set_resolution(self, mode, win=None):
        self.settings["resolution_mode"] = mode
        if mode == "fullscreen":
            self.root.attributes("-fullscreen", True)
        elif mode == "windowed":
            self.root.attributes("-fullscreen", False)
            self.root.geometry("1200x800")
        else:
            self.root.attributes("-fullscreen", False)
            self.root.geometry(mode)
        save_settings(self.settings)
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    # ===================== THEME =====================
    def open_theme_picker(self):
        self.close_sidebar()
        colors = [("#7c4dff", "Purple"), ("#e94560", "Red"), ("#00bcd4", "Cyan"),
                  ("#00c853", "Green"), ("#ffd600", "Yellow"), ("#ff4081", "Pink"),
                  ("#ff6d00", "Orange"), ("#c44100", "Steam")]
        menu = NexusMenuWindow(self, t("theme_title", self.lang),
                               [], icon="\U0001F3A8", width=480, cols=4)
        opts = []
        for color, label in colors:
            opts.append((label, lambda col=color: self.apply_theme(col, menu),
                         {"bg": color,
                          "fg": "white" if color != "#ffd600" else "black",
                          "activebackground": color, "width": 8}))
        opts.append((t("theme_close", self.lang), menu.close,
                     {"width": 8}))
        menu.set_options(opts, opt_font=10)

    def apply_theme(self, color, win=None):
        global Config
        Config.ACCENT = color
        Config.ACCENT_GLOW = color
        self.refresh_ui()
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    # ===================== LANGUAGE =====================
    def open_language_picker(self):
        self.close_sidebar()
        menu = NexusMenuWindow(self, t("lang_title", self.lang),
                               [], icon="\U0001F310", width=420)
        languages = [
            ("pt-br", "\U0001F1E7\U0001F1F7  Portugues (BR)"),
            ("en", "\U0001F1EC\U0001F1E7  English"),
        ]
        opts = [((("\u2713 " if code == self.lang else "") + label),
                 lambda c=code: self.set_language(c, menu)) for code, label in languages]
        opts.append((t("lang_close", self.lang), menu.close))
        menu.set_options(opts)

    def set_language(self, lang_code, win=None):
        self.lang = lang_code
        self.settings["language"] = lang_code
        save_settings(self.settings)
        self.refresh_ui()
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    # ===================== MISC =====================
    WEEKDAY_KEYS = {
        0: "day_monday", 1: "day_tuesday", 2: "day_wednesday",
        3: "day_thursday", 4: "day_friday", 5: "day_saturday", 6: "day_sunday",
    }

    def _get_translated_weekday(self):
        key = self.WEEKDAY_KEYS.get(datetime.now().weekday(), "day_monday")
        return t(key, self.lang)

    def update_clock(self):
        now = datetime.now()
        try:
            if self.clock_label:
                self.clock_label.config(text=now.strftime("%H:%M"))
        except:
            pass
        try:
            if self.sidebar_time:
                self.sidebar_time.config(text=now.strftime("%H:%M"))
        except:
            pass
        try:
            if self.sidebar_date:
                weekday = self._get_translated_weekday()
                self.sidebar_date.config(text=f"{weekday}, {now.strftime('%d/%m/%Y')}")
        except:
            pass
        self.root.after(10000, self.update_clock)

    def toggle_fullscreen(self):
        current = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not current)

    def minimize_app(self):
        try:
            self.root.iconify()
        except Exception:
            pass

    def confirm_quit(self):
        menu = NexusMenuWindow(self, t("quit_title", self.lang), [],
                               subtitle=t("quit_question", self.lang),
                               icon="\U0001F6AA", width=440)
        menu.set_options([(t("quit_no", self.lang), menu.close),
                          (t("quit_yes", self.lang),
                           lambda: self.quit_app(menu),
                           {"bg": "#e94560", "fg": "white",
                            "activebackground": "#ff4570"})])

    def quit_app(self, menu=None):
        try:
            if menu is not None:
                menu.close()
        except Exception:
            pass
        for proc in list(BROWSER_PROCS):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        try:
            gp = getattr(self, "gamepad", None)
            if gp is not None:
                gp.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def refresh_ui(self):
        self.build_ui()


# ===================== MAIN =====================
if __name__ == "__main__":
    try:
        # AppID proprio: a barra de tarefas mostra a logo do Nexus
        # em vez de agrupar/icone generico do python.exe.
        # (v2 = nova entrada no cache de icones do Explorer)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "NexusStreamingHub.BigPicture.2")
    except Exception:
        pass
    root = tk.Tk()
    app = BigPictureApp(root)
    root.mainloop()
