# -*- coding: utf-8 -*-
"""Localizacao/abertura/instalacao de apps (extraido sem alteracao)."""

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import winreg
import xml.etree.ElementTree as ET

from .util import _norm


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
