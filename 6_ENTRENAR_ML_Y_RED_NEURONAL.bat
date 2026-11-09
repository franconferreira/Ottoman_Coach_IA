@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Entrenamiento ML y Red Neuronal MLP - 560 Ejemplos
echo ============================================================================
echo   ENTRENANDO MODELOS ML Y RED NEURONAL MLP (560 EJEMPLOS)
echo ============================================================================
echo.
python mi_desarrollo\entrenar.py
echo.
pause
