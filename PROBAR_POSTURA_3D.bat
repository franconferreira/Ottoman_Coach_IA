@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Demo 3D: Postura y Gesticulación al Hablar (Unitree G1)
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo    DEMO STANDALONE: POSTURAS Y GESTICULACIÓN 3D (G1)
echo ============================================================
echo.
echo    Abriendo visor interactivo 3D del humanoide...
echo.

python mi_desarrollo\demo_posturas_3d.py

if errorlevel 1 (
    echo.
    echo [AVISO] El programa terminó con código de error: %errorlevel%
    pause
)
