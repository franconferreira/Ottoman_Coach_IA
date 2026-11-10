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

from collections import deque
import json
import math
import os
from pathlib import Path
import re
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

def _manos_abiertas() -> dict[str, float]:
    """Manos relajadas y abiertas (0.05 rad en articulaciones de dedos MuJoCo)."""
    d = {}
    for lado in ("left", "right"):
        for dedo in ("index", "middle", "ring", "pinky", "thumb_bend", "thumb_rotation"):
            d[f"{lado}_hand_{dedo}"] = 0.05
    return d


def _pulgar_arriba_derecho() -> dict[str, float]:
    """Mano derecha con pulgar extendido y dedos cerrados; izquierda relajada."""
    d = _manos_abiertas()
    for dedo in ("index", "middle", "ring", "pinky"):
        d[f"right_hand_{dedo}"] = 1.25
    d["right_hand_thumb_bend"] = 0.0
    d["right_hand_thumb_rotation"] = 0.65
    return d


def _pose_neutra_suave() -> dict[str, float]:
    """Postura canónica neutra y relajada con brazos caídos a los lados (biomecánica humana)."""
    pose = {
        "waist_yaw": 0.0,
        "waist_roll": 0.0,
        "waist_pitch": 0.0,
        "left_shoulder_pitch": 0.42,
        "left_shoulder_roll": 0.08,
        "left_shoulder_yaw": 0.0,
        "left_elbow": 0.28,
        "left_wrist_pitch": 0.0,
        "left_wrist_roll": 0.0,
        "left_wrist_yaw": 0.0,
        "right_shoulder_pitch": 0.42,
        "right_shoulder_roll": -0.08,
        "right_shoulder_yaw": 0.0,
        "right_elbow": 0.28,
        "right_wrist_pitch": 0.0,
        "right_wrist_roll": 0.0,
        "right_wrist_yaw": 0.0,
    }
    pose.update(_manos_abiertas())
    return pose


