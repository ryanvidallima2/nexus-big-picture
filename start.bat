@echo off
cd /d "%~dp0"
rem Nexus launcher: tenta o Python em varios lugares (cada PC tem o seu).
rem 1) Maquina do Ryan
if exist "D:\Download\Python312\pythonw.exe" (
    start "" "D:\Download\Python312\pythonw.exe" bigpicture.py
    exit /b
)
rem 2) Instalacao per-user padrao (ex.: %LOCALAPPDATA%\Programs\Python\Python312)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" bigpicture.py
    exit /b
)
rem 3) Launcher py / pythonw / python no PATH
where py >nul 2>nul
if %errorlevel%==0 (
    start "" py -w bigpicture.py
    exit /b
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw bigpicture.py
    exit /b
)
where python >nul 2>nul
if %errorlevel%==0 (
    start "" python bigpicture.py
    exit /b
)
echo Python 3.12+ nao encontrado. Instale em python.org e rode de novo.
pause
