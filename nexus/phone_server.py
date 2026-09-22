# -*- coding: utf-8 -*-
"""Controle pelo celular: servidor HTTP na rede local + pareamento.

- Liga/desliga pelo painel Perfil. Porta padrao 48721.
- Pareamento: Nexus mostra codigo de 6 digitos (+ QR). O celular manda
  o codigo uma vez e recebe um token (secrets), guardado em settings.
- Toda /api/* (menos arquivos do app) exige token valido.
- Comandos do celular entram numa fila e rodam na thread do Tk
  (phone_poll via root.after) — nunca tocar widget de outra thread.
"""

import hmac
import json
import os
import queue
import random
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT_DEFAULT = 48721
CODE_TTL = 600
PHONE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "phone_app")

MIME = {".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".webmanifest": "application/manifest+json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".css": "text/css; charset=utf-8"}


def lan_ip():
    """IP local para o celular alcançar (sem trafego real)."""
    try:
        ips = lan_ips()
        if ips:
            return ips[0]
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            try:
                s.close()
            except Exception:
                pass
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return ""


def lan_ips():
    """Todos os IPv4 locais (Wi-Fi, VPN, cabo...). Rede local (o celular
    esta nela) primeiro: 192.168/10/172.16 antes de VPNs e afins."""
    out = []
    try:
        for fam, _typ, _proto, _canon, sockaddr in socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET):
            ip = (sockaddr or [""])[0] or ""
            if ip and not ip.startswith("127.") and ip not in out:
                out.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in out:
                out.insert(0, ip)
        finally:
            try:
                s.close()
            except Exception:
                pass
    except Exception:
        pass

    def _lan_first(ip):
        try:
            if ip.startswith("192.168.") or ip.startswith("10."):
                return 0
            if ip.startswith("172."):
                second = int(ip.split(".")[1])
                if 16 <= second <= 31:
                    return 0
        except Exception:
            pass
        return 1

    try:
        out.sort(key=_lan_first)
    except Exception:
        pass
    return out


def chosen_ip(app):
    """IP escolhido no painel (ou o primeiro)."""
    try:
        ips = lan_ips()
        if not ips:
            return lan_ip()
        want = (app.settings.get("phone_ip", "") or "").strip()
        if want in ips:
            return want
        return ips[0]
    except Exception:
        return lan_ip()


def new_pairing_code():
    return "%06d" % random.randint(0, 999999)


def _services_payload(app):
    """Lista de streamings p/ o app (usada no GET e no POST)."""
    try:
        svcs = app.get_all_services() or {}
    except Exception:
        svcs = {}
    out = []
    try:
        for nm, inf in svcs.items():
            inf = inf or {}
            out.append({"name": nm,
                        "icon": inf.get("icon", ""),
                        "color": inf.get("color", "")})
    except Exception:
        pass
    return out


