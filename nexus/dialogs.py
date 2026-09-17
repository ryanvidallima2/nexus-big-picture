# -*- coding: utf-8 -*-
"""Dialogos e janelas modais estilo Nexus (extraido sem alteracao)."""

import re
import threading
import time
import tkinter as tk
from tkinter import filedialog

from .apps import open_app_for_service, open_store_search, try_install_service
from .browser import open_in_nexus_browser
from .config import Config
from .i18n import t
from .pad import BROWSER_WATCH
from .paths import BROWSER_PROCS
from .win32 import (
    _top_level_windows, _apply_dark_title, _apply_dark_title_later,
)


# Presets de cor do fundo do card (nome, hex)
CARD_COLOR_PRESETS = [
    ("Netflix", "#E50914"), ("YouTube", "#FF0000"), ("Spotify", "#1DB954"),
    ("Disney+", "#113CCF"), ("Prime", "#00A8E1"), ("Twitch", "#9146FF"),
    ("Nexus", "#7c4dff"), ("Ciano", "#00bcd4"), ("Verde", "#00c853"),
    ("Amarelo", "#ffd600"), ("Rosa", "#ff4081"), ("Laranja", "#ff6d00"),
    ("Vermelho", "#e94560"), ("Azul", "#0d47a1"), ("Preto", "#000000"),
    ("Cinza", "#424242"),
]


