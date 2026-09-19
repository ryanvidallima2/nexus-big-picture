# -*- coding: utf-8 -*-
"""Janelas Win32: fullscreen sem bordas + hwnd (extraido sem alteracao)."""

import ctypes
import os
import sys

# Forca a janela do app aberto a tela cheia sem bordas (modo big picture).
# Forca a janela do app aberto a tela cheia sem bordas (modo big picture).
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_EX_DLGMODALFRAME = 0x00000001
WS_EX_WINDOWEDGE = 0x00000100
WS_EX_CLIENTEDGE = 0x00000200
WS_EX_STATICEDGE = 0x00020000
WS_EX_APPWINDOW = 0x00040000
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

try:
    _user32 = ctypes.windll.user32
    _EnumWindows = _user32.EnumWindows
    _EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p),
                             ctypes.c_void_p]
    _EnumWindows.restype = ctypes.c_bool
    _IsWindowVisible = _user32.IsWindowVisible
    _IsWindowVisible.argtypes = [ctypes.c_void_p]
    _IsWindowVisible.restype = ctypes.c_bool
    _GetWindowTextW = _user32.GetWindowTextW
    _GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    _GetWindowTextW.restype = ctypes.c_int
    _GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
    _GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    _GetWindowThreadProcessId.restype = ctypes.c_ulong
    _GetWindowLongPtrW = _user32.GetWindowLongPtrW
    _GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _GetWindowLongPtrW.restype = ctypes.c_void_p
    _SetWindowLongPtrW = _user32.SetWindowLongPtrW
    _SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    _SetWindowLongPtrW.restype = ctypes.c_void_p
    _SetWindowPos = _user32.SetWindowPos
    _SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    _SetWindowPos.restype = ctypes.c_bool
    _GetForegroundWindow = _user32.GetForegroundWindow
    _GetForegroundWindow.restype = ctypes.c_void_p
    _IsWindow = _user32.IsWindow
    _IsWindow.argtypes = [ctypes.c_void_p]
    _IsWindow.restype = ctypes.c_bool
    _MonitorFromWindow = _user32.MonitorFromWindow
    _MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    _MonitorFromWindow.restype = ctypes.c_void_p
    _GetMonitorInfoW = _user32.GetMonitorInfoW
    _WIN32_OK = True
except Exception:
    _WIN32_OK = False


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", _RECT),
                ("rcWork", _RECT), ("dwFlags", ctypes.c_ulong)]


def _top_level_windows():
    """[(hwnd, pid, titulo)] das janelas visiveis de outros processos."""
    out = []
    if not _WIN32_OK:
        return out
    try:
        mine = os.getpid()

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(hwnd, _lparam):
            try:
                if not _IsWindowVisible(hwnd):
                    return True
                buf = ctypes.create_unicode_buffer(256)
                if _GetWindowTextW(hwnd, buf, 256) <= 0:
                    return True
                pid = ctypes.c_ulong()
                _GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != mine:
                    out.append((hwnd, pid.value, buf.value))
            except Exception:
                pass
            return True

        _EnumWindows(_cb, None)
    except Exception:
        pass
    return out


def _monitor_rect(hwnd=None):
    """Retangulo do monitor (x, y, w, h). Cai para a tela primaria."""
    if _WIN32_OK and hwnd:
        try:
            mon = _MonitorFromWindow(hwnd, 1)
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if _GetMonitorInfoW(mon, ctypes.byref(mi)):
                r = mi.rcMonitor
                return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        except Exception:
            pass
    try:
        g = ctypes.windll.user32.GetSystemMetrics
        return (0, 0, g(0), g(1))
    except Exception:
        return (0, 0, 1920, 1080)


