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


@dataclass
class EventoMicroExpresion:
    """Micro-expresión facial programada en la línea de tiempo de habla."""
    t_inicio: float
    duracion: float
    forma_ojo: str
    glifo: Optional[str] = None
    apertura: Optional[float] = None
    inclinacion: Optional[float] = None


class PlanificadorCoreografiaFacial:
    """Planificador prosódico-lingüístico de micro-expresiones faciales en tiempo real.
    
    Analiza la estructura discursiva, signos de puntuación (¡!, ¿?, ,, .) y marcadores
    emocionales para generar una línea de tiempo dinámica de micro-gestos y glifos,
    evitando la rigidez de una máscara facial estática durante el habla de Ottoman.
    """

    @classmethod
    def planificar(
        cls,
        texto: str,
        emocion_base: str = "NEUTRO",
        prosodia: Optional[PerfilProsodico] = None,
    ) -> list[EventoMicroExpresion]:
        if not texto or not texto.strip():
            return []

        wpm = prosodia.velocidad_wpm if prosodia else 150
        # Velocidad en palabras por segundo (típicamente 2.5 palabras/s a 150 WPM)
        wps = max(1.4, wpm / 60.0)

        # Segmentar en oraciones manteniendo puntuación
        oraciones_crudas = [f.strip() for f in re.split(r"(?<=[.?!])\s+", texto.strip()) if f.strip()]
        bloques: list[str] = []
        for ora in oraciones_crudas:
            if "," in ora:
                sub = [s.strip() for s in ora.split(",") if s.strip()]
                for s in sub:
                    bloques.append(s)
            else:
                bloques.append(ora)

        if not bloques:
            bloques = [texto.strip()]

        eventos: list[EventoMicroExpresion] = []
        t_acumulado = 0.0

        for i, bloque in enumerate(bloques):
            txt_min = bloque.lower().strip()
            palabras = [p for p in re.findall(r"\w+", txt_min) if p]
            num_palabras = max(1, len(palabras))
            duracion_estimada = max(0.85, round(num_palabras / wps, 2))

            forma = "capsula"
            glifo = None
            apertura = None
            inclinacion = None

            # 1. Detección de exclamación o énfasis heroico / alerta
            if "¡" in bloque or "!" in bloque or any(w in txt_min for w in ("vamos", "excelente", "felicitaciones", "genial", "alegría")):
                if any(w in txt_min for w in ("cuidado", "atención", "ojo", "alto", "freno", "peligro", "emergencia", "bloqueo")):
                    glifo = "!"
                    forma = "diagonal_enojo"
                    inclinacion = 18.0
                    apertura = 1.10
                elif any(w in txt_min for w in ("eureka", "idea", "logramos", "brillante", "excelente", "super")):
                    glifo = "!"
                    forma = "chispa_estrella"
                    apertura = 1.12
                else:
                    glifo = "!"
                    forma = "arco_feliz"
                    apertura = 1.08

            # 2. Detección de interrogación / duda reflexiva
            elif "¿" in bloque or "?" in bloque or any(w in txt_min for w in ("cómo", "qué", "cuál", "quién", "dónde", "probaste", "pensás", "parece")):
                glifo = "?"
                forma = "entrecerrado_enfoque"
                apertura = 0.88

            # 3. Marcadores de co-regulación, respiración y calma
            elif any(w in txt_min for w in ("tranquilo", "calma", "despacio", "inhalá", "exhalá", "respiremos", "paz", "serenidad", "relajá")):
                forma = "suave_calma"
                apertura = 0.74

            # 4. Marcadores de concentración, análisis y foco cognitivo
            elif any(w in txt_min for w in ("pensemos", "analicemos", "plan", "primer paso", "opciones", "enfoque", "estrategia", "revisemos")):
                forma = "entrecerrado_enfoque"
                apertura = 0.82

            # 5. Marcadores de empatía cálida y contención
            elif any(w in txt_min for w in ("entiendo", "difícil", "cuesta", "duro", "pesar", "triste", "estoy con vos", "abrazo")):
                forma = "caido_triste"
                inclinacion = -14.0
                apertura = 0.80

            # 6. Marcadores de asombro y descubrimiento
            elif any(w in txt_min for w in ("guau", "sorprendente", "mirá", "increíble", "asombroso")):
                forma = "ojo_circular_asombro"
                apertura = 1.15

            # 7. Dispersión natural según la emoción dominante del coach
            else:
                if emocion_base == "MOTIVACION_ALEGRIA":
                    forma = "arco_feliz"
                    apertura = 1.05
                elif emocion_base == "ANSIEDAD_ESTRES":
                    forma = "suave_calma"
                    apertura = 0.76
                elif emocion_base == "TRISTEZA_DESANIMO":
                    forma = "caido_triste"
                    inclinacion = -12.0
                    apertura = 0.82
                elif emocion_base == "ENOJO_FRUSTRACION":
                    forma = "diagonal_enojo"
                    inclinacion = 14.0
                    apertura = 0.86
                elif emocion_base == "DUDA_INSEGURIDAD":
                    forma = "entrecerrado_enfoque"
                    apertura = 0.88
                else:
                    forma = "capsula"
                    apertura = 0.92

            eventos.append(
                EventoMicroExpresion(
                    t_inicio=round(t_acumulado, 2),
                    duracion=duracion_estimada,
                    forma_ojo=forma,
                    glifo=glifo,
                    apertura=apertura,
                    inclinacion=inclinacion,
                )
            )

            # Si el bloque empezó con glifo '!' o '?', y dura más de 1.1s, desvanecerlo suavemente a la forma ocular secundaria
            if glifo in ("!", "?") and duracion_estimada > 1.1:
                dur_glifo = 0.85
                dur_resto = round(duracion_estimada - dur_glifo, 2)
                eventos[-1].duracion = dur_glifo
                eventos.append(
                    EventoMicroExpresion(
                        t_inicio=round(t_acumulado + dur_glifo, 2),
                        duracion=dur_resto,
                        forma_ojo="arco_feliz" if glifo == "!" else "entrecerrado_enfoque",
                        glifo=None,
                        apertura=apertura,
                        inclinacion=inclinacion,
                    )
                )

            # Acumular tiempo para el próximo bloque más una micro-pausa
            t_acumulado += duracion_estimada + 0.15

        return eventos


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
                "D_apertura_calida": {
                    # Apertura amplia cordial al frente y leve asentimiento
                    "waist_pitch": -0.04,
                    "waist_yaw": 0.0,
                    "waist_roll": 0.0,
                    "left_shoulder_pitch": 0.02,
                    "right_shoulder_pitch": 0.02,
                    "left_shoulder_roll": 0.42,
                    "right_shoulder_roll": -0.42,
                    "left_elbow": 0.52,
                    "right_elbow": 0.52,
                    "left_wrist_roll": -0.40,
                    "right_wrist_roll": 0.40,
                    "left_knee": 0.38,
                    "right_knee": 0.38,
                    "left_hip_pitch": -0.19,
                    "right_hip_pitch": -0.19,
                    "left_ankle_pitch": -0.19,
                    "right_ankle_pitch": -0.19,
                    **_mano_declamatoria("left"),
                    **_mano_declamatoria("right"),
                },
            },
            "variantes": [
                # Variante 0: Victoria y Pulgar Triunfal (Alta energía)
                [
                    {
                        "waist_pitch": -0.10, "left_shoulder_pitch": -0.65, "right_shoulder_pitch": -0.65,
                        "left_shoulder_roll": 0.70, "right_shoulder_roll": -0.70, "left_elbow": 0.45, "right_elbow": 0.45,
                        "left_wrist_roll": 0.35, "right_wrist_roll": -0.35, "left_knee": 0.36, "right_knee": 0.36,
                        "left_hip_pitch": -0.18, "right_hip_pitch": -0.18, "left_ankle_pitch": -0.18, "right_ankle_pitch": -0.18,
                        **_mano_declamatoria("left"), **_mano_declamatoria("right"),
                    },
                    {
                        "waist_pitch": -0.06, "left_shoulder_pitch": 0.08, "left_shoulder_roll": 0.35, "left_elbow": 0.85,
                        "left_wrist_roll": -0.80, "right_shoulder_pitch": -0.52, "right_shoulder_roll": -0.22, "right_elbow": 0.88,
                        "right_wrist_roll": 0.0, "left_knee": 0.34, "right_knee": 0.44, "left_hip_pitch": -0.17, "right_hip_pitch": -0.22,
                        "left_ankle_pitch": -0.17, "right_ankle_pitch": -0.22,
                        **_mano_puno_victoria("left"), **_mano_pulgar_arriba("right"),
                    },
                ],
                # Variante 1: Apertura Cálida y Felicitación
                [
                    {
                        "waist_pitch": -0.04, "left_shoulder_pitch": 0.02, "right_shoulder_pitch": 0.02,
                        "left_shoulder_roll": 0.42, "right_shoulder_roll": -0.42, "left_elbow": 0.52, "right_elbow": 0.52,
                        "left_wrist_roll": -0.40, "right_wrist_roll": 0.40, "left_knee": 0.38, "right_knee": 0.38,
                        "left_hip_pitch": -0.19, "right_hip_pitch": -0.19, "left_ankle_pitch": -0.19, "right_ankle_pitch": -0.19,
                        **_mano_declamatoria("left"), **_mano_declamatoria("right"),
                    },
                ],
                # Variante 2: Complicidad y Señalamiento Dinámico
                [
                    {
                        "waist_pitch": 0.04, "waist_yaw": 0.18, "waist_roll": -0.05,
                        "left_shoulder_pitch": 0.38, "left_shoulder_roll": 0.08, "left_elbow": 0.18, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": -0.48, "right_shoulder_roll": -0.18, "right_elbow": 0.38, "right_wrist_pitch": 0.20,
                        "right_wrist_roll": 0.10, "left_knee": 0.50, "right_knee": 0.26, "left_hip_pitch": -0.25, "right_hip_pitch": -0.13,
                        "left_ankle_pitch": -0.25, "right_ankle_pitch": -0.13,
                        **_mano_relajada_organica("left"), **_mano_senalamiento("right"),
                    },
                ],
            ],
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
                "C_acompanamiento_silencioso": {
                    # Manos bajas al frente en bajo vientre, postura empática reflexiva
                    "waist_pitch": 0.14,
                    "waist_roll": 0.0,
                    "waist_yaw": 0.0,
                    "left_shoulder_pitch": 0.32,
                    "right_shoulder_pitch": 0.32,
                    "left_shoulder_roll": 0.12,
                    "right_shoulder_roll": -0.12,
                    "left_elbow": 0.48,
                    "right_elbow": 0.48,
                    "left_wrist_roll": -0.65,
                    "right_wrist_roll": 0.65,
                    "left_wrist_pitch": 0.15,
                    "right_wrist_pitch": 0.15,
                    "left_knee": 0.42,
                    "right_knee": 0.42,
                    "left_hip_pitch": -0.21,
                    "right_hip_pitch": -0.21,
                    "left_ankle_pitch": -0.21,
                    "right_ankle_pitch": -0.21,
                    **_mano_relajada_organica("left"),
                    **_mano_relajada_organica("right"),
                },
            },
            "variantes": [
                # Variante 0: Contención Íntima (Mano al corazón)
                [
                    {
                        "waist_pitch": 0.15, "waist_roll": 0.05, "waist_yaw": 0.04,
                        "left_shoulder_pitch": 0.40, "left_shoulder_roll": 0.06, "left_elbow": 0.16, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": 0.20, "right_shoulder_roll": -0.15, "right_shoulder_yaw": -0.35, "right_elbow": 1.15,
                        "right_wrist_pitch": 0.35, "right_wrist_roll": -0.20, "left_knee": 0.40, "right_knee": 0.40,
                        "left_hip_pitch": -0.20, "right_hip_pitch": -0.20, "left_ankle_pitch": -0.20, "right_ankle_pitch": -0.20,
                        **_mano_relajada_organica("left"), **_mano_empatica_pecho("right"),
                    },
                ],
                # Variante 1: Acogida y Apoyo en Dos Tiempos
                [
                    {
                        "waist_pitch": 0.15, "waist_roll": 0.04, "waist_yaw": 0.04,
                        "left_shoulder_pitch": 0.40, "left_shoulder_roll": 0.06, "left_elbow": 0.16, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": 0.20, "right_shoulder_roll": -0.15, "right_elbow": 1.15,
                        "right_wrist_pitch": 0.35, "right_wrist_roll": -0.20, "left_knee": 0.40, "right_knee": 0.40,
                        "left_hip_pitch": -0.20, "right_hip_pitch": -0.20, "left_ankle_pitch": -0.20, "right_ankle_pitch": -0.20,
                        **_mano_relajada_organica("left"), **_mano_empatica_pecho("right"),
                    },
                    {
                        "waist_pitch": 0.14, "waist_roll": 0.03, "waist_yaw": -0.05,
                        "left_shoulder_pitch": 0.40, "left_shoulder_roll": 0.06, "left_elbow": 0.16, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": -0.10, "right_shoulder_roll": -0.20, "right_elbow": 0.45,
                        "right_wrist_pitch": 0.15, "right_wrist_roll": 0.20, "left_knee": 0.44, "right_knee": 0.34,
                        "left_hip_pitch": -0.22, "right_hip_pitch": -0.17, "left_ankle_pitch": -0.22, "right_ankle_pitch": -0.17,
                        **_mano_relajada_organica("left"), **_mano_declamatoria("right"),
                    },
                ],
                # Variante 2: Acompañamiento Silencioso y Reflexivo
                [
                    {
                        "waist_pitch": 0.14, "waist_roll": 0.0, "waist_yaw": 0.0,
                        "left_shoulder_pitch": 0.32, "right_shoulder_pitch": 0.32, "left_shoulder_roll": 0.12, "right_shoulder_roll": -0.12,
                        "left_elbow": 0.48, "right_elbow": 0.48, "left_wrist_roll": -0.65, "right_wrist_roll": 0.65,
                        "left_wrist_pitch": 0.15, "right_wrist_pitch": 0.15, "left_knee": 0.42, "right_knee": 0.42,
                        "left_hip_pitch": -0.21, "right_hip_pitch": -0.21, "left_ankle_pitch": -0.21, "right_ankle_pitch": -0.21,
                        **_mano_relajada_organica("left"), **_mano_relajada_organica("right"),
                    },
                ],
            ],
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
                "C_canalizar_a_tierra": {
                    # Brazo derecho extendido en diagonal baja indicando espacio neutro ("bajemos a tierra")
                    "waist_pitch": -0.02,
                    "waist_roll": 0.03,
                    "waist_yaw": -0.06,
                    "left_shoulder_pitch": 0.38,
                    "left_shoulder_roll": 0.08,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,
                    "right_shoulder_pitch": 0.12,
                    "right_shoulder_roll": -0.20,
                    "right_elbow": 0.35,
                    "right_wrist_pitch": -0.20,
                    "right_wrist_roll": 0.25,
                    "left_knee": 0.46,
                    "right_knee": 0.46,
                    "left_hip_pitch": -0.23,
                    "right_hip_pitch": -0.23,
                    "left_ankle_pitch": -0.23,
                    "right_ankle_pitch": -0.23,
                    **_mano_relajada_organica("left"),
                    **_mano_pacificador("right"),
                },
            },
            "variantes": [
                # Variante 0: Barrera Pacificadora Frontal
                [
                    {
                        "waist_pitch": -0.04, "waist_roll": 0.0, "waist_yaw": 0.0,
                        "left_shoulder_pitch": 0.18, "right_shoulder_pitch": 0.18, "left_shoulder_roll": 0.30, "right_shoulder_roll": -0.30,
                        "left_elbow": 0.58, "right_elbow": 0.58, "left_wrist_pitch": -0.30, "right_wrist_pitch": -0.30,
                        "left_wrist_roll": -0.40, "right_wrist_roll": 0.40, "left_knee": 0.52, "right_knee": 0.52,
                        "left_hip_pitch": -0.26, "right_hip_pitch": -0.26, "left_ankle_pitch": -0.26, "right_ankle_pitch": -0.26,
                        **_mano_pacificador("left"), **_mano_pacificador("right"),
                    },
                ],
                # Variante 1: Escucha con Aplomo y Firmeza
                [
                    {
                        "waist_pitch": -0.02, "waist_roll": -0.04, "waist_yaw": 0.08,
                        "left_shoulder_pitch": 0.40, "left_shoulder_roll": 0.06, "left_elbow": 0.16, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": 0.18, "right_shoulder_roll": -0.26, "right_elbow": 0.50, "right_wrist_pitch": -0.25,
                        "right_wrist_roll": 0.30, "left_knee": 0.44, "right_knee": 0.50, "left_hip_pitch": -0.22, "right_hip_pitch": -0.25,
                        "left_ankle_pitch": -0.22, "right_ankle_pitch": -0.25,
                        **_mano_relajada_organica("left"), **_mano_pacificador("right"),
                    },
                ],
                # Variante 2: Canalización a Tierra
                [
                    {
                        "waist_pitch": -0.02, "waist_roll": 0.03, "waist_yaw": -0.06,
                        "left_shoulder_pitch": 0.38, "left_shoulder_roll": 0.08, "left_elbow": 0.16, "left_wrist_roll": -1.25,
                        "right_shoulder_pitch": 0.12, "right_shoulder_roll": -0.20, "right_elbow": 0.35, "right_wrist_pitch": -0.20,
                        "right_wrist_roll": 0.25, "left_knee": 0.46, "right_knee": 0.46, "left_hip_pitch": -0.23, "right_hip_pitch": -0.23,
                        "left_ankle_pitch": -0.23, "right_ankle_pitch": -0.23,
                        **_mano_relajada_organica("left"), **_mano_pacificador("right"),
                    },
                ],
            ],
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
                    # Expansión torácica y elevación vertical (rodillas se estiran ligeramente a 0.22 rad)
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
                "C_anclaje_a_tierra": {
                    # Ambas manos abiertas descendiendo lentamente hacia el piso marcando contacto con el suelo
                    "waist_pitch": 0.02,
                    "waist_roll": 0.0,
                    "waist_yaw": 0.0,
                    "left_shoulder_pitch": 0.20,
                    "right_shoulder_pitch": 0.20,
                    "left_shoulder_roll": 0.24,
                    "right_shoulder_roll": -0.24,
                    "left_elbow": 0.38,
                    "right_elbow": 0.38,
                    "left_wrist_pitch": -0.20,
                    "right_wrist_pitch": -0.20,
                    "left_wrist_roll": -0.50,
                    "right_wrist_roll": 0.50,
                    "left_knee": 0.42,
                    "right_knee": 0.42,
                    "left_hip_pitch": -0.21,
                    "right_hip_pitch": -0.21,
                    "left_ankle_pitch": -0.21,
                    "right_ankle_pitch": -0.21,
                    **_mano_pacificador("left"),
                    **_mano_pacificador("right"),
                },
                "D_pausa_y_sosiego": {
                    # Mano derecha al esternón/plexo solar, izquierda en pausa serena pidiendo un respiro
                    "waist_pitch": 0.02,
                    "waist_roll": -0.03,
                    "waist_yaw": 0.05,
                    "left_shoulder_pitch": 0.26,
                    "left_shoulder_roll": 0.18,
                    "left_elbow": 0.32,
                    "left_wrist_pitch": -0.15,
                    "left_wrist_roll": -0.60,
                    "right_shoulder_pitch": 0.24,
                    "right_shoulder_roll": -0.12,
                    "right_elbow": 0.95,
                    "right_wrist_pitch": 0.20,
                    "right_wrist_roll": -0.15,
                    "left_knee": 0.38,
                    "right_knee": 0.38,
                    "left_hip_pitch": -0.19,
                    "right_hip_pitch": -0.19,
                    "left_ankle_pitch": -0.19,
                    "right_ankle_pitch": -0.19,
                    **_mano_pacificador("left"),
                    **_mano_empatica_pecho("right"),
                },
            },
            "variantes": [
                # Variante 0: Metrónomo Respiratorio (Inhalación y Exhalación)
                [
                    {
                        "waist_pitch": -0.06, "left_knee": 0.22, "right_knee": 0.22, "left_hip_pitch": -0.11, "right_hip_pitch": -0.11,
                        "left_ankle_pitch": -0.11, "right_ankle_pitch": -0.11, "left_shoulder_pitch": 0.10, "right_shoulder_pitch": 0.10,
                        "left_shoulder_roll": 0.35, "right_shoulder_roll": -0.35, "left_elbow": 0.45, "right_elbow": 0.45,
                        "left_wrist_pitch": 0.18, "right_wrist_pitch": 0.18, "left_wrist_roll": -0.60, "right_wrist_roll": 0.60,
                        **_mano_declamatoria("left"), **_mano_declamatoria("right"),
                    },
                    {
                        "waist_pitch": 0.03, "left_knee": 0.44, "right_knee": 0.44, "left_hip_pitch": -0.22, "right_hip_pitch": -0.22,
                        "left_ankle_pitch": -0.22, "right_ankle_pitch": -0.22, "left_shoulder_pitch": 0.40, "right_shoulder_pitch": 0.40,
                        "left_shoulder_roll": 0.06, "right_shoulder_roll": -0.06, "left_elbow": 0.16, "right_elbow": 0.16,
                        "left_wrist_pitch": 0.0, "right_wrist_pitch": 0.0, "left_wrist_roll": -1.25, "right_wrist_roll": 1.25,
                        **_mano_relajada_organica("left"), **_mano_relajada_organica("right"),
                    },
                ],
                # Variante 1: Anclaje a Tierra / Grounding
                [
                    {
                        "waist_pitch": 0.02, "waist_roll": 0.0, "waist_yaw": 0.0, "left_shoulder_pitch": 0.20, "right_shoulder_pitch": 0.20,
                        "left_shoulder_roll": 0.24, "right_shoulder_roll": -0.24, "left_elbow": 0.38, "right_elbow": 0.38,
                        "left_wrist_pitch": -0.20, "right_wrist_pitch": -0.20, "left_wrist_roll": -0.50, "right_wrist_roll": 0.50,
                        "left_knee": 0.42, "right_knee": 0.42, "left_hip_pitch": -0.21, "right_hip_pitch": -0.21,
                        "left_ankle_pitch": -0.21, "right_ankle_pitch": -0.21,
                        **_mano_pacificador("left"), **_mano_pacificador("right"),
                    },
                ],
                # Variante 2: Pausa y Sosiego
                [
                    {
                        "waist_pitch": 0.02, "waist_roll": -0.03, "waist_yaw": 0.05, "left_shoulder_pitch": 0.26, "left_shoulder_roll": 0.18,
                        "left_elbow": 0.32, "left_wrist_pitch": -0.15, "left_wrist_roll": -0.60, "right_shoulder_pitch": 0.24,
                        "right_shoulder_roll": -0.12, "right_elbow": 0.95, "right_wrist_pitch": 0.20, "right_wrist_roll": -0.15,
                        "left_knee": 0.38, "right_knee": 0.38, "left_hip_pitch": -0.19, "right_hip_pitch": -0.19,
                        "left_ankle_pitch": -0.19, "right_ankle_pitch": -0.19,
                        **_mano_pacificador("left"), **_mano_empatica_pecho("right"),
                    },
                ],
            ],
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
                "C_indagacion_reflexiva": {
                    # Mano derecha en postura de reflexión socrática, izquierda al muslo
                    "waist_pitch": 0.04,
                    "waist_roll": 0.02,
                    "waist_yaw": 0.05,
                    "left_shoulder_pitch": 0.38,
                    "left_shoulder_roll": 0.06,
                    "left_elbow": 0.16,
                    "left_wrist_roll": -1.25,
                    "right_shoulder_pitch": 0.15,
                    "right_shoulder_roll": -0.14,
                    "right_elbow": 0.85,
                    "right_wrist_pitch": 0.25,
                    "right_wrist_roll": 0.10,
                    "left_knee": 0.38,
                    "right_knee": 0.34,
                    "left_hip_pitch": -0.19,
                    "right_hip_pitch": -0.17,
                    "left_ankle_pitch": -0.19,
                    "right_ankle_pitch": -0.17,
                    **_mano_relajada_organica("left"),
                    **_mano_empatica_pecho("right"),
                },
            },
            "variantes": [
                # Variante 0: Sopesar Opciones en Balanza
                [
                    {
                        "waist_yaw": 0.15, "waist_roll": -0.04, "left_shoulder_pitch": 0.12, "left_shoulder_roll": 0.32,
                        "left_elbow": 0.50, "left_wrist_roll": -0.30, "right_shoulder_pitch": 0.40, "right_shoulder_roll": -0.06,
                        "right_elbow": 0.16, "right_wrist_roll": 1.25, "left_knee": 0.44, "right_knee": 0.28,
                        "left_hip_pitch": -0.22, "right_hip_pitch": -0.14, "left_ankle_pitch": -0.22, "right_ankle_pitch": -0.14,
                        **_mano_declamatoria("left"), **_mano_relajada_organica("right"),
                    },
                    {
                        "waist_yaw": -0.15, "waist_roll": 0.04, "right_shoulder_pitch": 0.12, "right_shoulder_roll": -0.32,
                        "right_elbow": 0.50, "right_wrist_roll": 0.30, "left_shoulder_pitch": 0.40, "left_shoulder_roll": 0.06,
                        "left_elbow": 0.16, "left_wrist_roll": -1.25, "left_knee": 0.28, "right_knee": 0.44,
                        "left_hip_pitch": -0.14, "right_hip_pitch": -0.22, "left_ankle_pitch": -0.14, "right_ankle_pitch": -0.22,
                        **_mano_relajada_organica("left"), **_mano_declamatoria("right"),
                    },
                ],
                # Variante 1: Indagación Reflexiva Socrática
                [
                    {
                        "waist_pitch": 0.04, "waist_roll": 0.02, "waist_yaw": 0.05, "left_shoulder_pitch": 0.38,
                        "left_shoulder_roll": 0.06, "left_elbow": 0.16, "left_wrist_roll": -1.25, "right_shoulder_pitch": 0.15,
                        "right_shoulder_roll": -0.14, "right_elbow": 0.85, "right_wrist_pitch": 0.25, "right_wrist_roll": 0.10,
                        "left_knee": 0.38, "right_knee": 0.34, "left_hip_pitch": -0.19, "right_hip_pitch": -0.17,
                        "left_ankle_pitch": -0.19, "right_ankle_pitch": -0.17,
                        **_mano_relajada_organica("left"), **_mano_empatica_pecho("right"),
                    },
                ],
            ],
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
                "C_escucha_abierta": {
                    "waist_pitch": 0.01,
                    "waist_roll": 0.0,
                    "waist_yaw": 0.0,
                    "left_shoulder_pitch": 0.28,
                    "right_shoulder_pitch": 0.28,
                    "left_shoulder_roll": 0.14,
                    "right_shoulder_roll": -0.14,
                    "left_elbow": 0.30,
                    "right_elbow": 0.30,
                    "left_wrist_roll": -0.75,
                    "right_wrist_roll": 0.75,
                    "left_knee": 0.34,
                    "right_knee": 0.34,
                    "left_hip_pitch": -0.17,
                    "right_hip_pitch": -0.17,
                    "left_ankle_pitch": -0.17,
                    "right_ankle_pitch": -0.17,
                    **_mano_relajada_organica("left"),
                    **_mano_relajada_organica("right"),
                },
            },
            "variantes": [
                # Variante 0: Giro de Atención Receptiva Izquierda
                [
                    {
                        "waist_pitch": 0.02, "waist_yaw": 0.08, "left_shoulder_pitch": 0.24, "left_shoulder_roll": 0.20,
                        "left_elbow": 0.38, "left_wrist_roll": -0.50, "right_shoulder_pitch": 0.38, "right_elbow": 0.16,
                        "right_wrist_roll": 1.25, "left_knee": 0.40, "right_knee": 0.28, "left_hip_pitch": -0.20,
                        "right_hip_pitch": -0.14, "left_ankle_pitch": -0.20, "right_ankle_pitch": -0.14,
                        **_mano_declamatoria("left"), **_mano_relajada_organica("right"),
                    },
                ],
                # Variante 1: Giro de Atención Receptiva Derecha
                [
                    {
                        "waist_pitch": 0.02, "waist_yaw": -0.08, "right_shoulder_pitch": 0.24, "right_shoulder_roll": -0.20,
                        "right_elbow": 0.38, "right_wrist_roll": 0.50, "left_shoulder_pitch": 0.38, "left_elbow": 0.16,
                        "left_wrist_roll": -1.25, "left_knee": 0.28, "right_knee": 0.40, "left_hip_pitch": -0.14,
                        "right_hip_pitch": -0.20, "left_ankle_pitch": -0.14, "right_ankle_pitch": -0.20,
                        **_mano_relajada_organica("left"), **_mano_declamatoria("right"),
                    },
                ],
                # Variante 2: Escucha Abierta y Atenta
                [
                    {
                        "waist_pitch": 0.01, "waist_roll": 0.0, "waist_yaw": 0.0, "left_shoulder_pitch": 0.28,
                        "right_shoulder_pitch": 0.28, "left_shoulder_roll": 0.14, "right_shoulder_roll": -0.14,
                        "left_elbow": 0.30, "right_elbow": 0.30, "left_wrist_roll": -0.75, "right_wrist_roll": 0.75,
                        "left_knee": 0.34, "right_knee": 0.34, "left_hip_pitch": -0.17, "right_hip_pitch": -0.17,
                        "left_ankle_pitch": -0.17, "right_ankle_pitch": -0.17,
                        **_mano_relajada_organica("left"), **_mano_relajada_organica("right"),
                    },
                ],
            ],
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
            "variantes": [
                [
                    {
                        "waist_pitch": 0.04, "left_shoulder_pitch": 0.34, "right_shoulder_pitch": 0.34,
                        "left_elbow": 0.22, "right_elbow": 0.22, "left_wrist_roll": -1.20, "right_wrist_roll": 1.20,
                        "left_knee": 0.36, "right_knee": 0.36, "left_hip_pitch": -0.18, "right_hip_pitch": -0.18,
                        "left_ankle_pitch": -0.18, "right_ankle_pitch": -0.18,
                        **_mano_relajada_organica("left"), **_mano_relajada_organica("right"),
                    },
                ],
            ],
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

    _rotador_variantes: dict[str, int] = {}

    @classmethod
    def obtener_coreografia(
        cls,
        emocion: str,
        valencia: Optional[float] = None,
        arousal: Optional[float] = None,
        intensidad: float = 0.6,
        variante_idx: Optional[int] = None,
    ) -> tuple[list[dict[str, float]], float, float, float]:
        """Devuelve (secuencia_poses, duracion_step_s, proxemica_m, vel_proxemica_ms)."""
        base = _pose_neutra_suave()

        # Obtener datos del repertorio animatrónico
        rol = RepertorioAnimatronicoG1.ROLES.get(
            emocion, RepertorioAnimatronicoG1.ROLES["NEUTRO"]
        )

        variantes = rol.get("variantes")
        if not variantes:
            variantes = [list(rol.get("ademanes", {}).values())]

        if variante_idx is not None:
            v_idx = variante_idx % len(variantes)
        elif intensidad > 0.75:
            # Alta intensidad: variante 0 (más enérgica / expansiva)
            v_idx = 0
        else:
            # Rotación sin repetición inmediata
            v_idx = cls._rotador_variantes.get(emocion, 0) % len(variantes)
            cls._rotador_variantes[emocion] = (v_idx + 1) % len(variantes)

        pasos_ademan = variantes[v_idx]
        sec = []
        for ademan_dict in pasos_ademan:
            pose = dict(base)
            pose.update(rol["base"])
            pose.update(ademan_dict)
            if emocion == "MOTIVACION_ALEGRIA" and "C_celebracion_pulgar" in rol.get("ademanes", {}):
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
            # Idle diaphragmatic breathing (0.25 Hz = ~4s) + postural sway orgánico (~6.5s)
            f = fase_tiempo
            f_sway = f * 0.61  # ciclo pendular postural
            mod_torso = 0.038 * math.sin(f)
            mod_l_sh = 0.028 * math.sin(f + 0.25)
            mod_r_sh = 0.028 * math.sin(f + 0.25)
            mod_l_el = 0.022 * math.cos(f)
            mod_r_el = 0.022 * math.cos(f)
            mod_l_wr = 0.040 * math.sin(f + 0.50)
            mod_r_wr = -0.040 * math.sin(f + 0.50)
            dedos_val = float(np.clip(0.05 + 0.04 * (1.0 + math.sin(f)), 0.02, 0.20))
            sway_leg = math.sin(f_sway)
            sway_pelvis_roll = 0.022 * math.sin(f_sway)
            sway_pelvis_yaw = 0.014 * math.cos(f_sway * 0.5)

        pose = {
            "waist_pitch": pitch_base + mod_torso,
            "waist_roll": roll_base + (sway_pelvis_roll if not hablando else 0.0),
            "waist_yaw": yaw_base + (sway_pelvis_yaw if not hablando else 0.0),
            "left_shoulder_pitch": sh_pitch_base + mod_l_sh,
            "right_shoulder_pitch": sh_pitch_base + mod_r_sh,
            "left_shoulder_roll": sh_roll_base - (sway_pelvis_roll * 0.5 if not hablando else 0.0),
            "right_shoulder_roll": -sh_roll_base - (sway_pelvis_roll * 0.5 if not hablando else 0.0),
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

        # Piernas vivas con flexión orgánica visible y contrapposto dinámico
        knee_base = float(np.clip(0.32 + 0.10 * abs(a), 0.22, 0.48))
        leg_sway_amp = (0.042 * sway_leg) if not hablando else 0.0
        knee_l = knee_base + leg_sway_amp
        knee_r = knee_base - leg_sway_amp
        hip_pitch_l = -knee_l * 0.5
        hip_pitch_r = -knee_r * 0.5
        ankle_l = -knee_l * 0.5
        ankle_r = -knee_r * 0.5
        hip_roll_l = float(np.clip(0.02 + 0.03 * v + (0.012 * sway_leg if not hablando else 0.0), -0.06, 0.08))
        hip_roll_r = float(np.clip(-0.02 - 0.03 * v + (0.012 * sway_leg if not hablando else 0.0), -0.08, 0.06))

        pose["left_hip_pitch"] = hip_pitch_l
        pose["right_hip_pitch"] = hip_pitch_r
        pose["left_hip_roll"] = hip_roll_l
        pose["right_hip_roll"] = hip_roll_r
        pose["left_hip_yaw"] = 0.0
        pose["right_hip_yaw"] = 0.0
        pose["left_knee"] = knee_l
        pose["right_knee"] = knee_r
        pose["left_ankle_pitch"] = ankle_l
        pose["right_ankle_pitch"] = ankle_r
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
                "Pará un segundo... Te noto la voz súper acelerada y estás hablando casi sin respirar. Aflojá los hombros un momento conmigo. No intentes resolver todo el proyecto junto; vamos de a un paso. ¿Qué es lo más importante que tenemos que mirar ahora?",
                "Tranqui, frenemos la pelota un minuto. Cuando la cabeza va a mil por hora, todo parece urgente y no es así. Tomá aire lento... y decime: ¿cuál es la primera cosa que podemos cerrar en diez minutos?",
                "Te escucho y noto el apuro que tenés encima. Estás buscando que todo salga perfecto ya mismo, y el perfeccionismo te termina bloqueando. Bajemos la vara un poco hoy: ¿qué parte mínima podemos resolver ahora?",
                "Mirá, no te me aceleres que no ganamos nada corriendo en círculos. Respirá hondo conmigo mientras subo los brazos... y soltá despacio. Ahora sí: ¿por dónde arrancamos para destrabar esto?",
                "Tomate este momento para bajar un cambio. Si intentás abarcar cinco temas a la vez te vas a quemar la cabeza. Elijamos una sola tarea chiquita y la liquidamos juntos. ¿Cuál elegís?",
                "Aflojá un toque. Noto que tenés mucha presión encima, pero el mundo no se acaba hoy. Desarmemos el lío en partes manejables: decime cuál es la traba principal y le buscamos la vuelta.",
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
                "Che, te veo la cara y se nota que tuviste un día pesado. Es normal sentirse sin energía cuando las cosas no salen como esperabas, a todos nos pasa. Hoy date permiso para aflojar un poco, no te castigues tanto. ¿Querés que hagamos una pausa de cinco minutos?",
                "Sé que pesa mucho cuando le metés ganas a algo y no rinde lo que querías. Pero un mal resultado no borra todo lo que sabés hacer. Descansá la cabeza un rato y después lo miramos de nuevo con otra perspectiva, ¿dale?",
                "Te re entiendo, hay días en los que cuesta arrancar y dan ganas de mandar todo a volar. Pero acá me tenés haciéndote el aguante. No tenés que resolver el mundo hoy: hacete una pausa y cuando sientas ganas, damos el primer paso juntos.",
                "Es totalmente humano tener días grises, no tenés que estar siempre con una sonrisa. Tratate con paciencia hoy, como tratarías a un buen amigo. ¿Querés que charlemos un rato de otra cosa para despejar la cabeza?",
                "Lamento que estés pasando por este momento de bajón. No te exijas ser súper productivo ahora mismo; a veces frenar y tomar aire es lo más inteligente. Contame qué pasó si tenés ganas de descargarte.",
                "No te me caigas que esto tiene solución, aunque hoy lo veas todo cuesta arriba. Tomate un descanso merecido, despejate un toque y cuando retomes lo encaramos juntos de forma más simple.",
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
                "Te entiendo totalmente, es para enojarse en serio. Descargá tranquilo, tenés todo el derecho a estar molesto. Pero cuando estés listo, decime bien qué fue lo que falló y vemos cómo lo arreglamos juntos, ¿dale?",
                "Tiene sentido que te dé bronca cuando las cosas se traban de esa manera. Pero no dejemos que la calentura te nuble las ideas. Tomemos aire un instante y decime: ¿qué parte puntual del problema podemos dar vuelta ahora?",
                "Escucho tu frustración y no te voy a decir que te calmes, porque motivos tenés de sobra. Usemos esa energía a tu favor: identifiquemos el nudo del problema y armemos un plan directo para destrabarlo.",
                "Comprendo el disgusto, a cualquiera le pasaría lo mismo en tu lugar. Descargá toda la bronca que haga falta... y después vemos con la cabeza más fría cómo lo resolvemos punto por punto. ¿Por dónde empezamos?",
                "Pará un segundo. La bronca te da mucha fuerza, pero si actuás en caliente podés complicarla más. Frenemos un momento: decime en una frase concreta cuál es el obstáculo principal y le buscamos la vuelta.",
                "Te escucho con total atención. La queja sirve para desahogarse, pero no arregla el problema. Te propongo algo: decime qué depende de nosotros para corregir esto hoy y nos ponemos a trabajar en eso.",
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
                "Estás pensando demasiado cada detalle y eso te termina frenando. No existe una opción perfecta de entrada; lo importante es arrancar y corregir en el camino. Si tuvieras que elegir una ahora mismo sin pensarlo más, ¿por cuál vas?",
                "Es normal dudar cuando algo te importa, pero darle vueltas a la cabeza en círculos no te va a dar más certezas. Hagamos una prueba chica y reversible hoy: ¿cuál sería el primer paso más simple para probar?",
                "A veces el exceso de análisis te deja congelado. Si un amigo viniera con este mismo dilema a pedirte consejo, ¿qué camino le dirías que tome primero? Pensalo por un segundo.",
                "La duda aparece porque querés cuidar el resultado, pero la inacción también es una decisión. Elijamos la opción que más puertas te deje abiertas para ajustar sobre la marcha. ¿Cuál sentís más flexible?",
                "Para bajar la incertidumbre no sirve seguir pensando en abstracto; sirve dar un paso concreto. ¿Qué dato simple te falta hoy para sentirte un poco más seguro y avanzar?",
                "Animate a dar el salto. No necesitás tener todo el mapa resuelto para empezar a caminar, con ver los primeros dos metros alcanza. ¿Cuál es la primera acción concreta que podés hacer hoy?",
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
                "¡Qué bien, te felicito en serio! Me pone muy contento ver que te salió después de meterle tantas ganas. Festejalo hoy, te lo merecés. ¿Qué es lo próximo que tenés ganas de encarar?",
                "¡Excelente noticia! Disfrutá este momento porque es fruto directo de tu esfuerzo y constancia. Guardate bien esta sensación de logro para el próximo desafío. ¡A seguir con todo!",
                "¡Qué buen avance metiste! Me encanta ver esa energía positiva. Reconocer tus propios logros fortalece un montón la confianza. ¿Con qué objetivo seguimos ahora que venís con todo el envión?",
                "¡Buenísimo, felicitaciones! Esas son las noticias que dan gusto escuchar. Aprovechá este envión anímico para dar el siguiente paso con la misma determinación.",
                "¡Brillante lo que conseguiste! Qué satisfacción da cuando el trabajo rinde sus frutos. Tomate un momento para disfrutarlo, que te lo ganaste con creces.",
                "¡Qué momento genial! Mirá hacia atrás un segundo y fijate todo lo que tuviste que remar para llegar hasta acá. ¡Ahora a mantener esa motivación bien arriba!",
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
                "¿Cómo estás? Te veo pensativo. Si estás trabado con algún tema o querés charlar para despejar la cabeza, avisame y lo pensamos juntos. ¿En qué andás hoy?",
                "Acá estoy atento escuchándote. Contame cómo viene tu día o qué tema tenés en mente y le buscamos la vuelta a tu ritmo.",
                "Te escucho con atención. A veces poner las ideas en palabras ayuda a ordenar el panorama. ¿Qué es lo más importante que tenés para hoy?",
                "Claro, te voy siguiendo. Contame un poco más sobre eso y vemos cómo lo encaramos paso a paso.",
                "Entiendo lo que me decís. ¿Qué aspecto de eso sentís que es el que más atención necesita ahora mismo?",
                "Acá me tenés listo para lo que necesites, ya sea charlar de cualquier cosa o probar algún movimiento en el robot. ¿Por dónde querés ir?",
            ],
        ),
    }

    def __init__(self, usar_llm_si_disponible: bool = True, usar_llm_local: bool = False):
        self.usar_llm_si_disponible = usar_llm_si_disponible
        self.usar_llm_local = usar_llm_local
        self.nombre_usuario: Optional[str] = None
        self._contadores_rotacion: dict[str, int] = {}
        self.historial_chat: deque[dict[str, str]] = deque(maxlen=10)
        self._analizador_lexico = AnalizadorLexicoAfectivo()

    @staticmethod
    def _es_rechazo_invalido_llm(texto: str) -> bool:
        """Detecta si el LLM generó una negativa genérica, un rechazo ético absurdo o alucinó identidades."""
        if not texto or not texto.strip():
            return True
        t = texto.lower()
        patrones_rechazo = [
            r"\b(?:no\s+puedo\s+ayudarte|no\s+puedo\s+intervenir|no\s+puedo\s+asistirte|no\s+puedo\s+hacer\s+eso)\b",
            r"\b(?:libre\s+voluntad|libre\s+albedrio|asuntos\s+de\s+libre|situaciones\s+que\s+son\s+de\s+libre)\b",
            r"\b(?:como\s+modelo\s+de\s+lenguaje|como\s+ia|como\s+asistente\s+virtual\s+no\s+tengo)\b",
            r"\b(?:lo\s+siento,\s+pero\s+no\s+puedo|disculpa,\s+pero\s+no\s+puedo|lo\s+siento\s+pero\s+no)\b",
            r"\b(?:no\s+tengo\s+emociones|no\s+puedo\s+sentir)\b",
            r"\b(?:no\s+estoy\s+autorizado|no\s+tengo\s+permitido)\b",
            r"\b(?:descomportate|descomporte)\b",
            r"\b(?:como\s+te\s+llamas\s+tu,\s+ottoman|tu\s+nombre\s+es\s+ottoman|te\s+llamas\s+ottoman)\b",
            # Detección de jerga técnica/robótica de laboratorio en el diálogo:
            r"\b(?:decibel(?:es)?|hercio(?:s)?|hertz|\bhz\b|f0|frecuencia\s+fundamental|wpm|ppm|facs|au\d+)\b",
            r"\b(?:sensores\s+detectan|lectura\s+biom[eé]trica|algoritmo\s+indica|seg[uú]n\s+mis\s+sensores)\b",
        ]
        for p in patrones_rechazo:
            if re.search(p, t):
                return True

        # Si aún queda la palabra 'Ottoman' pero no se está presentando a sí mismo:
        if re.search(r"\bOttoman\b", texto, flags=re.IGNORECASE):
            if not re.search(r"\b(?:soy|me\s+llamo|mi\s+nombre\s+es)\s+Ottoman\b", texto, flags=re.IGNORECASE):
                return True

        return False

    def registrar_turno(self, texto_usuario: str, respuesta_robot: str) -> None:
        """Guarda un intercambio en la memoria conversacional multiturno."""
        if texto_usuario and texto_usuario.strip():
            self.historial_chat.append({"role": "user", "content": texto_usuario.strip()})
        if respuesta_robot and respuesta_robot.strip():
            self.historial_chat.append({"role": "assistant", "content": respuesta_robot.strip()})

    def _responder_conversacion_basica(
        self,
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

        # 0. Registro de nombre del usuario ("me llamo Franco", "mi nombre es Franco", "soy Franco")
        m_nombre = re.search(r"\b(?:me\s+llamo|mi\s+nombre\s+es)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]{2,20})\b", t)
        if not m_nombre:
            m_nombre = re.search(r"^soy\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]{2,20})[!?.]*$", t)
        if m_nombre:
            nom_candidato = m_nombre.group(1).capitalize()
            # Descartar falsos positivos de palabras afectivas o comunes
            if nom_candidato.lower() not in (
                "triste", "bien", "mal", "yo", "ottoman", "robot", "humano", "estudiante", "furioso", "enojado", "cansado"
            ):
                self.nombre_usuario = nom_candidato
                return (
                    "Registro de Nombre de Usuario",
                    "MOTIVACION_ALEGRIA",
                    f"¡Qué hacés, {self.nombre_usuario}! Un gustazo. Ya me lo guardo en la memoria para tenerlo presente. ¿Cómo andás hoy?",
                )

        # 0b. Pregunta por el nombre del usuario ("¿cómo me llamo?", "¿sabés mi nombre?", "¿quién soy?")
        if re.search(r"\b(?:como\s+me\s+llamo|sabes\s+mi\s+nombre|te\s+acordas\s+de\s+mi\s+nombre|quien\s+soy)\b", t):
            if self.nombre_usuario:
                return (
                    "Identidad de Usuario Recordada",
                    "MOTIVACION_ALEGRIA",
                    f"¡Obvio que me acuerdo! Te llamás {self.nombre_usuario}. ¿O me estabas poniendo a prueba para ver si me fallaba la memoria?",
                )
            else:
                return (
                    "Consulta de Identidad Desconocida",
                    "NEUTRO",
                    "Todavía no me dijiste tu nombre, che. ¿Cómo te llamás así ya nos conocemos bien?",
                )

        # 1. Identidad / presentación / apertura de charla ("hablame", "contame", "quién sos", "presentate")
        if re.search(
            r"\b(?:como\s+te\s+llamas|quien\s+sos|que\s+sos|tu\s+nombre|presentate|"
            r"hablame(?:\s+de\s+vos|\s+un\s+poco|\s+de\s+algo)?|contame(?:\s+de\s+vos|\s+algo)?|"
            r"charlame|sobre\s+vos)\b|^hablame$|^charlar$",
            t,
        ):
            prefijo_nom = f"¡Hola {self.nombre_usuario}! " if self.nombre_usuario else "¡Hola! "
            return (
                "Presentación e Identidad Robótica",
                "MOTIVACION_ALEGRIA",
                f"{prefijo_nom}Soy Ottoman, tu compañero y coach acá en UADE. Si querés probar algún movimiento del robot me decís, y si estás medio trabado con algo o querés charlar, acá estoy para darte una mano. ¿Cómo viene tu día?",
            )

        # 2. Capacidades / ayuda / cómo funciona
        if re.search(r"\b(?:que\s+podes\s+hacer|que\s+sabes\s+hacer|para\s+que\s+servis|en\s+que\s+me\s+ayudas|como\s+funciona|que\s+comandos)\b|^ayuda$", t):
            return (
                "Orientación de Capacidades Multimodales",
                "NEUTRO",
                "Puedo darte una mano con dos cosas: si me pedís avanzar, girar o saludar, muevo el cuerpo en el simulador. Y si estás estudiando o con la cabeza medio cansada, charlamos y buscamos la forma de destrabarlo juntos. ¿Por dónde querés arrancar?",
            )

        # 3. Pregunta de cortesía / estado al robot ("¿cómo estás?", "¿qué onda?", "¿todo bien?")
        if re.search(r"\b(?:como\s+estas|como\s+andas|que\s+onda|que\s+tal|como\s+va|como\s+te\s+sentis)\b", t) and not re.search(r"\b(?:bien|mal|triste|ansioso|cansado)\b", t):
            return (
                "Rapport Social y Apertura Empática",
                "MOTIVACION_ALEGRIA",
                "¡Por acá todo de diez! Con toda la energía para darte una mano en lo que necesites. ¿Cómo venís vos hoy con tus cosas?",
            )

        # 4. Usuario responde que está bien / tranquilo ("estoy bien", "todo bien", "bien y vos")
        if estado.emocion_dominante in ("NEUTRO", "MOTIVACION_ALEGRIA") and re.search(
            r"^(?:estoy\s+bien|todo\s+bien|muy\s+bien|bien\s+por\s+suerte|todo\s+tranqui|re\s+bien|barbaro|de\s+diez|joya|bien(?:\s+y\s+vos|\s+gracias)?)[!?.]*$",
            t,
        ):
            return (
                "Sintonía Positiva y Exploración de Metas",
                "MOTIVACION_ALEGRIA",
                "¡Qué bueno escuchar eso! Me alegra que vengas bien. ¿En qué estás trabajando hoy o qué tenés ganas de encarar?",
            )

        # 5. Agradecimientos ("gracias", "muchas gracias", "me sirvió")
        if re.search(r"^(?:gracias|muchas\s+gracias|te\s+agradezco|muy\s+amable|mil\s+gracias|me\s+sirvio)[!?.]*$", t):
            return (
                "Cierre Cálido y Disponibilidad",
                "MOTIVACION_ALEGRIA",
                "¡De nada! Para eso estamos acá. Avisame si querés seguir charlando o si le mandamos a algún movimiento.",
            )

        # 6. Despedidas ("chau", "hasta luego", "nos vemos", "adiós")
        if re.search(r"^(?:chau|adios|hasta\s+luego|nos\s+vemos|hasta\s+manana|me\s+voy\s+yendo)[!?.]*$", t):
            return (
                "Despedida Cordial",
                "MOTIVACION_ALEGRIA",
                "¡Nos vemos! Que termines muy bien el día y muchos éxitos con todo. ¡Cualquier cosa acá me tenés!",
            )

        # 7. Usuario no sabe qué decir / bloqueo reflexivo / momento de silencio
        if re.search(
            r"\b(?:no\s+se\s+que\s+decir(?:te)?|no\s+tengo\s+palabras|me\s+quede\s+en\s+blanco|no\s+se\s+me\s+ocurre)\b|^no\s+se[!?.]*$",
            t,
        ):
            respuestas_bloqueo = [
                "Está perfecto no saber qué decir, no te preocupes. No hay ningún apuro acá ni tenés que tener todo resuelto hoy. Podemos quedarnos un momento tranquilos o empezar por lo más simple. ¿Querés?",
                "Tranqui, tomarse un momento para pensar o no tener palabras claras es totalmente normal. Respiremos un segundo sin presiones; acá te acompaño a tu ritmo.",
                "No te preocupes en absoluto. A veces frenar un momento aclara las ideas. Tomate tu tiempo; cuando sientas ganas de retomar, avisame y seguimos.",
            ]
            import random
            return (
                "Contención y Descompresión Reflexiva",
                "ANSIEDAD_ESTRES",
                random.choice(respuestas_bloqueo),
            )

        # 8. Actividad física / esparcimiento / despeje ("salir a caminar", "dar una vuelta", "caminar un rato")
        if re.search(
            r"\b(?:salir\s+a\s+caminar|ir\s+a\s+caminar|caminar\s+un\s+rato|dar\s+una\s+vuelta|despejar(?:me)?\s+la\s+cabeza|cambiar\s+de\s+aire)\b",
            t,
        ):
            respuestas_caminar = [
                "¡Es una idea buenísima! Salir a caminar y cambiar de aire es de lo mejor para despejar la cabeza y bajar tensiones. ¿Tenés algún parque o lugar lindo cerca adonde ir?",
                "Caminar un rato viene bárbaro para oxigenarse y resetear la mente. Mover las piernas ayuda un montón a ordenar los pensamientos. ¡Hacelo, te va a hacer re bien!",
                "Totalmente de acuerdo. Una buena caminata sin presiones afloja el estrés y te renueva la energía. Si podés salir un rato, dale para adelante.",
            ]
            import random
            return (
                "Aliento al Esparcimiento y Bienestar",
                "MOTIVACION_ALEGRIA",
                random.choice(respuestas_caminar),
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
            if emo != "CRISIS_RIESGO"
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
                if resp_nube and not self._es_rechazo_invalido_llm(resp_nube):
                    respuesta = resp_nube
                    origen = orig_nube

            if not respuesta and self.usar_llm_local and not conv_basica:
                resp_local = self._consultar_llm_local_gguf(texto_usuario, estado, estrategia)
                if resp_local and not self._es_rechazo_invalido_llm(resp_local):
                    respuesta = resp_local
                    origen = "LLM_LOCAL_QWEN"

        if not respuesta:
            if respuesta_conv:
                respuesta = respuesta_conv
                origen = "CONV_RAPIDA"
            else:
                # Anti-repetición: evitar frases idénticas o muy similares de los últimos turnos del asistente
                respuestas_recientes = [
                    m["content"].strip().lower()
                    for m in list(self.historial_chat)[-8:]
                    if m.get("role") == "assistant"
                ]
                candidatas = list(plantillas)
                seleccionada = None
                start_idx = self._contadores_rotacion.get(emo, 0)
                for offset in range(len(candidatas)):
                    p_cand = candidatas[(start_idx + offset) % len(candidatas)]
                    prefijo = p_cand[:32].strip().lower()
                    if not any(prefijo in r for r in respuestas_recientes):
                        seleccionada = p_cand
                        self._contadores_rotacion[emo] = (start_idx + offset + 1) % len(candidatas)
                        break
                if not seleccionada:
                    idx = start_idx % len(plantillas)
                    self._contadores_rotacion[emo] = (idx + 1) % len(plantillas)
                    seleccionada = plantillas[idx]
                respuesta = seleccionada

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
            f"Estado emocional percibido: {estado.emocion_dominante}. "
            f"Estrategia de coaching sugerida: {estrategia}."
        ]
        if estado.facial.rostro_detectado:
            exp_facial = estado.facial.emocion_facial.lower().replace("_", " ")
            partes.append(f"Expresión en el rostro del usuario: {exp_facial}.")
        if estado.acustica.audio_analizado:
            # Describir la voz cualitativamente SIN números ni unidades de laboratorio
            acu = estado.acustica
            rasgos_voz = []
            if acu.tono_f0_hz > 190:
                rasgos_voz.append("tono agudo")
            elif acu.tono_f0_hz < 130:
                rasgos_voz.append("tono grave o apagado")
            if acu.rapidez_wpm > 170:
                rasgos_voz.append("ritmo rápido o acelerado")
            elif acu.rapidez_wpm < 115:
                rasgos_voz.append("ritmo lento o pausado")
            if acu.volumen_db < -26:
                rasgos_voz.append("volumen bajo o suave")
            elif acu.volumen_db > -18:
                rasgos_voz.append("volumen alto o enérgico")

            desc_voz = ", ".join(rasgos_voz) if rasgos_voz else "tono y ritmo moderados"
            partes.append(f"Sensación en la voz del usuario: {desc_voz}.")
        if estado.incongruencia_detectada:
            partes.append(
                f"Observación de incongruencia: {estado.detalle_incongruencia}. Comentalo con total calidez humana, jamás como un informe técnico."
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
            else "Mantené un tono conversacional, amigable, despierto y curioso."
        )
        if estado.incongruencia_detectada:
            tono_guia += f" Nota importante: {estado.detalle_incongruencia}. Mencionalo con tacto."

        nom_usr = self.nombre_usuario if self.nombre_usuario else "el usuario (no sabés su nombre; trátalo de 'vos')"
        sistema = (
            "Sos Ottoman, robot humanoide Unitree G1 de UADE y coach emocional. "
            f"Estás hablando con {nom_usr}. "
            "DIRECTIVAS: "
            "1. La persona que te habla es un estudiante. NUNCA la llames por ningún nombre propio a menos que te lo haya dicho explícitamente. "
            "2. Sos un coach empático y cercano: acompañá, escuchá y contené al usuario siempre que esté cansado, trabado o enojado. "
            "3. NUNCA te niegues a ayudarlo ni digas que 'no podés intervenir' ni hables de 'libre voluntad'. "
            "4. Hablá en español rioplatense natural y cercano ('vos', 'tenés', 'mirá', 'dale'), sin jerga pesada ni modismos exagerados. "
            "5. PROHIBICIÓN ESTRICTA: NUNCA menciones mediciones técnicas, decibeles (dB), hercios (Hz), frecuencias, velocidad en palabras por minuto, biometría ni sensores. Hablá como un amigo o tutor humano empático ('te noto la voz apagada', 'te veo la mirada cansada'). "
            "6. Respondé en 2 oraciones breves (máximo 40 palabras), sin usar listas ni enumeraciones. "
            f"{tono_guia}"
        )
        mensajes: list[dict[str, str]] = [
            {"role": "system", "content": sistema},
            {"role": "user", "content": "Hablame un poco."},
            {
                "role": "assistant",
                "content": "¡Buenas! Acá estoy listo para charlar o ayudarte a destrabar lo que necesites. ¿En qué estás trabajando hoy?",
            },
            {"role": "user", "content": "Estoy re caliente con este trabajo práctico, no me sale nada."},
            {
                "role": "assistant",
                "content": "Te entiendo totalmente, da mucha bronca cuando algo se traba así. Frenemos un segundo para tomar aire y decime qué parte puntual es la que falla, así le buscamos la vuelta.",
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
            # Limpiar cualquier vocativo donde el LLM intente llamar 'Ottoman' al usuario
            texto = re.sub(r",\s*Ottoman\b", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\bOttoman\s*,\s*", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\b(?:hola|che|tranqui|amigo|fiera)\s+Ottoman\b", r"\1", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\bOttoman\s*([.?!¿¡])", r"\1", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\s+", " ", texto).strip()
            if self._es_rechazo_invalido_llm(texto):
                return ""
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
        nom_usr = self.nombre_usuario if self.nombre_usuario else "el usuario (no sabés su nombre; tratalo cordialmente de 'vos')"
        sistema = (
            f"Sos Ottoman, el robot humanoide Unitree G1 de UADE actuando como compañero y Coach Emocional ético. "
            f"Estás hablando con {nom_usr}. TU nombre es Ottoman; NUNCA llames Ottoman al usuario ni asumas su nombre. "
            f"Es tu deber acompañar y contener al usuario en su enojo, tristeza o estrés; NUNCA te niegues a ayudarlo ni hables de libre voluntad. "
            f"Respondé en español rioplatense natural y casual ('vos', 'tenés', 'mirá', 'dale') en MÁXIMO 2 oraciones breves (40 palabras), sin jerga pesada ni modismos exagerados. "
            f"PROHIBICIÓN ESTRICTA: NUNCA menciones mediciones técnicas, decibeles (dB), hercios (Hz), frecuencias, sensores ni biometría. Hablá con empatía humana. "
            f"Estilo léxico: {prosodia.estilo_lexico}. Contexto del usuario: {ctx}"
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
                    txt_gen = partes[0]["text"].strip()
                    if not self._es_rechazo_invalido_llm(txt_gen):
                        return txt_gen, "GEMINI_API"
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
                    txt_gen = datos["choices"][0]["message"]["content"].strip()
                    orig = "GROQ_API" if es_groq else "OPENAI_API"
                    if not self._es_rechazo_invalido_llm(txt_gen):
                        return txt_gen, orig
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
        """Aplica la acústica caricaturesca del General Infantil:
        megáfono de juguete con crunch de cono y eco teatral de ópera/catedral.
        """
        if onda_int16.size == 0:
            return onda_int16
        try:
            from scipy.signal import butter, sosfilt
            x = onda_int16.astype(np.float32) / 32768.0
            nyq = 0.5 * sample_rate

            # 1. Filtro de megáfono adaptado a juguete pequeño (650 Hz - 4350 Hz)
            low_cut = min(650.0, nyq * 0.4)
            high_cut = min(4350.0, nyq * 0.85)
            sos_bp = butter(2, [low_cut / nyq, high_cut / nyq], btype="band", output="sos")
            x = sosfilt(sos_bp, x)

            # 2. Distorsión crunch de cono de plástico/papel al límite (hard clipping)
            x = np.clip(x * 1.55, -0.75, 0.75)

            # 3. Eco teatral de ópera / catedral (delays de 45ms, 90ms, 140ms y 210ms)
            delays = [int(sample_rate * 0.045), int(sample_rate * 0.090), int(sample_rate * 0.140), int(sample_rate * 0.210)]
            gains = [0.32, 0.22, 0.15, 0.09]
            rev = np.zeros_like(x)
            for dl, g in zip(delays, gains):
                if len(x) > dl:
                    rev += g * np.pad(x[:-dl], (dl, 0))
            x = x + rev

            pico = float(np.max(np.abs(x)))
            if pico > 0.01:
                x = (x / pico) * 0.92
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

                def _despachar_coreografia(rostro_ref):
                    if rostro_ref is None or not hasattr(rostro_ref, "disparar_micro_expresion"):
                        return None
                    emo_base = getattr(rostro_ref, "emocion_actual", "NEUTRO")
                    evs = PlanificadorCoreografiaFacial.planificar(texto_limpio, emocion_base=emo_base, prosodia=prosodia)
                    if not evs:
                        return None
                    stop_ev = threading.Event()
                    def _loop():
                        t0 = time.monotonic()
                        for ev in evs:
                            if stop_ev.is_set():
                                break
                            espera = (t0 + ev.t_inicio) - time.monotonic()
                            if espera > 0:
                                if stop_ev.wait(espera):
                                    break
                            if stop_ev.is_set():
                                break
                            try:
                                rostro_ref.disparar_micro_expresion(
                                    forma_ojo=ev.forma_ojo,
                                    glifo=ev.glifo,
                                    duracion=ev.duracion,
                                    apertura=ev.apertura,
                                    inclinacion=ev.inclinacion,
                                )
                            except Exception:
                                pass
                    t_coreo = threading.Thread(target=_loop, daemon=True)
                    t_coreo.start()
                    return stop_ev

                # INTENTO 1: edge-tts (Neuronal Argentino Tomás con nueva base ágil)
                try:
                    import asyncio
                    import edge_tts
                    from scipy.io import wavfile
                    import winsound

                    # Mapeo a la personalidad de caricatura: General Infantil con identidad cohesiva y estable
                    pct_rate = int(round(+14 + ((prosodia.velocidad_wpm - 150) / 150.0) * 10))
                    pct_rate = max(+12, min(+16, pct_rate))
                    val_pitch = int(round(+20 + (prosodia.tono_hz * 0.12)))
                    val_pitch = max(+18, min(+22, val_pitch))
                    val_vol = int(round(prosodia.volumen_db * 2.0))
                    val_vol = max(-15, min(+5, val_vol))

                    # Detección de bloques dinámicos (Contención inicial -> Silencio -> Acción)
                    oraciones = [o.strip() for o in re.split(r"(?<=[.!?])\s+", texto_prosodico) if o.strip()]
                    es_bimodal = len(oraciones) >= 2 and any(
                        w in texto_prosodico.lower() for w in ("vamos", "plan", "primer", "arranquemos", "contame", "¿dale?", "¡¿dale?!")
                    )

                    with tempfile.TemporaryDirectory() as tmpdir:
                        final_wav = os.path.join(tmpdir, "final.wav")
                        if es_bimodal:
                            # Transición suave sin saltos abruptos (apenas 1 Hz / 1% de matiz orgánico)
                            corte = max(1, len(oraciones) // 2)
                            txt_b1 = " ".join(oraciones[:corte])
                            txt_b2 = " ".join(oraciones[corte:])

                            r_b1 = f"{max(+12, pct_rate - 1):+d}%"
                            p_b1 = f"{max(+18, val_pitch - 1):+d}Hz"
                            v_b1 = f"{val_vol - 6:+d}%"

                            r_b2 = f"{min(+16, pct_rate + 1):+d}%"
                            p_b2 = f"{min(+22, val_pitch + 1):+d}Hz"
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

                        stop_coreo = None
                        if rostro is not None:
                            rostro.set_hablando(True, subtitulo=texto_limpio)
                            stop_coreo = _despachar_coreografia(rostro)
                        try:
                            winsound.PlaySound(final_wav, winsound.SND_FILENAME)
                            reproduccion_exitosa = True
                        finally:
                            if stop_coreo is not None:
                                stop_coreo.set()
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

                            stop_coreo = None
                            if rostro is not None:
                                rostro.set_hablando(True, subtitulo=texto_limpio)
                                stop_coreo = _despachar_coreografia(rostro)
                            try:
                                winsound.PlaySound(ruta_mod, winsound.SND_FILENAME)
                                reproduccion_exitosa = True
                            finally:
                                if stop_coreo is not None:
                                    stop_coreo.set()
                                if rostro is not None:
                                    rostro.set_hablando(False)
                        else:
                            stop_coreo = None
                            if rostro is not None:
                                rostro.set_hablando(True, subtitulo=texto_limpio)
                                stop_coreo = _despachar_coreografia(rostro)
                            try:
                                engine.setProperty("rate", int(prosodia.velocidad_wpm))
                                engine.say(texto_limpio)
                                engine.runAndWait()
                                reproduccion_exitosa = True
                            finally:
                                if stop_coreo is not None:
                                    stop_coreo.set()
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

