@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Nexus - Big Picture

rem ============================================================
rem  Nexus launcher universal: funciona em qualquer PC copiando
rem  a pasta. Nao edite caminhos aqui: o script descobre o Python
rem  sozinho (py launcher -> pastas conhecidas -> PATH), instala
rem  o que faltar e limpa cache obsoleto de outro Python.
rem ============================================================

rem 1) Limpa __pycache__ obsoleto (pasta copiada de outro PC/Python).
rem    Um .pyc de outra versao quebra o boot com AttributeError.
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

rem 2) Localiza o Python 3.10+. PYW = sem console (app), PY = pip.
rem    Pastas explicitas primeiro (deterministico); o comando `py` so vale
rem    se for o launcher de verdade (em alguns PCs `py` e o proprio
rem    python.exe, que nao entende `-w` e quebrava o boot).
rem    Entre os validos, prefere o que JA tem pygame (controle funciona
rem    sem instalar nada); o primeiro valido e o fallback.
set "PYW="
set "PY="
set "BESTW="
set "BEST="
for %%P in (
    "C:\Users\User\Desktop\Pasta do Ryan\Python\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
    "%ProgramFiles%\Python312\pythonw.exe"
    "%ProgramFiles%\Python313\pythonw.exe"
    "%ProgramFiles%\Python314\pythonw.exe"
    "D:\Download\Python312\pythonw.exe"
) do if exist %%P call :probe %%P
if defined BESTW (
    set "PYW=%BESTW%"
    set "PY=%BEST%"
)
if defined PYW goto :foundver
where py >nul 2>&1
if not errorlevel 1 (
    py --list >nul 2>&1
    if not errorlevel 1 (
        py -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
        if not errorlevel 1 (
            where pyw >nul 2>&1
            if not errorlevel 1 (
                set "PYW=pyw"
            ) else (
                set "PYW=py -w"
            )
            set "PY=py"
            goto :found
        )
    )
)
where pythonw >nul 2>&1
if not errorlevel 1 (
    set "PYW=pythonw"
    set "PY=python"
    goto :foundver
)
where python >nul 2>&1
if not errorlevel 1 (
    set "PYW=python"
    set "PY=python"
    goto :foundver
)
echo [Nexus] Python 3.10+ nao encontrado.
echo [Nexus] Instale em https://www.python.org/downloads/ ^(marque "Add to PATH"^) e rode de novo.
pause
exit /b 1

:foundver
"%PY%" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Encontrado mas antigo demais: %PYW%
    echo [Nexus] Instale o Python 3.10+ em https://www.python.org/downloads/ e rode de novo.
    pause
    exit /b 1
)

:found
if defined BESTW (
    set "PYW=%BESTW%"
    set "PY=%BEST%"
)
echo [Nexus] Usando: %PYW%
set "PYVER="
"%PY%" -c "import sys; open(r'%TEMP%\nexus_pyver.tmp','w').write(str(sys.version_info[0])+str(sys.version_info[1]))" >nul 2>&1
set /p PYVER=<"%TEMP%\nexus_pyver.tmp" 2>nul
del "%TEMP%\nexus_pyver.tmp" 2>nul

rem 3) Dependencia obrigatoria (sem Pillow o app nem abre).
"%PY%" -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Instalando Pillow...
    "%PY%" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo [Nexus] ERRO: nao consegui instalar o Pillow ^(sem internet?^).
        echo [Nexus] Rode uma vez com internet ou instale manual: "%PY%" -m pip install Pillow
        pause
        exit /b 1
    )
)

rem 4) Opcionais: tenta 1x por Python e segue o jogo se falhar.
rem    Falha carimbada em %TEMP% (por modulo+versao) p/ nao travar o boot
rem    seguinte retentando o impossivel (ex.: pygame sem wheel p/ 3.14).
"%PY%" -c "import webview" >nul 2>&1
if errorlevel 1 call :trypip webview pywebview "navegador embutido" "sem navegador embutido (abre no navegador normal)."
"%PY%" -c "import pygame" >nul 2>&1
if errorlevel 1 call :trypip pygame pygame "suporte a controle" "sem suporte a controle nesta maquina."

rem 5) Abre sem console.
if "%PYW%"=="py -w" (
    start "" py -w bigpicture.py
) else (
    start "" "%PYW%" bigpicture.py
)
exit /b 0

rem --- sub-rotinas (sair com goto :eof) ---
:probe
rem Avalia um pythonw.exe candidato: %1 vem com aspas.
set "CANDW=%~1"
set "CANDP=%~dp1python.exe"
if not exist "%CANDP%" set "CANDP=%~1"
"%CANDP%" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 goto :eof
if defined PYW goto havebest
set "PYW=%CANDW%"
set "PY=%CANDP%"
:havebest
if defined BESTW goto :eof
"%CANDP%" -c "import pygame" >nul 2>&1
if errorlevel 1 goto :eof
set "BESTW=%CANDW%"
set "BEST=%CANDP%"
goto :eof

:trypip
rem %1=modulo, %2=pacote pip, %3=descricao, %4=aviso de fallback.
if exist "%TEMP%\nexus_skip_%1_%PYVER%.flag" goto :eof
echo [Nexus] Instalando %~3 ^(%2^)...
"%PY%" -m pip install --disable-pip-version-check %2 >nul 2>&1
if not errorlevel 1 goto :eof
echo [Nexus] Aviso: %~4
type nul > "%TEMP%\nexus_skip_%1_%PYVER%.flag"
goto :eof