def force_borderless_fullscreen(hwnd, monitor_hwnd=None):
    """Tira bordas e estica a janela p/ tela cheia. Best-effort por app.
    Igual a receita do F11 (Maximized + DWM sem cantos): cobre a tarefa
    desde o primeiro abrir, sem precisar alternar."""
    if not _WIN32_OK or not hwnd:
        return False
    try:
        style = _GetWindowLongPtrW(hwnd, GWL_STYLE)
        style = int(style) & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        _SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        exstyle = _GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        exstyle = int(exstyle) & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE
                                   | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE)
        _SetWindowLongPtrW(hwnd, GWL_EXSTYLE, exstyle)
        try:
            _DwmAttr = ctypes.windll.dwmapi.DwmSetWindowAttribute
            _DwmAttr.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                 ctypes.c_void_p, ctypes.c_uint]
            _DwmAttr.restype = ctypes.c_long
            _DwmAttr(hwnd, 33, ctypes.byref(ctypes.c_int(1)),
                     ctypes.sizeof(ctypes.c_int))
            _DwmAttr(hwnd, 34, ctypes.byref(ctypes.c_int(0xFFFFFFFE)),
                     ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass
        x, y, w, h = _monitor_rect(monitor_hwnd)
        if not bool(_SetWindowPos(hwnd, None, x, y, w, h,
                                  SWP_FRAMECHANGED | SWP_SHOWWINDOW)):
            return False
        try:
            _ShowWindow = ctypes.windll.user32.ShowWindow
            _ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
            _ShowWindow.restype = ctypes.c_bool
            _ShowWindow(hwnd, 3)
        except Exception:
            pass
        ensure_fullscreen_top(hwnd)
        return True
    except Exception:
        return False


def _hwnd_alive(hwnd):
    try:
        return bool(_WIN32_OK and hwnd and _IsWindow(hwnd))
    except Exception:
        return False


def bring_to_front(hwnd):
    try:
        if _WIN32_OK and hwnd:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def ensure_fullscreen_top(hwnd):
    """Flash topmost SEM roubar foco: cobre a tarefa em fullscreen.
    O topmost e retirado em seguida; a posicao no z-order permanece."""
    if not _WIN32_OK or not hwnd:
        return False
    try:
        _SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0,
                      SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        _SetWindowPos(hwnd, ctypes.c_void_p(-2), 0, 0, 0, 0,
                      SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        return True
    except Exception:
        pass
    return False


def _set_cursor_pos(x, y):
    try:
        if _WIN32_OK:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            return True
    except Exception:
        pass
    return False


try:
    _ShowCursor = _user32.ShowCursor
    _ShowCursor.argtypes = [ctypes.c_bool]
    _ShowCursor.restype = ctypes.c_int
    _WIN32_CURSOR_OK = True
except Exception:
    _WIN32_CURSOR_OK = False

_cursor_hidden_by_us = False


def hide_cursor_for_gamepad():
    """Esconde o cursor (1x, com trava): controle em uso."""
    global _cursor_hidden_by_us
    try:
        if _cursor_hidden_by_us:
            return True
        if _WIN32_CURSOR_OK:
            _ShowCursor(False)
        _cursor_hidden_by_us = True
        return True
    except Exception:
        return False


def show_cursor_for_mouse():
    """Mostra o cursor de volta (1x, com trava): mouse em uso."""
    global _cursor_hidden_by_us
    try:
        if not _cursor_hidden_by_us:
            return True
        if _WIN32_CURSOR_OK:
            _ShowCursor(True)
        _cursor_hidden_by_us = False
        return True
    except Exception:
        return False


def ensure_cursor_visible():
    """Garante cursor visivel (saida/crash: nao some no Windows)."""
    return show_cursor_for_mouse()


def foreground_hwnd():
    try:
        if _WIN32_OK:
            return _GetForegroundWindow()
    except Exception:
        pass
    return None


def kill_process_tree(proc):
    """Mata o proc E os filhos (WebView2 orfa trava o perfil e o clear
    apos sair falha em silencio). Best-effort, nunca levanta."""
    try:
        pid = int(getattr(proc, "pid", 0) or 0)
    except Exception:
        pid = 0
    if pid:
        try:
            import subprocess as _sp
            _sp.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=15,
                    creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        except Exception:
            pass
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass
    return True


# Barra de titulo escura (DWM) das janelas tkinter (extraido sem alteracao).
def _log_dark_result(tag, hwnd, hrs):
    try:
        base = os.path.dirname(os.path.realpath(sys.argv[0] or "."))
        with open(os.path.join(base, "nexus_error.log"), "a", encoding="utf-8") as f:
            f.write(f"DARK {tag} hwnd={hwnd:#x} hrs="
                    f"{[hex(h) if h is not None else None for h in hrs]}\n")
    except Exception:
        pass


def _apply_dark_title(widget, tag="win"):
    # Barra de titulo escura na JANELA CERTA: o HWND que o DWM gerencia
    # e o PAI do winfo_id (o id cru e o filho interno -> E_HANDLE).
    # Tenta attr 20 e 19; depois forca o redesenho da moldura, senao o
    # Windows pode ignorar o atributo aplicado antes da janela abrir.
    # So registra log se o attr 20 falhar (para diagnostico).
    try:
        inner = int(widget.winfo_id())
        try:
            _get_parent = ctypes.windll.user32.GetParent
            _get_parent.argtypes = [ctypes.c_void_p]
            _get_parent.restype = ctypes.c_void_p
            outer = _get_parent(inner)
            hwnd = outer if outer else inner
        except Exception:
            hwnd = inner
        hrs = []
        v = ctypes.c_int(1)
        for attr in (20, 19):
            try:
                hrs.append(ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)))
            except Exception:
                hrs.append(None)
        try:
            _set_pos = ctypes.windll.user32.SetWindowPos
            _set_pos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                 ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            _set_pos.restype = ctypes.c_bool
            _set_pos(hwnd, 0, 0, 0, 0, 0, 0x37)
        except Exception:
            pass
        if hrs and hrs[0] != 0:
            _log_dark_result(tag, hwnd, hrs)
    except Exception:
        pass


