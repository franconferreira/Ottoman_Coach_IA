@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Ottoman Coach IA -- Estudio Visual de Animaciones y Biomecánica 3D
REM   Robot Humanoide Unitree G1 (29 DoF + Manos Diestras Inspire RH56)
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo   OTTOMAN COACH IA -- ESTUDIO Y CATÁLOGO DE ANIMACIONES 3D
echo   Universidad Argentina de la Empresa (UADE)
echo ============================================================
echo.
echo   Abriendo el visor interactivo completo:
echo     * 🎭 Emotes Teatrales (Alegría, Tristeza, Enojo, Ansiedad, Duda, Neutro, Crisis)
echo     * 🚶 Locomoción Bípeda (Caminar, Girar, Saludar, Reposo con vida)
echo     * 🖐️ Galería de Manos 6-DoF (Cascada, Pulgar, Puño, Pecho, Freno, Apuntar)
echo     * 🫁 Capas Vivas (Respiración diafragmática, Sway pendular, Co-speech)
echo     * 🎥 Cámaras Multicángulo (Frontal, Torso, Manos Close-Up, Perfil 3/4)
echo.
echo ============================================================
echo.

python mi_desarrollo\demo_posturas_3d.py

if errorlevel 1 (
    echo.
    echo [AVISO] El visor terminó con código de error: %errorlevel%
    pause
)
