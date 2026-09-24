# -*- coding: utf-8 -*-
"""Identidade visual propria do Nexus — Fase 2 (blindagem + marca propria).

OBRA ORIGINAL do projeto Nexus (criada em 2026-09-22, via este script).
Conjunto de 15 icones geometricos desenhados do zero com primitivas PIL
(retangulos, elipses, poligonos) — nenhuma forma copiada de marca de
terceiro:

  Serie 1: cat_filmes.png (claquete + play), cat_musica.png (nota dupla),
  cat_videos.png (moldura + play + progresso), cat_games.png (losango +
  ticks, eco do ◆ Nexus), nexus_default.png (anel + losango neutro).
  Serie 2 (2026-09-24): cat_anime (torii), cat_sports (bola),
  cat_news (globo), cat_kids (balao), cat_docs (livro), cat_horror
  (fantasma), cat_comedy (sorriso), cat_live (transmissao),
  cat_podcast (microfone), cat_fitness (halter).
  Serie 3 (2026-09-24): variacoes com nomes genericos (sem numerar):
  cat_cinema (projetor), cat_serie (TV), cat_fone (fones),
  cat_radio (radio), cat_camera (camera), cat_play (play),
  cat_dpad (controle), cat_dado (dado).

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


# --- Serie 2 (2026-09-24): 10 temas genericos p/ escolha de logo ---
# Mesmo formato (tile + halo neon + detalhe ciano). Formas geometricas
# originais, sem marca de terceiro. O ciano vai DENTRO de cada drawer.

def draw_anime(d, color):
    # Torii: viga superior + segunda viga + pilares + placa central.
    d.rectangle([52, 62, 204, 84], fill=color)
    d.rectangle([70, 94, 186, 108], fill=color)
    d.rectangle([82, 108, 100, 202], fill=color)
    d.rectangle([156, 108, 174, 202], fill=color)
    d.rectangle([116, 122, 140, 152], fill=CYAN)


def draw_sports(d, color):
    # Bola: aro + pentagono central + costuras em arco.
    d.ellipse([64, 64, 192, 192], outline=color, width=12)
    cx, cy, r = 128, 128, 22
    import math as _m
    pts = [(cx + r * _m.cos(-_m.pi / 2 + i * 2 * _m.pi / 5),
            cy + r * _m.sin(-_m.pi / 2 + i * 2 * _m.pi / 5))
           for i in range(5)]
    d.polygon(pts, fill=color)
    d.arc([78, 78, 178, 178], start=200, end=340, fill=color, width=8)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_news(d, color):
    # Globo: aro + meridiano + linha do equador + ponto.
    d.ellipse([62, 62, 194, 194], outline=color, width=12)
    d.ellipse([96, 62, 160, 194], outline=color, width=8)
    d.line([62, 128, 194, 128], fill=color, width=8)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_kids(d, color):
    # Balao: elipse + no + barbante + brilho.
    d.ellipse([84, 48, 172, 140], fill=color)
    d.polygon([(122, 140), (134, 140), (128, 154)], fill=color)
    d.line([128, 154, 118, 190, 132, 214], fill=color, width=7,
           joint="curve")
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_docs(d, color):
    # Livro aberto: duas paginas + lombada + linhas de texto.
    d.polygon([(40, 84), (120, 70), (120, 186), (40, 200),
               (40, 84)], outline=color, width=10)
    d.polygon([(216, 84), (136, 70), (136, 186), (216, 200),
               (216, 84)], outline=color, width=10)
    d.line([128, 70, 128, 186], fill=color, width=8)
    d.line([56, 108, 108, 98], fill=color, width=6)
    d.line([56, 130, 108, 120], fill=color, width=6)
    d.line([148, 98, 200, 108], fill=CYAN, width=6)
    d.line([148, 120, 200, 130], fill=color, width=6)


def draw_horror(d, color):
    # Fantasma: corpo + base ondulada + olhos e boca vazados.
    d.rectangle([88, 96, 168, 178], fill=color)
    d.pieslice([88, 40, 168, 120], start=180, end=360, fill=color)
    d.polygon([(88, 178), (104, 158), (120, 178), (136, 158),
               (152, 178), (168, 158), (168, 178)], fill=color)
    d.ellipse([106, 108, 122, 130], fill=TILE)
    d.ellipse([134, 108, 150, 130], fill=TILE)
    d.ellipse([120, 142, 136, 158], fill=TILE)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_comedy(d, color):
    # Sorriso: aro + olhos + arco do sorriso.
    d.ellipse([62, 62, 194, 194], outline=color, width=12)
    d.ellipse([100, 104, 116, 124], fill=color)
    d.ellipse([140, 104, 156, 124], fill=color)
    d.arc([92, 96, 164, 176], start=20, end=160, fill=color, width=10)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_live(d, color):
    # Transmissao: ponto central + arcos laterais.
    d.ellipse([114, 114, 142, 142], fill=color)
    d.arc([84, 84, 172, 172], start=200, end=340, fill=color, width=9)
    d.arc([84, 84, 172, 172], start=20, end=160, fill=color, width=9)
    d.arc([60, 60, 196, 196], start=205, end=335, fill=color, width=8)
    d.arc([60, 60, 196, 196], start=25, end=155, fill=color, width=8)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_podcast(d, color):
    # Microfone: capsula + berco + haste + base.
    d.rounded_rectangle([106, 44, 150, 126], radius=28, fill=color)
    d.line([106, 84, 150, 84], fill=TILE, width=6)
    d.arc([88, 96, 168, 176], start=0, end=180, fill=color, width=10)
    d.line([128, 140, 128, 196], fill=color, width=10)
    d.line([100, 196, 156, 196], fill=color, width=10)
    # (sem ponto decorativo: so o glifo pertence a imagem)


def draw_fitness(d, color):
    # Halter: barra + 2 anilhas de cada lado.
    d.rectangle([40, 121, 216, 135], fill=color)
    d.rectangle([62, 88, 80, 168], fill=color)
    d.rectangle([176, 88, 194, 168], fill=color)
    d.rectangle([88, 102, 102, 154], fill=color)
    d.rectangle([154, 102, 168, 154], fill=color)
    # (sem ponto decorativo: so o glifo pertence a imagem)


# --- Serie 3 (2026-09-24): variacoes por categoria, nomes genericos ---
# (sem numerar: cinema/serie, fone/radio, camera/play, dpad/dado).
# Ciano sempre ESTRUTURAL (encostado no glifo), nunca ponto solto.

def draw_cinema(d, color):
    # Projetor: corpo + 2 rolos + feixe de luz + fileira de furos.
    d.rounded_rectangle([56, 112, 168, 184], radius=12, fill=color)
    d.ellipse([70, 60, 118, 108], outline=color, width=10)
    d.ellipse([134, 60, 182, 108], outline=color, width=10)
    d.polygon([(168, 128), (168, 168), (216, 156), (216, 140)], fill=color)
    for x in (72, 92, 112, 132):
        d.rectangle([x, 158, x + 10, 168], fill=CYAN)


def draw_serie(d, color):
    # TV: moldura + antenas + play + base.
    d.line([100, 84, 76, 48], fill=color, width=9)
    d.line([156, 84, 180, 48], fill=color, width=9)
    d.rounded_rectangle([56, 84, 200, 176], radius=16, outline=color,
                        width=12)
    play_triangle(d, 130, 130, 40, 48, color)
    d.line([104, 186, 152, 186], fill=CYAN, width=10)


def draw_fone(d, color):
    # Fones: arco + 2 conchas + detalhe interno.
    d.arc([56, 48, 200, 208], start=180, end=360, fill=color, width=14)
    d.rounded_rectangle([48, 128, 84, 196], radius=16, fill=color)
    d.rounded_rectangle([172, 128, 208, 196], radius=16, fill=color)
    d.line([66, 140, 66, 184], fill=CYAN, width=6)
    d.line([190, 140, 190, 184], fill=CYAN, width=6)


def draw_radio(d, color):
    # Radio: caixa + falante + antena + sintonia.
    d.line([168, 100, 204, 52], fill=color, width=9)
    d.rounded_rectangle([56, 100, 200, 196], radius=14, outline=color,
                        width=12)
    d.ellipse([84, 122, 140, 178], outline=color, width=8)
    d.ellipse([104, 142, 120, 158], fill=color)
    d.line([150, 122, 186, 122], fill=CYAN, width=7)


def draw_camera(d, color):
    # Camera: corpo + lente + visor + luz de gravacao.
    d.rounded_rectangle([48, 96, 208, 180], radius=16, fill=color)
    d.rectangle([84, 72, 128, 96], fill=color)
    d.ellipse([96, 112, 160, 176], outline=TILE, width=9)
    d.ellipse([124, 158, 140, 174], fill=CYAN)
    d.rectangle([172, 116, 196, 132], fill=TILE)


def draw_play(d, color):
    # Play: aro + triangulo + base.
    d.ellipse([58, 50, 198, 190], outline=color, width=13)
    play_triangle(d, 132, 120, 52, 62, color)
    d.line([88, 196, 168, 196], fill=CYAN, width=10)


def draw_dpad(d, color):
    # Controle: cruz + furo central + 2 botoes de acao.
    d.rectangle([86, 62, 120, 194], fill=color)
    d.rectangle([36, 112, 170, 146], fill=color)
    d.ellipse([89, 115, 117, 143], fill=TILE)
    d.ellipse([186, 92, 214, 120], fill=color)
    d.ellipse([188, 140, 212, 164], fill=color)
    d.ellipse([186, 138, 214, 166], outline=CYAN, width=7)


def draw_dado(d, color):
    # Dado: quadrado + 5 pontos (centro em ciano).
    d.rounded_rectangle([70, 70, 186, 186], radius=26, outline=color,
                        width=13)
    for cx, cy in ((104, 104), (152, 104), (104, 152), (152, 152)):
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=color)
    d.ellipse([117, 117, 139, 139], fill=CYAN)


DRAWERS = {
    "cat_filmes.png": draw_filmes,
    "cat_musica.png": draw_musica,
    "cat_videos.png": draw_videos,
    "cat_games.png": draw_games,
    "nexus_default.png": draw_default,
    "cat_anime.png": draw_anime,
    "cat_sports.png": draw_sports,
    "cat_news.png": draw_news,
    "cat_kids.png": draw_kids,
    "cat_docs.png": draw_docs,
    "cat_horror.png": draw_horror,
    "cat_comedy.png": draw_comedy,
    "cat_live.png": draw_live,
    "cat_podcast.png": draw_podcast,
    "cat_fitness.png": draw_fitness,
    "cat_cinema.png": draw_cinema,
    "cat_serie.png": draw_serie,
    "cat_fone.png": draw_fone,
    "cat_radio.png": draw_radio,
    "cat_camera.png": draw_camera,
    "cat_play.png": draw_play,
    "cat_dpad.png": draw_dpad,
    "cat_dado.png": draw_dado,
}

# Serie 2 desenha o ciano dentro do drawer: sem ponto central extra.
SERIE2 = {"cat_anime.png", "cat_sports.png", "cat_news.png",
          "cat_kids.png", "cat_docs.png", "cat_horror.png",
          "cat_comedy.png", "cat_live.png", "cat_podcast.png",
          "cat_fitness.png", "cat_cinema.png", "cat_serie.png",
          "cat_fone.png", "cat_radio.png", "cat_camera.png",
          "cat_play.png", "cat_dpad.png", "cat_dado.png"}


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
    elif filename in SERIE2:
        pass  # serie 2: ciano ja vai dentro do drawer
    else:
        td.ellipse([120, 120, 136, 136], fill=CYAN)
    img = Image.alpha_composite(img, top)
    img.save(os.path.join(OUT, filename))


if __name__ == "__main__":
    for filename, drawer in DRAWERS.items():
        make_one(filename, drawer)
        print("  [OK] %s" % filename)
    print("\nDone! %d icones originais Nexus em %s" % (len(DRAWERS), OUT))
