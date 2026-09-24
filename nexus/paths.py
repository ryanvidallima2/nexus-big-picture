# -*- coding: utf-8 -*-
"""Caminhos base e perfil do navegador embutido.

Extraido de bigpicture.py sem mudar comportamento.
"""

import json
import os
import re
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
IMAGES_DIR = os.path.join(BASE_DIR, "streaming_images")
GAMES_DIR = os.path.join(BASE_DIR, "games")
DATABASE_FILE = os.path.join(BASE_DIR, "nexus.db")
# Identidade visual propria (Fase 2): icones originais por categoria,
# rastreados no git e embarcados no distribuivel (fallback de get_logo).
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")
CATEGORY_ICONS = {
    "Filmes": "cat_filmes.png",
    "Musica": "cat_musica.png",
    "Videos": "cat_videos.png",
    "Games": "cat_games.png",
}
DEFAULT_ICON = "nexus_default.png"
# Serie 2 (temas genericos p/ escolha de logo): (arquivo, rotulo_pt,
# rotulo_en). Formas originais, sem marca de terceiro.
EXTRA_ICONS = [
    ("cat_anime.png", "Anime", "Anime"),
    ("cat_sports.png", "Esportes", "Sports"),
    ("cat_news.png", "Notícias", "News"),
    ("cat_kids.png", "Infantil", "Kids"),
    ("cat_docs.png", "Documentários", "Documentaries"),
    ("cat_horror.png", "Terror", "Horror"),
    ("cat_comedy.png", "Comédia", "Comedy"),
    ("cat_live.png", "Ao vivo", "Live"),
    ("cat_podcast.png", "Podcast", "Podcast"),
    ("cat_fitness.png", "Fitness", "Fitness"),
    ("cat_cinema.png", "Cinema", "Cinema"),
    ("cat_serie.png", "Séries", "Series"),
    ("cat_fone.png", "Fones", "Headphones"),
    ("cat_radio.png", "Rádio", "Radio"),
    ("cat_camera.png", "Câmera", "Camera"),
    ("cat_play.png", "Play", "Play"),
    ("cat_dpad.png", "Controle", "Gamepad"),
    ("cat_dado.png", "Dado", "Dice"),
]


def category_icon_path(category):
    """PNG original Nexus p/ a categoria (ou o neutro). '' se ausente."""
    try:
        filename = CATEGORY_ICONS.get(category, DEFAULT_ICON)
        p = os.path.join(ICONS_DIR, filename)
        if os.path.isfile(p):
            return p
        fallback = os.path.join(ICONS_DIR, DEFAULT_ICON)
        if os.path.isfile(fallback):
            return fallback
    except Exception:
        pass
    return ""


def preset_icon_files():
    """[(arquivo, rotulo_pt, rotulo_en)] dos icones pre-definidos p/
    escolher no painel de logo. So arquivos conhecidos (sem traversal)."""
    out = []
    try:
        from .i18n import cat_label as _cat_label
    except Exception:
        _cat_label = None
    try:
        for cat, fn in CATEGORY_ICONS.items():
            p = os.path.join(ICONS_DIR, fn)
            if not os.path.isfile(p):
                continue
            if _cat_label is not None:
                try:
                    out.append((fn, _cat_label(cat, "pt-br"),
                                _cat_label(cat, "en")))
                    continue
                except Exception:
                    pass
            out.append((fn, cat, cat))
        for fn, pt, en in EXTRA_ICONS:
            if os.path.isfile(os.path.join(ICONS_DIR, fn)):
                out.append((fn, pt, en))
        p = os.path.join(ICONS_DIR, DEFAULT_ICON)
        if os.path.isfile(p) and all(f != DEFAULT_ICON for f, _p, _e in out):
            out.append((DEFAULT_ICON, "Padrão", "Default"))
    except Exception:
        pass
    return out


def preset_icon_names():
    """S so os nomes de arquivo validos (validacao do icon_asset)."""
    try:
        return {fn for fn, _p, _e in preset_icon_files()}
    except Exception:
        return set()
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


def service_key(name):
    """Slug seguro p/ pasta do perfil (a-z0-9, resto vira _)."""
    try:
        slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
        return slug[:48] or "app"
    except Exception:
        return "app"


def service_profile_dir(service):
    """Perfil SOLO do servico (logins/cookies isolados, limpavel sozinho).
    Sem servico: o compartilhado de sempre (compat)."""
    base = nexus_profile_dir()
    try:
        if service:
            d = os.path.join(base, service_key(service))
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            return d
    except Exception:
        pass
    return base


def service_profile_size(service):
    total = 0
    try:
        d = service_profile_dir(service)
        for dirpath, _dirnames, files in os.walk(d):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def clear_service_profile(service):
    """Apaga logins/cookies/cache SO deste servico. False se em uso."""
    if browser_running():
        return False
    try:
        d = service_profile_dir(service)
        base = os.path.abspath(nexus_profile_dir())
        if os.path.abspath(d) == base:
            return False  # sem slug: nunca apagar a base por aqui
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        return True
    except Exception:
        return False


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
