# -*- coding: utf-8 -*-
"""Teclado/mouse virtuais + deteccao de campo de texto (extraido sem alteracao)."""

import ctypes
import subprocess
import threading
import time

# Traduz o controle em teclado/mouse virtuais para comandar o app aberto.
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
WHEEL_DELTA = 120

VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_F = 0x46
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_BACK = 0x08
VK_TAB = 0x09
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_F7 = 0x76
VK_F8 = 0x77
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOL_DOWN = 0xAE
VK_VOL_UP = 0xAF


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT_UNION)]


_SendInput = ctypes.windll.user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint


def tap_key(vk):
    for flags in (0, KEYEVENTF_KEYUP):
        inp = _INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ii.ki = _KEYBDINPUT(vk, 0, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def key_down(vk):
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ii.ki = _KEYBDINPUT(vk, 0, 0, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def key_up(vk):
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ii.ki = _KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def type_text(root, text):
    """Tecla texto de verdade na janela em foco (teclado virtual global).
    Letras/numeros vao por VK; simbolos via Ctrl+V (a prova de layout ABNT)."""
    for ch in text:
        try:
            if "a" <= ch <= "z" or "A" <= ch <= "Z":
                upper = ch.isupper()
                if upper:
                    key_down(VK_SHIFT)
                tap_key(ord(ch.upper()))
                if upper:
                    key_up(VK_SHIFT)
            elif "0" <= ch <= "9":
                tap_key(ord(ch))
            elif ch == " ":
                tap_key(VK_SPACE)
            elif ch == "\n":
                tap_key(VK_RETURN)
            else:
                root.clipboard_clear()
                root.clipboard_append(ch)
                root.update_idletasks()
                key_down(VK_CONTROL)
                tap_key(0x56)  # V
                key_up(VK_CONTROL)
                time.sleep(0.02)
        except Exception:
            pass


try:
    import winsound as _winsound
except Exception:
    _winsound = None

_NAV_TICK_WAV = {}


def _nav_tick_wav(vol=10):
    """Pop grave e curto (sine 330Hz, 60ms, decaimento suave).
    Gerado em memoria por volume (0-100): sem arquivo, sem clique."""
    try:
        vol = max(0, min(100, int(vol)))
    except Exception:
        vol = 10
    if vol in _NAV_TICK_WAV:
        return _NAV_TICK_WAV[vol]
    import math
    import struct
    rate = 22050
    n = rate * 60 // 1000
    amp = 0.5 * (vol / 100.0)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 70.0)
        s = math.sin(2.0 * math.pi * 330.0 * t) * env * amp
        frames += struct.pack("<h", int(s * 32767))
    head = (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) +
            b"data" + struct.pack("<I", len(frames)))
    _NAV_TICK_WAV[vol] = head + bytes(frames)
    return _NAV_TICK_WAV[vol]


_TICK_LOCK = threading.Lock()
_TICK_STATE = {"playing": False, "pending": None, "last": 0.0}
_TICK_GAP = 0.09


def _play_nav_tick(vol=10):
    """Toca o blip. Retorna (ok, erro): o dialogo de Som mostra o erro.
    Thread + PlaySound bloqueante: SND_ASYNC da memoria falha em alguns
    drivers ('Cannot play asynchronously from memory') e era engolido.
    Coalesce: rajada rapida nao empilha (1 thread toca no maximo o
    primeiro + o ultimo, com 90ms entre inicios)."""
    try:
        vol = max(0, min(100, int(vol)))
    except Exception:
        return False, "volume invalido"
    try:
        if _winsound is None:
            return False, "winsound indisponivel"
        data = _nav_tick_wav(vol)
    except Exception as e:
        return False, str(e)[:120]
    try:
        with _TICK_LOCK:
            _TICK_STATE["pending"] = data
            if _TICK_STATE["playing"]:
                return True, ""
            _TICK_STATE["playing"] = True
        threading.Thread(target=_tick_worker, daemon=True).start()
        return True, ""
    except Exception as e:
        return False, str(e)[:120]


