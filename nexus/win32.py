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
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

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
    """Tira bordas e estica a janela p/ tela cheia. Best-effort por app."""
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
        x, y, w, h = _monitor_rect(monitor_hwnd)
        return bool(_SetWindowPos(hwnd, None, x, y, w, h,
                                  SWP_FRAMECHANGED | SWP_SHOWWINDOW))
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


def _set_cursor_pos(x, y):
    try:
        if _WIN32_OK:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            return True
    except Exception:
        pass
    return False


def foreground_hwnd():
    try:
        if _WIN32_OK:
            return _GetForegroundWindow()
    except Exception:
        pass
    return None


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
