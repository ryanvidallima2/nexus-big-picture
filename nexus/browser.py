# -*- coding: utf-8 -*-
"""Navegador embutido como processo separado (extraido sem alteracao)."""

import os
import subprocess
import sys
import urllib.parse

# Import tardio de proposito: webview puxa pythonnet (~130ms) e so faz
# falta ao abrir o Site. browser_available()/open importam sob demanda.
_pywebview = None
WEBVIEW_AVAILABLE = False


def _ensure_webview():
    """Importa o pywebview na primeira necessidade. True se disponivel."""
    global _pywebview, WEBVIEW_AVAILABLE
    if WEBVIEW_AVAILABLE:
        return True
    try:
        import webview as _mod
    except ImportError:
        return False
    _pywebview = _mod
    WEBVIEW_AVAILABLE = True
    return True

from .paths import NEXUS_BROWSER_EXE, NEXUS_BROWSER_FILE, nexus_profile_dir


# O botao Site abre o servico numa janela do proprio Nexus (pywebview +
# Edge WebView2) em vez do navegador externo. Roda como processo separado
# para nao travar o loop do tkinter.
def browser_available():
    if os.path.exists(NEXUS_BROWSER_EXE):
        return True  # release .exe: navegador ja compilado
    return bool(_ensure_webview()) and os.path.exists(NEXUS_BROWSER_FILE)


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
    # Propaga o perfil configurado (disco D) p/ o processo filho
    try:
        child_env = dict(os.environ)
        child_env["NEXUS_PROFILE_DIR"] = nexus_profile_dir()
        child_env["WEBVIEW2_USER_DATA_FOLDER"] = nexus_profile_dir()
    except Exception:
        child_env = None
    if os.path.exists(NEXUS_BROWSER_EXE):
        try:
            return subprocess.Popen(
                [NEXUS_BROWSER_EXE, url, title, pad_label or ""],
                env=child_env,
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
            env=child_env,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return None
