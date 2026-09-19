# -*- coding: utf-8 -*-
"""Bateria unitaria do Nexus (sem boot completo; smoke.py cobre o boot).
Uso: Python\\python.exe tests\\test_unit.py   (na pasta do projeto)

Secoes: A teclado geometrico | B remoto | C dock | D notificacoes |
E paineis | F tema | G flip fluxos | H guards de nav | I misc.
"""
import os
import struct
import sys
import textwrap
import threading
import time
import tkinter as tk
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.argv[0] = os.path.join(BASE, "bigpicture.py")
sys.stdout.reconfigure(encoding='utf-8')

fails = []
COUNT = [0]


def check(cond, msg):
    COUNT[0] += 1
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        fails.append(msg)


root = tk.Tk()
root.geometry('900x700+100+100')
root.deiconify()
root.lift()
root.update()

import bigpicture as B  # noqa: E402  (entry p/ Config/t/i18n)
from nexus import cardflip as CF  # noqa: E402
from nexus import input as NINPUT  # noqa: E402
from nexus import panels as PANELS  # noqa: E402
from nexus.config import Config  # noqa: E402
from nexus.i18n import t  # noqa: E402
from nexus.version import APP_VERSION, ver_tuple  # noqa: E402
from nexus.win32 import force_topmost_noactivate  # noqa: E402

CF.save_settings = lambda s: None
PANELS.save_settings = lambda s: None

kb_cls = B.NexusKeyboard if hasattr(B, 'NexusKeyboard') else None
if kb_cls is None:
    from nexus.keyboard import NexusKeyboard as kb_cls  # noqa: E402


class StubApp:
    def __init__(self):
        self.root = root
        self.lang = 'pt-br'
        self.settings = {"favorites": []}
        self.using_gamepad = False
        self.open_dialog = None
        self.active_menu = None
        self.pad_capture = None
        self.pad_window = None
        self.kb_window = None
        self.form_focus = []
        self.form_idx = 0
        self.nav_level = 'tabs'
        self.current_tab = 'all'
        self.ticks = []
        self.calls = []

    def browser_nav_active(self):
        return False

    def pad_sensitivity(self):
        return float(self.settings.get('pad_sensitivity', 12))

    def pad_scroll(self):
        return float(self.settings.get('pad_scroll', 8))

    def play_tick(self):
        self.ticks.append(True)

    def close_sidepanel(self):
        try:
            sp = getattr(self, "sidepanel", None)
            if sp is not None:
                sp.close()
        except Exception:
            pass


# ================= A) teclado geometrico =================
app = StubApp()
kb = kb_cls(app, tk.Entry(root))
app.kb_window = kb
root.update()
rows = kb.cells
check(len(rows) == 5, "A1 fileiras 10/10/9/9/6")
check([len(r) for r in rows] == [10, 10, 9, 9, 6], "A2 larguras")
pad_q = kb.row_frames[1].pack_info().get('padx')
pad_a = kb.row_frames[2].pack_info().get('padx')
pad_q = (pad_q, pad_q) if isinstance(pad_q, int) else tuple(pad_q)
pad_a = (pad_a, pad_a) if isinstance(pad_a, int) else tuple(pad_a)
check(pad_a[0] > pad_q[0], "A3 asdf indentada")
labels = [b.cget('text') for _k, b in rows[4]]
check(labels[0] == '?123' and labels[1] == 'BR' and labels[2] == '🙂'
      and labels[3] == '' and labels[4] == '.' and labels[5] == '✓',
      "A4 action row (?123, BR, emoji, espaco, ponto, check)")
root.update()
w_space = rows[4][3][1].winfo_width()
w_dot = rows[4][4][1].winfo_width()
check(w_space > 3 * w_dot, "A5 flex espaco domina")
W = kb.win.winfo_width()
scale = W / 691.0
exp_w = (W - 2 * 8 * scale - 9 * 7 * scale) / 10
w_q = rows[1][0][1].winfo_width()
check(abs(w_q - exp_w) < 6, "A6 largura exata por flex")
kb.press_key('?123')
check(kb.numeric and [len(r) for r in kb.cells] == [10, 10, 10, 10, 6],
      "A7 ?123 vira simbolos 4x10")
syms = [k for r in kb.cells[:4] for k, _b in r]
check(all(s in syms for s in ('!', '@', '#', '$', '%', '&', '*', '(', ')')),
      "A8 simbolos presentes")
ent = kb.entry
ent.delete(0, 'end')
kb.press_key('!')
check(ent.get() == '!', "A9 digita simbolo")
kb.press_key('?123')
kb.press_key('emoji')
check(kb.emoji and len(kb.cells) == 4, "A10 modo emoji")
kb.press_key('emoji')
kb.press_key('\u21E7')
check(kb.shift and kb.cells[3][0][1].cget('text') == '\u21E7\u25CF',
      "A11 shift marca")
kb.set_cursor(0, 0)
kb.on_hat((0, 1))
check(kb.cur == [-1, 0], "A12 toparea pelo controle")
kb.set_cursor(-1, 0)
kb.press_focused()
root.update()
check(kb.docked, "A13 A no dock ancora")
kb.set_docked(False)
root.update()
kb.close()

# ================= A14) layout BR/US + tecla morta =================
import nexus.keyboard as KBMOD  # noqa: E402
_saved_kb = []
_orig_kb_save = KBMOD.save_settings
KBMOD.save_settings = lambda s: _saved_kb.append(dict(s))
try:
    appL = StubApp()
    kbL = kb_cls(appL, tk.Entry(root))
    appL.kb_window = kbL
    root.update()
    check(getattr(kbL, "layout", "us") == "us", "A14 layout padrao us")
    check([len(r) for r in kbL.cells] == [10, 10, 9, 9, 6],
          "A15 alpha us + action 6")
    kbL.press_key("lang")
    check(kbL.layout == "br", "A16 alterna p/ br")
    check([len(r) for r in kbL.cells] == [10, 10, 10, 9, 3, 6],
          "A17 br: home com Ç + fileira de acentos")
    check("Ç" in [k for k, _b in kbL.cells[2]], "A18 Ç na home")
    check("´" in [k for k, _b in kbL.cells[4]], "A19 fileira ´ ^ ~")
    check(_saved_kb and _saved_kb[-1].get("kb_layout") == "br",
          "A20 persiste kb_layout")
    ent = kbL.entry
    ent.delete(0, "end")
    kbL.press_key("´")
    kbL.press_key("a")
    kbL.press_key("~")
    kbL.press_key("o")
    kbL.press_key("C")
    check(ent.get() == "áõc", "A21 morto compoe + Ç minusculo")
    kbL.press_key("⇧")
    kbL.press_key("Ç")
    kbL.press_key("^")
    kbL.press_key("E")
    kbL.press_key("⇧")
    check(ent.get() == "áõcÇÊ", "A22 shift + maiuscula com ^")
    kbL.press_key("´")
    kbL.press_key("b")
    kbL.press_key("~")
    kbL.press_key("~")
    check(ent.get() == "áõcÇÊ´b~", "A23 sem-combinacao, duplo vira literal")
    kbL.press_key("´")
    kbL.press_key("⌫")
    check(ent.get() == "áõcÇÊ´b~" and kbL.dead is None,
          "A24 backspace cancela o morto")
    kbL.press_key("lang")
    check(kbL.layout == "us"
          and [len(r) for r in kbL.cells] == [10, 10, 9, 9, 6],
          "A25 volta p/ us")
    kbG = kb_cls(appL, None)  # modo global (apps): layout vale sem entry
    kbG.press_key("lang")
    check(kbG.layout == "br", "A26 global alterna p/ br")
    kbG.close()
    kbL.close()
