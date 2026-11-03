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

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from percepcion_multimodal import EstadoAfectivoUsuario


# =====================================================================
#  ESTRUCTURAS DE SALIDA DEL MOTOR DE COACHING
# =====================================================================

@dataclass
class PerfilProsodico:
    """Parámetros acústicos y temporales que adopta la voz del robot."""
    velocidad_wpm: int          # Palabras por minuto objetivo (ej. 122 vs 172)
    velocidad_pct: int          # Delta porcentual respecto a voz neutra (-25% a +15%)
    volumen_db: float           # Ajuste relativo en decibeles (-6.0 dB a +4.0 dB)
    tono_hz: int                # Desplazamiento de tono fundamental (-18 Hz a +16 Hz)
    pausa_inicial_s: float      # Silencio deliberado antes de empezar a hablar
    pausa_entre_frases_s: float # Temporalización respiratoria entre oraciones
    estilo_lexico: str          # Registro lingüístico seleccionado


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
    pose = {
        "waist_yaw": 0.0,
        "waist_roll": 0.0,
        "waist_pitch": 0.0,
        "left_shoulder_pitch": 0.15,
        "left_shoulder_roll": 0.12,
        "left_shoulder_yaw": 0.0,
        "left_elbow": -0.25,
        "left_wrist_pitch": 0.0,
        "left_wrist_roll": 0.0,
        "left_wrist_yaw": 0.0,
        "right_shoulder_pitch": 0.15,
        "right_shoulder_roll": -0.12,
        "right_shoulder_yaw": 0.0,
        "right_elbow": -0.25,
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
    def obtener_coreografia(cls, emocion: str) -> tuple[list[dict[str, float]], float, float, float]:
        """Devuelve (secuencia_poses, duracion_step_s, proxemica_m, vel_proxemica_ms)."""
        base = _pose_neutra_suave()

        if emocion == "ANSIEDAD_ESTRES":
            # Guía de respiración diafragmática: brazos suben acompañando inhalación
            # y descienden lento acompañando exhalación; torso levemente receptivo.
            inhala = dict(base, **{
                "waist_pitch": 0.08,
                "left_shoulder_pitch": -0.78,
                "left_shoulder_roll": 0.42,
                "left_elbow": -0.55,
                "left_wrist_pitch": 0.35,
                "right_shoulder_pitch": -0.78,
                "right_shoulder_roll": -0.42,
                "right_elbow": -0.55,
                "right_wrist_pitch": 0.35,
            })
            sostener = dict(inhala, **{
                "left_shoulder_pitch": -0.88,
                "right_shoulder_pitch": -0.88,
            })
            exhala = dict(base, **{
                "waist_pitch": 0.10,
                "left_shoulder_pitch": -0.22,
                "left_shoulder_roll": 0.25,
                "left_elbow": -0.35,
                "left_wrist_pitch": -0.15,
                "right_shoulder_pitch": -0.22,
                "right_shoulder_roll": -0.25,
                "right_elbow": -0.35,
                "right_wrist_pitch": -0.15,
            })
            return [inhala, sostener, exhala, base], 0.95, 0.0, 0.0

        if emocion == "TRISTEZA_DESANIMO":
            # Acercamiento proxémico corto (+0.25m), inclinación empática del torso y
            # mano derecha al pecho/corazón con brazo izquierdo abierto contenedor.
            empatia_1 = dict(base, **{
                "waist_pitch": 0.16,
                "waist_roll": 0.12,
                "right_shoulder_pitch": -0.52,
                "right_shoulder_roll": 0.18,
                "right_shoulder_yaw": -0.85,
                "right_elbow": -0.98,
                "right_wrist_pitch": 0.25,
                "left_shoulder_pitch": -0.35,
                "left_shoulder_roll": 0.38,
                "left_elbow": -0.45,
            })
            empatia_2 = dict(empatia_1, **{
                "waist_pitch": 0.18,
                "left_shoulder_pitch": -0.45,
                "left_wrist_pitch": 0.30,
            })
            return [empatia_1, empatia_2, empatia_1, base], 0.85, +0.25, 0.12

        if emocion == "ENOJO_FRUSTRACION":
            # Proxémica de desescalada: paso corto hacia atrás (-0.25m) respetando espacio,
            # torso erguido estable, ambas palmas abiertas visibles al frente (no amenaza).
            calma_1 = dict(base, **{
                "waist_pitch": 0.0,
                "waist_roll": 0.0,
                "left_shoulder_pitch": -0.62,
                "left_shoulder_roll": 0.32,
                "left_elbow": -0.72,
                "left_wrist_pitch": 0.65,
                "right_shoulder_pitch": -0.62,
                "right_shoulder_roll": -0.32,
                "right_elbow": -0.72,
                "right_wrist_pitch": 0.65,
            })
            calma_2 = dict(calma_1, **{
                "left_shoulder_pitch": -0.48,
                "right_shoulder_pitch": -0.48,
                "left_wrist_pitch": 0.45,
                "right_wrist_pitch": 0.45,
            })
            return [calma_1, calma_2, base], 0.80, -0.25, 0.12

        if emocion == "DUDA_INSEGURIDAD":
            # Gesto socrático: presenta primera alternativa con mano izquierda abierta y
            # segunda alternativa con mano derecha abierta; torso atento.
            opcion_a = dict(base, **{
                "waist_yaw": 0.12,
                "waist_pitch": 0.06,
                "left_shoulder_pitch": -0.70,
                "left_shoulder_roll": 0.45,
                "left_elbow": -0.55,
                "left_wrist_roll": 0.45,
            })
            opcion_b = dict(base, **{
                "waist_yaw": -0.12,
                "waist_pitch": 0.06,
                "right_shoulder_pitch": -0.70,
                "right_shoulder_roll": -0.45,
                "right_elbow": -0.55,
                "right_wrist_roll": -0.45,
            })
            sintesis = dict(base, **{
                "waist_yaw": 0.0,
                "left_shoulder_pitch": -0.50,
                "right_shoulder_pitch": -0.50,
                "left_elbow": -0.50,
                "right_elbow": -0.50,
            })
            return [opcion_a, opcion_b, sintesis, base], 0.65, 0.0, 0.0

        if emocion == "MOTIVACION_ALEGRIA":
            # Postura expansiva celebratoria + gesto de pulgar arriba con mano Inspire.
            apertura = dict(base, **{
                "waist_pitch": -0.04,
                "left_shoulder_pitch": -1.15,
                "left_shoulder_roll": 0.65,
                "left_elbow": -0.40,
                "right_shoulder_pitch": -1.15,
                "right_shoulder_roll": -0.65,
                "right_elbow": -0.40,
            })
            pulgar = dict(base, **{
                "right_shoulder_pitch": -0.95,
                "right_shoulder_roll": -0.25,
                "right_elbow": -0.75,
                "right_wrist_roll": -0.35,
            })
            pulgar.update(_pulgar_arriba_derecho())
            return [apertura, pulgar, pulgar, base], 0.50, 0.0, 0.0

        # NEUTRO o CRISIS_RIESGO: presencia tranquila y manos visibles abiertas
        presencia = dict(base, **{
            "waist_pitch": 0.05,
            "left_shoulder_pitch": -0.30,
            "right_shoulder_pitch": -0.30,
            "left_elbow": -0.40,
            "right_elbow": -0.40,
        })
        return [presencia, base], 0.75, 0.0, 0.0


# =====================================================================
#  2. MOTOR DE RESPUESTA PSICOLINGÜÍSTICA (CBR LOCAL + GEMINI OPCIONAL)
# =====================================================================

class MotorRespuestaCoach:
    """Selecciona prosodia, estrategia HRI y léxico adaptado al usuario."""

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
            ),
            [
                "Lo que estás sintiendo es muy importante y no tenés que atravesarlo en soledad. Como soy un robot educativo, mi deber ético es cuidarte y pedirte que hables ahora mismo con una persona de confianza, con el equipo de orientación o al 135 de asistencia gratuita las 24 horas.",
            ],
        ),
        "NEUTRO": (
            "Escucha Activa Abierta",
            PerfilProsodico(
                velocidad_wpm=150,
                velocidad_pct=0,
                volumen_db=0.0,
                tono_hz=0,
                pausa_inicial_s=0.30,
                pausa_entre_frases_s=0.35,
                estilo_lexico="conversacional_empatico",
            ),
            [
                "Acá estoy atento escuchándote. Contame cómo te venís sintiendo hoy o qué tema tenés en mente y me adapto a tu ritmo.",
            ],
        ),
    }

    def __init__(self, usar_llm_si_disponible: bool = True):
        self.usar_llm_si_disponible = usar_llm_si_disponible
        self._contadores_rotacion: dict[str, int] = {}

    def planificar(
        self,
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
        historial_emociones: Optional[list[str]] = None,
    ) -> PlanRegulacionEmocional:
        """Construye el plan completo de voz, léxico, rostro y postura."""
        emo = estado.emocion_dominante if estado.emocion_dominante in self.PERFILES_BASE else "NEUTRO"
        estrategia, prosodia_base, plantillas = self.PERFILES_BASE[emo]

        # Ajuste continuo fino de la prosodia según la intensidad real medida en cara/voz
        factor_int = max(0.0, estado.intensidad - 0.5)
        vel_wpm = int(round(
            prosodia_base.velocidad_wpm
            + (-12 * factor_int if emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO") else 8 * factor_int if emo == "MOTIVACION_ALEGRIA" else 0)
        ))
        vol_db = round(
            prosodia_base.volumen_db
            + (-1.5 * factor_int if emo == "ANSIEDAD_ESTRES" else 0.0),
            1,
        )
        pausa_frases = round(
            prosodia_base.pausa_entre_frases_s + (0.20 * factor_int if emo == "ANSIEDAD_ESTRES" else 0.0),
            2,
        )
        prosodia = PerfilProsodico(
            velocidad_wpm=vel_wpm,
            velocidad_pct=prosodia_base.velocidad_pct,
            volumen_db=vol_db,
            tono_hz=prosodia_base.tono_hz,
            pausa_inicial_s=prosodia_base.pausa_inicial_s,
            pausa_entre_frases_s=pausa_frases,
            estilo_lexico=prosodia_base.estilo_lexico,
        )

        # Selección de respuesta: LLM opcional (si hay API Key y no es crisis) o CBR Local
        origen = "CBR_LOCAL"
        respuesta = ""
        if self.usar_llm_si_disponible and emo != "CRISIS_RIESGO" and os.environ.get("GEMINI_API_KEY"):
            respuesta_llm = self._consultar_gemini_flash(texto_usuario, estado, estrategia, prosodia)
            if respuesta_llm:
                respuesta = respuesta_llm
                origen = "GEMINI_API"

        if not respuesta:
            idx = self._contadores_rotacion.get(emo, 0) % len(plantillas)
            self._contadores_rotacion[emo] = idx + 1
            respuesta = plantillas[idx]

        # Si detectó incongruencia entre palabras ("estoy bien") y cara/voz, lo explicita con tacto
        if estado.incongruencia_detectada and emo != "CRISIS_RIESGO":
            prefijo = f"{estado.detalle_incongruencia}. No hace falta disimular conmigo. "
            respuesta = prefijo + respuesta

        # Si la memoria muestra persistencia de malestar en los últimos turnos, adapta seguimiento
        if historial_emociones and len(historial_emociones) >= 2 and emo != "CRISIS_RIESGO":
            previas = historial_emociones[-2:]
            if all(p == emo for p in previas) and emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO", "ENOJO_FRUSTRACION"):
                respuesta += " Noto que esta emoción sigue muy presente; tomemos todo el tiempo que necesites."
            elif previas[-1] in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO", "ENOJO_FRUSTRACION") and emo == "MOTIVACION_ALEGRIA":
                respuesta = "¡Qué bueno notar cómo cambió tu energía respecto a hace un rato! " + respuesta

        secuencia, dur_step, prox_m, prox_vel = CoreografoPosturalG1.obtener_coreografia(emo)

        return PlanRegulacionEmocional(
            emocion_usuario=emo,
            estrategia_hri=estrategia,
            texto_respuesta=respuesta,
            prosodia=prosodia,
            secuencia_postural=secuencia,
            duracion_step_postura=dur_step,
            proxemica_distancia_m=prox_m,
            proxemica_velocidad_ms=prox_vel,
            preset_rostro=emo,
            origen_respuesta=origen,
        )

    @staticmethod
    def _consultar_gemini_flash(
        texto_usuario: str,
        estado: EstadoAfectivoUsuario,
        estrategia: str,
        prosodia: PerfilProsodico,
    ) -> str:
        """Consulta opcional de baja latencia a Gemini API con fallback seguro."""
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return ""
        prompt = (
            "Sos Ottoman, el robot humanoide Unitree G1 de UADE actuando como Coach Emocional ético "
            "(principios human-ai.org). Respondé en español rioplatense en MÁXIMO 2 oraciones breves "
            f"aplicando la estrategia '{estrategia}' y estilo léxico '{prosodia.estilo_lexico}'. "
            f"Emoción percibida: {estado.emocion_dominante} (Valencia={estado.valencia}, Arousal={estado.arousal}). "
            f"Incongruencia no verbal: {estado.incongruencia_detectada}. "
            f"Mensaje del usuario: \"{texto_usuario}\""
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 140},
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                datos = json.loads(resp.read().decode("utf-8"))
                partes = datos["candidates"][0]["content"]["parts"]
                return partes[0]["text"].strip()
        except (urllib.error.URLError, KeyError, IndexError, TimeoutError, ValueError):
            return ""


# =====================================================================
#  3. SINTETIZADOR DE VOZ ADAPTATIVO (VELOCIDAD, PAUSAS, dB, TONO)
# =====================================================================

class SintetizadorVozAdaptativo:
    """Modula la voz del robot en velocidad (WPM), decibeles, tono y pausas."""

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

    def hablar_sincronizado(
        self,
        texto: str,
        prosodia: PerfilProsodico,
        rostro=None,
        bloqueante: bool = False,
    ) -> Optional[threading.Thread]:
        """Ejecuta el habla modulada respetando pausa inicial y pausas entre frases."""
        if not self.habilitado or not texto.strip():
            return None

        def _tarea_audio():
            with self._lock:
                time.sleep(max(0.0, prosodia.pausa_inicial_s))
                frases = self.segmentar_frases(texto)
                volumen_lineal = self.db_a_ganancia(prosodia.volumen_db)

                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    # Seleccionar voz en español si está instalada en el sistema
                    for v in engine.getProperty("voices") or []:
                        vid = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                        if any(tag in vid for tag in ("spanish", "espanol", "español", "es-", "es_", "helena", "sabina", "pablo")):
                            engine.setProperty("voice", v.id)
                            break
                    engine.setProperty("rate", int(prosodia.velocidad_wpm))
                    engine.setProperty("volume", volumen_lineal)

                    for i, frase in enumerate(frases):
                        if rostro is not None:
                            rostro.set_hablando(True, subtitulo=frase)
                        engine.say(frase)
                        engine.runAndWait()
                        if rostro is not None:
                            rostro.set_hablando(False)
                        if i < len(frases) - 1:
                            time.sleep(max(0.05, prosodia.pausa_entre_frases_s))
                except Exception:
                    # Si el sistema no tiene dispositivo de audio activo, simula el timing en el rostro
                    for i, frase in enumerate(frases):
                        if rostro is not None:
                            rostro.set_hablando(True, subtitulo=frase)
                        palabras = max(1, len(frase.split()))
                        dur = (palabras / max(80, prosodia.velocidad_wpm)) * 60.0
                        time.sleep(min(3.5, dur))
                        if rostro is not None:
                            rostro.set_hablando(False)
                        if i < len(frases) - 1:
                            time.sleep(max(0.05, prosodia.pausa_entre_frases_s))

        if bloqueante:
            _tarea_audio()
            return None
        hilo = threading.Thread(target=_tarea_audio, daemon=True)
        hilo.start()
        return hilo
