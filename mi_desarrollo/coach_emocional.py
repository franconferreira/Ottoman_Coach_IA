"""Motor de Coaching Emocional Multimodal: Léxico + Prosodia de Voz + Postura G1.

Fundamentación científica implementada:
  - Modelo Circumplejo del Afecto (Russell, 1980): Mapeo continuo Valencia-Arousal.
  - Co-regulación Interpersonal y Pacing & Leading (Computación Afectiva, Picard):
    El robot valida verbalmente el estado del usuario pero modula su cuerpo y su voz
    hacia una zona de regulación óptima (desaceleración en ansiedad, calidez en tristeza,
    desescalada espacial y vocal en ira, estructuración en duda).
  - Proxémica en HRI (Hall, 1966): Ajuste ético y seguro de distancia interpersonal.
  - Principios Human-Centered AI (human-ai.org): Transparencia, agencia del usuario y
    derivación humana obligatoria ante crisis.
"""

from __future__ import annotations

import asyncio
from collections import deque
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from percepcion_multimodal import AnalizadorLexicoAfectivo, EstadoAfectivoUsuario


def _cargar_dotenv_local() -> None:
    """Carga variables de entorno desde .env si existe en el proyecto."""
    for ruta in (
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ):
        if ruta.exists():
            try:
                for linea in ruta.read_text(encoding="utf-8").splitlines():
                    linea = linea.strip()
                    if not linea or linea.startswith("#") or "=" not in linea:
                        continue
                    k, v = linea.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass


_cargar_dotenv_local()


# =====================================================================
#  ESTRUCTURAS DE SALIDA DEL MOTOR DE COACHING
# =====================================================================

@dataclass
class PerfilProsodico:
    """Parámetros acústicos, espectrales y temporales que adopta la voz del robot."""
    velocidad_wpm: int          # Palabras por minuto objetivo (ej. 122 vs 172)
    velocidad_pct: int          # Delta porcentual respecto a voz neutra (-25% a +15%)
    volumen_db: float           # Ajuste relativo en decibeles (-6.0 dB a +4.0 dB)
    tono_hz: int                # Desplazamiento de tono fundamental (-18 Hz a +16 Hz)
    pausa_inicial_s: float      # Silencio deliberado antes de empezar a hablar
    pausa_entre_frases_s: float # Temporalización respiratoria entre oraciones
    estilo_lexico: str          # Registro lingüístico seleccionado
    timbre: str = "neutro_templado"  # Filtro espectral DSP: calido_suave | brillante_claro | firme_templado | neutro_templado


@dataclass
class PlanRegulacionEmocional:
    """Plan integral multimodal que ejecutará Ottoman (Voz + Cuerpo + Cara)."""
    emocion_usuario: str
    estrategia_hri: str
    texto_respuesta: str
    prosodia: PerfilProsodico
    secuencia_postural: list[dict[str, float]]
    duracion_step_postura: float
    proxemica_distancia_m: float    # + acerca suavemente, - da espacio atrás, 0 quieto
    proxemica_velocidad_ms: float   # siempre <= 0.15 m/s por seguridad afectiva
    preset_rostro: str
    origen_respuesta: str = "CBR_LOCAL"


# =====================================================================
#  1. COREÓGRAFO POSTURAL Y PROXÉMICO PARA UNITREE G1 (29 DoF + MANOS)
# =====================================================================

def _mano_relajada_organica(lado: str) -> dict[str, float]:
    """Cascada anatómica humana de reposo en las manos (Inspire RH56)."""
    return {
        f"{lado}_hand_index": 0.22,
        f"{lado}_hand_middle": 0.35,
        f"{lado}_hand_ring": 0.48,
        f"{lado}_hand_pinky": 0.58,
        f"{lado}_hand_thumb_rotation": 0.20,
        f"{lado}_hand_thumb_bend": 0.18,
    }


def _mano_empatica_pecho(lado: str) -> dict[str, float]:
    """Mano que se acopla con calidez y curvatura orgánica sobre el tórax."""
    return {
        f"{lado}_hand_index": 0.32,
        f"{lado}_hand_middle": 0.46,
        f"{lado}_hand_ring": 0.60,
        f"{lado}_hand_pinky": 0.72,
        f"{lado}_hand_thumb_rotation": 0.35,
        f"{lado}_hand_thumb_bend": 0.25,
    }


def _mano_pacificador(lado: str) -> dict[str, float]:
    """Dedos extendidos juntos con pulgar abierto: barrera universal de sosiego."""
    return {
        f"{lado}_hand_index": 0.05,
        f"{lado}_hand_middle": 0.05,
        f"{lado}_hand_ring": 0.05,
        f"{lado}_hand_pinky": 0.05,
        f"{lado}_hand_thumb_rotation": 0.85,
        f"{lado}_hand_thumb_bend": 0.05,
    }


def _mano_puno_victoria(lado: str) -> dict[str, float]:
    """Puño cerrado con firmeza festiva y pulgar envolvente."""
    return {
        f"{lado}_hand_index": 1.28,
        f"{lado}_hand_middle": 1.28,
        f"{lado}_hand_ring": 1.28,
        f"{lado}_hand_pinky": 1.28,
        f"{lado}_hand_thumb_rotation": 0.80,
        f"{lado}_hand_thumb_bend": 1.05,
    }


def _mano_senalamiento(lado: str) -> dict[str, float]:
    """Índice apuntando con complicidad hacia el usuario, restantes recogidos."""
    return {
        f"{lado}_hand_index": 0.05,
        f"{lado}_hand_middle": 1.22,
        f"{lado}_hand_ring": 1.22,
        f"{lado}_hand_pinky": 1.22,
        f"{lado}_hand_thumb_rotation": 0.65,
        f"{lado}_hand_thumb_bend": 0.90,
    }


def _mano_declamatoria(lado: str) -> dict[str, float]:
    """Apertura amplia en abanico con gracia escénica y dedos curvos."""
    return {
        f"{lado}_hand_index": 0.10,
        f"{lado}_hand_middle": 0.16,
        f"{lado}_hand_ring": 0.24,
        f"{lado}_hand_pinky": 0.32,
        f"{lado}_hand_thumb_rotation": 0.45,
        f"{lado}_hand_thumb_bend": 0.12,
    }


def _mano_pulgar_arriba(lado: str) -> dict[str, float]:
    """Pulgar extendido arriba con puño cerrado (triunfo y confirmación)."""
    return {
        f"{lado}_hand_index": 1.25,
        f"{lado}_hand_middle": 1.25,
        f"{lado}_hand_ring": 1.25,
        f"{lado}_hand_pinky": 1.25,
        f"{lado}_hand_thumb_rotation": 0.70,
        f"{lado}_hand_thumb_bend": 0.0,
    }


def _manos_abiertas() -> dict[str, float]:
    """Compatibilidad: manos relajadas orgánicas en ambos lados."""
    d = {}
    d.update(_mano_relajada_organica("left"))
    d.update(_mano_relajada_organica("right"))
    return d


def _pulgar_arriba_derecho() -> dict[str, float]:
    """Compatibilidad: mano derecha con pulgar arriba y mano izquierda relajada."""
    d = _mano_relajada_organica("left")
    d.update(_mano_pulgar_arriba("right"))
    return d


def _pose_neutra_suave() -> dict[str, float]:
    """Postura canónica neutra viva con brazos cayendo relajados a los muslos (palmas hacia el cuerpo)."""
    pose = {
        # Pelvis y columna
        "waist_yaw": 0.0,
        "waist_roll": 0.0,
        "waist_pitch": 0.0,
        
        # Brazos descansando naturalmente a los costados con palmas hacia el cuerpo
        "left_shoulder_pitch": 0.38,
        "left_shoulder_roll": 0.06,
        "left_shoulder_yaw": 0.0,
        "left_elbow": 0.18,
        "left_wrist_pitch": 0.0,
        "left_wrist_roll": -1.25,  # Palma hacia el cuerpo/muslo
        "left_wrist_yaw": 0.0,
        
        "right_shoulder_pitch": 0.38,
        "right_shoulder_roll": -0.06,
        "right_shoulder_yaw": 0.0,
        "right_elbow": 0.18,
        "right_wrist_pitch": 0.0,
        "right_wrist_roll": 1.25,  # Palma hacia el cuerpo/muslo
        "right_wrist_yaw": 0.0,
        
        # Piernas con flexión visible natural (rodillas amortiguadas hacia adelante)
        "left_hip_pitch": -0.16,
        "left_hip_roll": 0.02,
        "left_hip_yaw": 0.0,
        "left_knee": 0.32,
        "left_ankle_pitch": -0.16,
        "left_ankle_roll": -0.02,
        
        "right_hip_pitch": -0.16,
        "right_hip_roll": -0.02,
        "right_hip_yaw": 0.0,
        "right_knee": 0.32,
        "right_ankle_pitch": -0.16,
        "right_ankle_roll": 0.02,
    }
    pose.update(_mano_relajada_organica("left"))
    pose.update(_mano_relajada_organica("right"))
    return pose


