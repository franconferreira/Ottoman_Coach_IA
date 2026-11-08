"""Poses de dedos Inspire para las 8 palabras del dataset LSA.

q: 1.0 = abierto, 0.0 = cerrado.
Puede ser un dict fijo {derecha, izquierda} o una lista de esos dicts
(uno por frame de brazo) para animar la mano durante la sena.
"""

from __future__ import annotations

from .mano import ABIERTA, CERRADA, mano

# Formas reutilizables
_PUNO = CERRADA
_ABIERTA = ABIERTA
_PALMA = ABIERTA  # palma abierta (misma q; el brazo define orientacion)
_INDICE = mano(pinky=0.0, ring=0.0, middle=0.0, index=1.0,
               thumb_bend=0.15, thumb_rotation=0.45)
_W = mano(pinky=0.0, ring=1.0, middle=1.0, index=1.0,
          thumb_bend=0.0, thumb_rotation=0.15)  # contraste max meñique vs 3 dedos
_GANCHO = mano(pinky=0.0, ring=0.0, middle=0.05, index=0.25,
               thumb_bend=0.35, thumb_rotation=0.55)
_GANCHO_ALT = mano(pinky=0.0, ring=0.0, middle=0.05, index=0.4,
                   thumb_bend=0.25, thumb_rotation=0.65)
# Chau: abierta con un toque de "aleteo" (meñique un poco mas cerrado)
_OLA = mano(pinky=0.85, ring=1.0, middle=1.0, index=1.0,
            thumb_bend=0.9, thumb_rotation=0.85)

MANOS_POR_PALABRA: dict[str, dict | list] = {
    # Saludo: mano bien abierta todo el gesto.
    "hola": {"derecha": _ABIERTA, "izquierda": _ABIERTA},

    # Gracias: mano plana abierta (entrega).
    "gracias": {"derecha": _PALMA, "izquierda": _ABIERTA},

    # Chau: abierta + aleteo leve en frames de vaiven.
    "chau": [
        {"derecha": _OLA, "izquierda": _ABIERTA},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
        {"derecha": _OLA, "izquierda": _ABIERTA},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
        {"derecha": _OLA, "izquierda": _ABIERTA},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
        {"derecha": _OLA, "izquierda": _ABIERTA},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
    ],

    # Si: punio cerrado firme.
    "si": {"derecha": _PUNO, "izquierda": _ABIERTA},

    # No: solo indice extendido (resto cerrado).
    "no": {"derecha": _INDICE, "izquierda": _ABIERTA},

    # Ayuda: punio derecho sobre palma izquierda.
    "ayuda": {"derecha": _PUNO, "izquierda": _PALMA},

    # Agua: forma W (indice+medio+anular).
    "agua": {"derecha": _W, "izquierda": _ABIERTA},

    # Amigo: ganchos de indice que alternan.
    "amigo": [
        {"derecha": _GANCHO, "izquierda": _GANCHO_ALT},
        {"derecha": _GANCHO_ALT, "izquierda": _GANCHO},
        {"derecha": _GANCHO, "izquierda": _GANCHO_ALT},
        {"derecha": _GANCHO_ALT, "izquierda": _GANCHO},
        {"derecha": _GANCHO, "izquierda": _GANCHO_ALT},
        {"derecha": _GANCHO_ALT, "izquierda": _GANCHO},
        {"derecha": _ABIERTA, "izquierda": _ABIERTA},
    ],
}


def manos_de(palabra: str, frame_idx: int = 0) -> dict | None:
    """Devuelve {derecha, izquierda} para el frame indicado."""
    dato = MANOS_POR_PALABRA.get(palabra)
    if dato is None:
        return None
    if isinstance(dato, list):
        if not dato:
            return None
        return dato[min(frame_idx, len(dato) - 1)]
    return dato
