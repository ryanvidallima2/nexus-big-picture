# -*- coding: utf-8 -*-
"""Navegacao, abas e renderizacao base (extraido sem alteracao)."""

import os
import tkinter as tk
import urllib.parse

from .config import (
    Config, TABS, VIEW_MODES, VIEW_MODE_ICONS, view_mode_default,
    save_settings,
)
from .dialogs import _modal_alive, top_modal
from .games import PLATFORM_LABEL
from .i18n import cat_label, t
from .input import _play_nav_tick


class AppViewsMixin:
    """Keybinds, navegacao, foco, abas e renderizacao base."""

    # ===================== KEYBINDS =====================
    def setup_keybinds(self):
        self.root.bind("<Escape>", lambda e: self.go_back())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<F5>", lambda e: self.refresh_ui())
        self.root.bind("<Left>", lambda e: self._nav_keys("left"))
        self.root.bind("<Right>", lambda e: self._nav_keys("right"))
        self.root.bind("<Up>", lambda e: self._nav_keys("up"))
        self.root.bind("<Down>", lambda e: self._nav_keys("down"))
        self.root.bind("<Return>", lambda e: self.select_current())
        self.root.bind("<space>", lambda e: self.select_current())
        self.root.bind("<Control-q>", lambda e: self.toggle_sidebar())
        self.root.bind("<y>", lambda e: self.toggle_sidebar())
        self.root.bind("<Y>", lambda e: self.toggle_sidebar())
        self.root.bind("<x>", lambda e: self.go_to_cards())
        self.root.bind("<X>", lambda e: self.go_to_cards())
        self.root.bind("<n>", lambda e: self.toggle_notif_panel())
        self.root.bind("<N>", lambda e: self.toggle_notif_panel())
        self.root.bind("<FocusIn>", lambda e: self._on_focus_in())
        # Modalidade de entrada: controle x mouse/teclado (teclado virtual
        # so abre quando o foco veio do controle)
        self.root.bind("<Button-1>", lambda e: setattr(self, "using_gamepad", False), add="+")
        self.root.bind("<Key>", lambda e: setattr(self, "using_gamepad", False), add="+")

    # ===================== NAVIGATION =====================
    def _nav_keys(self, direction):
        self._nav(direction)
        self.warp_to_focus()

    def _at_top(self, canvas):
        try:
            return canvas.yview()[0] <= 0.0
        except Exception:
            return True

    def _at_bottom(self, canvas):
        try:
            return canvas.yview()[1] >= 1.0
        except Exception:
            return True

    def _on_mousewheel(self, event):
        if event.delta > 0 and self._at_top(self.canvas):
            return
        if event.delta < 0 and self._at_bottom(self.canvas):
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_global(self, event):
        if not self.sidebar_visible:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_wheel_tree(self, widget, handler):
        """Liga o scroll do mouse no widget E em todos os filhos (o evento
        nao propaga ao pai no tkinter, entao cada um precisa do proprio bind)."""
        try:
            widget.bind("<MouseWheel>", handler)
            for child in widget.winfo_children():
                self._bind_wheel_tree(child, handler)
        except Exception:
            pass

    def _on_sidebar_wheel(self, event):
        try:
            if event.delta > 0 and self._at_top(self.sidebar_canvas):
                return "break"
            if event.delta < 0 and self._at_bottom(self.sidebar_canvas):
                return "break"
            self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def play_tick(self):
        """Blip curto ao trocar de selecao (async; volume 0-100,
        nav_sound desliga; padrao 10). Retorna (ok, erro) p/ diagnostico."""
        try:
            vol = 10
            sonar = True
            if isinstance(self.settings, dict):
                try:
                    vol = int(self.settings.get("sound_volume", 10))
                except Exception:
                    vol = 10
                sonar = bool(self.settings.get("nav_sound", True))
            if not sonar:
                return False, "navegacao desligada"
            if vol <= 0:
                return False, "volume 0"
        except Exception:
            vol = 10
        try:
            return _play_nav_tick(vol)
        except Exception as e:
            return False, str(e)[:120]

    def _nav(self, direction):
        if self.sidebar_visible:
            if direction == "up":
                new_idx = max(0, self.sidebar_menu_index - 1)
            elif direction == "down":
                new_idx = min(len(self.sidebar_items) - 1, self.sidebar_menu_index + 1)
            else:
                return
            if new_idx == self.sidebar_menu_index:
                return  # no limite: para, sem update/scroll/som
            self.sidebar_menu_index = new_idx
            self.update_sidebar_focus()
            self.play_tick()
            return
        if self.nav_level == "form":
            if direction in ("up", "left"):
                self._form_move(-1)
            elif direction in ("down", "right"):
                self._form_move(1)
            else:
                return
            self.play_tick()
            return
        if getattr(self, "flipped", None) is not None and self.nav_level == "items":
            # Verso aberto: setas passeiam nas opcoes (como no dialogo).
            # Com cursor num campo de texto, as setas sao do campo.
            # Se o foco saiu do card virado, desvira e navega normal.
            try:
                import tkinter as _tk
                _f = self.root.focus_get()
                if isinstance(_f, _tk.Entry):
                    return
            except Exception:
                pass
            try:
                w, _n, _g = self.focused_card()
                same = (w is not None and w == self.flipped.get("widget"))
            except Exception:
                same = False
            if same:
                if direction in ("up", "left"):
                    self.flip_opt_move(-1)
                else:
                    self.flip_opt_move(1)
                return
            try:
                self.unflip_card()
            except Exception:
                pass
        if direction == "up":
            if self._dpad_up():
                self.play_tick()
        elif direction == "down":
            if self._dpad_down():
                self.play_tick()
        elif direction == "left":
            if self._dpad_left():
                self.play_tick()
        elif direction == "right":
            if self._dpad_right():
                self.play_tick()

    def _dpad_up(self):
        # Eixo vertical: troca de carrossel (linha). Nunca seleciona titulos/abas.
        # Retorna True se algo mudou; no limite, para (sem update/scroll).
        if self.nav_level == "tabs":
            return False
        sec = self.sections[self.focus_mgr.focused_row]
        if sec["canvas"] is None:
            cols = sec["visible_count"]
            total = len(sec["names"])
            if total > cols:
                new_col = self.focus_mgr.focused_col - cols
                if new_col >= 0:
                    self.focus_mgr.focused_col = new_col
                    self.update_all_focus()
                    return True
        if self.focus_mgr.focused_row > 0:
            self.focus_mgr.focused_row -= 1
            self._clamp_focused_col()
            self.update_all_focus()
            return True
        return False

    def _dpad_down(self):
        # Eixo vertical: troca de carrossel (linha).
        if self.nav_level == "tabs":
            if not self.sections:
                return False
            self.nav_level = "items"
            self.focus_mgr.focused_row = 0
            self.focus_mgr.focused_col = 0
            sec = self.sections[0]
            if sec["canvas"] is not None:
                sec["scroll_offset"] = 0
                self._update_carousel_scroll(sec)
            self.update_all_focus()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        if sec["canvas"] is None:
            cols = sec["visible_count"]
            total = len(sec["names"])
            if total > cols:
                new_col = self.focus_mgr.focused_col + cols
                if new_col < total:
                    self.focus_mgr.focused_col = new_col
                    self.update_all_focus()
                    return True
        if self.focus_mgr.focused_row < len(self.sections) - 1:
            self.focus_mgr.focused_row += 1
            self._clamp_focused_col()
            sec2 = self.sections[self.focus_mgr.focused_row]
            if sec2["canvas"] is not None:
                sec2["scroll_offset"] = 0
                self._update_carousel_scroll(sec2)
            self.update_all_focus()
            return True
        return False

    def _dpad_left(self):
        # Eixo horizontal: troca de card, 1 por 1. Nunca muda de linha/secao.
        if self.nav_level == "tabs":
            if self.focus_tab <= 0:
                return False
            self.focus_tab -= 1
            self.update_tab_highlight()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        col = self.focus_mgr.focused_col
        if col > 0:
            self.focus_mgr.focused_col -= 1
        elif sec["canvas"] is not None and sec["scroll_offset"] > 0:
            sec["scroll_offset"] -= 1
            self._update_carousel_scroll(sec)
        else:
            return False
        self.update_all_focus()
        return True

    def _dpad_right(self):
        # Eixo horizontal: troca de card, 1 por 1. Nunca muda de linha/secao.
        if self.nav_level == "tabs":
            tabs = TABS
            if self.focus_tab >= len(tabs) - 1:
                return False
            self.focus_tab += 1
            self.update_tab_highlight()
            return True
        sec = self.sections[self.focus_mgr.focused_row]
        total = len(sec["names"])
        col = self.focus_mgr.focused_col
        if sec["canvas"] is not None:
            start, end, _ = self._get_visible_range(sec)
            max_vis = end - start
            if col < max_vis - 1 and col < total - 1:
                self.focus_mgr.focused_col += 1
            elif end < total:
                sec["scroll_offset"] += 1
                self._update_carousel_scroll(sec)
            else:
                return False
        else:
            if col < total - 1:
                self.focus_mgr.focused_col += 1
            else:
                return False
        self.update_all_focus()
        return True

    def _clamp_focused_col(self):
        sec = self.sections[self.focus_mgr.focused_row]
        total = len(sec["names"])
        if sec["canvas"] is not None:
            vis = min(sec["visible_count"], total)
            self.focus_mgr.focused_col = min(self.focus_mgr.focused_col, vis - 1)
        else:
            self.focus_mgr.focused_col = min(self.focus_mgr.focused_col, total - 1)

    def _get_visible_range(self, sec):
        offset = sec["scroll_offset"]
        total = len(sec["names"])
        vis = min(sec["visible_count"], total)
        return offset, offset + vis, total

    def _get_sec_total(self, sec):
        return len(sec["names"])

    def select_current(self):
        if _modal_alive(self.open_dialog):
            return
        if self.sidebar_visible:
            if 0 <= self.sidebar_menu_index < len(self.sidebar_items):
                self.sidebar_items[self.sidebar_menu_index][1]()
            return
        if self.nav_level == "form":
            self._form_activate()
            return
        if self.nav_level == "tabs":
            tabs = TABS
            if self.focus_tab < len(tabs):
                self.switch_tab(tabs[self.focus_tab])
        elif self.nav_level == "items":
            w, name, is_game = self.focused_card()
            if w is None:
                return
            try:
                cur = getattr(self, "flipped", None)
                if cur is not None and cur.get("widget") == w:
                    self.flip_opt_activate()
                    return
            except Exception:
                pass
            try:
                self.flip_card(w, name, is_game)
            except Exception:
                pass

    def go_back(self):
        if self.theme_visible:
            self.close_theme_panel()
        elif self.notif_visible:
            self.close_notif_panel()
        elif (getattr(self, "sidepanel", None) is not None
                and self.sidepanel.visible):
            self.close_sidepanel()
        elif self.sidebar_visible:
            self.toggle_sidebar()
        elif hasattr(self, 'qa_visible') and self.qa_visible:
            self.close_qa()
        elif getattr(self, "flipped", None) is not None:
            self.unflip_card()
        elif self.nav_level == "form":
            self.switch_tab(self.current_tab)
        elif self.nav_level == "items":
            self.nav_level = "tabs"
            self.update_all_focus()

    def controller_back(self):
        """Bola no menu principal (nada aberto, ja nas abas) = sair ou nao.
        Em qualquer outro lugar, voltar normal."""
        try:
            if (not self.sidebar_visible
                    and not getattr(self, "notif_visible", False)
                    and not getattr(self, "theme_visible", False)
                    and not (getattr(self, "sidepanel", None) is not None
                             and self.sidepanel.visible)
                    and not getattr(self, "qa_visible", False)
                    and getattr(self, "flipped", None) is None
                    and self.nav_level == "tabs"
                    and top_modal(self) is None
                    and not _modal_alive(self.pad_window)):
                self.confirm_quit()
                return
        except Exception:
            pass
        self.go_back()

    def go_to_cards(self):
        # Botao X do controle: foca direto no primeiro card da aba atual
        if self.sidebar_visible:
            self.toggle_sidebar()
        if hasattr(self, 'qa_visible') and self.qa_visible:
            self.close_qa()
        if not self.sections:
            return
        self.nav_level = "items"
        self.focus_mgr.focused_row = 0
        self.focus_mgr.focused_col = 0
        sec = self.sections[0]
        if sec["canvas"] is not None:
            sec["scroll_offset"] = 0
            self._update_carousel_scroll(sec)
        self.update_all_focus()
        self.warp_to_focus()

    def _update_carousel_scroll(self, sec):
        canvas = sec["canvas"]
        if canvas is None:
            return
        inner = sec["inner_frame"]
        inner.update_idletasks()
        offset = sec["scroll_offset"]
        children = inner.winfo_children()
        if offset < len(children):
            widget = children[offset]
            widget.update_idletasks()
            x = widget.winfo_x()
            scroll_region = canvas.cget("scrollregion")
            if scroll_region:
                total_w = int(scroll_region.split()[2])
                if total_w > 0:
                    canvas.xview_moveto(x / total_w)

    def _scroll_to_section(self, section_idx):
        if section_idx < len(self.sections):
            sec = self.sections[section_idx]
            widget = sec["title_widget"]
            self.canvas.update_idletasks()
            y = widget.winfo_rooty() - self.canvas.winfo_rooty()
            canvas_h = self.canvas.winfo_height()
            total_h = self.scroll_frame.winfo_height()
            if total_h > 0:
                scroll_pos = max(0, (y - canvas_h // 3)) / total_h
                self.canvas.yview_moveto(min(1.0, scroll_pos))

    def _scroll_to_card(self, sec, abs_idx):
        # Grade (ex. aba Todos): rola o canvas principal ate o card focado
        if abs_idx < 0 or abs_idx >= len(sec["widgets"]):
            return
        widget = sec["widgets"][abs_idx]
        self.canvas.update_idletasks()
        widget.update_idletasks()
        canvas_h = self.canvas.winfo_height()
        total_h = self.scroll_frame.winfo_height()
        if total_h <= 0 or canvas_h <= 0 or total_h <= canvas_h:
            return
        wy = widget.winfo_rooty() - self.canvas.winfo_rooty()
        wh = widget.winfo_height()
        try:
            first, _ = self.canvas.yview()
        except:
            return
        margin = 15
        if wy < margin:
            self.canvas.yview_moveto(max(0.0, first + (wy - margin) / total_h))
        elif wy + wh > canvas_h - margin:
            self.canvas.yview_moveto(min(1.0, first + (wy + wh - canvas_h + margin) / total_h))

    def update_all_focus(self):
        self.update_tab_highlight()
        for i, sec in enumerate(self.sections):
            sec["title_widget"].configure(fg=Config.TEXT_PRIMARY)
            sec["line_widget"].configure(width=120)
            for j, w in enumerate(sec["widgets"]):
                if sec["canvas"] is not None:
                    # Carrossel: focused_col e relativo a janela visivel
                    is_focused = (self.nav_level == "items" and i == self.focus_mgr.focused_row
                                  and (j - sec["scroll_offset"]) == self.focus_mgr.focused_col)
                else:
                    is_focused = (self.nav_level == "items" and i == self.focus_mgr.focused_row
                                  and j == self.focus_mgr.focused_col)
                if is_focused:
                    w.configure(bg=Config.BG_CARD_HOVER,
                                highlightbackground=Config.ACCENT, highlightthickness=3)
                else:
                    w.configure(bg=Config.BG_CARD,
                                highlightbackground=Config.BORDER, highlightthickness=1)
        if self.nav_level == "items" and self.focus_mgr.focused_row < len(self.sections):
            sec = self.sections[self.focus_mgr.focused_row]
            if sec["canvas"] is None:
                self._scroll_to_card(sec, self.focus_mgr.focused_col)
            else:
                self._scroll_to_section(self.focus_mgr.focused_row)

    def update_sidebar_focus(self):
        for i, btn in enumerate(self.sidebar_btns):
            if i == self.sidebar_menu_index:
                btn.configure(bg=Config.ACCENT, fg="white")
            else:
                btn.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY)
        if self.sidebar_menu_index < len(self.sidebar_btns):
            btn = self.sidebar_btns[self.sidebar_menu_index]
            self.sidebar_canvas.update_idletasks()
            y = btn.winfo_y()
            h = btn.winfo_height()
            canvas_h = self.sidebar_canvas.winfo_height()
            total_h = self.sidebar_scroll_frame.winfo_height()
            if total_h > canvas_h:
                scroll_pos = max(0, (y - canvas_h // 3)) / total_h
                self.sidebar_canvas.yview_moveto(min(1.0, scroll_pos))

    def switch_tab(self, tab):
        tabs = TABS
        changed = (tab != self.current_tab)
        self.current_tab = tab
        self.focus_mgr.reset()
        self.nav_level = "tabs"
        self.form_focus = []
        self.form_idx = 0
        if tab in tabs:
            self.focus_tab = tabs.index(tab)
        self.render_tab(tab)
        if changed:
            self.play_tick()

    def _reg_form(self, widget, kind, action=None):
        try:
            orig = (widget.cget("bg"), widget.cget("fg"))
        except Exception:
            orig = (None, None)
        self.form_focus.append((widget, kind, action, orig))

    def _paint_form(self):
        for i, (w, kind, _action, orig) in enumerate(self.form_focus):
            try:
                if not w.winfo_exists():
                    continue
                if i == self.form_idx:
                    if kind == "entry":
                        w.configure(highlightbackground=Config.ACCENT_GLOW,
                                    highlightthickness=2)
                    else:
                        w.configure(bg=Config.ACCENT, fg="white")
                else:
                    if kind == "entry":
                        w.configure(highlightbackground=Config.BORDER,
                                    highlightthickness=1)
                    elif orig[0] is not None:
                        w.configure(bg=orig[0], fg=orig[1])
            except Exception:
                pass

    def _form_move(self, d):
        if self.nav_level != "form" or not self.form_focus:
            return
        self.form_idx = (self.form_idx + d) % len(self.form_focus)
        self._paint_form()

    def _form_activate(self):
        if self.nav_level != "form" or not self.form_focus:
            return
        try:
            w, kind, action, _orig = self.form_focus[self.form_idx]
            if not w.winfo_exists():
                return
            if kind == "entry":
                w.focus_set()
            elif callable(action):
                action()
        except Exception:
            pass

    def tab_prev(self):
        tabs = TABS
        idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
        self.switch_tab(tabs[(idx - 1) % len(tabs)])
        self.warp_to_focus()

    def tab_next(self):
        tabs = TABS
        idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
        self.switch_tab(tabs[(idx + 1) % len(tabs)])
        self.warp_to_focus()

    def update_tab_highlight(self):
        tabs = TABS
        for tid, btn in self.nav_buttons.items():
            idx = tabs.index(tid) if tid in tabs else -1
            is_focused = self.nav_level == "tabs" and idx == self.focus_tab
            if tid == self.current_tab:
                btn.configure(bg=Config.ACCENT, fg="white", font=("Segoe UI", 13, "bold"))
            elif is_focused:
                btn.configure(bg=Config.BG_CARD_HOVER, fg=Config.TEXT_PRIMARY, font=("Segoe UI", 13, "bold"))
            else:
                btn.configure(bg=Config.BG_SIDEBAR, fg=Config.TEXT_SECONDARY, font=("Segoe UI", 13))

    # ===================== RENDER =====================
    def render_tab(self, tab):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.all_cards = []
        self.card_widgets = []
        self.sections = []
        self.card_index = {}
        # Cards recriados: verso aberto cai (cfg_keep_flip re-vira depois).
        self.flipped = None
        if tab == "home":
            # Legado: aba Home foi removida, mostra Todos
            tab = "all"
            self.current_tab = "all"
        self.update_tab_highlight()

        if tab == "favorites":
            names = self.settings.get("favorites", [])
            if names:
                self.render_view_bar(tab)
                self.render_names(tab, t("sec_favorites", self.lang), names)
        elif tab == "movies":
            names = [n for n, i in self.get_all_services().items() if i.get("category") == "Filmes"]
            if names:
                self.render_view_bar(tab)
                self.render_names(tab, cat_label("Filmes", self.lang), names)
        elif tab == "music":
            names = [n for n, i in self.get_all_services().items() if i.get("category") == "Musica"]
            if names:
                self.render_view_bar(tab)
                self.render_names(tab, cat_label("Musica", self.lang), names)
        elif tab == "videos":
            names = [n for n, i in self.get_all_services().items() if i.get("category") == "Videos"]
            if names:
                self.render_view_bar(tab)
                self.render_names(tab, cat_label("Videos", self.lang), names)
        elif tab == "games":
            self.render_games()
        else:
            all_names = list(self.get_all_services().keys())
            if all_names:
                self.render_view_bar(tab)
                self.render_names(tab, t("sec_all", self.lang), all_names)

        self.update_all_focus()

    def render_category(self, category):
        all_s = self.get_all_services()
        items = [n for n, info in all_s.items() if info.get("category") == category]
        self.render_section(category, items)

    # ===================== VIEW MODES (Explorer) =====================
    def get_view_mode(self, tab):
        """Modo de exibicao ativo da aba (salvo em view_modes)."""
        try:
            saved = (self.settings.get("view_modes") or {}).get(tab, "")
            if saved in VIEW_MODES:
                return saved
        except Exception:
            pass
        return view_mode_default(tab)

    def set_view_mode(self, tab, mode):
        if mode not in VIEW_MODES:
            return
        try:
            modes = dict(self.settings.get("view_modes") or {})
            modes[tab] = mode
            self.settings["view_modes"] = modes
            save_settings(self.settings)
        except Exception:
            pass
        self.refresh_ui()

    def render_view_bar(self, tab):
        """Botoes Cards | Grade | Lista | Detalhes no topo da aba."""
        cur = self.get_view_mode(tab)
        bar = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        bar.pack(fill="x", padx=30, pady=(20, 0))
        tk.Label(bar, text="\U0001F441", font=("Segoe UI", 13),
                 fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY).pack(side="left", padx=(0, 8))
        for mode in VIEW_MODES:
            active = (mode == cur)
            tk.Button(bar, text="%s %s" % (VIEW_MODE_ICONS.get(mode, ""), t("view_" + mode, self.lang)),
                      font=("Segoe UI", 11, "bold" if active else "normal"),
                      bg=(Config.ACCENT if active else Config.BG_CARD),
                      fg=("white" if active else Config.TEXT_SECONDARY),
                      activebackground=Config.ACCENT_GLOW, activeforeground="white",
                      relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
                      command=lambda m=mode: self.set_view_mode(tab, m)).pack(side="left", padx=(0, 6))
        return bar

    def render_names(self, tab, title, names):
        """Titulo + itens no modo de exibicao ativo da aba."""
        mode = self.get_view_mode(tab)
        if mode == "grid":
            self.render_grid(title, names)
        elif mode in ("list", "details"):
            self.render_list(title, names, details=(mode == "details"))
        else:
            self.render_section(title, names)

    def item_details(self, name):
        """(tipo, detalhe) de cada item p/ o modo Detalhes."""
        try:
            if self.game_is_platform(name):
                data = self.game_platform_data(name)
                label = PLATFORM_LABEL.get(data.get("platform", ""), "")
                return (label, data.get("location", ""))
            if self.game_is_external(name):
                exe = (self.settings.get("external_games") or {}).get(name, {}).get("exe", "")
                return (t("view_type_link", self.lang),
                        os.path.dirname(exe) if exe else "")
            if self.game_folder(name):
                return (t("view_type_folder", self.lang), self.game_folder(name))
        except Exception:
            pass
        try:
            info = self.get_all_services().get(name, {})
            try:
                host = urllib.parse.urlparse(info.get("url", "")).netloc or info.get("url", "")
            except Exception:
                host = info.get("url", "")
            return (cat_label(info.get("category", ""), self.lang), host)
        except Exception:
            pass
        return ("", "")

    def render_list(self, title, names, details=False):
        """Lista (1 coluna) ou Detalhes (colunas Nome/Tipo/Detalhe)."""
        if not names:
            return
        section = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        section.pack(fill="x", padx=30, pady=(20, 5))
        title_lbl = tk.Label(section, text=title, font=("Segoe UI", 20, "bold"),
                 fg=Config.TEXT_PRIMARY, bg=Config.BG_PRIMARY)
        title_lbl.pack(anchor="w")
        line = tk.Frame(section, bg=Config.ACCENT, height=3, width=120)
        line.pack(anchor="w", pady=(5, 15))
        if details:
            hdr = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
            hdr.pack(fill="x", padx=30, pady=(0, 2))
            tk.Label(hdr, text=t("view_col_name", self.lang), font=("Segoe UI", 10, "bold"),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY,
                     width=34, anchor="w").pack(side="left")
            tk.Label(hdr, text=t("view_col_type", self.lang), font=("Segoe UI", 10, "bold"),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY,
                     width=12, anchor="w").pack(side="left", padx=(10, 0))
            tk.Label(hdr, text=t("view_col_detail", self.lang), font=("Segoe UI", 10, "bold"),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_PRIMARY,
                     anchor="w").pack(side="left", padx=(10, 0), fill="x", expand=True)
        list_frame = tk.Frame(self.scroll_frame, bg=Config.BG_PRIMARY)
        list_frame.pack(fill="x", padx=30, pady=(0, 10))
        sec_widgets = []
        for i, name in enumerate(names):
            row = self.create_list_row(list_frame, name, details)
            row.pack(fill="x", pady=2)
            sec_widgets.append(row)
            self.card_index[row] = (len(self.sections), i)
        self.sections.append({
            "title_widget": title_lbl,
            "line_widget": line,
            "canvas": None,
            "inner_frame": list_frame,
            "left_btn": None,
            "right_btn": None,
            "names": list(names),
            "widgets": sec_widgets,
            "scroll_offset": 0,
            "visible_count": 1,
        })

    def create_list_row(self, parent, name, details=False):
        """Linha compacta: miniatura + nome (+ tipo/detalhe)."""
        info = self.get_all_services().get(name, {})
        if not info and (self.game_folder(name) or self.game_is_external(name)
                         or self.game_is_platform(name)):
            info = {"icon": "\U0001F3AE", "category": "Games"}
        icon = info.get("icon", "\U0001F4F0")
        tipo, detalhe = self.item_details(name)
        star = "\u2B50 " if name in self.settings.get("favorites", []) else ""

        row = tk.Frame(parent, bg=Config.BG_CARD, relief="flat",
                       highlightbackground=Config.BORDER, highlightthickness=1,
                       cursor="hand2", height=52)
        row.pack_propagate(False)
        row._flip_tall = False

        mini = self.get_logo(name, size=40)
        if mini:
            thumb = tk.Label(row, image=mini, bg=Config.BG_CARD, cursor="hand2", width=48)
            thumb.image = mini
        else:
            thumb = tk.Label(row, text=icon, font=("Segoe UI Emoji", 20),
                             bg=Config.BG_CARD, fg="white", cursor="hand2", width=3)
        thumb.pack(side="left", padx=(8, 4), pady=4)

        name_lbl = tk.Label(row, text=star + name, font=("Segoe UI", 12, "bold"),
                            fg=Config.TEXT_PRIMARY, bg=Config.BG_CARD, cursor="hand2",
                            width=32, anchor="w")
        name_lbl.pack(side="left", padx=(4, 0))
        if details:
            tk.Label(row, text=tipo, font=("Segoe UI", 11),
                     fg=Config.ACCENT, bg=Config.BG_CARD, cursor="hand2",
                     width=12, anchor="w").pack(side="left", padx=(10, 0))
            tk.Label(row, text=detalhe, font=("Segoe UI", 10),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, cursor="hand2",
                     anchor="w").pack(side="left", padx=(10, 8), fill="x", expand=True)
        else:
            tk.Label(row, text=tipo, font=("Segoe UI", 10),
                     fg=Config.TEXT_SECONDARY, bg=Config.BG_CARD, cursor="hand2",
                     anchor="w").pack(side="left", padx=(10, 8))

        def on_click(e, n=name, c=row):
            self.on_card_click(c, n)

        def on_ctx(e, n=name):
            self.show_context_menu(e, n)

        def on_enter(e, c=row):
            c.configure(bg=Config.BG_CARD_HOVER, highlightbackground=Config.ACCENT, highlightthickness=2)
            self.sync_focus_to_card(c)

        def on_leave(e, c=row):
            c.configure(bg=Config.BG_CARD, highlightbackground=Config.BORDER, highlightthickness=1)

        # Clique/menu em row + filhos (Button-1 nao borbulha no Tk).
        row.bind("<Button-1>", on_click)
        row.bind("<Button-3>", on_ctx)
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        for w in (thumb, name_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Button-3>", on_ctx)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
        return row