class RepertorioAnimatronicoG1:
    """Catálogo de poses teatrales amplias (Laban + Lecoq + Disney Animatronics) para el Unitree G1."""

    ROLES: dict[str, dict] = {
        "MOTIVACION_ALEGRIA": {
            "nombre": "Compañero de Festejo",
            "base": {
                # Pelvis y caderas: contrapposto desinhibido con rodillas visiblemente flexionadas
                "waist_pitch": -0.08,
                "waist_roll": 0.04,
                "waist_yaw": 0.06,
                "left_hip_pitch": -0.22,
                "right_hip_pitch": -0.15,
                "left_hip_roll": 0.05,
                "right_hip_roll": -0.03,
                "left_knee": 0.44,
                "right_knee": 0.30,
                "left_ankle_pitch": -0.22,
                "right_ankle_pitch": -0.15,
                # Brazos abiertos y expansivos, palmas orientadas al cuerpo
                "left_shoulder_pitch": 0.10,
                "right_shoulder_pitch": 0.10,
                "left_shoulder_roll": 0.40,
                "right_shoulder_roll": -0.40,
                "left_elbow": 0.50,
                "right_elbow": 0.50,
                "left_wrist_roll": -1.15,
                "right_wrist_roll": 1.15,
            },
            "ademanes": {
                "A_apertura_triunfal": {
                    # Brazos en V de victoria arriba del torso
                    "waist_pitch": -0.10,
                    "waist_roll": 0.0,
                    "waist_yaw": 0.0,
                    "left_shoulder_pitch": -0.65,
                    "right_shoulder_pitch": -0.65,
                    "left_shoulder_roll": 0.70,
                    "right_shoulder_roll": -0.70,
                    "left_elbow": 0.45,
                    "right_elbow": 0.45,
                    "left_wrist_roll": 0.35,
                    "right_wrist_roll": -0.35,
                    "left_wrist_pitch": -0.15,
                    "right_wrist_pitch": -0.15,
                    "left_knee": 0.36,
                    "right_knee": 0.36,
                    "left_hip_pitch": -0.18,
                    "right_hip_pitch": -0.18,
                    "left_ankle_pitch": -0.18,
                    "right_ankle_pitch": -0.18,
                    **_mano_declamatoria("left"),
                    **_mano_declamatoria("right"),
                },
                "B_complicidad_senalamiento": {
                    # Torsión con señalamiento hacia el usuario y cadera en apoyo
                    "waist_pitch": 0.04,
                    "waist_yaw": 0.18,
                    "waist_roll": -0.05,
                    "left_shoulder_pitch": 0.38,
                    "left_shoulder_roll": 0.08,
                    "left_elbow": 0.18,
                    "left_wrist_roll": -1.25,  # Mano izquierda al muslo facing body
                    "right_shoulder_pitch": -0.48,
                    "right_shoulder_roll": -0.18,
                    "right_elbow": 0.38,
                    "right_wrist_pitch": 0.20,
                    "right_wrist_roll": 0.10,
                    "right_wrist_yaw": 0.10,
                    "left_knee": 0.50,
                    "right_knee": 0.26,
                    "left_hip_pitch": -0.25,
                    "right_hip_pitch": -0.13,
                    "left_ankle_pitch": -0.25,
                    "right_ankle_pitch": -0.13,
                    **_mano_relajada_organica("left"),
                    **_mano_senalamiento("right"),
                },
                "C_celebracion_pulgar": {
                    # Puño victorioso izquierdo y pulgar arriba derecho
                    "waist_pitch": -0.06,
                    "waist_yaw": -0.10,
                    "left_shoulder_pitch": 0.08,
                    "left_shoulder_roll": 0.35,
                    "left_elbow": 0.85,
                    "left_wrist_roll": -0.80,
                    "right_shoulder_pitch": -0.52,
                    "right_shoulder_roll": -0.22,
                    "right_elbow": 0.88,
                    "right_wrist_roll": 0.0,
                    "left_knee": 0.34,
                    "right_knee": 0.44,
                    "left_hip_pitch": -0.17,
                    "right_hip_pitch": -0.22,
                    "left_ankle_pitch": -0.17,
                    "right_ankle_pitch": -0.22,
                    **_mano_puno_victoria("left"),
                    **_mano_pulgar_arriba("right"),
                },
            },
        },
        "TRISTEZA_DESANIMO": {
            "nombre": "Contenedor Empático",
            "base": {
                # Inclinación empática de torso hacia adelante (>0.10 rad) con balance físico (caderas atrás, rodillas flexionadas)
                "waist_pitch": 0.15,
                "waist_roll": 0.04,
                "waist_yaw": 0.04,
                "left_hip_pitch": -0.20,
                "right_hip_pitch": -0.20,
                "left_knee": 0.40,
                "right_knee": 0.40,
                "left_ankle_pitch": -0.20,
                "right_ankle_pitch": -0.20,
                # Asimetría: brazo izquierdo descansando abajo (palma hacia muslo), derecho dispuesto a contener
                "left_shoulder_pitch": 0.38,
                "right_shoulder_pitch": 0.30,
                "left_shoulder_roll": 0.06,
                "right_shoulder_roll": -0.12,
                "left_elbow": 0.18,
                "right_elbow": 0.45,
                "left_wrist_roll": -1.25,
                "right_wrist_roll": 1.15,
            },
            "ademanes": {
                "A_mano_al_corazon": {
                    # Mano derecha al esternón con dedos curvados; izquierdo relajado abajo con palma al cuerpo
                    "waist_pitch": 0.15,
                    "waist_roll": 0.05,
                    "waist_yaw": 0.04,
                    "left_shoulder_pitch": 0.40,
                    "left_shoulder_roll": 0.06,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,  # Palma hacia el cuerpo
                    "right_shoulder_pitch": 0.20,
                    "right_shoulder_roll": -0.15,
                    "right_shoulder_yaw": -0.35,
                    "right_elbow": 1.15,
                    "right_wrist_pitch": 0.35,
                    "right_wrist_roll": -0.20,
                    "left_knee": 0.40,
                    "right_knee": 0.40,
                    "left_hip_pitch": -0.20,
                    "right_hip_pitch": -0.20,
                    "left_ankle_pitch": -0.20,
                    "right_ankle_pitch": -0.20,
                    **_mano_relajada_organica("left"),
                    **_mano_empatica_pecho("right"),
                },
                "B_acogida_y_apoyo": {
                    # Brazo derecho extendido en diagonal baja hacia el usuario ofreciendo calma; izquierdo al muslo
                    "waist_pitch": 0.14,
                    "waist_roll": 0.03,
                    "waist_yaw": -0.05,
                    "left_shoulder_pitch": 0.40,
                    "left_shoulder_roll": 0.06,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,  # Palma hacia el cuerpo
                    "right_shoulder_pitch": -0.10,
                    "right_shoulder_roll": -0.20,
                    "right_elbow": 0.45,
                    "right_wrist_pitch": 0.15,
                    "right_wrist_roll": 0.20,
                    "left_knee": 0.44,
                    "right_knee": 0.34,
                    "left_hip_pitch": -0.22,
                    "right_hip_pitch": -0.17,
                    "left_ankle_pitch": -0.22,
                    "right_ankle_pitch": -0.17,
                    **_mano_relajada_organica("left"),
                    **_mano_declamatoria("right"),
                },
            },
        },
        "ENOJO_FRUSTRACION": {
            "nombre": "Pacificador / Desescalada",
            "base": {
                # Base ancha y centro de gravedad bajo y enraizado (rodillas profundamente flexionadas)
                "waist_pitch": -0.04,
                "waist_roll": 0.0,
                "waist_yaw": 0.0,
                "left_hip_roll": 0.10,
                "right_hip_roll": -0.10,
                "left_hip_pitch": -0.24,
                "right_hip_pitch": -0.24,
                "left_knee": 0.48,
                "right_knee": 0.48,
                "left_ankle_pitch": -0.24,
                "right_ankle_pitch": -0.24,
                # Brazos en diagonal baja pacificadora
                "left_shoulder_pitch": 0.24,
                "right_shoulder_pitch": 0.24,
                "left_shoulder_roll": 0.25,
                "right_shoulder_roll": -0.25,
                "left_elbow": 0.45,
                "right_elbow": 0.45,
                "left_wrist_roll": -1.15,
                "right_wrist_roll": 1.15,
            },
            "ademanes": {
                "A_barrera_de_serenidad": {
                    # Palmas orientadas al frente y abajo hacia el interlocutor en señal de frenado pacífico
                    "waist_pitch": -0.04,
                    "waist_roll": 0.0,
                    "waist_yaw": 0.0,
                    "left_shoulder_pitch": 0.18,
                    "right_shoulder_pitch": 0.18,
                    "left_shoulder_roll": 0.30,
                    "right_shoulder_roll": -0.30,
                    "left_elbow": 0.58,
                    "right_elbow": 0.58,
                    "left_wrist_pitch": -0.30,
                    "right_wrist_pitch": -0.30,
                    "left_wrist_roll": -0.40,
                    "right_wrist_roll": 0.40,
                    "left_knee": 0.52,
                    "right_knee": 0.52,
                    "left_hip_pitch": -0.26,
                    "right_hip_pitch": -0.26,
                    "left_ankle_pitch": -0.26,
                    "right_ankle_pitch": -0.26,
                    **_mano_pacificador("left"),
                    **_mano_pacificador("right"),
                },
                "B_escucha_con_aplomo": {
                    # Asimetría: mano derecha sosteniendo sosiego, izquierda descansando con palma al muslo
                    "waist_pitch": -0.02,
                    "waist_roll": -0.04,
                    "waist_yaw": 0.08,
                    "left_shoulder_pitch": 0.40,
                    "left_shoulder_roll": 0.06,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,  # Palma al muslo
                    "right_shoulder_pitch": 0.18,
                    "right_shoulder_roll": -0.26,
                    "right_elbow": 0.50,
                    "right_wrist_pitch": -0.25,
                    "right_wrist_roll": 0.30,
                    "left_knee": 0.44,
                    "right_knee": 0.50,
                    "left_hip_pitch": -0.22,
                    "right_hip_pitch": -0.25,
                    "left_ankle_pitch": -0.22,
                    "right_ankle_pitch": -0.25,
                    **_mano_relajada_organica("left"),
                    **_mano_pacificador("right"),
                },
            },
        },
        "ANSIEDAD_ESTRES": {
            "nombre": "Guía de Respiración y Sosiego",
            "base": {
                # Pelvis centrada y articulaciones visiblemente flexibles
                "waist_pitch": 0.02,
                "waist_roll": 0.0,
                "waist_yaw": 0.0,
                "left_hip_pitch": -0.17,
                "right_hip_pitch": -0.17,
                "left_knee": 0.34,
                "right_knee": 0.34,
                "left_ankle_pitch": -0.17,
                "right_ankle_pitch": -0.17,
                "left_shoulder_pitch": 0.36,
                "right_shoulder_pitch": 0.36,
                "left_shoulder_roll": 0.10,
                "right_shoulder_roll": -0.10,
                "left_elbow": 0.22,
                "right_elbow": 0.22,
                "left_wrist_roll": -1.20,
                "right_wrist_roll": 1.20,
            },
            "ademanes": {
                "A_inhalacion_profunda": {
                    # Expansión torácica y elevación vertical (rodillas se estiran ligeramente a 0.20 rad)
                    "waist_pitch": -0.06,
                    "left_knee": 0.22,
                    "right_knee": 0.22,
                    "left_hip_pitch": -0.11,
                    "right_hip_pitch": -0.11,
                    "left_ankle_pitch": -0.11,
                    "right_ankle_pitch": -0.11,
                    "left_shoulder_pitch": 0.10,
                    "right_shoulder_pitch": 0.10,
                    "left_shoulder_roll": 0.35,
                    "right_shoulder_roll": -0.35,
                    "left_elbow": 0.45,
                    "right_elbow": 0.45,
                    "left_wrist_pitch": 0.18,
                    "right_wrist_pitch": 0.18,
                    "left_wrist_roll": -0.60,
                    "right_wrist_roll": 0.60,
                    **_mano_declamatoria("left"),
                    **_mano_declamatoria("right"),
                },
                "B_exhalacion_calma": {
                    # Descenso cadencioso (rodillas flexionan visiblemente a 0.44 rad, palmas hacia el cuerpo)
                    "waist_pitch": 0.03,
                    "left_knee": 0.44,
                    "right_knee": 0.44,
                    "left_hip_pitch": -0.22,
                    "right_hip_pitch": -0.22,
                    "left_ankle_pitch": -0.22,
                    "right_ankle_pitch": -0.22,
                    "left_shoulder_pitch": 0.40,
                    "right_shoulder_pitch": 0.40,
                    "left_shoulder_roll": 0.06,
                    "right_shoulder_roll": -0.06,
                    "left_elbow": 0.16,
                    "right_elbow": 0.16,
                    "left_wrist_pitch": 0.0,
                    "right_wrist_pitch": 0.0,
                    "left_wrist_roll": -1.25,  # Palmas hacia el cuerpo
                    "right_wrist_roll": 1.25,
                    **_mano_relajada_organica("left"),
                    **_mano_relajada_organica("right"),
                },
            },
        },
        "DUDA_INSEGURIDAD": {
            "nombre": "Andamiaje y Diálogo Socrático",
            "base": {
                "waist_pitch": 0.04,
                "waist_roll": 0.02,
                "waist_yaw": 0.0,
                "left_knee": 0.34,
                "right_knee": 0.34,
                "left_hip_pitch": -0.17,
                "right_hip_pitch": -0.17,
                "left_ankle_pitch": -0.17,
                "right_ankle_pitch": -0.17,
                "left_shoulder_pitch": 0.36,
                "right_shoulder_pitch": 0.36,
                "left_shoulder_roll": 0.12,
                "right_shoulder_roll": -0.12,
                "left_elbow": 0.24,
                "right_elbow": 0.24,
                "left_wrist_roll": -1.20,
                "right_wrist_roll": 1.20,
            },
            "ademanes": {
                "A_sopesar_opcion_a": {
                    "waist_yaw": 0.15,
                    "waist_roll": -0.04,
                    "left_shoulder_pitch": 0.12,
                    "left_shoulder_roll": 0.32,
                    "left_elbow": 0.50,
                    "left_wrist_roll": -0.30,
                    "right_shoulder_pitch": 0.40,
                    "right_shoulder_roll": -0.06,
                    "right_elbow": 0.16,
                    "right_wrist_roll": 1.25,  # Mano derecha al muslo
                    "left_knee": 0.44,
                    "right_knee": 0.28,
                    "left_hip_pitch": -0.22,
                    "right_hip_pitch": -0.14,
                    "left_ankle_pitch": -0.22,
                    "right_ankle_pitch": -0.14,
                    **_mano_declamatoria("left"),
                    **_mano_relajada_organica("right"),
                },
                "B_sopesar_opcion_b": {
                    "waist_yaw": -0.15,
                    "waist_roll": 0.04,
                    "right_shoulder_pitch": 0.12,
                    "right_shoulder_roll": -0.32,
                    "right_elbow": 0.50,
                    "right_wrist_roll": 0.30,
                    "left_shoulder_pitch": 0.40,
                    "left_shoulder_roll": 0.06,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,  # Mano izquierda al muslo
                    "left_knee": 0.28,
                    "right_knee": 0.44,
                    "left_hip_pitch": -0.14,
                    "right_hip_pitch": -0.22,
                    "left_ankle_pitch": -0.14,
                    "right_ankle_pitch": -0.22,
                    **_mano_relajada_organica("left"),
                    **_mano_declamatoria("right"),
                },
            },
        },
        "NEUTRO": {
            "nombre": "Atento y Conversacional",
            "base": {
                "waist_pitch": 0.0,
                "waist_roll": 0.0,
                "waist_yaw": 0.0,
                "left_knee": 0.32,
                "right_knee": 0.32,
                "left_hip_pitch": -0.16,
                "right_hip_pitch": -0.16,
                "left_ankle_pitch": -0.16,
                "right_ankle_pitch": -0.16,
                "left_shoulder_pitch": 0.38,
                "right_shoulder_pitch": 0.38,
                "left_shoulder_roll": 0.06,
                "right_shoulder_roll": -0.06,
                "left_elbow": 0.18,
                "right_elbow": 0.18,
                "left_wrist_roll": -1.25,
                "right_wrist_roll": 1.25,
            },
            "ademanes": {
                "A_atencion_izq": {
                    "waist_pitch": 0.02,
                    "waist_yaw": 0.08,
                    "left_shoulder_pitch": 0.24,
                    "left_shoulder_roll": 0.20,
                    "left_elbow": 0.38,
                    "left_wrist_roll": -0.50,
                    "right_shoulder_pitch": 0.38,
                    "right_elbow": 0.16,
                    "right_wrist_roll": 1.25,
                    "left_knee": 0.40,
                    "right_knee": 0.28,
                    "left_hip_pitch": -0.20,
                    "right_hip_pitch": -0.14,
                    "left_ankle_pitch": -0.20,
                    "right_ankle_pitch": -0.14,
                    **_mano_declamatoria("left"),
                    **_mano_relajada_organica("right"),
                },
                "B_atencion_der": {
                    "waist_pitch": 0.02,
                    "waist_yaw": -0.08,
                    "right_shoulder_pitch": 0.24,
                    "right_shoulder_roll": -0.20,
                    "right_elbow": 0.38,
                    "right_wrist_roll": 0.50,
                    "left_shoulder_pitch": 0.38,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,
                    "left_knee": 0.28,
                    "right_knee": 0.40,
                    "left_hip_pitch": -0.14,
                    "right_hip_pitch": -0.20,
                    "left_ankle_pitch": -0.14,
                    "right_ankle_pitch": -0.20,
                    **_mano_relajada_organica("left"),
                    **_mano_declamatoria("right"),
                },
            },
        },
        "CRISIS_RIESGO": {
            "nombre": "Contención Ética",
            "base": {
                "waist_pitch": 0.04,
                "waist_roll": 0.0,
                "waist_yaw": 0.0,
                "left_knee": 0.34,
                "right_knee": 0.34,
                "left_hip_pitch": -0.17,
                "right_hip_pitch": -0.17,
                "left_ankle_pitch": -0.17,
                "right_ankle_pitch": -0.17,
                "left_shoulder_pitch": 0.38,
                "right_shoulder_pitch": 0.38,
                "left_shoulder_roll": 0.06,
                "right_shoulder_roll": -0.06,
                "left_elbow": 0.18,
                "right_elbow": 0.18,
                "left_wrist_roll": -1.25,
                "right_wrist_roll": 1.25,
            },
            "ademanes": {
                "A_escucha_pacifica": {
                    "waist_pitch": 0.04,
                    "left_shoulder_pitch": 0.34,
                    "right_shoulder_pitch": 0.34,
                    "left_elbow": 0.22,
                    "right_elbow": 0.22,
                    "left_wrist_roll": -1.20,
                    "right_wrist_roll": 1.20,
                    "left_knee": 0.36,
                    "right_knee": 0.36,
                    "left_hip_pitch": -0.18,
                    "right_hip_pitch": -0.18,
                    "left_ankle_pitch": -0.18,
                    "right_ankle_pitch": -0.18,
                    **_mano_relajada_organica("left"),
                    **_mano_relajada_organica("right"),
                },
            },
        },
    }


