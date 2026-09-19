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
# IIDs de sessao (conferidos contra o pycaw; decorar falha aqui).
_IID_IAudioSessionManager2 = _makeguid("77aa99a0-1bd6-484f-8bc7-2c654c9a9b6f")
_IID_IAudioSessionControl2 = _makeguid("BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D")
_IID_ISimpleAudioVolume = _makeguid("87CE5498-68D6-44E5-9215-6DA47EF883D8")
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


def _default_device():
    """IMMDevice do render padrao (c_void_p) ou None."""
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
        return dev
    except Exception:
        return None


def _exe_of_pid(pid):
    """Nome do exe do pid (minusculo) ou ''."""
    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetModuleBaseNameW.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong]
        psapi.GetModuleBaseNameW.restype = ctypes.c_ulong
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool,
                                    ctypes.c_ulong]
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k32.OpenProcess(0x410, False, int(pid))
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(256)
            if psapi.GetModuleBaseNameW(h, None, buf, 256) > 0:
                return (buf.value or "").strip().lower()
        finally:
            try:
                k32.CloseHandle(h)
            except Exception:
                pass
    except Exception:
        pass
    return ""


def audio_sessions():
    """[(pid, exe, level)] das sessoes ativas. Lista vazia se falhar."""
    out = []
    try:
        dev = _default_device()
        if not dev:
            return out
        WINFUNCTYPE = ctypes.WINFUNCTYPE
        dvt = ctypes.cast(dev.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_act = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID, ctypes.c_ulong,
                             _LPVOID,
                             ctypes.POINTER(_LPVOID))(dvt[0][3])
        mgr = _LPVOID()
        if fn_act(dev, ctypes.byref(_IID_IAudioSessionManager2),
                  _CLSCTX_INPROC_SERVER, None, ctypes.byref(mgr)) != 0:
            return out
        mvt = ctypes.cast(mgr.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        # GetSessionEnumerator = 3 IUnknown + 2 base + 1o da Manager2.
        fn_enum = WINFUNCTYPE(_HRESULT, _LPVOID,
                              ctypes.POINTER(_LPVOID))(mvt[0][5])
        penum = _LPVOID()
        if fn_enum(mgr, ctypes.byref(penum)) != 0:
            return out
        evt = ctypes.cast(penum.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_count = WINFUNCTYPE(_HRESULT, _LPVOID,
                               ctypes.POINTER(ctypes.c_int))(evt[0][3])
        fn_session = WINFUNCTYPE(_HRESULT, _LPVOID, ctypes.c_int,
                                 ctypes.POINTER(_LPVOID))(evt[0][4])
        n = ctypes.c_int()
        if fn_count(penum, ctypes.byref(n)) != 0:
            return out
        for i in range(max(0, min(int(n.value), 64))):
            try:
                psess = _LPVOID()
                if fn_session(penum, i, ctypes.byref(psess)) != 0:
                    continue
                svt = ctypes.cast(psess.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                # IUnknown::QueryInterface = indice 0
                fn_qi = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID,
                                    ctypes.POINTER(_LPVOID))(svt[0][0])
                p2 = _LPVOID()
                if fn_qi(psess, ctypes.byref(_IID_IAudioSessionControl2),
                         ctypes.byref(p2)) != 0:
                    continue
                c2t = ctypes.cast(p2.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                fn_pid = WINFUNCTYPE(_HRESULT, _LPVOID,
                                     ctypes.POINTER(ctypes.c_ulong))(c2t[0][14])
                pid = ctypes.c_ulong()
                if fn_pid(p2, ctypes.byref(pid)) != 0:
                    continue
                fn_qv = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID,
                                    ctypes.POINTER(_LPVOID))(svt[0][0])
                pv = _LPVOID()
                if fn_qv(psess, ctypes.byref(_IID_ISimpleAudioVolume),
                         ctypes.byref(pv)) != 0:
                    continue
                qvt = ctypes.cast(pv.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                fn_lv = WINFUNCTYPE(_HRESULT, _LPVOID,
                                    ctypes.POINTER(ctypes.c_float))(qvt[0][4])
                lvl = ctypes.c_float()
                if fn_lv(pv, ctypes.byref(lvl)) != 0:
                    continue
                out.append((int(pid.value),
                            _exe_of_pid(pid.value),
                            max(0.0, min(1.0, float(lvl.value)))))
            except Exception:
                continue
    except Exception:
        pass
    return out


def session_set_volume(exe_name, level):
    """Poe o volume (0.0-1.0) nas sessoes do exe. True se ao menos uma."""
    try:
        want = (exe_name or "").strip().lower()
        level = max(0.0, min(1.0, float(level)))
    except Exception:
        return False
    if not want:
        return False
    try:
        dev = _default_device()
        if not dev:
            return False
        WINFUNCTYPE = ctypes.WINFUNCTYPE
        dvt = ctypes.cast(dev.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_act = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID, ctypes.c_ulong,
                             _LPVOID,
                             ctypes.POINTER(_LPVOID))(dvt[0][3])
        mgr = _LPVOID()
        if fn_act(dev, ctypes.byref(_IID_IAudioSessionManager2),
                  _CLSCTX_INPROC_SERVER, None, ctypes.byref(mgr)) != 0:
            return False
        mvt = ctypes.cast(mgr.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        # GetSessionEnumerator = 3 IUnknown + 2 base + 1o da Manager2.
        fn_enum = WINFUNCTYPE(_HRESULT, _LPVOID,
                              ctypes.POINTER(_LPVOID))(mvt[0][5])
        penum = _LPVOID()
        if fn_enum(mgr, ctypes.byref(penum)) != 0:
            return False
        evt = ctypes.cast(penum.value, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p)))
        fn_count = WINFUNCTYPE(_HRESULT, _LPVOID,
                               ctypes.POINTER(ctypes.c_int))(evt[0][3])
        fn_session = WINFUNCTYPE(_HRESULT, _LPVOID, ctypes.c_int,
                                 ctypes.POINTER(_LPVOID))(evt[0][4])
        n = ctypes.c_int()
        if fn_count(penum, ctypes.byref(n)) != 0:
            return False
        hit = False
        for i in range(max(0, min(int(n.value), 64))):
            try:
                psess = _LPVOID()
                if fn_session(penum, i, ctypes.byref(psess)) != 0:
                    continue
                svt = ctypes.cast(psess.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                fn_qi = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID,
                                    ctypes.POINTER(_LPVOID))(svt[0][0])
                p2 = _LPVOID()
                if fn_qi(psess, ctypes.byref(_IID_IAudioSessionControl2),
                         ctypes.byref(p2)) != 0:
                    continue
                c2t = ctypes.cast(p2.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                fn_pid = WINFUNCTYPE(_HRESULT, _LPVOID,
                                     ctypes.POINTER(ctypes.c_ulong))(c2t[0][14])
                pid = ctypes.c_ulong()
                if fn_pid(p2, ctypes.byref(pid)) != 0:
                    continue
                if _exe_of_pid(pid.value) != want:
                    continue
                fn_qv = WINFUNCTYPE(_HRESULT, _LPVOID, _LPGUID,
                                    ctypes.POINTER(_LPVOID))(svt[0][0])
                pv = _LPVOID()
                if fn_qv(psess, ctypes.byref(_IID_ISimpleAudioVolume),
                         ctypes.byref(pv)) != 0:
                    continue
                qvt = ctypes.cast(pv.value, ctypes.POINTER(
                    ctypes.POINTER(ctypes.c_void_p)))
                fn_sv = WINFUNCTYPE(_HRESULT, _LPVOID, ctypes.c_float,
                                    _LPVOID)(qvt[0][3])
                if fn_sv(pv, ctypes.c_float(level), None) == 0:
                    hit = True
            except Exception:
                continue
        return hit
    except Exception:
        return False


def ensure_app_volumes(exes, level, tries=12, _set=None):
    """Garante o volume nas sessoes dos exes (a sessao nasce quando o app
    toca algo: tenta 1x/s ate acertar todos ou esgotar). Retorna os que
    faltaram. _set injetavel p/ teste."""
    try:
        level = max(0.0, min(1.0, float(level)))
    except Exception:
        return list(exes or [])
    try:
        import time as _time
    except Exception:
        _time = None
    remaining = []
    try:
        remaining = [str(e or "").strip().lower() for e in (exes or [])]
        remaining = [e for e in remaining if e]
    except Exception:
        return list(exes or [])
    if not remaining:
        return []
    do_set = _set or session_set_volume
    try:
        rounds = max(1, min(int(tries), 60))
    except Exception:
        rounds = 12
    for _ in range(rounds):
        try:
            remaining = [e for e in remaining if not do_set(e, level)]
        except Exception:
            pass
        if not remaining:
            break
        try:
            if _time is not None:
                _time.sleep(1.0)
        except Exception:
            break
    return remaining