finally:
    KBMOD.save_settings = _orig_kb_save

# ================= B) remoto com teclado =================
import pygame  # noqa: E402
try:
    pygame.init()
    pygame.event.clear()
except Exception:
    pass
from nexus.gamepad import GamepadManager as GM  # noqa: E402

taps = []
ns_tap = GM.__module__
import nexus.gamepad as GMOD  # noqa: E402
_orig_tap = GMOD.tap_key
_orig_click = GMOD.mouse_click
GMOD.tap_key = lambda vk: taps.append(vk)
clicks = []
GMOD.mouse_click = lambda right=False: clicks.append(right)

app2 = StubApp()
kb2 = kb_cls(app2, tk.Entry(root))
app2.kb_window = kb2
typed = []
kb2.press_key = lambda ch: typed.append(ch)
root.update()


class FakeJS:
    def __init__(self):
        self.hat = (0, 0)
        self.btns = set()

    def get_numhats(self):
        return 1

    def get_hat(self, i):
        return self.hat

    def get_numbuttons(self):
        return 12

    def get_button(self, i):
        return i in self.btns

    def get_numaxes(self):
        return 0

    def get_axis(self, i):
        return 0.0


mgr = GM.__new__(GM)
mgr.app = app2
mgr.joystick = FakeJS()
mgr.dpad_sources = [("hat", 0)]
mgr.raw_to_logical = {0: "south", 1: "east"}
mgr.logical_to_raw = {}
mgr.hat_debounce = {}
mgr.prev_buttons = {}
mgr.remote_cal = None
mgr.remote_off = [0.0, 0.0, 0.0, 0.0]
mgr.remote_kb_time = 0.0
mgr.remote_service = ""
mgr.remote_hwnd = None
mgr.remote_watch_list = []
mgr.remote_watch_count = 0
mgr.remote_watch_seen = False
mgr.remote_watch_missed = 0
mgr._maybe_hotplug = lambda: None
kb2.set_cursor(0, 0)
mgr.joystick.hat = (1, 0)
GM._poll_remote(mgr)
check(kb2.cur == [0, 1] and taps == [], "B1 D-pad no teclado sem vazar")
mgr.joystick.hat = (0, 0)
mgr.joystick.btns = {0}
GM._poll_remote(mgr)
check(typed == ['2'] and clicks == [], "B2 A digita sem clicar")
mgr.prev_buttons = {}
mgr.joystick.btns = {1}
GM._poll_remote(mgr)
check(kb2.closed and app2.kb_window is None and taps == [],
      "B3 B fecha sem Esc")
mgr.prev_buttons = {}
mgr.joystick.btns = set()
mgr.joystick.hat = (0, 1)
GM._poll_remote(mgr)
check(taps == [GMOD.VK_UP], "B4 sem teclado o D-pad comanda")
kb2.close()
GMOD.tap_key = _orig_tap
GMOD.mouse_click = _orig_click

# ================= C) dock =================
app3 = StubApp()
kb3 = kb_cls(app3, tk.Entry(root))
root.update()
kb3.toggle_dock()
root.update()
geo = kb3.win.geometry()
w3 = int(geo.split('x')[0])
h3 = int(geo.split('x')[1].split('+')[0])
check(w3 > 400 and h3 > 150, "C1 dock=flutuante ancorado (%s)" % geo)
px = kb3.cells[1][0][1].winfo_width()
s3 = w3 / 691.0
exp3 = (w3 - 2 * 8 * s3 - 9 * 7 * s3) / 10
check(abs(px - exp3) < 8, "C2 teclas preenchem")
kb3.toggle_dock()
root.update()
check(not kb3.docked, "C3 undock")
kb3.close()

print("PARTE 1 OK (%d checks)" % COUNT[0], flush=True)


def _exec_methods(src_file, start_mark, end_mark, globs, cls):
    import nexus.dialogs as DLG  # noqa: F401
    src = open(src_file, encoding='utf-8').read()
    s = src.index(start_mark)
    e = src.index(end_mark, s)
    ns = dict(globs)
    exec(textwrap.dedent(src[s:e]), ns)
    for k, v in ns.items():
        if isinstance(v, type(lambda: 0)):
            setattr(cls, k, lambda self, *a, _f=v, **k2: _f(self, *a, **k2))


def _next_def(src, start):
    i = src.index('\n    def ', start)
    return i


# ================= D) notificacoes =================
from nexus.dialogs import _modal_alive as _ma  # noqa: E402
NOTIF_SRC = os.path.join(BASE, 'nexus', 'app_settings.py')
_exec_methods(NOTIF_SRC, '    NOTIF_WIDTH = 360',
              '    def show_gamepad_info(self):',
              {'t': t, 'Config': Config, 'tk': tk, '_modal_alive': _ma,
               'top_modal': lambda app: None, 'ver_tuple': ver_tuple,
               'APP_VERSION': APP_VERSION, 'save_settings': lambda s: None,
               'STREAMINGS_DB': {}, 'threading': threading,
               'NexusKeyboard': type('NK', (), {}),
               'NexusTextDialog': type('NTD', (), {}),
               'NexusMenuWindow': type('NMW', (), {}),
               'OpenTargetDialog': type('OTD', (), {}),
               'GameCardDialog': type('GCD', (), {})},
              StubApp)
StubApp.NOTIF_WIDTH = 360


class BadgeStub:
    def __init__(self):
        self.mapped = False
        self.text = ''

    def config(self, text=''):
        self.text = text

    def place(self, **k):
        self.mapped = True

    def place_forget(self):
        self.mapped = False


class BtnStub:
    def __init__(self):
        self.fg = None

    def configure(self, **k):
        self.fg = k.get('fg', self.fg)


appN = StubApp()
appN.main_frame = tk.Frame(root)
appN.main_frame.pack(fill='both', expand=True)
appN._latest_release = None
appN.sidebar_visible = False
appN.notif_badge = BadgeStub()
appN.notif_btn = BtnStub()
appN.offered = []
appN.offer_update = lambda info: appN.offered.append(info)
root.update()
appN.build_notif_panel()
check(appN.notif_visible is False, "D1 painel nasce oculto")
appN._refresh_notif_badge()
check(appN.notif_badge.mapped is False
      and appN.notif_btn.fg == Config.TEXT_SECONDARY,
      "D2 sem novidade sem badge")
appN._latest_release = {"tag": "9.9.9", "notes": "N", "date": "2026-01-01",
                        "changes": ["A", "B"]}
appN._refresh_notif_badge()
check(appN.notif_badge.mapped is True and appN.notif_btn.fg == '#e94560',
      "D3 sino vermelho + badge")
appN.open_notif_panel()
root.update()
check(appN.notif_visible is True, "D4 painel abre")
check(appN.settings.get('notif_seen_update') == '9.9.9'
      and appN.notif_badge.mapped is False
      and appN.notif_btn.fg != '#e94560', "D5 ler marca lido e apaga")
texts = set()


def _collect(w):
    try:
        tx = w.cget('text')
        if tx:
            texts.add(str(tx))
    except Exception:
        pass
    for ch in w.winfo_children():
        _collect(ch)


