@echo off
cd /d "%~dp0"
 
where python >nul 2>nul
if errorlevel 1 (
    echo Python n'est pas installe ou pas dans le PATH.
    echo Installe-le depuis https://www.python.org/downloads/ en cochant "Add python.exe to PATH".
    pause
    exit /b 1
)
 
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo L'installation des dependances a echoue.
    pause
    exit /b 1
)
 
start "" pythonw main.py