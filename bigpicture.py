# -*- coding: utf-8 -*-
import os as _os
import sys as _sys
# Sem console (pythonw.exe): esconde banner do pygame, evita crash em print
# e grava erros nao tratados em nexus_error.log
_os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
if _sys.stdout is None:
    _sys.stdout = open(_os.devnull, "w")
if _sys.stderr is None:
    _sys.stderr = open(_os.devnull, "w")


def _nexus_excepthook(exc_type, exc_value, exc_tb):
    try:
        import traceback as _tb
        import datetime as _dt
        base = _os.path.dirname(_os.path.realpath(_sys.argv[0] or "."))
        with open(_os.path.join(base, "nexus_error.log"), "a", encoding="utf-8") as f:
            f.write(_dt.datetime.now().isoformat() + " UNCAUGHT\n")
            _tb.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass


if (_sys.executable or "").lower().endswith("pythonw.exe"):
    _sys.excepthook = _nexus_excepthook

import ctypes
import os
import sys
import tkinter as tk

from nexus.app import BigPictureApp


# ===================== MAIN =====================
if __name__ == "__main__":
    try:
        # AppID proprio: a barra de tarefas mostra a logo do Nexus
        # em vez de agrupar/icone generico do python.exe.
        # (v2 = nova entrada no cache de icones do Explorer)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "NexusStreamingHub.BigPicture.2")
    except Exception:
        pass
    root = tk.Tk()
    app = BigPictureApp(root)
    root.mainloop()
