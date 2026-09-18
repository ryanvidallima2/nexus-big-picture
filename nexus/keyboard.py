# -*- coding: utf-8 -*-
"""Teclado virtual do Nexus (extraido sem alteracao)."""

import ctypes
import time
import tkinter as tk

from .config import Config
from .i18n import t
from .input import VK_BACK, VK_RETURN, tap_key, type_text
from .win32 import (
    _apply_dark_title, bring_to_front, force_topmost_noactivate,
    foreground_hwnd,
)


# ===================== NEXUS VIRTUAL KEYBOARD =====================
class NexusKeyboard:
    """Teclado virtual p/ controle: analogico/setas movem o cursor,
    confirmar tecla. Tecla de verdade onde o foco estiver (Nexus e browser).
    Sem grab: o foco pode ficar no campo de login do site."""

    # Geometria baseline 691px (ref. visual estilo Gboard): tudo escala
    # por scale = largura_janela / 691. Tecla ~61x51 (aspecto ~1,2:1),
    # gap horizontal ~7, vertical ~13, lateral ~7-8. Sem border-radius
    # (botao nativo do tkinter e retangular).
    KB_BASE_W = 691.0
    KB_KEY_W = 61.0
    KB_KEY_H = 51.0
    KB_GAP_X = 7.0
    KB_GAP_Y = 13.0
    KB_SIDE = 8.0
    KB_HOME_INDENT = 31.0
    KB_SHIFT_FLEX = (1.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.5)
    KB_ACTION_FLEX = (1.8, 0.5, 5.8, 0.8, 1.4)

    # Cada fileira: (teclas, flex|None, estilo)
    # estilo None = ocupa tudo; "home" = indentada p/ direita sem esticar;
    # "fixed" = teclas tamanho baseline centralizadas.
    ROWS_ALPHA = [
        (["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], None, None),
        (["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"], None, None),
        (["A", "S", "D", "F", "G", "H", "J", "K", "L"], None, "home"),
        (["\u21E7", "Z", "X", "C", "V", "B", "N", "M", "\u232B"],
         list(KB_SHIFT_FLEX), None),
    ]

    ROWS_NUM = [
        (["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], None, None),
        (["!", "@", "#", "$", "%", "\u00A8", "&", "*", "(", ")"], None, None),
        (["-", "_", "+", "=", "/", "?", ":", ";", '"', "'"], None, None),
        (["<", ">", "[", "]", "{", "}", "|", ",", ".", "\u232B"], None, None),
    ]

    ROWS_EMOJI = [
        (["\U0001F600", "\U0001F601", "\U0001F602", "\U0001F923", "\U0001F60A",
          "\U0001F60D", "\U0001F60E", "\U0001F914", "\U0001F605", "\U0001F62D"],
         None, None),
        (["\U0001F44D", "\U0001F44E", "\U0001F44F", "\U0001F64F", "\u2764",
          "\U0001F525", "\U0001F389", "\u2B50", "\u2705", "\u274C"],
         None, None),
        (["\U0001F3AE", "\U0001F3B5", "\U0001F4F7", "\U0001F355", "\u26BD",
          "\U0001F697", "\u2708", "\U0001F319", "\u2600", "\U0001F381"],
         None, None),
    ]

    # Fileira de acao (sempre visivel): ?123 alterna simbolos, emoji
    # alterna emojis, espaco em branco (sem idioma), . e ✓ fecha.
    ACTION_ROW = (["?123", "emoji", " ", ".", "ok"], list(KB_ACTION_FLEX), None)

    def __init__(self, app, entry=None, numeric=False):
        self.app = app
        self.entry = entry
        self.closed = False
        self.born = time.time()
        self.shift = False
        self.numeric = bool(numeric)
        self.emoji = False
        self.cur = [0, 0]
        self.cells = []
        self.row_frames = []
        self.top_btns = []
        self.bottom_btns = []
        self.docked = False
        self.float_geom = None
        try:
            self.target_hwnd = foreground_hwnd()
        except Exception:
            self.target_hwnd = None
        lang = app.lang

        win = tk.Toplevel(app.root)
        self.win = win
        win.title(t("kb_title", lang))
        win.configure(bg=Config.BG_SIDEBAR)
        win.resizable(False, False)
        # Ancorado embaixo como o teclado virtual do Windows (sem moldura)
        try:
            win.overrideredirect(True)
        except Exception:
            pass
        try:
            # Sempre visivel, inclusive sobre o navegador/app externo
            win.attributes("-topmost", True)
        except Exception:
            pass
        if entry is None:
            # Modo global: nao rouba o foco do campo (o digitado vai p/ ele)
            try:
                win.focusmodel("passive")
            except Exception:
                pass
        win.update_idletasks()
        try:
            state = ""
            try:
                state = app.root.state()
            except Exception:
                pass
            if state in ("iconic", "withdrawn"):
                # Root minimizado (modo remoto): ancora na area util da
                # tela (winfo da erro -32000). Respeita a barra de tarefas.
                w2, h2, x2, y2 = None, None, None, None
                try:
                    rect = (ctypes.c_long * 4)()
                    if ctypes.windll.user32.SystemParametersInfoW(
                            0x0030, 0, rect, 0):
                        w2 = min(800, max(512, (rect[2] - rect[0]) - 120))
                        h2 = 340
                        x2 = rect[0] + (rect[2] - rect[0] - w2) // 2
                        y2 = rect[3] - h2
                except Exception:
                    pass
                if w2 is None:
                    try:
                        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
                        w2 = min(800, max(512, sw - 120))
                        h2 = 340
                        x2 = (sw - w2) // 2
                        y2 = sh - h2 - 60
                    except Exception:
                        w2, h2, x2, y2 = 500, 340, 200, 150
                w, h, x, y = w2, h2, x2, y2
            else:
                w = min(800, max(512, app.root.winfo_width() - 120))
                h = 340
                x = app.root.winfo_x() + (app.root.winfo_width() - w) // 2
                y = app.root.winfo_y() + app.root.winfo_height() - h
        except Exception:
            w, h, x, y = 620, 430, 200, 150
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.force_front()
        try:
            win.after(150, self.dock_bottom)
        except Exception:
            pass
        _apply_dark_title(win, "kbd")

        # TopArea slim: titulo + ancorar + fechar (mouse e controle).
        # No dock o titulo some mas os botoes ficam (p/ desancorar).
        self.toparea = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.toparea.pack(fill="x", padx=8, pady=(6, 2))
        self.top_title = tk.Label(self.toparea, text=f"\u2328 {t('kb_title', lang)}",
                                  font=("Segoe UI", 11, "bold"), fg=Config.ACCENT,
                                  bg=Config.BG_SIDEBAR)
        self.top_title.pack(side="left")
        dock_btn = tk.Button(self.toparea, text="\u2B07", font=("Segoe UI", 11, "bold"),
                             bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                             relief="flat", bd=0, cursor="hand2",
                             padx=10, pady=2, command=self.toggle_dock)
        dock_btn.pack(side="right", padx=4)
        self.top_btns.append(("dock", dock_btn))
        close_btn = tk.Button(self.toparea, text="\u2715", font=("Segoe UI", 11, "bold"),
                              bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                              relief="flat", bd=0, cursor="hand2",
                              padx=10, pady=2, command=self.close)
        close_btn.pack(side="right", padx=4)
        self.top_btns.append(("close", close_btn))
        for i, (_bid, _b) in enumerate(self.top_btns):
            _b.bind("<Enter>", lambda e, idx=i: self.set_top(idx))

        self.grid_frame = tk.Frame(win, bg=Config.BG_SIDEBAR)
        self.grid_frame.pack(fill="x")
        self._build_keys()
        self._layout_geometry()
        self._size_to_content()

        self._paint()
        win.bind("<Escape>", lambda e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        app.kb_window = self

    def _rows(self):
        if self.emoji:
            rows = list(self.ROWS_EMOJI)
        elif self.numeric:
            rows = list(self.ROWS_NUM)
        else:
            rows = list(self.ROWS_ALPHA)
        rows.append(self.ACTION_ROW)
        return rows

    def toggle_dock(self):
        self.set_docked(not self.docked)

    def set_docked(self, on):
        if self.closed:
            return
        on = bool(on)
        if on == self.docked:
            if on:
                self._place_docked()
            return
        self.docked = on
        if on:
            try:
                self.float_geom = self.win.geometry()
            except Exception:
                self.float_geom = None
            self._place_docked()
        else:
            try:
                if self.float_geom:
                    self.win.geometry(self.float_geom)
            except Exception:
                pass
        try:
            self.win.update_idletasks()
        except Exception:
            pass
        self._apply_compact(on)

    def _floating_w(self):
        """Largura do teclado (~20% menor que a v1): mesma nos dois modos,
        p/ o dock ficar proximo do flutuante."""
        try:
            state = ""
            try:
                state = self.app.root.state()
            except Exception:
                pass
            if state in ("iconic", "withdrawn"):
                try:
                    rect = (ctypes.c_long * 4)()
                    if ctypes.windll.user32.SystemParametersInfoW(
                            0x0030, 0, rect, 0):
                        return min(800, max(512, (rect[2] - rect[0]) - 120))
                except Exception:
                    pass
                try:
                    return min(800, max(512, self.win.winfo_screenwidth() - 120))
                except Exception:
                    return 512
            return min(800, max(512, self.app.root.winfo_width() - 120))
        except Exception:
            return 512

    def _place_docked(self):
        # Dock = flutuante ancorado embaixo e centralizado (nada de faixa
        # fina esticada): mesma largura, altura ajustada ao conteudo.
        w = self._floating_w()
        try:
            scale = w / self.KB_BASE_W
            est = int(44 + 5 * (self.KB_KEY_H + self.KB_GAP_Y) * scale + 16)
        except Exception:
            est = 340
        try:
            rect = (ctypes.c_long * 4)()
            ok = bool(ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, rect, 0))
        except Exception:
            ok = False
            rect = None
        if ok:
            sw, x0, yb = rect[2] - rect[0], rect[0], rect[3]
        else:
            try:
                sw = self.win.winfo_screenwidth()
                sh = self.win.winfo_screenheight() - 60
                x0, yb = 0, sh
            except Exception:
                return
        try:
            self.win.geometry(f"{w}x{est}+{max(0, x0 + (sw - w) // 2)}+{max(0, yb - est)}")
        except Exception:
            pass

    def _layout_geometry(self):
        """Geometria pela escala W/691: largura exata por flex (uniform),
        fonte pela altura da tecla. Vale p/ flutuante e dock (mesmo tamanho).
        Gaps via padx/pady das teclas."""
        try:
            self.win.update_idletasks()
            W = max(200, self.win.winfo_width())
        except Exception:
            return
        scale = W / self.KB_BASE_W
        gapx = max(2, int(round(self.KB_GAP_X * scale)))
        gapy = max(4, int(round(self.KB_GAP_Y * scale)))
        key_h = self.KB_KEY_H * scale
        font = max(8, min(22, int(key_h * 0.30)))
        padx = max(1, gapx // 2)
        pady = max(1, gapy // 2)
        side = max(2, int(round(self.KB_SIDE * scale)))
        for rf in getattr(self, "row_frames", []):
            style = getattr(rf, "_kb_style", None)
            try:
                if style == "home":
                    ind = int(round(self.KB_HOME_INDENT * scale))
                    rf.pack_configure(padx=(ind, ind))
                elif style == "fixed":
                    # Teclas tamanho baseline centralizadas
                    need = 3 * self.KB_KEY_W * scale + 2 * gapx
                    pad = max(side, int((W - need) / 2))
                    rf.pack_configure(padx=(pad, pad))
                else:
                    rf.pack_configure(padx=(side, side))
            except Exception:
                pass
        for row in self.cells:
            for _key, b in row:
                try:
                    b.configure(font=("Segoe UI", font, "bold"))
                    b.grid_configure(padx=padx, pady=pady)
                except Exception:
                    pass
        for _bid, b in self.top_btns:
            try:
                b.configure(font=("Segoe UI", max(8, min(13, font - 2)), "bold"))
            except Exception:
                pass
        self._paint()

    def _size_to_content(self):
        """Altura justa ao conteudo (ancorado embaixo). Vale p/ flutuante
        e dock: o dock e um flutuante fixado na base."""
        if self.closed:
            return
        try:
            self.win.update_idletasks()
            need = self.win.winfo_reqheight()
            W = self.win.winfo_width()
            x = self.win.winfo_x()
            try:
                yb = self.win.winfo_y() + self.win.winfo_height()
            except Exception:
                yb = None
            h = max(120, min(700, need + 8))
            if yb is None:
                self.win.geometry(f"{W}x{h}")
            else:
                self.win.geometry(f"{W}x{h}+{x}+{max(0, yb - h)}")
        except Exception:
            pass

    def _apply_compact(self, on):
        try:
            if on:
                self.top_title.pack_forget()
            else:
                self.top_title.pack(side="left")
        except Exception:
            pass
        self._layout_geometry()
        self._size_to_content()
        try:
            self.dock_bottom()
        except Exception:
            pass

    def force_front(self, retries=4):
        """Traz p/ frente SEM roubar o foco (teclado sobre app/site em
        tela cheia ou janela). Repete: fullscreen pode se reafirmar depois."""
        if self.closed:
            return
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.win.lift()
        except Exception:
            pass
        try:
            force_topmost_noactivate(self.win)
        except Exception:
            pass
        if retries > 0:
            try:
                self.win.after(400, lambda: self.force_front(retries - 1))
            except Exception:
                pass

    def dock_bottom(self):
        """Reancora na base da area util (barra de tarefas descontada)."""
        if self.closed:
            return
        try:
            self.win.update_idletasks()
            w = self.win.winfo_width()
            h = self.win.winfo_height()
            if w < 50 or h < 50:
                w, h = 800, 340
        except Exception:
            return
        placed = False
        try:
            rect = (ctypes.c_long * 4)()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, rect, 0):
                x = rect[0] + (rect[2] - rect[0] - w) // 2
                y = rect[3] - h
                self.win.geometry(f"+{max(0, x)}+{max(0, y)}")
                placed = True
        except Exception:
            pass
        if not placed:
            try:
                sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
                self.win.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, sh - h - 60)}")
            except Exception:
                pass

    def _build_keys(self):
        try:
            for w in self.grid_frame.winfo_children():
                w.destroy()
        except Exception:
            pass
        self.cells = []
        self.row_frames = []
        for r, (keys, flex, style) in enumerate(self._rows()):
            rf = tk.Frame(self.grid_frame, bg=Config.BG_SIDEBAR)
            rf.pack(fill="x")
            rf._kb_style = style
            self.row_frames.append(rf)
            n = len(keys)
            flexes = list(flex) if flex else [1.0] * n
            row_cells = []
            for c, key in enumerate(keys):
                b = tk.Button(rf, relief="flat", bd=0, cursor="hand2",
                              width=1, height=1,
                              command=lambda rr=r, cc=c: self._click(rr, cc))
                b.grid(row=0, column=c, sticky="nsew")
                try:
                    rf.grid_columnconfigure(c, weight=max(1, int(flexes[c] * 10)),
                                            uniform="kb")
                except Exception:
                    pass
                b.bind("<Enter>", lambda e, rr=r, cc=c: self.set_cursor(rr, cc))
                row_cells.append((key, b))
            self.cells.append(row_cells)
        self.cur = [0, 0]
        self._layout_geometry()

    def toggle_mode(self):
        if self.closed:
            return
        try:
            was_top = self.cur[0] < 0
            was_c = self.cur[1] if was_top else 0
        except Exception:
            was_top, was_c = False, 0
        self.numeric = not self.numeric
        self.emoji = False
        self.shift = False
        self._build_keys()
        if was_top:
            self.cur = [-1, min(was_c, len(self.top_btns) - 1)]
        self._apply_compact(self.docked)
        self._paint()

    def toggle_emoji(self):
        if self.closed:
            return
        try:
            was_top = self.cur[0] < 0
            was_c = self.cur[1] if was_top else 0
        except Exception:
            was_top, was_c = False, 0
        self.emoji = not self.emoji
        if self.emoji:
            self.numeric = False
        self.shift = False
        self._build_keys()
        if was_top:
            self.cur = [-1, min(was_c, len(self.top_btns) - 1)]
        self._apply_compact(self.docked)
        self._paint()

    def _paint_mode_btn(self):
        # Legado: o rotulo ?123/ABC agora sai do _disp via _paint.
        try:
            self._paint()
        except Exception:
            pass

    def _disp(self, key):
        if key == "?123":
            return "ABC" if self.numeric else "?123"
        if key == "emoji":
            return "\U0001F642"
        if key == " ":
            return ""
        if key == "ok":
            return "\u2713"
        if len(key) == 1 and key.isalpha():
            return key.upper() if self.shift else key.lower()
        if key == "\u21E7":
            return "\u21E7●" if self.shift else "\u21E7"
        return key

    def _paint(self):
        for r, row in enumerate(self.cells):
            for c, (key, b) in enumerate(row):
                focused = (self.cur == [r, c])
                b.configure(text=self._disp(key))
                if focused:
                    b.configure(bg=Config.ACCENT, fg="white",
                                highlightbackground=Config.ACCENT_GLOW,
                                highlightthickness=2)
                else:
                    b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                highlightbackground=Config.BORDER,
                                highlightthickness=1)
        for i, (_bid, b) in enumerate(self.top_btns):
            try:
                if self.cur == [-1, i]:
                    b.configure(bg=Config.ACCENT, fg="white",
                                highlightbackground="white",
                                highlightthickness=3)
                else:
                    b.configure(bg=Config.BG_CARD, fg=Config.TEXT_PRIMARY,
                                highlightbackground=Config.BORDER,
                                highlightthickness=1)
            except Exception:
                pass

    def set_cursor(self, r, c):
        if self.closed:
            return
        rows = len(self.cells)
        nt = len(self.top_btns)
        if r < 0:
            r = -1
            c = max(0, min(c, nt - 1)) if nt else 0
        else:
            r = max(0, min(r, rows - 1))
            c = max(0, min(c, len(self.cells[r]) - 1))
        self.cur = [r, c]
        self._paint()

    def set_top(self, idx):
        if self.closed or not self.top_btns:
            return
        self.cur = [-1, max(0, min(idx, len(self.top_btns) - 1))]
        self._paint()

    def on_hat(self, hat):
        if self.closed:
            return
        rows = len(self.cells)
        nt = len(self.top_btns)
        r, c = self.cur
        if r < 0:
            if not nt:
                return
            if hat == (0, 1):
                r, c = rows - 1, min(c, len(self.cells[rows - 1]) - 1)
            elif hat == (0, -1):
                r, c = 0, min(c, len(self.cells[0]) - 1)
            elif hat == (-1, 0):
                c = (c - 1) % nt
            elif hat == (1, 0):
                c = (c + 1) % nt
            else:
                return
        elif hat == (0, 1):
            if r == 0 and nt:
                r, c = -1, min(c, nt - 1)
            else:
                r = (r - 1) % rows
        elif hat == (0, -1):
            r = (r + 1) % rows
        elif hat == (-1, 0):
            c = (c - 1) % len(self.cells[r])
        elif hat == (1, 0):
            c = (c + 1) % len(self.cells[r])
        else:
            return
        self.cur = [r, c]
        self._paint()

    def _click(self, r, c):
        self.set_cursor(r, c)
        self.press_focused()

    def press_focused(self):
        if self.closed:
            return
        r, c = self.cur
        if r < 0:
            try:
                bid = self.top_btns[c][0]
            except Exception:
                return
            if bid == "dock":
                self.toggle_dock()
            elif bid == "close":
                self.close()
            return
        try:
            key = self.cells[r][c][0]
        except Exception:
            return
        self.press_key(key)

    def press_key(self, key):
        if self.closed:
            return
        if key == "?123":
            self.toggle_mode()
            return
        if key == "emoji":
            self.toggle_emoji()
            return
        if key == "ok":
            self.submit()
            return
        if key == "\u21E7":
            self.shift = not self.shift
            self._paint()
            return
        if key == "\u232B":
            self._erase()
            return
        ch = key.upper() if (len(key) == 1 and key.isalpha() and self.shift) else key
        if len(key) == 1 and key.isalpha() and not self.shift:
            ch = key.lower()
        try:
            ent = self.entry
            if ent is not None and ent.winfo_exists():
                ent.insert(tk.INSERT, ch)
                try:
                    ent.event_generate("<KeyRelease>")
                except Exception:
                    pass
                return
        except Exception:
            pass
        self._type_global(ch)

    def _erase(self):
        try:
            ent = self.entry
            if ent is not None and ent.winfo_exists():
                pos = ent.index(tk.INSERT)
                if pos > 0:
                    ent.delete(pos - 1)
                return
        except Exception:
            pass
        self._type_global_key(VK_BACK)

    def _own_hwnd(self):
        try:
            return int(self.win.winfo_id())
        except Exception:
            return None

    def _type_global(self, text):
        try:
            hw = foreground_hwnd()
            if not hw or hw == self._own_hwnd():
                hw = self.target_hwnd
            if hw:
                bring_to_front(hw)
                time.sleep(0.05)
            type_text(self.app.root, text)
        except Exception:
            pass

    def _type_global_key(self, vk):
        try:
            hw = foreground_hwnd()
            if not hw or hw == self._own_hwnd():
                hw = self.target_hwnd
            if hw:
                bring_to_front(hw)
                time.sleep(0.05)
            tap_key(vk)
        except Exception:
            pass

    def submit(self):
        """Confirma o texto e fecha. No modo global (sobre app/site, sem
        entry do Nexus) manda Enter junto p/ submeter a busca/login; com
        entry do Nexus so fecha (o dialogo confirma separado)."""
        try:
            global_mode = True
            try:
                ent = self.entry
                global_mode = not (ent is not None and ent.winfo_exists())
            except Exception:
                pass
        except Exception:
            global_mode = True
        self.close()
        if global_mode:
            try:
                self._type_global_key(VK_RETURN)
            except Exception:
                pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.app.kb_window is self:
                self.app.kb_window = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
