# -*- coding: utf-8 -*-
"""Login/perfis + controle pelo celular (servidor, pareamento, PWA).
Uso: Python\\python.exe tests\\test_phone.py   (na pasta do projeto)
"""
import json
import os
import queue
import sys
import tempfile
import tkinter as tk
import urllib.request

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


# Nao suja o settings.json do usuario (switch/pair salvam de verdade):
# backup byte a byte + restauracao no fim (igual ao smoke.py).
_saved_settings = None
try:
    _sp = os.path.join(BASE, "settings.json")
    _saved_settings = open(_sp, "rb").read() if os.path.exists(_sp) else None
except Exception:
    _saved_settings = None


def _restore_settings():
    try:
        _sp = os.path.join(BASE, "settings.json")
        if _saved_settings is None:
            if os.path.exists(_sp):
                os.remove(_sp)
        else:
            with open(_sp, "wb") as _fh:
                _fh.write(_saved_settings)
    except Exception:
        pass


import atexit as _atexit
_atexit.register(_restore_settings)


import nexus.profiles as PROF  # noqa: E402
import nexus.phone_server as PSRV  # noqa: E402

_tmp = tempfile.mkdtemp(prefix="nexus-prof-test-")
PROF.PROFILES_DIR = _tmp

# ---------- perfis (produto: 1 unico perfil) ----------
ok, err = PROF.create_profile("Pedro", "1234", {"language": "pt-br",
                                                "sound_volume": 10})
check(ok, "perfil cria (%s)" % err)
ok, err = PROF.create_profile("Pedro", "", {})
check(not ok, "perfil duplicado recusa")
ok, err = PROF.create_profile("Ana", "12", {})
check(not ok, "pin curto recusa")
ok, err = PROF.create_profile("Ana", "", {})
check(not ok and "limite" in err, "2o perfil recusa (limite 1)")
check(PROF.verify_pin("Pedro", "1234"), "pin certo")
check(not PROF.verify_pin("Pedro", "0000"), "pin errado")
check(PROF.profile_has_pin("Pedro"), "tem pin?")


class StubApp:
    def __init__(self):
        self.settings = {"language": "pt-br", "sound_volume": 99}
        self.profile = None
        self.lang = "pt-br"
        self.infos = []
        self.refreshed = []

    def show_info_message(self, t, m):
        self.infos.append((t, m))

    def refresh_ui(self):
        self.refreshed.append(True)


app = StubApp()
PROF.switch_profile(app, "Pedro")
check(app.profile == "Pedro" and app.settings.get("language") == "pt-br"
      and app.refreshed, "login carrega snapshot")
app.settings["sound_volume"] = 55
PROF.switch_profile(app, None)
check(PROF.load_profile_data("Pedro").get("settings", {}).get(
    "sound_volume") == 55 and app.profile is None,
    "logout salva e vira convidado")
PROF.switch_profile(app, "Pedro")
check(app.profile == "Pedro" and app.settings.get("sound_volume") == 55,
      "login recarrega snapshot")
app2 = StubApp()
check(PROF.require_login(app2, "X") is False and app2.infos,
      "convidado bloqueia + avisa")
app2.profile = "Pedro"
check(PROF.require_login(app2, "X") is True, "logado passa")

# ---------- servidor ----------
root = tk.Tk()
root.geometry('900x700+100+100')
root.deiconify()
root.lift()
root.update()
try:
    # Hermetico: cursor parado sobre a janela dispara <Enter> e muda o
    # foco no meio dos checks. Estaciona no canto (so o inicio).
    import ctypes as _ct
    _ct.windll.user32.SetCursorPos(2, 2)
    print("INFO cursor estacionado no canto (nao mexa o mouse)", flush=True)
except Exception:
    pass


class SrvApp(StubApp):
    def __init__(self):
        super().__init__()
        self.root = root
        self.phone_server = None
        self.phone_queue = None
        self.after_calls = []
        try:
            self.root.after = (lambda ms, fn: self.after_calls.append(ms)
                               or "t")
        except Exception:
            pass


sapp = SrvApp()
sapp.settings = {"phone_tokens": {}}
srv = PSRV.PhoneServer(sapp, 0)
ok, err = srv.start()
check(ok and srv.running, "servidor sobe (%s)" % err)
try:
    port = srv.httpd.server_address[1]
