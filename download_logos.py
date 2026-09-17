# -*- coding: utf-8 -*-
"""Baixa os ICONES minimalistas oficiais (estilo app de celular) para streaming_images/.

Fontes: arquivos oficiais no Wikimedia Commons, via Special:FilePath.
- Envia User-Agent (sem isso o Wikimedia retorna 403).
- WHITEN: logos monocromaticas escuras convertidas p/ branco (versao clara
  oficial para fundo escuro, preservando o alfa original).
- Peacock: crop do pavao em File:NBC Peacock (2020).svg (passo manual).
"""
import io
import os
import time
import urllib.error
import urllib.parse
import urllib.request

IMAGES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "streaming_images")
WIDTH = 512
PAUSE = 0.7
UA = "NexusStreamingHub/5.0 (uso pessoal local; Python-urllib)"
opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", UA)]

# basename final -> (arquivo no Commons, termo de busca reserva)
ICONS = {
    "Netflix_logo.png": ("Netflix icon.svg", "Netflix icon"),
    "Youtube_logo.png": ("YouTube full-color icon (2017).svg", "YouTube icon"),
    "Spotify_logo.png": ("Spotify-icon.png", "Spotify icon"),
    "Disney+_logo.png": ("Disney plus icon.png", "Disney Plus icon"),
    "Amazon_Prime_logo.png": ("Prime Video logo (2024).svg", "Amazon Prime Video logo"),
    "HBO_Max_logo.png": ("HBO Max Logo.svg", "HBO Max logo"),
    "Twitch_logo.png": ("Twitch icon 2012.svg", "Twitch logo"),
    "Crunchyroll_logo.png": ("Crunchyroll-Icon-White.svg", "Crunchyroll icon"),
    "Dailymotion_logo.png": ("Dailymotion+Icon+Square.svg", "Dailymotion icon"),
    "Bandcamp_logo.png": ("Bandcamp-button-circle-black.svg", "Bandcamp icon"),
    "SoundCloud_logo.png": ("SoundCloud Logo rounded.png", "SoundCloud logo"),
    "Pluto_TV_logo.png": ("Pluto TV logo 2020.svg", "Pluto TV logo"),
    "Apple_TV_logo.png": ("Apple TV logo.svg", "Apple TV logo"),
    "Peacock_logo.png": ("NBC Peacock (2020).svg", "Peacock streaming logo"),
    "Paramount_Plus_logo.png": ("Paramount Plus.svg", "Paramount Plus logo"),
    "Discovery_Plus_logo.png": ("Discovery Plus logo.svg", "Discovery Plus logo"),
    "Globoplay_logo.png": ("Globoplay icon.svg", "Globoplay icon"),
    "Vix_logo.png": ("ViX Logo.svg", "ViX logo"),
    "Curiosity_Stream_logo.png": ("CuriosityStreamBlack.svg", "CuriosityStream logo"),
    "MUBI_logo.png": ("Mubi logo.svg", "MUBI logo"),
    "Shudder_logo.png": ("Shudder-logo-flat.png", "Shudder logo"),
    "BritBox_logo.png": ("BritBox 2026.svg", "BritBox logo"),
    "Tubi_logo.png": ("Tubi logo.svg", "Tubi logo"),
    "Plex_logo.png": ("Plex logo 2022 full color on black.png", "Plex logo"),
    "Kodi_logo.png": ("Kodi-logo-Thumbnail-light-transparent.png", "Kodi logo"),
    "Jellyfin_logo.png": ("Jellyfin - icon-transparent.svg", "Jellyfin logo"),
    "Mixer_logo.png": ("Mixer Icon Light 2017.svg", "Mixer icon"),
    "Vimeo_logo.png": ("Vimeo icon block.svg", "Vimeo icon"),
    "Rumble_logo.png": ("Rumble logo.svg", "Rumble logo"),
    "Tidal_logo.png": ("Tidal (service) logo.svg", "Tidal logo"),
    "Deezer_logo.png": ("Deezer New Icon.svg", "Deezer logo"),
    "Mixcloud_logo.png": ("Cib-mixcloud (CoreUI Icons v1.0.0).svg", "Mixcloud logo"),
}

# Arquivos monocromaticos escuros -> converter p/ branco (fundo escuro do app)
WHITEN = {
    "Paramount_Plus_logo.png", "Globoplay_logo.png", "MUBI_logo.png",
    "Shudder_logo.png", "Tidal_logo.png", "Deezer_logo.png",
    "Twitch_logo.png",
}

# Recolores especiais + tile preto arredondado (icone de app fiel):
# Crunchyroll: olho -> laranja #F47521 em tile preto
# Apple TV: logo -> branco em tile preto
APP_TILE_BUILDS = {
    "Crunchyroll_logo.png": {"color": (244, 117, 33), "tile": True, "glyph_box": (300, 300)},
    "Apple_TV_logo.png": {"color": (255, 255, 255), "tile": True, "glyph_box": (330, 330)},
}

STALE_EXTS = (".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp")


def fetch(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            with opener.open(url, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise last


def file_path_url(commons_name):
    quoted = urllib.parse.quote(commons_name.replace(" ", "_"), safe="()%")
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quoted}?width={WIDTH}"


def validate(data, min_width=50):
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    img.load()
    if img.width < min_width:
        raise ValueError(f"imagem muito pequena: {img.width}x{img.height}")
    return img


os.makedirs(IMAGES_DIR, exist_ok=True)
success, failed = 0, []
for filename, (commons_name, _search) in ICONS.items():
    try:
        data = fetch(file_path_url(commons_name))
        validate(data)
        if filename in WHITEN or filename in APP_TILE_BUILDS:
            from PIL import Image, ImageDraw
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            if filename in APP_TILE_BUILDS:
                cfg = APP_TILE_BUILDS[filename]
                solid = Image.new("RGBA", img.size, cfg["color"] + (255,))
                solid.putalpha(img.split()[3])
                if cfg["tile"]:
                    w, h = solid.size
                    s = min(cfg["glyph_box"][0] / w, cfg["glyph_box"][1] / h)
                    glyph = solid.resize((max(1, int(w * s)), max(1, int(h * s))))
                    tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
                    ImageDraw.Draw(tile).rounded_rectangle(
                        [0, 0, 511, 511], radius=115, fill=(0, 0, 0, 255))
                    tile.paste(glyph, ((512 - glyph.width) // 2,
                                       (512 - glyph.height) // 2), glyph)
                    solid = tile
            else:
                solid = Image.new("RGBA", img.size, (255, 255, 255, 255))
                solid.putalpha(img.split()[3])
            buf = io.BytesIO()
            solid.save(buf, format="PNG")
            data = buf.getvalue()
        with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
            f.write(data)
        base = os.path.splitext(filename)[0]
        for other in os.listdir(IMAGES_DIR):
            if other != filename and os.path.splitext(other)[0] == base \
                    and os.path.splitext(other)[1].lower() in STALE_EXTS:
                os.remove(os.path.join(IMAGES_DIR, other))
        print(f"  [OK] {filename} <- Commons:{commons_name}")
        success += 1
    except Exception as e:
        print(f"  [FAIL] {filename}: {e}")
        failed.append(filename)
    time.sleep(PAUSE)

print(f"\nPronto! {success} icones, {len(failed)} falhas: {failed}")
print("NOTA: Peacock_logo.png precisa de crop manual do pavao (ver historico).")
