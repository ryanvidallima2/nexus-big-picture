# -*- coding: utf-8 -*-
"""Volume master do dispositivo (Core Audio MMDevice via ctypes).

Usado pelo preset "volume padrao": ao abrir um app/site, o Nexus poe o
volume geral no padrao e restaura ao sair. Sem dependencias novas.
Tudo retorna None/False em vez de levantar (sem audio, sem COM, etc.).
"""

import ctypes


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)]


_LPGUID = ctypes.POINTER(_GUID)
_LPVOID = ctypes.c_void_p
_HRESULT = ctypes.c_long


def _makeguid(s):
    a, b, c, d, e = s.split("-")
    g = _GUID()
    g.Data1 = int(a, 16)
    g.Data2 = int(b, 16)
    g.Data3 = int(c, 16)
    g.Data4 = (ctypes.c_ubyte * 8)(*bytes.fromhex(d + e))
    return g


_CLSID_MMDeviceEnumerator = _makeguid("BCDE0395-E52F-467C-8E3D-C4579291692E")
# IID verificado empiricamente (o "de livro" ...63688E6 devolve
# E_NOINTERFACE; ...63617E6 abre de verdade).
_IID_IMMDeviceEnumerator = _makeguid("A95664D2-9614-4F35-A746-DE8DB63617E6")
_IID_IMMDeviceEnumerator_ALT = _makeguid("A95664D2-9614-4F35-A746-DE8DB63688E6")
_IID_IAudioEndpointVolume = _makeguid("5CDF2C82-841E-4546-9722-0CF74078229A")
_CLSCTX_INPROC_SERVER = 0x1
_E_RENDER = 0
_E_MULTIMEDIA = 1


def _ole32():
    try:
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        ole32.CoInitializeEx.argtypes = [_LPVOID, ctypes.c_ulong]
        ole32.CoInitializeEx.restype = _HRESULT
        ole32.CoCreateInstance.argtypes = [
            _LPGUID, _LPVOID, ctypes.c_ulong, _LPGUID,
            ctypes.POINTER(_LPVOID)]
        ole32.CoCreateInstance.restype = _HRESULT
        return ole32
    except Exception:
        return None


def _endpoint_volume():
    """Interface IAudioEndpointVolume do render padrao (ou None)."""
    try:
        ole32 = _ole32()
        if ole32 is None:
            return None
        hr = ole32.CoInitializeEx(None, 0x2)
        if hr not in (0, 1, 0x80010106):
            return None
        WINFUNCTYPE = ctypes.WINFUNCTYPE
        enum = _LPVOID()
        hr = ole32.CoCreateInstance(
            ctypes.byref(_CLSID_MMDeviceEnumerator), None,
            _CLSCTX_INPROC_SERVER,
            ctypes.byref(_IID_IMMDeviceEnumerator),
            ctypes.byref(enum))
        if hr != 0:
            hr = ole32.CoCreateInstance(
                ctypes.byref(_CLSID_MMDeviceEnumerator), None,
                _CLSCTX_INPROC_SERVER,
                ctypes.byref(_IID_IMMDeviceEnumerator_ALT),
                ctypes.byref(enum))
            if hr != 0:
                return None
        vtbl = ctypes.cast(enum.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_default = WINFUNCTYPE(_HRESULT, _LPVOID, ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.POINTER(_LPVOID))(vtbl[0][4])
        dev = _LPVOID()
        if fn_default(enum, _E_RENDER, _E_MULTIMEDIA,
                      ctypes.byref(dev)) != 0:
            return None
        dvt = ctypes.cast(dev.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_act = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID, ctypes.c_ulong,
                             _LPVOID,
                             ctypes.POINTER(_LPVOID))(dvt[0][3])
        epv = _LPVOID()
        if fn_act(dev, ctypes.byref(_IID_IAudioEndpointVolume),
                  _CLSCTX_INPROC_SERVER, None, ctypes.byref(epv)) != 0:
            return None
        return ctypes.cast(epv.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
    except Exception:
        return None


def audio_get_master():
    """Volume master 0.0-1.0 (None se indisponivel)."""
    try:
        evt = _endpoint_volume()
        if not evt:
            return None
        fn_get = ctypes.WINFUNCTYPE(_HRESULT, _LPVOID,
                                    ctypes.POINTER(ctypes.c_float))(evt[0][9])
        lvl = ctypes.c_float()
        if fn_get(evt, ctypes.byref(lvl)) != 0:
            return None
        return max(0.0, min(1.0, float(lvl.value)))
    except Exception:
        return None


def audio_set_master(level):
    """Volume master 0.0-1.0. True se o Windows aceitou."""
    try:
        level = max(0.0, min(1.0, float(level)))
    except Exception:
        return False
    try:
        evt = _endpoint_volume()
        if not evt:
            return False
        fn_set = ctypes.WINFUNCTYPE(_HRESULT, _LPVOID, ctypes.c_float,
                                    _LPVOID)(evt[0][7])
        return fn_set(evt, ctypes.c_float(level), None) == 0
    except Exception:
        return False
