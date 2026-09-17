# -*- coding: utf-8 -*-
"""Versao e repositorio (sem dependencias internas)."""


APP_VERSION = "5.5.0"
GITHUB_REPO = "ryanvidallima2/nexus-big-picture"
UPDATE_URL = "https://api.github.com/repos/" + GITHUB_REPO + "/releases/latest"


def ver_tuple(v):
    parts = []
    for p in str(v).lstrip("vV").split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)
