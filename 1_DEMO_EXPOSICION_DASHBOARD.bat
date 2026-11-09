@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Ottoman Coach IA - Demo Exposicion en Vivo
echo ============================================================================
echo   LANZANDO DEMO AUTOMATICA DE EXPOSICION CON DASHBOARD MULTIMODAL
echo ============================================================================
echo.
echo Abriendo Dashboard 1240x700 y ejecutando los 6 perfiles afectivos...
echo (Si queres ver el cuerpo 3D, tene abierto antes INICIAR_SIMULADOR.bat)
echo.
python mi_desarrollo\mi_tp07.py --ml --dashboard --demo-coach
echo.
pause
