@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Ottoman Coach IA - Modo Completo en Vivo (Camara + Microfono)
echo ============================================================================
echo   LANZANDO MODO EN VIVO CON SENSORES REALES (CAMARA + MICROFONO)
echo ============================================================================
echo.
echo Activando lectura facial OpenCV por webcam y analisis acustico DSP por microfono...
echo.
python mi_desarrollo\mi_tp07.py --ml --dashboard --camara --voz
echo.
pause
