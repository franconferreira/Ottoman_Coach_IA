@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================================
echo    OTTOMAN COACH IA - Agente de Regulacion Emocional Multimodal (UADE)
echo    Unitree G1 + Dashboard (Rostro 60FPS + Camara FACS + Plano Russell V-A)
echo ============================================================================
echo.
echo    Recordatorio: Si queres ver el cuerpo 3D de Ottoman en movimiento,
echo    abri primero INICIAR_SIMULADOR.bat en otra ventana (Opcion 1 = G1).
echo.
echo    Elegi el modo de ejecucion:
echo.
echo      1) Modo Dashboard de Exposicion Interactivo (Rostro + Camara + Plano V-A + Voz)
echo      2) Modo Multimodal Completo EN VIVO (Dashboard + Camara + Microfono + G1)
echo      3) Demo Automatica de Exposicion (6 Perfiles + Enmascaramiento en Dashboard)
echo      4) Modo Visor Compacto Clasico (680x500 + Teclado + Voz Adaptativa)
echo      5) Suite Completa de Evaluacion (TP07 25/25 + MLP 560 ej. + Algoritmo Genetico)
echo.
set MODO=1
set /p MODO="   Opcion [1-5, Enter=1]: "
echo.

if "%MODO%"=="2" (
    python mi_desarrollo\mi_tp07.py --ml --dashboard --camara --voz
    goto :fin
)
if "%MODO%"=="3" (
    python mi_desarrollo\mi_tp07.py --ml --dashboard --demo-coach
    goto :fin
)
if "%MODO%"=="4" (
    python mi_desarrollo\mi_tp07.py --ml
    goto :fin
)
if "%MODO%"=="5" (
    python mi_desarrollo\mi_tp07.py --sin-robot --ml
    python mi_desarrollo\entrenar.py
    python mi_desarrollo\algoritmo_genetico.py
    python mi_desarrollo\evaluar_coach.py
    goto :fin
)

python mi_desarrollo\mi_tp07.py --ml --dashboard

:fin
echo.
pause
