# -*- coding: utf-8 -*-
"""Jogos: capas + deteccao Steam/Epic/Xbox (extraido sem alteracao)."""

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import winreg

from .util import _norm


GAME_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".ico")
GAME_COVER_HINTS = ("cover", "front", "box", "poster", "icon", "logo",
                    "capsule", "header", "capa")
GAME_SKIP_EXE = ("uninstall", "uninstal", "setup", "installer", "update",
                 "crash", "report", "redist", "vcredist", "dxsetup",
                 "oalinst", "dotnet", "helper", "config")
GAME_SKIP_DIRS = ("redist", "installer", "__installer", "directx", "dotnet",
                  "vcredist", "vulkanrt", "nodejs", "python", "drivers")

# Capa dos cards de jogo: area do topo tem 260x160 -> capa 616x353 da Steam
# (260x149) preenche quase perfeito. Streamings continuam em 80x80.
GAME_COVER_SIZE = (250, 150)

STEAM_SEARCH_URL = ("https://store.steampowered.com/api/storesearch/"
                    "?term=%s&l=english&cc=US")
STEAM_UA = "NexusBigPicture/5.4 (uso pessoal local; Python-urllib)"


def steam_search_game(name, timeout=15):
    """Busca o jogo na Steam. Retorna (appid, nome, tiny_image) ou (None, None, None)."""
    try:
        term = urllib.parse.quote((name or "").strip())
        if not term:
            return None, None, None
        req = urllib.request.Request(STEAM_SEARCH_URL % term,
                                     headers={"User-Agent": STEAM_UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        items = [i for i in (data.get("items") or [])
                 if isinstance(i, dict) and i.get("id") and i.get("name")]
        if not items:
            return None, None, None
        want = _norm(name)
        best = items[0]
        for it in items:
            if _norm(it.get("name", "")) == want:
                best = it
                break
        return int(best["id"]), best["name"], best.get("tiny_image", "")
    except Exception:
        return None, None, None


def _fetch_cover_urls(urls, dest_path, timeout=25, min_width=200):
    """Baixa a primeira URL valida (imagem >= min_width). True se salvou."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    except Exception:
        pass
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": STEAM_UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if len(data) < 5000:
                continue
            # Valida que e imagem de verdade e tem largura minima
            try:
                from PIL import Image as _Img
                import io as _io
                img = _Img.open(_io.BytesIO(data))
                img.load()
                if img.width < min_width:
                    continue
            except Exception:
                continue
            with open(dest_path, "wb") as f:
                f.write(data)
            return True
        except Exception:
            continue
    return False


def download_steam_cover_by_appid(appid, dest_path, timeout=25):
    """Capa oficial da Steam sabendo o appid (via appdetails). True se baixou."""
    try:
        appid = int(appid)
    except Exception:
        return False
    urls = []
    try:
        req = urllib.request.Request(
            "https://store.steampowered.com/api/appdetails?appids=%d&l=english" % appid,
            headers={"User-Agent": STEAM_UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        info = (data.get(str(appid)) or {}).get("data") or {}
        header = info.get("header_image", "")
        if header:
            urls.append(header.split("?")[0])
    except Exception:
        pass
    urls += [
        ("https://shared.akamai.steamstatic.com/store_item_assets"
         "/steam/apps/%d/capsule_616x353.jpg" % appid),
        ("https://shared.akamai.steamstatic.com/store_item_assets"
         "/steam/apps/%d/header.jpg" % appid),
    ]
    return _fetch_cover_urls(urls, dest_path, timeout=timeout)


def download_game_cover(game_name, dest_path, timeout=25):
    """Baixa a capa oficial da Steam (616x353, ideal p/ o card).

    Jogos novos as vezes so tem a capsula pequena (231x87): usa como
    ultimo recurso. Retorna o nome encontrado na Steam ou None
    (sem internet / nao achou).
    """
    try:
        appid, found, tiny = steam_search_game(game_name, timeout=15)
        if not appid:
            return None
        urls = [
            ("https://shared.akamai.steamstatic.com/store_item_assets"
             "/steam/apps/%d/capsule_616x353.jpg" % appid),
            ("https://shared.akamai.steamstatic.com/store_item_assets"
             "/steam/apps/%d/header.jpg" % appid),
        ]
        # Jogos novos: assets moram sob hash (ex. .../apps/ID/HASH/capsule_231x87.jpg)
        # dado pelo tiny_image -> tenta os irmaos grandes no mesmo diretorio
        try:
            if tiny and ("/apps/%d/" % appid) in tiny:
                base = tiny.rsplit("/", 1)[0]
                for fn in ("capsule_616x353.jpg", "header.jpg",
                           "hero_capsule.jpg", "library_600x900.jpg"):
                    urls.append(base + "/" + fn)
                urls.append(tiny.split("?")[0])  # capsula 231x87 original
        except Exception:
            pass
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        except Exception:
            pass
        if _fetch_cover_urls(urls, dest_path, timeout=timeout):
            return found
        return None
    except Exception:
        return None


def find_game_cover(folder):
    """Capa do jogo: imagem no topo da pasta (prefere cover/front/...)."""
    try:
        files = [f for f in sorted(os.listdir(folder))
                 if os.path.isfile(os.path.join(folder, f))
                 and f.lower().endswith(GAME_IMG_EXTS)]
    except Exception:
        return None
    if not files:
        return None
    for f in files:
        if f.lower().startswith(GAME_COVER_HINTS):
            return os.path.join(folder, f)
    return os.path.join(folder, files[0])


def find_game_exe(folder):
    """Acha o executavel principal do jogo (pasta do jogo)."""
    cands = []
    try:
        for dirpath, dirnames, files in os.walk(folder):
            dirnames[:] = [d for d in dirnames if d.lower() not in GAME_SKIP_DIRS]
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                low = f.lower()
                if any(k in low for k in GAME_SKIP_EXE):
                    continue
                full = os.path.join(dirpath, f)
                try:
                    size = os.path.getsize(full)
                except Exception:
                    size = 0
                depth = os.path.relpath(full, folder).count(os.sep)
                cands.append((depth, -size, full))
    except Exception:
        return None
    if not cands:
        return None
    norm_folder = _norm(os.path.basename(folder.rstrip(os.sep)))
    for depth, negsize, full in sorted(cands):
        if _norm(os.path.splitext(os.path.basename(full))[0]) == norm_folder:
            return full
    return sorted(cands)[0][2]


# ===================== PLATAFORMAS (deteccao local, sem login) =====================
# Le os manifestos de jogos JA INSTALADOS no PC: Steam (appmanifest_*.acf),
# Epic (Manifests/*.item) e Xbox/MS Store (Get-AppxPackage). Nenhuma conta,
# chave de API ou internet e necessaria p/ detectar (so p/ baixar capas).
PLATFORM_LABEL = {"steam": "Steam", "epic": "Epic Games", "xbox": "Xbox"}

STEAM_SKIP_SUBSTR = ("steamworks", "redistributable", "proton", " runtime",
                     "dedicated server", "soundtrack", "linux runtime")
EPIC_SKIP_SUBSTR = ("unreal engine", "epic games launcher", "epic online services")
EPIC_MANIFEST_DIR = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
# Substrings (normalizadas) que NUNCA sao jogo no Xbox: streamings + Ferragens
XBOX_SKIP_SUBSTR = ("netflix", "spotify", "whatsapp", "youtube", "disney",
                    "primevideo", "hbomax", "crunchyroll", "deezer", "dailymotion",
                    "soundcloud", "paramount", "discovery", "curiosity", "shudder",
                    "britbox", "mixcloud", "peacock", "twitch", "vimeo", "tidal",
                    "plex", "tubi", "vix", "clipchamp", "winrar", "realtek",
                    "nvidia", "hpprinter", "onedrive", "powerautomate", "pcmanager",
                    "devhome", "gethelp", "feedbackhub", "notepad", "calculator",
                    "stickynotes", "soundrecorder", "screensketch", "alarms",
                    "camera", "photos", "maps", "weather", "paint", "terminal",
                    "onenote", "yourphone", "crossdevice", "winget", "storepurchase",
                    "desktophostinstaller", "sechealth", "startExperiences",
                    "gamingservices", "gamingapp", "gamingoverlay", "identityprovider",
                    "tcui", "gamecallableui", "oobe", "shellExperience",
                    "startmenu", "pinningconfirmation", "printqueue", "printdialog",
                    "secureassessment", "capturepicker", "cloudexperience",
                    "contentdelivery", "parentalcontrols", "peopleexperience",
                    "xgpueject", "narratorquickstart", "cbs", "photon",
                    "undockeddevkit", "mixedreality", "asyncText", "brokerplugin",
                    "accountscontrol", "bioenrollment", "creddialoghost",
                    "devtoolsclient", "webviewhost", "apprep", "assignedaccess",
                    "lockapp", "immersivecontrolpanel", "handwriting",
                    "videoextension", "imageextension", "widgetsplatform",
                    "languageexperience", "webmediaextension", "rawimage",
                    "webexperience", "winaappruntime", "fileexp", "coreai",
                    "ecapp", "voiess", "livtop", "speion", "inpapp")
# Jogos Microsoft.* que SAO jogo de verdade (o resto Microsoft.* e sistema)
XBOX_KEEP_SUBSTR = ("solitaire", "mahjong", "minecraft", "forza", "halo",
                    "gears", "seaofthieves", "flightsimulator", "ageofempires",
                    "stateofdecay", "killerinstinct", "crackdown", "recore",
                    "sunsetoverdrive", "quantumbreak", "bleedingedge", "grounded",
                    "pentiment", "hifirush", "ori", "psychonauts", "fable",
                    "everwild", "perfectdark", "avowed", "clockwork")
XBOX_KNOWN_NAMES = {"microsoftminecraftuwp": "Minecraft",
                    "microsoftmahjong": "Mahjong",
                    "microsoftmicrosoftmahjong": "Mahjong",
                    "microsoftmicrosoftsolitairecollection": "Solitaire Collection",
                    "microsoft4297127d64ec6": "Minecraft Launcher"}
# Prefixos (normalizados, sem ponto) que sao sistema/inbox salvo excecao
XBOX_MS_PREFIXES = ("microsoft", "microsoftwindows", "windows",
                    "microsoftcorporation")


def platform_key(platform, pid):
    return "%s:%s" % (platform, pid)


def parse_acf(path):
    """Le appmanifest_*.acf da Steam -> dict minusculo ou {}."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"([^"]+)"\s+"([^"]*)"', f.read()):
                out[m.group(1).lower()] = m.group(2)
    except Exception:
        pass
    return out


def find_steam_path():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            p, _ = winreg.QueryValueEx(k, "SteamPath")
            if p and os.path.isdir(p):
                return os.path.normpath(p)
    except OSError:
        pass
    for cand in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam",
                 r"D:\Arquivos e Programas\Steam"):
        if os.path.isdir(cand):
            return cand
    return None


def steam_library_folders(steam_path):
    folders = [os.path.join(steam_path, "steamapps")]
    seen = {os.path.normcase(folders[0])}
    try:
        with open(os.path.join(steam_path, "steamapps", "libraryfolders.vdf"),
                  encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                sa = os.path.join(os.path.normpath(m.group(1)), "steamapps")
                if os.path.isdir(sa) and os.path.normcase(sa) not in seen:
                    seen.add(os.path.normcase(sa))
                    folders.append(sa)
    except Exception:
        pass
    return folders


def scan_steam_games():
    """Jogos instalados na Steam: [{platform, id, name, location}]."""
    found = []
    sp = find_steam_path()
    if not sp:
        return found
    for lib in steam_library_folders(sp):
        try:
            files = sorted(os.listdir(lib))
        except Exception:
            continue
        for fn in files:
            if not (fn.startswith("appmanifest_") and fn.endswith(".acf")):
                continue
            appid = fn[len("appmanifest_"):-len(".acf")]
            if not appid.isdigit():
                continue
            acf = parse_acf(os.path.join(lib, fn))
            name = (acf.get("name") or "").strip()
            inst = (acf.get("installdir") or "").strip()
            if not name or not inst:
                continue
            if any(k in name.lower() for k in STEAM_SKIP_SUBSTR):
                continue
            loc = os.path.join(lib, "common", inst)
            if not os.path.isdir(loc):
                continue
            found.append({"platform": "steam", "id": appid,
                          "name": name, "location": loc})
    return found


def scan_epic_games():
    """Jogos instalados na Epic: [{platform, id, name, location, exe, args}]."""
    found = []
    try:
        files = sorted(os.listdir(EPIC_MANIFEST_DIR))
    except Exception:
        return found
    for fn in files:
        if not fn.endswith(".item"):
            continue
        try:
            with open(os.path.join(EPIC_MANIFEST_DIR, fn), encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        name = (d.get("DisplayName") or "").strip()
        app = (d.get("AppName") or "").strip()
        loc = (d.get("InstallLocation") or "").strip()
        if not name or not app or not loc:
            continue
        if any(k in name.lower() for k in EPIC_SKIP_SUBSTR):
            continue
        if not os.path.isdir(loc):
            continue
        exe_rel = (d.get("LaunchExecutable") or "").strip().replace("/", os.sep)
        exe = os.path.join(loc, exe_rel) if exe_rel else ""
        if exe_rel and not os.path.isfile(exe):
            try:
                exe = find_game_exe(loc) or ""
            except Exception:
                exe = ""
        args = (d.get("LaunchCommand") or "").strip()
        found.append({"platform": "epic", "id": app, "name": name,
                      "location": loc, "exe": exe or "", "args": args})
    return found


def resolve_ms_resource(s, pri_path=""):
    """Resolve 'ms-resource:...' p/ texto (SHLoadIndirectString). '' se nao der."""
    if not s or not s.lower().startswith("ms-resource:"):
        return s or ""
    cands = []
    if pri_path and os.path.isfile(pri_path):
        cands.append("@%s? %s" % (pri_path, s))
    cands += ["@" + s, s]
    try:
        from ctypes import windll, create_unicode_buffer
        for src in cands:
            try:
                buf = create_unicode_buffer(512)
                if windll.shlwapi.SHLoadIndirectString(src, buf, 512, None) == 0:
                    val = buf.value.strip()
                    if val and not val.lower().startswith("ms-resource:"):
                        return val
            except Exception:
                continue
    except Exception:
        pass
    return ""


def prettify_pkg_name(pname):
    """'HoodedHorse.CorsairCove' -> 'Corsair Cove' (fallback sem recurso)."""
    try:
        base = (pname or "").split(".")[-1]
        base = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", base)
        base = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", base)
        base = re.sub(r"\s+", " ", base).strip(" -_")
        return base or pname
    except Exception:
        return pname


def parse_xbox_manifest(loc):
    """AppxManifest.xml -> {appid, display, logos[]} ou {}."""
    out = {}
    try:
        root = ET.parse(os.path.join(loc, "AppxManifest.xml")).getroot()
    except Exception:
        return out
    try:
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag == "Application" and el.get("Id"):
                out["appid"] = el.get("Id")
                for ch in el.iter():
                    if ch.tag.split("}")[-1] == "VisualElements":
                        out["display"] = ch.get("DisplayName", "")
                        out["logos"] = [ch.get("Square310x310Logo", ""),
                                        ch.get("Square150x150Logo", ""),
                                        ch.get("Square44x44Logo", "")]
                        break
                break
    except Exception:
        pass
    return out


def find_xbox_logo(loc, rels):
    """Resolve logo do manifesto (tokens {scale} viram glob). Maior arquivo."""
    import glob as _g
    for rel in rels or []:
        if not rel:
            continue
        pat = os.path.join(loc, rel.replace("/", os.sep))
        if "{" in pat:
            cands = _g.glob(re.sub(r"\{[^}]*\}", "*", pat))
        elif os.path.isfile(pat):
            cands = [pat]
        else:
            # Fallback: mesmo radical com variante (MedTile.jpg ->
            # MedTile.scale-200.png); ignora contrast e tamanhos miudos
            d, base = os.path.split(pat)
            stem = os.path.splitext(base)[0]
            cands = []
            try:
                for c in _g.glob(os.path.join(d, stem + "*")):
                    low = os.path.basename(c).lower()
                    if "contrast-" in low:
                        continue
                    if re.search(r"targetsize-(16|20|24|32|48)[^0-9]", low):
                        continue
                    cands.append(c)
            except Exception:
                cands = []
        best = None
        for c in cands:
            try:
                if not os.path.isfile(c):
                    continue
                low = os.path.basename(c).lower()
                m = re.search(r"scale-(\d+)", low)
                score = (int(m.group(1)) if m else 0, os.path.getsize(c))
                if best is None or score > best[1]:
                    best = (c, score)
            except Exception:
                continue
        if best:
            return best[0]
    return None


def scan_xbox_games(timeout=40):
    """Jogos da MS Store/Xbox instalados: [{platform, id, name, ...}]."""
    found = []
    ps = ("Get-AppxPackage | Select-Object Name,PackageFamilyName,"
          "InstallLocation,SignatureKind | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return found
    try:
        data = json.loads((out.stdout or "").strip() or "[]")
    except Exception:
        return found
    if isinstance(data, dict):
        data = [data]
    for pkg in data:
        try:
            # SignatureKind: 3 = Store (serializa como numero no JSON)
            if str(pkg.get("SignatureKind") or "") not in ("3", "Store"):
                continue
            pname = pkg.get("Name") or ""
            pfn = pkg.get("PackageFamilyName") or ""
            loc = pkg.get("InstallLocation") or ""
            if not pname or not pfn or not os.path.isdir(loc):
                continue
            n = _norm(pname)
            if n in XBOX_KNOWN_NAMES:
                pass  # jogo conhecido: importa direto
            elif any(k in n for k in XBOX_SKIP_SUBSTR):
                continue
            elif n.startswith(XBOX_MS_PREFIXES) and not any(
                    k in n for k in XBOX_KEEP_SUBSTR):
                continue
            man = parse_xbox_manifest(loc)
            if not man.get("appid"):
                continue
            disp = man.get("display", "")
            name = ""
            if disp and not disp.lower().startswith("ms-resource:"):
                name = disp
            if not name and disp:
                try:
                    pri = os.path.join(loc, "resources.pri")
                    name = resolve_ms_resource(disp, pri)
                except Exception:
                    name = ""
            if not name:
                name = XBOX_KNOWN_NAMES.get(n, "") or prettify_pkg_name(pname)
            if not name:
                continue
            found.append({"platform": "xbox", "id": pfn, "name": name,
                          "location": loc, "pfn": pfn,
                          "appid": man.get("appid", "App"),
                          "logos": man.get("logos") or []})
        except Exception:
            continue
    return found


def _safe_icon_basename(name):
    """Nome seguro p/ arquivo de capa (remove <>:\"/\\|?*)."""
    s = (name or "jogo").strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)
    s = s.strip(" .")
    return s or "jogo"


def extract_exe_icon(exe_path, dest_png, timeout=20):
    """Extrai o icone original do .exe e salva como PNG. True se ok."""
    try:
        if not exe_path or not os.path.isfile(exe_path):
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_png)), exist_ok=True)
        except Exception:
            pass
        exe_abs = os.path.abspath(exe_path)
        dest_abs = os.path.abspath(dest_png)
        # Aspas simples dobradas p/ PowerShell
        exe_ps = exe_abs.replace("'", "''")
        dest_ps = dest_abs.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Drawing; "
            "$icon=[System.Drawing.Icon]::ExtractAssociatedIcon('%s'); "
            "if($icon -eq $null){exit 1}; "
            "$bmp=$icon.ToBitmap(); "
            "$bmp.Save('%s',[System.Drawing.Imaging.ImageFormat]::Png)"
            % (exe_ps, dest_ps)
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            if not (os.path.isfile(dest_abs) and os.path.getsize(dest_abs) > 0):
                return False
        except Exception:
            return False
        # Icones de .exe costumam sair 32x32: amplia p/ 128 p/ preencher
        # o card (80px) sem ficar minúsculo na busca visual.
        try:
            from PIL import Image as _PILImage
            im = _PILImage.open(dest_abs)
            try:
                try:
                    if im.mode not in ("RGBA", "LA"):
                        im = im.convert("RGBA")
                except Exception:
                    pass
                w, h = im.size
                if max(w, h) < 96:
                    resample = getattr(_PILImage, "LANCZOS", getattr(_PILImage, "BILINEAR", 1))
                    big = im.resize((128, 128), resample)
                    try:
                        im.close()
                    except Exception:
                        pass
                    big.save(dest_abs, "PNG")
                    try:
                        big.close()
                    except Exception:
                        pass
                else:
                    try:
                        im.close()
                    except Exception:
                        pass
            except Exception:
                try:
                    im.close()
                except Exception:
                    pass
        except Exception:
            pass
        return True
    except Exception:
        return False
