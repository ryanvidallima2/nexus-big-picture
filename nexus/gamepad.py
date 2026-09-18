# -*- coding: utf-8 -*-
"""Gamepad universal via pygame (extraido sem alteracao)."""

import re
import subprocess
import threading
import time

from .config import save_settings
from .dialogs import (
    NexusTextDialog, NexusMenuWindow,
    _modal_alive, top_modal,
)
from .i18n import t
from .input import (
    VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_RETURN, VK_ESCAPE, VK_SPACE,
    VK_F, VK_VOL_DOWN, VK_VOL_UP, VK_MEDIA_NEXT, VK_MEDIA_PREV,
    VK_MEDIA_PLAY_PAUSE, _debug_log, focused_is_text_field, mouse_click,
    mouse_move, mouse_wheel, remote_button_allowed, stick_response, tap_key,
)
from .keyboard import NexusKeyboard
from .pad import (
    REMOTE_WATCH, XBOX_RAW, PAD_LAYOUT_LABEL, detect_pad_layout,
    parse_sdl_mapping, DEFAULT_PAD_SENSITIVITY, DEFAULT_PAD_SCROLL,
)
from .win32 import _hwnd_alive

try:
    import pygame
    import pygame.joystick
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# ===================== GAMEPAD =====================
class GamepadManager:
    def __init__(self, app):
        self.app = app
        self.joystick = None
        self.controller = None  # pygame._sdl2.controller (mapeamento SDL)
        self.devices = []  # [{index, name, guid, layout}]
        self.active_index = 0
        self.logical_to_raw = dict(XBOX_RAW)
        self.raw_to_logical = {v: k for k, v in XBOX_RAW.items()}
        self.dpad_sources = []  # [('hat', idx) ou ('btn', (r...))] do D-pad
        self.running = False
        self.prev_buttons = {}
        self.prev_logical = {}
        self.hat_prev = (0, 0)
        self.hat_debounce = {}
        self.stick_nav_dir = (0, 0)
        self.stick_nav_next = 0.0
        self._poll_ticks = 0
        self._last_count = -1
        # Modo remoto: controle comanda o app aberto em vez do Nexus
        self.remote_active = False
        self.remote_service = None
        self.remote_wheel_acc = [0.0, 0.0]
        self.remote_watch_seen = False
        self.remote_watch_missed = 0
        self.remote_watch_count = 0
        self.remote_watch_list = []
        self.remote_hwnd = None
        self.remote_trig_rest = None
        self.remote_trig_samples = []
        self.remote_trig_state = {}
        self.browser_nav_dir = (0, 0)
        self.browser_nav_next = 0.0
        self.remote_enter_time = 0.0
        self.remote_off = [0.0, 0.0, 0.0, 0.0]
        self.remote_cal = []
        self.remote_kb_time = 0.0
        if PYGAME_AVAILABLE:
            try:
                pygame.init()
                pygame.joystick.init()
                self.running = True
                self.refresh_devices()
                self.app.root.after(50, self.poll)
            except:
                pass

    # ---------- dispositivos ----------
    def refresh_devices(self):
        """Re-enumera controles (hot-plug). Mantem o escolhido ou o salvo."""
        try:
            prev_guid = self.current_guid()
        except Exception:
            prev_guid = ""
        lst = []
        try:
            for i in range(pygame.joystick.get_count()):
                try:
                    js = pygame.joystick.Joystick(i)
                    name = js.get_name()
                except Exception:
                    continue
                try:
                    guid = js.get_guid()
                except Exception:
                    guid = ""
                lst.append({"index": i, "name": name or "Controle %d" % (i + 1),
                            "guid": guid or "",
                            "layout": detect_pad_layout(name)})
        except Exception:
            pass
        self.devices = lst
        want_guid = ""
        try:
            want_guid = self.app.settings.get("pad_device_guid", "") or ""
        except Exception:
            pass
        pick = 0
        if want_guid:
            for pos, d in enumerate(lst):
                if d["guid"] == want_guid:
                    pick = pos
                    break
        if self.joystick is not None:
            try:
                cur_name = self.joystick.get_name()
                for pos, d in enumerate(lst):
                    if d["name"] == cur_name and (not want_guid or d["guid"] == want_guid):
                        pick = pos
                        break
            except Exception:
                pass
        if lst:
            self.attach(lst[min(pick, len(lst) - 1)]["index"])
        else:
            self._detach()
        try:
            self.app.adopt_device_profile(prev_guid)
        except Exception:
            pass

    def _detach(self):
        try:
            if self.joystick is not None:
                self.joystick.quit()
        except Exception:
            pass
        self.joystick = None
        self.controller = None
        self.logical_to_raw = dict(XBOX_RAW)
        self.raw_to_logical = {v: k for k, v in XBOX_RAW.items()}
        self.dpad_sources = []
        self.prev_buttons = {}
        self.prev_logical = {}

    def attach(self, index):
        """Troca para o controle `index` (indice pygame)."""
        self._detach()
        try:
            js = pygame.joystick.Joystick(index)
            js.init()
        except Exception:
            return False
        self.joystick = js
        self.active_index = index
        table = parse_sdl_mapping(self._sdl_mapping(js))
        if table:
            self.logical_to_raw = table
            self.raw_to_logical = {v: k for k, v in table.items()}
        try:
            name = js.get_name() or ""
        except Exception:
            name = ""
        if detect_pad_layout(name) == "playstation":
            # DS4/DualSense: L2/R2 digitais (raw 6/7) alem dos eixos.
            # So preenche o que o SDL nao mapeou (nunca rouba botao real).
            for _log, _raw in (("l2", 6), ("r2", 7)):
                if _log in self.logical_to_raw or _raw in self.raw_to_logical:
                    continue
                try:
                    if js.get_numbuttons() > _raw:
                        self.logical_to_raw[_log] = _raw
                        self.raw_to_logical[_raw] = _log
                except Exception:
                    pass
        self.dpad_sources = self._dpad_sources(js)
        self.prev_buttons = {}
        self.prev_logical = {}
        self.remote_cal = []
        self.remote_off = [0.0, 0.0, 0.0, 0.0]
        return True

    @staticmethod
    def _sdl_mapping(js):
        try:
            from pygame._sdl2 import controller as _ctl
            try:
                _ctl.init()  # subsistema gamecontroller (pygame.init nao cobre)
            except Exception:
                pass
            ctl = _ctl.Controller.from_joystick(js)
            return ctl.get_mapping()
        except Exception:
            return {}

    def _dpad_sources(self, js):
        """De onde ler o D-pad: botoes ou hat (varia por controle)."""
        try:
            from pygame._sdl2 import controller as _ctl
            try:
                _ctl.init()
            except Exception:
                pass
            ctl = _ctl.Controller.from_joystick(js)
            mapping = ctl.get_mapping() or {}
            btns = {}
            hat = None
            for key in ("dpup", "dpdown", "dpleft", "dpright"):
                tgt = str(mapping.get(key, "")).strip().lower()
                m = re.match(r"b(\d+)$", tgt)
                if m:
                    btns[key] = int(m.group(1))
                    continue
                m = re.match(r"h(\d+)\.(\d+)$", tgt)
                if m:
                    hat = int(m.group(1))
            if len(btns) == 4:
                return [("btn", (btns["dpleft"], btns["dpright"],
                                 btns["dpup"], btns["dpdown"]))]
            if hat is not None:
                return [("hat", hat)]
        except Exception:
            pass
        return [("hat", 0)]

    def select_device(self, pos):
        """Escolhe o controle pela posicao na lista. Persiste por GUID."""
        if not self.devices or pos < 0 or pos >= len(self.devices):
            return False
        try:
            prev_guid = self.current_guid()
        except Exception:
            prev_guid = ""
        d = self.devices[pos]
        if not self.attach(d["index"]):
            return False
        try:
            self.app.settings["pad_device_guid"] = d["guid"]
            save_settings(self.app.settings)
        except Exception:
            pass
        try:
            self.app.adopt_device_profile(prev_guid)
        except Exception:
            pass
        return True

    @property
    def layout(self):
        if not self.devices:
            return "xbox"
        for d in self.devices:
            try:
                if self.joystick is not None and d["name"] == self.joystick.get_name():
                    return d["layout"]
            except Exception:
                pass
        return self.devices[0]["layout"] if self.devices else "xbox"

    def device_label(self):
        if self.joystick is None or not self.devices:
            return ""
        try:
            name = self.joystick.get_name()
        except Exception:
            return ""
        tag = PAD_LAYOUT_LABEL.get(self.layout, "")
        return "%s (%s)" % (name, tag) if tag else name

    def current_guid(self):
        """GUID do aparelho anexado agora ("" se nenhum)."""
        try:
            if self.joystick is None:
                return ""
            name = self.joystick.get_name()
            for d in self.devices:
                if d.get("name") == name:
                    return d.get("guid", "") or ""
        except Exception:
            pass
        return ""

    def connection_info(self):
        """'Cabo' se o pygame reporta wired; senao nivel de bateria."""
        if self.joystick is None:
            return ""
        try:
            power = self.joystick.get_power_level()
        except Exception:
            return ""
        mapping = {"wired": "pad_conn_wired", "empty": "pad_batt_empty",
                   "low": "pad_batt_low", "medium": "pad_batt_mid",
                   "full": "pad_batt_full", "max": "pad_batt_full"}
        key = mapping.get(str(power).lower())
        if not key:
            return ""
        try:
            return t(key, self.app.lang)
        except Exception:
            return ""

    # ---------- leitura logica ----------
    def logical_for_raw(self, raw):
        return self.raw_to_logical.get(raw, "raw%d" % raw)

    def raw_for_logical(self, logical):
        if logical in self.logical_to_raw:
            return self.logical_to_raw[logical]
        m = re.match(r"raw(\d+)$", str(logical))
        if m:
            return int(m.group(1))
        return XBOX_RAW.get(logical)

    def _pressed_raw(self):
        """Conjunto de indices raw pressionados (qualquer controle)."""
        out = set()
        js = self.joystick
        if js is None:
            return out
        try:
            n = js.get_numbuttons()
        except Exception:
            return out
        for i in range(n):
            try:
                if js.get_button(i):
                    out.add(i)
            except Exception:
                pass
        return out

    @staticmethod
    def _debug_cursor_pos():
        """Posicao atual do cursor p/ diagnostico (sem falhar)."""
        try:
            import ctypes

            class _PT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = _PT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return (pt.x, pt.y)
        except Exception:
            pass
        return None

    def pressed_logical(self):
        return {self.logical_for_raw(i) for i in self._pressed_raw()}

    def read_dpad(self):
        """D-pad como (x, y): funciona via hat ou via botoes."""
        js = self.joystick
        if js is None:
            return (0, 0)
        for kind, ref in self.dpad_sources or [("hat", 0)]:
            try:
                if kind == "hat":
                    if js.get_numhats() > ref:
                        h = js.get_hat(ref)
                        if h != (0, 0):
                            return (h[0], h[1])
                else:
                    left, right, up, down = ref
                    x = (1 if js.get_button(right) else 0) - (1 if js.get_button(left) else 0)
                    y = (1 if js.get_button(up) else 0) - (1 if js.get_button(down) else 0)
                    if x or y:
                        return (x, y)
            except Exception:
                pass
        return (0, 0)

    def _maybe_hotplug(self):
        try:
            count = pygame.joystick.get_count()
        except Exception:
            return
        if count != self._last_count:
            self._last_count = count
            try:
                alive = self.joystick is not None and self.joystick.get_init()
            except Exception:
                alive = False
            if count == 0 or not alive:
                self.refresh_devices()
                try:
                    if _modal_alive(self.app.pad_window):
                        self.app.pad_window.refresh_device_bar()
                except Exception:
                    pass

    def _stick_axes(self):
        """Eixos (lx, ly, rx, ry) com seguranca para qualquer controle."""
        js = self.joystick
        if js is None:
            return 0.0, 0.0, 0.0, 0.0
        try:
            na = js.get_numaxes()
            lx = js.get_axis(0) if na > 0 else 0.0
            ly = js.get_axis(1) if na > 1 else 0.0
            if na >= 4:
                rx, ry = js.get_axis(2), js.get_axis(3)
            else:
                rx = ry = 0.0
        except Exception:
            lx = ly = rx = ry = 0.0
        return lx, ly, rx, ry

    def _menu_deadzone(self):
        try:
            return max(0.45, float(self.app.pad_deadzone()))
        except Exception:
            return 0.45

    def _stick_nav_dir(self):
        """Direcao do analogico esquerdo p/ navegar nos menus (ou (0,0))."""
        lx, ly, _rx, _ry = self._stick_axes()
        dz = self._menu_deadzone()
        if abs(lx) < dz and abs(ly) < dz:
            return (0, 0)
        if abs(lx) >= abs(ly):
            return (1 if lx > 0 else -1, 0)
        return (0, -1 if ly > 0 else 1)

    def _stick_nav_action(self, ndir):
        """Mesmos alvos do D-pad: dialogos, janela de controles e cards."""
        top = top_modal(self.app)
        if isinstance(top, NexusMenuWindow):
            top.on_hat(ndir)
        elif isinstance(top, NexusKeyboard):
            top.on_hat(ndir)
        elif isinstance(top, NexusTextDialog):
            pass
        else:
            pw = self.app.pad_window
            if _modal_alive(pw) and self.app.pad_capture is None:
                if ndir == (0, 1):
                    pw.move_focus(-1)
                elif ndir == (0, -1):
                    pw.move_focus(1)
                else:
                    pw.sens_or_move(ndir)
            elif ndir == (0, 1):
                self.app._nav("up")
                self.app.warp_to_focus()
            elif ndir == (0, -1):
                self.app._nav("down")
                self.app.warp_to_focus()
            elif ndir == (-1, 0):
                self.app._nav("left")
                self.app.warp_to_focus()
            elif ndir == (1, 0):
                self.app._nav("right")
                self.app.warp_to_focus()

    def _poll_menu_sticks(self):
        """Analogicos nos menus: esquerdo navega (com repeticao),
        direito move o mouse como no modo remoto."""
        try:
            dz = float(self.app.pad_deadzone())
        except Exception:
            dz = 0.22
        lx, ly, rx, ry = self._stick_axes()
        now = time.time()
        ndir = (0, 0)
        if abs(lx) >= self._menu_deadzone() or abs(ly) >= self._menu_deadzone():
            if abs(lx) >= abs(ly):
                ndir = (1 if lx > 0 else -1, 0)
            else:
                ndir = (0, -1 if ly > 0 else 1)
        if ndir != (0, 0):
            if ndir != self.stick_nav_dir:
                self.stick_nav_dir = ndir
                self.stick_nav_next = now
            if now >= self.stick_nav_next:
                self.stick_nav_next = now + 0.22
                self._stick_nav_action(ndir)
        else:
            self.stick_nav_dir = (0, 0)
        nx = stick_response(rx, deadzone=dz)
        ny = stick_response(ry, deadzone=dz)
        if nx != 0.0 or ny != 0.0:
            try:
                sens = float(self.app.pad_sensitivity())
            except Exception:
                sens = float(DEFAULT_PAD_SENSITIVITY)
            mouse_move(sens * nx, sens * ny)

    def poll(self):
        if not self.running:
            return
        try:
            self._poll_ticks += 1
            for ev in pygame.event.get():
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._maybe_hotplug()
                    break
            if self._poll_ticks % 60 == 0:
                self._maybe_hotplug()
        except Exception:
            pass
        if not self.joystick:
            self.app.root.after(500, self.poll)
            return
        if self.remote_active:
            self._poll_remote()
            self.app.root.after(16, self.poll)
            return
        try:
            hat = self.read_dpad()
            now = time.time()
            if hat != (0, 0):
                if hat not in self.hat_debounce or (now - self.hat_debounce[hat]) > 0.15:
                    self.hat_debounce[hat] = now
                    self.app.using_gamepad = True
                    top = top_modal(self.app)
                    if isinstance(top, NexusMenuWindow):
                        top.on_hat(hat)
                    elif isinstance(top, NexusKeyboard):
                        top.on_hat(hat)
                    elif isinstance(top, NexusTextDialog):
                        pass
                    else:
                        pw = self.app.pad_window
                        if (_modal_alive(pw)
                                and self.app.pad_capture is None):
                            if hat == (0, 1):
                                pw.move_focus(-1)
                            elif hat == (0, -1):
                                pw.move_focus(1)
                            else:
                                pw.sens_or_move(hat)
                        elif getattr(self.app, "theme_visible", False):
                            self.app.theme_move(hat)
                        elif (getattr(self.app, "sidepanel", None) is not None
                                and self.app.sidepanel.visible
                                and self.app.nav_level != "form"):
                            self.app.sidepanel.on_hat(hat)
                        elif hat == (0, 1):
                            self.app._nav("up")
                            self.app.warp_to_focus()
                        elif hat == (0, -1):
                            self.app._nav("down")
                            self.app.warp_to_focus()
                        elif hat == (-1, 0):
                            self.app._nav("left")
                            self.app.warp_to_focus()
                        elif hat == (1, 0):
                            self.app._nav("right")
                            self.app.warp_to_focus()
            else:
                self.hat_debounce.clear()

            self._poll_menu_sticks()

            pressed = self._pressed_raw()
            for old_id in list(self.prev_buttons):
                if old_id not in pressed:
                    self.prev_buttons[old_id] = False
            for btn_id in sorted(pressed):
                if self.prev_buttons.get(btn_id, False):
                    continue
                self.prev_buttons[btn_id] = True
                self.app.using_gamepad = True
                logical = self.logical_for_raw(btn_id)
                is_confirm = (logical == "south")
                is_cancel = (logical == "east")
                top = top_modal(self.app)
                if isinstance(top, (NexusMenuWindow, NexusTextDialog)):
                    if is_confirm:
                        top.confirm()
                    elif is_cancel:
                        top.close()
                elif isinstance(top, NexusKeyboard):
                    if is_confirm:
                        top.press_focused()
                    elif is_cancel:
                        top.close()
                elif self.app.pad_capture is not None:
                    if is_cancel:
                        self.app.cancel_pad_capture()
                    else:
                        self.app.finish_pad_capture(logical)
                elif getattr(self.app, "theme_visible", False):
                    self.app.theme_press(logical)
                elif (getattr(self.app, "sidepanel", None) is not None
                        and self.app.sidepanel.visible
                        and self.app.nav_level != "form"):
                    self.app.sidepanel.press(logical)
                else:
                    pw = self.app.pad_window
                    if _modal_alive(pw):
                        if is_confirm:
                            pw.activate_focused()
                        elif is_cancel:
                            pw.close()
                    else:
                        action = self.app.nexus_action_for(logical)
                        if action == "select":
                            self.app.select_current()
                        elif action == "back":
                            self.app.controller_back()
                        elif action == "cards":
                            self.app.go_to_cards()
                        elif action == "sidebar":
                            self.app.toggle_sidebar()
                        elif action == "notif":
                            self.app.toggle_notif_panel()
                        elif action == "tab_prev":
                            self.app.tab_prev()
                        elif action == "tab_next":
                            self.app.tab_next()
        except:
            pass
        self.app.root.after(16, self.poll)

    def _poll_remote(self):
        """Controle vira controle remoto do app em foco (teclado/mouse virtual)."""
        js = self.joystick
        try:
            for ev in pygame.event.get():
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._maybe_hotplug()
                    break
            hat = self.read_dpad()
            now = time.time()
            if hat != (0, 0):
                if hat not in self.hat_debounce or (now - self.hat_debounce[hat]) > 0.15:
                    self.hat_debounce[hat] = now
                    self.app.using_gamepad = True
                    kb = self.app.kb_window
                    if _modal_alive(kb):
                        kb.on_hat(hat)
                    elif hat == (0, 1):
                        tap_key(VK_UP)
                    elif hat == (0, -1):
                        tap_key(VK_DOWN)
                    elif hat == (-1, 0):
                        tap_key(VK_LEFT)
                    elif hat == (1, 0):
                        tap_key(VK_RIGHT)
            else:
                self.hat_debounce.clear()

            try:
                na = js.get_numaxes()
                lx = js.get_axis(0) if na > 0 else 0.0
                ly = js.get_axis(1) if na > 1 else 0.0
                # Analógico direito = eixos 2,3. Eixos 4,5 (quando existem)
                # sao os GATILHOS (repouso em -1): ler eles puxa o mouse p/ cima.
                if na >= 4:
                    rx, ry = js.get_axis(2), js.get_axis(3)
                else:
                    rx = ry = 0.0
            except Exception:
                lx = ly = rx = ry = 0.0
            # Calibracao: media do repouso nas primeiras leituras estaveis
            if self.remote_cal is not None:
                self.remote_cal.append((lx, ly, rx, ry))
                if len(self.remote_cal) >= 8:
                    ok = True
                    off = []
                    for i in range(4):
                        vals = [s[i] for s in self.remote_cal]
                        if max(vals) - min(vals) > 0.3:
                            ok = False
                        off.append(sum(vals) / len(vals))
                    if ok or len(self.remote_cal) >= 40:
                        self.remote_off = off
                        self.remote_cal = None
                lx = ly = rx = ry = 0.0
            else:
                lx -= self.remote_off[0]
                ly -= self.remote_off[1]
                rx -= self.remote_off[2]
                ry -= self.remote_off[3]
            if self.app.browser_nav_active():
                self._browser_stick_nav(lx, ly)
            else:
                self._remote_stick_scroll(lx, ly)
            self._remote_stick_mouse(rx, ry)
            if any(abs(v) > 0.2 for v in (lx, ly, rx, ry)):
                self.app.using_gamepad = True
            self._remote_triggers()

            # Back + Start juntos = sair do modo remoto (logico: vale p/
            # Xbox, PlayStation, Switch e genericos). Fixo, antes de tudo.
            try:
                pressed_now = self._pressed_raw()
                back_raw = self.raw_for_logical("back")
                start_raw = self.raw_for_logical("start")
                if (back_raw is not None and start_raw is not None
                        and back_raw in pressed_now and start_raw in pressed_now):
                    for i in (back_raw, start_raw):
                        self.prev_buttons[i] = True
                    self.app.exit_remote_mode()
                    return
            except Exception:
                pass

            for btn_id in list(self.prev_buttons):
                if btn_id not in pressed_now:
                    self.prev_buttons[btn_id] = False
            for btn_id in sorted(pressed_now):
                if self.prev_buttons.get(btn_id, False):
                    continue
                self.prev_buttons[btn_id] = True
                self.app.using_gamepad = True
                logical = self.logical_for_raw(btn_id)
                kb = self.app.kb_window
                if _modal_alive(kb) and logical in ("south", "east"):
                    # Teclado aberto sobre o app: A digita, B fecha.
                    # Continue: o botao ja foi tratado; sem isso o codigo
                    # abaixo usaria `top` de outra iteracao (ou NameError).
                    if logical == "south":
                        kb.press_focused()
                    else:
                        kb.close()
                    continue
                top = top_modal(self.app)
                if isinstance(top, NexusKeyboard):
                    if logical == "south":
                        top.press_focused()
                    elif logical == "east":
                        top.close()
                elif self.app.pad_capture is not None:
                    if logical == "east":
                        self.app.cancel_pad_capture()
                    else:
                        self.app.finish_pad_capture(logical)
                else:
                    action = self.app.remote_action_for(logical)
                    if action == "click_left":
                        try:
                            _pos = self._debug_cursor_pos()
                        except Exception:
                            _pos = None
                        try:
                            _dev = ""
                            _js = getattr(self, "joystick", None)
                            if _js is not None:
                                _dev = _js.get_name()
                        except Exception:
                            _dev = ""
                        try:
                            _bnav = bool(self.app.browser_nav_active())
                        except Exception:
                            _bnav = None
                        try:
                            _debug_log("A remoto: click_left bnav=%r pos=%r dev=%r" % (
                                _bnav, _pos, _dev))
                        except Exception:
                            pass
                        if self.app.browser_nav_active():
                            tap_key(VK_RETURN)  # modo console: A abre o quadro
                        else:
                            mouse_click(right=False)
                            self._maybe_open_kb_for_focus()
                    elif action == "keyboard":
                        self._open_kb_global()
                    elif action == "click_right":
                        mouse_click(right=True)
                    elif action == "enter":
                        tap_key(VK_RETURN)
                    elif action == "back":
                        tap_key(VK_ESCAPE)
                    elif action == "space":
                        tap_key(VK_SPACE)
                    elif action == "fullscreen":
                        try:
                            _allowed = remote_button_allowed("fullscreen")
                        except Exception:
                            _allowed = True
                        try:
                            _debug_log("Y remoto: guard(fullscreen) -> %r"
                                       % (_allowed,))
                        except Exception:
                            pass
                        if _allowed:
                            tap_key(VK_F)
                    elif action == "vol_down":
                        tap_key(VK_VOL_DOWN)
                    elif action == "vol_up":
                        tap_key(VK_VOL_UP)
                    elif action == "play_pause":
                        tap_key(VK_MEDIA_PLAY_PAUSE)
                    elif action == "next_track":
                        tap_key(VK_MEDIA_NEXT)
                    elif action == "prev_track":
                        tap_key(VK_MEDIA_PREV)
                    elif action == "app_tab_prev":
                        self.app.remote_tab(prev=True)
                    elif action == "app_tab_next":
                        self.app.remote_tab(prev=False)
            self._remote_watch_tick()
        except Exception:
            pass

    def _maybe_open_kb_for_focus(self):
        """Apos clique com o controle: se o foco caiu num campo de texto,
        abre o teclado (com cooldown). Nos primeiros 6s de remoto, nao:
        o foco inicial do app/site (barra de endereco etc.) nao conta."""
        try:
            if _modal_alive(self.app.kb_window):
                return
            now = time.time()
            try:
                born = float(getattr(self, "remote_enter_time", 0.0) or 0.0)
            except Exception:
                born = 0.0
            if born and now - born < 6.0:
                return
            if now - (self.remote_kb_time or 0.0) < 3.0:
                return
            self.remote_kb_time = now
        except Exception:
            return
        try:
            threading.Thread(target=self._focus_check_thread,
                             daemon=True).start()
        except Exception:
            pass

    def _focus_check_thread(self):
        try:
            time.sleep(0.45)
            is_text = focused_is_text_field()
        except Exception:
            is_text = False
        if is_text:
            try:
                self.app.root.after(0, self._open_kb_global)
            except Exception:
                pass

    def _open_kb_global(self):
        try:
            if _modal_alive(self.app.kb_window):
                try:
                    self.app.kb_window.force_front()
                except Exception:
                    pass
                return
            self.app.open_keyboard(None)
        except Exception:
            pass

    def _browser_stick_nav(self, x, y):
        """Analogico esquerdo no navegador: move o anel entre os quadros
        (modo console). Repeticao ao segurar; analógico direito segue mouse."""
        ndir = (0, 0)
        if abs(x) >= 0.5 or abs(y) >= 0.5:
            if abs(x) >= abs(y):
                ndir = (1 if x > 0 else -1, 0)
            else:
                ndir = (0, -1 if y > 0 else 1)
        now = time.time()
        if ndir != (0, 0):
            if ndir != self.browser_nav_dir:
                self.browser_nav_dir = ndir
                self.browser_nav_next = now
            if now >= self.browser_nav_next:
                self.browser_nav_next = now + 0.28
                if ndir == (0, 1):
                    tap_key(VK_UP)
                elif ndir == (0, -1):
                    tap_key(VK_DOWN)
                elif ndir == (-1, 0):
                    tap_key(VK_LEFT)
                else:
                    tap_key(VK_RIGHT)
        else:
            self.browser_nav_dir = (0, 0)

    def _trigger_axes(self):
        """Eixos 4/5 = gatilhos LT/RT na maioria dos controles."""
        js = self.joystick
        if js is None:
            return []
        try:
            na = js.get_numaxes()
        except Exception:
            return []
        out = []
        for i in (4, 5):
            if i < na:
                try:
                    out.append(float(js.get_axis(i)))
                except Exception:
                    out.append(0.0)
        return out

    def _remote_triggers(self):
        """LT = volume -, RT = volume +. Calibra o repouso e repete ao segurar."""
        try:
            if not self.app.vol_trigger_enabled():
                return
        except Exception:
            pass
        vals = self._trigger_axes()
        if len(vals) < 2:
            return
        if self.remote_trig_rest is None:
            self.remote_trig_samples.append(list(vals))
            if len(self.remote_trig_samples) >= 8:
                ok = True
                rest = []
                for i in range(2):
                    col = [s[i] for s in self.remote_trig_samples]
                    if max(col) - min(col) > 0.3:
                        ok = False
                    rest.append(sum(col) / len(col))
                if ok or len(self.remote_trig_samples) >= 40:
                    self.remote_trig_rest = rest
                    self.remote_trig_samples = []
            return
        now = time.time()
        for i, vk in ((0, VK_VOL_DOWN), (1, VK_VOL_UP)):
            pressed = (vals[i] - self.remote_trig_rest[i]) > 0.5
            st = self.remote_trig_state.get(i, [False, 0.0])
            if pressed and (not st[0] or now >= st[1]):
                tap_key(vk)
                self.remote_trig_state[i] = [True, now + 0.25]
            elif not pressed:
                self.remote_trig_state[i] = [False, 0.0]

    def _remote_stick_scroll(self, x, y):
        """Analogico esquerdo = rolagem da pagina (vertical + horizontal)."""
        try:
            dz = self.app.pad_deadzone()
        except Exception:
            dz = 0.22
        nx = stick_response(x, deadzone=dz)
        ny = stick_response(y, deadzone=dz)
        if nx == 0.0 and ny == 0.0:
            return
        try:
            rate = self.app.pad_scroll()
        except Exception:
            rate = float(DEFAULT_PAD_SCROLL)
        step = rate * 0.016  # ~16ms por poll
        self.remote_wheel_acc[0] += nx * step
        self.remote_wheel_acc[1] += -ny * step  # cima = rolar p/ cima
        for i, is_vert in ((0, False), (1, True)):
            n = int(self.remote_wheel_acc[i])
            if n:
                self.remote_wheel_acc[i] -= n
                if is_vert:
                    mouse_wheel(v_notches=n)
                else:
                    mouse_wheel(h_notches=n)

    def _remote_stick_mouse(self, x, y):
        try:
            dz = self.app.pad_deadzone()
        except Exception:
            dz = 0.22
        nx = stick_response(x, deadzone=dz)
        ny = stick_response(y, deadzone=dz)
        if nx == 0.0 and ny == 0.0:
            return
        try:
            sens = self.app.pad_sensitivity()
        except Exception:
            sens = float(DEFAULT_PAD_SENSITIVITY)
        mouse_move(sens * nx, sens * ny)

    def _remote_watch_tick(self):
        # Caminho rapido: janela do app rastreada (IsWindow e barato).
        # Fecha -> volta ao Nexus em ~0,5s em vez de ~6s do tasklist.
        hwnd = getattr(self, "remote_hwnd", None)
        if hwnd:
            self.remote_watch_count += 1
            if self.remote_watch_count < 15:  # ~250ms
                return
            self.remote_watch_count = 0
            if _hwnd_alive(hwnd):
                self.remote_watch_seen = True
                self.remote_watch_missed = 0
                return
            self.remote_watch_missed += 1
            if self.remote_watch_seen and self.remote_watch_missed >= 2:
                self.app.exit_remote_mode()
            elif self.remote_watch_missed >= 8:
                self.remote_hwnd = None  # janela sumiu: volta ao tasklist
            return
        exes = getattr(self, "remote_watch_list", None)
        if exes is None:
            exes = REMOTE_WATCH.get(self.remote_service or "", [])
        if not exes:
            return
        self.remote_watch_count += 1
        if self.remote_watch_count < 45:  # ~0,75s
            return
        self.remote_watch_count = 0
        alive = any(self._process_alive(exe) for exe in exes)
        if alive:
            self.remote_watch_seen = True
            self.remote_watch_missed = 0
        elif self.remote_watch_seen:
            self.remote_watch_missed += 1
            if self.remote_watch_missed >= 2:
                self.app.exit_remote_mode()

    @staticmethod
    def _process_alive(exe_name):
        try:
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW)
            want = exe_name.lower()
            for line in (out.stdout or "").splitlines():
                if line.split('","')[0].strip('"').lower() == want:
                    return True
        except Exception:
            pass
        return False

    def stop(self):
        self.running = False
        if PYGAME_AVAILABLE:
            try:
                pygame.quit()
            except:
                pass
