# -*- coding: utf-8 -*-
"""Manual de uso do Nexus (Guia/POP por categoria, PT-BR + EN)."""

GUIDE_CATS = [
    {
        "key": "controle",
        "icon": "\U0001F3AE",
        "title_pt": "Controle no Nexus",
        "title_en": "Gamepad in Nexus",
        "body_pt": (
            "Esse controle é seu tapete voador pelo Nexus — só não cai do sofá.\n"
            "D-pad ou analógico esquerdo: passeia entre abas e cards.\n"
            "A: o botão 'faz acontecer' — confirma, abre e vira os cards.\n"
            "B: o botão 'ops, voltei' — volta uma etapa (e desvira card).\n"
            "X: teletransporte direto para os cards. Y: abre o menu lateral.\n"
            "LB e RB: folheiam as abas como revista de fofoca.\n"
            "Start: abre as notificações (o sino agradece).\n"
            "Truque de mestre: Back + Start juntos te resgatam de "
            "qualquer app de volta ao Nexus."
        ),
        "body_en": (
            "This gamepad is your flying carpet through Nexus — just don't "
            "fall off the couch.\n"
            "D-pad or left stick: roam between tabs and cards.\n"
            "A: the 'make it happen' button — confirms, opens, flips cards.\n"
            "B: the 'oops, go back' button — one step back (and unflips).\n"
            "X: teleports straight to the cards. Y: opens the sidebar.\n"
            "LB and RB: flip through tabs like a gossip magazine.\n"
            "Start: opens notifications (the bell says thanks).\n"
            "Master trick: Back + Start together rescue you from any app."
        ),
    },
    {
        "key": "assistir",
        "icon": "\U0001F4FA",
        "title_pt": "Assistindo",
        "title_en": "Watching",
        "body_pt": (
            "Viu um card bonito? Aperta A (ou clica) e ele vira igual "
            "carta de baralho.\n"
            "No verso tem três portas mágicas:\n"
            "Site: abre no navegador — bom para maratonar sem instalar nada.\n"
            "App: abre o aplicativo instalado — e se não tiver, o Nexus "
            "tenta instalar para você (gentileza gera gentileza).\n"
            "Lá dentro, seu controle vira controle remoto: analógico "
            "direito é o mouse, esquerdo rola a tela, A clica.\n"
            "Para voltar ao Nexus de qualquer lugar: segure Back + Start, "
            "como um passe de mágica.\n"
            "Start sozinho abre o menu rápido: som, janela e imagem sem "
            "sair do app."
        ),
        "body_en": (
            "See a pretty card? Press A (or click) and it flips like a "
            "playing card.\n"
            "On the back there are three magic doors:\n"
            "Site: opens in the browser — great for binging with zero installs.\n"
            "App: opens the installed app — and if it's missing, Nexus "
            "tries to install it for you (kindness breeds kindness).\n"
            "Inside, your gamepad becomes a remote: right stick is the "
            "mouse, left stick scrolls, A clicks.\n"
            "Back to Nexus from anywhere: hold Back + Start, like a spell.\n"
            "Start alone opens the quick menu: sound, window and picture."
        ),
    },
    {
        "key": "teclado",
        "icon": "\u2328",
        "title_pt": "Teclado virtual",
        "title_en": "Virtual keyboard",
        "body_pt": (
            "O teclado aparece sozinho quando você clica numa barra de "
            "texto com o controle — ele sente cheiro de login.\n"
            "?123: vira símbolos (!@# e a turma toda).\n"
            "Emoji: para rir em qualquer idioma.\n"
            "Tecla lang: alterna BR (com Ç!) e US. Shift: GRITA EM MAIÚSCULAS.\n"
            "No controle: D-pad anda, A digita, B foge, Start entrega o "
            "texto (fecha + Enter).\n"
            "Botão ⬇ gruda o teclado embaixo (dock); ⬆ solta de novo."
        ),
        "body_en": (
            "The keyboard pops up by itself when you click a text field "
            "with the gamepad — it can smell a login.\n"
            "?123: turns into symbols (!@# and the whole gang).\n"
            "Emoji: for laughing in any language.\n"
            "Lang key: switches BR (with Ç!) and US. Shift: SHOUTS IN CAPS.\n"
            "On gamepad: D-pad walks, A types, B runs away, Start delivers "
            "the text (closes + Enter).\n"
            "⬇ docks the keyboard at the bottom; ⬆ releases it."
        ),
    },
    {
        "key": "cards",
        "icon": "\U0001F0CF",
        "title_pt": "Cards",
        "title_en": "Cards",
        "body_pt": (
            "Todo card tem um verso misterioso: clique ou A para virar.\n"
            "Lá atrás moram Site, App e Config.\n"
            "No Config dá para favoritar (⭐), pintar o card da sua cor, "
            "trocar o link e a logo, ou excluir sem dó nem piedade.\n"
            "A borda neon mostra a cor do card — card bonito, sofá feliz.\n"
            "B ou ← desvira. Botão direito abre o menu rapidinho."
        ),
        "body_en": (
            "Every card has a mysterious back: click or press A to flip.\n"
            "Back there live Site, App and Config.\n"
            "In Config you can favorite (⭐), paint the card your color, "
            "change the link and logo, or delete with no mercy.\n"
            "The neon border shows the card color — pretty card, happy couch.\n"
            "B or ← unflips. Right click opens the quick menu."
        ),
    },
    {
        "key": "jogos",
        "icon": "\U0001F3AE",
        "title_pt": "Jogos",
        "title_en": "Games",
        "body_pt": (
            "A aba Jogos é uma estante mágica: cada pasta dentro de games/ "
            "vira um card sozinha, sem você fazer nada.\n"
            "Vire o card: Jogar executa o jogo; Config troca a capa e a cor "
            "(ou manda o jogo passear com Excluir).\n"
            "Atalhos e jogos de plataforma (Steam e cia) também entram "
            "na estante.\n"
            "Pasta vazia não vira card — o Nexus ainda não faz milagre."
        ),
        "body_en": (
            "The Games tab is a magic shelf: each folder inside games/ "
            "becomes a card all by itself.\n"
            "Flip the card: Play runs the game; Config swaps the cover and "
            "color (or sends the game away with Delete).\n"
            "Shortcuts and platform games (Steam and friends) join the "
            "shelf too.\n"
            "Empty folders don't become cards — Nexus does no miracles yet."
        ),
    },
    {
        "key": "ajustes",
        "icon": "\u2699",
        "title_pt": "Configurações",
        "title_en": "Settings",
        "body_pt": (
            "Menu > Controles: veja seus aparelhos conectados, troque "
            "entre eles, remapeie qualquer botão e ajuste a sensibilidade "
            "dos analógicos (para o analógico parar de andar sozinho).\n"
            "Menu > Som: volume de 0 a 100 para o blip de navegação, "
            "liga/desliga e botão Testar (aperte sem medo, não morde).\n"
            "Volume padrão: tudo que você abre (Spotify, Netflix, YouTube, "
            "jogos) já começa nele.\n"
            "Tudo que você mudar fica salvo — pode desligar o PC tranquilo."
        ),
        "body_en": (
            "Menu > Controls: see your connected gamepads, switch between "
            "them, remap any button and tune stick sensitivity (so the "
            "stick stops walking alone).\n"
            "Menu > Sound: volume 0 to 100 for the navigation blip, "
            "on/off switch and Test button (press it, it doesn't bite).\n"
            "Default volume: everything you open starts at it.\n"
            "Everything you change is saved — shut down in peace."
        ),
    },
    {
        "key": "sistema",
        "icon": "\U0001F514",
        "title_pt": "Notificações, Temas e Sistema",
        "title_en": "Notifications, Themes and System",
        "body_pt": (
            "O sino 🔔 fica vermelho quando tem novidade — versão nova "
            "sempre conta o que mudou, sem mistério.\n"
            "Menu > Tema: pinta o app da sua cor favorita num painel lateral.\n"
            "Menu > Sistema: resolução da tela, limpar logins e cache, "
            "resgatar jogos ignorados e caçar atualizações.\n"
            "F11: tela cheia. N: abre as notificações. B: quase sempre volta."
        ),
        "body_en": (
            "The bell 🔔 turns red when there's news — new versions always "
            "tell you what changed, no mystery.\n"
            "Menu > Theme: paint the app your favorite color in a panel.\n"
            "Menu > System: screen resolution, clear logins and cache, "
            "rescue ignored games and hunt for updates.\n"
            "F11: fullscreen. N: opens notifications. B: almost always back."
        ),
    },
]


def guide_title(lang):
    return "Guia de uso" if (lang or "").startswith("pt") else "User guide"


def guide_cat_title(cat, lang):
    key = "title_pt" if (lang or "").startswith("pt") else "title_en"
    return cat.get(key, cat.get("title_pt", ""))


def guide_cat_body(cat, lang):
    key = "body_pt" if (lang or "").startswith("pt") else "body_en"
    return cat.get(key, cat.get("body_pt", ""))
