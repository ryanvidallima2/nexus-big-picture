# Nexus - Big Picture v5.7.0

Interface de streaming inspirada no Steam Big Picture Mode.

## Recursos

- **Design Big Picture**: Cards grandes com cores do servico, hover effects, fundo escuro imersivo
- **32 Streamings**: Netflix, YouTube, Spotify, Disney+, Amazon Prime, HBO Max, Twitch, Crunchyroll, e mais
- **Deep Links**: Abre filmes/series diretamente no app ou navegador
- **Banco SQLite**: Historico de assistidos e estatisticas
- **Sidebar**: Painel lateral estilo Steam com historico, favoritos, configuracoes
- **Navegacao por teclado**: Setas para navegar, Enter para selecionar, Esc para voltar
- **Gamepad**: Suporte universal (Xbox, PlayStation, Switch, genericos) via pygame + SDL - deteccao automatica do tipo com nomes de botoes de cada familia (A vs. X vs. B...), D-pad por hat ou botoes conforme o controle
- **Seletor de controle**: Configuracoes > Controles lista todos os conectados (cabo, Bluetooth, 2.4GHz, virtuais) com tipo e conexao/bateria; troca com 1 clique, hot-plug e memoria por aparelho
- **Otimizacao por conexao**: zona morta ajustavel (ideal p/ drift no Bluetooth), calibracao automatica, polling 60Hz; dongle 2.4GHz aparece como Cabo (latencia minima)
- **Abas**: Favoritos, Filmes, Musica, Videos, Todos, Jogos, Jogos Favoritos
- **Busca**: Barra de pesquisa em todas as abas com filtro em tempo real ("Buscar aplicativo..."/"Buscar jogo...")
- **Logos**: Sistema automatico de busca por `{nome}_logo.{ext}` na pasta `streaming_images`
- **Trocar logo**: Clique direito > Trocar Logo
- **Adicionar streaming**: Formulario completo com nome, URL, categoria e logo
- **Favoritos**: Adicionar/remover com clique direito; aba Favoritos so p/ aplicativos e aba Jogos Favoritos so p/ jogos
- **Navegador embutido**: botao Site abre o servico em tela cheia sem bordas numa janela do proprio Nexus (WebView2), com transicao e mesmo icone na barra de tarefas - parece um app so. Barra discreta com minimizar/fechar, F11 p/ tela cheia e confirmacao de saida. Janela unica no Alt+Tab: minimizar leva tudo junto e voltar pela tarefa restaura tudo
- **Logins salvos**: perfil persistente mantem logins, cookies e senhas entre sessoes; limpeza em Configuracoes > Limpar logins e cache
- **Apps em tela cheia**: botao App forca o aplicativo a fullscreen sem bordas (modo big picture); ao fechar, o Nexus volta em ~0,5s e sempre maximizado
- **Leitura rapida**: logos com cache de caminho e miniaturas otimizadas; abertura de sites ~2x mais rapida
- **Teclado virtual**: ⌨ na sidebar e nos campos de texto - analogico/setas movem, confirmar tecla; tecla de verdade onde o foco estiver (vale nos logins do navegador). Abre sozinho ao clicar no campo; detecta numerico (123) vs letras, com alternador manual. Tecla BR/US troca o layout ABNT2 (com Ç) e US; no BR, a fileira ´ ^ ~ acentua a vogal seguinte (tecla morta). Vale nos campos do Nexus e nos apps
- **Foco unificado**: cursor do mouse e selecao sao uma coisa so - navegar com controle/teclado leva o cursor junto; apontar com o mouse leva o foco junto
- **Modo console nos sites**: no navegador embutido, setas/analogico selecionam os quadros (filmes, series) com anel roxo como num videogame, rolando o catalogo sozinho; A abre, B volta. R1/L1 percorrem as abas de categoria; modal flutuante (ex. preview Netflix) ganha prioridade automatica
- **Bola no menu principal**: pergunta sair ou nao sair do aplicativo
- **Midia no controle**: botao Back/View = play/pause universal (Spotify, Netflix, YouTube); proxima/anterior remapeaveis em Controles
- **Shoulders e gatilhos**: LB/RB trocam abas dentro dos apps (Ctrl+Tab); LT/RT controlam o volume (com repeticao ao segurar)
- **L1/R1/L2/R2 no PS**: abas em L1/R1 e volume em L2/R2 como acoes mapeaveis (eixo analogico comanda junto, sem duplo)
- **3 perfis de botoes**: slot 1 sempre o padrao; slots 2-3 salvos com o nome que quiser (mapeamento manual por clique + pressao, compativel com qq controle)
- **Hub em fullscreen**: abre em tela cheia sem bordas (F11 alterna); controles com deteccao automatica e area de teste ao vivo em Configuracoes > Controles
- **Instalacao automatica**: botao App baixa e instala sozinho via winget/Store quando o app nao esta instalado
- **Aba Jogos**: 3 formas - (1) botao Detectar puxa instalados da Steam, Epic e Xbox sozinho (sem login); (2) cada pasta em `games/` vira um card; (3) Adicionar .exe cria atalho sem mover o jogo. Capas oficiais automaticas, 4 modos de exibicao e pop-up com botao Jogar
- **Modos de exibicao**: todas as abas tem Cards, Grade, Lista e Detalhes estilo Windows Explorer (lembrado por aba)
- **Atualizacao automatica**: o Nexus avisa e se atualiza sozinho pela aba Configuracoes ou na abertura
- **Resolucoes**: Tela cheia, 1920x1080, 1400x900, 1280x720, Janela
- **Temas**: 8 cores de destaque disponiveis

## Como Rodar