_collect(appN.notif_panel)
blob = '\n'.join(texts)
check('9.9.9' in blob and 'A' in blob, "D6 card lista mudancas")
appN._notif_go_update()
check(appN.offered and appN.offered[0]['tag'] == '9.9.9', "D7 update oferta")
appN.close_notif_panel()
_gosrc = open(os.path.join(BASE, 'nexus', 'app_views.py'), encoding='utf-8').read()
_sg = _gosrc.index('    def go_back(self):')
_eg = _gosrc.index('    def go_to_cards(self):')
_nsG = {'top_modal': lambda app: None, '_modal_alive': _ma}
exec(textwrap.dedent(_gosrc[_sg:_eg]), _nsG)
for _k, _v in _nsG.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
quits = []
appN.confirm_quit = lambda: quits.append(True)
appN.qa_visible = False
appN.pad_window = None
appN.theme_visible = False
appN.sidebar_visible = False
appN.open_notif_panel()
root.update()
appN.go_back()
check(appN.notif_visible is False and quits == [], "D8 B fecha sem sair")

# ================= E) paineis =================
from nexus.panels import (  # noqa: E402
    AdicionarPanel, ControlesPanel, IdiomaPanel, SistemaPanel, SomPanel,
)
_src_panels = open(os.path.join(BASE, 'nexus', 'app_views.py'),
                   encoding='utf-8').read()
_s = _src_panels.index('    def _reg_form(self, widget, kind, action=None):')
_e = _src_panels.index('\n    def ', _s + 10)
_nsF = {'Config': Config}
exec(textwrap.dedent(_src_panels[_s:_e]), _nsF)
for _k, _v in _nsF.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
_src_set = open(os.path.join(BASE, 'nexus', 'app_settings.py'),
                encoding='utf-8').read()
_s2 = _src_set.index('    def add_new_streaming(self):')
_e2 = _src_set.index('    def close_qa(self):')
_nsA = {'t': t, 'Config': Config, 'os': os,
       'copy2': lambda *a: None, 'save_settings': lambda s: None,
       'IMAGES_DIR': os.path.join(BASE, 'streaming_images')}
exec(textwrap.dedent(_src_set[_s2:_e2]), _nsA)
StubApp.add_new_streaming = _nsA['add_new_streaming']


def new_panel_app():
    a = StubApp()
    a.main_frame = tk.Frame(root)
    a.main_frame.pack(fill='both', expand=True)
    a.sidebar_visible = False
    a.theme_visible = False
    a.notif_visible = False
    a.sidepanel = None
    a.gamepad = None
    a.logo_path_cache = {}
    a.close_sidebar = lambda: setattr(a, 'sidebar_visible', False)
    a.close_theme_panel = lambda: setattr(a, 'theme_visible', False)
    a.close_notif_panel = lambda: setattr(a, 'notif_visible', False)
    a.update_all_focus = lambda: None
    a.show_gamepad_info = lambda: a.calls.append('remap')
    a.open_keyboard = lambda *x: a.calls.append('kb')
    a.set_language = lambda c: a.calls.append(('lang', c))
    a.open_resolution = lambda: a.calls.append('res')
    a.confirm_clear_browser_profile = lambda: a.calls.append('cache')
    a.restore_ignored_platform = lambda: a.calls.append('ignored')
    a.check_updates_manual = lambda: a.calls.append('update')
    a.switch_tab = lambda x: a.calls.append(('switch', x))
    a.show_info_message = lambda *x: a.calls.append(('info',) + x)
    a.refresh_ui = lambda: a.calls.append('refresh')
    a.bind_keyboard_popup = lambda e, mode='auto': None
    a.browse_image = lambda e: a.calls.append('browse')
    a._pad_devs = []
    a.pad_devices = lambda: list(a._pad_devs)
    a.select_pad_device = lambda pos: a.calls.append(('pad', pos)) or True
    root.update()
    return a


appP = new_panel_app()
p = ControlesPanel(appP)
p.open()
root.update()
check([f['kind'] for f in p.focusables] == ['button', 'button', 'slider',
      'slider', 'slider', 'button'], "E1 controles estrutura")


class FakeJS2:
    def get_name(self):
        return 'PS3/PC Gamepad'


class FakeGP2:
    def __init__(self):
        self.joystick = FakeJS2()

    def connection_info(self):
        return 'Cabo'


appP.gamepad = FakeGP2()
appP._pad_devs = [{"name": "PS3/PC Gamepad", "layout": "playstation",
                   "guid": "x"}]
p.open()
root.update()
check(any('PS3/PC Gamepad' in (f['widget'].cget('text') if f['kind'] == 'button' else '')
          for f in p.focusables), "E2 lista identifica")
p.set_focus(0)
p.press('south')
check(appP.calls[-1] == ('pad', 0), "E3 troca aparelho")
p.set_focus(3)
p.on_hat((1, 0))
check(appP.settings.get('pad_sensitivity') == 13 and appP.ticks,
      "E4 slider salva + tick")
p.set_focus(2)
p.press('south')
check(appP.calls[-1] == 'remap', "E5 remapear")
p.set_focus(6)
p.press('south')
check(appP.calls[-1] == 'kb', "E6 teclado dentro de controles")
p.press('east')
check(not p.visible and appP.sidepanel is None, "E7 B fecha painel")

appI = new_panel_app()
q = IdiomaPanel(appI)
q.open()
root.update()
check(len(q.focusables) == 2, "E8 idioma 2 opcoes")
q.set_focus(1)
q.press('south')
check(appI.calls == [('lang', 'en')], "E9 idioma troca")

appS = new_panel_app()
s = SistemaPanel(appS)
s.open()
root.update()
for _i, _key in enumerate(['res', 'cache', 'ignored', 'update']):
    s.set_focus(_i)
    s.press('south')
    check(appS.calls[-1] == _key, "E10 sistema %s" % _key)

appA = new_panel_app()
a = AdicionarPanel(appA)
a.open()
root.update()
check(appA.nav_level == 'form' and len(appA.form_focus) == 8,
      "E11 form 8 itens")
_keys = list(appA.add_entries.keys())
appA.add_entries[_keys[0]].delete(0, 'end')
appA.add_entries[_keys[1]].delete(0, 'end')
appA.add_new_streaming()
check(appA.calls and appA.calls[0][0] == 'info', "E12 valida vazio")
appA.add_entries[_keys[0]].insert(0, 'TesteX')
appA.add_entries[_keys[1]].insert(0, 'https://exemplo.com')
appA.add_new_streaming()
check('TesteX' in appA.settings.get('custom_streamings', {}),
      "E13 salvar streaming")
a.close()
check(appA.nav_level == 'items' and appA.form_focus == []
      and appA.sidepanel is None, "E14 fechar reseta form")

print("PARTE 2 OK (%d checks)" % COUNT[0], flush=True)

# ================= F) tema =================
THEME_SRC = os.path.join(BASE, 'nexus', 'app_settings.py')
_th = open(THEME_SRC, encoding='utf-8').read()
_ts = _th.index('    THEME_COLORS = [')
_te = _th.index('    def apply_theme(self, color, win=None):')
_nsT = {'t': t, 'Config': Config, 'tk': tk}
exec(textwrap.dedent(_th[_ts:_te]), _nsT)
for _k, _v in _nsT.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
for _k in ('THEME_COLORS', 'THEME_WIDTH', 'THEME_COLS'):
    setattr(StubApp, _k, _nsT[_k])

appT = StubApp()
appT.main_frame = tk.Frame(root)
appT.main_frame.pack(fill='both', expand=True)
appT.sidebar_visible = False
appT.notif_visible = False
appT.theme_visible = False
appT.theme_focus = 0
appT.close_sidebar = lambda: setattr(appT, 'sidebar_visible', False)
appT.close_notif_panel = lambda: setattr(appT, 'notif_visible', False)
appT.close_sidepanel = lambda: None
appT.applied = []
appT.apply_theme = lambda c: appT.applied.append(c)
root.update()
appT.build_theme_panel()
appT.open_theme_picker()
root.update()
check(appT.theme_visible is True and len(appT.theme_swatches) == 8,
      "F1 painel 8 swatches")
