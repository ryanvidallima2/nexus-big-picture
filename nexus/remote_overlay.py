# -*- coding: utf-8 -*-
"""Menu rapido sobre o app/site aberto (modo remoto).

Start abre; D-pad navega, A confirma, B/Start fecha.
Config: som (master ao vivo), janela (borda/tela) e imagem
(brilho + tema). Voltar ao Nexus = sair do remoto.
"""

import time
import tkinter as tk

from .audio import audio_get_master, audio_set_master
from .config import Config, save_settings
from .i18n import t
from .win32 import (
    _hwnd_alive, bring_to_front, force_borderless_fullscreen,
    force_topmost_noactivate, is_borderless, restore_windowed,
    set_brightness,
)


class RemoteOverlay:
    """Janela topmost sobre o app externo (Nexus minimizado)."""

    WIDTH = 400

    def __init__(self, app):
        self.app = app
        self.closed = False
        self.born = time.time()
        self.focus = 0
        self.items = []
        self.vol_item = None
        self.bright_item = None
        self.win_item = None
        lang = app.lang

        try:
            svc = ""
            gp = getattr(app, "gamepad", None)
            if gp is not None:
                svc = getattr(gp, "remote_service", "") or ""
        except Exception:
            svc = ""
        self.service = svc

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(t("ov_title", lang))
        win.configure(bg=Config.BG_SIDEBAR)
        win.resizable(False, False)
        try:
            win.overrideredirect(True)
        except Exception:
            pass
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
        try:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            w, h = self.WIDTH, 560
            x, y = (sw - w) // 2, (sh - h) // 2
            win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass
        try:
            win.lift()
            force_topmost_noactivate(win)
        except Exception:
            pass

        head = tk.Frame(win, bg=Config.BG_SIDEBAR)
        head.pack(fill="x", pady=(14, 2), padx=16)
        tk.Label(head, text="\U0001F3AE %s" % (svc or t("ov_title", lang)),
                 font=("Segoe UI", 16, "bold"), fg=Config.ACCENT,
                 bg=Config.BG_SIDEBAR, anchor="w").pack(side="left")
        tk.Button(head, text="\u2715", font=("Segoe UI", 11, "bold"),
                  bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY,
                  activebackground="#e94560", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2", padx=10, pady=2,
                  command=self.close).pack(side="right")
        tk.Frame(win, bg=Config.BORDER, height=1).pack(
            fill="x", padx=16, pady=(2, 8))

        self.body = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)
        self.page = "menu"
        self._show_page("menu")

        hint = tk.Label(win, text=t("ov_hint", lang), font=("Segoe UI", 10),
                        fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        hint.pack(side="bottom", pady=10)
        win.bind("<Escape>", lambda e: self.close())
        win.bind("<Return>", lambda e: self.press("south"))
        win.bind("<KP_Enter>", lambda e: self.press("south"))
        win.bind("<space>", lambda e: self.press("south"))
        try:
            win.bind("<Motion>", lambda e: self._mouse_seen(), add="+")
            win.bind("<Button-1>", lambda e: self._mouse_seen(), add="+")
        except Exception:
            pass
        win.protocol("WM_DELETE_WINDOW", self.close)
        try:
            app.remote_overlay = self
        except Exception:
            pass
        try:
            win.after(400, lambda: self._refront())
        except Exception:
            pass
        try:
            self.app.play_open_sound()
        except Exception:
            pass

    # ---------- estrutura ----------
    def _section(self, text):
        tk.Label(self.body, text=text.upper(), font=("Segoe UI", 11, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x", padx=16, pady=(8, 2))

    def _button(self, text, cmd):
        b = tk.Button(self.body, text=text, font=("Segoe UI", 13),
                      fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                      activebackground=Config.BG_CARD_HOVER,
                      activeforeground=Config.TEXT_PRIMARY,
                      relief="flat", bd=0, cursor="hand2", anchor="w",
                      padx=18, pady=7, highlightthickness=1,
                      highlightbackground=Config.BORDER,
                      command=cmd)
        b.pack(fill="x", padx=16, pady=2)
        item = {"kind": "button", "widget": b, "cmd": cmd}
        self.items.append(item)
        idx = len(self.items) - 1
        b.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        return item

    def _slider(self, label, vmin, vmax, get, put, step=5):
        row = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        row.pack(fill="x", padx=16, pady=(4, 0))
        lab = tk.Label(row, text=label, font=("Segoe UI", 12),
                       fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR,
                       wraplength=self.WIDTH - 150, justify="left")
        lab.pack(side="left")
        val = tk.Label(row, font=("Segoe UI", 12, "bold"),
                       fg=Config.ACCENT, bg=Config.BG_SIDEBAR, width=4)
        val.pack(side="right")
        sc = tk.Scale(self.body, from_=vmin, to=vmax, orient="horizontal",
                      showvalue=False, bg=Config.BG_SIDEBAR,
                      fg=Config.TEXT_PRIMARY, troughcolor=Config.BG_CARD,
                      highlightthickness=0, bd=0)
        sc.pack(fill="x", padx=16)
        item = {"kind": "slider", "scale": sc, "label": lab, "value": val,
                "min": vmin, "max": vmax, "step": step,
                "get": get, "put": put, "prog": False}
        self.items.append(item)
        idx = len(self.items) - 1

        def _drag(v, _it=item):
            if _it["prog"]:
                return
            try:
                _it["put"](int(float(v)))
            except Exception:
                pass
            self.refresh_slider(_it, tick=False)

        sc.configure(command=_drag)
        sc.bind("<ButtonRelease-1>",
                lambda e, _it=item: self.refresh_slider(_it, tick=True))
        sc.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        for w in (row, lab, val):
            try:
                w.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
            except Exception:
                pass
        self.refresh_slider(item, tick=False)
        return item

    def refresh_slider(self, item, tick=True):
        try:
            v = max(item["min"], min(item["max"], int(item["get"]())))
        except Exception:
            return
        try:
            item["prog"] = True
            item["scale"].set(v)
        except Exception:
            pass
        finally:
            try:
                item["prog"] = False
            except Exception:
                pass
        try:
            item["value"].config(text=str(v))
        except Exception:
            pass

    # ---------- paginas ----------
    def _show_page(self, page):
        if self.closed:
            return
        self.page = page
        self.focus = 0
        self.items = []
        try:
            for w in self.body.winfo_children():
                w.destroy()
        except Exception:
            return
        if page == "config":
            self._page_config()
        else:
            self._page_menu()
        self.paint()

    def _page_menu(self):
        lang = self.app.lang
        self._section(t("ov_menu", lang))
        self._button(t("ov_config", lang),
                     lambda: self._show_page("config"))
        self._button("\u2190 " + t("ov_back", lang), self.back_to_nexus)

    def _page_config(self):
        lang = self.app.lang
        self._section(t("ov_config", lang))
        self.vol_item = self._slider(
            t("ov_sound", lang), 0, 100, self._get_vol, self._put_vol, step=5)
        self._section(t("ov_image", lang))
        self._bright_val = getattr(self, "_bright_val", 100)
        self.bright_item = self._slider(
            t("ov_bright", lang), 5, 100, lambda: self._bright_val,
            self._put_bright, step=5)
        self.win_item = self._button("", self._toggle_window)
        self._paint_window()
        self._button("\u2190 " + t("ov_menu", lang),
                     lambda: self._show_page("menu"))

    # ---------- secoes ----------
    def _get_vol(self):
        try:
            v = audio_get_master()
            if v is not None:
                return int(round(v * 100))
        except Exception:
            pass
        return 70

    def _put_vol(self, v):
        try:
            audio_set_master(max(0, min(100, int(v))) / 100.0)
        except Exception:
            pass

    def _put_bright(self, v):
        try:
            v = max(5, min(100, int(v)))
        except Exception:
            return
        try:
            if set_brightness(v):
                self._bright_val = v
        except Exception:
            pass

    # ---------- janela ----------
    def _remote_hwnd(self):
        try:
            gp = self.app.gamepad
            hwnd = getattr(gp, "remote_hwnd", None) if gp else None
            if hwnd and _hwnd_alive(hwnd):
                return hwnd
        except Exception:
            pass
        return None

    def _paint_window(self):
        try:
            hwnd = self._remote_hwnd()
            if not hwnd:
                self.win_item["widget"].configure(
                    text="\U0001F5BC " + t("ov_window", self.app.lang)
                    + " — " + t("ov_nosupport", self.app.lang))
                return
            if is_borderless(hwnd):
                txt = "\u2713 " + t("ov_full", self.app.lang)
            else:
                txt = "\u2713 " + t("ov_win", self.app.lang)
            self.win_item["widget"].configure(text=txt)
        except Exception:
            pass

    def _toggle_window(self):
        try:
            hwnd = self._remote_hwnd()
            if not hwnd:
                return
            if is_borderless(hwnd):
                restore_windowed(hwnd)
            else:
                force_borderless_fullscreen(hwnd)
            self._paint_window()
            try:
                self.app.play_tick()
            except Exception:
                pass
        except Exception:
            pass

    # ---------- imagem ----------

    # ---------- acoes ----------
    def back_to_nexus(self):
        self.close()
        try:
            self.app.exit_remote_mode()
        except Exception:
            pass

    def _mouse_seen(self):
        try:
            self.app.using_gamepad = False
        except Exception:
            pass

    def _refront(self):
        if self.closed:
            return
        try:
            self.win.attributes("-topmost", True)
            self.win.lift()
            force_topmost_noactivate(self.win)
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if getattr(self.app, "remote_overlay", None) is self:
                self.app.remote_overlay = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
        try:
            self.app.play_back_sound()
        except Exception:
            pass
        try:
            hwnd = self._remote_hwnd()
            if hwnd:
                bring_to_front(hwnd)
        except Exception:
            pass

    # ---------- navegacao (controle) ----------
    def set_focus(self, idx):
        if self.closed or not self.items:
            return
        new = idx % len(self.items)
        if new != self.focus:
            self.focus = new
            self.paint()
            try:
                self.app.play_tick()
            except Exception:
                pass

    def paint(self):
        for i, item in enumerate(self.items):
            try:
                if item.get("kind") == "slider":
                    item["label"].configure(
                        fg=Config.ACCENT if i == self.focus
                        else Config.TEXT_PRIMARY)
                else:
                    b = item["widget"]
                    if i == self.focus:
                        b.configure(bg=Config.ACCENT, fg="white",
                                    highlightbackground="white",
                                    highlightthickness=3)
                    else:
                        b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                    highlightbackground=Config.BORDER,
                                    highlightthickness=1)
            except Exception:
                pass
        try:
            self._paint_window()
        except Exception:
            pass

    def adjust(self, d):
        if self.closed or not self.items:
            return
        item = self.items[self.focus % len(self.items)]
        kind = item.get("kind")
        if kind == "slider":
            try:
                cur = int(item["get"]())
            except Exception:
                return
            try:
                item["put"](max(item["min"], min(item["max"],
                                                 cur + d * item["step"])))
            except Exception:
                return
            self.refresh_slider(item, tick=True)

    def on_hat(self, hat):
        if self.closed:
            return
        if hat == (0, 1):
            self.set_focus(self.focus - 1)
        elif hat == (0, -1):
            self.set_focus(self.focus + 1)
        elif hat == (-1, 0):
            self.adjust(-1)
        elif hat == (1, 0):
            self.adjust(1)

    def press(self, logical):
        if self.closed:
            return
        if logical == "east":
            if getattr(self, "page", "menu") == "menu":
                self.close()
            else:
                self._show_page("menu")
            return
        if logical != "south" or not self.items:
            return
        item = self.items[self.focus % len(self.items)]
        if item.get("kind") == "button":
            try:
                item["cmd"]()
            except Exception:
                pass