class PhoneServer:
    def __init__(self, app, port=PORT_DEFAULT):
        self.app = app
        try:
            self.port = int(port) if port is not None else PORT_DEFAULT
        except Exception:
            self.port = PORT_DEFAULT
        self.httpd = None
        self.thread = None
        self.tokens = {}
        self.codes = {}
        self.shown_code = ""
        try:
            saved = (app.settings.get("phone_tokens", {}) or {})
            if isinstance(saved, dict):
                for tok, info in saved.items():
                    if isinstance(info, dict):
                        self.tokens[str(tok)] = info
        except Exception:
            pass

    @property
    def running(self):
        try:
            return self.httpd is not None and self.thread is not None \
                and self.thread.is_alive()
        except Exception:
            return False

    def start(self):
        if self.running:
            return True, "on"
        try:
            app = self.app
            server = self

            class _Handler(BaseHTTPRequestHandler):
                # HTTP/1.1 = conexao persistente (o touchpad manda ~30
                # POSTs/s; recriar TCP a cada um gera lag).
                protocol_version = "HTTP/1.1"

                def log_message(self, *a):
                    pass

                def _send(self, code, body, ctype="application/json"):
                    try:
                        if isinstance(body, str):
                            body = body.encode("utf-8")
                        self.send_response(code)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(body)))
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception:
                        pass

                def _json(self, code, obj):
                    try:
                        self._send(code, json.dumps(obj))
                    except Exception:
                        pass

                def _body(self):
                    try:
                        n = int(self.headers.get("Content-Length", "0") or 0)
                    except Exception:
                        n = 0
                    try:
                        raw = self.rfile.read(max(0, n)) if n > 0 else b""
                    except Exception:
                        raw = b""
                    try:
                        return json.loads(raw.decode("utf-8") or "{}")
                    except Exception:
                        return {}

                def _authed(self, data):
                    try:
                        tok = str((data or {}).get("token", ""))
                        if not tok:
                            return None
                        for saved, info in list(server.tokens.items()):
                            if hmac.compare_digest(saved, tok):
                                return info
                    except Exception:
                        pass
                    return None

                def do_GET(self):
                    try:
                        path = urlparse(self.path).path or "/"
                    except Exception:
                        path = "/"
                    if path == "/":
                        path = "/index.html"
                    if not path.startswith("/api/"):
                        base = os.path.realpath(PHONE_DIR)
                        target = os.path.realpath(
                            os.path.join(base, path.lstrip("/").replace(
                                "/", os.sep)))
                        if not target.startswith(base) or \
                                not os.path.isfile(target):
                            self._send(404, "nf", "text/plain")
                            return
                        ext = os.path.splitext(target)[1].lower()
                        try:
                            with open(target, "rb") as fh:
                                data = fh.read()
                        except Exception:
                            self._send(404, "nf", "text/plain")
                            return
                        self._send(200, data,
                                   MIME.get(ext, "application/octet-stream"))
                        return
                    if path == "/api/status":
                        import urllib.parse as _up
                        try:
                            qs = _up.parse_qs(
                                urlparse(self.path).query or "")
                            tok = (qs.get("token", [""])[0] or "")
                        except Exception:
                            tok = ""
                        info = None
                        try:
                            for saved, inf in list(server.tokens.items()):
                                if hmac.compare_digest(saved, tok):
                                    info = inf
                                    break
                        except Exception:
                            info = None
                        if info is None:
                            self._json(403, {"ok": False})
                            return
                        try:
                            prof = getattr(app, "profile", None)
                        except Exception:
                            prof = None
                        self._json(200, {"ok": True, "profile": prof or ""})
                        return
                    if path == "/api/services":
                        # O app pede via GET (?token=); aceita aqui tambem
                        import urllib.parse as _up
                        try:
                            qs = _up.parse_qs(
                                urlparse(self.path).query or "")
                            tok = (qs.get("token", [""])[0] or "")
                        except Exception:
                            tok = ""
                        ok = False
                        try:
                            for saved in list(server.tokens.keys()):
                                if hmac.compare_digest(saved, tok):
                                    ok = True
                                    break
                        except Exception:
                            ok = False
                        if not ok:
                            self._json(403, {"ok": False})
                            return
                        self._json(200, {"ok": True,
                                         "services": _services_payload(app)})
                        return
                    self._json(404, {"ok": False})

                def do_POST(self):
                    try:
                        path = urlparse(self.path).path or "/"
                    except Exception:
                        path = "/"
                    data = self._body()
                    if path == "/api/pair":
                        code = str((data or {}).get("code", "")).strip()
                        device = str((data or {}).get("device", "")
                                     ).strip()[:40] or "celular"
                        ok, resp = server.pair(code, device)
                        self._json(200 if ok else 403, resp)
                        return
                    info = self._authed(data)
                    if info is None:
                        self._json(403, {"ok": False})
                        return
                    if path == "/api/services":
                        self._json(200, {"ok": True,
                                         "services": _services_payload(app)})
                        return
                    if path == "/api/input":
                        cmd = (data or {}).get("cmd", "")
                        args = (data or {}).get("args", {})
                        if not isinstance(args, dict):
                            args = {}
                        try:
                            app.phone_queue.put_nowait(
                                {"cmd": str(cmd), "args": args})
                            self._json(200, {"ok": True})
                        except Exception:
                            self._json(500, {"ok": False})
                        return
                    if path == "/api/launch":
                        name = str((data or {}).get("name", ""))
                        try:
                            app.phone_queue.put_nowait(
                                {"cmd": "launch", "args": {"name": name}})
                            self._json(200, {"ok": True})
                        except Exception:
                            self._json(500, {"ok": False})
                        return
                    if path == "/api/unpair":
                        try:
                            tok = str((data or {}).get("token", ""))
                            server.revoke_token(tok)
                        except Exception:
                            pass
                        self._json(200, {"ok": True})
                        return
                    self._json(404, {"ok": False})

            httpd = ThreadingHTTPServer(("0.0.0.0", self.port), _Handler)
            httpd.daemon_threads = True
            try:
                if hasattr(httpd, "socket") and hasattr(httpd.socket, "settimeout"):
                    httpd.socket.settimeout(30)
            except Exception:
                pass
            try:  # Sem Nagle: pacotes pequenos do touchpad saem na hora
                import socket as _sock
                httpd.socket.setsockopt(_sock.IPPROTO_TCP,
                                        _sock.TCP_NODELAY, 1)
            except Exception:
                pass
            self.httpd = httpd
            th = threading.Thread(target=httpd.serve_forever,
                                  kwargs={"poll_interval": 0.25},
                                  daemon=True)
            th.start()
            self.thread = th
            try:
                import queue as _q
                app.phone_queue = _q.Queue()
            except Exception:
                pass
            try:
                app.phone_server = self
                app.root.after(50, lambda: phone_poll(app))
            except Exception:
                pass
            return True, ""
        except Exception as e:
            try:
                self.httpd = None
                self.thread = None
            except Exception:
                pass
            return False, str(e)[:120]

    def stop(self):
        try:
            app = self.app
            if getattr(app, "phone_server", None) is self:
                app.phone_server = None
        except Exception:
            pass
        try:
            if self.httpd is not None:
                try:
                    self.httpd.shutdown()
                except Exception:
                    pass
                try:
                    self.httpd.server_close()
                except Exception:
                    pass
        except Exception:
            pass
        self.httpd = None
        self.thread = None
        return True

    def new_code(self):
        now = time.time()
        try:
            for code in [c for c, exp in list(self.codes.items())
                         if exp < now]:
                self.codes.pop(code, None)
            while True:
                code = new_pairing_code()
                if code not in self.codes:
                    break
            self.codes[code] = now + CODE_TTL
            self.shown_code = code
            return code
        except Exception:
            return ""

    def pair(self, code, device):
        """Troca codigo de 6 digitos por token. Uso unico."""
        try:
            code = str(code or "").strip()
            now = time.time()
            exp = self.codes.get(code)
            if not exp or exp < now:
                return False, {"ok": False}
            self.codes.pop(code, None)
            try:
                profile = getattr(self.app, "profile", None)
            except Exception:
                profile = None
            tok = secrets.token_urlsafe(24)
            info = {"device": device or "celular",
                    "profile": profile or "",
                    "created": int(now)}
            self.tokens[tok] = info
            try:
                saved = self.app.settings.get("phone_tokens", {}) or {}
                if not isinstance(saved, dict):
                    saved = {}
                saved[tok] = info
                self.app.settings["phone_tokens"] = saved
                from .config import save_settings as _save
                _save(self.app.settings)
            except Exception:
                pass
            return True, {"ok": True, "token": tok, "profile": profile or ""}
        except Exception:
            return False, {"ok": False}

    def revoke_token(self, tok):
        try:
            self.tokens.pop(tok, None)
            saved = self.app.settings.get("phone_tokens", {}) or {}
            if tok in saved:
                saved.pop(tok, None)
                self.app.settings["phone_tokens"] = saved
                from .config import save_settings as _save
                _save(self.app.settings)
            return True
        except Exception:
            return False

    def paired_devices(self):
        try:
            return [{"token": tok, "device": (inf or {}).get("device", ""),
                     "profile": (inf or {}).get("profile", "")}
                    for tok, inf in list(self.tokens.items())]
        except Exception:
            return []