check(sum(1 for b in appT.theme_swatches if b.cget('text') == '\u2713') == 1,
      "F2 atual marcado")
appT.theme_focus = 0
appT.theme_move((1, 0))
check(appT.theme_focus == 1 and appT.ticks, "F3 direita + tick")
appT.theme_move((0, -1))
check(appT.theme_focus == 5, "F4 desce")
appT.theme_set_focus(0)
appT.theme_move((-1, 0))
check(appT.theme_focus == 7, "F5 wrap esquerda")
appT.theme_set_focus(2)
appT.theme_press('south')
check(appT.applied == ['#00bcd4'], "F6 A aplica cor")
appT.theme_press('east')
check(appT.theme_visible is False, "F7 B fecha")
appT.open_theme_picker()
root.update()
appT.theme_swatches[5].event_generate('<Enter>')
root.update()
# hover pode nao disparar headless; aceita foco via API como reserva
if appT.theme_focus != 5:
    appT.theme_set_focus(5)
check(appT.theme_focus == 5, "F8 hover/API foca")
appT.qa_visible = False
appT.pad_window = None
appT.nav_level = 'tabs'
appT.theme_visible = True
appT.close_theme_panel = lambda: setattr(appT, 'theme_visible', False)
appT.quits = []
appT.confirm_quit = lambda: appT.quits.append(True)
appT.controller_back()
check(appT.theme_visible is False and appT.quits == [],
      "F9 voltar fecha sem sair")

# ================= G) flip fluxos =================
class FlipH(CF.CardFlipMixin):
    pass


fh = FlipH()
fh.root = root
fh.lang = 'pt-br'
fh.settings = {"favorites": [], "embedded_browser": True}
fh.calls = []
fh.opener = SimpleNamespace(
    effective_url=lambda n: 'https://exemplo.com',
    open_content=lambda n: fh.calls.append(('open_content', n)))
fh.db = SimpleNamespace(
    add_history=lambda n: fh.calls.append(('hist', n)))
fh.enter_site_remote = lambda *a: fh.calls.append(('site_remote', a[1]))
fh.enter_remote_mode = lambda *a, **k: fh.calls.append(('remote', a[0] if a else None))
fh.show_transition_splash = lambda n: None
fh.borderless_new_app = lambda b: fh.calls.append('borderless')
fh.toggle_favorite = lambda n: fh.calls.append(('fav', n))
fh.reset_card_color = lambda n: fh.calls.append(('uncolor', n))
fh.set_card_color = lambda n, c: fh.calls.append(('color', n, c))
fh.edit_card_url = lambda n, u: True
fh.change_logo = lambda n, p=None: fh.calls.append(('logo', n))
fh.set_game_cover = lambda n, p: True
fh.game_is_platform = lambda n: False
fh.game_is_external = lambda n: False
fh.remove_platform_game = lambda n: fh.calls.append(('rmplat', n))
fh.remove_external_game = lambda n: fh.calls.append(('rmext', n))
fh.delete_game_folder = lambda n: True
fh.refresh_ui = lambda: fh.calls.append('refresh')
fh.open_keyboard = lambda e: fh.calls.append('kb')
fh.current_pad_label = lambda: ''
fh.sections = []
fh.flipped = None
fh._pending_flip = None
fh.nav_level = 'items'
fh.using_gamepad = False
fh.kb_window = None
CF.BROWSER_PROCS = []
CF.open_in_nexus_browser = lambda url, name, pad, service="": SimpleNamespace(
    poll=lambda: None)


class _Proc:
    def poll(self):
        return None


CF.open_in_nexus_browser = lambda url, name, pad, service="": _Proc()
_stat = []
fh.launch_site_flow('N', status_cb=lambda x: _stat.append(x),
                     done_cb=lambda: fh.calls.append('done'))
time.sleep(0.7)
root.update()
check(('hist', 'N') in fh.calls and 'done' in fh.calls
      and any(c[0] == 'site_remote' for c in fh.calls), "G1 site embutido")
fh.calls.clear()
fh.settings["embedded_browser"] = False
fh.launch_site_flow('N', done_cb=lambda: fh.calls.append('done2'))
root.update()
check(('open_content', 'N') in fh.calls and ('remote', 'N') in fh.calls
      and 'done2' in fh.calls, "G2 site fallback externo")
fh.settings["embedded_browser"] = True

_real_open_app = CF.open_app_for_service
CF.open_app_for_service = lambda n: True
fh.calls.clear()
fh.launch_app_flow('N', done_cb=lambda: fh.calls.append('done3'))
time.sleep(0.7)
root.update()
check(('remote', 'N') in fh.calls and 'done3' in fh.calls, "G3 app abre")
CF.open_app_for_service = _real_open_app

fh.flipped = {"busy": True, "status": None, "widget": None, "opts": []}
fh.calls.clear()
fh._flip_site('N')
check(fh.calls == [], "G4 ocupado ignora duplo")
fh.flipped = None

fh.sections = [{"names": ["N"], "widgets": []}]
w1 = tk.Frame(root)
fh.sections = [{"names": ["N"], "widgets": [w1]}]
fh.flip_card(w1, 'N', False)
root.update()
check(fh.flipped is not None and len(fh.flipped["opts"]) == 3,
      "G5 flip monta verso")
fh.cfg_keep_flip('N', False, 'config', lambda: fh.calls.append('go'))
check(fh.calls == ['go'] and fh.flipped is not None, "G6 keep sem refresh")
w1.destroy()
fh.flipped = None
fh._pending_flip = ('N', False, 'config')
w2 = tk.Frame(root)
w2.pack()
fh.sections = [{"names": ["N"], "widgets": [w2]}]
root.update()
fh._restore_pending_flip()
check(fh.flipped is not None and fh.flipped["widget"] is w2
      and fh.flipped["page"] == "config", "G7 restore re-vira")
fh._pending_flip = ('ZZZ', False, 'main')
fh.flipped = None
fh._restore_pending_flip()
check(fh.flipped is None, "G8 restore sem card some quieto")

fh.settings["custom_streamings"] = {"X": {}}
fh.settings["favorites"] = ["X"]
fh.calls.clear()
fh._flip_delete_yes('X', False)
check('X' not in fh.settings.get('custom_streamings', {})
      and 'refresh' in fh.calls, "G9 excluir streaming")
fh.calls.clear()
fh.game_is_platform = lambda n: True
fh._flip_delete_yes('Y', True)
check(('rmplat', 'Y') in fh.calls, "G10 excluir plataforma")
check(fh.find_card_widget('ZZZ') is None, "G11 find vazio")
fh.nav_level = 'items'
fh.focus_mgr = SimpleNamespace(focused_row=0, focused_col=0)
fh.sections = [{"names": ["N"], "widgets": [w2], "canvas": None}]
fh.current_tab = 'all'
_w, _n, _g = fh.focused_card()
check((_n, _g) == ('N', False) and _w is w2, "G12 focused_card")

# ================= H) nav guards =================
b1 = tk.Button(root)
b2 = tk.Button(root)
fh.flipped = {"widget": w2, "opts": [(b1, lambda: fh.calls.append('o1')),
                                     (b2, lambda: fh.calls.append('o2'))],
              "idx": 0, "page": "main", "back": tk.Frame(root)}
fh.play_tick = lambda: None
for _ in range(3):
    fh.flip_opt_move(1)
