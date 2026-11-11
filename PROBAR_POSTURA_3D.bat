@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Ottoman Coach IA -- Estudio de Animaciones y Biomecanica 3D
REM   Robot Humanoide Unitree G1 (29 DoF + Manos Inspire RH56)
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo   Inteligencia Artificial - UADE
echo   ESTUDIO Y CATALOGO DE ANIMACIONES Y BIOMECANICA 3D (G1)
echo ============================================================
echo.
echo   Abriendo el visor interactivo completo:
echo     [1] Emotes Teatrales (Alegria, Tristeza, Enojo, Ansiedad, Duda, Neutro, Crisis)
echo     [2] Locomocion Bipeda (Caminar, Girar, Saludar, Reposo vivo)
echo     [3] Galeria de Manos 6-DoF (Cascada, Pulgar, Puno, Pecho, Freno, Apuntar)
echo     [4] Capas Vivas (Respiracion diafragmatica, Sway pendular, Co-speech)
echo     [5] Camaras Multicangulo (Frontal, Torso, Manos Close-Up, Perfil 3/4)
echo.
echo ============================================================
echo.

python mi_desarrollo\demo_posturas_3d.py

if errorlevel 1 (
    echo.
    echo [AVISO] El visor termino con codigo de error: %errorlevel%
    pause
)