class CoreografoPosturalG1:
    """Diseña el lenguaje corporal (kinésica + proxémica) según la emoción."""

    # Límites seguros estrictos para torso, extremidades y manos del G1 (subconjunto conservador del XML)
    LIMITES_ARTICULARES: dict[str, tuple[float, float]] = {
        # Pelvis y tronco
        "waist_yaw": (-0.45, 0.45),
        "waist_roll": (-0.25, 0.25),
        "waist_pitch": (-0.15, 0.25),
        # Extremidades superiores (brazos)
        "left_shoulder_pitch": (-2.20, 0.80),
        "right_shoulder_pitch": (-2.20, 0.80),
        "left_shoulder_roll": (-0.60, 1.40),
        "right_shoulder_roll": (-1.40, 0.60),
        "left_shoulder_yaw": (-1.30, 1.30),
        "right_shoulder_yaw": (-1.30, 1.30),
        "left_elbow": (-1.04, 1.60),
        "right_elbow": (-1.04, 1.60),
        "left_wrist_pitch": (-1.30, 1.30),
        "right_wrist_pitch": (-1.30, 1.30),
        "left_wrist_roll": (-1.40, 1.40),
        "right_wrist_roll": (-1.40, 1.40),
        "left_wrist_yaw": (-1.20, 1.20),
        "right_wrist_yaw": (-1.20, 1.20),
        # Extremidades inferiores (piernas vivas y amortiguadas)
        "left_hip_pitch": (-0.60, 0.60),
        "right_hip_pitch": (-0.60, 0.60),
        "left_hip_roll": (-0.35, 0.35),
        "right_hip_roll": (-0.35, 0.35),
        "left_hip_yaw": (-0.40, 0.40),
        "right_hip_yaw": (-0.40, 0.40),
        "left_knee": (0.0, 0.80),
        "right_knee": (0.0, 0.80),
        "left_ankle_pitch": (-0.50, 0.50),
        "right_ankle_pitch": (-0.50, 0.50),
        "left_ankle_roll": (-0.30, 0.30),
        "right_ankle_roll": (-0.30, 0.30),
        # Manos diestras Inspire RH56 (6 articulaciones independientes por mano)
        "left_hand_index": (0.0, 1.40),
        "right_hand_index": (0.0, 1.40),
        "left_hand_middle": (0.0, 1.40),
        "right_hand_middle": (0.0, 1.40),
        "left_hand_ring": (0.0, 1.40),
        "right_hand_ring": (0.0, 1.40),
        "left_hand_pinky": (0.0, 1.40),
        "right_hand_pinky": (0.0, 1.40),
        "left_hand_thumb_rotation": (0.0, 1.00),
        "right_hand_thumb_rotation": (0.0, 1.00),
        "left_hand_thumb_bend": (0.0, 1.25),
        "right_hand_thumb_bend": (0.0, 1.25),
    }

    @classmethod
    def _modular_poses_continuas(
        cls,
        secuencia: list[dict[str, float]],
        base: dict[str, float],
        valencia: float,
        arousal: float,
        intensidad: float,
    ) -> list[dict[str, float]]:
        """Escala continuamente las amplitudes articulares según (valencia, arousal, intensidad)."""
        escala = float(np.clip(0.85 + 0.35 * intensidad + 0.12 * abs(arousal), 0.72, 1.25))
        tilt_pitch = float(np.clip(-0.02 * valencia - 0.01 * arousal, -0.03, 0.03))
        salida: list[dict[str, float]] = []
        n = len(secuencia)
        for idx, pose in enumerate(secuencia):
            # Mantener el último keyframe de retorno a base limpio y estable
            if idx == n - 1 and n > 1:
                salida.append(dict(pose))
                continue
            nueva = dict(pose)
            for art, val in pose.items():
                if art in cls.LIMITES_ARTICULARES and art in base:
                    b_val = base[art]
                    delta = (val - b_val) * escala
                    if art == "waist_pitch":
                        nuevo_val = val + tilt_pitch
                    else:
                        nuevo_val = b_val + delta
                    lim_min, lim_max = cls.LIMITES_ARTICULARES[art]
                    nueva[art] = round(float(np.clip(nuevo_val, lim_min, lim_max)), 4)
            salida.append(nueva)
        return salida

    @classmethod
    def obtener_coreografia(
        cls,
        emocion: str,
        valencia: Optional[float] = None,
        arousal: Optional[float] = None,
        intensidad: float = 0.6,
    ) -> tuple[list[dict[str, float]], float, float, float]:
        """Devuelve (secuencia_poses, duracion_step_s, proxemica_m, vel_proxemica_ms)."""
        base = _pose_neutra_suave()

        # Obtener datos del repertorio animatrónico
        rol = RepertorioAnimatronicoG1.ROLES.get(
            emocion, RepertorioAnimatronicoG1.ROLES["NEUTRO"]
        )

        sec = []
        for ademan_dict in rol["ademanes"].values():
            pose = dict(base)
            pose.update(rol["base"])
            pose.update(ademan_dict)
            if emocion == "MOTIVACION_ALEGRIA" and "C_celebracion_pulgar" in rol["ademanes"]:
                if ademan_dict == rol["ademanes"]["C_celebracion_pulgar"]:
                    pose.update(_pulgar_arriba_derecho())
            sec.append(pose)
        sec.append(base)

        # Definir parámetros dinámicos según emoción
        configuraciones = {
            "ANSIEDAD_ESTRES": (0.95, 0.0, 0.0),
            "TRISTEZA_DESANIMO": (0.85, +0.25, 0.12),
            "ENOJO_FRUSTRACION": (0.80, -0.25, 0.12),
            "DUDA_INSEGURIDAD": (0.65, 0.0, 0.0),
            "MOTIVACION_ALEGRIA": (0.50, 0.0, 0.0),
            "NEUTRO": (0.60, 0.0, 0.0),
            "CRISIS_RIESGO": (0.70, 0.0, 0.0),
        }

        dur, pm, pv = configuraciones.get(emocion, (0.70, 0.0, 0.0))

        if valencia is not None and arousal is not None and emocion != "CRISIS_RIESGO":
            sec = cls._modular_poses_continuas(sec, base, valencia, arousal, intensidad)
            dur = round(float(np.clip(dur * (1.0 - 0.15 * arousal), 0.42, 1.15)), 2)

        return sec, dur, pm, pv

    @classmethod
    def generar_postura_continua(
        cls,
        valencia: float = 0.0,
        arousal: float = 0.0,
        fase_tiempo: float = 0.0,
        hablando: bool = False,
        energia: float = 1.0,
    ) -> dict[str, float]:
        """Calcula la postura 29-DoF continua según Laban Movement Analysis, Lecoq y McNeill.
        
        Aplica Center-Out movement donde el torso precede a los brazos y extremidades,
        modulando respiración diafragmática en reposo o batutas rítmicas al hablar.
        """
        v = float(np.clip(valencia, -1.0, 1.0))
        a = float(np.clip(arousal, -1.0, 1.0))
        e = float(np.clip(energia, 0.4, 2.0))

        # 1. Postura Base Continua f(V, A)
        pitch_base = float(np.clip(-0.06 * v - 0.03 * a if v < 0 else -0.04 * v, -0.05, 0.16))
        roll_base = float(np.clip(0.02 * v, -0.04, 0.04))
        yaw_base = 0.0

        sh_pitch_base = float(np.clip(0.42 - 0.12 * max(0.0, v) - 0.08 * max(0.0, a), 0.24, 0.46))
        sh_roll_base = float(np.clip(0.08 + 0.10 * max(0.0, v), 0.06, 0.22))
        el_base = float(np.clip(0.28 + 0.10 * max(0.0, v) + 0.04 * a, 0.22, 0.45))

        # 2. Modulaciones Armónicas Dinámicas con desfasaje Center-Out (Lecoq / Disney)
        if hablando:
            f = fase_tiempo
            amp_torso = 0.012 * e
            amp_sh = (0.04 + 0.04 * max(0.0, a)) * e
            amp_el = (0.06 + 0.06 * max(0.0, a)) * e
            amp_dedos = (0.08 + 0.10 * max(0.0, a)) * e

            # Center-out phase lags: torso -> hombro -> codo -> muñeca
            mod_torso = amp_torso * math.sin(f)
            mod_l_sh = -amp_sh * math.sin(f + 0.35)
            mod_r_sh = -amp_sh * math.sin(f + 0.35 + 0.80)
            mod_l_el = amp_el * math.cos(f + 0.80)
            mod_r_el = amp_el * math.cos(f + 0.80 + 0.80)
            mod_l_wr = 0.15 * math.sin(f + 1.15)
            mod_r_wr = -0.15 * math.sin(f + 1.15 + 0.80)
            dedos_val = float(np.clip(0.06 + amp_dedos * abs(math.sin((f + 1.15) * 0.5)), 0.02, 0.45))
        else:
            # Idle diaphragmatic breathing (0.25 Hz)
            f = fase_tiempo
            mod_torso = 0.014 * math.sin(f)
            mod_l_sh = 0.010 * math.sin(f + 0.20)
            mod_r_sh = 0.010 * math.sin(f + 0.20)
            mod_l_el = 0.008 * math.cos(f)
            mod_r_el = 0.008 * math.cos(f)
            mod_l_wr = 0.0
            mod_r_wr = 0.0
            dedos_val = float(np.clip(0.04 + 0.02 * (1.0 + math.sin(f)), 0.02, 0.10))

        pose = {
            "waist_pitch": pitch_base + mod_torso,
            "waist_roll": roll_base,
            "waist_yaw": yaw_base,
            "left_shoulder_pitch": sh_pitch_base + mod_l_sh,
            "right_shoulder_pitch": sh_pitch_base + mod_r_sh,
            "left_shoulder_roll": sh_roll_base,
            "right_shoulder_roll": -sh_roll_base,
            "left_shoulder_yaw": 0.0,
            "right_shoulder_yaw": 0.0,
            "left_elbow": el_base + mod_l_el,
            "right_elbow": el_base + mod_r_el,
            "left_wrist_pitch": 0.0,
            "right_wrist_pitch": 0.0,
            "left_wrist_roll": float(np.clip(-1.25 + mod_l_wr, -1.40, 1.40)),
            "right_wrist_roll": float(np.clip(1.25 + mod_r_wr, -1.40, 1.40)),
            "left_wrist_yaw": 0.0,
            "right_wrist_yaw": 0.0,
        }

        # Piernas vivas con flexión orgánica visible y contrapposto
        knee_base = float(np.clip(0.32 + 0.10 * abs(a), 0.22, 0.48))
        ankle_base = -knee_base * 0.5
        hip_pitch_base = -knee_base * 0.5
        hip_roll_l = float(np.clip(0.02 + 0.03 * v, -0.06, 0.08))
        hip_roll_r = float(np.clip(-0.02 - 0.03 * v, -0.08, 0.06))

        pose["left_hip_pitch"] = hip_pitch_base
        pose["right_hip_pitch"] = hip_pitch_base
        pose["left_hip_roll"] = hip_roll_l
        pose["right_hip_roll"] = hip_roll_r
        pose["left_hip_yaw"] = 0.0
        pose["right_hip_yaw"] = 0.0
        pose["left_knee"] = knee_base
        pose["right_knee"] = knee_base
        pose["left_ankle_pitch"] = ankle_base
        pose["right_ankle_pitch"] = ankle_base
        pose["left_ankle_roll"] = -hip_roll_l * 0.5
        pose["right_ankle_roll"] = -hip_roll_r * 0.5

        # Dedos Inspire RH56 con cascada anatómica natural (6 DoF por mano)
        for lado in ("left", "right"):
            pose[f"{lado}_hand_index"] = float(np.clip(dedos_val, 0.05, 1.30))
            pose[f"{lado}_hand_middle"] = float(np.clip(dedos_val * 1.20 + 0.04, 0.05, 1.35))
            pose[f"{lado}_hand_ring"] = float(np.clip(dedos_val * 1.40 + 0.08, 0.05, 1.38))
            pose[f"{lado}_hand_pinky"] = float(np.clip(dedos_val * 1.60 + 0.12, 0.05, 1.40))
            pose[f"{lado}_hand_thumb_rotation"] = float(np.clip(0.20 + 0.30 * max(0.0, a), 0.10, 0.80))
            pose[f"{lado}_hand_thumb_bend"] = float(np.clip(dedos_val * 0.70, 0.05, 1.00))

        # Respetar límites seguros estrictos
        for art in list(pose.keys()):
            if art in cls.LIMITES_ARTICULARES:
                lim_min, lim_max = cls.LIMITES_ARTICULARES[art]
                pose[art] = round(float(np.clip(pose[art], lim_min, lim_max)), 4)

        return pose


