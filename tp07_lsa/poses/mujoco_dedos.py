"""Convierte poses Inspire (0=cerrado..1=abierto) a joints MuJoCo (radianes).

Joints del modelo g1_29dof.xml (manos LSA en capsulas):
  {left|right}_hand_{pinky|ring|middle|index}_joint
  {left|right}_hand_thumb_bend_joint
  {left|right}_hand_thumb_rotation_joint

q Inspire 1.0 = abierto = angulo 0
q Inspire 0.0 = cerrado = angulo CURL_MAX
"""

from __future__ import annotations

from .mano import DEDOS_MANO

CURL_MAX: dict[str, float] = {
    "pinky": 1.35,
    "ring": 1.35,
    "middle": 1.4,
    "index": 1.35,
    "thumb_bend": 1.15,
    "thumb_rotation": 0.9,
}

# dedo Inspire -> sufijo del joint MuJoCo
_JOINT_SUFIJO: dict[str, str] = {
    "pinky": "pinky",
    "ring": "ring",
    "middle": "middle",
    "index": "index",
    "thumb_bend": "thumb_bend",
    "thumb_rotation": "thumb_rotation",
}


def inspire_a_angulo(dedo: str, q: float) -> float:
    q = max(0.0, min(1.0, float(q)))
    return (1.0 - q) * CURL_MAX.get(dedo, 1.2)


def mano_a_joints(lado: str, pose_mano: dict[str, float] | None) -> dict[str, float]:
    """lado: 'right' o 'left'. Devuelve dict nombre_joint_sin_suffix -> rad."""
    if not pose_mano:
        return {}
    prefijo = "right_hand" if lado.startswith("r") else "left_hand"
    out: dict[str, float] = {}
    for dedo in DEDOS_MANO:
        if dedo not in pose_mano:
            continue
        sufijo = _JOINT_SUFIJO[dedo]
        out[f"{prefijo}_{sufijo}"] = inspire_a_angulo(dedo, pose_mano[dedo])
    return out


def frame_a_joints(frame: dict) -> dict[str, float]:
    """Une brazo + manos de un frame unificado en un solo dict de joints."""
    joints = dict(frame.get("brazo") or {})
    joints.update(mano_a_joints("right", frame.get("mano_derecha")))
    joints.update(mano_a_joints("left", frame.get("mano_izquierda")))
    return joints