class CoreografoPosturalG1:
    """Diseña el lenguaje corporal (kinésica + proxémica) según la emoción."""

    # Límites seguros estrictos para torso y brazos del G1 (subconjunto conservador del XML)
    LIMITES_ARTICULARES: dict[str, tuple[float, float]] = {
        "waist_yaw": (-0.45, 0.45),
        "waist_roll": (-0.25, 0.25),
        "waist_pitch": (-0.15, 0.25),
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
        tilt_pitch = float(np.clip(-0.04 * valencia - 0.03 * arousal, -0.06, 0.06))
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

        if emocion == "ANSIEDAD_ESTRES":
            # Co-regulación respiratoria diafragmática: torso receptive, brazos suben
            # suavemente acompañando inhalación y descienden lento en exhalación.
            inhala = dict(base, **{
                "waist_pitch": 0.04,
                "left_shoulder_pitch": 0.32,
                "left_shoulder_roll": 0.16,
                "left_elbow": 0.40,
                "left_wrist_pitch": 0.15,
                "right_shoulder_pitch": 0.32,
                "right_shoulder_roll": -0.16,
                "right_elbow": 0.40,
                "right_wrist_pitch": 0.15,
            })
            sostener = dict(inhala, **{
                "left_shoulder_pitch": 0.30,
                "right_shoulder_pitch": 0.30,
                "left_elbow": 0.44,
                "right_elbow": 0.44,
            })
            exhala = dict(base, **{
                "waist_pitch": 0.02,
                "left_shoulder_pitch": 0.40,
                "left_shoulder_roll": 0.10,
                "left_elbow": 0.30,
                "left_wrist_pitch": -0.05,
                "right_shoulder_pitch": 0.40,
                "right_shoulder_roll": -0.10,
                "right_elbow": 0.30,
                "right_wrist_pitch": -0.05,
            })
            sec, dur, pm, pv = [inhala, sostener, exhala, base], 0.95, 0.0, 0.0

        elif emocion == "TRISTEZA_DESANIMO":
            # Acercamiento proxémico empático (+0.25m), inclinación empática del torso (+0.14 rad),
            # mano derecha al pecho/corazón con codo flexionado natural, brazo izquierdo contenedor.
            empatia_1 = dict(base, **{
                "waist_pitch": 0.14,
                "waist_roll": 0.04,
                "right_shoulder_pitch": 0.30,
                "right_shoulder_roll": -0.14,
                "right_shoulder_yaw": -0.30,
                "right_elbow": 0.50,
                "right_wrist_pitch": 0.20,
                "left_shoulder_pitch": 0.40,
                "left_shoulder_roll": 0.12,
                "left_elbow": 0.32,
            })
            empatia_2 = dict(empatia_1, **{
                "waist_pitch": 0.16,
                "left_shoulder_pitch": 0.36,
                "left_wrist_pitch": 0.15,
            })
            sec, dur, pm, pv = [empatia_1, empatia_2, empatia_1, base], 0.85, +0.25, 0.12

        elif emocion == "ENOJO_FRUSTRACION":
            # Proxémica de desescalada: paso corto atrás (-0.25m) respetando espacio personal,
            # torso erguido estable, ambas palmas abiertas hacia el frente (no amenaza).
            calma_1 = dict(base, **{
                "waist_pitch": 0.0,
                "waist_roll": 0.0,
                "left_shoulder_pitch": 0.34,
                "left_shoulder_roll": 0.16,
                "left_elbow": 0.44,
                "left_wrist_pitch": 0.30,
                "right_shoulder_pitch": 0.34,
                "right_shoulder_roll": -0.16,
                "right_elbow": 0.44,
                "right_wrist_pitch": 0.30,
            })
            calma_2 = dict(calma_1, **{
                "left_shoulder_pitch": 0.38,
                "right_shoulder_pitch": 0.38,
                "left_elbow": 0.36,
                "right_elbow": 0.36,
                "left_wrist_pitch": 0.18,
                "right_wrist_pitch": 0.18,
            })
            sec, dur, pm, pv = [calma_1, calma_2, base], 0.80, -0.25, 0.12

        elif emocion == "DUDA_INSEGURIDAD":
            # Gesto socrático: presenta primera opción con mano izquierda abierta y
            # segunda opción con mano derecha abierta; torso atento con leve rotación.
            opcion_a = dict(base, **{
                "waist_yaw": 0.10,
                "waist_pitch": 0.04,
                "left_shoulder_pitch": 0.32,
                "left_shoulder_roll": 0.20,
                "left_elbow": 0.42,
                "left_wrist_roll": 0.20,
            })
            opcion_b = dict(base, **{
                "waist_yaw": -0.10,
                "waist_pitch": 0.04,
                "right_shoulder_pitch": 0.32,
                "right_shoulder_roll": -0.20,
                "right_elbow": 0.42,
                "right_wrist_roll": -0.20,
            })
            sintesis = dict(base, **{
                "waist_yaw": 0.0,
                "left_shoulder_pitch": 0.36,
                "right_shoulder_pitch": 0.36,
                "left_elbow": 0.36,
                "right_elbow": 0.36,
            })
            sec, dur, pm, pv = [opcion_a, opcion_b, sintesis, base], 0.65, 0.0, 0.0

        elif emocion == "MOTIVACION_ALEGRIA":
            # Postura expansiva celebratoria + pulgar arriba Inspire RH56 con brazos abiertos y vivos.
            apertura = dict(base, **{
                "waist_pitch": -0.04,
                "left_shoulder_pitch": 0.26,
                "left_shoulder_roll": 0.24,
                "left_elbow": 0.42,
                "right_shoulder_pitch": 0.26,
                "right_shoulder_roll": -0.24,
                "right_elbow": 0.42,
            })
            pulgar = dict(base, **{
                "waist_pitch": -0.03,
                "right_shoulder_pitch": 0.28,
                "right_shoulder_roll": -0.16,
                "right_elbow": 0.46,
                "right_wrist_roll": -0.20,
            })
            pulgar.update(_pulgar_arriba_derecho())
            sec, dur, pm, pv = [apertura, pulgar, pulgar, base], 0.50, 0.0, 0.0

        else:
            # NEUTRO o CRISIS_RIESGO: gesticulación conversacional orgánica y atenta
            gesto_izq = dict(base, **{
                "waist_pitch": 0.03,
                "waist_yaw": 0.06,
                "left_shoulder_pitch": 0.34,
                "left_shoulder_roll": 0.14,
                "left_elbow": 0.38,
                "left_wrist_roll": 0.15,
                "right_shoulder_pitch": 0.42,
                "right_elbow": 0.28,
            })
            gesto_der = dict(base, **{
                "waist_pitch": 0.02,
                "waist_yaw": -0.06,
                "left_shoulder_pitch": 0.42,
                "left_elbow": 0.28,
                "right_shoulder_pitch": 0.34,
                "right_shoulder_roll": -0.14,
                "right_elbow": 0.38,
                "right_wrist_roll": -0.15,
            })
            sec, dur, pm, pv = [gesto_izq, gesto_der, base], 0.60, 0.0, 0.0

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
            "left_wrist_roll": mod_l_wr,
            "right_wrist_roll": mod_r_wr,
            "left_wrist_yaw": 0.0,
            "right_wrist_yaw": 0.0,
        }

        # Dedos Inspire RH56
        for lado in ("left", "right"):
            for dedo in ("index", "middle", "ring", "pinky"):
                pose[f"{lado}_hand_{dedo}"] = dedos_val
            pose[f"{lado}_hand_thumb_rotation"] = 0.05
            pose[f"{lado}_hand_thumb_bend"] = dedos_val * 0.6

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

