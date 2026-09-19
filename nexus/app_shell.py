# -*- coding: utf-8 -*-
"""Init + construcao da janela principal (extraido sem alteracao)."""

import os
import time
import tkinter as tk
import tkinter.ttk as tk_ttk
from datetime import datetime
from PIL import Image, ImageTk

from .config import Config, ensure_images_dir, load_settings, save_settings
from .database import NexusDB
from .focus import FocusManager
from .gamepad import GamepadManager
from .games import GAME_COVER_SIZE, find_game_cover
from .i18n import t
from .opener import StreamingOpener
from .paths import BASE_DIR, IMAGES_DIR
from .streamings import STREAMINGS_DB
from .win32 import _apply_dark_title


class AppShellMixin:
    """Init, visuais, dados de servicos e construcao da UI."""

    def __init__(self, root):
        self.root = root
        self.root.title("Nexus - Big Picture")
        self.root.configure(bg=Config.BG_PRIMARY)
        self.root.geometry("1920x1080")
        # Hub abre em tela cheia sem bordas (modo big picture); F11 alterna.
        try:
            self.root.attributes("-fullscreen", True)
        except Exception:
            pass
        self._set_dark_title_bar()
        self._set_app_icon()
        # Reaplica ao mostrar/restaurar (o atributo pre-mapeamento pode ser ignorado)
        try:
            self.root.after(300, self._set_dark_title_bar)
            self.root.bind("<Map>", lambda e: self._set_dark_title_bar())
        except Exception:
            pass

        self.settings = load_settings()
        if self.settings.get("resolution_mode") != "fullscreen":
            self.settings["resolution_mode"] = "fullscreen"
            try:
                save_settings(self.settings)
            except Exception:
                pass
        ensure_images_dir()
        self.db = NexusDB()
        self.opener = StreamingOpener(self.settings)
        self.photo_cache = {}
        self.logo_path_cache = {}
        self.current_tab = "all"
        self.sidebar_visible = False
        self.sidebar_menu_index = 0
        self.notif_visible = False
        self._latest_release = None
        self.theme_visible = False
        self.theme_focus = 0
        self.sidepanel = None
        self.focus_tab = 0
        self.focus_mgr = FocusManager()
        self.nav_level = "tabs"
        self.sections = []
        self.card_index = {}
        self.all_cards = []
        self.card_widgets = []
        self.carousel_cards = []
        self.open_dialog = None
        self.flipped = None
        self._pending_flip = None
        self.active_menu = None
        self.pad_capture = None
        self.pad_window = None
        self.kb_window = None
        self.browser_remote = None
        # Procs do navegador que o Nexus matou de proposito (Back+Start,
        # quit): a morte deles nao e crash e nao cai no fallback externo.
        self._browser_closing = set()
        self.using_gamepad = False
        self.form_focus = []
        self.form_idx = 0
        self.lang = self.settings.get("language", "pt-br")
        self.search_query = ""
        self._search_refocus = False
        self.search_entry = None
        self._migrate_favorites()

        self.build_ui()
        self.setup_keybinds()
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.confirm_quit)
        except Exception:
            pass
        self.gamepad = GamepadManager(self)
        self.update_clock()
        self.check_updates_startup()

    def _set_app_icon(self):
        # Logo_mini na barra de tarefas/titulo (vale p/ todas as janelas).
        # iconbitmap (.ico nativo) + iconphoto: cobre barra, Alt+Tab e titulo.
        try:
            ico = os.path.join(BASE_DIR, "logo_nexus", "Nexus.ico")
            if os.path.exists(ico):
                try:
                    self.root.iconbitmap(default=ico)
                except Exception:
                    pass
            from PIL import Image as _Img, ImageTk as _ImgTk
            p = os.path.join(BASE_DIR, "logo_nexus", "Logo_mini.png")
            if os.path.exists(p):
                img = _Img.open(p).convert("RGBA")
                img.thumbnail((64, 64), _Img.LANCZOS)
                self.icon_photo = _ImgTk.PhotoImage(img)
                # Passar o NOME (str): o objeto cru quebra o parse de args do Tcl.
                # Tenta ate confirmar que fixou (consulta nao-vazia).
                for _try in range(3):
                    try:
                        self.root.iconphoto(True, str(self.icon_photo))
                        if self.root.tk.call("wm", "iconphoto", self.root._w):
                            break
                    except Exception:
                        pass
                    try:
                        time.sleep(0.05)
                    except Exception:
                        pass
        except Exception:
            pass

    def _set_dark_title_bar(self):
        _apply_dark_title(self.root, "root")

    def _style_scrollbars(self):
        style = tk_ttk.Style()
        style.theme_use("default")
        style.configure("Accent.Vertical.TScrollbar",
                        background=Config.ACCENT,
                        troughcolor=Config.BG_PRIMARY,
                        arrowcolor=Config.BG_PRIMARY,
                        bordercolor=Config.BG_PRIMARY,
                        lightcolor=Config.BG_PRIMARY,
                        darkcolor=Config.BG_PRIMARY,
                        relief="flat",
                        borderwidth=0)
        style.map("Accent.Vertical.TScrollbar",
                  background=[("active", Config.ACCENT_GLOW)])

    def load_photo(self, filepath, size=Config.LOGO_SIZE):
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            key = filepath + str(size)
            if key in self.photo_cache:
                return self.photo_cache[key]
            try:
                box = (int(size), int(size))
            except Exception:
                box = tuple(size)  # (largura, altura) p/ capas de jogo
            pil_img = Image.open(filepath)
            pil_img.thumbnail(box, Image.BILINEAR)  # 2x mais rapido; igual em 80px
            photo = ImageTk.PhotoImage(pil_img)
            self.photo_cache[key] = photo
            return photo
        except:
            return None

    def get_logo(self, name, size=None):
        # Capas de jogo usam o tamanho do card; streamings usam 80x80
        try:
            big = bool(self.game_is_external(name) or self.game_folder(name)
                       or self.game_is_platform(name))
        except Exception:
            big = False
        cover_size = size or (GAME_COVER_SIZE if big else Config.LOGO_SIZE)
        # 1) Logo trocado manualmente (vale p/ streamings, pastas e atalhos)
        custom = self.settings.get("custom_streamings", {})
        if name in custom and "image" in custom[name]:
            img_path = custom[name]["image"]
            if img_path and os.path.exists(img_path):
                return self.load_photo(img_path, size=cover_size)
        # 2) Capa do atalho externo (.exe em qualquer pasta)
        try:
            ext_cover = (self.settings.get("external_games") or {}).get(name, {}).get("cover", "")
            if ext_cover and os.path.exists(ext_cover):
                return self.load_photo(ext_cover, size=cover_size)
        except Exception:
            pass
        # 2b) Capa do jogo de plataforma (Steam/Epic/Xbox)
        try:
            plat_cover = (self.settings.get("platform_games") or {}).get(name, {}).get("cover", "")
            if plat_cover and os.path.exists(plat_cover):
                return self.load_photo(plat_cover, size=cover_size)
        except Exception:
            pass
        # 3) Capa dentro da pasta do jogo (games/Nome/)
        gf = self.game_folder(name)
        if gf:
            cover = find_game_cover(gf)
            if cover:
                return self.load_photo(cover, size=cover_size)
        try:
            hit = self.logo_path_cache.get(name)
            if hit and os.path.exists(hit):
                return self.load_photo(hit)
        except Exception:
            pass
        # Variantes do nome de arquivo: exato, minusculo e normalizado
        # ("Amazon Prime" -> Amazon_Prime, "Paramount+" -> Paramount_Plus)
        normalized = name.replace(" ", "_").replace("+", "_Plus")
        seen = set()
        candidates = []
        for variant in (name, normalized):
            for form in (variant, variant.lower()):
                if form not in seen:
                    seen.add(form)
                    candidates.append(form)
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp"]:
            for base in candidates:
                p = os.path.join(IMAGES_DIR, base + "_logo" + ext)
                if os.path.exists(p):
                    try:
                        self.logo_path_cache[name] = p
                    except Exception:
                        pass
                    return self.load_photo(p)
        return None

    def get_all_services(self):
        hidden = set(self.settings.get("hidden_streamings", []))
        overrides = self.settings.get("custom_urls", {})
        all_s = {}
        for k, v in STREAMINGS_DB.items():
            if k not in hidden:
                if k in overrides:
                    v = {**v, "url": overrides[k]}
                all_s[k] = v
        for k, v in self.settings.get("custom_streamings", {}).items():
            if k not in hidden:
                all_s[k] = v
        return all_s

    def set_card_color(self, name, hex_color):
        colors = self.settings.get("card_colors", {})
        colors[name] = hex_color
        self.settings["card_colors"] = colors
        save_settings(self.settings)
        self.refresh_ui()

    def reset_card_color(self, name):
        colors = self.settings.get("card_colors", {})
        if name in colors:
            del colors[name]
            self.settings["card_colors"] = colors
            save_settings(self.settings)
            self.refresh_ui()

    def edit_card_url(self, name, url):
        url = (url or "").strip()
        if not url:
            return False
        custom = self.settings.get("custom_streamings", {})
        if name in custom:
            custom[name]["url"] = url
            self.settings["custom_streamings"] = custom
        else:
            urls = self.settings.get("custom_urls", {})
            urls[name] = url
            self.settings["custom_urls"] = urls
        save_settings(self.settings)
        return True

    # ===================== BUILD UI =====================
    def build_ui(self):
        self.close_child_windows()
        for w in self.root.winfo_children():
            w.destroy()

        self.root.configure(bg=Config.BG_PRIMARY)

        self.main_frame = tk.Frame(self.root, bg=Config.BG_PRIMARY)
        self.main_frame.pack(fill="both", expand=True)

        self.build_top_bar()
        self.build_content_area()
        self.build_bottom_tabs()
        self.build_sidebar()
        self.build_qa_overlay()
        self.build_notif_panel()
        self.build_theme_panel()
        if self.theme_visible:
            # Aplicar tema reconstrui a UI: reabre o painel onde estava.
            self.render_theme_panel()
            self._show_theme_panel()
        try:
            sp = getattr(self, "sidepanel", None)
            if sp is not None and getattr(sp, "visible", False):
                sp.reopen()
        except Exception:
            pass

        self.render_tab(self.current_tab)

    def close_child_windows(self):
        """Fecha logicamente as janelas filhas antes de reconstruir a UI.
        Sem isso elas viram zumbis (destruidas com closed=False) e o
        controle passa a falar com janela morta: confirmar/X param."""
        for attr, closer in (("kb_window", "close"), ("pad_window", "close"),
                             ("open_dialog", "_close"), ("active_menu", "close")):
            try:
                w = getattr(self, attr, None)
                if w is not None and not getattr(w, "closed", True):
                    getattr(w, closer)()
            except Exception:
                pass

    def build_top_bar(self):
        bar = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR, height=70)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        logo = tk.Label(bar, text="\u25C6 NEXUS", font=("Segoe UI", 24, "bold"),
                        fg=Config.ACCENT, bg=Config.BG_SIDEBAR)
        logo.pack(side="left", padx=30)

        self.nav_frame = tk.Frame(bar, bg=Config.BG_SIDEBAR)
        self.nav_frame.pack(side="left", padx=40)

        self.nav_buttons = {}
        tabs = [
            (t("tab_favorites", self.lang), "favorites"),
            (t("tab_movies", self.lang), "movies"),
            (t("tab_music", self.lang), "music"),
            (t("tab_videos", self.lang), "videos"),
            (t("tab_all", self.lang), "all"),
            (t("tab_games", self.lang), "games"),
            (t("tab_gamefavorites", self.lang), "gamefavorites"),
        ]
        for idx, (text, tid) in enumerate(tabs):
            if tid == "games":
                # Divisoria visual: Jogos e outra categoria (so visual)
                sep = tk.Frame(self.nav_frame, bg=Config.BORDER, width=2)
                sep.pack(side="left", fill="y", padx=10, pady=12)
            btn = tk.Button(self.nav_frame, text=text, font=("Segoe UI", 13),
                            bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                            activebackground=Config.ACCENT, activeforeground="white",
                            relief="flat", cursor="hand2", bd=0,
                            command=lambda t=tid: self.switch_tab(t))
            btn.pack(side="left", padx=4)
            btn.bind("<Enter>", lambda e, i=idx: self.sync_focus_to_tab(i))
            self.nav_buttons[tid] = btn

        right = tk.Frame(bar, bg=Config.BG_SIDEBAR)
        right.pack(side="right", padx=20)

        self.clock_label = tk.Label(right, font=("Segoe UI", 13),
                                    fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.clock_label.pack(side="left", padx=10)

        self.notif_btn = tk.Button(right, text="\U0001F514", font=("Segoe UI", 16),
                                   bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                                   activebackground=Config.ACCENT, relief="flat",
                                   cursor="hand2", command=self.toggle_notif_panel, bd=0)
        self.notif_btn.pack(side="left", padx=10)
        self.notif_badge = tk.Label(self.notif_btn, text="",
                                    font=("Segoe UI", 8, "bold"),
                                    bg="#e94560", fg="white")
        self.notif_badge.place(relx=0.7, rely=0.12)
        self.notif_badge.place_forget()

        qa_btn = tk.Button(right, text="\u2630", font=("Segoe UI", 18),
                           bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY,
                           activebackground=Config.ACCENT, relief="flat",
                           cursor="hand2", command=self.toggle_sidebar, bd=0)
        qa_btn.pack(side="left", padx=10)

        # Botoes de janela discretos: minimizar e fechar (F11 alterna tela cheia)
        min_btn = tk.Button(right, text="\u2013", font=("Segoe UI", 12),
                            bg=Config.BG_SIDEBAR, fg="#4a4a6a",
                            activebackground=Config.BG_CARD_HOVER,
                            activeforeground=Config.TEXT_PRIMARY,
                            relief="flat", cursor="hand2", bd=0,
                            padx=10, pady=2, command=self.minimize_app)
        min_btn.pack(side="left", padx=2)
        min_btn.bind("<Enter>", lambda e: min_btn.configure(fg=Config.TEXT_PRIMARY))
        min_btn.bind("<Leave>", lambda e: min_btn.configure(fg="#4a4a6a"))
        close_btn = tk.Button(right, text="\u2715", font=("Segoe UI", 12),
                              bg=Config.BG_SIDEBAR, fg="#4a4a6a",
                              activebackground="#e94560",
                              activeforeground="white",
                              relief="flat", cursor="hand2", bd=0,
                              padx=10, pady=2, command=self.confirm_quit)
        close_btn.pack(side="left", padx=2)
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#e94560"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#4a4a6a"))

        # Arrastar a janela pelo cursor nas areas livres da barra superior
        for w in (bar, logo, self.nav_frame, right, self.clock_label):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        try:
            if self.root.attributes("-fullscreen"):
                return
            self._drag_offset = (event.x_root - self.root.winfo_x(),
                                 event.y_root - self.root.winfo_y())
        except Exception:
            pass

    def _drag_move(self, event):
        try:
            if self.root.attributes("-fullscreen"):
                return
            dx, dy = getattr(self, "_drag_offset", (0, 0))
            self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
        except Exception:
            pass

    def build_content_area(self):
        self.content_frame = tk.Frame(self.main_frame, bg=Config.BG_PRIMARY)
        self.content_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.content_frame, bg=Config.BG_PRIMARY,
                                highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self._style_scrollbars()
        self.scrollbar = tk_ttk.Scrollbar(self.content_frame, orient="vertical",
                                          command=self.canvas.yview,
                                          style="Accent.Vertical.TScrollbar")
        self.scrollbar.pack(side="right", fill="y", padx=(0, 2))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame = tk.Frame(self.canvas, bg=Config.BG_PRIMARY)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame,
                                                        anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self.canvas_window, width=e.width))

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scroll_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.config(takefocus=True)

        self.root.bind("<MouseWheel>", self._on_mousewheel_global)

    def build_bottom_tabs(self):
        pass

    def build_sidebar(self):
        self.sidebar = tk.Frame(self.main_frame, bg=Config.BG_SIDEBAR,
                                width=Config.SIDEBAR_WIDTH)
        self.sidebar.place(x=-Config.SIDEBAR_WIDTH, y=0, relheight=1)
        self.sidebar.pack_propagate(False)
        self.sidebar_visible = False

        header = tk.Frame(self.sidebar, bg=Config.BG_SIDEBAR)
        header.pack(fill="x", padx=0, pady=(25, 0))

        tk.Label(header, text="\u25C6 NEXUS", font=("Segoe UI", 26, "bold"),
                 fg=Config.ACCENT, bg=Config.BG_SIDEBAR).pack(padx=25, anchor="w")

        self.sidebar_time = tk.Label(header, font=("Segoe UI", 44, "bold"),
                                     fg=Config.TEXT_PRIMARY, bg=Config.BG_SIDEBAR)
        self.sidebar_time.pack(pady=(8, 2), padx=25, anchor="w")

        self.sidebar_date = tk.Label(header, font=("Segoe UI", 14),
                                     fg=Config.TEXT_SECONDARY, bg=Config.BG_SIDEBAR)
        self.sidebar_date.pack(pady=(0, 20), padx=25, anchor="w")

        weekday = self._get_translated_weekday()
        now = datetime.now()
        self.sidebar_date.config(text=f"{weekday}, {now.strftime('%d/%m/%Y')}")

        tk.Frame(self.sidebar, bg=Config.BORDER, height=1).pack(fill="x", padx=25)

        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=Config.BG_SIDEBAR,
                                        highlightthickness=0, bd=0)

        self.sidebar_scrollbar = tk_ttk.Scrollbar(self.sidebar, orient="vertical",
                                                  command=self.sidebar_canvas.yview,
                                                  style="Accent.Vertical.TScrollbar")
        self.sidebar_scroll_frame = tk.Frame(self.sidebar_canvas, bg=Config.BG_SIDEBAR)

        self.sidebar_scroll_frame.bind(
            "<Configure>", lambda e: self.sidebar_canvas.configure(
                scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_scroll_frame,
                                          anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_scrollbar.pack(side="right", fill="y", padx=(0, 2))

        self.sidebar_btns = []
        self.sidebar_items = []

        tk.Label(self.sidebar_scroll_frame, text=t("sidebar_settings", self.lang),
                 font=("Segoe UI", 13, "bold"), fg=Config.TEXT_PRIMARY,
                 bg=Config.BG_SIDEBAR, anchor="w").pack(pady=(0, 8), padx=25, fill="x")

        settings_items = [
            (t("settings_theme", self.lang), self.open_theme_picker, "\U0001F3A8"),
            (t("settings_controls", self.lang), self.open_controles, "\U0001F3AE"),
            (t("settings_sound", self.lang), self.open_som, "\U0001F50A"),
            (t("settings_language", self.lang), self.open_idioma, "\U0001F310"),
            (t("sidebar_add", self.lang), self.open_adicionar, "\U0001F4FA"),
            (t("settings_system", self.lang), self.open_sistema, "\u2699"),
        ]

        for text, cmd, icon in settings_items:
            btn = tk.Button(self.sidebar_scroll_frame, text=f"  {icon}  {text}",
                            font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                            fg=Config.TEXT_SECONDARY, activebackground=Config.ACCENT,
                            activeforeground="white", relief="flat", anchor="w",
                            cursor="hand2", bd=0, padx=20, pady=10, command=cmd)
            btn.pack(fill="x", padx=15, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
            self.sidebar_btns.append(btn)
            self.sidebar_items.append((text, cmd))

        tk.Frame(self.sidebar_scroll_frame, bg=Config.BORDER, height=1).pack(
            fill="x", padx=25, pady=(15, 10))

        add_btn = tk.Button(self.sidebar_scroll_frame,
                            text=f"  \U0001F4FA  {t('sidebar_add', self.lang)}",
                            font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                            fg=Config.TEXT_SECONDARY, activebackground=Config.ACCENT,
                            activeforeground="white", relief="flat", anchor="w",
                             cursor="hand2", bd=0, padx=20, pady=10,
                             command=self.open_adicionar)
        add_btn.pack(fill="x", padx=15, pady=2)
        add_btn.bind("<Enter>", lambda e, b=add_btn: b.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY))
        add_btn.bind("<Leave>", lambda e, b=add_btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
        self.sidebar_btns.append(add_btn)
        self.sidebar_items.append((t("sidebar_add", self.lang), self.open_adicionar))

        close_btn = tk.Button(self.sidebar_scroll_frame,
                              text=f"  \u2715  {t('sidebar_close', self.lang)}",
                              font=("Segoe UI", 13), bg=Config.BG_SIDEBAR,
                              fg=Config.TEXT_SECONDARY, activebackground="#e94560",
                              activeforeground="white", relief="flat", anchor="w",
                              cursor="hand2", bd=0, padx=20, pady=10,
                              command=self.toggle_sidebar)
        close_btn.pack(fill="x", padx=15, pady=(2, 20))
        close_btn.bind("<Enter>", lambda e, b=close_btn: b.configure(bg="#e94560", fg="white"))
        close_btn.bind("<Leave>", lambda e, b=close_btn: b.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY))
        self.sidebar_btns.append(close_btn)
        self.sidebar_items.append((t("sidebar_close", self.lang), self.toggle_sidebar))
        # Scroll com o mouse em QUALQUER ponto da sidebar
        self._bind_wheel_tree(self.sidebar, self._on_sidebar_wheel)

    def build_qa_overlay(self):
        self.dim_overlay = tk.Frame(self.root, bg="#000000")
        self.dim_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.dim_overlay.place_forget()
        self.dim_overlay.lower(self.main_frame)
        self.dim_overlay.bind("<Button-1>", lambda e: self.close_qa())

        self.qa_frame = tk.Frame(self.root, bg=Config.BG_SIDEBAR,
                                  highlightbackground=Config.ACCENT, highlightthickness=2)
        self.qa_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.qa_frame.place_forget()
