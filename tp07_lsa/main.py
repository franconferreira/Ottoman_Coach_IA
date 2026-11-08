"""Entrada LSA: palabra -> pose -> simulador MuJoCo o G1 real (Inspire).

Uso:
  python3 main.py --modo simulacion --demo
  python3 main.py --modo real --interfaz eth0 --palabra hola
  python3 main.py --modo simulacion          # bucle interactivo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Asegura imports locales (poses/, senas/, ...)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_MI = _ROOT.parent / "mi_desarrollo"
if str(_MI) not in sys.path:
    sys.path.insert(0, str(_MI))


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="TP07 LSA — Ottoman G1 + Inspire")
    p.add_argument(
        "--modo",
        choices=("simulacion", "real"),
        default="simulacion",
        help="Donde ejecutar las poses (default: simulacion)",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Recorre las 8 palabras del vocabulario",
    )
    p.add_argument(
        "--palabra",
        type=str,
        default=None,
        help="Ejecuta una sola palabra y sale",
    )
    p.add_argument(
        "--interfaz",
        type=str,
        default=None,
        help="Interfaz de red DDS (solo modo real). Ej: eth0, enp0s31f6",
    )
    p.add_argument(
        "--domain",
        type=int,
        default=0,
        help="Domain DDS (robot real UADE = 0)",
    )
    p.add_argument(
        "--sin-robot",
        action="store_true",
        help="Modo simulacion sin conectar al MuJoCo (solo imprime manos)",
    )
    return p.parse_args(argv)


def _elegir_ejecutor(modo: str, interfaz: str | None, domain: int):
    if modo == "simulacion":
        from simulador.ejecutor_pose import ejecutor_pose

        return ejecutor_pose, {}
    from robot_real.ejecutor_pose_real import (
        DDS_INTERFAZ,
        ErrorConexionRobot,
        ejecutor_pose,
    )

    kwargs = {
        "interfaz": interfaz or DDS_INTERFAZ,
        "domain": domain,
    }
    return ejecutor_pose, kwargs


def _conectar_sim(sin_robot: bool):
    if sin_robot:
        return None
    try:
        from robot import Robot

        r = Robot()
        r.conectar()
        return r
    except Exception as exc:  # noqa: BLE001
        print(f"  [AVISO] No conecte al simulador MuJoCo: {exc}")
        print("  Sigo solo con log de manos. Abri el sim con mjpython si queres brazos.")
        return None


def _correr_palabra(palabra: str, ejecutar, kwargs, robot):
    from senas.diccionario import DICCIONARIO_POSES

    if palabra not in DICCIONARIO_POSES:
        print(f"  Palabra '{palabra}' no esta en el dataset.")
        print(f"  Validas: {', '.join(DICCIONARIO_POSES)}")
        return False
    secuencia = DICCIONARIO_POSES[palabra]
    print(f"  -> {palabra} ({len(secuencia)} frames)")
    try:
        msg = ejecutar(secuencia, robot=robot, **kwargs)
    except Exception as exc:
        # ErrorConexionRobot u otros
        print(f"  ERROR: {exc}")
        return False
    print(f"    {msg}")
    return True


def main(argv=None) -> int:
    args = _parse_args(argv)
    from senas.diccionario import VOCABULARIO_LSA

    print("=" * 60)
    print("  TP07 LSA — Ottoman (G1) + mano Inspire")
    print(f"  Modo: {args.modo}")
    print(f"  Vocabulario: {', '.join(VOCABULARIO_LSA)}")
    print("=" * 60)

    try:
        ejecutar, kwargs = _elegir_ejecutor(args.modo, args.interfaz, args.domain)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR al cargar ejecutor: {exc}")
        return 1

    robot = None
    if args.modo == "simulacion":
        robot = _conectar_sim(args.sin_robot)

    try:
        if args.palabra:
            ok = _correr_palabra(args.palabra.lower().strip(), ejecutar, kwargs, robot)
            return 0 if ok else 2

        if args.demo:
            for palabra in VOCABULARIO_LSA:
                if not _correr_palabra(palabra, ejecutar, kwargs, robot):
                    if args.modo == "real":
                        return 3
            print("\n  Demo terminada.")
            return 0

        print("\n  Escribi una palabra del vocabulario. Enter vacio sale.")
        while True:
            try:
                texto = input("\n  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not texto:
                break
            if texto.lower() in {"salir", "exit", "quit"}:
                break
            _correr_palabra(texto.lower(), ejecutar, kwargs, robot)
        return 0
    finally:
        if robot is not None:
            try:
                robot.detenerse()
                robot.desconectar()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    raise SystemExit(main())
