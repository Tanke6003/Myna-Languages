@echo off
REM Doble clic para instalar Myna (instala Ollama, modelo y dependencias).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