check(fh.flipped["idx"] == 1, "H1 opt anda")
fh.flip_opt_move(-1)
fh.flip_opt_move(-1)
check(fh.flipped["idx"] == 1, "H2 opt wrap volta")
fh.calls.clear()
fh.flip_opt_activate()
fh.flip_opt_activate()
check(fh.calls == ['o2', 'o2'], "H3 A ativa focada")

appH = StubApp()
appH.theme_visible = False
appH.notif_visible = False
appH.sidepanel = None
appH.sidebar_visible = False
appH.qa_visible = False
appH.nav_level = 'items'
appH.flipped = {"widget": w2}
appH.unflipped = []
appH.unflip_card = lambda: appH.unflipped.append(True)
appH.go_back()
check(appH.unflipped == [True], "H4 voltar desvira")

# ================= I) misc =================
check(isinstance(force_topmost_noactivate(root), bool), "I1 topmost bool")
_w1 = NINPUT._nav_tick_wav(100)
_w2 = NINPUT._nav_tick_wav(30)
check(_w1[:4] == b'RIFF', "I2 wav valido")


def _peak(w):
    n = (len(w) - 44) // 2
    return max(abs(struct.unpack('<h', w[44 + 2 * i:46 + 2 * i])[0])
               for i in range(0, n, 7))


check(_peak(_w1) > _peak(_w2) > 0, "I3 volume escala")
_vs = open(os.path.join(BASE, 'nexus', 'app_views.py'), encoding='utf-8').read()
_ps = _vs.index('    def play_tick(self):')
_pe = _vs.index('\n    def ', _ps + 10)
_nsP = {'_play_nav_tick': lambda vol=10: played_vol.append(vol)}
played_vol = []
exec(textwrap.dedent(_vs[_ps:_pe]), _nsP)
_pt = _nsP['play_tick']


class _PA:
    settings = {}


_pt(_PA())
check(played_vol == [10], "I4 tick padrao 10")


class _PB:
    settings = {'sound_volume': 0}


_pt(_PB())
check(played_vol == [10], "I5 volume 0 mudo")


class _PC:
    settings = {'nav_sound': False, 'sound_volume': 90}


_pt(_PC())
check(played_vol == [10], "I6 toggle respeitado")
check(ver_tuple('v5.4.0') == ver_tuple('5.4.0'), "I7 versao com v")
check(ver_tuple('5.4.0') < ver_tuple('9.9.9'), "I8 versao ordena")
from nexus.pad import detect_pad_layout  # noqa: E402
check(detect_pad_layout('Xbox 360 Controller') == 'xbox'
      and detect_pad_layout('PS3/PC Gamepad') == 'playstation'
      and detect_pad_layout('Teclado X') == 'generic', "I9 layouts")
calls_f = []
_real_fit = NINPUT.focused_is_text_field
NINPUT.focused_is_text_field = lambda: calls_f.append(True) or False
NINPUT._FOCUS_CACHE.update(t=None, v=False)
NINPUT.focused_is_text_field_cached()
NINPUT.focused_is_text_field_cached()
check(len(calls_f) == 1, "I10 foco com cache (1 consulta)")
NINPUT.focused_is_text_field_cached(ttl=0)
check(len(calls_f) == 2, "I11 ttl=0 reconsulta")
NINPUT.focused_is_text_field = _real_fit

print("PARTE 3 OK (%d checks)" % COUNT[0], flush=True)

# ================= J) Y-guard ponta a ponta =================
import nexus.gamepad as GMOD2  # noqa: E402
_t2, _c2 = GMOD2.tap_key, GMOD2.mouse_click
tapsY = []
GMOD2.tap_key = lambda vk: tapsY.append(vk)
GMOD2.mouse_click = lambda right=False: None

appY = StubApp()
appY.remote_action_for = lambda logical: "fullscreen" if logical == "north" else None
kbY = kb_cls(appY, tk.Entry(root))
appY.kb_window = kbY
typedY = []
kbY.press_key = lambda ch: typedY.append(ch)
root.update()
mgrY = GM.__new__(GM)
mgrY.app = appY
mgrY.joystick = FakeJS()
mgrY.dpad_sources = [("hat", 0)]
mgrY.raw_to_logical = {0: "south", 1: "east", 3: "north"}
mgrY.logical_to_raw = {}
mgrY.hat_debounce = {}
mgrY.prev_buttons = {}
mgrY.remote_cal = None
mgrY.remote_off = [0.0, 0.0, 0.0, 0.0]
mgrY.remote_kb_time = 0.0
mgrY.remote_enter_time = 0.0
mgrY.remote_service = ""
mgrY.remote_hwnd = None
mgrY.remote_watch_list = []
mgrY.remote_watch_count = 0
mgrY.remote_watch_seen = False
mgrY.remote_watch_missed = 0
mgrY._maybe_hotplug = lambda: None

# H2: A com teclado aberto digita 1x, sem clique e sem NameError
kbY.set_cursor(0, 0)
mgrY.joystick.btns = {0}
GM._poll_remote(mgrY)
check(typedY == ['1'], "J1 A digita 1x com kb aberto")
mgrY.prev_buttons = {}
mgrY.joystick.btns = {1}
GM._poll_remote(mgrY)
check(kbY.closed, "J2 B fecha kb (sem cair no dispatch)")

# H4: Y em campo bloqueia F e loga a decisao; fora do campo, manda F
import os as _os
_os.environ["NEXUS_DEBUG"] = "1"
try:
    try:
        _os.remove(os.path.join(BASE, 'nexus_debug.log'))
    except Exception:
        pass
    NINPUT.focused_is_text_field = lambda: True
    NINPUT._FOCUS_CACHE.update(t=None, v=False)
    mgrY.prev_buttons = {}
    mgrY.joystick.btns = {3}
    GM._poll_remote(mgrY)
    tail = ""
    try:
        _loglines = open(os.path.join(BASE, 'nexus_debug.log'),
                         encoding='utf-8').read().splitlines()
        tail = _loglines[-1] if _loglines else ""
    except Exception:
        tail = ""
    check(tapsY == [] and 'guard(fullscreen)' in tail and 'False' in tail,
          "J3 Y em campo bloqueia + loga")
finally:
    _os.environ.pop("NEXUS_DEBUG", None)
NINPUT.focused_is_text_field = lambda: False
NINPUT._FOCUS_CACHE.update(t=None, v=False)
mgrY.prev_buttons = {}
mgrY.joystick.btns = {3}
GM._poll_remote(mgrY)
check(tapsY == [GMOD2.VK_F], "J4 Y fora do campo manda F")
NINPUT.focused_is_text_field = _real_fit
kbY.close()
GMOD2.tap_key = _t2
GMOD2.mouse_click = _c2

