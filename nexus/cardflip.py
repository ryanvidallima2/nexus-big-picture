# -*- coding: utf-8 -*-
"""Verso do card: Site/App/Config (streamings) e Jogar/Config (jogos)
inline, sem janela popup. Clique/A vira o card; B desvira."""

import threading
import time
import tkinter as tk

from .apps import open_app_for_service, open_store_search, try_install_service
from .browser import open_in_nexus_browser
from .config import Config
from .dialogs import CARD_COLOR_PRESETS, _modal_alive
from .i18n import t
from .pad import BROWSER_WATCH
from .paths import BROWSER_PROCS
from .win32 import _top_level_windows


class CardFlipMixin:
    """Estado e verso dos cards."""

    # ---------- estado ----------
    def focused_card(self):
        """(widget, name, is_game) do card focado, ou (None, None, False)."""
        try:
            if self.nav_level != "items" or not self.sections:
                return None, None, False
            r = min(self.focus_mgr.focused_row, len(self.sections) - 1)
            sec = self.sections[r]
            if sec["canvas"] is None:
                j = self.focus_mgr.focused_col
            else:
                j = sec.get("scroll_offset", 0) + self.focus_mgr.focused_col
            names = sec["names"]
            widgets = sec.get("widgets", [])
            if 0 <= j < len(names) and 0 <= j < len(widgets):
                return widgets[j], names[j], self.current_tab == "games"
        except Exception:
            pass
        return None, None, False

    def find_card_widget(self, name):
        try:
            for sec in self.sections:
                names = sec.get("names", [])
                widgets = sec.get("widgets", [])
                if name in names:
                    j = names.index(name)
                    if 0 <= j < len(widgets):
                        return widgets[j]
        except Exception:
            pass
        return None

    # ---------- flip ----------
    def flip_card(self, widget, name, is_game):
        cur = getattr(self, "flipped", None)
        try:
            if cur is not None and cur.get("widget") == widget:
                self.unflip_card()
                return
        except Exception:
            pass
        self.unflip_card()
        try:
            if widget is None or not widget.winfo_exists():
                return
        except Exception:
            return
        tall = getattr(widget, "_flip_tall", True)
        try:
            icon = "\U0001F3AE"
            if not is_game:
                try:
                    icon = (self.get_all_services().get(name, {}).get("icon")
                            or "\U0001F4F0")
                except Exception:
                    icon = "\U0001F4F0"
        except Exception:
            icon = "\U0001F3AE"
        try:
            back = tk.Frame(widget, bg=Config.BG_SIDEBAR,
                            highlightbackground=Config.ACCENT,
                            highlightthickness=2)
        except Exception:
            return
        flip = {"widget": widget, "name": name, "is_game": bool(is_game),
                "tall": bool(tall), "back": back, "opts": [], "idx": 0,
                "page": "main", "busy": False, "status": None, "orig_h": None,
                "icon": icon}
        self.flipped = flip
        try:
            if tall:
                back.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                try:
                    flip["orig_h"] = widget.cget("height")
                except Exception:
                    flip["orig_h"] = 52
                try:
                    widget.configure(height=190)
                except Exception:
                    pass
                back.pack(fill="both", expand=True)
            back.bind("<Button-1>", lambda e: self.unflip_card())
            self.flip_show_page("main")
        except Exception:
            try:
                self.unflip_card()
            except Exception:
                pass

    def unflip_card(self):
        flip = getattr(self, "flipped", None)
        self.flipped = None
        if not flip:
            return
        try:
            w = flip.get("widget")
            if not flip.get("tall", True) and w is not None:
                try:
                    if w.winfo_exists():
                        w.configure(height=flip.get("orig_h") or 52)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            back = flip.get("back")
            if back is not None:
                back.destroy()
        except Exception:
            pass

    # ---------- verso ----------
    def _flip_header(self, parent, name, icon=""):
        head = tk.Frame(parent, bg=Config.BG_SIDEBAR)
        head.pack(fill="x", pady=(8, 2), padx=8)
        b = tk.Button(head, text="\u2190", font=("Segoe UI", 11, "bold"),
                      bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                      activebackground=Config.BG_CARD_HOVER,
                      relief="flat", bd=0, cursor="hand2", padx=8, pady=0,
                      command=self.unflip_card)
        b.pack(side="left")
        b.bind("<Button-1>", lambda e: (self.unflip_card(), "break"),
               add="+")
        short = name if len(name) <= 14 else name[:13] + "\u2026"
        title = f"{icon} - {short} - {icon}" if icon else short
        tk.Label(head, text=title, font=("Segoe UI", 11, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR).pack(
                     side="left", padx=(6, 0))
        return b

    def _flip_status(self, parent, flip):
        st = tk.Label(parent, text="", font=("Segoe UI", 9),
                      fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                      wraplength=220, justify="center")
        st.pack(fill="x", padx=8)
        flip["status"] = st
        return st

    def _flip_opt(self, parent, flip, text, cmd, big=False):
        b = tk.Button(parent, text=text,
                      font=("Segoe UI", 12 if big else 11, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      highlightthickness=1,
                      highlightbackground=Config.BORDER,
                      command=lambda: None)
        idx = len(flip["opts"])
        flip["opts"].append((b, cmd))
        b.bind("<Enter>", lambda e, i=idx: self.flip_set_focus(i))
        b.bind("<Button-1>", lambda e, i=idx: self.flip_click(i))
        return b

    def flip_set_focus(self, idx):
        flip = getattr(self, "flipped", None)
        if not flip or not flip["opts"]:
            return
        flip["idx"] = idx % len(flip["opts"])
        self.flip_paint()

    def flip_paint(self):
        flip = getattr(self, "flipped", None)
        if not flip:
            return
        for i, (b, _cmd) in enumerate(flip["opts"]):
            try:
                if i == flip["idx"]:
                    b.configure(bg=Config.ACCENT, fg="white",
                                highlightbackground=Config.ACCENT_GLOW,
                                highlightthickness=2)
                else:
                    b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                highlightbackground=Config.BORDER,
                                highlightthickness=1)
            except Exception:
                pass

    def flip_opt_move(self, d):
        flip = getattr(self, "flipped", None)
        if not flip or not flip["opts"]:
            return
        flip["idx"] = (flip["idx"] + d) % len(flip["opts"])
        self.flip_paint()
        try:
            self.play_tick()
        except Exception:
            pass

    def flip_click(self, idx):
        flip = getattr(self, "flipped", None)
        if not flip:
            return "break"
        flip["idx"] = idx % max(1, len(flip["opts"]))
        self.flip_paint()
        self.flip_opt_activate()
        return "break"

    def flip_opt_activate(self):
        flip = getattr(self, "flipped", None)
        if not flip or not flip["opts"]:
            return
        _b, cmd = flip["opts"][flip["idx"] % len(flip["opts"])]
        try:
            cmd()
        except Exception:
            pass

    ROW_H = {"main": 190, "config": 300, "color": 320,
             "url": 250, "logo": 250, "delete": 210}

    def flip_show_page(self, page):
        flip = getattr(self, "flipped", None)
        if not flip:
            return
        try:
            if not flip["back"].winfo_exists():
                return
        except Exception:
            return
        flip["page"] = page
        flip["opts"] = []
        flip["idx"] = 0
        back = flip["back"]
        try:
            for w in back.winfo_children():
                w.destroy()
        except Exception:
            return
        name = flip["name"]
        self._flip_header(back, name, flip.get("icon", ""))
        self._flip_status(back, flip)
        if not flip["tall"]:
            try:
                flip["widget"].configure(height=self.ROW_H.get(page, 190))
            except Exception:
                pass
        body = tk.Frame(back, bg=Config.BG_SIDEBAR)
        body.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        if flip["is_game"]:
            if page == "config":
                self._flip_game_config(body, flip, name)
            elif page == "color":
                self._flip_color_page(body, flip, name, True)
            elif page == "logo":
                self._flip_path_page(body, flip, name, True)
            elif page == "delete":
                self._flip_delete_page(body, flip, name, True)
            else:
                self._flip_game_main(body, flip, name)
        else:
            if page == "config":
                self._flip_stream_config(body, flip, name)
            elif page == "color":
                self._flip_color_page(body, flip, name, False)
            elif page == "url":
                self._flip_url_page(body, flip, name)
            elif page == "logo":
                self._flip_path_page(body, flip, name, False)
            elif page == "delete":
                self._flip_delete_page(body, flip, name, False)
            else:
                self._flip_stream_main(body, flip, name)
        self.flip_paint()

    # ---------- paginas: streaming ----------
    def _flip_stream_main(self, body, flip, name):
        lang = self.lang
        row = tk.Frame(body, bg=Config.BG_SIDEBAR)
        row.pack(fill="both", expand=True)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        b1 = self._flip_opt(row, flip, t("dlg_site", lang),
                            lambda: self._flip_site(name), big=True)
        b1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        b2 = self._flip_opt(row, flip, t("dlg_app", lang),
                            lambda: self._flip_app(name), big=True)
        b2.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        b3 = self._flip_opt(body, flip, t("dlg_config", lang),
                            lambda: self.flip_show_page("config"))
        b3.pack(fill="both", expand=True, pady=(6, 0))

    def _flip_stream_config(self, body, flip, name):
        lang = self.lang
        favs = self.settings.get("favorites", [])
        rows = [
            ((f"\u2716 {t('ctx_remove_fav', lang)}" if name in favs
              else f"\u2B50 {t('ctx_add_fav', lang)}"),
             lambda: self.cfg_keep_flip(name, False, "config",
                                        lambda: self.toggle_favorite(name))),
            (t("dlg_color", lang), lambda: self.flip_show_page("color")),
            (t("dlg_color_reset", lang),
             lambda: self.cfg_keep_flip(name, False, "config",
                                        lambda: self.reset_card_color(name))),
            (t("dlg_url", lang), lambda: self.flip_show_page("url")),
            ((f"\U0001F5BC {t('ctx_change_logo', lang)}"),
             lambda: self.flip_show_page("logo")),
            ((f"\U0001F4CB {t('ctx_copy_url', lang)}"),
             lambda: self._flip_copy_url(name)),
            ((f"\U0001F5D1 {t('ctx_delete', lang)}"),
             lambda: self.flip_show_page("delete")),
            ((f"\u2190 {t('dlg_back', lang)}"),
             lambda: self.flip_show_page("main")),
        ]
        for text, cmd in rows:
            b = self._flip_opt(body, flip, text, cmd)
            b.configure(anchor="w", padx=12)
            b.pack(fill="both", expand=True, pady=1)

    # ---------- paginas: jogos ----------
    def _flip_game_main(self, body, flip, name):
        lang = self.lang
        row = tk.Frame(body, bg=Config.BG_SIDEBAR)
        row.pack(fill="both", expand=True)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        b1 = self._flip_opt(row, flip, t("dlg_play", lang),
                            lambda: self._flip_play(name), big=True)
        b1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        b2 = self._flip_opt(row, flip, t("dlg_config", lang),
                            lambda: self.flip_show_page("config"), big=True)
        b2.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

    def _flip_game_config(self, body, flip, name):
        lang = self.lang
        try:
            _tipo, _loc = self.item_details(name)
            folder = _loc or self.game_folder(name) or ""
            if folder:
                tk.Label(body, text=f"{t('games_folder', lang)} {folder}",
                         font=("Segoe UI", 8), fg=Config.TEXT_SECONDARY,
                         bg=Config.BG_SIDEBAR, wraplength=220,
                         justify="center").pack(pady=(0, 2))
        except Exception:
            pass
        favs = self.settings.get("favorites", [])
        rows = [
            ((f"\u2716 {t('ctx_remove_fav', lang)}" if name in favs
              else f"\u2B50 {t('ctx_add_fav', lang)}"),
             lambda: self.cfg_keep_flip(name, True, "config",
                                        lambda: self.toggle_favorite(name))),
            (t("dlg_color", lang), lambda: self.flip_show_page("color")),
            (t("dlg_color_reset", lang),
             lambda: self.cfg_keep_flip(name, True, "config",
                                        lambda: self.reset_card_color(name))),
            (t("dlg_cover", lang), lambda: self.flip_show_page("logo")),
            (t("games_openfolder", lang),
             lambda: self._flip_open_folder(name)),
            ((f"\U0001F5D1 {t('ctx_delete', lang)}"),
             lambda: self.flip_show_page("delete")),
            ((f"\u2190 {t('dlg_back', lang)}"),
             lambda: self.flip_show_page("main")),
        ]
        for text, cmd in rows:
            b = self._flip_opt(body, flip, text, cmd)
            b.configure(anchor="w", padx=12)
            b.pack(fill="both", expand=True, pady=1)

    # ---------- acoes: abrir ----------
    def _flip_status_text(self, text):
        flip = getattr(self, "flipped", None)
        if not flip:
            return
        try:
            st = flip.get("status")
            if st is not None and st.winfo_exists():
                st.configure(text=text)
        except Exception:
            pass

    def _flip_site(self, name):
        flip = getattr(self, "flipped", None)
        if not flip or flip.get("busy"):
            return
        flip["busy"] = True
        lang = self.lang
        self._flip_status_text(t("dlg_opening_nexus", lang))
        self.launch_site_flow(
            name,
            status_cb=lambda txt: self._flip_status_text(txt),
            done_cb=lambda: self.unflip_card())

    def _flip_app(self, name):
        flip = getattr(self, "flipped", None)
        if not flip or flip.get("busy"):
            return
        flip["busy"] = True
        self.launch_app_flow(
            name,
            status_cb=lambda txt: self._flip_status_text(txt),
            done_cb=lambda: self.unflip_card())

    def _flip_play(self, name):
        self.unflip_card()
        try:
            self.launch_game(name)
        except Exception:
            pass

    def launch_site_flow(self, name, status_cb=lambda txt: None,
                         done_cb=lambda: None):
        """Abre Site (extraido do dialogo, agora sem janela)."""
        try:
            url = self.opener.effective_url(name)
        except Exception:
            url = ""
        proc = None
        if self.settings.get("embedded_browser", True):
            try:
                status_cb(t("dlg_opening_nexus", self.lang))
            except Exception:
                pass
            try:
                pad_label = self.current_pad_label()
            except Exception:
                pad_label = ""
            proc = open_in_nexus_browser(url, name, pad_label)
        try:
            self.db.add_history(name)
        except Exception:
            pass
        if proc is not None:
            BROWSER_PROCS.append(proc)
            try:
                splash = self.show_transition_splash(name)
            except Exception:
                splash = None
            svc = name
            born = time.time()
            try:
                done_cb()
            except Exception:
                pass
            try:
                self.root.after(
                    450, lambda: self.enter_site_remote(proc, svc, splash, born))
            except Exception:
                self.enter_site_remote(proc, svc, splash, born)
            return
        try:
            self.opener.open_content(name)
            self.enter_remote_mode(name, watch=BROWSER_WATCH)
        finally:
            try:
                done_cb()
            except Exception:
                pass

    def launch_app_flow(self, name, status_cb=lambda txt: None,
                        done_cb=lambda: None):
        """Abre App (thread + poll, extraido do dialogo, sem janela)."""
        state = {"result": None}
        try:
            status_cb(t("dlg_searching", self.lang))
        except Exception:
            pass
        threading.Thread(target=self._launch_app_thread,
                         args=(name, state), daemon=True).start()
        self._launch_app_poll(name, state, status_cb, done_cb)

    def _launch_app_thread(self, name, state):
        try:
            if open_app_for_service(name):
                state["result"] = "app"
                return
            if try_install_service(
                    name,
                    status_cb=lambda key: self._launch_install_status(key)):
                try:
                    if open_app_for_service(name):
                        state["result"] = "app"
                        return
                except Exception:
                    pass
        except Exception:
            try:
                open_store_search(name)
            except Exception:
                pass
            state["result"] = "store"

    def _launch_install_status(self, key):
        try:
            txt = t(key, self.lang)
        except Exception:
            txt = ""
        try:
            self.root.after(0, lambda: self._flip_status_text(txt))
        except Exception:
            pass

    def _launch_app_poll(self, name, state, status_cb, done_cb):
        if state.get("result") is None:
            try:
                self.root.after(120, lambda: self._launch_app_poll(
                    name, state, status_cb, done_cb))
            except Exception:
                pass
            return
        try:
            self.db.add_history(name)
        except Exception:
            pass
        if state.get("result") == "app":
            try:
                self.enter_remote_mode(name)
            except Exception:
                pass
            try:
                before = [hw for hw, _p, _t in _top_level_windows()]
            except Exception:
                before = []
            try:
                self.root.after(
                    2500, lambda: self.borderless_new_app(before))
            except Exception:
                pass
        try:
            done_cb()
        except Exception:
            pass

    # ---------- acoes: config ----------
    def find_card_widget(self, name):
        try:
            for sec in self.sections:
                names = sec.get("names", [])
                widgets = sec.get("widgets", [])
                if name in names:
                    j = names.index(name)
                    if 0 <= j < len(widgets):
                        return widgets[j]
        except Exception:
            pass
        return None

    def cfg_keep_flip(self, name, is_game, page, fn):
        """Roda fn (que pode dar refresh_ui) e re-vira o card na pagina."""
        self._pending_flip = (name, bool(is_game), page)
        try:
            fn()
        finally:
            self._restore_pending_flip()

    def _restore_pending_flip(self):
        try:
            pend = getattr(self, "_pending_flip", None)
            self._pending_flip = None
        except Exception:
            return
        if not pend:
            return
        if getattr(self, "flipped", None) is not None:
            return
        try:
            w = self.find_card_widget(pend[0])
            if w is not None and w.winfo_exists():
                self.flip_card(w, pend[0], pend[1])
                if pend[2] != "main":
                    self.flip_show_page(pend[2])
        except Exception:
            pass

    def _flip_entry_page(self, body, flip, initial, on_ok):
        """Pagina com campo de texto inline (URL/caminho): sem janelas.
        Mouse clica e digita; no controle o teclado virtual abre sozinho."""
        e = tk.Entry(body, font=("Segoe UI", 11),
                     bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                     insertbackground=Config.ACCENT, bd=0,
                     highlightbackground=Config.ACCENT, highlightthickness=1)
        e.pack(fill="x", pady=(4, 6))
        try:
            e.insert(0, initial or "")
        except Exception:
            pass
        flip["entry"] = e
        ok = self._flip_opt(body, flip, "\u2713 OK", lambda: self._flip_entry_ok(on_ok))
        ok.pack(fill="x", pady=1)
        back = self._flip_opt(body, flip, "\u2190 " + t("dlg_back", self.lang),
                              lambda: self.flip_show_page("config"))
        back.pack(fill="x", pady=1)
        try:
            if getattr(self, "using_gamepad", False):
                try:
                    if _modal_alive(self.kb_window):
                        self.kb_window.close()
                except Exception:
                    pass
                self.open_keyboard(e)
        except Exception:
            pass
        return e

    def _flip_entry_ok(self, on_ok):
        flip = getattr(self, "flipped", None)
        try:
            if _modal_alive(self.kb_window):
                self.kb_window.close()
        except Exception:
            pass
        val = ""
        try:
            if flip is not None and flip.get("entry") is not None:
                val = flip["entry"].get()
        except Exception:
            pass
        try:
            on_ok(val)
        except Exception:
            pass

    def _flip_color_page(self, body, flip, name, is_game):
        grid = tk.Frame(body, bg=Config.BG_SIDEBAR)
        grid.pack(fill="both", expand=True)
        for i, (_label, color) in enumerate(CARD_COLOR_PRESETS):
            b = tk.Button(grid, text="\u2713" if color == Config.ACCENT else "",
                          font=("Segoe UI", 10, "bold"),
                          bg=color, fg="black" if color == "#ffd600" else "white",
                          activebackground=color, relief="flat", bd=0,
                          cursor="hand2", width=4, height=1,
                          highlightthickness=1,
                          highlightbackground=Config.BORDER)
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky="nsew")
            idx = len(flip["opts"])
            flip["opts"].append((b, lambda col=color: self.cfg_keep_flip(
                name, is_game, "color",
                lambda: self.set_card_color(name, col))))
            b.bind("<Enter>", lambda e, j=idx: self.flip_set_focus(j))
            b.bind("<Button-1>", lambda e, j=idx: self.flip_click(j))
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1)
        back = self._flip_opt(body, flip, "\u2190 " + t("dlg_back", self.lang),
                              lambda: self.flip_show_page("config"))
        back.pack(fill="x", pady=(4, 0))

    def _flip_pick_color(self, name, is_game, color):
        self.cfg_keep_flip(name, is_game, "color",
                           lambda: self.set_card_color(name, color))

    def _flip_url_page(self, body, flip, name):
        lang = self.lang
        try:
            current = self.opener.effective_url(name)
        except Exception:
            current = ""
        tk.Label(body, text=t("dlg_url", lang), font=("Segoe UI", 10),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x")

        def _ok(val):
            if (val or "").strip() and self.edit_card_url(name, val):
                self.flip_show_page("config")

        self._flip_entry_page(body, flip, current, _ok)

    def _flip_path_page(self, body, flip, name, is_game):
        lang = self.lang
        key = "dlg_cover" if is_game else "ctx_change_logo"
        tk.Label(body, text=t(key, lang), font=("Segoe UI", 10),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x")

        def _ok(val):
            path = (val or "").strip()
            if not path:
                return
            try:
                ok = (self.set_game_cover(name, path) if is_game
                      else self._flip_logo_path(name, path))
            except Exception:
                ok = False
            if ok:
                self.cfg_keep_flip(name, is_game, "logo", lambda: None)
            else:
                self._flip_status_text(path + " ?")

        self._flip_entry_page(body, flip, "", _ok)

    def _flip_logo_path(self, name, path):
        import os as _os
        if not path or not _os.path.isfile(path):
            return False
        self.change_logo(name, path)
        return True

    def _flip_delete_page(self, body, flip, name, is_game):
        lang = self.lang
        tk.Label(body, text=f"{t('games_del_q' if is_game else 'delete_question', lang)} '{name}'?",
                 font=("Segoe UI", 11, "bold"), fg=Config.TEXT_PRIMARY,
                 bg=Config.BG_SIDEBAR, wraplength=220,
                 justify="center").pack(pady=(6, 8))
        yes = self._flip_opt(
            body, flip, f"\U0001F5D1 {t('ctx_delete', lang)}",
            lambda: self._flip_delete_yes(name, is_game))
        yes.pack(fill="x", pady=1)
        no = self._flip_opt(body, flip, "\u2190 " + t("dlg_back", lang),
                            lambda: self.flip_show_page("config"))
        no.pack(fill="x", pady=1)

    def _flip_copy_url(self, name):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.opener.effective_url(name))
        except Exception:
            pass

    def _flip_open_folder(self, name):
        try:
            self.open_game_location(name)
        except Exception:
            pass

    def _flip_delete_yes(self, name, is_game):
        if is_game:
            try:
                if self.game_is_platform(name):
                    self.unflip_card()
                    self.remove_platform_game(name)
                    return
                if self.game_is_external(name):
                    self.unflip_card()
                    self.remove_external_game(name)
                    return
            except Exception:
                pass
            self.unflip_card()
            try:
                if self.delete_game_folder(name):
                    try:
                        self.refresh_ui()
                    except Exception:
                        pass
            except Exception:
                pass
            return
        self.unflip_card()
        try:
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
            try:
                self.refresh_ui()
            except Exception:
                pass
        except Exception:
            pass
