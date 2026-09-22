# -*- coding: utf-8 -*-
"""Identidade visual propria do Nexus — Fase 2 (blindagem + marca propria).

OBRA ORIGINAL do projeto Nexus (criada em 2026-09-22, via este script).
Conjunto de 5 icones geometricos desenhados do zero com primitivas PIL
(retangulos, elipses, poligonos) — nenhuma forma copiada de marca de
terceiro:

  cat_filmes.png   - claquete estilizada + play
  cat_musica.png   - nota musical dupla + viga
  cat_videos.png   - moldura + play + barra de progresso
  cat_games.png    - losango + ticks (eco do ◆ Nexus)
  nexus_default.png - anel + losango (neutro p/ streaming sem logo)

Paleta roxo-futurista do Nexus (nexus/config.py):
  tile #1a1a2e, borda #2a2545, acento #7c4dff, glow #b048ff, ciano #00e5ff.

Uso: `python assets/icons/make_icons.py` (regenera os 5 PNGs, 256px).
Os PNGs SAO rastreados no git (ao contrario de streaming_images/) e
embarcados no distribuivel como fallback de categoria (ver
nexus/paths.py ICONS_DIR e AppShellMixin.get_logo).
"""

import os

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
OUT = os.path.dirname(os.path.realpath(__file__))

TILE = (26, 26, 46, 255)
BORDER = (42, 37, 69, 255)
ACCENT = (124, 77, 255, 255)
GLOW = (176, 72, 255, 255)
CYAN = (0, 229, 255, 255)
WHITE = (255, 255, 255, 255)


def base_tile():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, SIZE - 5, SIZE - 5], radius=56, fill=TILE)
    d.rounded_rectangle([4, 4, SIZE - 5, SIZE - 5], radius=56,
                        outline=BORDER, width=4)
    # Filete superior sutil (brilho futurista).
    d.line([56, 14, SIZE - 56, 14], fill=(255, 255, 255, 28), width=3)
    return img


def neon(layer_draw_fn):
    """Camada do glifo com halo: desenha em GLOW borrado + nitido em ACCENT."""
    glow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    layer_draw_fn(ImageDraw.Draw(glow_layer), GLOW)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(7))
    sharp_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    layer_draw_fn(ImageDraw.Draw(sharp_layer), ACCENT)
    return glow_layer, sharp_layer


def play_triangle(d, cx, cy, w, h, fill):
    d.polygon([(cx - w // 2, cy - h // 2), (cx - w // 2, cy + h // 2),
               (cx + w // 2, cy)], fill=fill)


def diamond(d, cx, cy, r, fill, width=0):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if width:
        d.line(pts + [pts[0]], fill=fill, width=width, joint="curve")
    else:
        d.polygon(pts, fill=fill)


def draw_filmes(d, color):
    # Claquete: corpo + ripas diagonais no topo + play central.
    d.rounded_rectangle([64, 96, 192, 196], radius=14, outline=color, width=12)
    for i in range(4):
        x0 = 72 + i * 32
        d.polygon([(x0, 96), (x0 + 18, 96), (x0 + 2, 66), (x0 - 16, 66)],
                  fill=color)
    d.rectangle([64, 88, 192, 100], fill=color)
    play_triangle(d, 132, 152, 44, 52, color)
    d.rounded_rectangle([96, 176, 160, 186], radius=5, fill=CYAN)


def draw_musica(d, color):
    # Nota dupla: duas cabecas + duas hastes + viga.
    d.ellipse([66, 168, 106, 200], fill=color)
    d.ellipse([150, 158, 190, 190], fill=color)
    d.rectangle([98, 70, 110, 182], fill=color)
    d.rectangle([182, 60, 194, 172], fill=color)
    d.polygon([(98, 70), (194, 60), (194, 88), (98, 98)], fill=color)
    d.ellipse([178, 196, 194, 212], fill=CYAN)


def draw_videos(d, color):
    # Moldura 16:9 + play + barra de progresso com knob.
    d.rounded_rectangle([52, 72, 204, 184], radius=18, outline=color, width=12)
    play_triangle(d, 130, 128, 46, 56, color)
    d.rounded_rectangle([70, 158, 186, 168], radius=5, fill=(255, 255, 255, 70))
    d.rounded_rectangle([70, 158, 132, 168], radius=5, fill=CYAN)
    d.ellipse([126, 152, 142, 168], fill=CYAN)


def draw_games(d, color):
    # Losango (eco do ◆ Nexus) + ticks d-pad + nucleo.
    diamond(d, 128, 128, 72, color, width=13)
    diamond(d, 128, 128, 34, color)
    for (x0, y0, x1, y1) in ((128, 22, 128, 40), (128, 216, 128, 234),
                             (22, 128, 40, 128), (216, 128, 234, 128)):
        d.line([x0, y0, x1, y1], fill=color, width=11)
    d.ellipse([120, 120, 136, 136], fill=CYAN)


def draw_default(d, color):
    # Neutro: anel + losango + ponto (sem referencia a categoria).
    d.ellipse([58, 58, 198, 198], outline=color, width=13)
    diamond(d, 128, 128, 52, color, width=12)
    diamond(d, 128, 128, 22, GLOW if color == ACCENT else color)
    d.ellipse([120, 120, 136, 136], fill=CYAN)


DRAWERS = {
    "cat_filmes.png": draw_filmes,
    "cat_musica.png": draw_musica,
    "cat_videos.png": draw_videos,
    "cat_games.png": draw_games,
    "nexus_default.png": draw_default,
}


def make_one(filename, drawer):
    img = base_tile()
    glow_layer, sharp_layer = neon(drawer)
    img = Image.alpha_composite(img, glow_layer)
    img = Image.alpha_composite(img, sharp_layer)
    # Detalhes em ciano/branco por cima do halo (nitidos).
    top = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(top)
    if filename == "cat_filmes.png":
        td.rounded_rectangle([96, 176, 160, 186], radius=5, fill=CYAN)
    elif filename == "cat_musica.png":
        td.ellipse([178, 196, 194, 212], fill=CYAN)
    elif filename == "cat_videos.png":
        td.rounded_rectangle([70, 158, 132, 168], radius=5, fill=CYAN)
        td.ellipse([126, 152, 142, 168], fill=CYAN)
    else:
        td.ellipse([120, 120, 136, 136], fill=CYAN)
    img = Image.alpha_composite(img, top)
    img.save(os.path.join(OUT, filename))


if __name__ == "__main__":
    for filename, drawer in DRAWERS.items():
        make_one(filename, drawer)
        print("  [OK] %s" % filename)
    print("\nDone! %d icones originais Nexus em %s" % (len(DRAWERS), OUT))
