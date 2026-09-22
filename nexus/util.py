# -*- coding: utf-8 -*-
"""Utilidades de texto (extraido sem alteracao)."""

import re


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())
