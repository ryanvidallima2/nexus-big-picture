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
set "PYW="
set "PY="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
    "%ProgramFiles%\Python312\pythonw.exe"
    "%ProgramFiles%\Python313\pythonw.exe"
    "%ProgramFiles%\Python314\pythonw.exe"
    "D:\Download\Python312\pythonw.exe"
) do (
    if exist %%P (
        set "PYW=%%~P"
        if exist "%%~dpPpython.exe" (
            set "PY=%%~dpPpython.exe"
        ) else (
            set "PY=%%~dpPpythonw.exe"
        )
        goto :foundver
    )
)
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
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Encontrado mas antigo demais: %PYW%
    echo [Nexus] Instale o Python 3.10+ em https://www.python.org/downloads/ e rode de novo.
    pause
    exit /b 1
)

:found
echo [Nexus] Usando: %PYW%

rem 3) Dependencia obrigatoria (sem Pillow o app nem abre).
%PY% -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Instalando Pillow...
    %PY% -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo [Nexus] ERRO: nao consegui instalar o Pillow ^(sem internet?^).
        echo [Nexus] Rode uma vez com internet ou instale manual: %PY% -m pip install Pillow
        pause
        exit /b 1
    )
)

rem 4) Opcionais: tenta, mas segue o jogo se falhar.
%PY% -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Instalando navegador embutido ^(pywebview^)...
    %PY% -m pip install --disable-pip-version-check pywebview >nul 2>&1
    if errorlevel 1 echo [Nexus] Aviso: sem navegador embutido ^(abre no navegador normal^).
)
%PY% -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Instalando suporte a controle ^(pygame^)...
    %PY% -m pip install --disable-pip-version-check pygame >nul 2>&1
    if errorlevel 1 echo [Nexus] Aviso: sem suporte a controle nesta maquina.
)

rem 5) Abre sem console.
start "" %PYW% bigpicture.py
exit /b 0
