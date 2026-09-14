# Nexus - Big Picture v5.3

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
- **Abas**: Home, Favoritos, Filmes, Musica, Videos, Todos
- **Busca**: Pesquisa por nome em tempo real
- **Logos**: Sistema automatico de busca por `{nome}_logo.{ext}` na pasta `streaming_images`
- **Trocar logo**: Clique direito > Trocar Logo
- **Adicionar streaming**: Formulario completo com nome, URL, categoria e logo
- **Favoritos**: Adicionar/remover com clique direito
- **Navegador embutido**: botao Site abre o servico em tela cheia sem bordas numa janela do proprio Nexus (WebView2), com transicao e mesmo icone na barra de tarefas - parece um app so. Barra discreta com minimizar/fechar, F11 p/ tela cheia e confirmacao de saida
- **Logins salvos**: perfil persistente mantem logins, cookies e senhas entre sessoes; limpeza em Configuracoes > Limpar logins e cache
- **Apps em tela cheia**: botao App forca o aplicativo a fullscreen sem bordas (modo big picture); ao fechar, o Nexus volta em ~0,5s e sempre maximizado
- **Leitura rapida**: logos com cache de caminho e miniaturas otimizadas; abertura de sites ~2x mais rapida
- **Teclado virtual**: ⌨ na sidebar e nos campos de texto - analogico/setas movem, confirmar tecla; tecla de verdade onde o foco estiver (vale nos logins do navegador). Abre sozinho ao clicar no campo; detecta numerico (123) vs letras, com alternador manual
- **Foco unificado**: cursor do mouse e selecao sao uma coisa so - navegar com controle/teclado leva o cursor junto; apontar com o mouse leva o foco junto
- **Modo console nos sites**: no navegador embutido, setas/analogico selecionam os quadros (filmes, series) com anel roxo como num videogame, rolando o catalogo sozinho; A abre, B volta. R1/L1 percorrem as abas de categoria; modal flutuante (ex. preview Netflix) ganha prioridade automatica
- **Bola no menu principal**: pergunta sair ou nao sair do aplicativo
- **Midia no controle**: botao Back/View = play/pause universal (Spotify, Netflix, YouTube); proxima/anterior remapeaveis em Controles
- **Shoulders e gatilhos**: LB/RB trocam abas dentro dos apps (Ctrl+Tab); LT/RT controlam o volume (com repeticao ao segurar)
- **L1/R1/L2/R2 no PS**: abas em L1/R1 e volume em L2/R2 como acoes mapeaveis (eixo analogico comanda junto, sem duplo)
- **3 perfis de botoes**: slot 1 sempre o padrao; slots 2-3 salvos com o nome que quiser (mapeamento manual por clique + pressao, compativel com qq controle)
- **Hub em fullscreen**: abre em tela cheia sem bordas (F11 alterna); controles com deteccao automatica e area de teste ao vivo em Configuracoes > Controles
- **Instalacao automatica**: botao App baixa e instala sozinho via winget/Store quando o app nao esta instalado
- **Resolucoes**: Tela cheia, 1920x1080, 1400x900, 1280x720, Janela
- **Temas**: 8 cores de destaque disponiveis

## Como Rodar

1. Duplo clique em **`Nexus.exe`**

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

## Requisitos

- Windows 10 ou superior
- Python 3.12
- Pillow (`pip install Pillow`)
- pygame (`pip install pygame`) - opcional, para gamepad
- pywebview (`pip install pywebview`) - navegador embutido (usa o WebView2 do Windows)
- winget (ja vem no Windows 10/11) - instalacao automatica de apps
- Internet

## Estrutura de Pastas

```
Default Project/
├── bigpicture.py          # Codigo principal
├── nexus_browser.py       # Janela do navegador embutido (Site)
├── start.bat              # Launcher
├── settings.json          # Configuracoes salvas
├── nexus.db               # Banco SQLite (criado automaticamente)
├── streaming_images/      # Logos dos streamings
│   ├── Netflix_logo.jpg
│   ├── YouTube_logo.png
│   └── ... (32 arquivos)
└── README.md              # Este arquivo
```