def _apply_dark_title_later(widget, delay=150, tag="win"):
    try:
        widget.after(delay, lambda: _apply_dark_title(widget, tag))
    except Exception:
        pass


def force_topmost_noactivate(widget):
    """Joga a janela p/ frente SEM roubar o foco (teclado virtual sobre
    app/site em tela cheia). Retorna True se o Windows aceitou."""
    try:
        inner = int(widget.winfo_id())
    except Exception:
        return False
    if not _WIN32_OK:
        return False
    try:
        try:
            _get_parent = ctypes.windll.user32.GetParent
            _get_parent.argtypes = [ctypes.c_void_p]
            _get_parent.restype = ctypes.c_void_p
            outer = _get_parent(inner)
            hwnd = outer if outer else inner
        except Exception:
            hwnd = inner
        HWND_TOPMOST = ctypes.c_void_p(-1)
        flags = 0x0001 | 0x0002 | 0x0010 | 0x0040  # NOSIZE|NOMOVE|NOACTIVATE|SHOW
        return bool(_SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags))
    except Exception:
        return False


GWLP_HWNDPARENT = -8
SW_HIDE = 0
SW_SHOW = 5
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9


def find_window_by_title(title):
    """HWND da janela top-level com o titulo exato (ou None)."""
    try:
        if _WIN32_OK and title:
            _FindWindowW = ctypes.windll.user32.FindWindowW
            _FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
            _FindWindowW.restype = ctypes.c_void_p
            hwnd = _FindWindowW(None, title)
            if hwnd:
                return hwnd
    except Exception:
        pass
    return None


def find_window_by_title_pid(title, pid):
    """Como acima, mas so aceita se o PID bater (titulos duplicados:
    outra instancia, janela velha de teste)."""
    try:
        if not (_WIN32_OK and title and pid):
            return None
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _cb(hwnd, _lparam):
            try:
                buf = ctypes.create_unicode_buffer(256)
                if _GetWindowTextW(hwnd, buf, 256) > 0 and buf.value == title:
                    _pid = ctypes.c_ulong()
                    _GetWindowThreadProcessId(hwnd, ctypes.byref(_pid))
                    if int(_pid.value) == int(pid):
                        found.append(hwnd)
            except Exception:
                pass
            return True

        _EnumWindows(_cb, None)
        if found:
            return found[0]
    except Exception:
        pass
    return None


def is_window_visible(hwnd):
    try:
        if _WIN32_OK and hwnd:
            return bool(_IsWindowVisible(hwnd))
    except Exception:
        pass
    return False


def show_window(hwnd, cmd):
    """ShowWindow generico (SW_RESTORE/SW_SHOW/SW_MINIMIZE)."""
    try:
        if _WIN32_OK and hwnd:
            _ShowWindow = ctypes.windll.user32.ShowWindow
            _ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
            _ShowWindow.restype = ctypes.c_bool
            return bool(_ShowWindow(hwnd, int(cmd)))
    except Exception:
        pass
    return False


def set_owner_window(child_hwnd, owner_hwnd):
    """Torna a janela owned (some do Alt+Tab e minimiza/restaura junto
    do dono, sem virar filha: input, foco e F11 intactos)."""
    if not _WIN32_OK or not child_hwnd or not owner_hwnd:
        return False
    try:
        _SetWindowLongPtrW(child_hwnd, GWLP_HWNDPARENT, owner_hwnd)
    except Exception:
        return False
    try:
        exstyle = int(_GetWindowLongPtrW(child_hwnd, GWL_EXSTYLE))
        exstyle &= ~WS_EX_APPWINDOW  # APPWINDOW furaria o owned no Alt+Tab
        _SetWindowLongPtrW(child_hwnd, GWL_EXSTYLE, exstyle)
    except Exception:
        pass
    return True