class SintetizadorVozAdaptativo:
    """Modula la onda acústica del robot en WPM, decibeles, tono F0 (Hz) y timbre espectral."""

    def __init__(self, habilitado: bool = True):
        self.habilitado = habilitado
        self._lock = threading.Lock()

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
        """Sintetiza la respuesta completa de una sola vez, aplica DSP de Tono/Timbre/Volumen y reproduce."""
        texto_limpio = texto.strip()
        if not self.habilitado or not texto_limpio:
            return None

        def _tarea_audio():
            with self._lock:
                time.sleep(max(0.0, prosodia.pausa_inicial_s))
                volumen_lineal = self.db_a_ganancia(prosodia.volumen_db)
                ratio_pitch = float(np.clip((160.0 + float(prosodia.tono_hz)) / 160.0, 0.84, 1.20))
                rate_compensado = int(round(prosodia.velocidad_wpm / ratio_pitch))

                fd_raw, ruta_raw = tempfile.mkstemp(suffix="_raw.wav")
                os.close(fd_raw)
                fd_mod, ruta_mod = tempfile.mkstemp(suffix="_dsp.wav")
                os.close(fd_mod)

                reproduccion_exitosa = False
                try:
                    import pyttsx3
                    from scipy.io import wavfile
                    import winsound

                    engine = pyttsx3.init()
                    for v in engine.getProperty("voices") or []:
                        vid = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                        if any(tag in vid for tag in ("spanish", "espanol", "español", "es-", "es_", "helena", "sabina", "pablo")):
                            engine.setProperty("voice", v.id)
                            break
                    engine.setProperty("rate", rate_compensado)
                    engine.setProperty("volume", volumen_lineal)

                    # Sintetizar el texto completo de una sola vez para evitar el bug COM de Windows
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
                finally:
                    # Garantía absoluta: apagar boca de la cara y limpiar archivos temporales
                    if rostro is not None:
                        rostro.set_hablando(False)
                    for r_tmp in (ruta_raw, ruta_mod):
                        try:
                            if os.path.exists(r_tmp):
                                os.remove(r_tmp)
                        except OSError:
                            pass

                # Fallback visual por duración estimada si el hardware de audio no estuvo disponible
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