def _tick_worker():
    while True:
        try:
            wait = _TICK_GAP - (time.monotonic() - _TICK_STATE["last"])
            if wait > 0:
                time.sleep(wait)
            with _TICK_LOCK:
                data = _TICK_STATE["pending"]
                _TICK_STATE["pending"] = None
                if data is None:
                    _TICK_STATE["playing"] = False
                    return
                _TICK_STATE["last"] = time.monotonic()
        except Exception:
            try:
                with _TICK_LOCK:
                    _TICK_STATE["playing"] = False
            except Exception:
                pass
            return
        try:
            _winsound.PlaySound(data, _winsound.SND_MEMORY)
        except Exception:
            pass


def _play_test_tone():
    """Tom de diagnostico em thread (mesmo motivo acima)."""
    try:
        if _winsound is None:
            return False, "winsound indisponivel"
        data = _nav_test_wav()
    except Exception as e:
        return False, str(e)[:120]
    try:
        threading.Thread(target=_winsound.PlaySound, args=(data, _winsound.SND_MEMORY),
                         daemon=True).start()
        return True, ""
    except Exception as e:
        return False, str(e)[:120]


def _nav_test_wav():
    """Tom de teste: 2 notas (660 + 880Hz), 400ms, alto. P/ diagnostico."""
    import math
    import struct
    rate = 22050
    notes = [(660.0, 200), (880.0, 200)]
    frames = bytearray()
    for freq, ms in notes:
        n = rate * ms // 1000
        for i in range(n):
            t = i / rate
            env = min(1.0, t * 60.0) * math.exp(-t * 6.0)
            s = math.sin(2.0 * math.pi * freq * t) * env * 0.6
            frames += struct.pack("<h", int(s * 32767))
    head = (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) +
            b"data" + struct.pack("<I", len(frames)))
    return head + bytes(frames)


def ctrl_tab(prev=False):
    """Troca de aba no app em foco (Ctrl+Tab / Ctrl+Shift+Tab)."""
    try:
        key_down(VK_CONTROL)
        if prev:
            key_down(VK_SHIFT)
        tap_key(VK_TAB)
        if prev:
            key_up(VK_SHIFT)
        key_up(VK_CONTROL)
    except Exception:
        pass


