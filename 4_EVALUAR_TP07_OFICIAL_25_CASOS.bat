@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Evaluacion TP07 Oficial - 25 Casos
echo ============================================================================
echo   CORRIENDO EVALUADOR OFICIAL DE LA CATEDRA (25 CASOS DE CASOS_PRUEBA.JSON)
echo ============================================================================
echo.
python mi_desarrollo\mi_tp07.py --sin-robot --ml
echo.
pause
