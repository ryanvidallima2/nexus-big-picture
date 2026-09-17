# -*- coding: utf-8 -*-
"""Update via GitHub Releases (sem dependencias da UI)."""

import json
import urllib.request

from .version import APP_VERSION, GITHUB_REPO, UPDATE_URL, ver_tuple


def _fetch_changes_since(tag, timeout=15):
    """Primeiras linhas dos commits entre a versao atual e a tag (resumo
    do que mudou p/ o card). Falhou = lista vazia (card usa as notas)."""
    out = []
    try:
        if not tag:
            return out
        try:
            if ver_tuple(tag) <= ver_tuple(APP_VERSION):
                return out
        except Exception:
            return out
        base = ("v" + APP_VERSION) if tag.startswith("v") else APP_VERSION
        url = ("https://api.github.com/repos/" + GITHUB_REPO +
               "/compare/%s...%s" % (base, tag))
        req = urllib.request.Request(
            url, headers={"User-Agent": "NexusBigPicture",
                          "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        total = 0
        try:
            total = int(data.get("total_commits", 0))
        except Exception:
            total = 0
        for cm in (data.get("commits", []) or [])[:6]:
            try:
                msg = (((cm or {}).get("commit") or {}).get("message")
                       or "").strip().split("\n")[0].strip()
            except Exception:
                msg = ""
            if not msg or msg.lower().startswith("merge "):
                continue
            out.append(msg[:100])
            if len(out) >= 5:
                break
        if total > len(out) and out:
            out.append("+%d" % (total - len(out)))
    except Exception:
        return []
    return out


def fetch_latest_release(timeout=15):
    """Ultima release no GitHub {tag, zip, notes, date, changes} ou None.
    changes = 1a linha dos commits desde a versao atual (o que mudou)."""
    try:
        req = urllib.request.Request(
            UPDATE_URL,
            headers={"User-Agent": "NexusBigPicture",
                     "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        tag = str(data.get("tag_name", ""))
        zip_url = ""
        for a in data.get("assets", []) or []:
            url = a.get("browser_download_url", "")
            if url.lower().endswith(".zip"):
                zip_url = url
                break
        info = {"tag": tag, "zip": zip_url,
                "notes": str(data.get("body", "") or "")[:600],
                "date": str(data.get("published_at", "") or "")[:10],
                "changes": _fetch_changes_since(tag, timeout=timeout)}
        return info
    except Exception:
        return None
