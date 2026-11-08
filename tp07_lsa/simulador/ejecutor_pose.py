"""Ejecutor de poses en el simulador MuJoCo (brazo + dedos articulares).

Firma unificada con el ejecutor real:

    ejecutor_pose(pose) -> None

`pose` puede ser un dict unico o una lista de frames con claves:
  - brazo: dict joint_snake_case -> radianes
  - mano_derecha / mano_izquierda: dict dedo -> [0,1] (Inspire)
"""

from __future__ import annotations

import time

from poses.mujoco_dedos import frame_a_joints


def _normalizar_frames(pose: dict | list[dict]) -> list[dict]:
    if isinstance(pose, dict) and "brazo" in pose:
        return [pose]
    if isinstance(pose, dict) and any(
        k.startswith(("left_", "right_")) for k in pose
    ):
        return [{"brazo": pose, "mano_derecha": {}, "mano_izquierda": {}}]
    if isinstance(pose, list):
        return pose
    raise TypeError(
        "pose debe ser un dict {brazo, mano_*} o una lista de esos frames"
    )


def ejecutor_pose(pose: dict | list[dict], robot=None, duracion_step: float = 0.35) -> str:
    """Anima brazo y dedos en MuJoCo (modelo g1 con manos LSA)."""
    frames = _normalizar_frames(pose)
    secuencia = [frame_a_joints(f) for f in frames]

    if robot is not None and secuencia:
        robot.ejecutar_secuencia_senas(secuencia, duracion_step=duracion_step)
    else:
        for joints in secuencia:
            manos = {k: v for k, v in joints.items() if "_hand_" in k}
            print(f"      [SIM dedos] {manos}")
            time.sleep(min(duracion_step, 0.05))

    ultimo = frames[-1]
    return (
        "pose sim OK "
        f"(frames={len(frames)}; "
        f"mano_der={ultimo.get('mano_derecha')}; "
        f"mano_izq={ultimo.get('mano_izquierda')})"
    )


ejecutar_pose = ejecutor_pose
