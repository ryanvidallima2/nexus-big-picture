# -*- coding: utf-8 -*-
"""Mapeamento do controle e modo remoto (extraido sem alteracao)."""

import threading
import time
import tkinter as tk

from .audio import audio_get_master, audio_set_master
from .config import Config, save_settings
from .dialogs import _modal_alive
from .i18n import t
from .input import VK_F7, VK_F8, ctrl_tab, tap_key
from .pad import (
    BROWSER_WATCH, DEFAULT_NEXUS_MAP, DEFAULT_REMOTE_MAP, LOGICAL_BUTTONS,
    REMOTE_WATCH, DEFAULT_PAD_SENSITIVITY, DEFAULT_PAD_SCROLL,
    DEFAULT_PAD_DEADZONE, normalize_pad_value,
)
from .paths import BROWSER_PROCS
from .win32 import (
    _top_level_windows, force_borderless_fullscreen, find_window_by_title,
    find_window_by_title_pid, is_window_visible, set_owner_window,
    show_window, ensure_fullscreen_top, kill_process_tree, SW_HIDE, SW_SHOW,
    SW_MAXIMIZE,
)


class AppRemoteMixin:
    """Pad remap/perfis e controle do app/site aberto."""

    def _pad_lookup(self, base_map, settings_key, btn_or_logical):
        try:
            gp = self.gamepad
            if isinstance(btn_or_logical, str):
                logical = btn_or_logical
            elif gp is not None:
                logical = gp.logical_for_raw(btn_or_logical)
            else:
                logical = normalize_pad_value(btn_or_logical)
            merged = dict(base_map)
            merged.update(self.settings.get(settings_key, {}))
            for action, val in merged.items():
                if normalize_pad_value(val) == logical:
                    return action
        except Exception:
            pass
        return None

    def nexus_action_for(self, btn_or_logical):
        return self._pad_lookup(DEFAULT_NEXUS_MAP, "pad_nexus", btn_or_logical)

    def remote_action_for(self, btn_or_logical):
        return self._pad_lookup(DEFAULT_REMOTE_MAP, "pad_remote", btn_or_logical)

    def vol_trigger_enabled(self):
        """Eixo do gatilho so comanda volume se o usuario nao remapeou
        vol_down/vol_up para outros botoes (evita volume duplo)."""
        try:
            merged = dict(DEFAULT_REMOTE_MAP)
            merged.update(self.settings.get("pad_remote", {}))
            return (normalize_pad_value(merged.get("vol_down")) == "l2"
                    and normalize_pad_value(merged.get("vol_up")) == "r2")
        except Exception:
            return True

    def remote_tab(self, prev):
        """LB/RB: no navegador embutido percorre as abas de categoria (F7/F8);
        em apps/navegadores externos troca de aba de verdade (Ctrl+Tab)."""
        try:
            if self.browser_nav_active():
                tap_key(VK_F7 if prev else VK_F8)
            else:
                ctrl_tab(prev=prev)
        except Exception:
            pass

    def pad_sensitivity(self):
        try:
            return min(30.0, max(4.0, float(self.settings.get(
                "pad_sensitivity", DEFAULT_PAD_SENSITIVITY))))
        except Exception:
            return float(DEFAULT_PAD_SENSITIVITY)

    def pad_scroll(self):
        """Encaixes de scroll por segundo com o analogico todo p/ o lado."""
        try:
            return min(20.0, max(2.0, float(self.settings.get(
                "pad_scroll", DEFAULT_PAD_SCROLL))))
        except Exception:
            return float(DEFAULT_PAD_SCROLL)

    def pad_deadzone(self):
        """Zona morta dos analogicos (0.05-0.40). Maior = melhor p/ BT com drift."""
        try:
            return min(0.40, max(0.05, float(self.settings.get(
                "pad_deadzone", DEFAULT_PAD_DEADZONE)) / 100.0))
        except Exception:
            return 0.22

    def pad_devices(self):
        try:
            gp = self.gamepad
            return list(gp.devices) if gp else []
        except Exception:
            return []

    def current_pad_label(self):
        try:
            gp = self.gamepad
            return gp.device_label() if gp else ""
        except Exception:
            return ""

    def current_pad_layout(self):
        try:
            gp = self.gamepad
            return gp.layout if gp else "xbox"
        except Exception:
            return "xbox"

    def select_pad_device(self, pos):
        try:
            gp = self.gamepad
            if gp is None:
                return False
            ok = gp.select_device(pos)
            if ok and _modal_alive(self.pad_window):
                self.pad_window.refresh()
            return ok
        except Exception:
            return False

    # ---------- perfis de mapeamento (3 slots) ----------
    def pad_profile_name(self, slot):
        if slot == 1:
            try:
                return t("pad_profile_default", self.lang)
            except Exception:
                return "Padr\u00E3o"
        try:
            prof = (self.settings.get("pad_profiles", {}) or {}).get(str(slot), {})
            name = (prof.get("name", "") or "").strip()
            if name:
                return name[:18]
        except Exception:
            pass
        try:
            return t("pad_profile_empty", self.lang).replace("{n}", str(slot))
        except Exception:
            return "Perfil %d" % slot

    def pad_profile_snapshot(self):
        try:
            return {
                "nexus": dict(self.settings.get("pad_nexus", {}) or {}),
                "remote": dict(self.settings.get("pad_remote", {}) or {}),
                "sensitivity": self.settings.get("pad_sensitivity", DEFAULT_PAD_SENSITIVITY),
                "scroll": self.settings.get("pad_scroll", DEFAULT_PAD_SCROLL),
                "deadzone": self.settings.get("pad_deadzone", DEFAULT_PAD_DEADZONE),
            }
        except Exception:
            return {"nexus": {}, "remote": {}}

    def save_pad_profile(self, slot):
        """Salva o mapeamento atual no slot 2 ou 3 (o 1 e sempre o padrao)."""
        if slot not in (2, 3):
            return False
        try:
            if self.pad_capture is not None:
                self.cancel_pad_capture()
            profiles = dict(self.settings.get("pad_profiles", {}) or {})
            old = profiles.get(str(slot), {})
            snap = self.pad_profile_snapshot()
            snap["name"] = (old.get("name", "") or "").strip() or None
            profiles[str(slot)] = snap
            self.settings["pad_profiles"] = profiles
            self.settings["pad_profile_active"] = slot
            save_settings(self.settings)
            return True
        except Exception:
            return False

    def rename_pad_profile(self, slot, name):
        if slot not in (2, 3):
            return False
        try:
            profiles = dict(self.settings.get("pad_profiles", {}) or {})
            prof = dict(profiles.get(str(slot), {}))
            prof["name"] = (name or "").strip()[:18]
            profiles[str(slot)] = prof
            self.settings["pad_profiles"] = profiles
            save_settings(self.settings)
            return True
        except Exception:
            return False

    def load_pad_profile(self, slot):
        """Slot 1 = padrao de fabrica; 2/3 = salvos (vazio = padrao)."""
        try:
            if self.pad_capture is not None:
                self.cancel_pad_capture()
            if slot == 1:
                snap = {}
            else:
                snap = ((self.settings.get("pad_profiles", {}) or {}).get(str(slot), {})
                        or {})
            self.settings["pad_nexus"] = dict(snap.get("nexus", {}) or {})
            self.settings["pad_remote"] = dict(snap.get("remote", {}) or {})
            self.settings["pad_sensitivity"] = snap.get("sensitivity", DEFAULT_PAD_SENSITIVITY)
            self.settings["pad_scroll"] = snap.get("scroll", DEFAULT_PAD_SCROLL)
            self.settings["pad_deadzone"] = snap.get("deadzone", DEFAULT_PAD_DEADZONE)
            self.settings["pad_profile_active"] = slot
            save_settings(self.settings)
            self.store_current_device()
            if _modal_alive(self.pad_window):
                self.pad_window.refresh()
            return True
        except Exception:
            return False

    # ---------- perfis por aparelho (cada controle guarda o seu mapa) ----------
    def device_profiles(self):
        try:
            d = self.settings.get("pad_per_device", {})
            return dict(d) if isinstance(d, dict) else {}
        except Exception:
            return {}

    def store_device_profile(self, guid):
        """Guarda o mapa atual como sendo do aparelho guid."""
        if not guid:
            return False
        try:
            snap = self.pad_profile_snapshot()
            profs = self.device_profiles()
            profs[guid] = snap
            self.settings["pad_per_device"] = profs
            save_settings(self.settings)
            return True
        except Exception:
            return False

    def adopt_device_profile(self, prev_guid):
        """Troca de aparelho: guarda o mapa no anterior e aplica o do atual.
        Boot (prev vazio): semeia o slot com o mapa do arquivo. Aparelho
        novo: comeca do padrao de fabrica. Mesmo aparelho: nao faz nada."""
        try:
            gp = self.gamepad
            cur = gp.current_guid() if gp else ""
        except Exception:
            cur = ""
        try:
            if prev_guid and prev_guid != cur:
                self.store_device_profile(prev_guid)
            if not cur or prev_guid == cur:
                return True
            if not prev_guid:
                self.store_device_profile(cur)
                return True
            snap = self.device_profiles().get(cur) or {}
            if snap:
                self.settings["pad_nexus"] = dict(snap.get("nexus", {}) or {})
                self.settings["pad_remote"] = dict(snap.get("remote", {}) or {})
                self.settings["pad_sensitivity"] = snap.get(
                    "sensitivity", DEFAULT_PAD_SENSITIVITY)
                self.settings["pad_scroll"] = snap.get(
                    "scroll", DEFAULT_PAD_SCROLL)
                self.settings["pad_deadzone"] = snap.get(
                    "deadzone", DEFAULT_PAD_DEADZONE)
            else:
                self.settings["pad_nexus"] = {}
                self.settings["pad_remote"] = {}
                self.settings["pad_sensitivity"] = DEFAULT_PAD_SENSITIVITY
                self.settings["pad_scroll"] = DEFAULT_PAD_SCROLL
                self.settings["pad_deadzone"] = DEFAULT_PAD_DEADZONE
            save_settings(self.settings)
            return True
        except Exception:
            return False

    def store_current_device(self):
        """Guarda o mapa atual no aparelho anexado (pos-remap/sliders)."""
        try:
            gp = self.gamepad
            return self.store_device_profile(gp.current_guid() if gp else "")
        except Exception:
            return False

    def default_volume(self):
        """Volume padrao 0-100 p/ tudo que abre (padrao 70)."""
        try:
            return max(0, min(100, int(self.settings.get("sound_default", 70))))
        except Exception:
            return 70

    def _apply_default_volume(self):
        """Ao abrir app/site: guarda o atual e poe o padrao. True se aplicou."""
        try:
            cur = audio_get_master()
            if cur is not None:
                self._pre_remote_vol = cur
        except Exception:
            pass
        try:
            return bool(audio_set_master(self.default_volume() / 100.0))
        except Exception:
            return False

    def _restore_pre_volume(self):
        """Ao sair do remoto: volta o volume de antes (se guardado)."""
        try:
            pre = getattr(self, "_pre_remote_vol", None)
            if pre is None:
                return False
            self._pre_remote_vol = None
            return bool(audio_set_master(pre))
        except Exception:
            return False

    def start_pad_capture(self, section, action):
        self.pad_capture = {"section": section, "action": action}
        if self.pad_window is not None:
            self.pad_window.on_capture_start()

    def cancel_pad_capture(self):
        self.pad_capture = None
        if self.pad_window is not None:
            self.pad_window.on_capture_end()

    def finish_pad_capture(self, btn_or_logical):
        cap = self.pad_capture
        if not cap:
            return
        self.pad_capture = None
        section, action = cap["section"], cap["action"]
        key = "pad_nexus" if section == "nexus" else "pad_remote"
        base = DEFAULT_NEXUS_MAP if section == "nexus" else DEFAULT_REMOTE_MAP
        try:
            logical = (btn_or_logical if isinstance(btn_or_logical, str)
                       else normalize_pad_value(btn_or_logical))
            cur = dict(base)
            cur.update(self.settings.get(key, {}))
            for a, b in list(cur.items()):
                if a != action and normalize_pad_value(b) == logical:
                    old = normalize_pad_value(cur.get(action))
                    if old in LOGICAL_BUTTONS or str(old).startswith("raw"):
                        cur[a] = old  # troca: o dono antigo fica com o botao livre
                    else:
                        del cur[a]
            cur[action] = logical
            self.settings[key] = cur
            save_settings(self.settings)
            self.store_current_device()
        except Exception:
            pass
        if self.pad_window is not None:
            # Atualiza na hora: sem isso o selo mostra o botao antigo
            # ate qualquer outro refresh (parecia "nao salvou").
            try:
                self.pad_window.refresh()
            except Exception:
                try:
                    self.pad_window.on_capture_end()
                except Exception:
                    pass

    def enter_remote_mode(self, service, watch=None):
        """O controle passa a comandar o app/site aberto. So com controle ligado."""
        try:
            gp = self.gamepad
            if not gp or not gp.running:
                return
            try:
                self._pre_remote = {
                    "fullscreen": bool(self.root.attributes("-fullscreen")),
                    "zoomed": self.root.state() == "zoomed",
                }
            except Exception:
                self._pre_remote = {"fullscreen": False, "zoomed": False}
            gp.remote_active = True
            gp.remote_service = service
            gp.remote_watch_list = list(watch) if watch else list(REMOTE_WATCH.get(service, []))
            gp.remote_wheel_acc = [0.0, 0.0]
            gp.remote_watch_seen = False
            gp.remote_watch_missed = 0
            gp.remote_watch_count = 0
            gp.remote_hwnd = None
            gp.remote_trig_rest = None
            gp.remote_trig_samples = []
            gp.remote_trig_state = {}
            gp.remote_enter_time = time.time()
            gp.remote_off = [0.0, 0.0, 0.0, 0.0]
            gp.remote_cal = []
            gp.remote_kb_time = 0.0
            gp.hat_debounce.clear()
            gp.prev_buttons.clear()
            try:
                self._apply_default_volume()
            except Exception:
                pass
            self.root.iconify()
        except Exception:
            pass

    def exit_remote_mode(self):
        # O navegador embutido e parte do Nexus: fecha junto (Back+Start
        # ou retorno). Apps externos (Spotify etc.) continuam abertos.
        try:
            self.browser_hwnd = None
        except Exception:
            pass
        try:
            closing = getattr(self, "_browser_closing", None)
            if closing is None:
                closing = self._browser_closing = set()
        except Exception:
            closing = None
        for proc in list(BROWSER_PROCS):
            try:
                if proc.poll() is None:
                    if closing is not None:
                        closing.add(proc)
                    kill_process_tree(proc)
            except Exception:
                pass
            try:
                BROWSER_PROCS.remove(proc)
            except Exception:
                pass
        try:
            self.browser_remote = None
        except Exception:
            pass
        try:
            gp = self.gamepad
            if gp:
                gp.remote_active = False
                gp.remote_service = None
                gp.remote_wheel_acc = [0.0, 0.0]
                gp.hat_debounce.clear()
                gp.prev_buttons.clear()
        except Exception:
            pass
        try:
            self._restore_pre_volume()
        except Exception:
            pass
        try:
            pre = getattr(self, "_pre_remote", None) or {}
            self.root.deiconify()
            if pre.get("fullscreen"):
                try:
                    self.root.attributes("-fullscreen", True)
                except Exception:
                    pass
            else:
                # Volta sempre maximizada (nunca minimizada nem janela pequena)
                try:
                    self.root.state("zoomed")
                except Exception:
                    pass
            self.root.lift()
            self.root.update_idletasks()
            try:
                self.root.focus_force()
            except Exception:
                pass
        except Exception:
            pass

    def nexus_hwnd(self):
        try:
            return self.root.winfo_id()
        except Exception:
            return None

    def show_transition_splash(self, service):
        """Tela preta 'Nexus - servico' na transicao (efeito app unico)."""
        try:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.configure(bg="#000000")
            w, h = 520, 220
            win.update_idletasks()
            try:
                x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
            except Exception:
                x, y = 200, 150
            win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
            tk.Label(win, text="\u25C6 %s" % service, font=("Segoe UI", 24, "bold"),
                     fg=Config.ACCENT, bg="#000000").pack(expand=True)
            tk.Label(win, text=t("dlg_opening_nexus", self.lang), font=("Segoe UI", 13),
                     fg=Config.TEXT_SECONDARY, bg="#000000").pack(pady=(0, 24))
            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass
            return win
        except Exception:
            return None

    def enter_site_remote(self, proc, service, splash, born):
        try:
            if splash is not None:
                splash.destroy()
        except Exception:
            pass
        try:
            alive = proc.poll() is None
        except Exception:
            alive = False
        if alive:
            self.enter_remote_mode(service, watch=[])
            self.browser_remote = service
            self.monitor_browser_process(proc, service)
            try:
                self.root.after(800, lambda: self._own_browser_tick(
                    proc, service, 0))
            except Exception:
                pass
        else:
            try:
                self.opener.open_content(service)
            except Exception:
                pass
            self.enter_remote_mode(service, watch=BROWSER_WATCH)

    def _own_browser_tick(self, proc, service, tries=0):
        """Torna o navegador owned do Nexus (1 aba no Alt+Tab, minimiza e
        restaura junto). Poll: a janela demora ~1s p/ aparecer."""
        try:
            alive = proc.poll() is None
        except Exception:
            alive = False
        if not alive:
            return
        try:
            if getattr(self, "browser_remote", None) != service:
                return
            if getattr(self, "browser_hwnd", None):
                return
        except Exception:
            return
        hwnd = None
        try:
            pid = getattr(proc, "pid", None)
        except Exception:
            pid = None
        if pid:
            hwnd = find_window_by_title_pid("Nexus - %s" % service, pid)
        if not hwnd:
            hwnd = find_window_by_title("Nexus - %s" % service)
        if hwnd:
            # Dono tem que ser top-level: winfo_id e o filho interno, o
            # top-level de verdade e o wm_frame() (hex) ou o pai do winfo_id.
            root_hw = None
            try:
                root_hw = int(self.root.wm_frame(), 16)
            except Exception:
                root_hw = None
            if not root_hw:
                try:
                    import ctypes as _ct
                    _get_parent = _ct.windll.user32.GetParent
                    _get_parent.argtypes = [_ct.c_void_p]
                    _get_parent.restype = _ct.c_void_p
                    _outer = _get_parent(int(self.root.winfo_id()))
                    if _outer:
                        root_hw = int(_outer)
                except Exception:
                    root_hw = None
            if root_hw:
                try:
                    if set_owner_window(hwnd, root_hw):
                        self.browser_hwnd = hwnd
                        try:
                            show_window(hwnd, SW_MAXIMIZE)
                        except Exception:
                            pass
                        try:
                            ensure_fullscreen_top(hwnd)
                        except Exception:
                            pass
                        try:
                            self.root.after(
                                500, self._browser_visibility_tick)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
        try:
            self.root.after(500, lambda: self._own_browser_tick(
                proc, service, tries + 1))
        except Exception:
            pass

    def _browser_visibility_tick(self):
        """Sincronia Nexus <-> navegador owned (poll 500ms).
        Root minimizou -> esconde o browser; root restaurou -> reexibe.
        Por borda: o proprio enter ja deixa o root minimizado, sem
        fingir acao do usuario. Map/Unmap/FocusIn nao chegam aqui."""
        try:
            hwnd = getattr(self, 'browser_hwnd', None)
            if not hwnd:
                return
            try:
                alive = False
                for proc in list(BROWSER_PROCS):
                    try:
                        if proc.poll() is None:
                            alive = True
                            break
                    except Exception:
                        continue
                if not alive:
                    try:
                        self.browser_hwnd = None
                    except Exception:
                        pass
                    return
            except Exception:
                return
            try:
                iconic = (self.root.state() == 'iconic')
            except Exception:
                return
            prev = getattr(self, '_browser_root_was_icon', None)
            self._browser_root_was_icon = iconic
            if prev is None or prev == iconic:
                pass
            elif iconic:
                if is_window_visible(hwnd):
                    show_window(hwnd, SW_HIDE)
            else:
                if not is_window_visible(hwnd):
                    show_window(hwnd, SW_SHOW)
        except Exception:
            pass
        try:
            if getattr(self, 'browser_hwnd', None):
                self.root.after(500, self._browser_visibility_tick)
        except Exception:
            pass


    def borderless_new_app(self, before, tries=0):
        """Converte a janela nova do app externo p/ fullscreen sem bordas."""
        try:
            gp = self.gamepad
            if not gp or not gp.remote_active:
                return
        except Exception:
            return
        try:
            before_set = set(before)
            for hwnd, _pid, _title in _top_level_windows():
                if hwnd not in before_set:
                    if force_borderless_fullscreen(hwnd, self.nexus_hwnd()):
                        try:
                            gp.remote_hwnd = hwnd  # vigia rapida: volta em ~0,5s
                            gp.remote_watch_seen = True
                            gp.remote_watch_missed = 0
                        except Exception:
                            pass
                        return
        except Exception:
            pass
        if tries < 4:
            try:
                self.root.after(2500, lambda: self.borderless_new_app(before, tries + 1))
            except Exception:
                pass

    def browser_nav_active(self):
        """Remoto comandando o navegador embutido (modo console nos quadros)."""
        try:
            gp = self.gamepad
            return bool(gp and gp.remote_active
                        and getattr(self, "browser_remote", None)
                        and any(p.poll() is None for p in BROWSER_PROCS))
        except Exception:
            return False

    def monitor_browser_process(self, proc, service):
        """Sai do remoto quando o navegador embutido fechar. Se ele morrer
        rapido (<5s, ex. WebView2 indisponivel), cai para o navegador externo."""
        born = time.time()

        def _watch():
            # Rearma o wait em fatias: senao, aos 6000s o timeout estoura com
            # o browser ainda vivo e o _browser_closed derruba o remoto do nada.
            while True:
                try:
                    proc.wait(timeout=600)
                except Exception:
                    pass
                try:
                    if proc.poll() is None:
                        continue
                except Exception:
                    pass
                break
            try:
                self.root.after(0, self._browser_closed, proc, service, born)
            except Exception:
                pass

        threading.Thread(target=_watch, daemon=True).start()

    def _browser_closed(self, proc, service, born):
        try:
            if proc in BROWSER_PROCS:
                BROWSER_PROCS.remove(proc)
        except Exception:
            pass
        try:
            closing = getattr(self, "_browser_closing", None) or set()
            intentional = proc in closing
            if intentional:
                closing.discard(proc)
        except Exception:
            intentional = False
        try:
            if getattr(self, "browser_remote", None) == service:
                self.browser_remote = None
            try:
                self.browser_hwnd = None
            except Exception:
                pass
        except Exception:
            pass
        try:
            elapsed = time.time() - born
        except Exception:
            elapsed = 999.0
        gp = getattr(self, "gamepad", None)
        still_remote = bool(gp and gp.remote_active
                            and gp.remote_service == service)
        try:
            rc = proc.poll()
        except Exception:
            rc = None
        # Fallback externo so em morte rapida ANORMAL (crash na abertura,
        # ex. WebView2 indisponivel): saida limpa (codigo 0), proc ainda
        # vivo ou morte pedida pelo Nexus (Back+Start/quit) nao reabrem nada.
        if elapsed < 5.0 and not intentional and rc not in (None, 0):
            try:
                self.opener.open_content(service)
            except Exception:
                pass
            if still_remote:
                try:
                    gp.remote_watch_list = list(BROWSER_WATCH)
                    gp.remote_enter_time = time.time()
                except Exception:
                    pass
            else:
                self.enter_remote_mode(service, watch=BROWSER_WATCH)
            return
        if still_remote:
            self.exit_remote_mode()

    def _on_focus_in(self):
        # Usuario voltou ao Nexus (Alt+Tab/clique): sai do modo remoto.
        # Ignora o foco dos primeiros 2s (restos da troca dialogo->app).
        # EXCECAO: voltou de um minimize junto (navegador owned escondido).
        # Ai reexibe o navegador em vez de matar a sessao.
        try:
            gp = self.gamepad
            if gp and gp.remote_active:
                if time.time() - getattr(gp, "remote_enter_time", 0) < 2.0:
                    return
                try:
                    if getattr(self, "browser_remote", None) is not None:
                        hwnd = getattr(self, "browser_hwnd", None)
                        if hwnd and not is_window_visible(hwnd):
                            alive = False
                            for proc in list(BROWSER_PROCS):
                                try:
                                    if proc.poll() is None:
                                        alive = True
                                        break
                                except Exception:
                                    continue
                            if alive:
                                show_window(hwnd, SW_SHOW)
                                return
                except Exception:
                    pass
                self.exit_remote_mode()
        except Exception:
            pass
