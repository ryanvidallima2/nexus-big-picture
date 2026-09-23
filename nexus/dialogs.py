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
from .guide import GUIDE_CATS, guide_cat_body, guide_cat_title, guide_title
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


# ===================== NEXUS TEXT DIALOG =====================
class NexusTextDialog:
    """Pequeno editor de texto estilo Nexus (mouse + teclado + controle)."""

    def __init__(self, app, title, prompt, initial, on_done, password=False):
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
        try:
            win.bind("<Motion>", lambda e: app._on_mouse_motion(), add="+")
        except Exception:
            pass

        tk.Label(win, text=f"\U0001F517 {title}", font=("Segoe UI", 18, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR).pack(pady=(18, 4))
        tk.Label(win, text=prompt, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR).pack(pady=(0, 8))
        self.entry = tk.Entry(win, font=("Segoe UI", 13), bg=Config.BG_CARD,
                              fg=Config.TEXT_PRIMARY, insertbackground=Config.ACCENT,
                              relief="flat", bd=0, highlightbackground=Config.BORDER,
                              highlightthickness=1)
        self.entry.pack(fill="x", padx=36, ipady=8)
        if password:
            try:
                self.entry.configure(show="•")
            except Exception:
                pass
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
        try:
            win.bind("<Motion>", lambda e: app._on_mouse_motion(), add="+")
        except Exception:
            pass
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

# ===================== GUIDE WINDOW =====================
class GuideWindow(NexusMenuWindow):
    """Manual de uso: categorias a esquerda, guia a direita.
    Mouse, teclado e controle: cima/baixo trocam de categoria."""

    WIN_W, WIN_H = 740, 540

    def __init__(self, app):
        self.cat_btns = []
        self.body_title = None
        self.body_text = None
        NexusMenuWindow.__init__(self, app, guide_title(app.lang), [],
                                 icon="\U0001F4D6", width=self.WIN_W)
        try:
            for w in self.body.winfo_children():
                w.destroy()
        except Exception:
            pass
        left_wrap = tk.Frame(self.body, bg=Config.BG_SIDEBAR, width=220)
        left_wrap.pack(side="left", fill="y", padx=(0, 8))
        left_wrap.pack_propagate(False)
        import tkinter.ttk as _ttk
        _gsb = _ttk.Scrollbar(left_wrap, orient="vertical",
                              style="Transparent.Vertical.TScrollbar")
        # Scrollbar PRIMEIRO: canvas com expand antes esmaga ela p/ 1px
        _gsb.pack(side="right", fill="y")
        left = tk.Canvas(left_wrap, bg=Config.BG_SIDEBAR,
                         highlightthickness=0, bd=0)
        left.pack(side="left", fill="both", expand=True)
        self.guide_canvas = left
        _gsb.configure(command=left.yview)
        left.configure(yscrollcommand=_gsb.set)
        inner = tk.Frame(left, bg=Config.BG_SIDEBAR)
        left.create_window((0, 0), window=inner, anchor="nw",
                           tags="guide_inner")
        inner.bind("<Configure>", lambda e: left.configure(
            scrollregion=left.bbox("all")))
        left.bind("<Configure>", lambda e: left.itemconfig(
            "guide_inner", width=e.width))
        try:
            self.app._bind_wheel_tree(self.win, self._guide_wheel)
        except Exception:
            pass
        right = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        right.pack(side="left", fill="both", expand=True)
        self.body_title = tk.Label(right, text="", font=("Segoe UI", 16, "bold"),
                                   fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                                   anchor="w", justify="left")
        self.body_title.pack(fill="x", pady=(2, 8))
        self.body_text = tk.Label(right, text="", font=("Segoe UI", 12),
                                  fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR,
                                  anchor="nw", justify="left",
                                  wraplength=self.WIN_W - 300)
        self.body_text.pack(fill="both", expand=True)
        for i, cat in enumerate(GUIDE_CATS):
            b = tk.Button(inner, text="%s  %s" % (
                              cat.get("icon", ""),
                              guide_cat_title(cat, app.lang)),
                          font=("Segoe UI", 12, "bold"),
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          padx=12, highlightthickness=3,
                          command=lambda idx=i: self.select(idx))
            b.pack(fill="x", pady=2)
            b.bind("<Enter>", lambda e, idx=i: self.select(idx))
            self.cat_btns.append(b)
        try:
            self.win.geometry(f"{self.WIN_W}x{self.WIN_H}+{self.win_x}+{self.win_y}")
        except Exception:
            pass
        self.btns = list(self.cat_btns)
        self.select(0)

    def set_options(self, options, opt_font=14):
        # Chamado pela base no __init__: corpo proprio vem depois.
        try:
            self.focus_idx = 0
        except Exception:
            pass

    def _guide_wheel(self, event):
        try:
            cv = self.guide_canvas
            if event.delta > 0 and self.app._at_top(cv):
                return "break"
            if event.delta < 0 and self.app._at_bottom(cv):
                return "break"
            cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def _guide_ensure_visible(self):
        try:
            cv = self.guide_canvas
            btns = self.cat_btns
            if not btns or self.focus_idx >= len(btns):
                return
            cv.update_idletasks()
            w = btns[self.focus_idx]
            w.update_idletasks()
            ch = cv.winfo_height()
            inner_h = cv.bbox("all")
            total = inner_h[3] if inner_h else 0
            if total <= 0 or ch <= 0 or total <= ch:
                return
            wy = w.winfo_rooty() - cv.winfo_rooty()
            wh = w.winfo_height()
            first, _ = cv.yview()
            if wy < 0:
                cv.yview_moveto(max(0.0, first + wy / total))
            elif wy + wh > ch:
                cv.yview_moveto(min(1.0, first + (wy + wh - ch) / total))
        except Exception:
            pass

    def select(self, idx):
        if self.closed or not self.cat_btns:
            return
        new = idx % len(self.cat_btns)
        changed = (new != self.focus_idx)
        self.focus_idx = new
        try:
            cat = GUIDE_CATS[self.focus_idx]
            self.body_title.configure(text="%s  %s" % (
                cat.get("icon", ""), guide_cat_title(cat, self.app.lang)))
            self.body_text.configure(text=guide_cat_body(cat, self.app.lang))
        except Exception:
            pass
        self._paint()
        self._guide_ensure_visible()
        if changed:
            try:
                self.app.play_tick()
            except Exception:
                pass

    def _paint(self):
        for i, b in enumerate(self.cat_btns):
            try:
                if i == self.focus_idx:
                    b.configure(bg=Config.ACCENT, fg="white",
                                highlightbackground="white",
                                highlightcolor="white")
                else:
                    b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                highlightbackground=Config.BORDER,
                                highlightcolor=Config.BORDER)
            except Exception:
                pass

    def set_focus(self, idx):
        self.select(idx)

    def on_hat(self, hat):
        if hat in ((0, 1), (-1, 0)):
            self.select(self.focus_idx - 1)
        elif hat in ((0, -1), (1, 0)):
            self.select(self.focus_idx + 1)

    def move(self, dh, dv):
        d = dv if dv != 0 else dh
        self.select(self.focus_idx + d)

    def confirm(self):
        if not self.closed:
            self.select(self.focus_idx)

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
    """A janela modal mais nova ainda aberta (dialogo, menu, texto, teclado, QR)."""
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
        q = getattr(app, "qr_window", None)
        if _modal_alive(q):
            cands.append(q)
    except Exception:
        pass
    if not cands:
        return None
    return max(cands, key=lambda w: getattr(w, "born", 0))


