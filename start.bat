@echo off
cd /d "%~dp0"
rem Nexus launcher - Python instalado em D:\Download\Python312
if exist "D:\Download\Python312\pythonw.exe" (
    start "" "D:\Download\Python312\pythonw.exe" bigpicture.py
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
where py >nul 2>nul
if %errorlevel%==0 (
    start "" py -w bigpicture.py
    exit /b
)
echo Python nao encontrado em D:\Download\Python312 nem no PATH.
pause