def _phone_external_active(app):
    """Site/app aberto em foco? (remoto do controle OU navegador owned,
    que vale mesmo sem controle fisico). Se sim, setas do celular viram
    teclas de verdade p/ o app em foco, em vez de navegar no Nexus."""
    try:
        gp = getattr(app, "gamepad", None)
        if gp is not None and getattr(gp, "remote_active", False):
            return True
    except Exception:
        pass
    try:  # navegador owned aberto (monitorado por processo vivo)
        from .app_remote import BROWSER_PROCS
        if getattr(app, "browser_remote", None) is not None and any(
                p.poll() is None for p in BROWSER_PROCS):
            return True
    except Exception:
        pass
    return False


def phone_poll(app):
    """Roda na thread do Tk: executa 1 lote da fila do celular.
    50ms p/ o cursor nao arrastar (lote vazio custa quase nada)."""
    try:
        srv = getattr(app, "phone_server", None)
        if srv is None or not srv.running:
            return
    except Exception:
        return
    try:
        q = getattr(app, "phone_queue", None)
        if q is None:
            return
        for _ in range(20):
            try:
                item = q.get_nowait()
            except Exception:
                break
            try:
                exec_phone_action(app, (item or {}).get("cmd", ""),
                                  (item or {}).get("args", {}) or {})
            except Exception:
                pass
            try:
                q.task_done()
            except Exception:
                pass
    except Exception:
        pass
    try:
        app.root.after(50, lambda: phone_poll(app))
    except Exception:
        pass


