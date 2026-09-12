# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os

IMAGES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "streaming_images")
SIZE = 80

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

services = {
    "Netflix": ("N", "#E50914"),
    "YouTube": ("YT", "#FF0000"),
    "Spotify": ("S", "#1DB954"),
    "Disney+": ("D+", "#113CCF"),
    "Amazon_Prime": ("AP", "#00A8E1"),
    "HBO_Max": ("HBO", "#B01CDE"),
    "Twitch": ("TW", "#9146FF"),
    "Crunchyroll": ("CR", "#F47521"),
    "Dailymotion": ("DM", "#0066DC"),
    "Bandcamp": ("BC", "#629AA9"),
    "SoundCloud": ("SC", "#FF5500"),
    "Pluto_TV": ("PTV", "#2B2B2B"),
    "Apple_TV": ("TV", "#555555"),
    "Peacock": ("PK", "#000000"),
    "Paramount_Plus": ("P+", "#0064FF"),
    "Discovery_Plus": ("D+", "#0A0A0A"),
    "Globoplay": ("GP", "#E41E2C"),
    "Vix": ("VX", "#E30613"),
    "Curiosity_Stream": ("CS", "#1A1A2E"),
    "MUBI": ("M", "#000000"),
    "Shudder": ("SH", "#FF3333"),
    "BritBox": ("BB", "#2C3E50"),
    "Tubi": ("TB", "#FA382F"),
    "Plex": ("PX", "#EBAF00"),
    "Kodi": ("K", "#17B2E7"),
    "Jellyfin": ("JF", "#9B59B6"),
    "Mixer": ("MX", "#0024AF"),
    "Vimeo": ("V", "#1AB7EA"),
    "Rumble": ("R", "#85C7DE"),
    "Tidal": ("TD", "#000000"),
    "Deezer": ("DZ", "#A238FF"),
    "Mixcloud": ("MC", "#5000E5"),
}

try:
    font = ImageFont.truetype("arial.ttf", 36)
except:
    font = ImageFont.load_default()

created = 0
for name, (text, color) in services.items():
    filename = f"{name}_logo.png"
    filepath = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(filepath):
        print(f"  [SKIP] {filename}")
        continue
    img = Image.new("RGB", (SIZE, SIZE), color)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (SIZE - tw) // 2
    y = (SIZE - th) // 2
    draw.text((x, y), text, fill="white", font=font)
    img.save(filepath)
    print(f"  [OK] {filename} ({color})")
    created += 1

print(f"\nDone! {created} logos created")
