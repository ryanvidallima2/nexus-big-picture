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
        "key": "login",
        "icon": "\U0001F464",
        "title_pt": "Login e perfis",
        "title_en": "Login and profiles",
        "body_pt": (
            "Um login, um perfil: ele guarda seus favoritos, ajustes e "
            "aparelhos pareados.\n"
            "O avatar redondo ao lado do relógio abre o login: criar perfil "
            "pede nome, PIN (4 a 8 dígitos, pode deixar vazio) e um avatar "
            "à sua escolha (troca depois no mesmo lugar).\n"
            "Quem tem cadeado pede o PIN na entrada. Sair volta a convidado.\n"
            "Sem login você passeia como convidado, mas controle pelo "
            "celular e alguns recursos pedem um perfil."
        ),
        "body_en": (
            "One login, one profile: it keeps your favorites, settings "
            "and paired devices.\n"
            "The round avatar next to the clock opens login: creating a "
            "profile asks for a name, a PIN (4 to 8 digits, may be empty) "
            "and an avatar of your choice (change it later in the same place).\n"
            "Locked ones ask for the PIN at the door. Signing out returns "
            "to guest.\n"
            "Without login you roam as a guest, but phone control and some "
            "features require a profile."
        ),
    },
    {
        "key": "celular",
        "icon": "\U0001F4F1",
        "title_pt": "Controle pelo celular",
        "title_en": "Phone control",
        "body_pt": (
            "Menu > Controles > Controle virtual: Ligue e o Nexus vira um "
            "servidor na sua rede (precisa de login no perfil).\n"
            "Gerar QR Code abre o código grandão: mire a câmera do celular "
            "e o site abre sozinho com tudo preenchido — é só Parear.\n"
            "Sem câmera? Digite IP, porta e código na tela Parear (ou use "
            "Testar conexão se empacar: mesmo roteador + porta liberada).\n"
            "Abas do site: Streams abre serviços no PC, Controle tem mouse, "
            "setas e teclado, e Jogo vira um controle completo (A/B/X/Y, "
            "ombros, gatilhos, Start) sem mouse na frente."
        ),
        "body_en": (
            "Menu > Controls > Virtual remote: turn it on and Nexus becomes "
            "a server on your network (profile login required).\n"
            "Generate QR Code opens a big code: point your phone camera and "
            "the site opens pre-filled — just Pair.\n"
            "No camera? Type IP, port and code on the Pair screen (or use "
            "Test connection if stuck: same router + open port).\n"
            "Site tabs: Streams opens services on the PC, Control has mouse, "
            "arrows and keyboard, and Game becomes a full gamepad (A/B/X/Y, "
            "bumpers, triggers, Start) with no mouse in the way."
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
            "Trocar logo usa só imagem do seu computador "
            "(sem busca automática por nome de serviço).\n"
            "A borda neon mostra a cor do card — card bonito, sofá feliz.\n"
            "B ou ← desvira. Botão direito abre o menu rapidinho."
        ),
        "body_en": (
            "Every card has a mysterious back: click or press A to flip.\n"
            "Back there live Site, App and Config.\n"
            "In Config you can favorite (⭐), paint the card your color, "
            "change the link and logo, or delete with no mercy.\n"
            "Change logo only uses an image from your own computer "
            "(no automatic search by service name).\n"
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
            "Botão Detectar: caça jogos instalados de Steam, Epic e Xbox "
            "e pendura as capas sozinho (rode de novo após instalar algo).\n"
            "Vire o card: Jogar executa o jogo; Config troca a capa e a cor "
            "(ou manda o jogo passear com Excluir).\n"
            "Atalhos e jogos de plataforma (Steam e cia) também entram "
            "na estante.\n"
            "Pasta vazia não vira card — o Nexus ainda não faz milagre."
        ),
        "body_en": (
            "The Games tab is a magic shelf: each folder inside games/ "
            "becomes a card all by itself.\n"
            "Detect button: hunts installed Steam, Epic and Xbox games "
            "and hangs their covers by itself (run it again after installs).\n"
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
            "Ali também mora o Controle virtual do celular: ligar, QR, "
            "rede e aparelhos pareados.\n"
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
            "The virtual phone remote also lives there: on/off, QR, "
            "network and paired devices.\n"
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
    {
        "key": "legal",
        "icon": "⚖",
        "title_pt": "Sobre / Aviso legal",
        "title_en": "About / Legal notice",
        "body_pt": (
            "Nexus não é afiliado a nenhum serviço de streaming mencionado. "
            "Todas as marcas e nomes citados pertencem aos seus respectivos donos.\n"
            "Os ícones padrão do app são genéricos (cor + iniciais/emoji) — "
            "sem logo oficial de terceiros.\n"
            "Trocar logo e Adicionar usam só imagem do seu computador; "
            "o Nexus nunca busca logo automática por nome de serviço."
        ),
        "body_en": (
            "Nexus is not affiliated with any streaming service mentioned. "
            "All brands and names belong to their respective owners.\n"
            "The app's default icons are generic (color + initials/emoji) — "
            "no third-party official logos.\n"
            "Change logo and Add only use an image from your own computer; "
            "Nexus never auto-fetches a logo by service name."
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
