# -*- coding: utf-8 -*-
"""Avatares pre-definidos do Login: formas geometricas desenhadas via PIL.

Quadro redondo de verdade (mascara eliptica com transparencia), sem
depender de fonte/emoji do sistema. Gerados em runtime, com cache.
"""

try:
    from PIL import Image as _Img, ImageDraw as _Draw, ImageTk as _ImgTk
    _PIL_OK = True
except Exception:
    _PIL_OK = False

# (id, rotulo_pt, rotulo_en, cor_fundo, desenho)
# Desenhos: disco, anel, quadrado, losango, triangulo, estrela, cruz, coracao.
AVATARS = [
    ("av0", "Azul", "Blue", "#1e63e9", "disc"),
    ("av1", "Verde", "Green", "#00a651", "ring"),
    ("av2", "Roxo", "Purple", "#7c4dff", "square"),
    ("av3", "Laranja", "Orange", "#f47521", "diamond"),
    ("av4", "Rosa", "Pink", "#ff4081", "triangle"),
    ("av5", "Ciano", "Cyan", "#00bcd4", "star"),
    ("av6", "Vermelho", "Red", "#e50914", "plus"),
    ("av7", "Amarelo", "Yellow", "#e6a800", "heart"),
]

_AVATAR_IDS = [a[0] for a in AVATARS]
_CACHE = {}


def avatar_ids():
    return list(_AVATAR_IDS)


def avatar_label(avid, lang="pt-br"):
    try:
        for aid, pt, en, _bg, _sh in AVATARS:
            if aid == avid:
                return pt if str(lang).startswith("pt") else en
    except Exception:
        pass
    return avid or ""


def default_avatar(name):
    """Avatar deterministico p/ quem nunca escolheu (pelo nome)."""
    try:
        h = 0
        for ch in str(name or "?"):
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return _AVATAR_IDS[h % len(_AVATAR_IDS)]
    except Exception:
        return _AVATAR_IDS[0]


def _star_points(cx, cy, r_out, r_in, n=5):
    import math as _math
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = -_math.pi / 2 + i * _math.pi / n
        pts.append((cx + r * _math.cos(a), cy + r * _math.sin(a)))
    return pts


def _draw_shape(d, shape, box, fg):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    r = min(x1 - x0, y1 - y0) / 2.0
    if shape == "disc":
        d.ellipse(box, fill=fg)
    elif shape == "ring":
        d.ellipse(box, outline=fg, width=max(3, int(r * 0.28)))
    elif shape == "square":
        d.rectangle(box, fill=fg)
    elif shape == "diamond":
        d.polygon([(cx, y0), (x1, cy), (cx, y1), (x0, cy)], fill=fg)
    elif shape == "triangle":
        d.polygon([(cx, y0), (x1, y1), (x0, y1)], fill=fg)
    elif shape == "star":
        d.polygon(_star_points(cx, cy, r, r * 0.45), fill=fg)
    elif shape == "plus":
        w = r * 0.55
        d.rectangle([cx - w, y0, cx + w, y1], fill=fg)
        d.rectangle([x0, cy - w, x1, cy + w], fill=fg)
    elif shape == "heart":
        d.ellipse([x0, y0, cx, cy + r * 0.35], fill=fg)
        d.ellipse([cx, y0, x1, cy + r * 0.35], fill=fg)
        d.polygon([(x0, cy), (x1, cy), (cx, y1)], fill=fg)
    else:
        d.ellipse(box, fill=fg)


def make_avatar_photo(avid, size=96):
    """PhotoImage redonda do avatar (None sem Pillow)."""
    if not _PIL_OK:
        return None
    try:
        size = max(32, min(256, int(size)))
    except Exception:
        size = 96
    key = (str(avid), size)
    if key in _CACHE:
        return _CACHE[key]
    bg = "#7c4dff"
    shape = "disc"
    try:
        for aid, _pt, _en, c, s in AVATARS:
            if aid == avid:
                bg, shape = c, s
                break
    except Exception:
        pass
    try:
        img = _Img.new("RGBA", (size, size), (0, 0, 0, 0))
        mask = _Img.new("L", (size, size), 0)
        _Draw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        base = _Img.new("RGBA", (size, size), bg + "FF")
        img.paste(base, (0, 0), mask)
        d = _Draw.Draw(img)
        m = int(size * 0.24)
        _draw_shape(d, shape, [m, m, size - m, size - m], (255, 255, 255, 255))
        # Aplica o recorte redondo tambem no desenho
        img.putalpha(mask)
        photo = _ImgTk.PhotoImage(img)
        _CACHE[key] = photo
        return photo
    except Exception:
        return None
