# =====================================================================
#  Ejecutor. ESTE ARCHIVO TE LO DAMOS HECHO.
#
#  Es la ultima etapa del pipeline: recibe la intencion ya clasificada y
#  validada, y la manda al robot.
#
#  ACA ES DONDE SE CONVIERTE A VELOCIDAD Y TIEMPO.
#
#  Tu clasificador y tu extractor trabajan en las unidades en que habla
#  la gente: metros y grados. Esta bien, eso es lenguaje natural. Pero al
#  robot NUNCA le llega un metro ni un grado: le llegan velocidad y
#  tiempo, que es como piensa el SDK.
#
#      "avanza 2 metros"  a 0.2 m/s  ->  avanzar(0.2, 10 s)
#      "gira 90 grados"   a 0.5 rad/s ->  girar(0.5, 3.14 s)
#
#  Y como hay un tope de tiempo por orden, un movimiento largo se PARTE
#  en tramos. "avanza 2 metros" con tope de 5 s sale como dos ordenes de
#  5 s, no como una de 10. El robot recorre lo mismo; simplemente ninguna
#  orden individual supera el limite.
# =====================================================================

import math
import re
import sys
import time
import unicodedata
from pathlib import Path

from vocabulario_dataset import ALIAS_A_CANONICA

_ENTORNO = Path(__file__).resolve().parent.parent / "entorno"
if str(_ENTORNO) not in sys.path:
    sys.path.insert(0, str(_ENTORNO))

try:
    from sim.safety import ErrorDeSeguridad
except ImportError:
    class ErrorDeSeguridad(ValueError):
        pass