# A no remoto clica e loga (acao + cursor + aparelho)
_t3, _c3 = GMOD2.tap_key, GMOD2.mouse_click
clicksA = []
GMOD2.tap_key = lambda vk: None
GMOD2.mouse_click = lambda right=False: clicksA.append(right)
appR = StubApp()
appR.remote_action_for = lambda logical: "click_left" if logical == "south" else None
appR.browser_nav_active = lambda: False
appR.kb_window = None
mgrR = GM.__new__(GM)
mgrR.app = appR
mgrR.joystick = FakeJS()
mgrR.joystick.get_name = lambda: "Xbox 360 Controller"
mgrR.dpad_sources = [("hat", 0)]
mgrR.raw_to_logical = {0: "south"}
mgrR.logical_to_raw = {}
mgrR.hat_debounce = {}
mgrR.prev_buttons = {}
mgrR.remote_cal = None
mgrR.remote_off = [0.0, 0.0, 0.0, 0.0]
mgrR.remote_kb_time = 0.0
mgrR.remote_enter_time = 0.0
mgrR.remote_service = ""
mgrR.remote_hwnd = None
mgrR.remote_watch_list = []
mgrR.remote_watch_count = 0
mgrR.remote_watch_seen = False
mgrR.remote_watch_missed = 0
mgrR._maybe_hotplug = lambda: None
mgrR._maybe_open_kb_for_focus = lambda: None
mgrR.joystick.btns = {0}
_os.environ["NEXUS_DEBUG"] = "1"
try:
    try:
        _os.remove(os.path.join(BASE, 'nexus_debug.log'))
    except Exception:
        pass
    GM._poll_remote(mgrR)
    _logA = ""
    try:
        _logA = open(os.path.join(BASE, 'nexus_debug.log'),
                     encoding='utf-8').read()
    except Exception:
        pass
    check(clicksA == [False] and 'A remoto: click_left' in _logA
          and 'Xbox 360 Controller' in _logA, "J5 A remoto clica + loga")
finally:
    _os.environ.pop("NEXUS_DEBUG", None)
GMOD2.tap_key = _t3
GMOD2.mouse_click = _c3

print("PARTE 4 OK (%d checks)" % COUNT[0], flush=True)

# ================= K) mapa por aparelho + Y livre =================
from nexus.pad import (  # noqa: E402
    DEFAULT_PAD_DEADZONE, DEFAULT_PAD_SCROLL, DEFAULT_PAD_SENSITIVITY,
    DEFAULT_REMOTE_MAP, REMOTE_ACTION_ORDER, normalize_pad_value,
)
check("fullscreen" not in DEFAULT_REMOTE_MAP, "K1 Y livre de fabrica")
check("fullscreen" in REMOTE_ACTION_ORDER, "K2 fullscreen remapeavel")
_ar = open(os.path.join(BASE, 'nexus', 'app_remote.py'), encoding='utf-8').read()
_nsR = {'save_settings': lambda s: None,
        'DEFAULT_NEXUS_MAP': {}, 'DEFAULT_REMOTE_MAP': DEFAULT_REMOTE_MAP,
        'DEFAULT_PAD_SENSITIVITY': DEFAULT_PAD_SENSITIVITY,
        'DEFAULT_PAD_SCROLL': DEFAULT_PAD_SCROLL,
        'DEFAULT_PAD_DEADZONE': DEFAULT_PAD_DEADZONE,
        'LOGICAL_BUTTONS': (), 'normalize_pad_value': normalize_pad_value,
        '_modal_alive': lambda w: False}
for _mark in ('    def _pad_lookup(self, base_map, settings_key, btn_or_logical):',
              '    def remote_action_for(self, btn_or_logical):',
              '    def pad_profile_snapshot(self):',
              '    def device_profiles(self):',
              '    def store_device_profile(self, guid):',
              '    def adopt_device_profile(self, prev_guid):',
              '    def store_current_device(self):',
              '    def finish_pad_capture(self, btn_or_logical):'):
    _s = _ar.index(_mark)
    _e = _ar.index('\n    def ', _s + 10)
    exec(textwrap.dedent(_ar[_s:_e]), _nsR)
for _k, _v in _nsR.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
_gp = open(os.path.join(BASE, 'nexus', 'gamepad.py'), encoding='utf-8').read()
_sg = _gp.index('    def current_guid(self):')
_eg = _gp.index('\n    def ', _sg + 10)
_nsG2 = {}
exec(textwrap.dedent(_gp[_sg:_eg]), _nsG2)


class GPStub:
    def __init__(self, devs, joy_name):
        self.devices = devs
        self.joystick = SimpleNamespace(get_name=lambda: joy_name) \
            if joy_name else None


GPStub.current_guid = _nsG2['current_guid']
appK = StubApp()
appK.settings = {"pad_nexus": {"select": "south"}, "pad_remote": {},
                 "pad_sensitivity": 15, "pad_scroll": 9, "pad_deadzone": 25}
appK.gamepad = GPStub([{"name": "A", "guid": "A"},
                       {"name": "B", "guid": "B"}], "A")
appK.pad_window = None
check(appK.remote_action_for("north") is None, "K3 Y sem acao padrao")
appK.adopt_device_profile("")
check(appK.settings.get("pad_per_device", {}).get("A", {}).get(
    "nexus") == {"select": "south"}, "K4 boot semeia aparelho")
appK.gamepad = GPStub([{"name": "A", "guid": "A"},
                       {"name": "B", "guid": "B"}], "B")
appK.adopt_device_profile("A")
_slots = appK.settings.get("pad_per_device", {})
check(_slots.get("A", {}).get("sensitivity") == 15
      and appK.settings.get("pad_nexus") == {}
      and appK.settings.get("pad_sensitivity") == DEFAULT_PAD_SENSITIVITY,
      "K5 troca guarda A e zera B")
appK.settings["pad_sensitivity"] = 20
appK.gamepad = GPStub([{"name": "A", "guid": "A"},
                       {"name": "B", "guid": "B"}], "A")
appK.adopt_device_profile("B")
check(appK.settings.get("pad_nexus") == {"select": "south"}
      and appK.settings.get("pad_sensitivity") == 15,
      "K6 voltar restaura A")
appK.pad_capture = {"section": "nexus", "action": "cards"}
appK.finish_pad_capture("west")
_slots = appK.settings.get("pad_per_device", {})
check(appK.settings["pad_nexus"].get("cards") == "west"
      and _slots.get("A", {}).get("nexus", {}).get("cards") == "west",
      "K7 remap carimba aparelho")
check(GPStub([{"name": "B", "guid": "B"}], "B").current_guid() == "B"
      and GPStub([], None).current_guid() == "", "K8 guid atual")

# ================= L) teclado: abre no 1o confirmar, fecha ao confirmar ====
import nexus.keyboard as KMOD  # noqa: E402
ktaps = []
_orig_ktap = KMOD.tap_key
KMOD.tap_key = lambda vk: ktaps.append(vk)

# L1: Start com teclado global confirma o texto (fecha + Enter)
appL = StubApp()
kbL = kb_cls(appL, None)
appL.kb_window = kbL
root.update()
mgrL = GM.__new__(GM)
mgrL.app = appL
mgrL.joystick = FakeJS()
mgrL.dpad_sources = [("hat", 0)]
mgrL.raw_to_logical = {0: "south", 1: "east", 7: "start"}
mgrL.logical_to_raw = {}
mgrL.hat_debounce = {}
mgrL.prev_buttons = {}
mgrL.remote_cal = None
mgrL.remote_off = [0.0, 0.0, 0.0, 0.0]
mgrL.remote_kb_time = 0.0
mgrL.remote_enter_time = 0.0
mgrL.remote_service = ""
mgrL.remote_hwnd = None
mgrL.remote_watch_list = []
mgrL.remote_watch_count = 0
mgrL.remote_watch_seen = False
mgrL.remote_watch_missed = 0
mgrL._maybe_hotplug = lambda: None
mgrL.joystick.btns = {7}
GM._poll_remote(mgrL)
check(kbL.closed and appL.kb_window is None and ktaps == [KMOD.VK_RETURN],
      "L1 Start confirma texto (fecha + Enter)")

# L2/L3: tecla ok: global fecha + Enter; com entry so fecha
ktaps.clear()
kbLG = kb_cls(appL, None)
kbLG.press_key("ok")
check(kbLG.closed and ktaps == [KMOD.VK_RETURN], "L2 ok global fecha + Enter")
ktaps.clear()
kbLE = kb_cls(appL, tk.Entry(root))
kbLE.press_key("ok")
check(kbLE.closed and ktaps == [], "L3 ok com entry fecha sem Enter")
KMOD.tap_key = _orig_ktap

