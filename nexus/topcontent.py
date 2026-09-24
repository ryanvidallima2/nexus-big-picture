# -*- coding: utf-8 -*-
"""Top 3 online por streaming (descricoes vivas nos cards).

- Cache em disco (topcache.json): {servico: {"titles": [...], "ts": epoch}}.
- refresh_all() roda em thread no boot e atualiza o que estiver vencido
  (TTL de 30 dias); sem internet ou com falha, mantem o cache antigo.
- get_top() nunca faz rede: devolve cache fresco ou o estatico do
  STREAMINGS_DB (fallback). Formato igual ao do DB: [{"title": ...}].
- FETCHERS: fontes gratuitas sem chave (Deezer e Dailymotion tem API
  publica estavel). Spotify virou SPA (CSV morto) e o YouTube exigiria
  chave oficial — esses ficam no estatico. P/ adicionar fonte nova,
  escreva _fetch_*() e registre no dict.
"""

import json
import os
import time
import urllib.request

try:
    from .paths import BASE_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOPCACHE_FILE = os.path.join(BASE_DIR, "topcache.json")
TOP_TTL = 30 * 24 * 3600
TOP_N = 3
_TITLE_LIMIT = 30
_UA = "NexusBigPicture/5.4 (uso pessoal local; Python-urllib)"


def _clean(title, limit=_TITLE_LIMIT):
    try:
        s = " ".join(str(title or "").split())
        if len(s) > limit:
            s = s[:limit - 1].rstrip() + "…"
        return s
    except Exception:
        return ""


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _fetch_deezer():
    """Top faixas (API publica do Deezer, sem chave)."""
    data = json.loads(_get("https://api.deezer.com/chart",
                           timeout=12).decode("utf-8", "replace"))
    tracks = ((data.get("tracks") or {}).get("data") or [])
    out = [_clean(t.get("title")) for t in tracks[:TOP_N]]
    out = [t for t in out if t]
    if not out:
        raise ValueError("sem faixas")
    return out


def _fetch_dailymotion():
    """Videos em alta (API publica Dailymotion p/ campos basicos)."""
    data = json.loads(_get("https://api.dailymotion.com/videos"
                           "?fields=title&sort=trending&limit=5",
                           timeout=12).decode("utf-8", "replace"))
    out = [_clean(v.get("title")) for v in (data.get("list") or [])[:TOP_N]]
    out = [t for t in out if t]
    if not out:
        raise ValueError("sem videos")
    return out


FETCHERS = {
    "Deezer": _fetch_deezer,
    "Dailymotion": _fetch_dailymotion,
}


def _load_cache():
    try:
        with open(TOPCACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache):
    try:
        with open(TOPCACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def _static_top(service):
    try:
        from .streamings import STREAMINGS_DB
        items = (STREAMINGS_DB.get(service) or {}).get("top_content") or []
        return [{"title": _clean(i.get("title"))} for i in items[:TOP_N]
                if _clean(i.get("title"))]
    except Exception:
        return []


def get_top(service, static=None):
    """Top 3 p/ o card: cache fresco, senao estatico (sem rede aqui)."""
    try:
        entry = _load_cache().get(service) or {}
        titles = entry.get("titles") or []
        ts = float(entry.get("ts") or 0)
        if titles and (time.time() - ts) < TOP_TTL:
            return [{"title": t} for t in titles[:TOP_N]]
    except Exception:
        pass
    try:
        if static:
            return [{"title": _clean(i.get("title"))} for i in static[:TOP_N]
                    if _clean(i.get("title"))]
    except Exception:
        pass
    return _static_top(service)


def refresh_all(services=None):
    """Atualiza o que venceu (thread do boot). So grava com sucesso."""
    try:
        if services is None:
            from .streamings import STREAMINGS_DB
            services = [s for s in STREAMINGS_DB if s in FETCHERS]
        else:
            services = [s for s in services if s in FETCHERS]
    except Exception:
        return {}
    if not services:
        return {}
    try:
        cache = _load_cache()
    except Exception:
        cache = {}
    now = time.time()
    done = {}
    for service in services:
        try:
            entry = cache.get(service) or {}
            ts = float(entry.get("ts") or 0)
            if entry.get("titles") and (now - ts) < TOP_TTL:
                continue
            titles = FETCHERS[service]()[:TOP_N]
            if titles:
                cache[service] = {"titles": titles, "ts": now}
                done[service] = titles
        except Exception:
            continue
    try:
        if done:
            _save_cache(cache)
    except Exception:
        pass
    return done
