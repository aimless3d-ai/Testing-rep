@echo off
REM Startet den PowerShell-Build fuer die Windows-Anwendung.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" %*
if errorlevel 1 (
    echo.
    echo Build fehlgeschlagen.
    pause
    exit /b 1
)
echo.
echo Build erfolgreich abgeschlossen.
pause