def exec_phone_action(app, cmd, args):
    """Executa comando do celular (sempre na thread do Tk)."""
    try:
        cmd = str(cmd or "")
        args = args if isinstance(args, dict) else {}
        if cmd == "move":
            try:
                from .input import mouse_move
                mouse_move(float(args.get("dx", 0)),
                           float(args.get("dy", 0)))
            except Exception:
                pass
            return True
        if cmd == "click":
            try:
                from .input import mouse_click
                mouse_click(right=str(args.get("button", "left")) == "right")
            except Exception:
                pass
            return True
        if cmd == "wheel":
            try:
                from .input import mouse_wheel
                mouse_wheel(int(args.get("v", 0)), int(args.get("h", 0)))
            except Exception:
                pass
            return True
        if cmd == "key":
            try:
                from .input import tap_key
                tap_key(int(args.get("vk", 0)))
            except Exception:
                pass
            return True
        if cmd == "text":
            try:
                from .input import type_text
                type_text(app.root, str(args.get("text", ""))[:200])
            except Exception:
                pass
            return True
        if cmd == "nav":
            try:
                if _phone_external_active(app):
                    from .input import (tap_key, VK_UP, VK_DOWN,
                                        VK_LEFT, VK_RIGHT)
                    vk = {"up": VK_UP, "down": VK_DOWN,
                          "left": VK_LEFT, "right": VK_RIGHT}.get(
                              str(args.get("dir", "")))
                    if vk:
                        tap_key(vk)
                else:
                    app._nav(str(args.get("dir", "")))
            except Exception:
                pass
            return True
        if cmd == "select":
            try:
                if _phone_external_active(app):
                    from .input import tap_key, VK_RETURN
                    tap_key(VK_RETURN)
                else:
                    app.select_current()
            except Exception:
                pass
            return True
        if cmd == "back":
            try:
                if _phone_external_active(app):
                    from .input import tap_key, VK_ESCAPE
                    tap_key(VK_ESCAPE)
                else:
                    app.controller_back()
            except Exception:
                pass
            return True
        if cmd == "tab":
            try:
                if str(args.get("dir", "next")) == "prev":
                    app.tab_prev()
                else:
                    app.tab_next()
            except Exception:
                pass
            return True
        if cmd == "cards":
            try:
                app.go_to_cards()
            except Exception:
                pass
            return True
        if cmd == "sidebar":
            try:
                app.toggle_sidebar()
            except Exception:
                pass
            return True
        if cmd == "volume":
            try:
                from .audio import audio_set_master
                audio_set_master(max(0, min(100,
                                            int(args.get("level", 70)))) / 100.0)
            except Exception:
                pass
            return True
        if cmd == "volstep":
            try:
                from .audio import audio_get_master, audio_set_master
                cur = audio_get_master()
                if cur is None:
                    return True
                d = -0.05 if str(args.get("dir", "")) == "-1" \
                    or int(args.get("dir", 1)) < 0 else 0.05
                audio_set_master(max(0.0, min(1.0, cur + d)))
            except Exception:
                pass
            return True
        if cmd == "launch":
            try:
                name = str(args.get("name", ""))
                svcs = {}
                try:
                    svcs = app.get_all_services() or {}
                except Exception:
                    pass
                if name in svcs:
                    try:
                        app.launch_site_flow(name)
                    except Exception:
                        pass
                else:
                    try:
                        app.launch_game(name)
                    except Exception:
                        pass
            except Exception:
                pass
            return True
        if cmd == "pad":
            # Botao logico do controle (south/east/west/north/lb/rb/l2/r2/
            # back/start/l3/r3): mesmo despacho do gamepad fisico, com o
            # remapeamento do usuario (menu ou app em foco).
            try:
                from .pad import LOGICAL_BUTTONS
                logical = str(args.get("button", "")).strip().lower()
                if logical not in LOGICAL_BUTTONS:
                    return True
                gp = getattr(app, "gamepad", None)
                if gp is not None and getattr(gp, "remote_active", False):
                    gp.do_remote_button(logical)
                elif gp is not None:
                    gp.press_menu_button(logical)
                else:  # sem gamepad: basico do Nexus
                    if logical == "south":
                        app.select_current()
                    elif logical == "east":
                        app.controller_back()
            except Exception:
                pass
            return True
        if cmd == "exit_remote":
            try:
                app.exit_remote_mode()
            except Exception:
                pass
            return True
        if cmd == "keyboard":
            try:
                app.open_keyboard(None)
            except Exception:
                pass
            return True
        if cmd == "kb_close":
            try:
                kb = getattr(app, "kb_window", None)
                if kb is not None:
                    kb.close()
            except Exception:
                pass
            return True
        return False
    except Exception:
        return False


