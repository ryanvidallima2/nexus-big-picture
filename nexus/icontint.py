# -*- coding: utf-8 -*-
"""Recolorimento programatico dos icones de categoria pelo tema ativo.

Em vez de um PNG por tema, os PNGs de assets/icons sao recoloridos em
runtime para a cor de destaque (settings.json: accent_color/accent_glow,
fallback Config.ACCENT). Duas estrategias:

- tint_icon: silhueta — cor solida usando o alpha original como mascara.
- tint_icon_shaded: com sombreado — ImageOps.colorize sobre a versao em
  cinza, preservando o alpha original (sombreamento vira tonalidade).

O cache get_themed_icon() gera uma vez por (icone, cor, tamanho) e
reaproveita nos redraws; trocar o tema = chave nova = regenera sozinho.
"""

import os

try:
    from PIL import Image as _Img, ImageOps as _Ops, ImageTk as _ImgTk
    _PIL_OK = True
except Exception:
    _PIL_OK = False

# {(path_norm, color_norm, size_key): ImageTk.PhotoImage}
_THEMED_CACHE = {}


def _norm_hex(color_hex, fallback="#7c4dff"):
    """'#7c4dff' canonico (minusculo, com #). Qualquer lixo -> fallback."""
    try:
        s = str(color_hex or "").strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) == 6:
            int(s, 16)
            return "#" + s.lower()
    except Exception:
        pass
    try:
        return _norm_hex(fallback, "#7c4dff")
    except Exception:
        return "#7c4dff"


def _hex_to_rgb(color_hex):
    s = _norm_hex(color_hex).lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def get_accent(settings=None):
    """Cor de destaque vigente: settings accent_color -> Config.ACCENT."""
    try:
        if isinstance(settings, dict):
            c = (settings.get("accent_color", "") or "").strip()
            if c:
                return _norm_hex(c)
    except Exception:
        pass
    try:
        from .config import Config
        return _norm_hex(getattr(Config, "ACCENT", "#7c4dff"))
    except Exception:
        return "#7c4dff"


def tint_icon(path, color_hex):
    """Silhueta: imagem RGBA toda na cor, com o alpha original.

    Retorna PIL.Image (RGBA) ou None (sem Pillow/arquivo invalido).
    """
    if not _PIL_OK:
        return None
    try:
        if not path or not os.path.isfile(path):
            return None
        rgb = _hex_to_rgb(color_hex)
        img = _Img.open(path).convert("RGBA")
        _r, _g, _b, alpha = img.split()
        solid = _Img.new("RGBA", img.size, rgb + (255,))
        solid.putalpha(alpha)
        return solid
    except Exception:
        return None


def tint_icon_shaded(path, color_hex):
    """Com sombreado: colorize (preto -> cor) sobre o cinza da imagem,
    preservando o alpha original. Claro vira a cor do tema, escuro
    continua escuro (fundo do tile nao estoura).

    Retorna PIL.Image (RGBA) ou None.
    """
    if not _PIL_OK:
        return None
    try:
        if not path or not os.path.isfile(path):
            return None
        rgb = _hex_to_rgb(color_hex)
        img = _Img.open(path).convert("RGBA")
        _r, _g, _b, alpha = img.split()
        gray = img.convert("L")
        colored = _Ops.colorize(gray, black=(0, 0, 0), white=rgb)
        colored.putalpha(alpha)
        return colored
    except Exception:
        return None


def _thumb(photo_img, size):
    """Reduz p/ size (int ou (larg, alt)), como load_photo."""
    try:
        if size is None:
            return photo_img
        box = (int(size), int(size)) if not isinstance(size, tuple) else tuple(size)
        photo_img.thumbnail(box, _Img.LANCZOS)
        return photo_img
    except Exception:
        try:
            box = (int(size), int(size)) if not isinstance(size, tuple) else tuple(size)
            photo_img.thumbnail(box, _Img.BILINEAR)
            return photo_img
        except Exception:
            return photo_img


def get_themed_icon(path, color_hex, size=None, shaded=True):
    """PhotoImage do icone recolorido, com cache por (icone, cor, tamanho).

    Gera uma vez por combinacao e reaproveita depois — redraws nao
    recolorem. None sem Pillow/Tk ou arquivo invalido. Chame com a cor
    vigente (get_accent) para trocar junto com o tema.
    """
    if not _PIL_OK:
        return None
    try:
        color = _norm_hex(color_hex)
    except Exception:
        return None
    try:
        if isinstance(size, tuple):
            size_key = (int(size[0]), int(size[1]))
        elif size is None:
            size_key = None
        else:
            size_key = int(size)
    except Exception:
        size_key = None
    try:
        key = (os.path.normcase(os.path.abspath(path or "")),
               color, size_key)
    except Exception:
        return None
    hit = _THEMED_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        img = (tint_icon_shaded(path, color) if shaded
               else tint_icon(path, color))
        if img is None:
            return None
        img = _thumb(img, size_key)
        photo = _ImgTk.PhotoImage(img)
    except Exception:
        return None
    try:
        _THEMED_CACHE[key] = photo
    except Exception:
        pass
    return photo


def clear_icon_cache():
    """Esvazia o cache (ex.: economia de memoria)."""
    try:
        _THEMED_CACHE.clear()
        return True
    except Exception:
        return False


def cache_size():
    try:
        return len(_THEMED_CACHE)
    except Exception:
        return 0
