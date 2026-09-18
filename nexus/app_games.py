# -*- coding: utf-8 -*-
"""Aba Jogos: deteccao, atalhos, capas e lancamento (extraido sem alteracao)."""

import os
import subprocess
import threading
import tkinter as tk
from shutil import copy2
from tkinter import filedialog, simpledialog

from .apps import launch_uwp
from .config import Config, VIEW_MODES, VIEW_MODE_ICONS, save_settings
from .dialogs import NexusMenuWindow
from .games import (
    GAME_COVER_SIZE, _safe_icon_basename, download_game_cover,
    download_steam_cover_by_appid, extract_exe_icon, find_game_exe,
    find_xbox_logo, platform_key, scan_epic_games, scan_steam_games,
    scan_xbox_games,
)
from .i18n import t
from .paths import GAMES_DIR, IMAGES_DIR


class AppGamesMixin:
    """Tudo da aba Jogos."""

    def game_folder(self, name):
        p = os.path.join(GAMES_DIR, name)
        return p if os.path.isdir(p) else None

    def game_is_external(self, name):
        try:
            return name in (self.settings.get("external_games") or {})
        except Exception:
            return False

    def game_is_platform(self, name):
        """Jogo detectado de plataforma (Steam/Epic/Xbox)."""
        try:
            return name in (self.settings.get("platform_games") or {})
        except Exception:
            return False

    def game_platform_data(self, name):
        try:
            return dict((self.settings.get("platform_games") or {}).get(name, {}))
        except Exception:
            return {}

    def game_exe_for(self, name):
        """Caminho do .exe do jogo (pasta interna ou atalho externo) ou None."""
        if self.game_is_external(name):
            try:
                exe = (self.settings.get("external_games") or {}).get(name, {}).get("exe", "")
            except Exception:
                exe = ""
            if exe and os.path.isfile(exe):
                return exe
            return None
        folder = self.game_folder(name)
        if not folder:
            return None
        return find_game_exe(folder)

    def scan_games(self):
        try:
            os.makedirs(GAMES_DIR, exist_ok=True)
        except Exception:
            pass
        try:
            entries = sorted(os.listdir(GAMES_DIR))
        except Exception:
            entries = []
        folders = [e for e in entries
                   if os.path.isdir(os.path.join(GAMES_DIR, e))]
        try:
            externals = sorted((self.settings.get("external_games") or {}).keys())
        except Exception:
            externals = []
        try:
            plats = sorted((self.settings.get("platform_games") or {}).keys())
        except Exception:
            plats = []
        # Mantem pastas + atalhos + plataformas (sem duplicar nomes)
        seen = set(folders)
        merged = list(folders)
        for n in list(externals) + list(plats):
            if n not in seen:
                merged.append(n)
                seen.add(n)
        return sorted(merged, key=str.lower)

    def open_games_folder(self):
        try:
            os.makedirs(GAMES_DIR, exist_ok=True)
            os.startfile(GAMES_DIR)
        except Exception:
            pass

    def add_external_game(self):
        """Opcao 2: procura o .exe em qualquer pasta e cria atalho no Nexus."""
        try:
            exe = filedialog.askopenfilename(
                title=t("games_add_exe", self.lang),
                filetypes=[("Executavel", "*.exe"), ("Todas", "*.*")])
        except Exception:
            return
        if not exe:
            return
        if not exe.lower().endswith(".exe") or not os.path.isfile(exe):
            self.show_info_message(t("msg_warning", self.lang),
                                   t("games_invalid", self.lang))
            return
        default = os.path.splitext(os.path.basename(exe))[0]
        try:
            name = simpledialog.askstring(t("games_name_title", self.lang),
                                          t("games_name_prompt", self.lang),
                                          initialvalue=default,
                                          parent=self.root)
        except Exception:
            name = default
        if name is None:
            return
        name = (name or "").strip()
        if not name:
            return
        if name in self.scan_games() or name in self.get_all_services():
            self.show_info_message(t("msg_warning", self.lang),
                                   t("games_exists", self.lang))
            return
        # Capa: tenta a oficial da Steam pelo nome; cai p/ o icone do .exe
        cover = ""
        try:
            jpg = os.path.join(IMAGES_DIR, "%s_logo.jpg" % _safe_icon_basename(name))
            if download_game_cover(name, jpg):
                cover = jpg
        except Exception:
            cover = ""
        if not cover:
            try:
                dest = os.path.join(IMAGES_DIR, "%s_logo.png" % _safe_icon_basename(name))
                if extract_exe_icon(os.path.abspath(exe), dest):
                    cover = dest
            except Exception:
                cover = ""
        try:
            ext = dict(self.settings.get("external_games") or {})
            data = {"exe": os.path.abspath(exe)}
            if cover:
                data["cover"] = cover
            ext[name] = data
            self.settings["external_games"] = ext
            save_settings(self.settings)
        except Exception:
            return
        self.refresh_ui()

    def reextract_external_icon(self, name):
        """Recarrega a capa a partir do icone original do .exe."""
        try:
            exe = (self.settings.get("external_games") or {}).get(name, {}).get("exe", "")
        except Exception:
            exe = ""
        if not exe or not os.path.isfile(exe):
            self.show_info_message(name, t("games_exe_missing", self.lang))
            return
        try:
            dest = os.path.join(IMAGES_DIR, "%s_logo.png" % _safe_icon_basename(name))
            ok = extract_exe_icon(os.path.abspath(exe), dest)
        except Exception:
            ok = False
        if not ok:
            return
        try:
            ext = dict(self.settings.get("external_games") or {})
            data = dict(ext.get(name, {}))
            data["cover"] = dest
            ext[name] = data
            self.settings["external_games"] = ext
            save_settings(self.settings)
            try:
                self.logo_path_cache.pop(name, None)
                self.photo_cache.pop(dest + str(GAME_COVER_SIZE), None)
                self.photo_cache.pop(dest + str(Config.LOGO_SIZE), None)
            except Exception:
                pass
        except Exception:
            pass
        self.refresh_ui()

    def search_game_cover_online(self, name):
        """Busca a capa oficial na Steam (vale p/ pasta, atalho e plataforma).

        Plataforma Steam usa o appid direto (sem busca). Pasta games/Nome
        salva como cover.jpg dentro da pasta. Sem internet ou fora da
        Steam: mantem a capa atual.
        """
        dest = ""
        is_folder = False
        try:
            folder = self.game_folder(name)
            if folder:
                dest = os.path.join(folder, "cover.jpg")
                is_folder = True
            else:
                dest = os.path.join(IMAGES_DIR, "%s_logo.jpg" % _safe_icon_basename(name))
        except Exception:
            return
        try:
            if self.game_is_platform(name):
                data0 = self.game_platform_data(name)
                if data0.get("platform") == "steam" and data0.get("id"):
                    ok = download_steam_cover_by_appid(data0["id"], dest)
                    found = name if ok else None
                else:
                    found = download_game_cover(name, dest)
            else:
                found = download_game_cover(name, dest)
        except Exception:
            found = None
        if not found:
            self.show_info_message(name, t("games_cover_notfound", self.lang))
            try:
                if os.path.isfile(dest) and os.path.getsize(dest) == 0:
                    os.remove(dest)
            except Exception:
                pass
            return
        try:
            if not is_folder:
                if self.game_is_platform(name):
                    plat = dict(self.settings.get("platform_games") or {})
                    data = dict(plat.get(name, {}))
                    data["cover"] = dest
                    plat[name] = data
                    self.settings["platform_games"] = plat
                else:
                    ext = dict(self.settings.get("external_games") or {})
                    data = dict(ext.get(name, {}))
                    data["cover"] = dest
                    ext[name] = data
                    self.settings["external_games"] = ext
                save_settings(self.settings)
            try:
                self.logo_path_cache.pop(name, None)
                self.photo_cache.pop(dest + str(GAME_COVER_SIZE), None)
                self.photo_cache.pop(dest + str(Config.LOGO_SIZE), None)
            except Exception:
                pass
        except Exception:
            pass
        self.refresh_ui()
        self.show_info_message(t("msg_success", self.lang),
                               '"%s" %s' % (found, t("games_cover_found", self.lang)))

    def rename_game(self, name):
        """Renomeia o jogo (atalho .exe, plataforma ou pasta em games/)."""
        try:
            new = simpledialog.askstring(t("games_rename_title", self.lang),
                                         t("games_name_prompt", self.lang),
                                         initialvalue=name,
                                         parent=self.root)
        except Exception:
            return
        if new is None:
            return
        new = (new or "").strip()
        if not new or new == name:
            return
        if new in self.scan_games() or new in self.get_all_services():
            self.show_info_message(t("msg_warning", self.lang),
                                   t("games_exists", self.lang))
            return
        try:
            if self.game_is_platform(name):
                # Seguro: a deteccao casa por plataforma:id, nao pelo nome
                plat = dict(self.settings.get("platform_games") or {})
                data = dict(plat.pop(name, {}))
                try:
                    cover = (data.get("cover") or "")
                    if cover:
                        abs_cover = os.path.abspath(cover)
                        if abs_cover.lower().startswith(os.path.abspath(IMAGES_DIR).lower()):
                            ext2 = os.path.splitext(abs_cover)[1].lower() or ".jpg"
                            dest = os.path.join(IMAGES_DIR, "%s_logo%s"
                                                % (_safe_icon_basename(new), ext2))
                            if not os.path.exists(dest) and os.path.isfile(abs_cover):
                                os.rename(abs_cover, dest)
                                data["cover"] = dest
                except Exception:
                    pass
                plat[new] = data
                self.settings["platform_games"] = plat
            elif self.game_is_external(name):
                ext = dict(self.settings.get("external_games") or {})
                data = dict(ext.pop(name, {}))
                # Renomeia o arquivo da capa junto (evita orfao)
                try:
                    cover = (data.get("cover") or "")
                    if cover:
                        abs_cover = os.path.abspath(cover)
                        if abs_cover.lower().startswith(os.path.abspath(IMAGES_DIR).lower()):
                            ext2 = os.path.splitext(abs_cover)[1].lower() or ".jpg"
                            dest = os.path.join(IMAGES_DIR, "%s_logo%s"
                                                % (_safe_icon_basename(new), ext2))
                            if not os.path.exists(dest) and os.path.isfile(abs_cover):
                                os.rename(abs_cover, dest)
                                data["cover"] = dest
                except Exception:
                    pass
                ext[new] = data
                self.settings["external_games"] = ext
            else:
                old_folder = self.game_folder(name)
                if not old_folder:
                    return
                new_folder = os.path.join(GAMES_DIR, new)
                if os.path.exists(new_folder):
                    self.show_info_message(t("msg_warning", self.lang),
                                           t("games_exists", self.lang))
                    return
                os.rename(old_folder, new_folder)
                # Renomeia capas Trocar Logo que carregam o nome antigo
                try:
                    for key in ("custom_streamings",):
                        custom = dict(self.settings.get(key) or {})
                        if name in custom and isinstance(custom[name], dict):
                            custom[new] = custom.pop(name)
                            self.settings[key] = custom
                except Exception:
                    pass
            # Migra referencias com o nome antigo
            try:
                favs = self.settings.get("game_favorites", [])
                if name in favs:
                    self.settings["game_favorites"] = [new if f == name else f for f in favs]
                colors = self.settings.get("card_colors", {})
                if name in colors:
                    colors[new] = colors.pop(name)
                    self.settings["card_colors"] = colors
            except Exception:
                pass
            save_settings(self.settings)
            try:
                self.logo_path_cache.pop(name, None)
            except Exception:
                pass
        except Exception:
            return
        self.refresh_ui()

    def remove_external_game(self, name):
        def _yes(menu):
            try:
                ext = dict(self.settings.get("external_games") or {})
                old_cover = ""
                if name in ext:
                    try:
                        old_cover = (ext.get(name) or {}).get("cover", "")
                    except Exception:
                        old_cover = ""
                    del ext[name]
                    self.settings["external_games"] = ext
                favs = self.settings.get("game_favorites", [])
                if name in favs:
                    favs.remove(name)
                    self.settings["game_favorites"] = favs
                save_settings(self.settings)
                # Limpa o PNG do icone orfao (so dentro de streaming_images)
                try:
                    if old_cover:
                        abs_cover = os.path.abspath(old_cover)
                        if abs_cover.lower().startswith(os.path.abspath(IMAGES_DIR).lower()):
                            if os.path.isfile(abs_cover):
                                os.remove(abs_cover)
                except Exception:
                    pass
                try:
                    self.logo_path_cache.pop(name, None)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                menu.close()
            except Exception:
                pass
            self.refresh_ui()

        menu = NexusMenuWindow(self, t("delete_confirm", self.lang), [],
                               subtitle=f"{t('delete_question', self.lang)} '{name}'?",
                               icon="\U0001F5D1", width=460)
        menu.set_options([(t("games_remove_link", self.lang),
                           lambda: _yes(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def remove_platform_game(self, name):
        """Remove jogo detectado e ignora em futuras deteccoes."""
        def _yes(menu):
            try:
                plat = dict(self.settings.get("platform_games") or {})
                old_cover = ""
                key = ""
                if name in plat:
                    try:
                        data = plat.get(name) or {}
                        old_cover = data.get("cover", "")
                        key = platform_key(data.get("platform", ""), data.get("id", ""))
                    except Exception:
                        old_cover, key = "", ""
                    del plat[name]
                    self.settings["platform_games"] = plat
                if key:
                    ign = list(self.settings.get("platform_ignored") or [])
                    if key not in ign:
                        ign.append(key)
                    self.settings["platform_ignored"] = ign
                favs = self.settings.get("game_favorites", [])
                if name in favs:
                    favs.remove(name)
                    self.settings["game_favorites"] = favs
                save_settings(self.settings)
                try:
                    if old_cover:
                        abs_cover = os.path.abspath(old_cover)
                        if abs_cover.lower().startswith(os.path.abspath(IMAGES_DIR).lower()):
                            if os.path.isfile(abs_cover):
                                os.remove(abs_cover)
                except Exception:
                    pass
                try:
                    self.logo_path_cache.pop(name, None)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                menu.close()
            except Exception:
                pass
            self.refresh_ui()

        menu = NexusMenuWindow(self, t("delete_confirm", self.lang), [],
                               subtitle=f"{t('delete_question', self.lang)} '{name}'?",
                               icon="\U0001F5D1", width=460)
        menu.set_options([(t("games_remove_detected", self.lang),
                           lambda: _yes(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def restore_ignored_platform(self):
        """Volta a oferecer jogos ignorados e roda a deteccao de novo."""
        try:
            self.settings["platform_ignored"] = []
            save_settings(self.settings)
        except Exception:
            pass
        try:
            self.close_sidebar()
        except Exception:
            pass
        self.detect_platform_games()

    def detect_platform_games(self):
        """Detecta instalados (Steam/Epic/Xbox) em 2o plano e importa."""
        if getattr(self, "_detecting", False):
            return
        self._detecting = True
        try:
            self.show_info_message(t("games_detect", self.lang),
                                   t("games_detecting", self.lang))
        except Exception:
            pass

        def _cover_for(g, dest):
            plat = g.get("platform", "")
            try:
                if plat == "steam":
                    return bool(download_steam_cover_by_appid(g.get("id", ""), dest))
                if plat == "xbox":
                    src = find_xbox_logo(g.get("location", ""), g.get("logos") or [])
                    if src and os.path.isfile(src):
                        try:
                            from PIL import Image as _Img
                            im = _Img.open(src)
                            im.load()
                            im.save(dest)
                            try:
                                im.close()
                            except Exception:
                                pass
                            return True
                        except Exception:
                            try:
                                copy2(src, dest)
                                return True
                            except Exception:
                                return False
                    return False
                # Epic: busca na Steam pelo nome; cai p/ icone do .exe
                if download_game_cover(g.get("name", ""), dest):
                    return True
                exe = g.get("exe", "")
                if exe and os.path.isfile(exe):
                    return bool(extract_exe_icon(exe, dest))
            except Exception:
                pass
            return False

        def _work():
            found = []
            for scanner in (scan_steam_games, scan_epic_games, scan_xbox_games):
                try:
                    found += scanner()
                except Exception:
                    continue
            # Capas ainda no worker (rede/disco) p/ nao travar a UI
            try:
                os.makedirs(IMAGES_DIR, exist_ok=True)
            except Exception:
                pass
            for g in found:
                try:
                    dest = os.path.join(IMAGES_DIR, "%s_logo.jpg"
                                        % _safe_icon_basename(g.get("name", "jogo")))
                    g["_cover_dest"] = dest
                    if _cover_for(g, dest):
                        g["_cover"] = dest
                except Exception:
                    continue
            try:
                self.root.after(0, self._finish_detect, found)
            except Exception:
                self._detecting = False

        try:
            threading.Thread(target=_work, daemon=True).start()
        except Exception:
            self._detecting = False

    def _finish_detect(self, found):
        self._detecting = False
        try:
            ignored = set(self.settings.get("platform_ignored") or [])
            cur = dict(self.settings.get("platform_games") or {})
            seen_keys = set()
            added, updated = [], []
            for g in found or []:
                key = platform_key(g.get("platform", ""), g.get("id", ""))
                seen_keys.add(key)
                if key in ignored:
                    continue
                same = None
                for n, d in cur.items():
                    try:
                        if ((d.get("platform") == g.get("platform"))
                                and str(d.get("id")) == str(g.get("id"))):
                            same = n
                            break
                    except Exception:
                        continue
                if same is not None:
                    try:
                        data = dict(cur[same])
                        for f in ("location", "exe", "args", "pfn", "appid"):
                            if g.get(f):
                                data[f] = g[f]
                        cur[same] = data
                        updated.append(same)
                    except Exception:
                        pass
                    continue
                name, base, i = g.get("name", "Jogo"), g.get("name", "Jogo"), 2
                try:
                    while (name in self.scan_games()
                           or name in self.get_all_services()):
                        name = "%s (%d)" % (base, i)
                        i += 1
                except Exception:
                    pass
                data = {"platform": g.get("platform", ""),
                        "id": g.get("id", ""),
                        "location": g.get("location", ""),
                        "exe": g.get("exe", ""),
                        "args": g.get("args", ""),
                        "pfn": g.get("pfn", ""),
                        "appid": g.get("appid", "")}
                if g.get("_cover") and os.path.isfile(g["_cover"]):
                    data["cover"] = g["_cover"]
                cur[name] = data
                added.append(name)
            removed = []
            for n in list(cur):
                try:
                    k = platform_key((cur[n] or {}).get("platform", ""),
                                     (cur[n] or {}).get("id", ""))
                except Exception:
                    continue
                if k not in seen_keys:
                    try:
                        cov = (cur[n] or {}).get("cover", "")
                        if cov:
                            ac = os.path.abspath(cov)
                            if ac.lower().startswith(os.path.abspath(IMAGES_DIR).lower()):
                                if os.path.isfile(ac):
                                    os.remove(ac)
                    except Exception:
                        pass
                    try:
                        favs = self.settings.get("game_favorites", [])
                        if n in favs:
                            favs.remove(n)
                    except Exception:
                        pass
                    try:
                        self.logo_path_cache.pop(n, None)
                    except Exception:
                        pass
                    del cur[n]
                    removed.append(n)
            self.settings["platform_games"] = cur
            save_settings(self.settings)
            self.refresh_ui()
            try:
                msg = t("games_detected", self.lang) % (len(added), len(removed))
                detail = ", ".join(added[:8]) if added else ""
                self.show_info_message(t("msg_success", self.lang),
                                       msg + (("\n" + detail) if detail else ""))
            except Exception:
                pass
        except Exception:
            try:
                self.refresh_ui()
            except Exception:
                pass

    def open_game_location(self, name):
        """Abre no Explorer a pasta do jogo (interno/plataforma) ou do .exe."""
        try:
            if self.game_is_platform(name):
                loc = self.game_platform_data(name).get("location", "")
                if loc and os.path.exists(loc):
                    os.startfile(loc)
                return
            if self.game_is_external(name):
                exe = (self.settings.get("external_games") or {}).get(name, {}).get("exe", "")
                if exe and os.path.exists(exe):
                    try:
                        subprocess.Popen(["explorer", "/select,", os.path.abspath(exe)])
                        return
                    except Exception:
                        os.startfile(os.path.dirname(os.path.abspath(exe)))
                        return
                return
            folder = self.game_folder(name)
            if folder:
                os.startfile(folder)
        except Exception:
            pass

    def backfill_missing_game_icons(self, names):
        """Para atalhos antigos sem capa: extrai o icone em 2o plano e atualiza."""
        try:
            todo = []
            for n in names or []:
                try:
                    if not self.game_is_external(n):
                        continue
                    data = (self.settings.get("external_games") or {}).get(n, {})
                    cover = (data or {}).get("cover", "")
                    exe = (data or {}).get("exe", "")
                    if cover and os.path.isfile(cover):
                        continue
                    if not exe or not os.path.isfile(exe):
                        continue
                    todo.append((n, os.path.abspath(exe),
                                 os.path.join(IMAGES_DIR, "%s_logo.png" % _safe_icon_basename(n))))
                except Exception:
                    continue
            if not todo:
                return
        except Exception:
            return

        def _work():
            changed = False
            for n, exe, dest in todo:
                try:
                    if extract_exe_icon(exe, dest):
                        ext = dict(self.settings.get("external_games") or {})
                        data = dict(ext.get(n, {}))
                        data["cover"] = dest
                        # exe pode ter mudado de letra? mantem o atual se valido
                        if not data.get("exe"):
                            data["exe"] = exe
                        ext[n] = data
                        self.settings["external_games"] = ext
                        changed = True
                except Exception:
                    continue
            if changed:
                try:
                    save_settings(self.settings)
                except Exception:
                    pass
                try:
                    self.root.after(0, self.refresh_ui)
                except Exception:
                    pass

        try:
            threading.Thread(target=_work, daemon=True).start()
        except Exception:
            pass

    def render_games(self):
        names = self.scan_games()
        names = [n for n in names if self._match_search(n)]
        self.backfill_missing_game_icons(names)
        mode = self.get_view_mode("games")
        try:
            favs = set(self.settings.get("game_favorites", []))
        except Exception:
            favs = set()
        names.sort(key=lambda n: (0 if n in favs else 1, n.lower()))
        bar = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        bar.pack(fill="x", padx=30, pady=(20, 0))
        tk.Button(bar, text=f"\U0001F4C1 {t('games_open', self.lang)}",
                  font=("Segoe UI", 13, "bold"),
                  bg=Config.ACCENT, fg="white",
                  activebackground=Config.ACCENT_GLOW, activeforeground="white",
                  relief="flat", cursor="hand2", bd=0, padx=20, pady=8,
                  command=self.open_games_folder).pack(side="left", padx=(0, 10))
        tk.Button(bar, text=f"\u2795 {t('games_add_exe', self.lang)}",
                  font=("Segoe UI", 13, "bold"),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                  activebackground=Config.BG_CARD_HOVER,
                  activeforeground=Config.TEXT_PRIMARY,
                  relief="flat", cursor="hand2", bd=0, padx=20, pady=8,
                  command=self.add_external_game).pack(side="left", padx=(0, 10))
        tk.Button(bar, text=f"\u21BB {t('games_refresh', self.lang)}",
                  font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                  activebackground=Config.BG_CARD_HOVER,
                  activeforeground=Config.TEXT_PRIMARY,
                  relief="flat", cursor="hand2", bd=0, padx=20, pady=8,
                  command=lambda: self.switch_tab("games")).pack(side="left")
        tk.Button(bar, text=f"\U0001F50D {t('games_detect', self.lang)}",
                  font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                  activebackground=Config.BG_CARD_HOVER,
                  activeforeground=Config.TEXT_PRIMARY,
                  relief="flat", cursor="hand2", bd=0, padx=20, pady=8,
                  command=self.detect_platform_games).pack(side="left", padx=(10, 0))
        view_box = tk.Frame(bar, bg=Config.BG_PRIMARY)
        view_box.pack(side="right")
        for m in VIEW_MODES:
            active = (m == mode)
            tk.Button(view_box, text="%s %s" % (VIEW_MODE_ICONS.get(m, ""), t("view_" + m, self.lang)),
                      font=("Segoe UI", 10, "bold" if active else "normal"),
                      bg=(Config.ACCENT if active else Config.BG_CARD),
                      fg=("white" if active else Config.TEXT_SECONDARY),
                      activebackground=Config.ACCENT_GLOW, activeforeground="white",
                      relief="flat", cursor="hand2", bd=0, padx=10, pady=5,
                      command=lambda m=m: self.set_view_mode("games", m)).pack(side="left", padx=(6, 0))
        self.render_search_bar("games")
        if names:
            title = f"\U0001F3AE {t('games_title', self.lang)}"
            if mode == "grid":
                self.render_grid(title, names)
            elif mode in ("list", "details"):
                self.render_list(title, names, details=(mode == "details"))
            else:
                self.render_section(title, names)
        else:
            tk.Label(self.scroll_frame, text=t("games_empty", self.lang),
                     font=("Segoe UI", 18), fg=Config.TEXT_SECONDARY,
                     bg=Config.BG_PRIMARY, justify="center",
                     wraplength=900).pack(expand=True, pady=100)

    def launch_game(self, name):
        if self.game_is_platform(name):
            try:
                if self.launch_platform(self.game_platform_data(name)):
                    self.db.add_history(name)
                else:
                    self.show_info_message(name, t("games_noexe", self.lang))
            except Exception:
                self.show_info_message(name, t("games_noexe", self.lang))
            return
        if self.game_is_external(name):
            exe = self.game_exe_for(name)
            if not exe:
                self.show_info_message(name, t("games_exe_missing", self.lang))
                return
            try:
                subprocess.Popen([exe], cwd=os.path.dirname(exe) or None)
                self.db.add_history(name)
            except Exception:
                self.show_info_message(name, t("games_exe_missing", self.lang))
            return
        folder = self.game_folder(name)
        if not folder:
            return
        exe = find_game_exe(folder)
        if not exe:
            self.show_info_message(name, t("games_noexe", self.lang))
            return
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
            self.db.add_history(name)
        except Exception:
            self.show_info_message(name, t("games_noexe", self.lang))

    def launch_platform(self, data):
        """Abre jogo de plataforma (Steam/Epic/Xbox). True se disparou."""
        plat = (data or {}).get("platform", "")
        if plat == "steam":
            try:
                os.startfile("steam://rungameid/%s" % data.get("id", ""))
                return True
            except Exception:
                pass
            try:
                exe = find_game_exe(data.get("location", ""))
                if exe:
                    subprocess.Popen([exe], cwd=os.path.dirname(exe))
                    return True
            except Exception:
                pass
            return False
        if plat == "epic":
            exe = (data or {}).get("exe", "")
            if exe and os.path.isfile(exe):
                try:
                    import shlex as _shlex
                    args = _shlex.split(data.get("args", "") or "", posix=False)
                except Exception:
                    args = []
                try:
                    subprocess.Popen([exe] + args, cwd=os.path.dirname(exe))
                    return True
                except Exception:
                    return False
            try:
                os.startfile("com.epicgames.launcher://apps/%s?action=launch&silent=true"
                             % data.get("id", ""))
                return True
            except Exception:
                return False
        if plat == "xbox":
            try:
                launch_uwp(data.get("pfn", ""),
                            data.get("appid", "") or "App")
                return True
            except Exception:
                return False
        return False
