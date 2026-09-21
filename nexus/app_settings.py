# -*- coding: utf-8 -*-
"""Menu contexto, sidebar, tema, idioma e update (extraido sem alteracao)."""

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import urllib.parse
from datetime import datetime
from shutil import copy2
from tkinter import filedialog

from .config import Config, save_settings
from .dialogs import (
    GuideWindow, NexusMenuWindow, NexusTextDialog,
    _modal_alive, sniff_numeric_entry, top_modal,
)
from .games import GAME_COVER_SIZE
from .i18n import t
from .keyboard import NexusKeyboard
from .panels import (
    AdicionarPanel, ControlesPanel, GamepadConfigWindow, IdiomaPanel,
    PerfilPanel, SistemaPanel, SomPanel,
)
from .paths import (
    BROWSER_PROCS, IMAGES_DIR, browser_profile_size, browser_running,
    clear_browser_profile, service_profile_size, clear_service_profile,
)
from .update import fetch_latest_release
from .version import APP_VERSION, ver_tuple
from .win32 import kill_process_tree


class AppSettingsMixin:
    """Chrome do app: menus, paineis, tema, idioma, update, quit."""

    # ===================== CONTEXT MENU =====================
    def show_context_menu(self, event, name):
        # Menu proprio da aba Jogos (pastas, atalhos .exe e plataformas)
        if self.current_tab == "games" or self.game_is_external(name) or self.game_folder(name) or self.game_is_platform(name):
            menu = tk.Menu(self.root, tearoff=0, bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                            activebackground=Config.ACCENT, activeforeground="white",
                            font=("Segoe UI", 12), bd=0)
            menu.add_command(label=f"\u25B6 {t('ctx_open', self.lang)}", command=lambda: self.on_card_click(None, name))
            if self.is_favorite(name):
                menu.add_command(label=f"\u2716 {t('ctx_remove_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
            else:
                menu.add_command(label=f"\u2B50 {t('ctx_add_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
            menu.add_separator()
            menu.add_command(label=f"\U0001F5BC {t('ctx_change_logo', self.lang)}", command=lambda: self.change_logo(name))
            menu.add_separator()
            if self.game_is_platform(name):
                menu.add_command(label=f"\U0001F50D {t('games_search_cover', self.lang)}",
                                 command=lambda: self.search_game_cover_online(name))
                menu.add_command(label=f"\u270F {t('games_rename', self.lang)}",
                                 command=lambda: self.rename_game(name))
                menu.add_command(label=f"\U0001F4C1 {t('games_open_folder', self.lang)}",
                                 command=lambda: self.open_game_location(name))
                menu.add_command(label=f"\U0001F5D1 {t('games_remove_detected', self.lang)}",
                                 command=lambda: self.remove_platform_game(name))
            elif self.game_is_external(name):
                menu.add_command(label=f"\U0001F50D {t('games_search_cover', self.lang)}",
                                 command=lambda: self.search_game_cover_online(name))
                menu.add_command(label=f"\u270F {t('games_rename', self.lang)}",
                                 command=lambda: self.rename_game(name))
                menu.add_command(label=f"\U0001F504 {t('games_reload_icon', self.lang)}",
                                 command=lambda: self.reextract_external_icon(name))
                menu.add_command(label=f"\U0001F4C2 {t('games_open_exe_folder', self.lang)}",
                                 command=lambda: self.open_game_location(name))
                menu.add_command(label=f"\U0001F5D1 {t('games_remove_link', self.lang)}",
                                 command=lambda: self.remove_external_game(name))
            else:
                menu.add_command(label=f"\U0001F50D {t('games_search_cover', self.lang)}",
                                 command=lambda: self.search_game_cover_online(name))
                menu.add_command(label=f"\u270F {t('games_rename', self.lang)}",
                                 command=lambda: self.rename_game(name))
                menu.add_command(label=f"\U0001F4C1 {t('games_open_folder', self.lang)}",
                                 command=lambda: self.open_game_location(name))
            menu.tk_popup(event.x_root, event.y_root)
            return
        menu = tk.Menu(self.root, tearoff=0, bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                        activebackground=Config.ACCENT, activeforeground="white",
                        font=("Segoe UI", 12), bd=0)
        menu.add_command(label=f"\u25B6 {t('ctx_open', self.lang)}", command=lambda: self.on_card_click(None, name))
        if self.is_favorite(name):
            menu.add_command(label=f"\u2716 {t('ctx_remove_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
        else:
            menu.add_command(label=f"\u2B50 {t('ctx_add_fav', self.lang)}", command=lambda: self.toggle_favorite(name))
        menu.add_separator()
        menu.add_command(label=f"\U0001F5BC {t('ctx_change_logo', self.lang)}", command=lambda: self.change_logo(name))
        menu.add_separator()
        menu.add_command(label=f"\U0001F5D1 {t('ctx_delete', self.lang)}", command=lambda: self.delete_streaming(name))
        menu.add_command(label=f"\U0001F4CB {t('ctx_copy_url', self.lang)}",
                         command=lambda: self.root.clipboard_append(
                             self.get_all_services().get(name, {}).get("url", "")))
        menu.tk_popup(event.x_root, event.y_root)

    def is_game_name(self, name):
        """Nome e jogo (pasta, atalho .exe ou plataforma)?"""
        try:
            return bool(self.game_folder(name) or self.game_is_external(name)
                        or self.game_is_platform(name))
        except Exception:
            return False

    def game_favorites(self):
        try:
            return list(self.settings.get("game_favorites", []) or [])
        except Exception:
            return []

    def is_favorite(self, name):
        """Estrela: consulta a lista certa (jogos x aplicativos)."""
        try:
            if self.is_game_name(name):
                return name in (self.settings.get("game_favorites", []) or [])
            return name in (self.settings.get("favorites", []) or [])
        except Exception:
            return False

    def _migrate_favorites(self):
        """Uma vez: jogos que cairam em favorites mudam p/ game_favorites."""
        try:
            favs = list(self.settings.get("favorites", []) or [])
            gfavs = list(self.settings.get("game_favorites", []) or [])
            moved = False
            for n in list(favs):
                try:
                    if self.is_game_name(n):
                        favs.remove(n)
                        if n not in gfavs:
                            gfavs.append(n)
                        moved = True
                except Exception:
                    continue
            if moved:
                self.settings["favorites"] = favs
                self.settings["game_favorites"] = gfavs
                save_settings(self.settings)
        except Exception:
            pass

    def toggle_favorite(self, name):
        if self.is_game_name(name):
            favs = list(self.settings.get("game_favorites", []) or [])
            key, other = "game_favorites", "favorites"
        else:
            favs = list(self.settings.get("favorites", []) or [])
            key, other = "favorites", "game_favorites"
        if name in favs:
            favs.remove(name)
        else:
            favs.append(name)
            try:
                wrong = list(self.settings.get(other, []) or [])
                if name in wrong:
                    wrong.remove(name)
                    self.settings[other] = wrong
            except Exception:
                pass
        self.settings[key] = favs
        save_settings(self.settings)
        self.refresh_ui()

    def delete_streaming(self, name):
        def _yes(menu):
            custom = self.settings.get("custom_streamings", {})
            if name in custom:
                del custom[name]
                self.settings["custom_streamings"] = custom
            else:
                hidden = self.settings.get("hidden_streamings", [])
                if name not in hidden:
                    hidden.append(name)
                self.settings["hidden_streamings"] = hidden
            favs = self.settings.get("favorites", [])
            if name in favs:
                favs.remove(name)
                self.settings["favorites"] = favs
            save_settings(self.settings)
            self.refresh_ui()
            menu.close()

        menu = NexusMenuWindow(self, t("delete_confirm", self.lang), [],
                               subtitle=f"{t('delete_question', self.lang)} '{name}'?",
                               icon="\U0001F5D1", width=460)
        menu.set_options([(t("ctx_delete", self.lang),
                           lambda: _yes(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def show_info_message(self, title, message):
        menu = NexusMenuWindow(self, title, [], subtitle=message,
                               icon="\u2139", width=440)
        menu.set_options([(t("sidebar_close", self.lang), menu.close)])

    def change_logo(self, name, path=None):
        if path is None:
            filepath = filedialog.askopenfilename(
                title=f"Logo de {name}",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.ico"), ("Todas", "*.*")])
        else:
            filepath = path
        if filepath:
            ext = os.path.splitext(filepath)[1].lower()
            dest = os.path.join(IMAGES_DIR, f"{name}_logo{ext}")
            try:
                copy2(filepath, dest)
            except:
                dest = filepath
            # Atalho/plataforma: guarda a capa no registro do jogo
            if self.game_is_external(name):
                try:
                    extg = dict(self.settings.get("external_games") or {})
                    data = dict(extg.get(name, {}))
                    data["cover"] = dest
                    extg[name] = data
                    self.settings["external_games"] = extg
                except Exception:
                    pass
            elif self.game_is_platform(name):
                try:
                    plat = dict(self.settings.get("platform_games") or {})
                    data = dict(plat.get(name, {}))
                    data["cover"] = dest
                    plat[name] = data
                    self.settings["platform_games"] = plat
                except Exception:
                    pass
            else:
                custom = self.settings.get("custom_streamings", {})
                if name not in custom:
                    custom[name] = {}
                custom[name]["image"] = dest
                self.settings["custom_streamings"] = custom
            try:
                self.logo_path_cache.pop(name, None)
                self.photo_cache.pop(dest + str(GAME_COVER_SIZE), None)
                self.photo_cache.pop(dest + str(Config.LOGO_SIZE), None)
                self.photo_cache.pop(dest + "40", None)
            except Exception:
                pass
            save_settings(self.settings)
            self.refresh_ui()

    # ===================== SIDEBAR =====================
    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.close_sidebar()
        else:
            self.open_sidebar()

    def open_sidebar(self):
        self.sidebar_visible = True
        self.sidebar_menu_index = 0
        now = datetime.now()
        self.sidebar_time.config(text=now.strftime("%H:%M"))
        self.sidebar_date.config(text=now.strftime("%A, %d/%m/%Y"))
        self.sidebar.place(x=0, y=0, relheight=1)
        self.sidebar.lift()
        self.update_sidebar_focus()

    def close_sidebar(self):
        self.sidebar_visible = False
        self.sidebar.place(x=-Config.SIDEBAR_WIDTH, y=0, relheight=1)

    # ===================== NOTIFICACOES (painel direito) =====================
    NOTIF_WIDTH = 360

    def build_notif_panel(self):
        self.notif_visible = False
        self.notif_panel = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR,
                                    width=self.NOTIF_WIDTH)
        self.notif_panel.pack_propagate(False)
        self.notif_panel.place_forget()

    def toggle_notif_panel(self):
        try:
            top = top_modal(self)
            if isinstance(top, (NexusKeyboard, NexusTextDialog, NexusMenuWindow)):
                return
        except Exception:
            pass
        if self.notif_visible:
            self.close_notif_panel()
        else:
            self.open_notif_panel()

    def open_notif_panel(self):
        if self.sidebar_visible:
            self.close_sidebar()
        self.close_sidepanel()
        self.notif_visible = True
        self.render_notif_panel()
        self.notif_panel.place(relx=1.0, y=0, relheight=1, anchor="ne",
                               width=self.NOTIF_WIDTH)
        self.notif_panel.lift()
        self._mark_notif_seen()

    def close_notif_panel(self):
        self.notif_visible = False
        try:
            self.notif_panel.place_forget()
        except Exception:
            pass

    def _notif_newer_tag(self):
        """Tag mais nova que a atual (ou None)."""
        try:
            info = self._latest_release or {}
            tag = (info.get("tag") or "").strip()
            if tag and ver_tuple(tag) > ver_tuple(APP_VERSION):
                return tag
        except Exception:
            pass
        return None

    def _refresh_notif_badge(self):
        try:
            tag = self._notif_newer_tag()
            seen = (self.settings.get("notif_seen_update", "")
                    if isinstance(self.settings, dict) else "")
            if tag and tag != seen and tag != self.settings.get("update_seen", ""):
                self.notif_badge.config(text="1")
                self.notif_badge.place(relx=0.7, rely=0.12)
                self.notif_btn.configure(fg="#e94560")
            else:
                self.notif_badge.place_forget()
                self.notif_btn.configure(fg=Config.TEXT_SECONDARY)
        except Exception:
            pass

    def _mark_notif_seen(self):
        try:
            tag = self._notif_newer_tag()
            if tag and isinstance(self.settings, dict):
                self.settings["notif_seen_update"] = tag
                save_settings(self.settings)
            self.notif_badge.place_forget()
            self.notif_btn.configure(fg=Config.TEXT_SECONDARY)
        except Exception:
            pass

    def _notif_card(self, parent, title, subtitle, accent, on_click=None):
        card = tk.Frame(parent, bg=Config.BG_CARD, highlightbackground=accent,
                        highlightthickness=2)
        card.pack(fill="x", padx=16, pady=6)
        inner = tk.Frame(card, bg=Config.BG_CARD)
        inner.pack(fill="x", padx=12, pady=10)
        tk.Label(inner, text=title, font=("Segoe UI", 12, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                 anchor="w", justify="left", wraplength=self.NOTIF_WIDTH - 60).pack(fill="x")
        if subtitle:
            tk.Label(inner, text=subtitle, font=("Segoe UI", 10),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD,
                     anchor="w", justify="left",
                     wraplength=self.NOTIF_WIDTH - 60).pack(fill="x", pady=(4, 0))
        if on_click is not None:
            for w in (card, inner):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e: on_click())
                for ch in w.winfo_children():
                    try:
                        ch.configure(cursor="hand2")
                        ch.bind("<Button-1>", lambda e: on_click())
                    except Exception:
                        pass
        return card

    def _notif_section(self, parent, text):
        tk.Label(parent, text=text.upper(), font=("Segoe UI", 11, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x", padx=16, pady=(14, 2))

    def render_notif_panel(self):
        try:
            for w in self.notif_panel.winfo_children():
                w.destroy()
        except Exception:
            return
        lang = self.lang
        head = tk.Frame(self.notif_panel, bg=Config.BG_SIDEBAR)
        head.pack(fill="x", pady=(20, 4))
        tk.Label(head, text="\U0001F514 " + t("notif_title", lang),
                 font=("Segoe UI", 18, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR).pack(side="left", padx=16)
        tk.Button(head, text="\u2715", font=("Segoe UI", 12),
                  bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                  activebackground="#e94560", activeforeground="white",
                  relief="flat", cursor="hand2", bd=0, padx=10,
                  command=self.close_notif_panel).pack(side="right", padx=12)
        tk.Frame(self.notif_panel, bg=Config.BORDER, height=1).pack(
            fill="x", padx=16, pady=(4, 2))

        # ---- Do Nexus: atualizacoes ----
        self._notif_section(self.notif_panel, t("notif_nexus", lang))
        tag = self._notif_newer_tag()
        if tag:
            try:
                info = self._latest_release or {}
                notes = (info.get("notes") or "").strip()
                date = (info.get("date") or "").strip()
                changes = [c for c in (info.get("changes") or []) if c][:6]
            except Exception:
                notes, date, changes = "", "", []
            # O card diz O QUE foi atualizado: resumo dos commits
            # ("Simbolos no ?123", ...) ou as notas da release.
            parts = []
            if date:
                parts.append(date)
            if changes:
                parts.append(t("notif_whatsnew", lang))
                parts.extend("\u2022 " + c for c in changes)
            elif notes:
                parts.append(notes)
            sub = "\n".join(parts)
            self._notif_card(self.notif_panel, t("notif_upd_avail", lang) % tag,
                             sub, "#e94560",
                             on_click=lambda: self._notif_go_update())
        else:
            self._notif_card(self.notif_panel, t("notif_upd_cur", lang) % APP_VERSION,
                             "", Config.ACCENT)
        tk.Button(self.notif_panel, text="\u27F3 " + t("notif_check", lang),
                  font=("Segoe UI", 11), fg=Config.TEXT_SECONDARY,
                  bg=Config.BG_CARD, activebackground=Config.BG_CARD_HOVER,
                  activeforeground=Config.TEXT_PRIMARY,
                  relief="flat", cursor="hand2", padx=12, pady=4,
                  command=self._notif_manual_check).pack(anchor="e", padx=16, pady=(2, 0))

    def _notif_go_update(self):
        info = self._latest_release
        self.close_notif_panel()
        if info:
            self.offer_update(info)

    def _notif_manual_check(self):
        threading.Thread(target=self._update_check_thread,
                         args=(False,), daemon=True).start()

    def show_gamepad_info(self):
        self.close_sidebar()
        if _modal_alive(self.pad_window):
            try:
                self.pad_window.win.lift()
            except Exception:
                pass
            return
        GamepadConfigWindow(self)

    def open_keyboard(self, entry=None, mode="auto"):
        try:
            kb = self.kb_window
            if _modal_alive(kb):
                try:
                    kb.force_front()
                except Exception:
                    pass
                return
        except Exception:
            pass
        numeric = False
        if mode == "numeric":
            numeric = True
        elif mode != "text":
            numeric = sniff_numeric_entry(entry)
        NexusKeyboard(self, entry, numeric=numeric)

    def bind_keyboard_popup(self, entry, mode="auto"):
        """Foco via controle abre o teclado sozinho (letras ou numerico).
        Clique do mouse ou Tab do teclado nao abrem (usa o teclado fisico)."""
        try:
            entry.kb_mode = mode
            entry.bind("<FocusIn>",
                       lambda e, ent=entry: self._entry_focused(ent), add="+")
        except Exception:
            pass

    def _entry_focused(self, entry):
        try:
            if not getattr(self, "using_gamepad", False):
                return
            if _modal_alive(self.kb_window):
                return
            mode = getattr(entry, "kb_mode", "auto") or "auto"
            self.open_keyboard(entry, mode=mode)
        except Exception:
            pass

    def confirm_clear_browser_profile(self):
        self.close_sidebar()
        if browser_running():
            self.show_info_message(t("msg_warning", self.lang),
                                   t("cache_in_use", self.lang))
            return
        try:
            size_mb = browser_profile_size() / 1048576.0
        except Exception:
            size_mb = 0.0
        menu = NexusMenuWindow(self, t("settings_clear_cache", self.lang), [],
                               subtitle=t("cache_confirm", self.lang) % size_mb,
                               icon="\U0001F9F9", width=480)
        menu.set_options([(t("cache_clear_yes", self.lang),
                           lambda: self.do_clear_browser_profile(menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def do_clear_browser_profile(self, menu):
        ok = clear_browser_profile()
        try:
            menu.close()
        except Exception:
            pass
        self.show_info_message(
            t("msg_success", self.lang) if ok else t("msg_warning", self.lang),
            t("cache_cleared", self.lang) if ok else t("cache_in_use", self.lang))

    def confirm_clear_service_profile(self, name):
        self.close_sidebar()
        if browser_running():
            self.show_info_message(t("msg_warning", self.lang),
                                   t("cache_in_use", self.lang))
            return
        try:
            size_mb = service_profile_size(name) / 1048576.0
        except Exception:
            size_mb = 0.0
        menu = NexusMenuWindow(self, name, [],
                               subtitle=t("cache_confirm", self.lang) % size_mb,
                               icon="\U0001F9F9", width=480)
        menu.set_options([(t("cache_clear_yes", self.lang),
                           lambda: self.do_clear_service_profile(name, menu)),
                          (t("sidebar_close", self.lang), menu.close)])

    def do_clear_service_profile(self, name, menu):
        ok = clear_service_profile(name)
        try:
            menu.close()
        except Exception:
            pass
        self.show_info_message(
            t("msg_success", self.lang) if ok else t("msg_warning", self.lang),
            t("cache_cleared", self.lang) if ok else t("cache_in_use", self.lang))

    # ===================== ADD STREAMING =====================
    def browse_image(self, entry):
        fp = filedialog.askopenfilename(
            title="Escolher logo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.ico"), ("Todas", "*.*")])
        if fp:
            entry.delete(0, "end")
            entry.insert(0, fp)

    def add_new_streaming(self):
        name = self.add_entries.get(t("add_name", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        url = self.add_entries.get(t("add_url", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        cat = self.add_entries.get(t("add_category", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        icon = self.add_entries.get(t("add_emoji", self.lang), type("x", (), {"get": lambda: ""})).get().strip()
        img = self.add_entries.get(t("add_logo", self.lang), type("x", (), {"get": lambda: ""})).get().strip()

        if not name or not url:
            self.show_info_message(t("msg_warning", self.lang), t("add_warning", self.lang))
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        custom = self.settings.get("custom_streamings", {})
        data = {"url": url, "category": cat or "Filmes", "icon": icon or "\U0001F4F0",
                "color": Config.ACCENT, "deep_link": "", "url_template": url,
                "top_content": []}
        if img and os.path.exists(img):
            ext = os.path.splitext(img)[1].lower()
            dest = os.path.join(IMAGES_DIR, f"{name}_logo{ext}")
            try:
                copy2(img, dest)
                data["image"] = dest
            except:
                data["image"] = img
        custom[name] = data
        self.settings["custom_streamings"] = custom
        try:
            self.logo_path_cache.pop(name, None)
        except Exception:
            pass
        if name not in self.settings.get("favorites", []):
            self.settings["favorites"].append(name)
        save_settings(self.settings)
        self.show_info_message(t("msg_success", self.lang), f'"{name}" {t("add_success", self.lang)}')
        self.refresh_ui()

    # ===================== QA OVERLAY =====================
    def close_qa(self):
        self.qa_visible = False
        self.dim_overlay.place_forget()
        self.qa_frame.place_forget()

    # ===================== RESOLUTION =====================
    def open_resolution(self):
        self.close_sidebar()
        menu = NexusMenuWindow(self, t("res_title", self.lang),
                               [], icon="\U0001F5A9")
        cur = self.settings.get("resolution_mode", "fullscreen")
        options = [
            (t("res_fullscreen", self.lang), "fullscreen"),
            ("1920x1080", "1920x1080"),
            ("1400x900", "1400x900"),
            ("1280x720", "1280x720"),
            (t("res_windowed", self.lang), "windowed"),
        ]
        opts = [((("\u2713 " if mode == cur else "") + text),
                 lambda m=mode: self.set_resolution(m, menu)) for text, mode in options]
        opts.append((t("res_close", self.lang), menu.close))
        menu.set_options(opts)

    def set_resolution(self, mode, win=None):
        self.settings["resolution_mode"] = mode
        if mode == "fullscreen":
            self.root.attributes("-fullscreen", True)
        elif mode == "windowed":
            self.root.attributes("-fullscreen", False)
            self.root.geometry("1200x800")
        else:
            self.root.attributes("-fullscreen", False)
            self.root.geometry(mode)
        save_settings(self.settings)
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    # ===================== THEME =====================
    THEME_COLORS = [("#7c4dff", "Purple"), ("#e94560", "Red"),
                    ("#00bcd4", "Cyan"), ("#00c853", "Green"),
                    ("#ffd600", "Yellow"), ("#ff4081", "Pink"),
                    ("#ff6d00", "Orange"), ("#c44100", "Steam")]
    THEME_WIDTH = 360
    THEME_COLS = 4

    def open_theme_picker(self):
        # Virou painel lateral (antes: dialogo central).
        self.close_sidebar()
        self.close_sidepanel()
        if getattr(self, "notif_visible", False):
            self.close_notif_panel()
        self.theme_visible = True
        self.render_theme_panel()
        self._show_theme_panel()

    def build_theme_panel(self):
        self.theme_panel = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR,
                                    width=self.THEME_WIDTH)
        self.theme_panel.pack_propagate(False)
        self.theme_panel.place_forget()
        self.theme_swatches = []

    def _show_theme_panel(self):
        try:
            self.theme_panel.place(relx=1.0, y=0, relheight=1, anchor="ne",
                                   width=self.THEME_WIDTH)
            self.theme_panel.lift()
        except Exception:
            pass

    def toggle_theme_panel(self):
        if self.theme_visible:
            self.close_theme_panel()
        else:
            self.open_theme_picker()

    def close_theme_panel(self):
        self.theme_visible = False
        try:
            self.theme_panel.place_forget()
        except Exception:
            pass

    def render_theme_panel(self):
        try:
            for w in self.theme_panel.winfo_children():
                w.destroy()
        except Exception:
            return
        self.theme_swatches = []
        lang = self.lang
        head = tk.Frame(self.theme_panel, bg=Config.BG_SIDEBAR)
        head.pack(fill="x", pady=(20, 4))
        tk.Label(head, text="\U0001F3A8 " + t("theme_title", lang),
                 font=("Segoe UI", 18, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR).pack(side="left", padx=16)
        tk.Button(head, text="\u2715", font=("Segoe UI", 12),
                  bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                  activebackground="#e94560", activeforeground="white",
                  relief="flat", cursor="hand2", bd=0, padx=10,
                  command=self.close_theme_panel).pack(side="right", padx=12)
        tk.Frame(self.theme_panel, bg=Config.BORDER, height=1).pack(
            fill="x", padx=16, pady=(4, 10))
        grid = tk.Frame(self.theme_panel, bg=Config.BG_SIDEBAR)
        grid.pack(fill="x", padx=16)
        cur = Config.ACCENT
        for i, (color, label) in enumerate(self.THEME_COLORS):
            cell = tk.Frame(grid, bg=Config.BG_SIDEBAR)
            cell.grid(row=i // self.THEME_COLS, column=i % self.THEME_COLS,
                      padx=6, pady=8, sticky="nsew")
            fg = "black" if color == "#ffd600" else "white"
            b = tk.Button(cell, text="\u2713" if color == cur else "",
                          font=("Segoe UI", 16, "bold"),
                          bg=color, fg=fg, activebackground=color,
                          activeforeground=fg, relief="flat", bd=0,
                          cursor="hand2", width=5, height=2,
                          highlightthickness=1,
                          highlightbackground=Config.BORDER,
                          command=lambda col=color: self.apply_theme(col))
            b.pack()
            b.bind("<Enter>", lambda e, idx=i: self.theme_set_focus(idx))
            tk.Label(cell, text=label, font=("Segoe UI", 9),
                     fg=Config.TEXT_SECONDARY,
                     bg=Config.BG_SIDEBAR).pack(pady=(4, 0))
            self.theme_swatches.append(b)
        for c in range(self.THEME_COLS):
            grid.grid_columnconfigure(c, weight=1)
        self.theme_paint()

    def theme_paint(self):
        for i, b in enumerate(getattr(self, "theme_swatches", [])):
            try:
                if i == self.theme_focus:
                    b.configure(highlightbackground="white",
                                highlightthickness=3)
                else:
                    b.configure(highlightbackground=Config.BORDER,
                                highlightthickness=1)
            except Exception:
                pass

    def theme_set_focus(self, idx):
        if not getattr(self, "theme_visible", False):
            return
        n = len(getattr(self, "theme_swatches", []))
        if not n:
            return
        self.theme_focus = idx % n
        self.theme_paint()

    def theme_move(self, hat):
        if not getattr(self, "theme_visible", False):
            return
        n = len(getattr(self, "theme_swatches", []))
        if not n:
            return
        cols = self.THEME_COLS
        i = self.theme_focus
        if hat == (-1, 0):
            i = (i - 1) % n
        elif hat == (1, 0):
            i = (i + 1) % n
        elif hat == (0, 1):
            i = max(0, i - cols)
        elif hat == (0, -1):
            i = min(n - 1, i + cols)
        else:
            return
        if i != self.theme_focus:
            self.theme_focus = i
            self.theme_paint()
            self.play_tick()

    def theme_press(self, logical):
        if not getattr(self, "theme_visible", False):
            return
        if logical == "south":
            try:
                color = self.THEME_COLORS[self.theme_focus % len(self.THEME_COLORS)][0]
            except Exception:
                return
            self.apply_theme(color)
        elif logical == "east":
            self.close_theme_panel()

    def apply_theme(self, color, win=None):
        global Config
        Config.ACCENT = color
        Config.ACCENT_GLOW = color
        self.refresh_ui()
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    def open_som(self):
        SomPanel(self).open()

    # ===================== SIDE PANELS =====================
    def close_sidepanel(self):
        try:
            sp = getattr(self, "sidepanel", None)
            if sp is not None:
                sp.close()
        except Exception:
            pass

    def open_controles(self):
        ControlesPanel(self).open()

    def open_idioma(self):
        IdiomaPanel(self).open()

    def open_adicionar(self):
        AdicionarPanel(self).open()

    def open_sistema(self):
        SistemaPanel(self).open()

    def open_perfil(self):
        PerfilPanel(self).open()

    def open_guia(self):
        self.close_sidebar()
        GuideWindow(self)

    # ===================== LANGUAGE =====================
    def open_language_picker(self):
        self.close_sidebar()
        menu = NexusMenuWindow(self, t("lang_title", self.lang),
                               [], icon="\U0001F310", width=420)
        languages = [
            ("pt-br", "BR  Portugues (BR)"),
            ("en", "EN  English"),
        ]
        opts = [((("\u2713 " if code == self.lang else "") + label),
                 lambda c=code: self.set_language(c, menu)) for code, label in languages]
        opts.append((t("lang_close", self.lang), menu.close))
        menu.set_options(opts)

    def set_language(self, lang_code, win=None):
        self.lang = lang_code
        self.settings["language"] = lang_code
        save_settings(self.settings)
        self.refresh_ui()
        try:
            if win is not None:
                win.close()
        except Exception:
            pass

    # ===================== MISC =====================
    WEEKDAY_KEYS = {
        0: "day_monday", 1: "day_tuesday", 2: "day_wednesday",
        3: "day_thursday", 4: "day_friday", 5: "day_saturday", 6: "day_sunday",
    }

    def _get_translated_weekday(self):
        key = self.WEEKDAY_KEYS.get(datetime.now().weekday(), "day_monday")
        return t(key, self.lang)

    def update_clock(self):
        now = datetime.now()
        try:
            if self.clock_label:
                self.clock_label.config(text=now.strftime("%H:%M"))
        except:
            pass
        try:
            if self.sidebar_time:
                self.sidebar_time.config(text=now.strftime("%H:%M"))
        except:
            pass
        try:
            if self.sidebar_date:
                weekday = self._get_translated_weekday()
                self.sidebar_date.config(text=f"{weekday}, {now.strftime('%d/%m/%Y')}")
        except:
            pass
        self.root.after(10000, self.update_clock)

    def toggle_fullscreen(self):
        current = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not current)

    def minimize_app(self):
        try:
            self.root.iconify()
        except Exception:
            pass

    def confirm_quit(self):
        menu = NexusMenuWindow(self, t("quit_title", self.lang), [],
                               subtitle=t("quit_question", self.lang),
                               icon="\U0001F6AA", width=440)
        menu.set_options([(t("quit_no", self.lang), menu.close),
                          (t("quit_yes", self.lang),
                           lambda: self.quit_app(menu),
                           {"bg": "#e94560", "fg": "white",
                            "activebackground": "#ff4570"})])

    def quit_app(self, menu=None):
        try:
            if menu is not None:
                menu.close()
        except Exception:
            pass
        for proc in list(BROWSER_PROCS):
            try:
                if proc.poll() is None:
                    try:
                        closing = getattr(self, "_browser_closing", None)
                        if closing is None:
                            closing = self._browser_closing = set()
                        closing.add(proc)
                    except Exception:
                        pass
                    kill_process_tree(proc)
            except Exception:
                pass
        try:
            gp = getattr(self, "gamepad", None)
            if gp is not None:
                gp.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ===================== AUTO-UPDATE =====================
    def check_updates_startup(self):
        threading.Thread(target=self._update_check_thread,
                         args=(True,), daemon=True).start()

    def check_updates_manual(self):
        self.close_sidebar()
        threading.Thread(target=self._update_check_thread,
                         args=(False,), daemon=True).start()

    def _update_check_thread(self, auto):
        info = fetch_latest_release()
        if not info or not info.get("tag"):
            if not auto:
                self.root.after(0, lambda: self.show_info_message(
                    t("msg_warning", self.lang), t("update_error", self.lang)))
            return
        self._latest_release = info
        try:
            self.root.after(0, self._refresh_notif_badge)
        except Exception:
            pass
        try:
            newer = ver_tuple(info["tag"]) > ver_tuple(APP_VERSION)
        except Exception:
            newer = False
        if not newer:
            if not auto:
                self.root.after(0, lambda: self.show_info_message(
                    t("msg_success", self.lang), t("update_latest", self.lang)))
            return
        if auto:
            try:
                if self.settings.get("update_seen", "") == info["tag"]:
                    return
            except Exception:
                pass
        self.root.after(0, lambda: self.offer_update(info))

    def offer_update(self, info):
        if getattr(sys, "frozen", False):
            subtitle = t("update_found", self.lang) % (info["tag"], APP_VERSION)
            changes = [c for c in (info.get("changes") or []) if c][:6]
            notes = (info.get("notes") or "").strip()
            if changes:
                subtitle += ("\n\n" + t("notif_whatsnew", self.lang) + "\n"
                             + "\n".join("\u2022 " + c for c in changes))
            elif notes:
                subtitle += "\n\n" + notes[:300]
            menu = NexusMenuWindow(self, t("update_title", self.lang), [],
                                   subtitle=subtitle, icon="\u2193", width=520)
            menu.set_options([(t("update_now", self.lang),
                               lambda: self.start_update_download(info, menu)),
                              (t("update_later", self.lang),
                               lambda: self.defer_update(info, menu))])
        else:
            self.show_info_message(t("update_title", self.lang),
                                   t("update_git", self.lang) % info["tag"])

    def defer_update(self, info, menu):
        try:
            self.settings["update_seen"] = info.get("tag", "")
            save_settings(self.settings)
        except Exception:
            pass
        try:
            menu.close()
        except Exception:
            pass

    def start_update_download(self, info, menu):
        try:
            menu.close()
        except Exception:
            pass
        self.show_info_message(t("update_title", self.lang),
                               t("update_downloading", self.lang))
        threading.Thread(target=self._update_download_thread,
                         args=(info,), daemon=True).start()

    def _update_download_thread(self, info):
        url = info.get("zip", "")
        tmp = ""
        try:
            tmpdir = os.environ.get("TEMP") or os.path.expanduser("~")
            tmp = os.path.join(tmpdir, "nexus_update.zip")
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1024 * 256)
        except Exception:
            self.root.after(0, lambda: self.show_info_message(
                t("msg_warning", self.lang), t("update_error", self.lang)))
            return
        self.root.after(0, lambda: self.offer_update_apply(info, tmp))

    def offer_update_apply(self, info, tmp):
        menu = NexusMenuWindow(self, t("update_title", self.lang), [],
                               subtitle=t("update_ready", self.lang),
                               icon="\u2193", width=480)
        menu.set_options([(t("update_apply", self.lang),
                           lambda: self.apply_update_and_restart(menu, tmp)),
                          (t("sidebar_close", self.lang), menu.close)])

    def apply_update_and_restart(self, menu, tmp):
        try:
            install_dir = os.path.dirname(os.path.realpath(sys.executable))
            bat = os.path.join(os.environ.get("TEMP") or os.path.expanduser("~"),
                               "nexus_atualizar.bat")
            with open(bat, "w") as f:
                f.write("@echo off\r\n"
                        "taskkill /F /IM Nexus.exe >nul 2>nul\r\n"
                        "taskkill /F /IM nexus_browser.exe >nul 2>nul\r\n"
                        "timeout /t 3 /nobreak >nul\r\n"
                        "powershell -NoProfile -Command \"Expand-Archive"
                        " -LiteralPath '" + tmp + "' -DestinationPath '" + install_dir + "'"
                        " -Force\"\r\n"
                        "del \"" + tmp + "\"\r\n"
                        "start \"\" \"" + install_dir + "\\Nexus.exe\"\r\n"
                        "(goto) 2>nul & del \"%~f0\"\r\n")
            subprocess.Popen(["cmd", "/c", "start", "/min", "", bat], shell=False)
        except Exception:
            try:
                self.show_info_message(t("msg_warning", self.lang),
                                       t("update_error", self.lang))
            except Exception:
                pass
            return
        self.quit_app(menu)

    def refresh_ui(self):
        self.build_ui()