except Exception:
    port = 0
check(port > 0, "porta efemera %s" % port)
base = "http://127.0.0.1:%d" % port


def _get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=5) as r:
            body = r.read()
            try:
                return r.status, json.loads(body.decode("utf-8"))
            except Exception:
                return r.status, body
    except Exception as e:
        try:
            return getattr(e, "code", 0), b""
        except Exception:
            return 0, b""


def _post(path, obj):
    try:
        req = urllib.request.Request(
            base + path, data=json.dumps(obj).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        try:
            code = getattr(e, "code", 0)
            body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            return code, json.loads(body or "{}")
        except Exception:
            return 0, {}


st, body = _get("/")
check(st == 200 and b"Nexus Remote" in body, "PWA servido sem token")
st, _ = _get("/app.js")
check(st == 200, "app.js servido")
st, _ = _get("/manifest.json")
check(st == 200, "manifest servido")
st, out = _post("/api/pair", {"code": "000000", "device": "t"})
check(st == 403, "codigo errado 403")
code = srv.new_code()
check(len(code) == 6 and code.isdigit(), "codigo 6 digitos")
st, out = _post("/api/pair", {"code": code, "device": "cel-teste"})
check(st == 200 and out.get("token"), "pareamento ok")
tok = out.get("token", "")
st, out = _post("/api/pair", {"code": code, "device": "t2"})
check(st == 403, "codigo uso unico")
st, out = _get("/api/status?token=%s" % tok)
check(st == 200 and out.get("ok"), "status com token")
st, out = _get("/api/status?token=lixo")
check(st == 403, "status sem token 403")
sapp.get_all_services = lambda: {"Netflix": {"icon": "X", "color": "#000"}}
st, out = _post("/api/services", {"token": tok})
check(st == 200 and out.get("services", [{}])[0].get("name") == "Netflix",
      "lista streamings")
st, out = _post("/api/input", {"token": "lixo", "cmd": "click", "args": {}})
check(st == 403, "input sem token 403")
st, out = _post("/api/input", {"token": tok, "cmd": "click",
                               "args": {"button": "left"}})
check(st == 200, "input enfileira")
st, out = _post("/api/launch", {"token": tok, "name": "Netflix"})
check(st == 200, "launch enfileira")
try:
    qsize = sapp.phone_queue.qsize()
except Exception:
    qsize = -1
check(qsize == 2, "fila tem 2 (qsize=%s)" % qsize)
st, out = _post("/api/unpair", {"token": tok})
check(st == 200, "desparear ok")
st, out = _get("/api/status?token=%s" % tok)
check(st == 403, "token revogado")
pl = PSRV.qr_payload(sapp, "123456")
check(set(("t", "ip", "port", "code", "v")) <= set(pl.keys()),
      "QR payload (%s)" % pl.get("ip", "?"))
ips = PSRV.lan_ips()
check(isinstance(ips, list) and len(ips) >= 1
      and all(i and not i.startswith("127.") for i in ips),
      "lan_ips (%s)" % ",".join(ips))
sapp.settings["phone_ip"] = ips[-1]
check(PSRV.chosen_ip(sapp) == ips[-1], "IP escolhido respeitado")
sapp.settings.pop("phone_ip", None)
check(PSRV.chosen_ip(sapp) == ips[0], "IP padrao e o primeiro")
photo = PSRV.make_qr_photo('{"t":"nexus"}', box=4)
check(photo is not None, "QR gera imagem")
srv.stop()
check(not srv.running, "servidor para")

# ---------- painel Controles: IPs + controle virtual ----------
from nexus.panels import ControlesPanel  # noqa: E402


class PSrvFake:
    running = True

    def __init__(self, app):
        self.app = app
        self.codes = []

    def paired_devices(self):
        return []

    def new_code(self):
        self.codes.append(True)
        return "123456"


papp = StubApp()
papp.main_frame = tk.Frame(root)
papp.main_frame.pack(fill='both', expand=True)
papp.sidepanel = None
papp.sidebar_visible = False
papp.theme_visible = False
papp.notif_visible = False
papp.close_sidebar = lambda: None
papp.close_theme_panel = lambda: None
papp.close_notif_panel = lambda: None
papp.update_all_focus = lambda: None
papp.nav_level = "items"
papp.form_focus = []
papp.form_idx = 0
papp.phone_server = PSrvFake(papp)
papp.lang = "pt-br"
papp.gamepad = None
papp.pad_devices = lambda: []
papp.show_gamepad_info = lambda: None
papp.open_keyboard = lambda *a: None
papp.pad_sensitivity = lambda: 12
papp.pad_scroll = lambda: 8
papp.pad_deadzone = lambda: 22
pp = ControlesPanel(papp)
pp.open()
root.update()
_ipbtns = [f for f in pp.focusables
            if f.get("kind") == "button"
            and f["widget"].cget("text").replace("\u2713 ", "").strip() in ips]
check(len(_ipbtns) == len(ips), "painel lista IPs (%d)" % len(ips))
pp.set_focus(pp.focusables.index(_ipbtns[-1]))
pp.press("south")
root.update()
check(papp.settings.get("phone_ip") == ips[-1], "trocar IP salva")
pp.close()

# ---------- execucao de comandos ----------
calls = []


class XApp(StubApp):
    def __init__(self):
        super().__init__()
        self.root = root


xapp = XApp()
import nexus.input as NINPUT  # noqa: E402
_real_move = NINPUT.mouse_move
_real_click = NINPUT.mouse_click
_real_tap = NINPUT.tap_key
NINPUT.mouse_move = lambda dx, dy: calls.append(("move", dx, dy))
NINPUT.mouse_click = lambda right=False: calls.append(("click", right))
NINPUT.tap_key = lambda vk: calls.append(("key", vk))
xapp._nav = lambda d: calls.append(("nav", d))
xapp.select_current = lambda: calls.append(("select",))
xapp.controller_back = lambda: calls.append(("back",))
xapp.tab_prev = lambda: calls.append(("tabprev",))
xapp.tab_next = lambda: calls.append(("tabnext",))
xapp.go_to_cards = lambda: calls.append(("cards",))
xapp.toggle_sidebar = lambda: calls.append(("sidebar",))
xapp.get_all_services = lambda: {"Netflix": {}}
xapp.launch_site_flow = lambda n: calls.append(("site", n))
xapp.launch_game = lambda n: calls.append(("game", n))
xapp.open_keyboard = lambda e: calls.append(("kb",))
xapp.kb_window = None
PSRV.exec_phone_action(xapp, "move", {"dx": 5, "dy": -3})
PSRV.exec_phone_action(xapp, "click", {"button": "right"})
PSRV.exec_phone_action(xapp, "key", {"vk": 13})
PSRV.exec_phone_action(xapp, "text", {"text": "oi"})
PSRV.exec_phone_action(xapp, "nav", {"dir": "left"})
PSRV.exec_phone_action(xapp, "select", {})
PSRV.exec_phone_action(xapp, "tab", {"dir": "prev"})
PSRV.exec_phone_action(xapp, "cards", {})
PSRV.exec_phone_action(xapp, "launch", {"name": "Netflix"})
PSRV.exec_phone_action(xapp, "launch", {"name": "Doom"})
PSRV.exec_phone_action(xapp, "keyboard", {})
PSRV.exec_phone_action(xapp, "back", {})
PSRV.exec_phone_action(xapp, "bogus", {})
check(("move", 5.0, -3.0) in calls and ("click", True) in calls
      and ("key", 13) in calls, "mouse+tecla")
check(("nav", "left") in calls and ("select",) in calls
      and ("back",) in calls and ("tabprev",) in calls
      and ("cards",) in calls, "nav/selecao")
check(("site", "Netflix") in calls and ("game", "Doom") in calls
      and ("kb",) in calls, "launch+teclado")
NINPUT.mouse_move = _real_move
NINPUT.mouse_click = _real_click
NINPUT.tap_key = _real_tap

print("TOTAL %d checks, %d falhas" % (COUNT[0], len(fails)), flush=True)
if fails:
    print("FALHAS:", fails, flush=True)
    sys.exit(1)
try:
    root.destroy()
except Exception:
    pass
print("PHONE OK", flush=True)