def qr_payload(app, code):
    try:
        return {"t": "nexus", "ip": chosen_ip(app),
                "port": app_phone_port(app), "code": code, "v": 1}
    except Exception:
        return {}


def qr_url(app, code):
    """URL direta p/ o QR: a camera nativa abre o Nexus Remote no
    navegador (com o codigo), em vez de pesquisar o texto no Google."""
    try:
        return "http://%s:%s/?code=%s" % (chosen_ip(app),
                                          app_phone_port(app), code)
    except Exception:
        return ""


def app_phone_port(app):
    try:
        srv = getattr(app, "phone_server", None)
        if srv is not None:
            return int(srv.port)
    except Exception:
        pass
    return PORT_DEFAULT


def make_qr_photo(payload_str, box=5):
    """PhotoImage do QR (None se lib ausente)."""
    try:
        import qrcode
        from PIL import ImageTk
        qr = qrcode.QRCode(box_size=box, border=2)
        qr.add_data(payload_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black",
                            back_color="white").convert("RGB")
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def start_phone_server(app, port=PORT_DEFAULT):
    try:
        old = getattr(app, "phone_server", None)
        if old is not None:
            try:
                if old.running:
                    return True, ""
            except Exception:
                pass
            try:
                old.stop()
            except Exception:
                pass
        srv = PhoneServer(app, port)
        return srv.start()
    except Exception as e:
        return False, str(e)[:120]


def stop_phone_server(app):
    try:
        srv = getattr(app, "phone_server", None)
        if srv is not None:
            srv.stop()
        app.phone_server = None
        return True
    except Exception:
        return False
