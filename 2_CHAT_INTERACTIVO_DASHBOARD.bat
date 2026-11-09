@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Ottoman Coach IA - Modo Interactivo con Dashboard
echo ============================================================================
echo   LANZANDO MODO INTERACTIVO (DASHBOARD + CHAT + VOZ DEL ROBOT)
echo ============================================================================
echo.
echo Se abrira el Dashboard en vivo y podras chatear con Ottoman por consola.
echo Escribi frases emocionales (ej: 'estoy colapsando de ansiedad') o comandos fisicos.
echo.
python mi_desarrollo\mi_tp07.py --ml --dashboard
echo.
pause
