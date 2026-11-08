"""Poses de mano Inspire (0.0=cerrado, 1.0=abierto).

Orden oficial RH56 (Unitree dfx_inspire_service):
  pinky, ring, middle, index, thumb_bend, thumb_rotation
"""

from __future__ import annotations

# Nombres canonicos usados en senas/ y en el mapeo al SDK.
DEDOS_MANO: tuple[str, ...] = (
    "pinky",
    "ring",
    "middle",
    "index",
    "thumb_bend",
    "thumb_rotation",
)

ABIERTA: dict[str, float] = {d: 1.0 for d in DEDOS_MANO}
CERRADA: dict[str, float] = {d: 0.0 for d in DEDOS_MANO}
MEDIA: dict[str, float] = {d: 0.5 for d in DEDOS_MANO}


def mano(**kwargs: float) -> dict[str, float]:
    """Construye una pose de mano partiendo de abierta y aplicando overrides."""
    pose = dict(ABIERTA)
    for clave, valor in kwargs.items():
        if clave not in pose:
            raise KeyError(f"Dedo desconocido '{clave}'. Validos: {DEDOS_MANO}")
        pose[clave] = float(max(0.0, min(1.0, valor)))
    return pose


def a_vector(pose_mano: dict[str, float] | None) -> list[float]:
    """Convierte dict de dedos a lista [pinky..thumb_rotation] de largo 6."""
    base = dict(ABIERTA)
    if pose_mano:
        base.update(pose_mano)
    return [float(base[d]) for d in DEDOS_MANO]
