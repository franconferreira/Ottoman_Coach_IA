@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Evaluador Completo: 25 Casos TP07 + 16 Pruebas Multimodales
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo    Inteligencia Artificial - UADE
echo    EVALUACION AUTOMATIZADA COMPLETA DE OTTOMAN COACH
echo ============================================================
echo.
echo [PARTE 1] Evaluando los 25 casos oficiales de TP07...
python mi_desarrollo\mi_tp07.py --sin-robot

echo.
echo [PARTE 2] Evaluando las 16 pruebas multimodales avanzadas...
python mi_desarrollo\evaluar_coach.py

echo.
echo ============================================================
echo    EVALUACION FINALIZADA
echo ============================================================
pause
