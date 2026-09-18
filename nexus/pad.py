# -*- coding: utf-8 -*-
"""Mapeamento logico do gamepad + watch lists (extraido sem alteracao)."""

import re

# Processos para detectar que o app foi fechado (saida automatica do remoto).
# So nomes confiaveis: se o processo nunca aparecer, nao ha saida automatica
# (o usuario sai com Back+Start).
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

# Botoes LOGICOS (posicao fisica, padrao SDL): south = botao de baixo,
# east = direita, west = esquerda, north = cima. Valem para Xbox,
# PlayStation, Switch e genericos.
LOGICAL_BUTTONS = ("south", "east", "west", "north", "lb", "rb",
                   "back", "start", "guide", "l3", "r3", "l2", "r2")

# Tabela raw padrao (Xbox / ordem classica). Indices salvos antigos usam ela.
XBOX_RAW = {"south": 0, "east": 1, "west": 2, "north": 3, "lb": 4,
            "rb": 5, "back": 6, "start": 7, "l3": 8, "r3": 9}
XBOX_POSITIONAL = {v: k for k, v in XBOX_RAW.items()}

# Nomes por layout (mesma posicao fisica, nome de cada familia).
PAD_LAYOUT_NAMES = {
    "xbox": {"south": "A", "east": "B", "west": "X", "north": "Y",
             "lb": "LB", "rb": "RB", "back": "Back", "start": "Start",
             "guide": "Guide", "l3": "L3", "r3": "R3",
             "l2": "LT", "r2": "RT"},
    "playstation": {"south": "\u2715", "east": "\u25CB", "west": "\u25A1",
                    "north": "\u25B3", "lb": "L1", "rb": "R1",
                    "back": "Share", "start": "Options", "guide": "PS",
                    "l3": "L3", "r3": "R3", "l2": "L2", "r2": "R2"},
    "switch": {"south": "B", "east": "A", "west": "Y", "north": "X",
               "lb": "L", "rb": "R", "back": "-", "start": "+",
               "guide": "Home", "l3": "L3", "r3": "R3",
               "l2": "ZL", "r2": "ZR"},
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
# Y (north) vem LIVRE de fabrica: fullscreen nao e universal
# (vira letra em campo de texto) - quem quiser, remapeia.
DEFAULT_NEXUS_MAP = {"select": 0, "back": 1, "cards": 2,
                     "sidebar": 3, "tab_prev": 4, "tab_next": 5,
                     "notif": 7}
DEFAULT_REMOTE_MAP = {"click_left": 0, "back": 1, "click_right": 2,
                       "app_tab_prev": 4, "app_tab_next": 5,
                       "space": 8, "enter": 9, "play_pause": 6,
                       "vol_down": "l2", "vol_up": "r2"}
NEXUS_ACTION_ORDER = ["select", "back", "cards", "sidebar", "tab_prev", "tab_next",
                      "notif"]
REMOTE_ACTION_ORDER = ["click_left", "click_right", "enter", "back",
                       "space", "fullscreen", "vol_down", "vol_up",
                       "play_pause", "next_track", "prev_track",
                       "app_tab_prev", "app_tab_next", "keyboard"]
DEFAULT_PAD_SENSITIVITY = 12
DEFAULT_PAD_SCROLL = 8
DEFAULT_PAD_DEADZONE = 22
PAD_PROFILE_SLOTS = (1, 2, 3)


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
