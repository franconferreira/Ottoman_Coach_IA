#!/usr/bin/env bash
# ============================================================
#   Inteligencia Artificial - TP07
#   Levanta el simulador oficial de Unitree listo para el TP.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo "============================================================"
echo "   Inteligencia Artificial"
echo "   Simulador de robots Unitree"
echo "============================================================"
echo
echo "   Que robot queres usar?"
echo
echo "     1)  G1   - robot humanoide (camina en dos patas)"
echo "     2)  Go2  - robot perro     (camina en cuatro patas)"
echo
read -r -p "   Elegi 1 o 2 [1]: " OPCION

case "$OPCION" in
  2) ROBOT="go2" ;;
  *) ROBOT="g1"  ;;
esac
echo
echo "   Revisando que este todo instalado..."
echo "   (la primera vez puede tardar unos minutos)"
echo

# Buscamos un Python que ademas pueda abrir la ventana 3D. Una maquina puede
# tener varios Python y que solo uno tenga MuJoCo: si elegimos el primero que
# aparece, el simulador arranca sin ventana y parece roto.
# Se prueban en orden y gana el PRIMERO que tenga MuJoCo. Los nombres con
# version explicita estan porque en algunas distros `python3` apunta a una
# version vieja y la buena esta al lado.
#
# En macOS MuJoCo exige `mjpython` para la ventana 3D (launch_passive).
CANDIDATOS="python3 python3.13 python3.12 python3.11 python3.10 python"
[ -x "$HOME/.venvs/unitree/bin/python" ] && CANDIDATOS="$HOME/.venvs/unitree/bin/python $CANDIDATOS"
[ -x "$HOME/Library/Python/3.9/bin/mjpython" ] && CANDIDATOS="$HOME/Library/Python/3.9/bin/mjpython $CANDIDATOS"
[ -x "$HOME/Library/Python/3.10/bin/mjpython" ] && CANDIDATOS="$HOME/Library/Python/3.10/bin/mjpython $CANDIDATOS"
[ -x "$HOME/Library/Python/3.11/bin/mjpython" ] && CANDIDATOS="$HOME/Library/Python/3.11/bin/mjpython $CANDIDATOS"
[ -x "$HOME/Library/Python/3.12/bin/mjpython" ] && CANDIDATOS="$HOME/Library/Python/3.12/bin/mjpython $CANDIDATOS"
command -v mjpython >/dev/null 2>&1 && CANDIDATOS="mjpython $CANDIDATOS"

PYTHON=""; PRIMERO=""
for PY in $CANDIDATOS; do
  command -v "$PY" >/dev/null 2>&1 || [ -x "$PY" ] || continue
  [ -z "$PRIMERO" ] && PRIMERO="$PY"
  # mjpython es el wrapper de MuJoCo: priorizarlo si existe
  case "$PY" in
    *mjpython*) PYTHON="$PY"; break ;;
  esac
  if "$PY" -c "import mujoco" >/dev/null 2>&1; then PYTHON="$PY"; break; fi
done
[ -z "$PYTHON" ] && PYTHON="$PRIMERO"

if [ -z "$PYTHON" ]; then
  echo
  echo "   ============================================================"
  echo "   NO ENCUENTRO PYTHON"
  echo "   ============================================================"
  echo
  echo "   En Ubuntu o Debian:"
  echo "       sudo apt install python3 python3-pip"
  echo
  echo "   En Fedora:"
  echo "       sudo dnf install python3 python3-pip"
  echo
  echo "   En macOS (con Homebrew):"
  echo "       brew install python"
  echo "   ============================================================"
  echo
  read -r -p "   Enter para cerrar..."; exit 1
fi

cd entorno || exit 1
"$PYTHON" -m sim --robot "$ROBOT" --materia tp07

echo
read -r -p "El simulador se cerro. Enter para salir..."