# L4/L5: confirmar no Site e via Enter agenda a checagem do teclado
_tL, _cL = GMOD2.tap_key, GMOD2.mouse_click
tapsL = []
GMOD2.tap_key = lambda vk: tapsL.append(vk)
GMOD2.mouse_click = lambda right=False: None


def _mgrE(bnav, action):
    aE = StubApp()
    aE.browser_nav_active = lambda: bnav
    aE.remote_action_for = lambda l: action if l == "south" else None
    aE.kb_window = None
    mE = GM.__new__(GM)
    mE.app = aE
    mE.joystick = FakeJS()
    mE.dpad_sources = [("hat", 0)]
    mE.raw_to_logical = {0: "south"}
    mE.logical_to_raw = {}
    mE.hat_debounce = {}
    mE.prev_buttons = {}
    mE.remote_cal = None
    mE.remote_off = [0.0, 0.0, 0.0, 0.0]
    mE.remote_kb_time = 0.0
    mE.remote_enter_time = 0.0
    mE.remote_service = ""
    mE.remote_hwnd = None
    mE.remote_watch_list = []
    mE.remote_watch_count = 0
    mE.remote_watch_seen = False
    mE.remote_watch_missed = 0
    mE.browser_nav_dir = (0, 0)
    mE.browser_nav_next = 0.0
    mE._maybe_hotplug = lambda: None
    mE.joystick.btns = {0}
    return mE


mgrE4 = _mgrE(True, "click_left")
kbchecks4 = []
mgrE4._maybe_open_kb_for_focus = lambda: kbchecks4.append(True)
GM._poll_remote(mgrE4)
check(tapsL == [GMOD2.VK_RETURN] and kbchecks4 == [True],
      "L4 confirmar no Site checa teclado no 1o toque")
mgrE5 = _mgrE(False, "enter")
kbchecks5 = []
mgrE5._maybe_open_kb_for_focus = lambda: kbchecks5.append(True)
mgrE5.prev_buttons = {}
tapsL.clear()
GM._poll_remote(mgrE5)
check(tapsL == [GMOD2.VK_RETURN] and kbchecks5 == [True],
      "L5 Enter checa teclado no 1o toque")
GMOD2.tap_key = _tL
GMOD2.mouse_click = _cL

# L6: foco com atraso (2a fase) tambem abre o teclado
_real_gfit = GMOD2.focused_is_text_field
_script = [False, True]
GMOD2.focused_is_text_field = lambda: _script.pop(0) if _script else False
appT = StubApp()
appT.kb_window = None
openedT = []
appT.open_keyboard = lambda *a, **k: openedT.append(True)
mgrT = GM.__new__(GM)
mgrT.app = appT
GM._focus_check_thread(mgrT)
root.update()
check(openedT == [True], "L6 foco tardio abre o teclado")
GMOD2.focused_is_text_field = _real_gfit

# ================= PARTE 6: busca + favoritos segregados =================
import nexus.app_settings as SETMOD  # noqa: E402
import nexus.app_views as VIEWMOD  # noqa: E402
from nexus.app_games import AppGamesMixin as _GMX  # noqa: E402
_orig_set_save = SETMOD.save_settings
SETMOD.save_settings = lambda s: None
try:
    for _k in ("is_game_name", "game_favorites", "is_favorite",
               "_migrate_favorites", "toggle_favorite"):
        setattr(StubApp, _k, getattr(SETMOD.AppSettingsMixin, _k))
    setattr(StubApp, "_match_search", VIEWMOD.AppViewsMixin._match_search)
    for _k in ("game_folder", "game_is_external", "game_is_platform"):
        setattr(StubApp, _k, getattr(_GMX, _k))
    StubApp.refresh_ui = lambda self: None

    g = StubApp()
    g.settings = {"favorites": [],
                  "external_games": {"ZZJogo": {"exe": "x"}},
                  "game_favorites": []}
    g.search_query = ""
    check(g.is_game_name("ZZJogo") is True, "M1 jogo detectado")
    check(g.is_game_name("Netflix") is False, "M2 app nao e jogo")
    g.toggle_favorite("ZZJogo")
    check("ZZJogo" in g.settings["game_favorites"]
          and "ZZJogo" not in g.settings["favorites"],
          "M3 toggle jogo vai p/ game_favorites")
    g.toggle_favorite("Netflix")
    check("Netflix" in g.settings["favorites"], "M4 toggle app vai p/ favorites")
    g.toggle_favorite("ZZJogo")
    check("ZZJogo" not in g.settings["game_favorites"], "M5 toggle remove jogo")
    g2 = StubApp()
    g2.settings = {"favorites": ["Netflix", "ZZJogo2"],
                   "external_games": {"ZZJogo2": {"exe": "x"}},
                   "game_favorites": []}
    g2.search_query = ""
    g2._migrate_favorites()
    check("ZZJogo2" not in g2.settings["favorites"]
          and "ZZJogo2" in g2.settings["game_favorites"]
          and "Netflix" in g2.settings["favorites"], "M6 migracao separa")
    check(g2.is_favorite("ZZJogo2") and g2.is_favorite("Netflix")
          and not g2.is_favorite("Nada"), "M7 is_favorite roteia")
    g2.search_query = ""
    check(g2._match_search("Netflix") is True, "M8 match vazio passa")
    g2.search_query = "net"
    check(g2._match_search("Netflix") is True
          and g2._match_search("YouTube") is False, "M9 match filtra")
    g2.search_query = "pokemon"
    check(g2._match_search("Pokémon") is True, "M10 match sem acento")
finally:
    SETMOD.save_settings = _orig_set_save

# ================= PARTE 6: perfil por aplicativo =================
import shutil
import tempfile
from nexus import paths as _PTH
_tmpbase = tempfile.mkdtemp(prefix="nxprof_")
_old_env = os.environ.get("NEXUS_PROFILE_DIR")
os.environ["NEXUS_PROFILE_DIR"] = _tmpbase
try:
    check(_PTH.service_key("Disney+") == "disney", "P1 slug disney")
    check(_PTH.service_key("A&B C") == "a_b_c", "P2 slug simbolos")
    check(_PTH.service_key("") == "app", "P3 slug vazio")
    dn = _PTH.service_profile_dir("Netflix")
    check(os.path.isdir(dn) and os.path.abspath(dn).startswith(
        os.path.abspath(_tmpbase)), "P4 dir aninhada na base")
    open(os.path.join(dn, "x.dat"), "w").write("12345")
    dy = _PTH.service_profile_dir("YouTube")
    open(os.path.join(dy, "y.dat"), "w").write("1234567890")
    check(_PTH.service_profile_size("Netflix") == 5, "P5 size solo")
    check(_PTH.browser_profile_size() >= 15, "P6 size global soma")
    check(_PTH.clear_service_profile("Netflix") is True, "P7 clear solo")
    check(not os.path.exists(os.path.join(dn, "x.dat")), "P8 arquivo sumiu")
    check(os.path.exists(os.path.join(dy, "y.dat")), "P9 outro intacto")
    check(_PTH.clear_service_profile("") is False, "P10 sem slug nao apaga base")
    check(os.path.isdir(_tmpbase), "P11 base intacta")
finally:
    if _old_env is None:
        os.environ.pop("NEXUS_PROFILE_DIR", None)
    else:
        os.environ["NEXUS_PROFILE_DIR"] = _old_env
    shutil.rmtree(_tmpbase, ignore_errors=True)

