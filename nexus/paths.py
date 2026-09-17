# -*- coding: utf-8 -*-
"""Caminhos base e perfil do navegador embutido.

Extraido de bigpicture.py sem mudar comportamento.
"""

import json
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
IMAGES_DIR = os.path.join(BASE_DIR, "streaming_images")
GAMES_DIR = os.path.join(BASE_DIR, "games")
DATABASE_FILE = os.path.join(BASE_DIR, "nexus.db")
NEXUS_BROWSER_FILE = os.path.join(BASE_DIR, "nexus_browser.py")
NEXUS_BROWSER_EXE = os.path.join(BASE_DIR, "nexus_browser.exe")

# Processos do navegador embutido (para detectar saida / limpar perfil).
BROWSER_PROCS = []


def legacy_profile_dir():
    """Caminho antigo no C (só leitura p/ migração)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Nexus", "browser_profile")


def configured_profile_dir():
    """Override do perfil: env NEXUS_PROFILE_DIR > settings.json > ''."""
    try:
        env = (os.environ.get("NEXUS_PROFILE_DIR") or "").strip()
        if env:
            return env
    except Exception:
        pass
    try:
        if os.path.isfile(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            custom = (data.get("browser_profile_dir") or "").strip()
            if custom:
                return custom
    except Exception:
        pass
    return ""


def nexus_profile_dir():
    """Perfil do navegador embutido (logins, cookies, senhas).

    Configurável p/ tirar do C pequeno: settings.json -> browser_profile_dir
    ou env NEXUS_PROFILE_DIR. Cai no caminho legado do C se vazio.
    """
    try:
        custom = configured_profile_dir()
        if custom:
            d = os.path.abspath(os.path.expandvars(custom))
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            return d
    except Exception:
        pass
    d = legacy_profile_dir()
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
