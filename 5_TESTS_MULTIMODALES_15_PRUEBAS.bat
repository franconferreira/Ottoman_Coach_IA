@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Evaluacion Multimodal y de Reglas - 15 Pruebas
echo ============================================================================
echo   CORRIENDO SUITE DE VERIFICACION INTEGRAL MULTIMODAL (15 PRUEBAS)
echo ============================================================================
echo.
python mi_desarrollo\evaluar_coach.py
echo.
pause
