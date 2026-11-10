@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Ottoman Coach IA -- Sistema Multimodal Unificado
REM   Unitree G1 Humanoide (Simulador 3D + Rostro + FACS + Voz + Chat)
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo    Inteligencia Artificial - UADE
echo    OTTOMAN COACH IA -- SISTEMA MULTIMODAL UNIFICADO
echo    Robot Humanoide Unitree G1 (29 Grados de Libertad)
echo ============================================================
echo.
echo    Iniciando Pantalla Unificada:
echo      * Simulador 3D MuJoCo G1 embebido
echo      * Rostro Afectivo y Lip-Sync
echo      * Vision FACS OpenCV y Plano Valencia-Arousal
echo      * Sensores en vivo con reconexion en caliente
echo      * Chat interactivo con entrada en pantalla
echo.
echo ============================================================
echo.

python mi_desarrollo\mi_tp07.py --ml %*

if errorlevel 1 (
    echo.
    echo [AVISO] El programa termino con codigo de error: %errorlevel%
    pause
)
