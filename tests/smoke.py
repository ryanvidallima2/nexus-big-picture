# -*- coding: utf-8 -*-
"""Smoke do Nexus: py_compile + boot + render + modulos. Sem dependencias novas.

Uso (qualquer PC):  Python\\python.exe tests\\smoke.py   (na pasta do projeto)
Saida: linhas PASS/FAIL + RESULT. Exit 0 = tudo ok.

Nao suja arquivos do usuario: settings.json/nexus.db vao p/ backup e voltam
(byte a byte; se nao existiam, sao removidos no fim).
"""
import os
import py_compile
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
# nexus.paths deriva o BASE_DIR de sys.argv[0]: aponta p/ o entry real.
sys.argv[0] = os.path.join(BASE, "bigpicture.py")

fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        fails.append(msg)


def main():
    # 0) compila tudo
    targets = [os.path.join(BASE, "bigpicture.py"),
               os.path.join(BASE, "nexus_browser.py")]
    for f in sorted(os.listdir(os.path.join(BASE, "nexus"))):
        if f.endswith(".py"):
            targets.append(os.path.join(BASE, "nexus", f))
    try:
        for tfile in targets:
            py_compile.compile(tfile, doraise=True)
        check(True, "py_compile %d arquivos" % len(targets))
    except Exception as e:
        check(False, "py_compile (%r)" % e)
        return 1

    # snapshot dos arquivos do usuario
    saved = {}
    for f in ("settings.json", "nexus.db"):
        p = os.path.join(BASE, f)
        saved[f] = open(p, "rb").read() if os.path.exists(p) else None

    try:
        return run()
    finally:
        for f, data in saved.items():
            p = os.path.join(BASE, f)
            if data is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, "wb") as fh:
                    fh.write(data)


def run():
    from nexus.i18n import TRANSLATIONS, cat_label, t
    check(len(TRANSLATIONS.get("pt-br", {})) == len(TRANSLATIONS.get("en", {})) > 200,
          "i18n pt/en completos")
    check(t("sec_all", "en") == "All Streamings"
          and cat_label("Filmes", "en") == "Movies", "i18n chaves")

    import tkinter as tk
    import bigpicture as B
    tk_errors = []
    _orig_rep = tk.Tk.report_callback_exception

    def _rep(self, exc, val, tb):
        tk_errors.append(str(val))

    tk.Tk.report_callback_exception = _rep
    root = tk.Tk()
    root.withdraw()
    app = None
    try:
        app = B.BigPictureApp(root)
        check(app.current_tab == "all" and len(app.get_all_services()) >= 32,
              "boot (aba all, 32 servicos)")

        from nexus.app import BigPictureApp as App2
        check(B.BigPictureApp is App2, "entry usa nexus.app")

        for lang, title_all, tag in (("pt-br", "Todos os Streamings", "FILMES"),
                                     ("en", "All Streamings", "MOVIES")):
            app.lang = lang
            for tab in ("all", "movies", "music", "videos", "favorites", "games"):
                app.render_tab(tab)
                root.update()
            for mode in ("cards", "grid", "list", "details"):
                app.set_view_mode("all", mode)
                app.render_tab("all")
                root.update()
            app.set_view_mode("all", "grid")
            app.render_tab("all")
            root.update()
            texts = collect_texts(app.scroll_frame)
            check(title_all in texts and tag in texts, "render %s" % lang)

        for d in ("up", "down", "left", "right"):
            app._nav(d)
        app.go_back()
        app.toggle_sidebar()
        app.toggle_sidebar()
        check(True, "nav + sidebar")

        app.settings["favorites"] = []
        app.toggle_favorite("Netflix")
        app.toggle_favorite("Netflix")
        check("Netflix" not in app.settings.get("favorites", []), "favorito")

        from nexus.dialogs import NexusMenuWindow, NexusTextDialog
        got = []
        td = NexusTextDialog(app, "T", "P", "x", got.append)
        td.confirm()
        menu = NexusMenuWindow(app, "M", [])
        menu.set_options([("O", lambda: got.append(1))])
        menu.confirm()
        menu.close()
        check(got == ["x", 1], "dialogos")

        app.render_tab("all")
        root.update()
        w = app.sections[0]["widgets"][0]
        n = app.sections[0]["names"][0]
        app.flip_card(w, n, False)
        root.update()
        back_on = (app.flipped is not None and app.flipped["back"].winfo_ismapped()
                   and len(app.flipped["opts"]) == 3)
        check(back_on, "card vira (verso Site/App/Config)")
        app.flip_show_page("config")
        root.update()
        check(app.flipped["page"] == "config" and len(app.flipped["opts"]) == 8,
              "verso config (8 acoes)")
        app.flip_opt_move(1)
        check(app.flipped["idx"] == 1, "opcao navega")
        app.unflip_card()
        root.update()
        check(app.flipped is None, "card desvira")

        entry = tk.Entry(root)
        entry.pack()
        app.open_keyboard(entry)
        app.kb_window.on_hat((1, 0))
        app.kb_window.close()
        for opener in (app.open_controles, app.open_idioma, app.open_adicionar,
                       app.open_sistema, app.open_som):
            opener()
            app.close_sidepanel()
        from nexus.panels import GamepadConfigWindow
        gw = GamepadConfigWindow(app)
        gw.close()
        check(True, "teclado + paineis + padconfig")

        gm = app.gamepad
        gm.refresh_devices()
        check(gm.read_dpad() == (0, 0)
              and gm.logical_for_raw(0) == "south"
              and gm.raw_for_logical("south") == 0, "gamepad sem controle")
        gm.poll()
        gm.stop()
        check(True, "gamepad poll/stop")

        app.scan_games()
        app.render_games()
        root.update()
        check(True, "games scan+render")
    finally:
        try:
            tk.Tk.report_callback_exception = _orig_rep
        except Exception:
            pass
        try:
            if app is not None:
                app.root.after(200, app.root.destroy)
                app.root.mainloop()
        except Exception:
            pass
    if tk_errors:
        print("WARN callbacks Tk com erro (%d): %s" % (len(tk_errors), tk_errors[:3]))
    return 0 if not fails else 1


def collect_texts(widget):
    import tkinter as tk
    out = []

    def walk(w):
        try:
            if isinstance(w, tk.Label):
                out.append(w.cget("text"))
        except Exception:
            pass
        for c in w.winfo_children():
            walk(c)

    walk(widget)
    return out


if __name__ == "__main__":
    sys.exit(main() or (1 if fails else 0))
