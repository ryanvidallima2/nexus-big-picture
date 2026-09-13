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
    text = ("\\U0001F3AE " + pad_label + "  \u2022  setas: quadros  \u2022  A abre  \u2022  F11: tela cheia")
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
    """Mantem barra/modal/F11 e o modo console vivos (sites trocam de pagina)."""
    for _ in range(300):  # ~10 min de vigilancia
        time.sleep(2.0)
        try:
            window.evaluate_js(_CHROME_JS)
        except Exception:
            pass
        try:
            window.evaluate_js(_NAV_JS)
        except Exception:
            try:
                time.sleep(2.0)
            except Exception:
                pass


# Modo console: analógico/D-pad seleciona os quadros (filmes, series)
# como num videogame. Anel roxo, navegacao espacial, A abre, B volta.
_NAV_JS = """try{
if(!window.__nexusNav){
window.__nexusNav={idx:-1,prev:null};
window.__nexusNavCollect=function(){
var sel='a[href],button,input,select,textarea,video,[role="button"],[role="link"],[role="tab"],[role="menuitem"],[role="option"],[tabindex]:not([tabindex="-1"]),[jsaction],[onclick]';
var out=[],els=document.querySelectorAll(sel);
for(var i=0;i<els.length&&out.length<500;i++){var el=els[i];try{var r=el.getBoundingClientRect();
if(r.width>40&&r.height>20&&!el.disabled)out.push(el);}catch(e){}}
if(out.length<5){
try{var divs=document.querySelectorAll('div');var n=0;
for(var j=0;j<divs.length&&n<2000;j++){var d=divs[j];n++;
try{var q=d.getBoundingClientRect();
if(q.width<80||q.height<40)continue;
var cur='';try{cur=window.getComputedStyle(d).cursor;}catch(e2){}
if(cur==='pointer'){out.push(d);}}catch(e3){}}}catch(e4){}}
return out;};
window.__nexusNavFocus=function(el){
var N=window.__nexusNav;
if(N.prev){try{N.prev.style.outline=N.prev._nxO||'';N.prev.style.outlineOffset=N.prev._nxOO||'';N.prev.style.transform=N.prev._nxT||'';}catch(e){}N.prev=null;}
if(!el){N.idx=-1;return 'cleared';}
try{el._nxO=el.style.outline;el._nxOO=el.style.outlineOffset;el._nxT=el.style.transform;
el.style.outline='3px solid #7c4dff';el.style.outlineOffset='2px';el.style.transform='scale(1.04)';
if(el.scrollIntoView)el.scrollIntoView({block:'nearest',inline:'nearest'});
try{el.focus({preventScroll:true});}catch(e){try{el.focus();}catch(e2){}}
N.prev=el;}catch(e){}
return 'ok';};
window.__nexusNavMove=function(dir){
var items=window.__nexusNavCollect();var N=window.__nexusNav;
if(!items.length){return 'empty';}
var cx=window.innerWidth/2,cy=window.innerHeight/2,cur=null;
if(N.prev&&document.contains(N.prev)){try{var r=N.prev.getBoundingClientRect();cx=r.left+r.width/2;cy=r.top+r.height/2;cur=N.prev;}catch(e){}}
var best=null,bestScore=1e12;
for(var i=0;i<items.length;i++){var el=items[i];if(el===cur)continue;
try{var q=el.getBoundingClientRect();var ex=q.left+q.width/2-cx,ey=q.top+q.height/2-cy;
var ok=dir==='left'?ex<-4:dir==='right'?ex>4:dir==='up'?ey<-4:ey>4;
if(!ok)continue;
var score=(dir==='left'||dir==='right')?Math.abs(ex)+Math.abs(ey)*2.5:Math.abs(ey)+Math.abs(ex)*2.5;
if(score<bestScore){bestScore=score;best=el;}}catch(e){}}
if(!best){var ncx=window.innerWidth/2,ncy=window.innerHeight/2;best=items[0];bestScore=1e12;
for(var k=0;k<items.length;k++){try{var rk=items[k].getBoundingClientRect();
var dd=Math.abs(rk.left+rk.width/2-ncx)+Math.abs(rk.top+rk.height/2-ncy);
if(dd<bestScore){bestScore=dd;best=items[k];}}catch(e2){}}
N.idx=items.indexOf(best);}
return window.__nexusNavFocus(best)+' '+(N.idx+1)+'/'+items.length;};
window.__nexusNavClick=function(){
var N=window.__nexusNav;var el=(N.prev&&document.contains(N.prev))?N.prev:null;
if(!el){var items=window.__nexusNavCollect();if(!items.length)return 'empty';el=items[0];}
try{el.click();return 'clicked';}catch(e){return 'fail';}};
window.__nexusNavCount=function(){return window.__nexusNavCollect().length;};
document.addEventListener('keydown',function(ev){
if(!ev)return;
var q=document.getElementById('nexus-quit');
if(q&&q.style.display==='flex')return;
var ae=null;try{ae=document.activeElement;}catch(e){}
var typing=ae&&((ae.tagName==='INPUT'||ae.tagName==='TEXTAREA'||ae.tagName==='SELECT')||ae.isContentEditable);
if(ev.key==='ArrowUp'||ev.key==='ArrowDown'||ev.key==='ArrowLeft'||ev.key==='ArrowRight'){
if(typing)return;
try{ev.preventDefault();}catch(e){}
var d=ev.key==='ArrowUp'?'up':ev.key==='ArrowDown'?'down':ev.key==='ArrowLeft'?'left':'right';
window.__nexusNavMove(d);}
else if(ev.key==='Enter'){
var N=window.__nexusNav;
if(!typing&&N.prev&&document.contains(N.prev)){try{ev.preventDefault();}catch(e){}window.__nexusNavClick();}}
else if(ev.key==='Escape'){
if(typing)return;
if(document.fullscreenElement)return;
try{history.back();}catch(e){}}
},true);
}
'nav-ready';
}catch(e){'nav-fail';}"""


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
