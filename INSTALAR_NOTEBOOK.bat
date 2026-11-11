@echo off
REM ============================================================
REM   Inteligencia Artificial - UADE (TPO Final)
REM   Ottoman Coach IA -- Instalador Rápido para Notebook / PC
REM ============================================================
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================================
echo   OTTOMAN COACH IA -- INSTALADOR DE DEPENDENCIAS
echo   Universidad Argentina de la Empresa (UADE)
echo ============================================================
echo.

REM 1. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se detecto Python en el sistema o no esta en el PATH.
    echo.
    echo Por favor instala Python 3.10, 3.11 o 3.12 desde https://www.python.org/downloads/
    echo IMPORTANTE: Marca la casilla "[X] Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python detectado:
python --version
echo.

REM 2. Actualizar pip e instalar requirements.txt
echo [2/3] Instalando librerias cientificas, ML, vision y simulacion...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [AVISO] Ocurrio un inconveniente al instalar alguna libreria.
    echo Verifica tu conexion a internet o permisos de instalacion.
    pause
    exit /b 1
)

REM 3. Intentar instalar PyAudio (opcional para microfono en vivo)
echo.
echo [3/3] Intentando instalar soporte de microfono en vivo (PyAudio)...
python -m pip install pyaudio >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyAudio no se pudo instalar de forma automatica (opcional).
    echo [INFO] El sistema funcionara 100%% en modo texto/chat y con voz de salida.
) else (
    echo [OK] Soporte de microfono en vivo instalado correctamente.
)

echo.
echo ============================================================
echo   VERIFICACION RAPIDA DE COMPONENTES NUCLEO
echo ============================================================
python -c "import numpy, scipy, sklearn, joblib, cv2, mujoco, pyttsx3; print('[TODO OK] Nucleo cientifico, ML, Vision y Simulacion listo.')"
if errorlevel 1 (
    echo [ALERTA] Alguna libreria fallo al importarse. Revisa los mensajes anteriores.
) else (
    echo.
    echo ============================================================
    echo   INSTALACION COMPLETADA CON EXITO
    echo ============================================================
    echo.
    echo Podes ejecutar el sistema con:
    echo   * INICIAR_OTTOMAN.bat  (Dashboard multimodal completo)
    echo   * EVALUAR_TODO.bat     (25 casos oficiales + 16 pruebas)
)
echo.
pause