# Vocabulario LSA como keyframes de brazo/muneca (G1) + dedos.
# Afinado para maximizar contraste visual entre las 8 palabras del dataset.
DICCIONARIO_SENAS = {
    # HOLA: mano abierta a la sien, arco corto hacia adelante.
    "hola": [
        {"right_shoulder_pitch": -1.75, "right_shoulder_roll": -1.05,
         "right_shoulder_yaw": -0.55, "right_elbow": -1.35,
         "right_wrist_pitch": 0.55, "right_wrist_yaw": 0.35, "right_wrist_roll": 0.15},
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.85,
         "right_shoulder_yaw": -0.35, "right_elbow": -1.05,
         "right_wrist_pitch": 0.35, "right_wrist_yaw": 0.2, "right_wrist_roll": 0.05},
        {"right_shoulder_pitch": -1.2, "right_shoulder_roll": -0.45,
         "right_shoulder_yaw": 0.05, "right_elbow": -0.55,
         "right_wrist_pitch": 0.1, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.2,
         "right_shoulder_yaw": 0.15, "right_elbow": -0.25,
         "right_wrist_pitch": 0.0, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_shoulder_yaw": 0.0, "right_elbow": 0.0,
         "right_wrist_pitch": 0.0, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
    ],
    # GRACIAS: palma MUY cerca de la cara (exagerado para el sim) y entrega.
    "gracias": [
        # Preparacion: mano sube hacia la cara
        {"right_shoulder_pitch": -0.35, "right_shoulder_roll": -0.55,
         "right_shoulder_yaw": -1.0, "right_elbow": -1.65,
         "right_wrist_pitch": 1.2, "right_wrist_yaw": 0.45, "right_wrist_roll": 0.2},
        # Menton: codo muy flexionado, muneca hacia arriba (contacto visual)
        {"right_shoulder_pitch": -0.25, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.15, "right_elbow": -1.75,
         "right_wrist_pitch": 1.35, "right_wrist_yaw": 0.55, "right_wrist_roll": 0.25},
        # Hold en menton
        {"right_shoulder_pitch": -0.25, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.15, "right_elbow": -1.75,
         "right_wrist_pitch": 1.35, "right_wrist_yaw": 0.55, "right_wrist_roll": 0.25},
        # Entrega adelante-abajo
        {"right_shoulder_pitch": 0.05, "right_shoulder_roll": 0.05,
         "right_shoulder_yaw": -0.2, "right_elbow": -0.7,
         "right_wrist_pitch": 0.25, "right_wrist_yaw": 0.1, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.45, "right_shoulder_roll": 0.25,
         "right_shoulder_yaw": 0.25, "right_elbow": -0.2,
         "right_wrist_pitch": 0.0, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_shoulder_yaw": 0.0, "right_elbow": 0.0,
         "right_wrist_pitch": 0.0, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
    ],
    # CHAU: brazo ALTO + wrist_roll (distinto de "no").
    "chau": [
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.55,
         "right_elbow": -0.35, "right_wrist_roll": 1.1, "right_wrist_yaw": 0.15,
         "right_wrist_pitch": 0.2},
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.55,
         "right_elbow": -0.35, "right_wrist_roll": -1.1, "right_wrist_yaw": -0.15,
         "right_wrist_pitch": 0.2},
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.55,
         "right_elbow": -0.35, "right_wrist_roll": 1.1, "right_wrist_yaw": 0.15,
         "right_wrist_pitch": 0.2},
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.55,
         "right_elbow": -0.35, "right_wrist_roll": -1.1, "right_wrist_yaw": -0.15,
         "right_wrist_pitch": 0.2},
        {"right_shoulder_pitch": -1.55, "right_shoulder_roll": -0.55,
         "right_elbow": -0.35, "right_wrist_roll": 1.1, "right_wrist_yaw": 0.15,
         "right_wrist_pitch": 0.2},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_elbow": 0.0, "right_wrist_roll": 0.0, "right_wrist_yaw": 0.0,
         "right_wrist_pitch": 0.0},
    ],
    "por": [
        {"right_shoulder_pitch": -0.65, "right_elbow": -1.2, "right_wrist_yaw": -0.8},
        {"right_shoulder_pitch": -0.8, "right_elbow": -1.0, "right_wrist_yaw": 0.8},
        {"right_shoulder_pitch": -0.65, "right_elbow": -1.2, "right_wrist_yaw": -0.8},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0, "right_wrist_yaw": 0.0}
    ],
    "favor": [
        {"left_shoulder_pitch": -0.9, "left_elbow": -0.7, "left_wrist_pitch": 0.5,
         "right_shoulder_pitch": -0.9, "right_elbow": -0.7, "right_wrist_pitch": 0.5},
        {"left_shoulder_pitch": -1.25, "left_elbow": -0.25, "left_wrist_pitch": 0.5,
         "right_shoulder_pitch": -1.25, "right_elbow": -0.25, "right_wrist_pitch": 0.5},
        {"left_shoulder_pitch": -0.9, "left_elbow": -0.7, "left_wrist_pitch": 0.5,
         "right_shoulder_pitch": -0.9, "right_elbow": -0.7, "right_wrist_pitch": 0.5},
        {"left_shoulder_pitch": 0.0, "left_elbow": 0.0, "left_wrist_pitch": 0.0,
         "right_shoulder_pitch": 0.0, "right_elbow": 0.0, "right_wrist_pitch": 0.0}
    ],
    # AYUDA: palma izq + punio der; suben juntas.
    "ayuda": [
        {"left_shoulder_pitch": -0.45, "left_shoulder_roll": 0.55,
         "left_elbow": -1.35, "left_wrist_pitch": 0.85, "left_wrist_roll": 0.2,
         "right_shoulder_pitch": -0.55, "right_shoulder_roll": -0.55,
         "right_elbow": -1.5, "right_wrist_pitch": -0.35, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -0.75, "left_shoulder_roll": 0.4,
         "left_elbow": -1.15, "left_wrist_pitch": 0.7, "left_wrist_roll": 0.15,
         "right_shoulder_pitch": -0.85, "right_shoulder_roll": -0.4,
         "right_elbow": -1.3, "right_wrist_pitch": -0.25, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -1.15, "left_shoulder_roll": 0.25,
         "left_elbow": -0.85, "left_wrist_pitch": 0.55, "left_wrist_roll": 0.1,
         "right_shoulder_pitch": -1.25, "right_shoulder_roll": -0.25,
         "right_elbow": -1.0, "right_wrist_pitch": -0.15, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -1.45, "left_shoulder_roll": 0.15,
         "left_elbow": -0.55, "left_wrist_pitch": 0.4, "left_wrist_roll": 0.05,
         "right_shoulder_pitch": -1.5, "right_shoulder_roll": -0.15,
         "right_elbow": -0.7, "right_wrist_pitch": -0.05, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -1.45, "left_shoulder_roll": 0.15,
         "left_elbow": -0.55, "left_wrist_pitch": 0.4,
         "right_shoulder_pitch": -1.5, "right_shoulder_roll": -0.15,
         "right_elbow": -0.7, "right_wrist_pitch": -0.05},
        {"left_shoulder_pitch": 0.0, "left_shoulder_roll": 0.0,
         "left_elbow": 0.0, "left_wrist_pitch": 0.0, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_elbow": 0.0, "right_wrist_pitch": 0.0, "right_wrist_roll": 0.0},
    ],
    # AMIGO: manos al centro, ganchos, alternan altura.
    "amigo": [
        {"left_shoulder_pitch": -0.85, "left_shoulder_roll": 0.65,
         "left_elbow": -1.25, "left_wrist_yaw": 0.75, "left_wrist_pitch": 0.25,
         "right_shoulder_pitch": -0.65, "right_shoulder_roll": -0.65,
         "right_elbow": -1.25, "right_wrist_yaw": -0.75, "right_wrist_pitch": -0.15},
        {"left_shoulder_pitch": -0.65, "left_shoulder_roll": 0.55,
         "left_elbow": -1.15, "left_wrist_yaw": 0.55, "left_wrist_pitch": -0.15,
         "right_shoulder_pitch": -0.85, "right_shoulder_roll": -0.55,
         "right_elbow": -1.15, "right_wrist_yaw": -0.55, "right_wrist_pitch": 0.25},
        {"left_shoulder_pitch": -0.85, "left_shoulder_roll": 0.65,
         "left_elbow": -1.25, "left_wrist_yaw": 0.75, "left_wrist_pitch": 0.25,
         "right_shoulder_pitch": -0.65, "right_shoulder_roll": -0.65,
         "right_elbow": -1.25, "right_wrist_yaw": -0.75, "right_wrist_pitch": -0.15},
        {"left_shoulder_pitch": -0.65, "left_shoulder_roll": 0.55,
         "left_elbow": -1.15, "left_wrist_yaw": 0.55, "left_wrist_pitch": -0.15,
         "right_shoulder_pitch": -0.85, "right_shoulder_roll": -0.55,
         "right_elbow": -1.15, "right_wrist_yaw": -0.55, "right_wrist_pitch": 0.25},
        {"left_shoulder_pitch": -0.75, "left_shoulder_roll": 0.6,
         "left_elbow": -1.2, "left_wrist_yaw": 0.65,
         "right_shoulder_pitch": -0.75, "right_shoulder_roll": -0.6,
         "right_elbow": -1.2, "right_wrist_yaw": -0.65},
        {"left_shoulder_pitch": 0.0, "left_shoulder_roll": 0.0,
         "left_elbow": 0.0, "left_wrist_yaw": 0.0, "left_wrist_pitch": 0.0,
         "right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_elbow": 0.0, "right_wrist_yaw": 0.0, "right_wrist_pitch": 0.0},
    ],
    "buenos": [
        {"right_shoulder_pitch": -1.5, "right_elbow": -0.8, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.3, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "dias": [
        {"right_shoulder_pitch": -1.3, "right_elbow": -0.6, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.75, "right_elbow": -0.2, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    # SI: punio, asiente fuerte.
    "si": [
        {"right_shoulder_pitch": -0.95, "right_shoulder_roll": -0.4,
         "right_elbow": -1.5, "right_wrist_pitch": 0.75, "right_wrist_roll": 0.1},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.3,
         "right_elbow": -1.0, "right_wrist_pitch": -0.55, "right_wrist_roll": 0.1},
        {"right_shoulder_pitch": -0.95, "right_shoulder_roll": -0.4,
         "right_elbow": -1.5, "right_wrist_pitch": 0.75, "right_wrist_roll": 0.1},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.3,
         "right_elbow": -1.0, "right_wrist_pitch": -0.55, "right_wrist_roll": 0.1},
        {"right_shoulder_pitch": -0.95, "right_shoulder_roll": -0.4,
         "right_elbow": -1.5, "right_wrist_pitch": 0.75, "right_wrist_roll": 0.1},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_elbow": 0.0, "right_wrist_pitch": 0.0, "right_wrist_roll": 0.0},
    ],
    # NO: mas bajo que chau; solo wrist_yaw + indice.
    "no": [
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.25,
         "right_elbow": -1.25, "right_wrist_yaw": 0.95, "right_wrist_pitch": 0.15,
         "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.25,
         "right_elbow": -1.25, "right_wrist_yaw": -0.95, "right_wrist_pitch": 0.15,
         "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.25,
         "right_elbow": -1.25, "right_wrist_yaw": 0.95, "right_wrist_pitch": 0.15,
         "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.25,
         "right_elbow": -1.25, "right_wrist_yaw": -0.95, "right_wrist_pitch": 0.15,
         "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_shoulder_roll": -0.25,
         "right_elbow": -1.25, "right_wrist_yaw": 0.95, "right_wrist_pitch": 0.15,
         "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_elbow": 0.0, "right_wrist_yaw": 0.0, "right_wrist_pitch": 0.0,
         "right_wrist_roll": 0.0},
    ],
    "perdon": [
        {"right_shoulder_pitch": -1.2, "right_elbow": -0.7, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_elbow": -0.3, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -1.2, "right_elbow": -0.7, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "robot": [
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.5, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.5, "right_elbow": 0.0, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "manana": [
        {"right_shoulder_pitch": -1.3, "right_elbow": -0.6, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.7, "right_elbow": -0.2, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "noche": [
        {"left_shoulder_pitch": -0.25, "left_elbow": -0.9, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": -0.25, "right_elbow": -0.9, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -0.55, "left_elbow": -1.2, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": -0.55, "right_elbow": -1.2, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -0.8, "left_elbow": -1.45, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": -0.8, "right_elbow": -1.45, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": -0.55, "left_elbow": -1.2, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": -0.55, "right_elbow": -1.2, "right_wrist_roll": 0.0},
        {"left_shoulder_pitch": 0.0, "left_elbow": 0.0, "left_wrist_roll": 0.0,
         "right_shoulder_pitch": 0.0, "right_elbow": 0.0, "right_wrist_roll": 0.0}
    ],
    # AGUA: W exagerada + toques al menton bien visibles.
    "agua": [
        # Acerca W a la cara
        {"right_shoulder_pitch": -0.3, "right_shoulder_roll": -0.45,
         "right_shoulder_yaw": -0.95, "right_elbow": -1.7,
         "right_wrist_pitch": 1.15, "right_wrist_yaw": 0.55, "right_wrist_roll": 0.2},
        # Toque 1 (hold)
        {"right_shoulder_pitch": -0.2, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.1, "right_elbow": -1.8,
         "right_wrist_pitch": 1.3, "right_wrist_yaw": 0.65, "right_wrist_roll": 0.25},
        {"right_shoulder_pitch": -0.2, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.1, "right_elbow": -1.8,
         "right_wrist_pitch": 1.3, "right_wrist_yaw": 0.65, "right_wrist_roll": 0.25},
        # Baja un poco
        {"right_shoulder_pitch": -0.4, "right_shoulder_roll": -0.35,
         "right_shoulder_yaw": -0.7, "right_elbow": -1.45,
         "right_wrist_pitch": 0.55, "right_wrist_yaw": 0.3, "right_wrist_roll": 0.1},
        # Toque 2
        {"right_shoulder_pitch": -0.2, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.1, "right_elbow": -1.8,
         "right_wrist_pitch": 1.3, "right_wrist_yaw": 0.65, "right_wrist_roll": 0.25},
        {"right_shoulder_pitch": -0.2, "right_shoulder_roll": -0.5,
         "right_shoulder_yaw": -1.1, "right_elbow": -1.8,
         "right_wrist_pitch": 1.3, "right_wrist_yaw": 0.65, "right_wrist_roll": 0.25},
        {"right_shoulder_pitch": 0.0, "right_shoulder_roll": 0.0,
         "right_shoulder_yaw": 0.0, "right_elbow": 0.0,
         "right_wrist_pitch": 0.0, "right_wrist_yaw": 0.0, "right_wrist_roll": 0.0},
    ],
    "comer": [
        {"right_shoulder_pitch": -0.6, "right_elbow": -1.1, "right_wrist_pitch": 0.8},
        {"right_shoulder_pitch": -0.9, "right_elbow": -0.7, "right_wrist_pitch": 0.4},
        {"right_shoulder_pitch": -0.6, "right_elbow": -1.1, "right_wrist_pitch": 0.8},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "casa": [
        {"left_shoulder_pitch": -0.8, "left_elbow": -0.4, "right_shoulder_pitch": -0.8, "right_elbow": -0.4},
        {"left_shoulder_pitch": -1.1, "left_elbow": -0.1, "right_shoulder_pitch": -1.1, "right_elbow": -0.1},
        {"left_shoulder_pitch": 0.0, "left_elbow": 0.0, "right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "escuela": [
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.6, "right_wrist_roll": 0.7},
        {"right_shoulder_pitch": -0.5, "right_elbow": -0.2, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.6, "right_wrist_roll": -0.7},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "familia": [
        {"left_shoulder_pitch": -0.7, "left_elbow": -0.7, "right_shoulder_pitch": -0.7, "right_elbow": -0.7},
        {"left_shoulder_pitch": -1.0, "left_elbow": -0.3, "right_shoulder_pitch": -1.0, "right_elbow": -0.3},
        {"left_shoulder_pitch": -0.7, "left_elbow": -0.7, "right_shoulder_pitch": -0.7, "right_elbow": -0.7},
        {"left_shoulder_pitch": 0.0, "left_elbow": 0.0, "right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "venir": [
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.5, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.4, "right_elbow": -0.1, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -1.0, "right_elbow": -0.5, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "donde": [
        {"right_shoulder_pitch": -1.4, "right_elbow": -0.4, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -1.4, "right_elbow": -0.4, "right_wrist_roll": 0.8},
        {"right_shoulder_pitch": -1.4, "right_elbow": -0.4, "right_wrist_roll": -0.8},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ],
    "nombre": [
        {"right_shoulder_pitch": -0.8, "right_elbow": -0.9, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.5, "right_elbow": -0.5, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": -0.8, "right_elbow": -0.9, "right_wrist_roll": 0.0},
        {"right_shoulder_pitch": 0.0, "right_elbow": 0.0}
    ]
}



def _agregar_frames_intermedios(secuencia):
    """Suaviza cada seña y garantiza mas de cuatro frames por palabra."""
    frames = []
    for actual, siguiente in zip(secuencia, secuencia[1:]):
        frames.append(actual)
        claves = set(actual) | set(siguiente)
        frames.append({
            clave: (actual.get(clave, 0.0) + siguiente.get(clave, 0.0)) / 2
            for clave in claves
        })
    frames.append(secuencia[-1])
    return frames


# Solo para senas viejas del diccionario ampliado. Las 8 del dataset
# (hola/gracias/chau/si/no/ayuda/agua/amigo) NO se pisan: el keyframe manda.
_PERFILES_VISUALES = {
    "por": {"right_shoulder_pitch": -0.65, "right_wrist_yaw": -0.8},
    "favor": {"left_shoulder_pitch": -0.9, "right_shoulder_pitch": -0.9},
    "buenos": {"left_shoulder_pitch": -1.3, "right_shoulder_pitch": -1.3},
    "dias": {"right_shoulder_pitch": 0.6, "right_elbow": -1.2},
    "perdon": {"right_shoulder_pitch": -0.2, "right_elbow": -1.4},
    "robot": {"right_shoulder_pitch": 0.8, "right_elbow": -0.2},
    "manana": {"right_shoulder_pitch": -0.8, "right_elbow": 0.5},
    "noche": {"left_shoulder_pitch": -0.8, "right_shoulder_pitch": -0.8},
    "comer": {"right_shoulder_pitch": -0.6, "right_elbow": -1.1, "right_wrist_pitch": 0.8},
    "casa": {"left_shoulder_pitch": -1.4, "right_shoulder_pitch": -1.4},
    "escuela": {"right_shoulder_pitch": 0.4, "right_elbow": -0.9},
    "familia": {"left_shoulder_pitch": -0.7, "right_shoulder_pitch": -0.7},
    "venir": {"right_shoulder_pitch": -0.3, "right_elbow": -1.3},
    "donde": {"right_shoulder_pitch": 0.7, "right_elbow": -0.8},
    "nombre": {"right_shoulder_pitch": -0.3, "right_elbow": -1.5},
}


def _aplicar_perfil_visual(palabra, secuencia):
    perfil = _PERFILES_VISUALES.get(palabra) or {}
    if not perfil:
        return secuencia
    return [
        {**frame, **perfil} if indice == 0 else frame
        for indice, frame in enumerate(secuencia)
    ]


DICCIONARIO_SENAS = {
    palabra: _aplicar_perfil_visual(palabra, _agregar_frames_intermedios(secuencia))
    for palabra, secuencia in DICCIONARIO_SENAS.items()
}


def _joints_dedos(palabra: str, frame_idx: int = 0) -> dict:
    """Suma joints de mano LSA si esta el paquete tp07_lsa (no rompe si falta)."""
    try:
        lsa = Path(__file__).resolve().parents[1] / "tp07_lsa"
        if str(lsa) not in sys.path:
            sys.path.insert(0, str(lsa))
        from poses.manos_dataset import manos_de
        from poses.mujoco_dedos import mano_a_joints

        manos = manos_de(palabra, frame_idx)
        if not manos:
            return {}
        joints = {}
        joints.update(mano_a_joints("right", manos.get("derecha")))
        joints.update(mano_a_joints("left", manos.get("izquierda")))
        return joints
    except Exception:
        return {}


# Enriquece las 8 palabras del dataset con angulos de dedos MuJoCo (por frame).
DICCIONARIO_SENAS = {
    palabra: [
        {**frame, **_joints_dedos(palabra, i)} for i, frame in enumerate(secuencia)
    ]
    for palabra, secuencia in DICCIONARIO_SENAS.items()
}


class Ejecutor:
    def __init__(self, robot, mostrar=True):
        self.robot = robot
        self.mostrar = mostrar
        self.perfil = robot.perfil

    def ejecutar(self, tipo, parametros):
        parametros = parametros or {}
        try:
            if tipo == "MOVER":
                return self._mover(parametros)
            if tipo == "GIRAR":
                return self._girar(parametros)
            if tipo == "DETENERSE":
                self.robot.detenerse()
                return "detenido"
            if tipo == "SALUDO":
                return self._ejecutar_senas({"texto_senas": "hola"})
            if tipo == "SENAS":
                return self._ejecutar_senas(parametros)
            if tipo == "CONSULTAR_ESTADO":
                e = self.robot.verificar_estado()
                return f"estado: {e}"
        except ErrorDeSeguridad as exc:
            return f"RECHAZADO POR EL ROBOT: {exc}"
        return f"no se como ejecutar {tipo}"

    def _ejecutar_senas(self, p):
        texto = str(p.get("texto_senas", "")).casefold()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        palabras = re.findall(r"[a-z]+", texto)
        secuencia_total = []
        palabras_no_registradas = []

        for palabra in palabras:
            palabra = ALIAS_A_CANONICA.get(palabra, palabra)
            if palabra in DICCIONARIO_SENAS:
                secuencia_total.extend(DICCIONARIO_SENAS[palabra])
            elif palabra not in {"y", "e"} and palabra not in palabras_no_registradas:
                palabras_no_registradas.append(palabra)

        if not secuencia_total:
            self._log(f"No se encontraron señas registradas para: '{texto}'")
            return f"sin señas registradas para '{texto}'"

        self._log(f"Ejecutando {len(secuencia_total)} keyframes de señas para: '{texto}'")
        if any(p in texto for p in ("gracias", "agua")):
            self._log(
                "Tip: acerca la camara a la cara/mano derecha "
                "(rueda del mouse). Menton/W no tienen contacto fisico real."
            )
        self.robot.ejecutar_secuencia_senas(secuencia_total, duracion_step=0.55)
        mensaje = f"señas ejecutadas para '{texto}'"
        if palabras_no_registradas:
            mensaje += "; sin seña cargada para: " + ", ".join(palabras_no_registradas)
        return mensaje

    def _mover(self, p):
        distancia = float(p.get("distancia_m", 0.5))
        velocidad = float(p.get("velocidad_ms", self.perfil.velocidad_max))
        velocidad = min(abs(velocidad), self.perfil.velocidad_max)
        if velocidad <= 0:
            return "velocidad cero"

        signo = -1.0 if p.get("direccion") == "atras" else 1.0
        tiempo_total = abs(distancia) / velocidad
        self.robot.avanzar(velocidad=signo * velocidad, tiempo=tiempo_total)
        return f"avanzo {distancia:g} m"

    def _girar(self, p):
        grados = float(p.get("angulo_deg", 90))
        velocidad = float(p.get("velocidad_giro", self.perfil.velocidad_angular_max))
        velocidad = min(abs(velocidad), self.perfil.velocidad_angular_max)
        if velocidad <= 0:
            return "velocidad de giro cero"

        signo = -1.0 if p.get("direccion") == "derecha" else 1.0
        radianes = math.radians(abs(grados))
        tiempo_total = radianes / velocidad
        self.robot.girar(velocidad=signo * velocidad, tiempo=tiempo_total)
        return f"giro {grados:g} grados"

    def _log(self, texto):
        if self.mostrar:
            print(f"      [EJECUTOR] {texto}")