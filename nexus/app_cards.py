# -*- coding: utf-8 -*-
"""Cards, grade, lista e foco (extraido sem alteracao)."""

import os
import shutil
import tkinter as tk
from shutil import copy2

from .config import Config, save_settings
from .dialogs import _modal_alive, top_modal
from .games import GAME_IMG_EXTS, _safe_icon_basename
from .i18n import cat_label
from .paths import GAMES_DIR, IMAGES_DIR
from .win32 import _set_cursor_pos, foreground_hwnd


class AppCardsMixin:
    """Renderizacao de cards/lista e sincronia do foco."""

    def render_section(self, title, names):
        if not names:
            return

        section = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        section.pack(fill="x", padx=30, pady=(20, 5))

        title_lbl = tk.Label(section, text=title, font=("Segoe UI", 20, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
        title_lbl.pack(anchor="w")

        line = tk.Frame(section, bg=Config.ACCENT, height=3, width=120)
        line.pack(anchor="w", pady=(5, 15))

        carousel_outer = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        carousel_outer.pack(fill="x", pady=(0, 10))

        arrow_bg = Config.BG_SIDEBAR
        arrow_fg = Config.ACCENT
        arrow_hover = Config.ACCENT_GLOW

        left_btn = tk.Button(carousel_outer, text="\u25C0", font=("Segoe UI", 20),
                             bg=arrow_bg, fg=arrow_fg, relief="flat", bd=0,
                             cursor="hand2", activebackground=arrow_hover,
                             activeforeground="white", width=4, height=3)
        left_btn.pack(side="left", fill="y")

        carousel_canvas = tk.Canvas(carousel_outer, bg=Config.BG_PRIMARY,
                                    highlightthickness=0, bd=0, height=Config.CARD_HEIGHT + 20)
        carousel_canvas.pack(side="left", fill="both", expand=True)

        right_btn = tk.Button(carousel_outer, text="\u25B6", font=("Segoe UI", 20),
                              bg=arrow_bg, fg=arrow_fg, relief="flat", bd=0,
                              cursor="hand2", activebackground=arrow_hover,
                              activeforeground="white", width=4, height=3)
        right_btn.pack(side="right", fill="y")

        for b in [left_btn, right_btn]:
            b.bind("<Enter>", lambda e, btn=b: btn.configure(fg=arrow_hover))
            b.bind("<Leave>", lambda e, btn=b: btn.configure(fg=arrow_fg))

        inner_frame = tk.Frame(carousel_canvas, bg=Config.BG_PRIMARY)
        carousel_canvas.create_window((0, 0), window=inner_frame, anchor="nw", tags="inner")

        sec = {
            "title_widget": title_lbl,
            "line_widget": line,
            "canvas": carousel_canvas,
            "inner_frame": inner_frame,
            "left_btn": left_btn,
            "right_btn": right_btn,
            "names": list(names),
            "widgets": [],
            "scroll_offset": 0,
            "visible_count": 4,
        }

        def _sync_focus_after_manual_scroll():
            if (self.nav_level == "items" and self.sections
                    and self.focus_mgr.focused_row < len(self.sections)
                    and self.sections[self.focus_mgr.focused_row] is sec):
                self._clamp_focused_col()
                self.update_all_focus()

        def scroll_left():
            if sec["scroll_offset"] > 0:
                sec["scroll_offset"] -= 1
                self._update_carousel_scroll(sec)
                _sync_focus_after_manual_scroll()

        def scroll_right():
            _, end, total = self._get_visible_range(sec)
            if end < total:
                sec["scroll_offset"] += 1
                self._update_carousel_scroll(sec)
                _sync_focus_after_manual_scroll()

        left_btn.configure(command=scroll_left)
        right_btn.configure(command=scroll_right)

        for i, name in enumerate(names):
            card = self.create_card(inner_frame, name)
            card.grid(row=0, column=i, padx=7, pady=5, sticky="nsew")
            inner_frame.columnconfigure(i, weight=0)
            sec["widgets"].append(card)
            self.card_index[card] = (len(self.sections), i)

        self.sections.append(sec)

        inner_frame.update_idletasks()
        total_width = inner_frame.winfo_reqwidth()
        carousel_canvas.configure(scrollregion=(0, 0, total_width, Config.CARD_HEIGHT + 20))

        def on_canvas_configure(e):
            carousel_canvas.itemconfig("inner", width=max(e.width, total_width))
        carousel_canvas.bind("<Configure>", on_canvas_configure)

        def _section_mousewheel(event):
            carousel_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        carousel_canvas.bind("<MouseWheel>", _section_mousewheel)
        inner_frame.bind("<MouseWheel>", _section_mousewheel)

    def render_grid(self, title, names):
        if not names:
            return

        section = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        section.pack(fill="x", padx=30, pady=(20, 5))

        title_lbl = tk.Label(section, text=title, font=("Segoe UI", 20, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
        title_lbl.pack(anchor="w")

        line = tk.Frame(section, bg=Config.ACCENT, height=3, width=120)
        line.pack(anchor="w", pady=(5, 15))

        grid_frame = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        grid_frame.pack(fill="x", padx=30, pady=(0, 10))

        sec_widgets = []
        for i, name in enumerate(names):
            card = self.create_card(grid_frame, name)
            card.grid(row=i // 5, column=i % 5, padx=7, pady=5, sticky="nsew")
            sec_widgets.append(card)
            self.card_index[card] = (len(self.sections), i)

        for c in range(5):
            grid_frame.columnconfigure(c, weight=1)

        self.sections.append({
            "title_widget": title_lbl,
            "line_widget": line,
            "canvas": None,
            "inner_frame": grid_frame,
            "left_btn": None,
            "right_btn": None,
            "names": list(names),
            "widgets": sec_widgets,
            "scroll_offset": 0,
            "visible_count": 5,
        })

    def create_card(self, parent, name):
        info = self.get_all_services().get(name, {})
        if not info and (self.game_folder(name) or self.game_is_external(name)
                         or self.game_is_platform(name)):
            info = {"icon": "\U0001F3AE", "category": "Games"}
        icon = info.get("icon", "\U0001F4F0")
        url = info.get("url", "#")
        category = info.get("category", "")
        color = self.settings.get("card_colors", {}).get(name, info.get("color", Config.ACCENT))

        card = tk.Frame(parent, bg=Config.BG_CARD, relief="flat",
                        highlightbackground=Config.BORDER, highlightthickness=1,
                        cursor="hand2", width=Config.CARD_WIDTH, height=Config.CARD_HEIGHT)
        card.pack_propagate(False)
        card._flip_tall = True

        top_area = tk.Frame(card, bg=color, height=160)
        top_area.pack(fill="x")
        top_area.pack_propagate(False)

        photo = self.get_logo(name)
        if photo:
            lbl = tk.Label(top_area, image=photo, bg=color, cursor="hand2")
            lbl.image = photo
            lbl.pack(expand=True)
        else:
            lbl = tk.Label(top_area, text=icon, font=("Segoe UI Emoji", 48),
                     bg=color, fg="white", cursor="hand2")
            lbl.pack(expand=True)

        info_area = tk.Frame(card, bg=Config.BG_CARD)
        info_area.pack(fill="both", expand=True, padx=12, pady=(10, 8))

        name_lbl = tk.Label(info_area, text=name, font=("Segoe UI", 14, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD, cursor="hand2",
                 wraplength=Config.CARD_WIDTH - 24)
        name_lbl.pack(anchor="w")

        cat_lbl = tk.Label(info_area, text=cat_label(category, self.lang).upper(), font=("Segoe UI", 9),
                 fg=Config.ACCENT, bg=Config.BG_CARD, cursor="hand2")
        cat_lbl.pack(anchor="w", pady=(2, 0))

        top_content = info.get("top_content", [])
        if top_content:
            for tc in top_content[:2]:
                tk.Label(info_area, text=f"\u25B8 {tc['title']}", font=("Segoe UI", 9),
                         fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, cursor="hand2",
                         anchor="w").pack(anchor="w", pady=(4, 0))

        if name in self.settings.get("favorites", []):
            tk.Label(card, text="\u2B50", font=("Segoe UI", 10),
                     fg="#ffd700", bg=Config.BG_CARD).place(relx=0.92, rely=0.03, anchor="ne")

        def on_click(e, n=name, c=card):
            self.on_card_click(c, n)

        def on_ctx(e, n=name):
            self.show_context_menu(e, n)

        def on_enter(e, c=card):
            c.configure(bg=Config.BG_CARD_HOVER, highlightbackground=Config.ACCENT, highlightthickness=2)
            self.sync_focus_to_card(c)

        def on_leave(e, c=card):
            c.configure(bg=Config.BG_CARD, highlightbackground=Config.BORDER, highlightthickness=1)

        # Clique/menu so no container: os filhos borbulham ate aqui
        # (um bind por nivel evitava flip-duplo; agora e bind unico).
        card.bind("<Button-1>", on_click)
        card.bind("<Button-3>", on_ctx)
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        top_area.bind("<Enter>", on_enter)
        top_area.bind("<Leave>", on_leave)

        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)

        info_area.bind("<Enter>", on_enter)
        info_area.bind("<Leave>", on_leave)

        name_lbl.bind("<Enter>", on_enter)
        name_lbl.bind("<Leave>", on_leave)

        cat_lbl.bind("<Enter>", on_enter)
        cat_lbl.bind("<Leave>", on_leave)

        return card

    def sync_focus_to_tab(self, idx):
        """Mouse sobre a aba vira o foco oficial (confirmar segue a seta)."""
        try:
            changed = (idx != self.focus_tab)
            self.nav_level = "tabs"
            self.focus_tab = idx
            self.update_all_focus()
            if changed:
                self.play_tick()
        except Exception:
            pass

    def warp_to_focus(self):
        """Cursor do mouse vai para o item focado: cursor e foco viram
        UMA selecao so. So quando o Nexus esta em primeiro plano e sem
        modal/remoto (nunca puxa o cursor do usuario a toa)."""
        try:
            gp = self.gamepad
            if not gp or not gp.running or gp.joystick is None:
                return
            if gp.remote_active:
                return
            if top_modal(self) is not None:
                return
            if self.nexus_hwnd() != foreground_hwnd():
                return
            w = None
            if self.nav_level == "tabs":
                tids = list(self.nav_buttons.keys())
                if 0 <= self.focus_tab < len(tids):
                    w = self.nav_buttons[tids[self.focus_tab]]
            elif self.nav_level == "items" and self.sections:
                row = min(self.focus_mgr.focused_row, len(self.sections) - 1)
                sec = self.sections[row]
                if sec.get("canvas") is None:
                    j = self.focus_mgr.focused_col
                else:
                    j = sec.get("scroll_offset", 0) + self.focus_mgr.focused_col
                widgets = sec.get("widgets", [])
                if 0 <= j < len(widgets):
                    w = widgets[j]
            if w is None:
                return
            try:
                if not w.winfo_exists():
                    return
                w.update_idletasks()
                x = w.winfo_rootx() + w.winfo_width() // 2
                y = w.winfo_rooty() + w.winfo_height() // 2
            except Exception:
                return
            _set_cursor_pos(x, y)
        except Exception:
            pass

    def sync_focus_to_card(self, card):
        """Mouse/seta sobre o card vira o foco oficial: o confirmar do
        controle abre ONDE a seta esta, nao a selecao antiga."""
        try:
            pos = self.card_index.get(card)
            if not pos:
                return
            row, col = pos
            if row >= len(self.sections):
                return
            sec = self.sections[row]
            if sec.get("canvas") is not None:
                col = col - sec.get("scroll_offset", 0)
            if col < 0:
                return
            old = (self.nav_level, self.focus_mgr.focused_row,
                   self.focus_mgr.focused_col)
            self.nav_level = "items"
            self.focus_mgr.focused_row = row
            self.focus_mgr.focused_col = col
            self.update_all_focus()
            if old != ("items", row, col):
                self.play_tick()
        except Exception:
            pass

    def on_card_click(self, widget, name):
        try:
            is_game = (self.current_tab == "games")
        except Exception:
            is_game = False
        if widget is None:
            try:
                widget = self.find_card_widget(name)
            except Exception:
                widget = None
        try:
            self.flip_card(widget, name, is_game)
        except Exception:
            pass

    def set_game_cover(self, name, src_path):
        if not src_path or not os.path.isfile(src_path):
            return False
        ext = os.path.splitext(src_path)[1].lower()
        if ext not in GAME_IMG_EXTS:
            return False
        # Atalho/plataforma: capa vai p/ streaming_images + registro
        if self.game_is_external(name) or self.game_is_platform(name):
            try:
                dest = os.path.join(IMAGES_DIR, "%s_logo%s"
                                    % (_safe_icon_basename(name), ext))
                copy2(src_path, dest)
            except Exception:
                return False
            try:
                if self.game_is_platform(name):
                    plat = dict(self.settings.get("platform_games") or {})
                    data = dict(plat.get(name, {}))
                    data["cover"] = dest
                    plat[name] = data
                    self.settings["platform_games"] = plat
                else:
                    extg = dict(self.settings.get("external_games") or {})
                    data = dict(extg.get(name, {}))
                    data["cover"] = dest
                    extg[name] = data
                    self.settings["external_games"] = extg
                save_settings(self.settings)
                try:
                    self.logo_path_cache.pop(name, None)
                except Exception:
                    pass
                return True
            except Exception:
                return False
        folder = self.game_folder(name)
        if not folder:
            return False
        try:
            for f in os.listdir(folder):
                if f.lower().startswith("cover") and f.lower().endswith(GAME_IMG_EXTS):
                    os.remove(os.path.join(folder, f))
            copy2(src_path, os.path.join(folder, "cover" + ext))
            return True
        except Exception:
            return False

    def delete_game_folder(self, name):
        folder = self.game_folder(name)
        if not folder:
            return False
        try:
            base = os.path.realpath(GAMES_DIR)
            target = os.path.realpath(folder)
            if os.path.commonpath([base, target]) != base or target == base:
                return False
            shutil.rmtree(target)
            favs = self.settings.get("favorites", [])
            if name in favs:
                favs.remove(name)
                self.settings["favorites"] = favs
                save_settings(self.settings)
            return True
        except Exception:
            return False
