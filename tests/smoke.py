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
import time

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
        exp_color = app.settings.get("card_colors", {}).get(
            n, (app.get_all_services().get(n, {}).get("color") or "#7c4dff"))
        check(app.flipped["back"].cget("bg").lower() == exp_color.lower(),
              "borda neon na cor do card")
        app.flip_show_page("config")
        root.update()
        check(app.flipped["page"] == "config" and len(app.flipped["opts"]) == 8,
              "verso config (8 acoes)")
        app.flip_opt_move(1)
        check(app.flipped["idx"] == 1, "opcao navega")
        app.flip_show_page("color")
        root.update()
        check(app.flipped["page"] == "color" and len(app.flipped["opts"]) == 17,
              "verso cor (16+cancela)")
        from nexus.dialogs import CARD_COLOR_PRESETS
        sw_bgs = set()
        for b, _c in app.flipped["opts"][:16]:
            try:
                sw_bgs.add(b.cget("bg"))
            except Exception:
                pass
        want = {c for _l, c in CARD_COLOR_PRESETS}
        check(want <= sw_bgs, "swatches coloridos")
        app.flip_click(0)
        root.update()
        check(app.settings.get("card_colors", {}).get(n)
              and app.flipped is not None
              and app.flipped["page"] == "color", "cor aplica e continua")
        w = app.flipped["widget"] if app.flipped else None
        if w is None:
            check(False, "verso url (sem card)")
            check(False, "verso excluir confirma")
            check(False, "card desvira")
            check(False, "clique em toda area do card")
        else:
            app.flip_show_page("url")
            root.update()
            check(app.flipped["page"] == "url" and app.flipped.get("entry") is not None
                  and len(app.flipped["opts"]) == 2, "verso url (campo+ok)")
            app.flip_show_page("delete")
            root.update()
            check(app.flipped["page"] == "delete" and len(app.flipped["opts"]) == 2,
                  "verso excluir confirma")
            app.unflip_card()
            root.update()
            check(app.flipped is None, "card desvira")
            bound = []

            def walk(x):
                try:
                    if x.bind("<Button-1>"):
                        bound.append(True)
                except Exception:
                    pass
                try:
                    kids = x.winfo_children()
                except Exception:
                    return
                for c in kids:
                    walk(c)

        walk(w)
        check(len(bound) >= 6, "clique em toda area do card")
        app.set_view_mode("all", "list")
        app.render_tab("all")
        root.update()
        rw = app.sections[0]["widgets"][0]
        rn = app.sections[0]["names"][0]
        row_kids = list(rw.winfo_children())
        app.flip_card(rw, rn, False)
        root.update()
        front_hidden = all(not c.winfo_ismapped() for c in row_kids)
        check(app.flipped is not None and front_hidden
              and app.flipped["back"].winfo_ismapped(),
              "linha vira inteira (frente some)")
        app.unflip_card()
        root.update()
        check(app.flipped is None
              and all(c.winfo_ismapped() for c in row_kids),
              "linha desvira (frente volta)")

        entry = tk.Entry(root)
        entry.pack()
        app.open_keyboard(entry)
        app.kb_window.on_hat((1, 0))
        app.kb_window.force_front()
        from nexus.win32 import force_topmost_noactivate
        check(isinstance(force_topmost_noactivate(app.kb_window.win), bool),
              "teclado forca frente")
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

        from nexus import input as nexus_input
        _orig_focus = nexus_input.focused_is_text_field
        nexus_input.focused_is_text_field = lambda: True
        try:
            no_f = nexus_input.remote_button_allowed("fullscreen")
            ok_other = nexus_input.remote_button_allowed("space")
        finally:
            nexus_input.focused_is_text_field = _orig_focus
        check(no_f is False and ok_other is True,
              "fullscreen nao digita em campo")

        gm.remote_enter_time = time.time()
        gm.remote_kb_time = 0.0
        gm._maybe_open_kb_for_focus()
        check(gm.remote_kb_time == 0.0, "teclado nao abre ao entrar no app")
        gm.remote_enter_time = time.time() - 30.0
        gm._maybe_open_kb_for_focus()
        check(gm.remote_kb_time != 0.0, "teclado abre apos carencia")

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
