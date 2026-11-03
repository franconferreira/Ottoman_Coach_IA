@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================================
echo    OTTOMAN COACH IA - Agente de Regulacion Emocional Multimodal (UADE)
echo    Robot Humanoide Unitree G1 (Cara + Voz + Lexico + Cuerpo + Rostro 60FPS)
echo ============================================================================
echo.
echo    Recordatorio: Si queres ver el cuerpo 3D de Ottoman en movimiento,
echo    abri primero INICIAR_SIMULADOR.bat en otra ventana (Opcion 1 = G1).
echo.
echo    Elegi el modo de ejecucion:
echo.
echo      1) Modo Interactivo (Teclado + Rostro Animado + Voz Adaptativa + G1)
echo      2) Modo Multimodal Completo EN VIVO (Camara Facial + Microfono + Voz + G1)
echo      3) Demo Automatica de los 6 Perfiles Emocionales e Incongruencia
echo      4) Evaluacion Oficial TP07 (25 casos) + Benchmark ML + Tests Multimodales
echo.
set MODO=1
set /p MODO="   Opcion [1-4, Enter=1]: "
echo.

if "%MODO%"=="2" (
    python mi_desarrollo\mi_tp07.py --ml --camara --voz
    goto :fin
)
if "%MODO%"=="3" (
    python mi_desarrollo\mi_tp07.py --ml --demo-coach
    goto :fin
)
if "%MODO%"=="4" (
    python mi_desarrollo\mi_tp07.py --sin-robot --ml
    python mi_desarrollo\entrenar.py
    python mi_desarrollo\evaluar_coach.py
    goto :fin
)

python mi_desarrollo\mi_tp07.py --ml

:fin
echo.
pause
