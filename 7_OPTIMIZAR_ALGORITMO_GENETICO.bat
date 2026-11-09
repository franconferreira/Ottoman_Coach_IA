@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Optimizacion Evolutiva - Algoritmo Genetico
echo ============================================================================
echo   EJECUTANDO ALGORITMO GENETICO (OPTIMIZACION FUSION MULTIMODAL)
echo ============================================================================
echo.
echo Evolucionando poblacion N=60 x G=50 generaciones sobre 180 escenarios...
echo.
python mi_desarrollo\algoritmo_genetico.py
echo.
pause