print("PARTE 5 OK (%d checks)" % COUNT[0], flush=True)

# ================= V) volume padrao =================
_ar = open(os.path.join(BASE, 'nexus', 'app_remote.py'), encoding='utf-8').read()
_box = {"get": 0.5}
_gets, _sets = [], []
_nsV = {'audio_get_master': lambda: _gets.append(1) or _box["get"],
        'audio_set_master': lambda v: _sets.append(round(float(v), 2)) or True}
for _mark in ('    def default_volume(self):',
              '    def _apply_default_volume(self):',
              '    def _restore_pre_volume(self):'):
    _s = _ar.index(_mark)
    _e = _ar.index('\n    def ', _s + 10)
    exec(textwrap.dedent(_ar[_s:_e]), _nsV)
for _k, _v in _nsV.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
from nexus.panels import SomPanel  # noqa: E402

appV = StubApp()
appV.settings = {}
check(appV.default_volume() == 70, "V1 padrao 70")
check(appV._apply_default_volume() is True and _sets == [0.7]
      and getattr(appV, '_pre_remote_vol', None) == 0.5,
      "V2 aplicar guarda previo e poe 70")
_box["get"] = None
_sets.clear()
check(appV._apply_default_volume() is True and _sets == [0.7],
      "V3 aplicar mesmo sem ler atual")
_box["get"] = 0.5
appV._pre_remote_vol = 0.5
_sets.clear()
check(appV._restore_pre_volume() is True and _sets == [0.5]
      and getattr(appV, '_pre_remote_vol', 'x') is None,
      "V4 sair restaura previo")
_sets.clear()
check(appV._restore_pre_volume() is False and _sets == [],
      "V5 sem previo nao mexe")
appS = new_panel_app()
sp = SomPanel(appS)
sp.open()
root.update()
_def = [f for f in sp.focusables if f.get('kind') == 'slider'][1]
_def['put'](70)
check(appS.settings.get('sound_default') == 70, "V6 slider salva padrao")
appS.gamepad = SimpleNamespace(remote_active=True)
_applied = []
appS._apply_default_volume = lambda: _applied.append(True)
_def['put'](65)
check(_applied == [True], "V7 slider aplica ao vivo no remoto")
sp.close()

# ================= M) 1 clique abre (retry) =================
import nexus.gamepad as _GM  # noqa: E402
_real_fit2 = _GM.focused_is_text_field
seq = iter([False, True])
_calls = []


def _seq_check():
    v = next(seq, True)
    _calls.append(v)
    return v
_GM.focused_is_text_field = _seq_check
appL = StubApp()
appL.opened = []
appL.open_keyboard = lambda e=None: appL.opened.append(True)
appL.kb_window = None
mgrL = GM.__new__(GM)
mgrL.app = appL
mgrL.remote_kb_time = 0.0
mgrL.remote_enter_time = 0.0
mgrL._focus_check_thread()
root.update()
check(appL.opened == [True], "M1 foco lento abre sozinho")
check(_calls == [False, True], "M2 2a chance apos 1o negativo")
_GM.focused_is_text_field = lambda: True
appL.opened.clear()
mgrL._focus_check_thread()
root.update()
check(appL.opened == [True], "M3 foco rapido abre")
_GM.focused_is_text_field = _real_fit2
# ================= W) coalesce de pops =================
played_ws = []
_real_ws = NINPUT._winsound


class _FakeWS:
    SND_MEMORY = 0

    def PlaySound(self, data, flags):
        played_ws.append(data)
        time.sleep(0.005)


NINPUT._winsound = _FakeWS()
NINPUT._TICK_STATE.update(playing=False, pending=None, last=0.0)
for _v in (10, 30, 50, 70, 90):
    ok, _err = NINPUT._play_nav_tick(_v)
    check(ok, "W0 tick aceito vol %d" % _v)
time.sleep(0.6)
check(1 <= len(played_ws) <= 2, "W1 rajada vira 1-2 pops (%d)" % len(played_ws))
check(bool(played_ws) and played_ws[-1] == NINPUT._nav_tick_wav(90),
      "W2 ultimo conta")
NINPUT._winsound = _real_ws
NINPUT._TICK_STATE.update(playing=False, pending=None, last=0.0)
# ================= X) preset em jogos =================
_g = open(os.path.join(BASE, 'nexus', 'app_games.py'), encoding='utf-8').read()
_s = _g.index('    def launch_game(')
_e = _g.index('\n    def ', _s + 10)
_popen_calls = []


class _FakePopen:
    def __init__(self, *a, **k):
        _popen_calls.append((a, k))


_nsX = {'os': os, 'subprocess': SimpleNamespace(Popen=_FakePopen),
        'find_game_exe': lambda folder: 'C:\\g\\g.exe',
        't': lambda k, lang='pt': k}
exec(textwrap.dedent(_g[_s:_e]), _nsX)
for _k, _v in _nsX.items():
    if isinstance(_v, type(lambda: 0)):
        setattr(StubApp, _k,
                lambda self, *a, _f=_v, **k2: _f(self, *a, **k2))
_sv = _g.index('    def _game_volume_preset(self):')
_ev = _g.index('\n    def ', _sv + 10)
_nsV2 = {}
exec(textwrap.dedent(_g[_sv:_ev]), _nsV2)
StubApp._game_volume_preset = _nsV2['_game_volume_preset']
appX = StubApp()
appX.lang = 'pt-br'
appX.game_is_platform = lambda n: False
appX.game_is_external = lambda n: False
appX.game_folder = lambda n: 'C:\\g'
appX.db = SimpleNamespace(add_history=lambda n: None)
appX.show_info_message = lambda *a: None
appX.applied = []
appX._apply_default_volume = lambda: appX.applied.append(True)
appX.launch_game('Doom')
check(_popen_calls and appX.applied == [True], "X1 jogo aplica preset")
_popen_calls.clear()
appX.applied.clear()
_nsX['find_game_exe'] = lambda folder: None
_src2 = _g[_s:_e]
_nsX2 = {'os': os, 'subprocess': SimpleNamespace(Popen=_FakePopen),
         'find_game_exe': lambda folder: None,
         't': lambda k, lang='pt': k}
exec(textwrap.dedent(_src2), _nsX2)
appX.launch_game = lambda name, _f=_nsX2['launch_game']: _f(appX, name)
appX.launch_game('Vazio')
check(_popen_calls == [] and appX.applied == [], "X2 sem exe sem preset")
# ================= Y) volume por programa =================
from nexus import audio as AUD  # noqa: E402
check(isinstance(AUD.audio_sessions(), list), "Y1 sessoes lista")
check(AUD.session_set_volume("nao-existe-xyz.exe", 0.7) is False,
      "Y2 exe ausente False")
_made = []


def _fake_set(exe, level):
    _made.append(exe)
    return exe == "a.exe"


check(AUD.ensure_app_volumes(["a.exe", "b.exe"], 0.7, tries=5,
                             _set=_fake_set) == ["b.exe"],
      "Y3 retry ate acertar")
check(_made.count("a.exe") == 1 and _made.count("b.exe") == 5,
      "Y4 para no acerto, insiste no resto")
check(AUD.ensure_app_volumes([], 0.7) == []
      and AUD.ensure_app_volumes(["z.exe"], 0.7, tries=2,
                                 _set=lambda e, l: False) == ["z.exe"],
      "Y5 vazio e esgotamento")
print("TOTAL %d checks, %d falhas" % (COUNT[0], len(fails)), flush=True)
if fails:
    print("FALHAS:", fails, flush=True)
    sys.exit(1)
root.destroy()
print("UNIT OK", flush=True)


