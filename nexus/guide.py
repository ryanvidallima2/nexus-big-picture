# -*- coding: utf-8 -*-
"""Manual de uso do Nexus (Guia/POP por categoria, PT-BR + EN)."""

GUIDE_CATS = [
    {
        "key": "controle",
        "icon": "\U0001F3AE",
        "title_pt": "Controle no Nexus",
        "title_en": "Gamepad in Nexus",
        "body_pt": (
            "D-pad / analógico esquerdo: navegar entre abas e cards.\n"
            "A: confirmar / abrir / virar o card.\n"
            "B: voltar (no card virado, desvira; no menu, fecha).\n"
            "X: ir direto para os cards. Y: menu lateral.\n"
            "LB / RB: trocar de aba. Start: notificações."
        ),
        "body_en": (
            "D-pad / left stick: move between tabs and cards.\n"
            "A: confirm / open / flip the card.\n"
            "B: back (unflips card; closes menu).\n"
            "X: jump to cards. Y: sidebar.\n"
            "LB / RB: switch tabs. Start: notifications."
        ),
    },
    {
        "key": "assistir",
        "icon": "\U0001F4FA",
        "title_pt": "Assistindo",
        "title_en": "Watching",
        "body_pt": (
            "Clique ou A no card e escolha no verso:\n"
            "Site: abre no navegador (embutido ou normal).\n"
            "App: abre o aplicativo instalado (ou instala via loja).\n"
            "No app/site, o controle vira controle remoto: analógico "
            "direito move o mouse, esquerdo rola, A clica.\n"
            "Back + Start juntos: volta para o Nexus."
        ),
        "body_en": (
            "Click or press A on the card and choose on the back:\n"
            "Site: opens in the browser (embedded or default).\n"
            "App: opens the installed app (or installs from store).\n"
            "In the app/site the gamepad becomes a remote: right stick "
            "moves the mouse, left stick scrolls, A clicks.\n"
            "Back + Start together: back to Nexus."
        ),
    },
    {
        "key": "teclado",
        "icon": "\u2328",
        "title_pt": "Teclado virtual",
        "title_en": "Virtual keyboard",
        "body_pt": (
            "Com o controle, clique (A) numa barra de texto: o teclado "
            "abre sozinho (1 clique basta).\n"
            "?123: símbolos. Emoji: emojis. Shift: maiúsculas.\n"
            "No controle: D-pad move, A digita, B fecha, Start confirma.\n"
            "Botão ⬇ ancora o teclado na base (dock); ⬆ solta."
        ),
        "body_en": (
            "With the gamepad, click (A) a text field: the keyboard "
            "opens by itself (single click).\n"
            "?123: symbols. Emoji: emojis. Shift: uppercase.\n"
            "On gamepad: D-pad moves, A types, B closes, Start submits.\n"
            "⬇ docks the keyboard at the bottom; ⬆ undocks."
        ),
    },
    {
        "key": "cards",
        "icon": "\U0001F0CF",
        "title_pt": "Cards",
        "title_en": "Cards",
        "body_pt": (
            "Cada card tem um verso: clique ou A para virar.\n"
            "No verso: Site, App e Config (favorito, cor, link, logo, "
            "excluir) — tudo sem abrir janelas.\n"
            "Borda neon na cor do card. B ou ← desvira.\n"
            "Botão direito: menu rápido (abrir, favorito, logo)."
        ),
        "body_en": (
            "Each card has a back: click or press A to flip.\n"
            "On the back: Site, App and Config (favorite, color, link, "
            "logo, delete) — no popups.\n"
            "Neon border in the card color. B or ← unflips.\n"
            "Right click: quick menu (open, favorite, logo)."
        ),
    },
    {
        "key": "jogos",
        "icon": "\U0001F3AE",
        "title_pt": "Jogos",
        "title_en": "Games",
        "body_pt": (
            "Aba Jogos: cada pasta dentro de games/ vira um card.\n"
            "Vire o card: Jogar abre o .exe; Config troca capa, cor e "
            "exclui.\n"
            "Atalhos e plataformas (Steam etc.) também aparecem aqui."
        ),
        "body_en": (
            "Games tab: each folder inside games/ becomes a card.\n"
            "Flip the card: Play runs the .exe; Config changes cover, "
            "color and deletes.\n"
            "Shortcuts and platforms (Steam etc.) show up here too."
        ),
    },
    {
        "key": "ajustes",
        "icon": "\u2699",
        "title_pt": "Controles e Som",
        "title_en": "Controls and Sound",
        "body_pt": (
            "Menu > Controles: lista de aparelhos (troca com 1 clique), "
            "remapear botões, sensibilidade e teclado virtual.\n"
            "Cada controle guarda o próprio mapa.\n"
            "Menu > Som: volume 0-100, liga/desliga o blip de navegação, "
            "botão Testar."
        ),
        "body_en": (
            "Menu > Controls: device list (switch with 1 click), "
            "button remap, sensitivity and virtual keyboard.\n"
            "Each gamepad keeps its own mapping.\n"
            "Menu > Sound: volume 0-100, navigation blip on/off, Test."
        ),
    },
    {
        "key": "sistema",
        "icon": "\U0001F514",
        "title_pt": "Notificações, Temas e Sistema",
        "title_en": "Notifications, Themes and System",
        "body_pt": (
            "Sino: vermelho = novidade (versão nova lista o que mudou).\n"
            "Menu > Tema: troca a cor do app num painel lateral.\n"
            "Menu > Sistema: resolução, limpar logins/cache, restaurar "
            "jogos ignorados e verificar atualizações.\n"
            "F11: tela cheia. N: notificações."
        ),
        "body_en": (
            "Bell: red = news (new versions list what changed).\n"
            "Menu > Theme: change the app color in a side panel.\n"
            "Menu > System: resolution, clear logins/cache, restore "
            "ignored games and check for updates.\n"
            "F11: fullscreen. N: notifications."
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
