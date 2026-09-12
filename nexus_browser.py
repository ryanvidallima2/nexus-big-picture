# -*- coding: utf-8 -*-
"""Janela Navegador do Nexus: abre um site DENTRO do app (pywebview + Edge WebView2),
sem usar o navegador externo da maquina.

Uso: nexus_browser.py <url> [titulo] [controle]
Chamado pelo Nexus (botao Site) como processo separado para nao travar o tkinter.
Os comandos do controle sao traduzidos pelo processo principal do Nexus
(teclado/mouse virtuais na janela em foco); aqui o navegador so identifica
o controle ativo com um aviso na pagina.

Para parecer o MESMO aplicativo: mesma AppUserModelID do Nexus (agrupa na
barra de tarefas), tela cheia sem bordas e perfil persistente (logins,
cookies e senhas salvos entre sessoes).

Controles da janela (injetados na pagina, discretos):
- barra flutuante: minimizar (_) e fechar (X), quase invisivel ate o hover
- F11: entra/sai da tela cheia
- fechar pede confirmacao "Deseja realmente sair do aplicativo" (Sim/Nao)
"""
import os
import sys
import threading
import time

APP_ID = "NexusStreamingHub.BigPicture.2"


def nexus_profile_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "Nexus", "browser_profile")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


# Perfil persistente ANTES de qualquer init do WebView2: e o que mantem
# logins, cookies, localStorage e senhas salvas entre as sessoes.
os.environ.setdefault("WEBVIEW2_USER_DATA_FOLDER", nexus_profile_dir())

try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass


class NexusApi:
    """Ponte pagina -> janela (chamada pelo JS injetado)."""
    def __init__(self):
        self._window = None  # underscore: o pywebview varre atributos
        # publicos da api e travaria enumerando a janela (.native)

    def minimize(self):
        try:
            if self._window is not None:
                self._window.minimize()
            return "ok"
        except Exception:
            return "fail"

    def toggle_fullscreen(self):
        try:
            if self._window is not None:
                self._window.toggle_fullscreen()
            return "ok"
        except Exception:
            return "fail"

    def quit_app(self):
        try:
            if self._window is not None:
                self._window.destroy()
            return "ok"
        except Exception:
            return "fail"


# Marca d'agua do controle (some sozinha apos ~4s)
_TOAST_JS = (
    "try{var d=document.createElement('div');"
    "d.setAttribute('id','nexus-pad-toast');"
    "d.textContent=%s;"
    "d.setAttribute('style','position:fixed;top:14px;left:50%%;transform:translateX(-50%%);"
    "background:#7c4dff;color:#fff;font:600 15px Segoe UI,sans-serif;"
    "padding:10px 22px;border-radius:24px;z-index:2147483647;"
    "box-shadow:0 4px 18px rgba(0,0,0,.5);opacity:.95;');"
    "document.documentElement.appendChild(d);"
    "setTimeout(function(){try{d.remove();}catch(e){}},4500);'ok';}catch(e){'fail';}"
)

