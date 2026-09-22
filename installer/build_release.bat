@echo off
setlocal EnableExtensions
rem Nexus - monta a pasta release\Nexus e (se houver Inno) o setup.
rem Uso: installer\build_release.bat   (rode na pasta do projeto)
cd /d "%~dp0.."
title Nexus - build da release

where python >nul 2>&1
if errorlevel 1 (
    echo [Nexus] Python nao encontrado no PATH.
    exit /b 1
)

echo [Nexus] Instalando deps de build...
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [Nexus] Falha no requirements obrigatorio.
    exit /b 1
)
python -m pip install --disable-pip-version-check pyinstaller pywebview pygame >nul 2>&1

echo [Nexus] Gerando placeholders de imagem (Fase 1: sem marca)...
python generate_logos.py

echo [Nexus] Limpando saidas antigas...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist release\Nexus rmdir /s /q release\Nexus
mkdir release\Nexus

echo [Nexus] Compilando Nexus.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name Nexus --icon logo_nexus\Nexus.ico ^
    --add-data "assets;assets" --add-data "logo_nexus;logo_nexus" ^
    bigpicture.py
if errorlevel 1 (
    echo [Nexus] Falha ao compilar Nexus.exe.
    exit /b 1
)

echo [Nexus] Compilando nexus_browser.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name nexus_browser ^
    nexus_browser.py
if errorlevel 1 (
    echo [Nexus] Falha ao compilar nexus_browser.exe.
    exit /b 1
)

echo [Nexus] Montando release\Nexus...
copy /y dist\Nexus.exe release\Nexus\ >nul
copy /y dist\nexus_browser.exe release\Nexus\ >nul
if exist assets xcopy /e /i /y assets release\Nexus\assets >nul
if exist logo_nexus xcopy /e /i /y logo_nexus release\Nexus\logo_nexus >nul
if exist streaming_images xcopy /e /i /y streaming_images release\Nexus\streaming_images >nul
if not exist release\Nexus\games mkdir release\Nexus\games
copy /y README.md release\Nexus\ >nul

where iscc >nul 2>&1
if not errorlevel 1 (
    echo [Nexus] Compilando instalador...
    iscc installer\nexus.iss
    if errorlevel 1 (
        echo [Nexus] Falha no Inno Setup.
        exit /b 1
    )
) else (
    echo [Nexus] ISCC nao encontrado: release pronta em release\Nexus\.
    echo [Nexus] Instale o Inno Setup 6 e rode: iscc installer\nexus.iss
)

echo [Nexus] OK.
