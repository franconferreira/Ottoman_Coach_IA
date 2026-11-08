"""Diccionario palabra -> secuencia de poses (brazo + manos).

Reusa los keyframes de brazo/muneca de mi_desarrollo/ejecutor.py y les
suma poses de mano Inspire (5 dedos + rotacion del pulgar).
"""

from __future__ import annotations

import sys
from pathlib import Path

from poses.manos_dataset import manos_de
from poses.mano import MEDIA

_MI_DESARROLLO = Path(__file__).resolve().parents[2] / "mi_desarrollo"
if str(_MI_DESARROLLO) not in sys.path:
    sys.path.insert(0, str(_MI_DESARROLLO))

from ejecutor import DICCIONARIO_SENAS as _BRAZO_SENAS  # noqa: E402


def _frame(brazo: dict, derecha: dict, izquierda: dict) -> dict:
    return {
        "brazo": dict(brazo),
        "mano_derecha": dict(derecha),
        "mano_izquierda": dict(izquierda),
    }


def construir_secuencia(palabra: str) -> list[dict]:
    palabra = palabra.lower().strip()
    if palabra not in _BRAZO_SENAS:
        raise KeyError(f"Sin keyframes de brazo para '{palabra}'")
    # Los frames de brazo ya traen joints de dedo embebidos desde ejecutor;
    # aca reconstruimos el formato unificado para tp07_lsa.
    out = []
    for i, brazo in enumerate(_BRAZO_SENAS[palabra]):
        # Filtrar joints de mano del dict de brazo enriquecido
        solo_brazo = {k: v for k, v in brazo.items() if "_hand_" not in k}
        manos = manos_de(palabra, i) or {"derecha": MEDIA, "izquierda": MEDIA}
        out.append(_frame(solo_brazo, manos["derecha"], manos["izquierda"]))
    return out


def obtener_secuencia(palabra: str) -> list[dict]:
    return construir_secuencia(palabra)


VOCABULARIO_LSA: tuple[str, ...] = (
    "hola", "gracias", "chau", "si", "no", "ayuda", "agua", "amigo",
)

DICCIONARIO_POSES: dict[str, list[dict]] = {
    palabra: construir_secuencia(palabra) for palabra in VOCABULARIO_LSA
}
