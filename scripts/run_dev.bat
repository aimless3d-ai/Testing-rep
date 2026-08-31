@echo off
REM Startet die App direkt aus dem Quellcode (fuer Entwicklung/Test).
setlocal
cd /d "%~dp0.."
if not exist ".venv" (
    echo Virtuelle Umgebung wird angelegt...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)
set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe -m vinted_tool
