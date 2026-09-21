# -*- coding: utf-8 -*-
"""Painel lateral + janela de configuracao do controle (extraido sem alteracao)."""

import tkinter as tk
import tkinter.ttk as tk_ttk

from .config import Config, save_settings
from .dialogs import NexusTextDialog
from .i18n import t
from .input import _play_test_tone
from .pad import (
    DEFAULT_NEXUS_MAP, DEFAULT_REMOTE_MAP, NEXUS_ACTION_ORDER,
    REMOTE_ACTION_ORDER, PAD_LAYOUT_LABEL, PAD_PROFILE_SLOTS,
    DEFAULT_PAD_DEADZONE, normalize_pad_value, pad_logical_label,
)
from .win32 import _apply_dark_title, _apply_dark_title_later

try:
    import pygame
    import pygame.joystick
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# ===================== GAMEPAD CONFIG WINDOW =====================
class GamepadConfigWindow:
    """Janela estilo Nexus: mostra e remapeia os botoes (Nexus x Apps)."""

    def __init__(self, app):
        self.app = app
        self.closed = False
        self.capture_token = 0
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(t("settings_gamepad", lang))
        win.configure(bg=Config.BG_PRIMARY)
        win.transient(app.root)
        win.resizable(False, False)
        w, h = 560, 780
        _apply_dark_title(win, "padwin")
        _apply_dark_title_later(win, tag="padwin")
        win.update_idletasks()
        try:
            x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
            y = app.root.winfo_y() + (app.root.winfo_height() - h) // 2
        except Exception:
            x, y = 200, 100
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        outer = tk.Canvas(win, bg=Config.BG_PRIMARY, highlightthickness=0, bd=0)
        outer.pack(side="left", fill="both", expand=True)
        self.scroll_canvas = outer
        sb = tk_ttk.Scrollbar(win, orient="vertical", command=outer.yview,
                              style="Accent.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        outer.configure(yscrollcommand=sb.set)
        self.body = tk.Frame(outer, bg=Config.BG_PRIMARY)
        outer.create_window((0, 0), window=self.body, anchor="nw", tags="inner")
        self.body.bind("<Configure>", lambda e: outer.configure(
            scrollregion=outer.bbox("all")))
        outer.bind("<Configure>", lambda e: outer.itemconfig("inner", width=e.width))

        try:
            gp = app.gamepad
            if PYGAME_AVAILABLE and gp and gp.joystick:
                status = f"\u2713 {gp.joystick.get_name()}"
            else:
                status = t("pad_none", lang)
        except Exception:
            status = t("pad_none", lang)
        tk.Label(self.body, text=f"\U0001F3AE {t('settings_gamepad', lang)}",
                 font=("Segoe UI", 22, "bold"), fg=Config.ACCENT,
                 bg=Config.BG_PRIMARY).pack(pady=(18, 2))
        tk.Label(self.body, text=status, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(self.body, text=t("pad_hint", lang), font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(pady=(0, 6))

        self.device_bar = tk.Frame(self.body, bg=Config.BG_PRIMARY)
        self.device_bar.pack(fill="x", padx=24, pady=(0, 4))
        self.device_items = []
        self.refresh_device_bar()

        self.capture_lbl = tk.Label(self.body, text="", font=("Segoe UI", 13, "bold"),
                                    fg=Config.ACCENT_GLOW, bg=Config.BG_PRIMARY)
        self.capture_lbl.pack(pady=(0, 4))

        self.test_lbl = tk.Label(self.body, text="", font=("Segoe UI", 12),
                                 fg=Config.ACCENT_GLOW, bg=Config.BG_PRIMARY,
                                 wraplength=500, justify="center")
        self.test_lbl.pack(pady=(0, 4))
        self._tick_test()

        self.rows_frame = tk.Frame(self.body, bg=Config.BG_PRIMARY)
        self.rows_frame.pack(fill="x", padx=24)
        self.focus_items = []
        self.pad_focus = 0
        self.refresh()

        win.bind("<Escape>", lambda e: self.on_escape())
        win.bind("<Up>", lambda e: self.move_focus(-1))
        win.bind("<Down>", lambda e: self.move_focus(1))
        win.bind("<Return>", lambda e: self.activate_focused())
        win.bind("<KP_Enter>", lambda e: self.activate_focused())
        try:
            win.bind("<Motion>", lambda e: app._on_mouse_motion(), add="+")
        except Exception:
            pass
        win.protocol("WM_DELETE_WINDOW", self.close)
        app.pad_window = self

    def refresh_device_bar(self):
        """Barra de selecao: um botao por controle + atualizar."""
        if self.closed:
            return
        try:
            for w in self.device_bar.winfo_children():
                w.destroy()
        except Exception:
            return
        self.device_items = []
        lang = self.app.lang
        try:
            devices = self.app.pad_devices()
        except Exception:
            devices = []
        tk.Label(self.device_bar, text=t("pad_device", lang), font=("Segoe UI", 13, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY).pack(anchor="w")
        if not devices:
            tk.Label(self.device_bar, text=t("pad_none", lang), font=("Segoe UI", 12),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(anchor="w")
        try:
            gp = self.app.gamepad
            active_name = gp.joystick.get_name() if gp and gp.joystick else None
            conn = gp.connection_info() if gp else ""
        except Exception:
            active_name, conn = None, ""
        for pos, d in enumerate(devices):
            tag = PAD_LAYOUT_LABEL.get(d.get("layout", "generic"), "")
            text = d["name"] + (" [%s]" % tag if tag else "")
            if d["name"] == active_name:
                text = "\u2713 " + text + ("  \u2022  " + conn if conn else "")
            b = tk.Button(self.device_bar, text=text, font=("Segoe UI", 12),
                          fg="white" if d["name"] == active_name else Config.TEXT_PRIMARY,
                          bg=Config.ACCENT if d["name"] == active_name else Config.BG_CARD,
                          activebackground=Config.ACCENT, activeforeground="white",
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          command=lambda p=pos: self._pick_device(p))
            b.pack(fill="x", pady=2)
            self.device_items.append(b)
        rb = tk.Button(self.device_bar, text="\u21BB " + t("pad_rescan", lang),
                       font=("Segoe UI", 12), fg=Config.TEXT_SECONDARY,
                       bg=Config.BG_CARD, relief="flat", cursor="hand2",
                       command=lambda: self._rescan_devices())
        rb.pack(anchor="e", pady=(4, 0))
        self.device_items.append(rb)

    def _pick_device(self, pos):
        try:
            self.app.select_pad_device(pos)
        except Exception:
            pass
        self.refresh_device_bar()
        self.refresh()

    def _rescan_devices(self):
        try:
            gp = self.app.gamepad
            if gp is not None:
                gp.refresh_devices()
        except Exception:
            pass
        self.refresh_device_bar()
        self.refresh()

    def _profile_section(self):
        """3 slots de mapeamento: 1 = padrao, 2/3 salvos pelo usuario."""
        lang = self.app.lang
        tk.Label(self.rows_frame, text=t("pad_profile", lang), font=("Segoe UI", 16, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY, anchor="w").pack(
                     fill="x", pady=(14, 2))
        tk.Frame(self.rows_frame, bg=Config.ACCENT, height=2, width=120).pack(anchor="w")
        try:
            active = int(self.app.settings.get("pad_profile_active", 1))
        except Exception:
            active = 1
        for slot in PAD_PROFILE_SLOTS:
            row = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            row.pack(fill="x", pady=2)
            name = self.app.pad_profile_name(slot)
            is_active = (slot == active)
            b = tk.Button(row, text=("\u2713 " if is_active else "") + name,
                          font=("Segoe UI", 13, "bold"),
                          fg="white" if is_active else Config.TEXT_PRIMARY,
                          bg=Config.ACCENT if is_active else Config.BG_CARD,
                          activebackground=Config.ACCENT, activeforeground="white",
                          relief="flat", bd=0, cursor="hand2", anchor="w", padx=18,
                          highlightthickness=1, highlightbackground=Config.BORDER,
                          command=lambda s=slot: self._pick_profile(s))
            b.pack(side="left", fill="x", expand=True)
            self.focus_items.append(("profile", b, slot))
            if slot in (2, 3):
                sv = tk.Button(row, text=t("pad_save", lang), font=("Segoe UI", 12),
                               fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                               activebackground=Config.ACCENT, activeforeground="white",
                               relief="flat", bd=0, cursor="hand2", padx=14,
                               highlightthickness=1, highlightbackground=Config.BORDER,
                               command=lambda s=slot: self._save_profile(s))
                sv.pack(side="left", padx=(8, 0))
                self.focus_items.append(("psave", sv, slot))
                rn = tk.Button(row, text="\u270E", font=("Segoe UI", 12),
                               fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD,
                               activebackground=Config.ACCENT, activeforeground="white",
                               relief="flat", bd=0, cursor="hand2", padx=12,
                               highlightthickness=1, highlightbackground=Config.BORDER,
                               command=lambda s=slot: self._rename_profile(s))
                rn.pack(side="left", padx=(8, 0))
                self.focus_items.append(("prename", rn, slot))

    def _pick_profile(self, slot):
        try:
            self.app.load_pad_profile(slot)
        except Exception:
            pass

    def _save_profile(self, slot):
        try:
            if self.app.save_pad_profile(slot):
                self.flash_saved()
                self.refresh()
        except Exception:
            pass

    def _rename_profile(self, slot):
        try:
            lang = self.app.lang
            current = self.app.pad_profile_name(slot)
            NexusTextDialog(self.app, t("pad_rename_title", lang),
                            t("pad_rename_prompt", lang), current,
                            lambda name: self._finish_rename(slot, name))
        except Exception:
            pass

    def _finish_rename(self, slot, name):
        try:
            if name and name.strip():
                self.app.rename_pad_profile(slot, name)
            if not self.closed:
                self.refresh()
        except Exception:
            pass

    def flash_saved(self):
        if self.closed:
            return
        try:
            self.capture_lbl.configure(text=t("pad_profile_saved", self.app.lang))
            token = self.capture_token + 1
            self.capture_token = token
            self.win.after(2000, lambda: self._clear_flash(token))
        except Exception:
            pass

    def _clear_flash(self, token):
        try:
            if not self.closed and token == self.capture_token:
                if self.app.pad_capture is None:
                    self.capture_lbl.configure(text="")
        except Exception:
            pass

    def _section(self, title_key, section, order, base_map, settings_key, extra=None):
        lang = self.app.lang
        tk.Label(self.rows_frame, text=t(title_key, lang), font=("Segoe UI", 16, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY, anchor="w").pack(
                     fill="x", pady=(14, 2))
        tk.Frame(self.rows_frame, bg=Config.ACCENT, height=2, width=120).pack(anchor="w")
        try:
            merged = dict(base_map)
            merged.update(self.app.settings.get(settings_key, {}))
        except Exception:
            merged = dict(base_map)
        for action in order:
            btn = merged.get(action)
            row = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            row.pack(fill="x", pady=2)
            try:
                gp = self.app.gamepad
                layout = gp.layout if gp else "xbox"
                if btn is None:
                    label = "\u2014"
                else:
                    logical = normalize_pad_value(btn)
                    raw = gp.raw_for_logical(logical) if gp else None
                    if not isinstance(raw, int):
                        raw = btn if isinstance(btn, int) else None
                    label = pad_logical_label(logical, layout, raw)
            except Exception:
                label = "?"
            tk.Label(row, text=label,
                     font=("Segoe UI", 12, "bold"), fg="white", bg=Config.ACCENT,
                     width=5, relief="flat", bd=0).pack(side="left", padx=(0, 10))
            b = tk.Button(row, text=t(f"pad_a_{action}", lang), font=("Segoe UI", 13),
                          fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                          activebackground=Config.BG_CARD_HOVER,
                          activeforeground=Config.TEXT_PRIMARY,
                          relief="flat", bd=0, cursor="hand2", anchor="w",
                          command=lambda s=section, a=action: self.app.start_pad_capture(s, a))
            b.pack(side="left", fill="x", expand=True)
            self.focus_items.append(("action", b, section, action))
        if extra == "sensitivity":
            srow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            srow.pack(fill="x", pady=(8, 0))
            sens_lbl = tk.Label(srow, text=t("pad_sens", lang), font=("Segoe UI", 13),
                                fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            sens_lbl.pack(side="left")
            self.focus_items.append(("sens", sens_lbl))
            self.sens_var = tk.IntVar(value=int(self.app.pad_sensitivity()))
            sc = tk.Scale(srow, from_=4, to=30, orient="horizontal", length=220,
                          showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                          troughcolor=Config.BG_CARD, highlightthickness=0,
                          activebackground=Config.ACCENT, variable=self.sens_var)
            sc.pack(side="right")
            sc.bind("<ButtonRelease-1>", lambda e: self._save_sens())
            scrow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            scrow.pack(fill="x", pady=(4, 0))
            scroll_lbl = tk.Label(scrow, text=t("pad_scroll", lang), font=("Segoe UI", 13),
                                  fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            scroll_lbl.pack(side="left")
            self.focus_items.append(("scroll", scroll_lbl))
            self.scroll_var = tk.IntVar(value=int(self.app.pad_scroll()))
            sc2 = tk.Scale(scrow, from_=2, to=20, orient="horizontal", length=220,
                           showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                           troughcolor=Config.BG_CARD, highlightthickness=0,
                           activebackground=Config.ACCENT, variable=self.scroll_var)
            sc2.pack(side="right")
            sc2.bind("<ButtonRelease-1>", lambda e: self._save_sens())
            dzrow = tk.Frame(self.rows_frame, bg=Config.BG_PRIMARY)
            dzrow.pack(fill="x", pady=(4, 0))
            dead_lbl = tk.Label(dzrow, text=t("pad_deadzone", lang), font=("Segoe UI", 13),
                                fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
            dead_lbl.pack(side="left")
            self.focus_items.append(("dead", dead_lbl))
            try:
                dz_val = int(self.settings.get("pad_deadzone", DEFAULT_PAD_DEADZONE))
            except Exception:
                dz_val = DEFAULT_PAD_DEADZONE
            self.dead_var = tk.IntVar(value=min(40, max(5, dz_val)))
            sc3 = tk.Scale(dzrow, from_=5, to=40, orient="horizontal", length=220,
                           showvalue=True, bg=Config.BG_PRIMARY, fg=Config.TEXT_PRIMARY,
                           troughcolor=Config.BG_CARD, highlightthickness=0,
                           activebackground=Config.ACCENT, variable=self.dead_var)
            sc3.pack(side="right")
            sc3.bind("<ButtonRelease-1>", lambda e: self._save_sens())
        reset_btn = tk.Button(self.rows_frame, text=t("pad_reset", lang), font=("Segoe UI", 12),
                              fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, relief="flat",
                              cursor="hand2", padx=16, pady=4,
                              command=lambda: self._reset(settings_key))
        reset_btn.pack(anchor="e", pady=(6, 0))
        self.focus_items.append(("reset", reset_btn, settings_key))

    def _save_sens(self):
        try:
            self.app.settings["pad_sensitivity"] = int(self.sens_var.get())
            self.app.settings["pad_scroll"] = int(self.scroll_var.get())
            self.app.settings["pad_deadzone"] = int(self.dead_var.get())
            save_settings(self.app.settings)
            self.app.store_current_device()
        except Exception:
            pass

    def _reset(self, settings_key):
        try:
            self.app.settings[settings_key] = {}
            save_settings(self.app.settings)
            self.app.store_current_device()
        except Exception:
            pass
        self.refresh()

    def refresh(self):
        if self.closed:
            return
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.focus_items = []
        self._profile_section()
        self._section("pad_nexus_sec", "nexus", NEXUS_ACTION_ORDER,
                      DEFAULT_NEXUS_MAP, "pad_nexus")
        tk.Label(self.rows_frame, text=t("pad_fixed_dpad", self.app.lang),
                 font=("Segoe UI", 11), fg=Config.TEXT_SECONDARY,
                 bg=Config.BG_PRIMARY, anchor="w").pack(fill="x", pady=(4, 0))
        self._section("pad_remote_sec", "remote", REMOTE_ACTION_ORDER,
                      DEFAULT_REMOTE_MAP, "pad_remote", extra="sensitivity")
        tk.Label(self.rows_frame, text=t("pad_fixed_remote", self.app.lang),
                 font=("Segoe UI", 11), fg=Config.TEXT_SECONDARY,
                 bg=Config.BG_PRIMARY, anchor="w", justify="left",
                 wraplength=500).pack(fill="x", pady=(4, 10))
        # Scroll com o mouse em QUALQUER ponto da janela (refresh recria linhas)
        self.app._bind_wheel_tree(self.win, self._on_wheel)
        if self.pad_focus >= len(self.focus_items):
            self.pad_focus = 0
        self._paint_focus()
        self.on_capture_end()

    def move_focus(self, d):
        if self.closed or not self.focus_items:
            return
        self.pad_focus = (self.pad_focus + d) % len(self.focus_items)
        self._paint_focus()
        self._ensure_focus_visible()

    def _ensure_focus_visible(self):
        if self.closed or not self.focus_items:
            return
        try:
            widget = self.focus_items[self.pad_focus][1]
            self.scroll_canvas.update_idletasks()
            widget.update_idletasks()
            ch = self.scroll_canvas.winfo_height()
            total = self.body.winfo_height()
            if total <= 0 or ch <= 0 or total <= ch:
                return
            wy = widget.winfo_rooty() - self.scroll_canvas.winfo_rooty()
            wh = widget.winfo_height()
            first, _ = self.scroll_canvas.yview()
            if wy < 0:
                self.scroll_canvas.yview_moveto(max(0.0, first + wy / total))
            elif wy + wh > ch:
                self.scroll_canvas.yview_moveto(min(1.0, first + (wy + wh - ch) / total))
        except Exception:
            pass

    def sens_or_move(self, hat):
        """Esquerda/direita nos ajustes altera; senao navega."""
        if self.closed or not self.focus_items:
            return
        item = self.focus_items[self.pad_focus]
        if item[0] in ("sens", "scroll", "dead"):
            self.adjust_sens(-1 if hat == (-1, 0) else 1)
        else:
            self.move_focus(-1 if hat == (-1, 0) else 1)

    def _paint_focus(self):
        for i, item in enumerate(self.focus_items):
            kind, widget = item[0], item[1]
            focused = (i == self.pad_focus)
            try:
                if kind in ("sens", "scroll", "dead"):
                    widget.configure(fg=Config.ACCENT_GLOW if focused else Config.TEXT_PRIMARY)
                elif kind in ("profile", "psave", "prename"):
                    widget.configure(highlightthickness=2 if focused else 1,
                                     highlightbackground=Config.ACCENT_GLOW if focused
                                     else Config.BORDER)
                elif focused:
                    widget.configure(bg=Config.ACCENT, fg="white")
                elif kind == "reset":
                    widget.configure(bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY)
                else:
                    widget.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY)
            except Exception:
                pass

    def activate_focused(self):
        if self.closed or not self.focus_items:
            return
        item = self.focus_items[self.pad_focus]
        try:
            if item[0] == "action":
                self.app.start_pad_capture(item[2], item[3])
            elif item[0] == "reset":
                self._reset(item[2])
            elif item[0] == "profile":
                self._pick_profile(item[2])
            elif item[0] == "psave":
                self._save_profile(item[2])
            elif item[0] == "prename":
                self._rename_profile(item[2])
        except Exception:
            pass

    def adjust_sens(self, d):
        if self.closed or not self.focus_items:
            return
        try:
            kind = self.focus_items[self.pad_focus][0]
            if kind == "scroll":
                v = min(20, max(2, int(self.scroll_var.get()) + d))
                self.scroll_var.set(v)
            elif kind == "dead":
                v = min(40, max(5, int(self.dead_var.get()) + d))
                self.dead_var.set(v)
            else:
                v = min(30, max(4, int(self.sens_var.get()) + d))
                self.sens_var.set(v)
            self._save_sens()
        except Exception:
            pass

    def close_via_pad(self):
        if self.closed:
            return
        try:
            if self.app.pad_capture is not None:
                self.app.cancel_pad_capture()
            else:
                self.close()
        except Exception:
            pass

    def on_escape(self):
        self.close_via_pad()

    def _on_wheel(self, event):
        try:
            if event.delta > 0 and self.app._at_top(self.scroll_canvas):
                return "break"
            if event.delta < 0 and self.app._at_bottom(self.scroll_canvas):
                return "break"
            self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def _tick_test(self):
        """Leitura ao vivo dos botoes: prova se o controle chega ao app."""
        if self.closed:
            return
        try:
            gp = self.app.gamepad
            if gp is not None and gp.joystick is not None:
                pressed = sorted(gp.pressed_logical())
                if pressed:
                    names = [pad_logical_label(
                        l, gp.layout,
                        gp.raw_for_logical(l)) for l in pressed]
                    txt = "\u25CF " + " + ".join(names)
                else:
                    txt = t("pad_test_idle", self.app.lang)
            else:
                txt = t("pad_none", self.app.lang)
            self.test_lbl.configure(text=txt)
        except Exception:
            pass
        try:
            self.win.after(300, self._tick_test)
        except Exception:
            pass

    def on_capture_start(self):
        if self.closed:
            return
        self.capture_token += 1
        token = self.capture_token
        self.capture_lbl.configure(text=t("pad_press", self.app.lang))
        try:
            self.win.after(12000, lambda: self._capture_timeout(token))
        except Exception:
            pass

    def _capture_timeout(self, token):
        if not self.closed and token == self.capture_token:
            self.app.cancel_pad_capture()

    def on_capture_end(self):
        if self.closed:
            return
        try:
            self.capture_lbl.configure(text="")
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.app.cancel_pad_capture()
        except Exception:
            pass
        try:
            if self.app.pad_window is self:
                self.app.pad_window = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


# ===================== SOUND SETTINGS WINDOW =====================
# ===================== SIDE PANEL =====================
class SidePanel:
    """Drawer direito generico das Configuracoes (Controles, Idioma,
    Adicionar, Sistema). Mouse e controle: cima/baixo focam, esq/dir
    ajustam sliders, A confirma, B fecha."""
    NAME = "base"
    TITLE_KEY = ""
    ICON = "\u25C6"
    WIDTH = 360
    IS_FORM = False

    def __init__(self, app):
        self.app = app
        self.visible = False
        self.focus = 0
        self.frame = None
        self.body = None
        self.focusables = []

    # ---------- ciclo ----------
    def open(self):
        app = self.app
        try:
            old = getattr(app, "sidepanel", None)
            if old is not None and old is not self:
                old.close()
        except Exception:
            pass
        for closer in ("close_sidebar", "close_theme_panel", "close_notif_panel"):
            try:
                if closer == "close_sidebar":
                    app.close_sidebar()
                elif closer == "close_theme_panel":
                    if getattr(app, "theme_visible", False):
                        app.close_theme_panel()
                elif closer == "close_notif_panel":
                    if getattr(app, "notif_visible", False):
                        app.close_notif_panel()
            except Exception:
                pass
        app.sidepanel = self
        self.visible = True
        self.focus = 0
        self.build()
        self.render()
        self.place()
        self.paint()
        try:
            self.after_open()
        except Exception:
            pass

    def close(self):
        app = self.app
        self.visible = False
        try:
            if self.frame is not None:
                self.frame.place_forget()
        except Exception:
            pass
        try:
            if getattr(app, "sidepanel", None) is self:
                app.sidepanel = None
        except Exception:
            pass
        if self.IS_FORM:
            try:
                app.nav_level = "items"
                app.form_focus = []
                app.form_idx = 0
                app.update_all_focus()
            except Exception:
                pass

    def reopen(self):
        if not self.visible:
            return
        self.focus = 0
        self.build()
        self.render()
        self.place()
        self.paint()
        try:
            self.after_open()
        except Exception:
            pass

    def after_open(self):
        pass

    # ---------- estrutura ----------
    def build(self):
        app = self.app
        try:
            if self.frame is not None:
                self.frame.destroy()
        except Exception:
            pass
        self.focusables = []
        self.frame = tk.Frame(app.main_frame, bg=Config.BG_SIDEBAR,
                              width=self.WIDTH)
        self.frame.pack_propagate(False)
        head = tk.Frame(self.frame, bg=Config.BG_SIDEBAR)
        head.pack(fill="x", pady=(20, 4))
        tk.Label(head, text="%s %s" % (self.ICON, t(self.TITLE_KEY, app.lang)),
                 font=("Segoe UI", 18, "bold"), fg=Config.TEXT_PRIMARY,
                 bg=Config.BG_SIDEBAR).pack(side="left", padx=16)
        tk.Button(head, text="\u2715", font=("Segoe UI", 12),
                  bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                  activebackground="#e94560", activeforeground="white",
                  relief="flat", cursor="hand2", bd=0, padx=10,
                  command=self.close).pack(side="right", padx=12)
        tk.Frame(self.frame, bg=Config.BORDER, height=1).pack(
            fill="x", padx=16, pady=(4, 6))
        self.body = tk.Frame(self.frame, bg=Config.BG_SIDEBAR)
        self.body.pack(fill="both", expand=True)

    def place(self):
        try:
            self.frame.place(relx=1.0, y=0, relheight=1, anchor="ne",
                             width=self.WIDTH)
            self.frame.lift()
        except Exception:
            pass

    def section(self, text):
        tk.Label(self.body, text=text.upper(), font=("Segoe UI", 11, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x", padx=16, pady=(12, 2))

    def button(self, text, cmd):
        b = tk.Button(self.body, text=text, font=("Segoe UI", 13),
                      fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD,
                      activebackground=Config.BG_CARD_HOVER,
                      activeforeground=Config.TEXT_PRIMARY,
                      relief="flat", bd=0, cursor="hand2", anchor="w",
                      padx=18, pady=8, highlightthickness=1,
                      highlightbackground=Config.BORDER,
                      command=cmd)
        b.pack(fill="x", padx=16, pady=3)
        self.focusables.append({"kind": "button", "widget": b, "cmd": cmd})
        idx = len(self.focusables) - 1
        b.bind("<Enter>", lambda e, i=idx: self.set_focus(i))
        return b

    def slider(self, label, vmin, vmax, get, put, step=1):
        """put(v) salva. Controle esq/dir ajusta (com tick); mouse arrasta."""
        row = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
        row.pack(fill="x", padx=16, pady=(6, 0))
        lab = tk.Label(row, text=label, font=("Segoe UI", 13),
                       fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR,
                       wraplength=self.WIDTH - 110, justify="left")
        lab.pack(side="left")
        val = tk.Label(row, font=("Segoe UI", 13, "bold"),
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
        self.focusables.append(item)
        idx = len(self.focusables) - 1

        def _drag(v, _it=item):
            if _it["prog"]:
                return
            try:
                _it["put"](int(float(v)))
            except Exception:
                pass
            self.refresh_slider(_it, tick=False)

        sc.configure(command=_drag)
        # e=None defensivo: o Tk pode disparar o bind sem evento em
        # cantos de corrida (o e nunca e usado; so _it importa).
        sc.bind("<ButtonRelease-1>",
                lambda e=None, _it=item: self.refresh_slider(_it, tick=True))
        sc.bind("<Enter>", lambda e=None, i=idx: self.set_focus(i))
        for w in (row, lab, val):
            try:
                w.bind("<Enter>", lambda e=None, i=idx: self.set_focus(i))
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
        if tick:
            try:
                self.app.play_tick()
            except Exception:
                pass

    def adjust(self, d):
        if not self.focusables:
            return
        item = self.focusables[self.focus % len(self.focusables)]
        if item.get("kind") != "slider":
            return
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

    # ---------- navegacao ----------
    def set_focus(self, idx):
        if not self.visible or not self.focusables:
            return
        new = idx % len(self.focusables)
        if new != self.focus:
            self.focus = new
            self.paint()
            try:
                self.app.play_tick()
            except Exception:
                pass

    def paint(self):
        for i, item in enumerate(self.focusables):
            try:
                if item.get("kind") == "slider":
                    item["label"].configure(
                        fg=Config.ACCENT if i == self.focus else Config.TEXT_PRIMARY)
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

    def on_hat(self, hat):
        if not self.visible or not self.focusables:
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
        if not self.visible:
            return
        if logical == "east":
            self.close()
            return
        if logical != "south" or not self.focusables:
            return
        item = self.focusables[self.focus % len(self.focusables)]
        if item.get("kind") == "button":
            try:
                item["cmd"]()
            except Exception:
                pass


class ControlesPanel(SidePanel):
    NAME = "controles"
    TITLE_KEY = "settings_controls"
    ICON = "\U0001F3AE"

    def render(self):
        app = self.app
        lang = app.lang
        self.section(t("ctrl_devices", lang))
        try:
            devices = app.pad_devices()
        except Exception:
            devices = []
        try:
            gp = app.gamepad
            active_name = gp.joystick.get_name() if (gp is not None and gp.joystick) else None
            conn = gp.connection_info() if gp else ""
        except Exception:
            active_name, conn = None, ""
        if not devices:
            tk.Label(self.body, text=t("pad_none", lang),
                     font=("Segoe UI", 12), fg=Config.TEXT_SECONDARY,
                     bg=Config.BG_SIDEBAR, anchor="w").pack(fill="x", padx=16)
        for pos, d in enumerate(devices):
            tag = PAD_LAYOUT_LABEL.get(d.get("layout", "generic"), "")
            text = d["name"] + (" [%s]" % tag if tag else "")
            if d["name"] == active_name:
                text = "\u2713 " + text + ("  \u2022  " + conn if conn else "")
            self.button(text, lambda p=pos: self._pick(p))
        try:
            mapped = bool(getattr(gp, "sdl_mapped", True))
        except Exception:
            mapped = True
        tk.Label(self.body,
                 text=t("ctrl_sdl_ok", lang) if mapped else t("ctrl_sdl_fix", lang),
                 font=("Segoe UI", 11),
                 fg=Config.TEXT_SECONDARY if mapped else "#e94560",
                 bg=Config.BG_SIDEBAR, anchor="w", justify="left",
                 wraplength=self.WIDTH - 40).pack(fill="x", padx=16, pady=(2, 0))
        self.button("\u21BB " + t("pad_rescan", lang),
                    lambda: self._rescan())
        self.section("\U0001F3AE " + t("ctrl_pad_sec", lang))
        self.button(t("pad_remap", lang),
                    lambda: app.show_gamepad_info())
        self.slider(t("pad_sens", lang), 4, 30,
                    lambda: int(app.pad_sensitivity()),
                    lambda v: self._save_pad("pad_sensitivity", v))
        self.slider(t("pad_scroll", lang), 2, 20,
                    lambda: int(app.pad_scroll()),
                    lambda v: self._save_pad("pad_scroll", v))
        self.slider(t("pad_deadzone", lang), 5, 40,
                    lambda: self._get_dead(),
                    lambda v: self._save_pad("pad_deadzone", v))
        self.section("\u2328 " + t("ctrl_kb_sec", lang))
        self.button(t("kb_open", lang),
                    lambda: app.open_keyboard())

    def _get_dead(self):
        try:
            return min(40, max(5, int(self.app.settings.get("pad_deadzone", 22))))
        except Exception:
            return 22

    def _pick(self, pos):
        try:
            self.app.select_pad_device(pos)
        except Exception:
            pass
        try:
            self.open()
        except Exception:
            pass

    def _rescan(self):
        try:
            gp = self.app.gamepad
            if gp is not None:
                gp.refresh_devices()
        except Exception:
            pass
        try:
            self.open()
        except Exception:
            pass

    def _save_pad(self, key, val):
        try:
            if isinstance(self.app.settings, dict):
                self.app.settings[key] = int(val)
                save_settings(self.app.settings)
                self.app.store_current_device()
        except Exception:
            pass


class IdiomaPanel(SidePanel):
    NAME = "idioma"
    TITLE_KEY = "settings_language"
    ICON = "\U0001F310"

    def render(self):
        app = self.app
        # Sigla de IDIOMA em texto (BR/EN): emoji de bandeira vira "BR"/"GB"
        # em maquina sem fonte emoji, e GB e pais, nao idioma.
        for code, label in (("pt-br", "BR  Portugues (BR)"),
                            ("en", "EN  English")):
            mark = "\u2713 " if code == app.lang else ""
            self.button(mark + label, lambda c=code: app.set_language(c))


class SistemaPanel(SidePanel):
    NAME = "sistema"
    TITLE_KEY = "settings_system"
    ICON = "\u2699"

    def render(self):
        app = self.app
        lang = app.lang
        self.button("\U0001F5A9  " + t("settings_resolution", lang),
                    lambda: app.open_resolution())
        self.button("\U0001F9F9  " + t("settings_clear_cache", lang),
                    lambda: app.confirm_clear_browser_profile())
        self.button("\u267B  " + t("games_restore_ignored", lang),
                    lambda: app.restore_ignored_platform())
        self.button("\u2193  " + t("update_check", lang),
                    lambda: app.check_updates_manual())


class PerfilPanel(SidePanel):
    NAME = "perfil"
    TITLE_KEY = "settings_profile"
    ICON = "\U0001F464"

    def render(self):
        app = self.app
        lang = app.lang
        try:
            from . import profiles as _prof
        except Exception:
            return
        cur = getattr(app, "profile", None)
        if cur:
            who = "\u2713 " + cur
        else:
            who = t("profile_guest", lang)
        tk.Label(self.body, text=who, font=("Segoe UI", 13, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR,
                 anchor="w").pack(fill="x", padx=16, pady=(4, 6))
        try:
            names = _prof.list_profiles()
        except Exception:
            names = []
        for name in names:
            try:
                lock = " \U0001F512" if _prof.profile_has_pin(name) else ""
            except Exception:
                lock = ""
            mark = "\u2713 " if name == cur else ""
            self.button(mark + "\U0001F464  " + name + lock,
                        lambda n=name: self._login_flow(n))
        self.button("+ " + t("profile_new", lang), self._new_flow)
        if cur:
            self.button(t("profile_logout", lang), self._logout)
        self.section(t("profile_phone", lang))
        self._render_phone()

    def _refresh(self):
        try:
            self.open()
        except Exception:
            pass

    def _login_flow(self, name):
        app = self.app
        try:
            from . import profiles as _prof
            from .dialogs import NexusTextDialog
        except Exception:
            return

        def _do(pin=None):
            try:
                if not _prof.verify_pin(name, pin or ""):
                    app.show_info_message(t("profile_login", app.lang),
                                          t("profile_bad_pin", app.lang))
                    return
                _prof.switch_profile(app, name)
                self._refresh()
            except Exception:
                pass

        try:
            if _prof.profile_has_pin(name):
                NexusTextDialog(app, t("profile_login", app.lang),
                                t("profile_pin", app.lang), "",
                                lambda v: _do(v), password=True)
            else:
                _do("")
        except Exception:
            pass

    def _new_flow(self):
        app = self.app
        try:
            from . import profiles as _prof
            from .dialogs import NexusTextDialog
        except Exception:
            return

        def _got_name(name):
            name = (name or "").strip()
            if not name:
                return

            def _got_pin(pin):
                try:
                    ok, err = _prof.create_profile(
                        name, pin, _prof.snapshot_settings(app))
                    if not ok:
                        app.show_info_message(
                            t("profile_new", app.lang), err)
                        return
                    _prof.switch_profile(app, name)
                    self._refresh()
                except Exception:
                    pass

            try:
                NexusTextDialog(app, t("profile_new", app.lang),
                                t("profile_pin", app.lang), "",
                                lambda v: _got_pin(v), password=True)
            except Exception:
                pass

        try:
            NexusTextDialog(app, t("profile_new", app.lang),
                            t("profile_name", app.lang), "",
                            lambda v: _got_name(v))
        except Exception:
            pass

    def _logout(self):
        try:
            from . import profiles as _prof
            _prof.switch_profile(self.app, None)
            self._refresh()
        except Exception:
            pass

    def _render_phone(self):
        app = self.app
        lang = app.lang
        try:
            from . import phone_server as _ps
        except Exception:
            return
        try:
            srv = getattr(app, "phone_server", None)
            on = bool(srv is not None and srv.running)
        except Exception:
            on = False
        info = t("phone_on", lang) if on else t("phone_off", lang)
        if on:
            try:
                info += "  %s:%s" % (_ps.chosen_ip(app),
                                     _ps.app_phone_port(app))
            except Exception:
                pass
        tk.Label(self.body, text=info, font=("Segoe UI", 12),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                 anchor="w", justify="left",
                 wraplength=self.WIDTH - 40).pack(fill="x", padx=16, pady=2)
        if on:
            try:
                ips = _ps.lan_ips()
            except Exception:
                ips = []
            try:
                cur_ip = _ps.chosen_ip(app)
            except Exception:
                cur_ip = ""
            if len(ips) > 1:
                tk.Label(self.body, text=t("phone_ip", lang),
                         font=("Segoe UI", 11, "bold"), fg=Config.ACCENT,
                         bg=Config.BG_SIDEBAR, anchor="w").pack(
                             fill="x", padx=16, pady=(8, 0))
                for ip in ips:
                    try:
                        mark = "\u2713 " if ip == cur_ip else ""
                        self.button(mark + ip,
                                    lambda _ip=ip: self._pick_ip(_ip))
                    except Exception:
                        pass
            self.button(t("phone_stop", lang), lambda: self._srv_stop())
            self.button(t("phone_newcode", lang), lambda: self._srv_code())
            self._render_qr()
            try:
                devs = srv.paired_devices()
            except Exception:
                devs = []
            if devs:
                tk.Label(self.body, text=t("phone_paired", lang),
                         font=("Segoe UI", 11, "bold"), fg=Config.ACCENT,
                         bg=Config.BG_SIDEBAR, anchor="w").pack(
                             fill="x", padx=16, pady=(8, 0))
                for d in devs:
                    try:
                        label = "%s (%s)" % (d.get("device", "?"),
                                             d.get("profile", "?") or "?")
                        self.button(label + "  \u2715",
                                    lambda tk_=d.get("token", ""):
                                    self._srv_revoke(tk_))
                    except Exception:
                        pass
        else:
            self.button(t("phone_start", lang), lambda: self._srv_start())

    def _srv_start(self):
        try:
            if not getattr(self.app, "profile", None):
                try:
                    self.app.show_info_message(
                        t("profile_phone", self.app.lang),
                        t("phone_login_first", self.app.lang))
                except Exception:
                    pass
                return
            from . import phone_server as _ps
            ok, err = _ps.start_phone_server(self.app)
            if not ok:
                try:
                    self.app.show_info_message(
                        t("profile_phone", self.app.lang), err or "?")
                except Exception:
                    pass
            self._refresh()
        except Exception:
            pass

    def _srv_stop(self):
        try:
            from . import phone_server as _ps
            _ps.stop_phone_server(self.app)
            self._refresh()
        except Exception:
            pass

    def _pick_ip(self, ip):
        try:
            if isinstance(self.app.settings, dict):
                self.app.settings["phone_ip"] = ip
                from .config import save_settings as _save
                _save(self.app.settings)
        except Exception:
            pass
        try:
            self._refresh()
        except Exception:
            pass

    def _srv_code(self):
        try:
            srv = getattr(self.app, "phone_server", None)
            if srv is not None:
                srv.new_code()
            self._refresh()
        except Exception:
            pass

    def _srv_revoke(self, tok):
        try:
            srv = getattr(self.app, "phone_server", None)
            if srv is not None:
                srv.revoke_token(tok)
            self._refresh()
        except Exception:
            pass

    def _render_qr(self):
        try:
            from . import phone_server as _ps
            srv = getattr(self.app, "phone_server", None)
            if srv is None:
                return
            code = getattr(srv, "shown_code", "") or ""
            if not code:
                code = srv.new_code()
            payload = _ps.qr_payload(self.app, code)
            import json as _json
            photo = _ps.make_qr_photo(_json.dumps(payload, sort_keys=True),
                                      box=5)
            lang = self.app.lang
            tk.Label(self.body, text="%s: %s" % (t("phone_code", lang), code),
                     font=("Segoe UI", 14, "bold"), fg=Config.TEXT_PRIMARY,
                     bg=Config.BG_SIDEBAR, anchor="w").pack(
                         fill="x", padx=16, pady=(6, 2))
            if photo is not None:
                self.qr_photo = photo
                tk.Label(self.body, image=photo, bg=Config.BG_SIDEBAR).pack(
                    padx=16, pady=2)
        except Exception:
            pass


class AdicionarPanel(SidePanel):
    NAME = "adicionar"
    TITLE_KEY = "sidebar_add"
    ICON = "\U0001F4FA"
    IS_FORM = True

    def render(self):
        app = self.app
        lang = app.lang
        fields = [(t("add_name", lang), "Meu Streaming"),
                  (t("add_url", lang), "https://"),
                  (t("add_category", lang), "Filmes"),
                  (t("add_emoji", lang), "\U0001F4F0"),
                  (t("add_logo", lang), "")]
        app.add_entries = {}
        app.form_focus = []
        app.form_idx = 0
        for label, default in fields:
            tk.Label(self.body, text=label, font=("Segoe UI", 12),
                     fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR,
                     anchor="w").pack(fill="x", padx=16, pady=(8, 0))
            if label == t("add_logo", lang):
                rowf = tk.Frame(self.body, bg=Config.BG_SIDEBAR)
                rowf.pack(fill="x", padx=16)
                e = tk.Entry(rowf, font=("Segoe UI", 12),
                             bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                             insertbackground=Config.ACCENT, bd=0,
                             highlightbackground=Config.BORDER,
                             highlightthickness=1)
                e.pack(side="left", fill="x", expand=True)
                bb = tk.Button(rowf, text="...", font=("Segoe UI", 12),
                               bg=Config.ACCENT, fg="white",
                               relief="flat", cursor="hand2", padx=10,
                               command=lambda ent=e: app.browse_image(ent))
                bb.pack(side="left", padx=(8, 0))
                app.add_entries[label] = e
                app.bind_keyboard_popup(e, mode="text")
                app._reg_form(e, "entry")
                app._reg_form(bb, "button",
                              lambda ent=e: app.browse_image(ent))
            else:
                e = tk.Entry(self.body, font=("Segoe UI", 12),
                             bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                             insertbackground=Config.ACCENT, bd=0,
                             highlightbackground=Config.BORDER,
                             highlightthickness=1)
                e.pack(fill="x", padx=16, pady=(0, 2))
                e.insert(0, default)
                app.add_entries[label] = e
                app.bind_keyboard_popup(e)
                app._reg_form(e, "entry")
        submit = tk.Button(self.body,
                           text="%s \u2192" % t("add_submit", lang),
                           font=("Segoe UI", 14, "bold"),
                           bg=Config.ACCENT, fg="white",
                           activebackground=Config.ACCENT_GLOW,
                           relief="flat", cursor="hand2", pady=8,
                           command=app.add_new_streaming)
        submit.pack(fill="x", padx=16, pady=(14, 4))
        app._reg_form(submit, "button", app.add_new_streaming)
        back = tk.Button(self.body,
                         text="\u2190 %s" % t("add_back", lang),
                         font=("Segoe UI", 12),
                         bg=Config.BG_CARD, fg=Config.TEXT_SECONDARY,
                         relief="flat", cursor="hand2", pady=6,
                         command=self._back)
        back.pack(fill="x", padx=16, pady=(0, 10))
        app._reg_form(back, "button", self._back)

    def _back(self):
        self.close()
        try:
            self.app.switch_tab(self.app.current_tab)
        except Exception:
            pass

    def after_open(self):
        try:
            self.app.nav_level = "form"
            self.app.form_idx = 0
            self.app._paint_form()
        except Exception:
            pass


class SomPanel(SidePanel):
    NAME = "som"
    TITLE_KEY = "settings_sound"
    ICON = "\U0001F50A"

    def render(self):
        app = self.app
        lang = app.lang
        self._outputs_box()
        self.vol_item = self.slider(t("snd_volume", lang), 0, 100,
                                    lambda: self._get_vol(),
                                    lambda v: self._set_volume(v, tick=False),
                                    step=5)
        self.defvol_item = self.slider(t("snd_defvol", lang), 0, 100,
                                       lambda: self._get_defvol(),
                                       lambda v: self._set_defvol(v),
                                       step=5)
        self.nav_btn = self.button("", self._toggle_nav)
        self._paint_nav()
        self.button("\U0001F50A " + t("snd_test", lang), self._test)
        self.status_lbl = tk.Label(self.body, text="", font=("Segoe UI", 10),
                                   fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR,
                                   wraplength=self.WIDTH - 40, justify="center")
        self.status_lbl.pack(fill="x", padx=16, pady=(6, 2))

    def _outputs_box(self):
        # Caixa com a saida atual; clica e abre a lista.
        try:
            from .audio import audio_outputs
            outs = audio_outputs()
        except Exception:
            outs = []
        cur = ""
        try:
            for o in outs:
                if o.get("default"):
                    cur = o.get("name") or o.get("id", "")
                    break
            if not cur and outs:
                cur = outs[0].get("name") or outs[0].get("id", "")
        except Exception:
            pass
        arrow = "▴" if getattr(self, "outputs_open", False) else "▾"
        self.button("\U0001F50A %s %s" % (cur or "—", arrow),
                    self._toggle_outputs)
        if getattr(self, "outputs_open", False):
            for o in outs:
                try:
                    mark = "\u2713 " if o.get("default") else ""
                    self.button(mark + (o.get("name") or o.get("id", "?")),
                                lambda _id=o.get("id", ""): self._pick_output(_id))
                except Exception:
                    pass

    def _toggle_outputs(self):
        self.outputs_open = not getattr(self, "outputs_open", False)
        self._rebuild()

    def _pick_output(self, device_id):
        try:
            from .audio import audio_set_output
            audio_set_output(device_id)
        except Exception:
            pass
        self.outputs_open = False
        self._rebuild()

    def _rebuild(self):
        try:
            for w in self.body.winfo_children():
                w.destroy()
        except Exception:
            return
        self.focusables = []
        self.focus = 0
        try:
            self.render()
            self.paint()
        except Exception:
            pass

    def _get_vol(self):
        try:
            return max(0, min(100, int(self.app.settings.get("sound_volume", 10))))
        except Exception:
            return 10

    def _get_defvol(self):
        try:
            return max(0, min(100, int(self.app.settings.get("sound_default", 70))))
        except Exception:
            return 70

    def _set_defvol(self, vol):
        try:
            vol = max(0, min(100, int(vol)))
        except Exception:
            return
        try:
            if isinstance(self.app.settings, dict):
                self.app.settings["sound_default"] = vol
                save_settings(self.app.settings)
        except Exception:
            pass
        try:
            self.refresh_slider(self.defvol_item, tick=False)
        except Exception:
            pass
        try:
            if getattr(getattr(self.app, "gamepad", None),
                       "remote_active", False):
                self.app._apply_default_volume()
        except Exception:
            pass
        try:
            self.app.play_tick()
        except Exception:
            pass

    def _set_volume(self, vol, tick=True):
        try:
            vol = max(0, min(100, int(vol)))
        except Exception:
            return
        try:
            if isinstance(self.app.settings, dict):
                self.app.settings["sound_volume"] = vol
                save_settings(self.app.settings)
        except Exception:
            pass
        try:
            self.refresh_slider(self.vol_item, tick=False)
        except Exception:
            pass
        if tick:
            try:
                self.app.play_tick()
            except Exception:
                pass

    def _toggle_nav(self):
        try:
            cur = True
            if isinstance(self.app.settings, dict):
                cur = bool(self.app.settings.get("nav_sound", True))
                self.app.settings["nav_sound"] = (not cur)
                save_settings(self.app.settings)
            self._paint_nav()
            if not cur:
                self.app.play_tick()
        except Exception:
            pass

    def _paint_nav(self):
        try:
            on = True
            if isinstance(self.app.settings, dict):
                on = bool(self.app.settings.get("nav_sound", True))
            mark = "\u2713 " if on else ""
            state = t("snd_on", self.app.lang) if on else t("snd_off", self.app.lang)
            self.nav_btn.configure(text="%s%s: %s" % (
                mark, t("snd_nav", self.app.lang), state))
        except Exception:
            pass

    def _test(self):
        try:
            ok, err = self.app.play_tick()
            msg = ("Blip ok (vol %d)" % self._get_vol()) if ok else ("Blip: %s" % (err or "falhou"))
        except Exception as e:
            msg = "Erro: %s" % str(e)[:100]
        try:
            ok2, err2 = _play_test_tone()
            msg += " + tom de teste" if ok2 else (" | tom: %s" % (err2 or "falhou"))
        except Exception as e:
            msg += " | tom: %s" % str(e)[:80]
        try:
            self.status_lbl.config(text=msg)
        except Exception:
            pass