# Barra discreta + modal de saida + F11 (re-injetado se a pagina trocar)
_CHROME_JS = """try{
if(!document.getElementById('nexus-bar')){
var css='#nexus-bar{position:fixed;top:10px;right:10px;z-index:2147483647;display:flex;gap:6px;opacity:.18;transition:opacity .2s;}'
+'#nexus-bar:hover{opacity:1;}'
+'.nxb{width:34px;height:30px;line-height:28px;text-align:center;font:600 15px Segoe UI,sans-serif;color:#cfcfe6;background:rgba(13,13,26,.85);border:1px solid #2a2545;border-radius:8px;cursor:pointer;user-select:none;}'
+'.nxb:hover{background:#252548;color:#fff;}'
+'#nxb-close:hover{background:#e94560!important;border-color:#e94560!important;color:#fff!important;}'
+'#nexus-quit{position:fixed;inset:0;z-index:2147483646;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.72);}'
+'#nexus-quit-box{width:400px;background:#0d0d1a;border:2px solid #7c4dff;border-radius:16px;padding:28px 30px;text-align:center;box-shadow:0 12px 48px rgba(0,0,0,.7);}'
+'#nexus-quit-box h2{margin:0 0 8px;font:700 20px Segoe UI,sans-serif;color:#7c4dff;}'
+'#nexus-quit-box p{margin:0 0 22px;font:400 15px Segoe UI,sans-serif;color:#8888bb;}'
+'#nexus-quit-box button{font:700 14px Segoe UI,sans-serif;border:0;border-radius:10px;padding:11px 0;width:150px;margin:0 6px;cursor:pointer;}'
+'#nxb-no{background:#1e2040;color:#fff;}'
+'#nxb-no:hover{background:#7c4dff;}'
+'#nxb-yes{background:#e94560;color:#fff;}'
+'#nxb-yes:hover{background:#ff4570;}';
var st=document.createElement('style');st.textContent=css;
(document.head||document.documentElement).appendChild(st);
var bar=document.createElement('div');bar.id='nexus-bar';bar.title='Nexus (F11: tela cheia)';
bar.innerHTML='<div class=nxb id=nxb-min title=Minimizar>&ndash;</div><div class=nxb id=nxb-close title=Fechar>&times;</div>';
(document.body||document.documentElement).appendChild(bar);
var ov=document.createElement('div');ov.id='nexus-quit';
ov.innerHTML='<div id=nexus-quit-box><h2>&#x1F6AA; Sair do Nexus</h2><p>Deseja realmente sair do aplicativo?</p><button id=nxb-no>N&atilde;o, ficar</button><button id=nxb-yes>Sim, sair</button></div>';
(document.body||document.documentElement).appendChild(ov);
document.getElementById('nxb-min').onclick=function(){try{window.pywebview.api.minimize();}catch(e){}};
document.getElementById('nxb-close').onclick=function(){document.getElementById('nexus-quit').style.display='flex';try{document.getElementById('nxb-no').focus();}catch(e){}};
document.getElementById('nxb-no').onclick=function(){document.getElementById('nexus-quit').style.display='none';};
document.getElementById('nxb-yes').onclick=function(){try{window.pywebview.api.quit_app();}catch(e){window.close();}};
document.getElementById('nexus-quit').onclick=function(ev){if(ev.target&&ev.target.id==='nexus-quit'){ev.target.style.display='none';}};
document.addEventListener('keydown',function(ev){
if(ev&&ev.key==='F11'){try{ev.preventDefault();}catch(e){}try{window.pywebview.api.toggle_fullscreen();}catch(e){}}
else if(ev&&ev.key==='Escape'){var q=document.getElementById('nexus-quit');if(q&&q.style.display==='flex'){q.style.display='none';}}
},true);
'ok';}
}catch(e){'fail';}"""


def _show_pad_toast(window, pad_label):
    """Injeta o aviso do controle identificado (aguarda a pagina carregar)."""
    if not pad_label:
        return
    text = ("\\U0001F3AE " + pad_label + "  \u2022  F11: tela cheia")
    text = text.replace("\\", "\\\\").replace("'", "\\'")
    js = _TOAST_JS % ("'" + text + "'")
    for _ in range(12):
        time.sleep(1.0)
        try:
            if window.evaluate_js(js) == "ok":
                return
        except Exception:
            pass


def _ensure_chrome(window):
    """Mantem barra/modal/F11 vivos mesmo quando o site troca de pagina."""
    for _ in range(300):  # ~10 min de vigilancia
        time.sleep(2.0)
        try:
            window.evaluate_js(_CHROME_JS)
        except Exception:
            try:
                time.sleep(2.0)
            except Exception:
                pass


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "about:blank"
    title = sys.argv[2] if len(sys.argv) > 2 else "Nexus"
    pad_label = sys.argv[3] if len(sys.argv) > 3 else ""
    if "://" not in url:
        url = "https://" + url
    import webview
    api = NexusApi()
    window = webview.create_window("Nexus - %s" % title, url,
                                   width=1280, height=800, min_size=(800, 600),
                                   fullscreen=True, focus=True, js_api=api)
    api._window = window
    threading.Thread(target=_show_pad_toast, args=(window, pad_label),
                     daemon=True).start()
    threading.Thread(target=_ensure_chrome, args=(window,),
                     daemon=True).start()
    try:
        auto_close = float(os.environ.get("NEXUS_BROWSER_TEST_CLOSE", "") or 0)
    except Exception:
        auto_close = 0
    if auto_close > 0:
        threading.Timer(auto_close, lambda: window.destroy()).start()
    # private_mode=False + storage_path: logins, cookies e senhas persistem.
    webview.start(private_mode=False, storage_path=nexus_profile_dir())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            sys.stderr.write("nexus_browser: %s\n" % e)
        except Exception:
            pass
        sys.exit(1)