1. Baixe o **`Nexus-vX.X.X-windows.zip`** na pagina de Releases do GitHub
2. Extraia numa pasta e duplo clique em **`Nexus.exe`** (sem instalar nada)
3. Para atualizar: o proprio app avisa, ou use Configuracoes > Verificar atualizacao

Para desenvolver (`start.bat` / `python bigpicture.py`), veja Requisitos abaixo.

## Atalhos de Teclado

| Tecla | Funcao |
|-------|--------|
| Setas | Navegar entre cards |
| Enter / Espaco | Abrir streaming selecionado |
| Esc | Voltar / Fechar sidebar |
| F11 | Tela cheia |
| F5 | Atualizar |
| Ctrl+Q | Abrir sidebar |

## Controles do Gamepad

| Botao | Funcao |
|-------|--------|
| A / X | Selecionar |
| B / Circulo | Voltar |
| D-Pad | Navegar |
| LB / RB | Trocar aba |
| Start | Abrir sidebar |

## Streamings Incluidos (32)

Netflix, YouTube, Spotify, Disney+, Amazon Prime, HBO Max, Twitch, Crunchyroll,
Dailymotion, Bandcamp, SoundCloud, Pluto TV, Apple TV, Peacock, Paramount+,
Discovery+, Globoplay, Vix, Curiosity Stream, MUBI, Shudder, BritBox, Tubi,
Plex, Kodi, Jellyfin, Mixer, Vimeo, Rumble, Tidal, Deezer, Mixcloud

## Requisitos (so para desenvolver)

- Windows 10 ou superior
- Python 3.12
- Pillow (`pip install Pillow`)
- pygame (`pip install pygame`) - opcional, para gamepad
- pywebview (`pip install pywebview`) - navegador embutido (usa o WebView2 do Windows)
- winget (ja vem no Windows 10/11) - instalacao automatica de apps
- Internet

## Pasta do .exe (release)

```
Nexus/
├── Nexus.exe                # Aplicativo (duplo clique)
├── nexus_browser.exe        # Navegador embutido (aberto pelo Nexus)
├── streaming_images/        # Logos dos streamings
├── logo_nexus/              # Icones do Nexus
├── games/                   # Seus jogos (uma pasta por jogo) - crie se nao existir
├── settings.json            # Criado sozinho no 1o uso
├── nexus.db                 # Criado sozinho no 1o uso
└── README.md                # Este arquivo
```

## Estrutura do codigo (desenvolvimento)

```
Nexus App/
├── bigpicture.py          # Entry fino (48 linhas: Tk + BigPictureApp + main)
├── nexus_browser.py       # Janela do navegador embutido (Site)
├── nexus/                 # Pacote interno (27 modulos)
│   ├── app.py             # BigPictureApp (composicao dos 6 mixins abaixo)
│   ├── app_shell.py       # Init + construcao da janela
│   ├── app_views.py       # Navegacao, abas e renderizacao base
│   ├── app_games.py       # Aba Jogos (deteccao, capas, lancamento)
│   ├── app_cards.py       # Cards, grade, lista e foco
│   ├── app_remote.py      # Mapeamento do controle e modo remoto
│   ├── app_settings.py    # Menus, sidebar, tema, idioma, update
│   ├── gamepad.py         # GamepadManager (polling pygame)
│   ├── keyboard.py        # Teclado virtual
│   ├── panels.py          # SidePanel (5 paineis) + GamepadConfigWindow
│   ├── dialogs.py         # OpenTarget/GameCard/Texto/Menu + modais
│   ├── i18n.py            # TRANSLATIONS pt-br/en + t()/cat_label()
│   ├── streamings.py      # Base dos 32 servicos
│   ├── games.py           # Steam/Epic/Xbox + capas
│   ├── apps.py            # UWP/atalho/exe + winget/Store
│   ├── input.py           # SendInput + sons + campo de texto
│   ├── pad.py             # Mapas e watch lists do controle
│   ├── win32.py           # Fullscreen, hwnd, titulo escuro (DWM)
│   ├── browser.py         # Processo do navegador embutido
│   ├── opener.py          # Deep-link / URL (com fallback externo)
│   ├── paths.py           # Pastas, perfil, BROWSER_PROCS
│   ├── config.py          # Config, settings.json, abas, modos
│   ├── database.py        # SQLite (historico, stats)
│   ├── focus.py           # Foco unificado mouse+teclado+controle
│   ├── util.py            # Normalizacao (_norm)
│   ├── update.py          # Release GitHub + changelog
│   └── version.py         # APP_VERSION (5.5.0)
├── tests/
│   └── smoke.py           # Suite: py_compile + boot + render + modulos
│                          # (rode: Python\python.exe tests\smoke.py)
├── start.bat              # Launcher
├── settings.json          # Configuracoes salvas (local, nao vai p/ git)
├── nexus.db               # Banco SQLite (local, nao vai p/ git)
├── streaming_images/      # Logos dos streamings
│   ├── Netflix_logo.jpg
│   ├── YouTube_logo.png
│   └── ... (32 arquivos)
└── README.md              # Este arquivo
```

## Rodar em outro PC (sem configurar nada)

1. Copie a pasta inteira para o outro PC (pendrive, rede, etc.).
2. Duplo clique em `start.bat`.

O launcher encontra o Python sozinho (qualquer instalacao 3.10+),
instala o que faltar (Pillow obrigatorio; pywebview/pygame se der),
limpa cache velho de outro Python e abre sem console. Na primeira vez
precisa de internet para baixar as dependencias.

- Sem pygame (ex.: Python 3.14 ainda sem wheel): o app abre normal,
  so o controle fica indisponivel (mouse/teclado funcionam).
- Para comecar do zero nessa maquina, apague `settings.json` e
  `nexus.db` (sao recriados; nao vao para o git).