def mouse_move(dx, dy):
    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.ii.mi = _MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, None)
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def mouse_click(right=False):
    down, up = ((MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP) if right
                else (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP))
    for flags in (down, up):
        inp = _INPUT()
        inp.type = INPUT_MOUSE
        inp.ii.mi = _MOUSEINPUT(0, 0, 0, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def mouse_wheel(v_notches=0, h_notches=0):
    """Rolagem: v>0 sobe, h>0 para a direita (em encaixes de 120)."""
    for flags, n in ((MOUSEEVENTF_WHEEL, int(v_notches)),
                     (MOUSEEVENTF_HWHEEL, int(h_notches))):
        if not n:
            continue
        inp = _INPUT()
        inp.type = INPUT_MOUSE
        inp.ii.mi = _MOUSEINPUT(0, 0, n * WHEEL_DELTA, flags, 0, None)
        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def stick_response(v, deadzone=0.22):
    """Resposta linear a partir da zona morta: reage na hora, sem rampa lenta."""
    a = abs(v)
    if a < deadzone:
        return 0.0
    return (1.0 if v > 0 else -1.0) * (a - deadzone) / (1.0 - deadzone)


_UIA_PS = (
    "Add-Type -AssemblyName UIAutomationClient; "
    "$el = [System.Windows.Automation.AutomationElement]::FocusedElement; "
    "if ($el -eq $null) { 'none' } "
    "else { $el.Current.ControlType.ProgrammaticName }"
)
_UIA_TEXT_TYPES = frozenset(["ControlType.Edit"])
_EDIT_CLASS_NAMES = frozenset([
    "edit", "richedit20wpt", "richedit20a", "richedit50w", "richedit50a",
    "_wwg", "_wwn",
])


def _debug_log(msg):
    """Log temporario de diagnostico (bug Y->F). Nao falha o app se der erro."""
    try:
        import datetime
        import os
        base = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(base, "..", "nexus_debug.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def _uia_focused_control(timeout=4):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _UIA_PS],
        capture_output=True, text=True, timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW)
    lines = (out.stdout or "").strip().splitlines()
    result = lines[-1].strip() if lines else None
    _debug_log("UIA stdout=%r stderr=%r -> result=%r" % (
        (out.stdout or "")[:200], (out.stderr or "")[:200], result))
    return result


def _caret_visible():
    try:
        u = ctypes.windll.user32

        class _RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        class _GUITHREADINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_ulong), ("flags", ctypes.c_ulong),
                        ("hwndActive", ctypes.c_void_p),
                        ("hwndFocus", ctypes.c_void_p),
                        ("hwndCapture", ctypes.c_void_p),
                        ("hwndMenuOwner", ctypes.c_void_p),
                        ("hwndMoveSize", ctypes.c_void_p),
                        ("hwndCaret", ctypes.c_void_p),
                        ("rcCaret", _RECT)]

        try:
            u.GetGUIThreadInfo.argtypes = [ctypes.c_ulong,
                                           ctypes.POINTER(_GUITHREADINFO)]
            u.GetGUIThreadInfo.restype = ctypes.c_bool
            u.GetClassNameW.argtypes = [ctypes.c_void_p,
                                        ctypes.c_wchar_p, ctypes.c_int]
            u.GetClassNameW.restype = ctypes.c_int
        except Exception:
            pass
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not u.GetGUIThreadInfo(0, ctypes.byref(info)):
            return False
        if info.hwndCaret:
            return True
        if info.hwndFocus:
            try:
                buf = ctypes.create_unicode_buffer(128)
                if u.GetClassNameW(info.hwndFocus, buf, 128) > 0:
                    if buf.value.lower() in _EDIT_CLASS_NAMES:
                        return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def focused_is_text_field():
    """True se o foco atual (outro app) esta num campo de texto."""
    try:
        name = _uia_focused_control()
        if name and name != "none":
            decision = name in _UIA_TEXT_TYPES
            _debug_log("focused_is_text_field: via UIA, name=%r -> %r" % (name, decision))
            return decision
        _debug_log("focused_is_text_field: UIA sem elemento util (name=%r), indo pro caret" % name)
    except Exception as e:
        _debug_log("focused_is_text_field: UIA falhou (%r), indo pro caret" % e)
    try:
        decision = _caret_visible()
        _debug_log("focused_is_text_field: via caret -> %r" % decision)
        return decision
    except Exception as e:
        _debug_log("focused_is_text_field: caret tambem falhou (%r) -> False" % e)
        return False


def remote_button_allowed(action):
    """No remoto, atalhos de tecla unica (F do fullscreen) nao disparam
    com campo de texto focado: virariam letra no meio da digitacao.
    Usa cache curto: cada consulta gera um powershell (~0,5s) e nao pode
    travar o loop do controle a cada aperto do Y."""
    if action != "fullscreen":
        return True
    try:
        return not focused_is_text_field_cached()
    except Exception:
        return True


_FOCUS_CACHE = {"t": None, "v": False}


def focused_is_text_field_cached(ttl=1.0):
    """Versao com cache p/ caminho sincrono (loop do gamepad).
    t=None na primeira vez: sempre roda a checagem real, nunca o default."""
    try:
        now = time.monotonic()
    except Exception:
        return focused_is_text_field()
    try:
        _t = _FOCUS_CACHE["t"]
        if _t is not None and now - _t < ttl:
            return _FOCUS_CACHE["v"]
    except Exception:
        pass
    v = focused_is_text_field()
    try:
        _FOCUS_CACHE["t"] = now
        _FOCUS_CACHE["v"] = bool(v)
    except Exception:
        pass
    return v
