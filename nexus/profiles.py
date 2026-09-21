# -*- coding: utf-8 -*-
"""Perfis locais do Nexus (login sem nuvem).

Cada perfil guarda seu proprio snapshot de settings em profiles/<nome>.json
e opcionalmente um PIN (sha256). Sem login = convidado ("_guest", tambem
persistido). Trocar de perfil salva o atual e carrega o novo na hora.
"""

import copy
import hashlib
import hmac
import json
import os
import re

try:
    from .paths import BASE_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
GUEST = "_guest"


def profiles_dir():
    try:
        os.makedirs(PROFILES_DIR, exist_ok=True)
    except Exception:
        pass
    return PROFILES_DIR


def _safe_name(name):
    name = (name or "").strip()
    name = re.sub(r"[^\w\-. ]+", "", name, flags=re.UNICODE).strip()
    return name[:24]


def _path(name):
    return os.path.join(profiles_dir(), _safe_name(name) + ".json")


def list_profiles():
    """Nomes de perfis (sem o convidado), ordenados."""
    out = []
    try:
        for f in os.listdir(profiles_dir()):
            if f.endswith(".json") and not f.startswith("_"):
                out.append(f[:-5])
    except Exception:
        pass
    return sorted(out)


def load_profile_data(name):
    try:
        with open(_path(name), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_profile_data(name, data):
    try:
        with open(_path(name), "w", encoding="utf-8") as fh:
            json.dump(data or {}, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def pin_hash(pin):
    pin = (pin or "").strip()
    if not pin:
        return ""
    return hashlib.sha256(("nexus-pin:" + pin).encode("utf-8")).hexdigest()


def profile_has_pin(name):
    try:
        return bool(load_profile_data(name).get("pin_hash", ""))
    except Exception:
        return False


def verify_pin(name, pin):
    try:
        want = (load_profile_data(name).get("pin_hash", "") or "")
        if not want:
            return True
        got = pin_hash(pin)
        return bool(got) and hmac.compare_digest(got, want)
    except Exception:
        return False


def create_profile(name, pin, settings_snapshot):
    """Cria perfil (nome único, PIN opcional). Retorna (ok, erro_pt)."""
    name = _safe_name(name)
    if not name or name.startswith("_"):
        return False, "nome inválido"
    if os.path.exists(_path(name)):
        return False, "esse nome já existe"
    pin = (pin or "").strip()
    if pin and (not pin.isdigit() or len(pin) < 4 or len(pin) > 8):
        return False, "PIN de 4 a 8 dígitos (ou vazio)"
    data = {"pin_hash": pin_hash(pin) if pin else "",
            "settings": copy.deepcopy(settings_snapshot or {})}
    if not save_profile_data(name, data):
        return False, "não consegui salvar"
    return True, ""


def snapshot_settings(app):
    try:
        return copy.deepcopy(dict(app.settings))
    except Exception:
        return {}


def switch_profile(app, name, save_fn=None):
    """Troca app.profile para `name` (None = convidado).

    Salva as settings atuais no perfil antigo e carrega as do novo.
    Retorna True. Nunca levanta exceção.
    """
    try:
        cur = getattr(app, "profile", None)
        snap = snapshot_settings(app)
        if cur:
            data = load_profile_data(cur)
            data["settings"] = snap
            save_profile_data(cur, data)
        else:
            save_profile_data(GUEST, {"pin_hash": "",
                                      "settings": snap})
        target = name or GUEST
        data = load_profile_data(target)
        settings = data.get("settings", {}) or {}
        if isinstance(settings, dict) and settings:
            try:
                app.settings = settings
            except Exception:
                pass
        # Perfil vazio/estreante: mantem as settings atuais como base.
        app.profile = name or None
        try:
            if save_fn is not None:
                save_fn(app.settings)
            else:
                from .config import save_settings as _save
                _save(app.settings)
        except Exception:
            pass
        try:
            app.lang = app.settings.get("language", "pt-br")
        except Exception:
            pass
        try:
            app.refresh_ui()
        except Exception:
            pass
        return True
    except Exception:
        return False


def require_login(app, feature="este recurso"):
    """Gate p/ funções que exigem login. True = pode seguir."""
    try:
        if getattr(app, "profile", None):
            return True
    except Exception:
        pass
    try:
        lang = getattr(app, "lang", "pt-br") or "pt-br"
        if str(lang).startswith("pt"):
            app.show_info_message("Login necessário",
                                  "%s precisa de login.\n"
                                  "Abra ☰ > Perfil e entre ou crie um." % feature)
        else:
            app.show_info_message("Login required",
                                  "%s needs login.\n"
                                  "Open ☰ > Profile and sign in or create one." % feature)
    except Exception:
        pass
    return False