# =====================================================================
#  2. MOTOR DE RESPUESTA PSICOLINGÜÍSTICA (LLM HÍBRIDO LOCAL/NUBE + CBR)
# =====================================================================

_LLM_LOCAL_INSTANCE = None
_LLM_LOCAL_LOCK = threading.Lock()


class MotorRespuestaCoach:
    """Selecciona prosodia continua, timbre, estrategia HRI y respuesta conversacional."""

    PERFILES_BASE: dict[str, tuple[str, PerfilProsodico, list[str]]] = {
        "ANSIEDAD_ESTRES": (
            "Grounding Sensorial y Co-regulación Respiratoria",
            PerfilProsodico(
                velocidad_wpm=124,
                velocidad_pct=-22,
                volumen_db=-4.0,
                tono_hz=-15,
                pausa_inicial_s=0.80,
                pausa_entre_frases_s=0.85,
                estilo_lexico="grounding_pausado_tiempo_presente",
                timbre="calido_suave",
            ),
            [
                "Paremos un segundo acá. Inhalá suave conmigo mientras subo los brazos... y soltá el aire despacio. No tenés que resolver todo al mismo tiempo; elijamos una sola cosa chiquita para los próximos diez minutos.",
                "Estás a salvo en este momento, bajemos un cambio juntos. Sentí el apoyo de los pies en el piso y tomá aire lento. Cuando la mente va a mil, frenar treinta segundos ordena todo el panorama.",
                "Te escucho y noto la presión que tenés encima. Hagamos una respiración profunda juntos ahora mismo... Eso es. Vamos paso a paso, sin exigirte perfección.",
            ],
        ),
        "TRISTEZA_DESANIMO": (
            "Validación Empática y Contención Compasiva",
            PerfilProsodico(
                velocidad_wpm=134,
                velocidad_pct=-15,
                volumen_db=-3.0,
                tono_hz=-8,
                pausa_inicial_s=0.60,
                pausa_entre_frases_s=0.65,
                estilo_lexico="calido_validante_compasivo",
                timbre="calido_suave",
            ),
            [
                "Te escucho de verdad, y es totalmente válido que hoy te sientas agotado o triste. Un tropiezo no borra todo el esfuerzo que venís haciendo. Hoy date permiso para descansar un poco; acá estoy acompañándote.",
                "Lamento que estés pasando este momento pesado. No tenés que poder con todo hoy ni forzar estar bien. Si querés, contame qué fue lo que más te dolió y lo pensamos sin apuro.",
                "Es humano sentirse sin fuerzas cuando algo no sale como esperabas. Tratate con la misma paciencia con la que tratarías a un buen amigo. Cuando estés listo, damos el próximo paso juntos.",
            ],
        ),
        "ENOJO_FRUSTRACION": (
            "Desescalada No-Confrontativa y Objetivación",
            PerfilProsodico(
                velocidad_wpm=140,
                velocidad_pct=-10,
                volumen_db=0.0,
                tono_hz=-5,
                pausa_inicial_s=0.70,
                pausa_entre_frases_s=0.55,
                estilo_lexico="ecuánime_objetivo_desescalador",
                timbre="firme_templado",
            ),
            [
                "Entiendo perfectamente tu bronca; cualquiera estaría frustrado en esa situación. Te doy tu espacio para descargar. Cuando quieras, separamos lo que no depende de vos de lo que sí podemos destrabar hoy.",
                "Tiene sentido que te dé impotencia cuando algo se traba así. Tomemos aire un instante para no decidir en caliente. Decime cuál es el obstáculo principal y lo atacamos de forma concreta.",
                "Escucho tu frustración y no te voy a pedir que la ignores. Usemos esa energía a tu favor: identifiquemos qué parte puntual falló y armemos un plan directo para corregirlo.",
            ],
        ),
        "DUDA_INSEGURIDAD": (
            "Andamiaje Cognitivo Socrático",
            PerfilProsodico(
                velocidad_wpm=154,
                velocidad_pct=0,
                volumen_db=+1.0,
                tono_hz=+5,
                pausa_inicial_s=0.40,
                pausa_entre_frases_s=0.42,
                estilo_lexico="estructurado_clarificador_socratico",
                timbre="brillante_claro",
            ),
            [
                "Cuando una decisión parece enorme, ayuda dividirla en dos caminos claros. Por un lado, pensá qué es lo peor realista que podría pasar; por el otro, qué aprenderías si sale bien. ¿Cuál opción te da más curiosidad que miedo?",
                "Es normal dudar cuando algo te importa. En vez de buscar la decisión perfecta de entrada, hagamos una prueba chiquita y reversible hoy. ¿Cuál sería el primer paso más simple para probar?",
                "Ordenemos las ideas juntos. Si tuvieras que aconsejar a un compañero en tu misma situación con los datos que hoy tenés en la mano, ¿qué camino le sugerirías elegir primero?",
            ],
        ),
        "MOTIVACION_ALEGRIA": (
            "Refuerzo Positivo y Anclaje de Autoeficacia",
            PerfilProsodico(
                velocidad_wpm=170,
                velocidad_pct=+12,
                volumen_db=+3.0,
                tono_hz=+15,
                pausa_inicial_s=0.20,
                pausa_entre_frases_s=0.25,
                estilo_lexico="entusiasta_celebratorio_energico",
                timbre="brillante_claro",
            ),
            [
                "¡Qué alegría enorme escuchar eso! Te lo ganaste con constancia y dedicación. Guardate bien esta sensación de logro para recordar de todo lo que sos capaz en el próximo desafío.",
                "¡Excelente noticia, felicitaciones! Disfrutá este resultado porque es fruto directo de tu trabajo. ¿Cuál es el próximo objetivo que te entusiasma encarar con este envión?",
                "¡Increíble avance! Me encanta ver esa energía. Reconocer tus propios logros fortalece tu confianza; celebralo hoy como corresponde.",
            ],
        ),
        "CRISIS_RIESGO": (
            "Protocolo Ético de Contención y Derivación Humana (human-ai.org)",
            PerfilProsodico(
                velocidad_wpm=130,
                velocidad_pct=-16,
                volumen_db=0.0,
                tono_hz=-6,
                pausa_inicial_s=0.50,
                pausa_entre_frases_s=0.65,
                estilo_lexico="contencion_etica_derivacion_humana",
                timbre="calido_suave",
            ),
            [
                "Lo que estás sintiendo es muy importante y no tenés que atravesarlo en soledad. Como soy un robot educativo, mi deber ético es cuidarte y pedirte que hables ahora mismo con una persona de confianza, con el equipo de orientación o al 135 de asistencia gratuita las 24 horas.",
            ],
        ),
        "NEUTRO": (
            "Conversación Empática y Escucha Activa",
            PerfilProsodico(
                velocidad_wpm=150,
                velocidad_pct=0,
                volumen_db=0.0,
                tono_hz=0,
                pausa_inicial_s=0.30,
                pausa_entre_frases_s=0.35,
                estilo_lexico="conversacional_empatico",
                timbre="neutro_templado",
            ),
            [
                "Acá estoy atento escuchándote. Contame cómo te venís sintiendo hoy o qué tema tenés en mente y me adapto a tu ritmo.",
                "Te escucho con atención. Contame un poco más sobre eso o cómo te hace sentir para poder acompañarte mejor.",
                "Claro, te sigo. ¿Y cómo venís llevando ese tema hoy? Si querés lo charlamos paso a paso.",
            ],
        ),
    }

    def __init__(self, usar_llm_si_disponible: bool = True, usar_llm_local: bool = False):
        self.usar_llm_si_disponible = usar_llm_si_disponible
        self.usar_llm_local = usar_llm_local
        self._contadores_rotacion: dict[str, int] = {}
        self.historial_chat: deque[dict[str, str]] = deque(maxlen=10)
        self._analizador_lexico = AnalizadorLexicoAfectivo()

    def registrar_turno(self, texto_usuario: str, respuesta_robot: str) -> None:
        """Guarda un intercambio en la memoria conversacional multiturno."""
        if texto_usuario and texto_usuario.strip():
            self.historial_chat.append({"role": "user", "content": texto_usuario.strip()})
        if respuesta_robot and respuesta_robot.strip():
            self.historial_chat.append({"role": "assistant", "content": respuesta_robot.strip()})

    @staticmethod
    def _responder_conversacion_basica(
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
    ) -> Optional[tuple[str, str, str]]:
        """Detecta intenciones de conversación social básica y devuelve (estrategia, preset_rostro, respuesta)."""
        if estado.incongruencia_detectada or estado.es_crisis_etica:
            return None

        from percepcion_multimodal import normalizar_texto
        t = normalizar_texto(texto_usuario).strip()
        if not t:
            return None

        # 1. Identidad / nombre / presentación del robot
        if re.search(r"\b(?:como\s+te\s+llamas|quien\s+sos|que\s+sos|tu\s+nombre|presentate)\b", t):
            return (
                "Presentación e Identidad Robótica",
                "MOTIVACION_ALEGRIA",
                "Me llamo Ottoman. Soy un robot humanoide Unitree G1 y tu coach de Inteligencia Artificial en UADE. Puedo ejecutar movimientos físicos seguros o charlar con vos de cualquier tema adaptando mi voz y mis gestos.",
            )

        # 2. Capacidades / ayuda / cómo funciona
        if re.search(r"\b(?:que\s+podes\s+hacer|que\s+sabes\s+hacer|para\s+que\s+servis|en\s+que\s+me\s+ayudas|como\s+funciona|que\s+comandos)\b|^ayuda$", t):
            return (
                "Orientación de Capacidades Multimodales",
                "NEUTRO",
                "Puedo ayudarte de dos formas: si me pedís avanzar, girar, saludar o frenar, muevo mi cuerpo en el simulador. Y si charlás conmigo de cualquier tema, analizo tus palabras, tu voz y tu cara para acompañarte.",
            )

        # 3. Pregunta de cortesía / estado al robot ("¿cómo estás?", "¿qué onda?", "¿todo bien?")
        if re.search(r"\b(?:como\s+estas|como\s+andas|que\s+onda|que\s+tal|como\s+va|como\s+te\s+sentis)\b", t) and not re.search(r"\b(?:bien|mal|triste|ansioso|cansado)\b", t):
            return (
                "Rapport Social y Apertura Empática",
                "MOTIVACION_ALEGRIA",
                "¡Todo excelente por acá! Tengo los motores listos y los sensores activos para escucharte. Contame de vos, ¿cómo viene tu día hoy?",
            )

        # 4. Usuario responde que está bien / tranquilo ("estoy bien", "todo bien", "bien y vos")
        if estado.emocion_dominante in ("NEUTRO", "MOTIVACION_ALEGRIA") and re.search(
            r"^(?:estoy\s+bien|todo\s+bien|muy\s+bien|bien\s+por\s+suerte|todo\s+tranqui|re\s+bien|barbaro|de\s+diez|joya|bien(?:\s+y\s+vos|\s+gracias)?)[!?.]*$",
            t,
        ):
            return (
                "Sintonía Positiva y Exploración de Metas",
                "MOTIVACION_ALEGRIA",
                "¡Qué bueno escuchar que estás bien! Mantener esa tranquilidad suma muchísimo. ¿En qué proyecto o tema estás pensando hoy?",
            )

        # 5. Agradecimientos ("gracias", "muchas gracias", "me sirvió")
        if re.search(r"^(?:gracias|muchas\s+gracias|te\s+agradezco|muy\s+amable|mil\s+gracias|me\s+sirvio)[!?.]*$", t):
            return (
                "Cierre Cálido y Disponibilidad",
                "MOTIVACION_ALEGRIA",
                "¡De nada! Es un verdadero gusto acompañarte. Acá me quedo atento por si querés seguir charlando o darme alguna orden de movimiento.",
            )

        # 6. Despedidas ("chau", "hasta luego", "nos vemos", "adiós")
        if re.search(r"^(?:chau|adios|hasta\s+luego|nos\s+vemos|hasta\s+manana|me\s+voy\s+yendo)[!?.]*$", t):
            return (
                "Despedida Cordial",
                "MOTIVACION_ALEGRIA",
                "¡Hasta luego! Que tengas un excelente resto del día y muchos éxitos con todo. ¡Nos vemos pronto!",
            )

        return None

    def planificar(
        self,
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
        historial_emociones: Optional[list[str]] = None,
    ) -> PlanRegulacionEmocional:
        """Construye el plan completo de conversación abierta, voz DSP, rostro y postura."""
        emo = estado.emocion_dominante if estado.emocion_dominante in self.PERFILES_BASE else "NEUTRO"
        estrategia, prosodia_base, plantillas = self.PERFILES_BASE[emo]
        preset_rostro = emo

        conv_basica = (
            self._responder_conversacion_basica(texto_usuario, estado)
            if emo in ("NEUTRO", "MOTIVACION_ALEGRIA")
            else None
        )
        if conv_basica is not None:
            estrategia, preset_rostro, respuesta_conv = conv_basica
            if preset_rostro in self.PERFILES_BASE:
                _, prosodia_base, _ = self.PERFILES_BASE[preset_rostro]
        else:
            respuesta_conv = ""

        # Selección de respuesta:
        # 1) API Cloud (Gemini / Groq / OpenAI) si está configurada
        # 2) LLM Local GGUF (Qwen2.5-1.5B-Instruct) cuando usar_llm_local=True
        # 3) Conversación básica rápida o Plantillas CBR
        origen = "CBR_LOCAL"
        respuesta = ""

        if self.usar_llm_si_disponible and emo != "CRISIS_RIESGO":
            if any(os.environ.get(k) for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")):
                resp_nube, orig_nube = self._consultar_llm_nube(texto_usuario, estado, estrategia, prosodia_base)
                if resp_nube:
                    respuesta = resp_nube
                    origen = orig_nube

            if not respuesta and self.usar_llm_local and not conv_basica:
                resp_local = self._consultar_llm_local_gguf(texto_usuario, estado, estrategia)
                if resp_local:
                    respuesta = resp_local
                    origen = "LLM_LOCAL_QWEN"

        if not respuesta:
            if respuesta_conv:
                respuesta = respuesta_conv
                origen = "CONV_RAPIDA"
            else:
                idx = self._contadores_rotacion.get(emo, 0) % len(plantillas)
                self._contadores_rotacion[emo] = idx + 1
                respuesta = plantillas[idx]

        # Retroproyección afectiva semántica: si el texto del usuario no tenía palabras clave
        # explícitas (NEUTRO sin cámara/micrófono) pero el LLM detectó alegría/tristeza/estrés
        # implícita en la historia del usuario, actualizamos prosodia, cara y cuerpo!
        if (
            emo == "NEUTRO"
            and conv_basica is None
            and not estado.facial.rostro_detectado
            and not estado.acustica.audio_analizado
            and origen in ("LLM_LOCAL_QWEN", "GEMINI_API", "GROQ_API", "OPENAI_API")
        ):
            retro = self._analizador_lexico.analizar(respuesta)
            if retro.es_expresion_emocional and retro.emocion_lexica in self.PERFILES_BASE and retro.emocion_lexica != "CRISIS_RIESGO":
                emo = retro.emocion_lexica
                preset_rostro = emo
                estrategia, prosodia_base, _ = self.PERFILES_BASE[emo]
                estado.emocion_dominante = emo
                estado.valencia = round(0.75 * retro.valencia_lexica, 3)
                estado.arousal = round(0.75 * retro.arousal_lexico, 3)
                estado.intensidad = round(max(0.45, retro.intensidad_lexica * 0.8), 3)

        # Modulación continua de velocidad (WPM), volumen (dB), tono (Hz) y timbre según (V, A, Intensidad)
        factor_int = max(0.0, estado.intensidad - 0.5)
        vel_wpm = int(round(
            prosodia_base.velocidad_wpm
            + (
                -12 * factor_int
                if emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO")
                else 8 * factor_int
                if emo == "MOTIVACION_ALEGRIA"
                else 10 * estado.valencia
                if emo == "NEUTRO"
                else 0
            )
        ))
        vol_db = round(
            prosodia_base.volumen_db
            + (-1.5 * factor_int if emo == "ANSIEDAD_ESTRES" else 0.0),
            1,
        )
        tono_hz = int(round(
            prosodia_base.tono_hz
            + (
                -6 * factor_int
                if emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO")
                else 5 * factor_int
                if emo == "MOTIVACION_ALEGRIA"
                else 8 * estado.valencia
                if emo == "NEUTRO"
                else 0
            )
        ))
        pausa_frases = round(
            prosodia_base.pausa_entre_frases_s + (0.20 * factor_int if emo == "ANSIEDAD_ESTRES" else 0.0),
            2,
        )

        timbre_elegido = prosodia_base.timbre
        if emo == "NEUTRO":
            if estado.valencia >= 0.25:
                timbre_elegido = "brillante_claro"
            elif estado.valencia <= -0.20:
                timbre_elegido = "calido_suave"

        prosodia = PerfilProsodico(
            velocidad_wpm=vel_wpm,
            velocidad_pct=int(round(((vel_wpm - 150) / 150.0) * 100)),
            volumen_db=vol_db,
            tono_hz=tono_hz,
            pausa_inicial_s=prosodia_base.pausa_inicial_s,
            pausa_entre_frases_s=pausa_frases,
            estilo_lexico=prosodia_base.estilo_lexico,
            timbre=timbre_elegido,
        )

        # Si detectó incongruencia entre palabras ("estoy bien") y cara/voz, lo explicita con tacto
        if estado.incongruencia_detectada and emo != "CRISIS_RIESGO" and origen == "CBR_LOCAL":
            prefijo = f"{estado.detalle_incongruencia}. No hace falta disimular conmigo. "
            respuesta = prefijo + respuesta

        # Si la memoria muestra persistencia de malestar en los últimos turnos, adapta seguimiento
        if historial_emociones and len(historial_emociones) >= 2 and emo != "CRISIS_RIESGO" and origen == "CBR_LOCAL":
            previas = historial_emociones[-2:]
            if all(p == emo for p in previas) and emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO", "ENOJO_FRUSTRACION"):
                respuesta += " Noto que esta emoción sigue muy presente; tomemos todo el tiempo que necesites."
            elif previas[-1] in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO", "ENOJO_FRUSTRACION") and emo == "MOTIVACION_ALEGRIA":
                respuesta = "¡Qué bueno notar cómo cambió tu energía respecto a hace un rato! " + respuesta

        # Registrar este intercambio en el historial conversacional multiturno
        self.registrar_turno(texto_usuario, respuesta)

        secuencia, dur_step, prox_m, prox_vel = CoreografoPosturalG1.obtener_coreografia(
            preset_rostro,
            valencia=estado.valencia,
            arousal=estado.arousal,
            intensidad=estado.intensidad,
        )

        return PlanRegulacionEmocional(
            emocion_usuario=emo if conv_basica is None else preset_rostro,
            estrategia_hri=estrategia,
            texto_respuesta=respuesta,
            prosodia=prosodia,
            secuencia_postural=secuencia,
            duracion_step_postura=dur_step,
            proxemica_distancia_m=prox_m,
            proxemica_velocidad_ms=prox_vel,
            preset_rostro=preset_rostro,
            origen_respuesta=origen,
        )

    @staticmethod
    def _obtener_llm_local():
        """Carga de forma perezosa (singleton) el modelo Qwen2.5-1.5B-Instruct GGUF."""
        global _LLM_LOCAL_INSTANCE
        if _LLM_LOCAL_INSTANCE is not None:
            return _LLM_LOCAL_INSTANCE
        with _LLM_LOCAL_LOCK:
            if _LLM_LOCAL_INSTANCE is not None:
                return _LLM_LOCAL_INSTANCE
            ruta_gguf = (
                Path(__file__).resolve().parent
                / "modelos"
                / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
            )
            if not ruta_gguf.exists():
                return None
            try:
                from llama_cpp import Llama
                _LLM_LOCAL_INSTANCE = Llama(
                    model_path=str(ruta_gguf),
                    n_ctx=1536,
                    n_threads=max(2, min(8, (os.cpu_count() or 4))),
                    verbose=False,
                )
                return _LLM_LOCAL_INSTANCE
            except Exception:
                return None

    def _construir_contexto_sensorial(self, estado: EstadoAfectivoUsuario, estrategia: str) -> str:
        partes = [
            f"Emoción detectada en el usuario: {estado.emocion_dominante} "
            f"(Valencia={estado.valencia:+.2f}, Arousal={estado.arousal:+.2f}). "
            f"Estrategia HRI a aplicar: {estrategia}."
        ]
        if estado.facial.rostro_detectado:
            partes.append(f"Cámara FACS: rostro con expresión {estado.facial.emocion_facial}.")
        if estado.acustica.audio_analizado:
            partes.append(
                f"Voz del usuario: tono {estado.acustica.tono_f0_hz:.0f} Hz, "
                f"velocidad {estado.acustica.rapidez_wpm:.0f} ppm, volumen {estado.acustica.volumen_db:.0f} dB."
            )
        if estado.incongruencia_detectada:
            partes.append(
                f"ATENCIÓN INCONGRUENCIA: {estado.detalle_incongruencia}. Mencionalo con mucha empatía."
            )
        return " ".join(partes)

    def _consultar_llm_local_gguf(
        self,
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
        estrategia: str,
    ) -> str:
        """Genera una respuesta conversacional abierta multiturno con Qwen2.5-1.5B-Instruct local."""
        llm = self._obtener_llm_local()
        if llm is None:
            return ""

        tono_guia = (
            f"El usuario se siente con {estado.emocion_dominante} (aplicá {estrategia})."
            if estado.emocion_dominante != "NEUTRO"
            else "Mantené un tono conversacional, amigable y curioso."
        )
        if estado.incongruencia_detectada:
            tono_guia += f" Nota importante: {estado.detalle_incongruencia}. Mencionalo con tacto."

        sistema = (
            "Sos un asistente y coach empático argentino (tu nombre es Ottoman y hablás con el usuario). "
            "Usá español rioplatense natural ('vos', 'tenés', 'descansá', 'contame'). "
            "Regla principal: respondé SIEMPRE de forma específica al tema concreto que cuenta o pregunta el usuario "
            "en 2 oraciones breves (máximo 40 palabras), sin usar listas. "
            f"{tono_guia}"
        )
        mensajes: list[dict[str, str]] = [
            {"role": "system", "content": sistema},
            {"role": "user", "content": "Estuve estudiando toda la tarde y ya tengo hambre."},
            {
                "role": "assistant",
                "content": "¡Qué gran esfuerzo metiste toda la tarde con el estudio! Hacete una pausa para comer algo rico y despejar la mente, te lo ganaste.",
            },
        ]
        # Agregar los últimos 6 mensajes del historial para sostener el hilo de la conversación
        for m in list(self.historial_chat)[-6:]:
            mensajes.append({"role": m["role"], "content": m["content"]})

        mensajes.append({"role": "user", "content": texto_usuario})

        try:
            res = llm.create_chat_completion(
                messages=mensajes,
                max_tokens=90,
                temperature=0.45,
                top_p=0.90,
                repeat_penalty=1.15,
            )
            texto = res["choices"][0]["message"]["content"].strip()
            texto = re.sub(r"^(?:Ottoman|Asistente|Respuesta)\s*:\s*", "", texto, flags=re.IGNORECASE).strip()
            return texto
        except Exception:
            return ""

    def _consultar_llm_nube(
        self,
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
        estrategia: str,
        prosodia: PerfilProsodico,
    ) -> tuple[str, str]:
        """Consulta Gemini, Groq u OpenAI si hay API key configurada."""
        ctx = self._construir_contexto_sensorial(estado, estrategia)
        sistema = (
            "Sos Ottoman, el robot humanoide Unitree G1 de UADE actuando como compañero conversacional "
            "y Coach Emocional ético (human-ai.org). Respondé en español rioplatense ('vos') en MÁXIMO "
            f"2 oraciones breves. Estilo léxico: {prosodia.estilo_lexico}. Contexto biométrico: {ctx}"
        )

        # 1. Gemini API
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            hist_txt = "\n".join(
                f"{'Usuario' if m['role'] == 'user' else 'Ottoman'}: {m['content']}"
                for m in list(self.historial_chat)[-6:]
            )
            prompt = f"{sistema}\n\nHistorial reciente:\n{hist_txt}\nUsuario: \"{texto_usuario}\"\nOttoman:"
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={gemini_key}"
            )
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.55, "maxOutputTokens": 130},
            }).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    datos = json.loads(resp.read().decode("utf-8"))
                    partes = datos["candidates"][0]["content"]["parts"]
                    return partes[0]["text"].strip(), "GEMINI_API"
            except Exception:
                pass

        # 2. Groq API o OpenAI API (formato compatible OpenAI Chat Completions)
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if groq_key or openai_key:
            es_groq = bool(groq_key)
            api_key = groq_key if es_groq else openai_key
            url = (
                "https://api.groq.com/openai/v1/chat/completions"
                if es_groq
                else "https://api.openai.com/v1/chat/completions"
            )
            modelo = "llama-3.3-70b-versatile" if es_groq else "gpt-4o-mini"
            mensajes = [{"role": "system", "content": sistema}]
            for m in list(self.historial_chat)[-6:]:
                mensajes.append({"role": m["role"], "content": m["content"]})
            mensajes.append({"role": "user", "content": texto_usuario})
            payload = json.dumps({
                "model": modelo,
                "messages": mensajes,
                "temperature": 0.55,
                "max_tokens": 120,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    datos = json.loads(resp.read().decode("utf-8"))
                    texto = datos["choices"][0]["message"]["content"].strip()
                    return texto, ("GROQ_API" if es_groq else "OPENAI_API")
            except Exception:
                pass

        return "", ""


# =====================================================================
#  3. SINTETIZADOR DE VOZ ADAPTATIVO DSP (VELOCIDAD, PAUSAS, dB, TONO Hz, TIMBRE)
# =====================================================================

def enriquecer_texto_prosodico(texto: str) -> str:
    """Aplica formato prosódico rioplatense: signos enfáticos en aperturas/cierres,
    comas de apoyo interno para forzar tildes y acentuación tónica viva (estilo Prueba 3).
    """
    if not texto:
        return ""
    t = texto.strip()

    # 1. Asegurar tildes obligatorias en voseo rioplatense
    reemplazos_voseo = [
        (r"\bmira\b", "mirá"),
        (r"\btenes\b", "tenés"),
        (r"\bestas\b", "estás"),
        (r"\bhace\b", "hacé"),
        (r"\brespira\b", "respirá"),
        (r"\bparate\b", "parate"),
        (r"\bdecime\b", "decime"),
    ]
    for pat, rep in reemplazos_voseo:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # 2. Aperturas coloquiales enfáticas (técnica de Prueba 3: ¡Mirá!,, ¡Che!,, etc.)
    t = re.sub(r"^(Che|Mirá|Atento)\s*,\s*", r"¡\1!, ", t, flags=re.IGNORECASE)
    t = re.sub(r"([.!?])\s*(Che|Mirá)\s*,\s*", r"\1 ¡\2!, ", t, flags=re.IGNORECASE)

    # 3. Cierres coloquiales vivos
    t = re.sub(r"¿(dale|sí|te parece)\?\s*$", r"¡¿\1?!", t, flags=re.IGNORECASE)

    # 4. Comas de apoyo rítmico en conectores clave
    t = re.sub(r"\s+([,.:;?!])", r"\1", t)
    t = re.sub(r",\s*,+", ", ", t)
    t = re.sub(r",\s*\.", ".", t)
    return t.strip()


class SintetizadorVozAdaptativo:
    """Modula la onda acústica del robot en WPM, decibeles, tono F0 (Hz) y timbre espectral."""

    def __init__(self, habilitado: bool = True):
        self.habilitado = habilitado
        self._lock = threading.Lock()

    @staticmethod
    def enriquecer_texto_prosodico(texto: str) -> str:
        return enriquecer_texto_prosodico(texto)

    @staticmethod
    def db_a_ganancia(volumen_db: float, base: float = 0.80) -> float:
        """Convierte un ajuste en decibeles (-6 dB a +4 dB) a volumen lineal [0.15, 1.0]."""
        ganancia = base * (10.0 ** (volumen_db / 20.0))
        return float(max(0.15, min(1.0, ganancia)))

    @staticmethod
    def segmentar_frases(texto: str) -> list[str]:
        """Divide la respuesta en unidades respiratorias para aplicar temporalización."""
        partes = [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\.\.\.\s*", texto) if p.strip()]
        return partes if partes else [texto.strip()]

    @staticmethod
    def aplicar_dsp_estudio(onda_int16: np.ndarray, sample_rate: int) -> np.ndarray:
        """Aplica presencia de pecho, suavizado de sibilancias y micro-reverberación física."""
        if onda_int16.size == 0:
            return onda_int16
        try:
            from scipy.signal import butter, sosfilt
            x = onda_int16.astype(np.float32) / 32768.0
            nyq = 0.5 * sample_rate

            # 1. De-essing: filtro low-pass suave para apagar sibilancias digitales (>6800 Hz)
            if nyq > 6800:
                sos_lp = butter(2, 6800.0 / nyq, btype="low", output="sos")
                x = sosfilt(sos_lp, x)

            # 2. Resonancia torácica: realce cálido en banda de pecho (200 Hz - 450 Hz)
            if nyq > 450:
                sos_band = butter(2, [200.0 / nyq, 450.0 / nyq], btype="band", output="sos")
                cuerpo = sosfilt(sos_band, x)
                x = x + 0.30 * cuerpo

            # 3. Micro-reverberación de sala física (early reflections a 18ms, 31ms, 46ms)
            delays_ms = [18, 31, 46]
            gains = [0.12, 0.08, 0.04]
            reverb = np.zeros_like(x)
            for d_ms, g in zip(delays_ms, gains):
                d_samples = int(sample_rate * (d_ms / 1000.0))
                if len(x) > d_samples:
                    delayed = np.pad(x[:-d_samples], (d_samples, 0))
                    reverb += g * delayed
            x = x + reverb

            pico = float(np.max(np.abs(x)))
            if pico > 0.01:
                x = (x / pico) * 0.94
            return (x * 32767.0).astype(np.int16)
        except Exception:
            return onda_int16

    @staticmethod
    def modular_onda_dsp(
        onda_int16: np.ndarray,
        sample_rate: int,
        prosodia: PerfilProsodico,
    ) -> tuple[np.ndarray, int]:
        """Aplica Pitch Shifting real (tono_hz), filtrado espectral Butterworth (timbre) y ganancia dB."""
        if onda_int16.size == 0:
            return onda_int16, sample_rate

        x = onda_int16.astype(np.float64)
        if x.ndim > 1:
            x = x.mean(axis=1)
        x /= 32768.0

        # 1. Desplazamiento real de F0 (Pitch Shift en Hz respecto a base 160 Hz)
        ratio_pitch = float(np.clip((160.0 + float(prosodia.tono_hz)) / 160.0, 0.84, 1.20))
        if abs(ratio_pitch - 1.0) > 0.01 and x.size > 64:
            nuevo_largo = max(64, int(round(x.size / ratio_pitch)))
            idx_orig = np.linspace(0.0, 1.0, x.size)
            idx_nuevo = np.linspace(0.0, 1.0, nuevo_largo)
            x = np.interp(idx_nuevo, idx_orig, x)

        # 2. Filtrado espectral de Timbre mediante filtros digitales Butterworth (scipy.signal)
        try:
            from scipy.signal import butter, sosfilt
            nyq = 0.5 * sample_rate
            timbre = getattr(prosodia, "timbre", "neutro_templado")
            if timbre == "calido_suave" and nyq > 2600:
                # Suaviza agudos (>2400 Hz) para dar calidez y calma en ansiedad/tristeza
                sos = butter(2, 2400.0 / nyq, btype="low", output="sos")
                x = 0.78 * sosfilt(sos, x) + 0.22 * x
            elif timbre == "brillante_claro" and nyq > 2200:
                # Realza armónicos superiores (>1500 Hz) para dar brillo y energía en alegría
                sos = butter(2, 1500.0 / nyq, btype="high", output="sos")
                x = x + 0.48 * sosfilt(sos, x)
            elif timbre == "firme_templado" and nyq > 3400:
                # Centra la energía en banda media vocal [160 Hz - 3200 Hz] para desescalada firme
                sos = butter(2, [160.0 / nyq, 3200.0 / nyq], btype="band", output="sos")
                x = 0.70 * sosfilt(sos, x) + 0.30 * x
        except Exception:
            pass

        # 3. Ganancia acústica según decibeles (volumen_db) con limitador suave
        ganancia = SintetizadorVozAdaptativo.db_a_ganancia(prosodia.volumen_db, base=0.82)
        pico = float(np.max(np.abs(x))) if x.size else 1.0
        if pico > 1e-4:
            x = (x / pico) * ganancia
        x = np.clip(x, -0.98, 0.98)
        return (x * 32767.0).astype(np.int16), sample_rate

    def hablar_sincronizado(
        self,
        texto: str,
        prosodia: PerfilProsodico,
        rostro=None,
        bloqueante: bool = False,
    ) -> Optional[threading.Thread]:
        """Sintetiza la respuesta usando edge-tts (es-AR-TomasNeural) con nueva base ágil,
        acentuación enfática, bloques dinámicos y cadena DSP, con fallback seguro a pyttsx3.
        """
        texto_limpio = texto.strip()
        if not self.habilitado or not texto_limpio:
            return None

        def _tarea_audio():
            with self._lock:
                time.sleep(max(0.0, prosodia.pausa_inicial_s))
                texto_prosodico = enriquecer_texto_prosodico(texto_limpio)

                reproduccion_exitosa = False
                archivos_a_borrar: list[str] = []

                # INTENTO 1: edge-tts (Neuronal Argentino Tomás con nueva base ágil)
                try:
                    import asyncio
                    import edge_tts
                    from scipy.io import wavfile
                    import winsound

                    # Mapeo a la nueva base ágil (+8% velocidad, +3Hz tono)
                    pct_rate = int(round(+8 + ((prosodia.velocidad_wpm - 150) / 150.0) * 35))
                    pct_rate = max(+3, min(+25, pct_rate))
                    val_pitch = int(round(+3 + (prosodia.tono_hz * 0.4)))
                    val_pitch = max(-4, min(+8, val_pitch))
                    val_vol = int(round(prosodia.volumen_db * 3.0))
                    val_vol = max(-25, min(+10, val_vol))

                    # Detección de bloques dinámicos (Contención inicial -> Silencio -> Acción)
                    oraciones = [o.strip() for o in re.split(r"(?<=[.!?])\s+", texto_prosodico) if o.strip()]
                    es_bimodal = len(oraciones) >= 2 and any(
                        w in texto_prosodico.lower() for w in ("vamos", "plan", "primer", "arranquemos", "contame", "¿dale?", "¡¿dale?!")
                    )

                    with tempfile.TemporaryDirectory() as tmpdir:
                        final_wav = os.path.join(tmpdir, "final.wav")
                        if es_bimodal:
                            # Mitad 1: contención suave (-4% vel, -3Hz tono, -12% vol)
                            corte = max(1, len(oraciones) // 2)
                            txt_b1 = " ".join(oraciones[:corte])
                            txt_b2 = " ".join(oraciones[corte:])

                            r_b1 = f"{max(+3, pct_rate - 4):+d}%"
                            p_b1 = f"{max(-3, val_pitch - 3):+d}Hz"
                            v_b1 = f"{val_vol - 12:+d}%"

                            r_b2 = f"{min(+22, pct_rate + 2):+d}%"
                            p_b2 = f"{min(+6, val_pitch + 1):+d}Hz"
                            v_b2 = f"{val_vol:+d}%"

                            mp3_1 = os.path.join(tmpdir, "b1.mp3")
                            mp3_2 = os.path.join(tmpdir, "b2.mp3")
                            wav_1 = os.path.join(tmpdir, "b1.wav")
                            wav_2 = os.path.join(tmpdir, "b2.wav")

                            async def _gen_bloques():
                                c1 = edge_tts.Communicate(txt_b1, "es-AR-TomasNeural", rate=r_b1, pitch=p_b1, volume=v_b1)
                                c2 = edge_tts.Communicate(txt_b2, "es-AR-TomasNeural", rate=r_b2, pitch=p_b2, volume=v_b2)
                                await c1.save(mp3_1)
                                await c2.save(mp3_2)

                            asyncio.run(_gen_bloques())

                            cmd1 = ["ffmpeg", "-y", "-i", mp3_1, "-ac", "1", "-ar", "24000", wav_1]
                            cmd2 = ["ffmpeg", "-y", "-i", mp3_2, "-ac", "1", "-ar", "24000", wav_2]
                            subprocess.run(cmd1, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                            sr, d1 = wavfile.read(wav_1)
                            _, d2 = wavfile.read(wav_2)
                            silencio = np.zeros(int(sr * 0.42), dtype=np.int16)
                            data_pcm = np.concatenate([d1, silencio, d2])
                        else:
                            r_str = f"{pct_rate:+d}%"
                            p_str = f"{val_pitch:+d}Hz"
                            v_str = f"{val_vol:+d}%"
                            mp3_u = os.path.join(tmpdir, "unit.mp3")
                            wav_u = os.path.join(tmpdir, "unit.wav")

                            async def _gen_unit():
                                c = edge_tts.Communicate(texto_prosodico, "es-AR-TomasNeural", rate=r_str, pitch=p_str, volume=v_str)
                                await c.save(mp3_u)

                            asyncio.run(_gen_unit())

                            cmd_u = ["ffmpeg", "-y", "-i", mp3_u, "-ac", "1", "-ar", "24000", wav_u]
                            subprocess.run(cmd_u, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            sr, data_pcm = wavfile.read(wav_u)

                        # Aplicar cadena DSP de estudio (pecho + de-essing + micro-reverberación)
                        data_final = SintetizadorVozAdaptativo.aplicar_dsp_estudio(data_pcm, sr)

                        # Modulación espectral de timbre según prosodia
                        data_mod, sr_mod = SintetizadorVozAdaptativo.modular_onda_dsp(data_final, sr, prosodia)
                        wavfile.write(final_wav, sr_mod, data_mod)

                        if rostro is not None:
                            rostro.set_hablando(True, subtitulo=texto_limpio)
                        try:
                            winsound.PlaySound(final_wav, winsound.SND_FILENAME)
                            reproduccion_exitosa = True
                        finally:
                            if rostro is not None:
                                rostro.set_hablando(False)
                except Exception:
                    reproduccion_exitosa = False

                # INTENTO 2: Fallback offline transparente a pyttsx3 si edge-tts no pudo emitir audio
                if not reproduccion_exitosa:
                    fd_raw, ruta_raw = tempfile.mkstemp(suffix="_raw.wav")
                    os.close(fd_raw)
                    fd_mod, ruta_mod = tempfile.mkstemp(suffix="_dsp.wav")
                    os.close(fd_mod)
                    archivos_a_borrar.extend([ruta_raw, ruta_mod])

                    try:
                        import pyttsx3
                        from scipy.io import wavfile
                        import winsound

                        volumen_lineal = self.db_a_ganancia(prosodia.volumen_db)
                        ratio_pitch = float(np.clip((160.0 + float(prosodia.tono_hz)) / 160.0, 0.84, 1.20))
                        rate_compensado = int(round(prosodia.velocidad_wpm / ratio_pitch))

                        engine = pyttsx3.init()
                        for v in engine.getProperty("voices") or []:
                            vid = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                            if any(tag in vid for tag in ("spanish", "espanol", "español", "es-", "es_", "helena", "sabina", "pablo")):
                                engine.setProperty("voice", v.id)
                                break
                        engine.setProperty("rate", rate_compensado)
                        engine.setProperty("volume", volumen_lineal)

                        engine.save_to_file(texto_limpio, ruta_raw)
                        engine.runAndWait()

                        if os.path.exists(ruta_raw) and os.path.getsize(ruta_raw) > 100:
                            sr, data = wavfile.read(ruta_raw)
                            data_mod, sr_mod = self.modular_onda_dsp(data, sr, prosodia)
                            wavfile.write(ruta_mod, sr_mod, data_mod)

                            if rostro is not None:
                                rostro.set_hablando(True, subtitulo=texto_limpio)
                            try:
                                winsound.PlaySound(ruta_mod, winsound.SND_FILENAME)
                                reproduccion_exitosa = True
                            finally:
                                if rostro is not None:
                                    rostro.set_hablando(False)
                        else:
                            if rostro is not None:
                                rostro.set_hablando(True, subtitulo=texto_limpio)
                            try:
                                engine.setProperty("rate", int(prosodia.velocidad_wpm))
                                engine.say(texto_limpio)
                                engine.runAndWait()
                                reproduccion_exitosa = True
                            finally:
                                if rostro is not None:
                                    rostro.set_hablando(False)
                    except Exception:
                        reproduccion_exitosa = False

                # Limpieza de archivos temporales
                for r_tmp in archivos_a_borrar:
                    try:
                        if os.path.exists(r_tmp):
                            os.remove(r_tmp)
                    except OSError:
                        pass

                # Fallback visual de seguridad por duración estimada si el audio no funcionó
                if not reproduccion_exitosa:
                    if rostro is not None:
                        rostro.set_hablando(True, subtitulo=texto_limpio)
                    palabras = max(1, len(texto_limpio.split()))
                    dur = (palabras / max(80, prosodia.velocidad_wpm)) * 60.0
                    time.sleep(min(6.0, dur))
                    if rostro is not None:
                        rostro.set_hablando(False)

        if bloqueante:
            _tarea_audio()
            return None
        hilo = threading.Thread(target=_tarea_audio, daemon=True)
        hilo.start()
        return hilo