# ===================== OPEN TARGET DIALOG =====================
class OpenTargetDialog:
    """Janela Site x App. Mouse, teclado e controle: A confirma, B cancela."""

    def __init__(self, app, name):
        self.app = app
        self.name = name
        self.mode = "main"
        self.focus_idx = 0
        self.busy = False
        self.closed = False
        self.thread_result = None
        self.born = time.time()
        self.options = []  # [(botao, comando)] da vista atual

        lang = app.lang
        win = tk.Toplevel(app.root)
        self.win = win
        win.title(name)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        self.win_w, self.win_h = 480, 360
        _apply_dark_title(win, "carddlg")
        _apply_dark_title_later(win, tag="carddlg")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - self.win_w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - self.win_h) // 2
        except Exception:
            x, y = 200, 150
        win.geometry(f"{self.win_w}x{self.win_h}+{max(0, x)}+{max(0, y)}")

        tk.Label(win, text=f"\u25C6 {name}", font=("Segoe UI", 20, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 wraplength=self.win_w - 40).pack(pady=(22, 4))
        self.sub = tk.Label(win, text=t("dlg_how", lang), font=("Segoe UI", 13),
                            fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.sub.pack(pady=(0, 16))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)

        self.status = tk.Label(win, text="", font=("Segoe UI", 12),
                               fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.status.pack(pady=(4, 0))
        tk.Label(win, text=t("dlg_remote", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                 wraplength=self.win_w - 40, justify="center").pack(pady=(8, 0))
        tk.Label(win, text=t("dlg_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(side="bottom", pady=14)

        win.bind("<Left>", lambda e: self.move_prev())
        win.bind("<Right>", lambda e: self.move_next())
        win.bind("<Up>", lambda e: self.move_prev())
        win.bind("<Down>", lambda e: self.move_next())
        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<space>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.cancel())
        win.protocol("WM_DELETE_WINDOW", self.cancel)
        win.grab_set()

        self.show_main()

    def _reg(self, btn, command):
        idx = len(self.options)
        self.options.append((btn, command))
        btn.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        return btn

    def _click(self, idx):
        self.set_focus(idx)
        self.confirm()

    def _resize(self, h):
        self.win_h = h
        try:
            self.win.geometry(f"{self.win_w}x{h}+{self.win.winfo_x()}+{self.win.winfo_y()}")
        except Exception:
            pass

    def show_main(self):
        if self.closed:
            return
        self.mode = "main"
        self.busy = False
        lang = self.app.lang
        self._resize(360)
        try:
            self.sub.configure(text=t("dlg_how", lang))
            self.status.configure(text="")
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        row = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        row.pack()
        for i, (key, cmd) in enumerate((("dlg_site", self._do_site),
                                        ("dlg_app", self._do_app))):
            b = tk.Button(row, text=t(key, lang), font=("Segoe UI", 16, "bold"),
                          width=11, height=2, relief="flat", bd=0, cursor="hand2",
                          command=lambda idx=i: self._click(idx))
            b.grid(row=0, column=i, padx=12)
            self._reg(b, cmd)
        cfg = tk.Button(self.body, text=t("dlg_config", lang), font=("Segoe UI", 14),
                        relief="flat", bd=0, cursor="hand2",
                        command=lambda: self._click(2))
        cfg.pack(fill="x", padx=52, pady=(14, 0))
        self._reg(cfg, self.show_edit)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def show_edit(self):
        if self.closed or self.busy:
            return
        self.mode = "edit"
        lang = self.app.lang
        name = self.name
        self._resize(620)
        try:
            self.sub.configure(text=t("dlg_config", lang))
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        favs = self.app.settings.get("favorites", [])
        rows = [
            ((f"\u2716 {t('ctx_remove_fav', lang)}" if name in favs
              else f"\u2B50 {t('ctx_add_fav', lang)}"), self._edit_fav),
            (t("dlg_color", lang), self._edit_color),
            (t("dlg_color_reset", lang), self._edit_color_reset),
            (t("dlg_url", lang), self._edit_url),
            (f"\U0001F5BC {t('ctx_change_logo', lang)}", self._edit_logo),
            (f"\U0001F4CB {t('ctx_copy_url', lang)}", self._edit_copy_url),
            (f"\U0001F5D1 {t('ctx_delete', lang)}", self._edit_delete),
            (t("dlg_back", lang), self.show_main),
        ]
        for i, (text, cmd) in enumerate(rows):
            b = tk.Button(self.body, text=text, font=("Segoe UI", 13),
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          padx=18, command=lambda idx=i: self._click(idx))
            b.pack(fill="x", padx=40, pady=2)
            self._reg(b, cmd)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def _alive(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def _after_refresh(self, rebuild=True):
        # Acoes que dao refresh_ui destroem esta janela (filha do root)
        if not self._alive():
            self._close()
            return False
        if rebuild:
            if self.mode == "edit":
                self.show_edit()
            else:
                self.show_main()
        return True

    def _edit_fav(self):
        self.app.toggle_favorite(self.name)
        self._after_refresh()

    def _edit_color(self):
        menu = NexusMenuWindow(self.app, t("dlg_color", self.app.lang), [],
                               icon="\U0001F3A8", width=480, cols=4)
        opts = []
        for label, color in CARD_COLOR_PRESETS:
            opts.append((label,
                         lambda col=color: self._pick_card_color(menu, col),
                         {"bg": color,
                          "fg": "black" if color == "#ffd600" else "white",
                          "activebackground": color, "width": 8}))
        opts.append((t("sidebar_close", self.app.lang), menu.close, {"width": 8}))
        menu.set_options(opts, opt_font=10)

    def _pick_card_color(self, menu, color):
        try:
            menu.close()
        except Exception:
            pass
        self.app.set_card_color(self.name, color)
        self._after_refresh(rebuild=False)
        if self._alive() and self.mode == "edit":
            self.show_edit()

    def _edit_color_reset(self):
        self.app.reset_card_color(self.name)
        self._after_refresh()

    def _edit_url(self):
        try:
            current = self.app.opener.effective_url(self.name)
        except Exception:
            current = ""
        NexusTextDialog(self.app, t("dlg_url_title", self.app.lang),
                        t("dlg_url_prompt", self.app.lang), current,
                        lambda url: self._finish_url(url))

    def _finish_url(self, url):
        if url:
            self.app.edit_card_url(self.name, url)

    def _edit_logo(self):
        self.app.change_logo(self.name)
        self._after_refresh()

    def _edit_copy_url(self):
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(self.app.opener.effective_url(self.name))
        except Exception:
            pass

    def _edit_delete(self):
        self.app.delete_streaming(self.name)
        try:
            alive = self.name in self.app.get_all_services()
        except Exception:
            alive = False
        if not alive or not self._alive():
            self._close()
        elif self.mode == "edit":
            self.show_edit()

    def _paint(self):
        for i, (b, _cmd) in enumerate(self.options):
            if i == self.focus_idx:
                b.configure(bg=Config.ACCENT, fg="white",
                            highlightbackground=Config.ACCENT_GLOW, highlightthickness=2)
            else:
                b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                            highlightbackground=Config.BORDER, highlightthickness=1)

    def set_focus(self, idx):
        if self.closed or not self.options:
            return
        self.focus_idx = idx % len(self.options)
        self._paint()

    def move(self, direction=None):
        self.move_next()

    def move_prev(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx - 1) % len(self.options)
        self._paint()

    def move_next(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx + 1) % len(self.options)
        self._paint()

    def confirm(self):
        if self.closed or self.busy or not self.options:
            return
        _btn, cmd = self.options[self.focus_idx]
        try:
            cmd()
        except Exception:
            pass

    def cancel(self):
        if self.closed:
            return
        if self.mode == "edit" and not self.busy:
            self.show_main()
        else:
            self._close()

    def _close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.open_dialog is self:
                self.app.open_dialog = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass

    def _do_site(self):
        url = self.app.opener.effective_url(self.name)
        proc = None
        if self.app.settings.get("embedded_browser", True):
            try:
                self.status.configure(text=t("dlg_opening_nexus", self.app.lang))
            except Exception:
                pass
            try:
                pad_label = self.app.current_pad_label()
            except Exception:
                pad_label = ""
            proc = open_in_nexus_browser(url, self.name, pad_label)
        try:
            self.app.db.add_history(self.name)
        except Exception:
            pass
        if proc is not None:
            # Transicao como se fosse o mesmo app: splash no estilo Nexus
            # enquanto o navegador abre; o remoto (e o minimizar) entram
            # quando a janela ja existe.
            BROWSER_PROCS.append(proc)
            try:
                splash = self.app.show_transition_splash(self.name)
            except Exception:
                splash = None
            svc = self.name
            born = time.time()
            self._close()
            try:
                self.app.root.after(
                    450, lambda: self.app.enter_site_remote(proc, svc, splash, born))
            except Exception:
                self.app.enter_site_remote(proc, svc, splash, born)
            return
        try:
            self.app.opener.open_content(self.name)
            # Entra no remoto ANTES de fechar (mesmo motivo do App):
            # minimiza com o dialogo junto e o foco vai p/ o navegador.
            self.app.enter_remote_mode(self.name, watch=BROWSER_WATCH)
        finally:
            self._close()

    def _install_status(self, key):
        try:
            if self.closed:
                return
            self.status.configure(text=t(key, self.app.lang))
        except Exception:
            pass

    def _do_app(self):
        self.busy = True
        try:
            self.status.configure(text=t("dlg_searching", self.app.lang))
        except Exception:
            pass
        threading.Thread(target=self._app_thread, daemon=True).start()
        self._schedule_check()

    def _app_thread(self):
        try:
            if open_app_for_service(self.name):
                self.thread_result = "app"
                return
            # Nao achou instalado: tenta baixar/instalar sozinho via winget.
            if try_install_service(
                    self.name,
                    status_cb=lambda key: self.app.root.after(
                        0, self._install_status, key)):
                try:
                    if open_app_for_service(self.name):
                        self.thread_result = "app"
                        return
                except Exception:
                    pass
            self.thread_result = "store"
            try:
                open_store_search(self.name)
            except Exception:
                pass
        except Exception:
            try:
                open_store_search(self.name)
            except Exception:
                pass
            self.thread_result = "store"

    def _schedule_check(self):
        try:
            self.app.root.after(120, self._check_result)
        except Exception:
            pass

    def _check_result(self):
        if self.closed:
            return
        if self.thread_result is None:
            self._schedule_check()
            return
        try:
            self.app.db.add_history(self.name)
        except Exception:
            pass
        opened = self.thread_result
        svc = self.name
        if opened == "app":
            # Entra no remoto ANTES de fechar o dialogo: o Nexus minimiza
            # (com o dialogo junto) e o foco vai p/ o app, nunca de volta
            # ao Nexus — sem isso o <FocusIn> mataria o remoto na hora.
            self.app.enter_remote_mode(svc)
            # Tenta deixar o app em tela cheia sem bordas (big picture).
            try:
                before = [hw for hw, _p, _t in _top_level_windows()]
            except Exception:
                before = []
            try:
                self.app.root.after(
                    2500, lambda: self.app.borderless_new_app(before))
            except Exception:
                pass
        self._close()


# ===================== GAME CARD DIALOG =====================
class GameCardDialog:
    """Janela do card de jogo: Play + Config. Mouse, teclado e controle."""

    def __init__(self, app, name):
        self.app = app
        self.name = name
        self.mode = "main"
        self.focus_idx = 0
        self.closed = False
        self.born = time.time()
        self.options = []

        lang = app.lang
        win = tk.Toplevel(app.root)
        self.win = win
        win.title(name)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        self.win_w = 480
        _apply_dark_title(win, "gamedlg")
        _apply_dark_title_later(win, tag="gamedlg")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - self.win_w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - 360) // 2
        except Exception:
            x, y = 200, 150
        win.geometry(f"{self.win_w}x360+{max(0, x)}+{max(0, y)}")

        tk.Label(win, text=f"\u25C6 {name}", font=("Segoe UI", 20, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 wraplength=self.win_w - 40).pack(pady=(22, 4))
        self.sub = tk.Label(win, text=t("games_how", lang), font=("Segoe UI", 13),
                            fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.sub.pack(pady=(0, 16))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)

        tk.Label(win, text=t("dlg_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(side="bottom", pady=14)

        win.bind("<Left>", lambda e: self.move_prev())
        win.bind("<Right>", lambda e: self.move_next())
        win.bind("<Up>", lambda e: self.move_prev())
        win.bind("<Down>", lambda e: self.move_next())
        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<space>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.cancel())
        win.protocol("WM_DELETE_WINDOW", self.cancel)
        win.grab_set()

        self.show_main()

    def _reg(self, btn, command):
        idx = len(self.options)
        self.options.append((btn, command))
        btn.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        return btn

    def _click(self, idx):
        self.set_focus(idx)
        self.confirm()

    def _resize(self, h):
        try:
            self.win.geometry(f"{self.win_w}x{h}+{self.win.winfo_x()}+{self.win.winfo_y()}")
        except Exception:
            pass

    def show_main(self):
        if self.closed:
            return
        self.mode = "main"
        lang = self.app.lang
        self._resize(360)
        try:
            self.sub.configure(text=t("games_how", lang))
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        row = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        row.pack()
        for i, (key, cmd) in enumerate((("dlg_play", self.play),
                                        ("dlg_config", self.show_edit))):
            b = tk.Button(row, text=t(key, lang), font=("Segoe UI", 16, "bold"),
                          width=11, height=2, relief="flat", bd=0, cursor="hand2",
                          command=lambda idx=i: self._click(idx))
            b.grid(row=0, column=i, padx=12)
            self._reg(b, cmd)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def show_edit(self):
        if self.closed:
            return
        self.mode = "edit"
        lang = self.app.lang
        name = self.name
        self._resize(640)
        try:
            self.sub.configure(text=t("dlg_config", lang))
        except Exception:
            pass
        for w in self.body.winfo_children():
            w.destroy()
        self.options = []
        self.focus_idx = 0
        try:
            _tipo, _loc = self.app.item_details(name)
            folder = _loc or self.app.game_folder(name) or ""
            tk.Label(self.body, text=f"{t('games_folder', lang)} {folder}",
                     font=("Segoe UI", 10), fg=Config.TEXT_SECONDARY,
                     bg=Config.BG_SIDEBAR, wraplength=self.win_w - 60,
                     justify="center").pack(pady=(0, 8))
        except Exception:
            pass
        favs = self.app.settings.get("favorites", [])
        rows = [
            ((f"\u2716 {t('ctx_remove_fav', lang)}" if name in favs
              else f"\u2B50 {t('ctx_add_fav', lang)}"), self._edit_fav),
            (t("dlg_color", lang), self._edit_color),
            (t("dlg_color_reset", lang), self._edit_color_reset),
            (t("dlg_cover", lang), self._edit_cover),
            (t("games_openfolder", lang), self._edit_open_folder),
            (f"\U0001F5D1 {t('ctx_delete', lang)}", self._edit_delete),
            (t("dlg_back", lang), self.show_main),
        ]
        for i, (text, cmd) in enumerate(rows):
            b = tk.Button(self.body, text=text, font=("Segoe UI", 13),
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          padx=18, command=lambda idx=i: self._click(idx))
            b.pack(fill="x", padx=40, pady=2)
            self._reg(b, cmd)
        self._paint()
        try:
            self.options[0][0].focus_set()
        except Exception:
            pass

    def _alive(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def _after_refresh(self, rebuild=True):
        if not self._alive():
            self._close()
            return False
        if rebuild and self.mode == "edit":
            self.show_edit()
        return True

    def play(self):
        try:
            self.app.launch_game(self.name)
        finally:
            self._close()

    def _edit_fav(self):
        self.app.toggle_favorite(self.name)
        self._after_refresh()

    def _edit_color(self):
        menu = NexusMenuWindow(self.app, t("dlg_color", self.app.lang), [],
                               icon="\U0001F3A8", width=480, cols=4)
        opts = []
        for label, color in CARD_COLOR_PRESETS:
            opts.append((label,
                         lambda col=color: self._pick_card_color(menu, col),
                         {"bg": color,
                          "fg": "black" if color == "#ffd600" else "white",
                          "activebackground": color, "width": 8}))
        opts.append((t("sidebar_close", self.app.lang), menu.close, {"width": 8}))
        menu.set_options(opts, opt_font=10)

    def _pick_card_color(self, menu, color):
        try:
            menu.close()
        except Exception:
            pass
        self.app.set_card_color(self.name, color)
        self._after_refresh(rebuild=False)
        if self._alive() and self.mode == "edit":
            self.show_edit()

    def _edit_color_reset(self):
        self.app.reset_card_color(self.name)
        self._after_refresh()

    def _edit_cover(self):
        try:
            picked = filedialog.askopenfilename(
                title=self.name,
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.ico"),
                           ("Todas", "*.*")],
                parent=self.win)
        except Exception:
            picked = ""
        if picked and self.app.set_game_cover(self.name, picked):
            self.app.refresh_ui()
        self._after_refresh(rebuild=False)
        if self._alive() and self.mode == "edit":
            self.show_edit()

    def _edit_open_folder(self):
        try:
            self.app.open_game_location(self.name)
        except Exception:
            pass

    def _edit_delete(self):
        name = self.name
        lang = self.app.lang
        try:
            if self.app.game_is_platform(name):
                self.app.remove_platform_game(name)
                self._close()
                return
            if self.app.game_is_external(name):
                self.app.remove_external_game(name)
                self._close()
                return
        except Exception:
            pass

        def _yes(menu):
            try:
                menu.close()
            except Exception:
                pass
            ok = self.app.delete_game_folder(name)
            if ok:
                try:
                    self.app.refresh_ui()
                except Exception:
                    pass
            if not self._alive():
                self._close()
            elif self.mode == "edit":
                self.show_edit()

        menu = NexusMenuWindow(self.app, t("ctx_delete", lang), [],
                               subtitle=f"{t('games_del_q', lang)} '{name}'?",
                               icon="\U0001F5D1", width=460)
        menu.set_options([(t("ctx_delete", lang), lambda: _yes(menu)),
                          (t("sidebar_close", lang), menu.close)])

    def _paint(self):
        for i, (b, _cmd) in enumerate(self.options):
            if i == self.focus_idx:
                b.configure(bg=Config.ACCENT, fg="white",
                            highlightbackground=Config.ACCENT_GLOW, highlightthickness=2)
            else:
                b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                            highlightbackground=Config.BORDER, highlightthickness=1)

    def set_focus(self, idx):
        if self.closed or not self.options:
            return
        self.focus_idx = idx % len(self.options)
        self._paint()

    def move(self, direction=None):
        self.move_next()

    def move_prev(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx - 1) % len(self.options)
        self._paint()

    def move_next(self):
        if self.closed or not self.options:
            return
        self.focus_idx = (self.focus_idx + 1) % len(self.options)
        self._paint()

    def confirm(self):
        if self.closed or not self.options:
            return
        _btn, cmd = self.options[self.focus_idx]
        try:
            cmd()
        except Exception:
            pass

    def cancel(self):
        if self.closed:
            return
        if self.mode == "edit":
            self.show_main()
        else:
            self._close()

    def _close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.open_dialog is self:
                self.app.open_dialog = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# ===================== NEXUS TEXT DIALOG =====================
class NexusTextDialog:
    """Pequeno editor de texto estilo Nexus (mouse + teclado + controle)."""

    def __init__(self, app, title, prompt, initial, on_done):
        self.app = app
        self.closed = False
        self.born = time.time()
        self.on_done = on_done
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(title)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        w, h = 480, 250
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        except Exception:
            x, y = 200, 150
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        _apply_dark_title(win, "textdlg")
        _apply_dark_title_later(win, tag="textdlg")
        # O grab bloqueia os binds do root: limpa o latch aqui dentro
        win.bind("<Button-1>", lambda e: setattr(app, "using_gamepad", False), add="+")
        win.bind("<Key>", lambda e: setattr(app, "using_gamepad", False), add="+")

        tk.Label(win, text=f"\U0001F517 {title}", font=("Segoe UI", 18, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR).pack(pady=(18, 4))
        tk.Label(win, text=prompt, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(pady=(0, 8))
        self.entry = tk.Entry(win, font=("Segoe UI", 13), bg=Config.BG_CARD,
                              fg=Config.TEXT_PRIMARY, insertbackground=Config.ACCENT,
                              relief="flat", bd=0, highlightbackground=Config.BORDER,
                              highlightthickness=1)
        self.entry.pack(fill="x", padx=36, ipady=8)
        app.bind_keyboard_popup(self.entry)
        if initial:
            self.entry.insert(0, initial)
            self.entry.select_range(0, "end")

        row = tk.Frame(win, bg=Config.BG_SIDEBAR)
        row.pack(pady=16)
        tk.Button(row, text="OK", font=("Segoe UI", 13, "bold"),
                  bg=Config.ACCENT, fg="white", relief="flat", bd=0,
                  cursor="hand2", padx=36, pady=6,
                  command=self.confirm).pack(side="left", padx=8)
        tk.Button(row, text="\u2328", font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY, relief="flat", bd=0,
                  cursor="hand2", padx=14, pady=6,
                  command=lambda: self.app.open_keyboard(self.entry)).pack(side="left", padx=8)
        tk.Button(row, text=t("sidebar_close", lang), font=("Segoe UI", 13),
                  bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY, relief="flat", bd=0,
                  cursor="hand2", padx=24, pady=6,
                  command=self.close).pack(side="left", padx=8)

        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        win.grab_set()
        try:
            self.entry.focus_set()
            app.active_menu = self
        except Exception:
            pass

    def on_hat(self, hat):
        return

    def confirm(self):
        if self.closed:
            return
        try:
            result = self.entry.get().strip()
        except Exception:
            result = ""
        cb = self.on_done
        self.close()
        try:
            if result:
                cb(result)
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.active_menu is self:
                self.app.active_menu = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# (util do teclado virtual; a classe NexusKeyboard viaja na fase 2c)
def sniff_numeric_entry(entry):
    """Conteudo com cara de numero (porta, ano, telefone...) -> numérico."""
    try:
        txt = (entry.get() or "").strip()
    except Exception:
        return False
    return bool(txt) and re.match(r"^[\d\s\.\,\+\-\(\)/:]+$", txt) is not None


# (helpers de modal; usados pelos dialogos e pelo GamepadManager)
def _modal_alive(w):
    """Janela modal realmente aberta (nao so flag: sem zumbis destruidos)."""
    try:
        if w is None or getattr(w, "closed", True):
            return False
        win = getattr(w, "win", None)
        return bool(win is not None and win.winfo_exists())
    except Exception:
        return False


def top_modal(app):
    """A janela modal mais nova ainda aberta (dialogo, menu, texto, teclado)."""
    cands = []
    try:
        d = app.open_dialog
        if _modal_alive(d):
            cands.append(d)
        m = app.active_menu
        if _modal_alive(m):
            cands.append(m)
        k = getattr(app, "kb_window", None)
        if _modal_alive(k):
            cands.append(k)
    except Exception:
        pass
    if not cands:
        return None
    return max(cands, key=lambda w: getattr(w, "born", 0))


# ===================== NEXUS MENU WINDOW =====================
class NexusMenuWindow:
    """Janela padrao Nexus: titulo + opcoes navegaveis.
    Mouse, teclado e controle: setas movem, A confirma, B fecha."""

    def __init__(self, app, title, options=(), subtitle="", icon="\u25C6",
                 width=440, cols=1, opt_font=14):
        self.app = app
        self.closed = False
        self.born = time.time()
        self.focus_idx = 0
        self.cols = max(1, cols)
        self.options = []
        self.btns = []
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(title)
        win.configure(bg=Config.BG_SIDEBAR)
        win.transient(app.root)
        win.resizable(False, False)
        self.win_w = width
        _apply_dark_title(win, "menuwin")
        _apply_dark_title_later(win, tag="menuwin")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - width) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - 400) // 2
        except Exception:
            x, y = 200, 150
        self.win_x, self.win_y = max(0, x), max(0, y)

        tk.Label(win, text=f"{icon} {title}", font=("Segoe UI", 22, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 wraplength=width - 40).pack(pady=(20, 4))
        self.sub = tk.Label(win, text=subtitle, font=("Segoe UI", 13),
                            fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                            wraplength=width - 40, justify="center")
        self.sub.pack(pady=(0, 12))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)
        self.set_options(options, opt_font=opt_font)

        tk.Label(win, text=t("dlg_hint", lang), font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(side="bottom", pady=14)

        win.bind("<Up>", lambda e: self.move(0, -1))
        win.bind("<Down>", lambda e: self.move(0, 1))
        win.bind("<Left>", lambda e: self.move(-1, 0))
        win.bind("<Right>", lambda e: self.move(1, 0))
        win.bind("<Return>", lambda e: self.confirm())
        win.bind("<KP_Enter>", lambda e: self.confirm())
        win.bind("<space>", lambda e: self.confirm())
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        win.grab_set()
        try:
            app.active_menu = self
        except Exception:
            pass

    def set_options(self, options, opt_font=14):
        if self.closed:
            return
        for w in self.body.winfo_children():
            w.destroy()
        self.options = list(options)
        self.btns = []
        self.focus_idx = 0
        for i, opt in enumerate(self.options):
            label, cmd = opt[0], opt[1]
            style = opt[2] if len(opt) > 2 else {}
            b = tk.Button(self.body, text=label, font=("Segoe UI", opt_font, "bold"),
                          relief="flat", bd=0, cursor="hand2",
                          highlightthickness=3,
                          command=lambda idx=i: (self.set_focus(idx), self.confirm()))
            b.configure(bg=style.get("bg", Config.BG_CARD),
                        fg=style.get("fg", Config.TEXT_PRIMARY),
                        activebackground=style.get("activebackground", Config.BG_CARD_HOVER),
                        activeforeground=style.get("fg", Config.TEXT_PRIMARY))
            if self.cols == 1:
                b.configure(anchor="w", padx=18)
                b.pack(fill="x", padx=40, pady=3)
            else:
                b.configure(width=style.get("width", 10))
                b.grid(row=i // self.cols, column=i % self.cols, padx=4, pady=4)
            b.bind("<Enter>", lambda e, idx=i: self.set_focus(idx))
            self.btns.append(b)
        rows = (len(self.options) + self.cols - 1) // max(1, self.cols)
        h = 250 + rows * (56 if self.cols > 1 else 52)
        try:
            self.win.geometry(f"{self.win_w}x{h}+{self.win_x}+{self.win_y}")
        except Exception:
            pass
        self._paint()
        try:
            if self.btns:
                self.btns[0].focus_set()
        except Exception:
            pass

    def _paint(self):
        for i, b in enumerate(self.btns):
            try:
                opt = self.options[i]
                style = opt[2] if len(opt) > 2 else {}
                plain = style.get("bg", Config.BG_CARD) == Config.BG_CARD
                if i == self.focus_idx:
                    b.configure(highlightbackground="white",
                                highlightcolor="white")
                    if plain:
                        b.configure(bg=Config.ACCENT, fg="white")
                else:
                    b.configure(highlightbackground=Config.BORDER,
                                highlightcolor=Config.BORDER)
                    if plain:
                        b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY)
                    else:
                        b.configure(bg=style.get("bg", Config.BG_CARD),
                                    fg=style.get("fg", Config.TEXT_PRIMARY))
            except Exception:
                pass

    def set_focus(self, idx):
        if self.closed or not self.btns:
            return
        self.focus_idx = idx % len(self.btns)
        self._paint()

    def on_hat(self, hat):
        if hat == (0, 1):
            self.move(0, -1)
        elif hat == (0, -1):
            self.move(0, 1)
        elif hat == (-1, 0):
            self.move(-1, 0)
        elif hat == (1, 0):
            self.move(1, 0)

    def move(self, dh, dv):
        if self.closed or not self.btns:
            return
        n = len(self.btns)
        if self.cols == 1:
            d = dv if dv != 0 else dh
            self.focus_idx = min(n - 1, max(0, self.focus_idx + d))
        else:
            r, c = divmod(self.focus_idx, self.cols)
            r = min((n - 1) // self.cols, max(0, r + dv))
            c = min(self.cols - 1, max(0, c + dh))
            self.focus_idx = min(n - 1, r * self.cols + c)
        self._paint()

    def confirm(self):
        if self.closed or not self.options:
            return
        try:
            self.options[self.focus_idx][1]()
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.active_menu is self:
                self.app.active_menu = None
        except Exception:
            pass
        try:
            self.win.grab_release()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
