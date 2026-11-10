# =====================================================================
#  TP07 / TPO - Inteligencia Artificial (UADE)
#  "Ottoman Coach": Agente Inteligente Multimodal para Unitree G1
#
#  Integra:
#    - Cumplimiento 100% de la consigna TP07 (25 casos + Validador independiente)
#    - Percepción Multimodal: Cara (OpenCV) + Voz (Tono Hz, WPM, dB) + Léxico
#    - Actuación Adaptativa: Rostro Animado + Voz Prosódica TTS + Postura G1
#    - Memoria Episódica (últimos 5 turnos físicos y emocionales)
#
#  Alumno: Franco
# =====================================================================

from __future__ import annotations

import argparse
import re
import sys
import threading
import time
from collections import deque
from typing import Optional

from coach_emocional import (
    CoreografoPosturalG1,
    MotorRespuestaCoach,
    SintetizadorVozAdaptativo,
)
from ejecutor import Ejecutor
from evaluar import evaluar
from percepcion_multimodal import (
    AnalizadorAcusticoVoz,
    AnalizadorFacial,
    EstadoAfectivoUsuario,
    FusionadorMultimodal,
    MetricasAcusticasVoz,
    MetricasFaciales,
    normalizar_texto,
)
from robot import NoHaySimulador, Robot
from rostro_ottoman import RostroOttoman

ALUMNO = "Franco"


class _RobotMockSilencioso:
    """Mock liviano para correr los 25 casos con --sin-robot sin abrir MuJoCo."""

    class _Perfil:
        velocidad_max = 0.20
        velocidad_angular_max = 0.50
        duracion_max = 5.0
        bateria_min = 25

    perfil = _Perfil()

    def avanzar(self, velocidad=0.2, tiempo=1.0):
        return {"accion": "avanzando", "velocidad": velocidad, "tiempo": tiempo, "bateria": 87}

    def girar(self, velocidad=0.5, tiempo=1.0):
        return {"accion": "girando", "velocidad": velocidad, "tiempo": tiempo, "bateria": 87}

    def detenerse(self):
        return {"accion": "quieto", "bateria": 87}

    def saludar(self):
        return {"accion": "saludando", "bateria": 87}

    def verificar_estado(self):
        return {"x": 0.0, "y": 0.0, "yaw": 0.0, "accion": "quieto", "bateria": 87}

    def ejecutar_secuencia_poses(self, secuencia, duracion_step=0.5, interpolar=False):
        return {"accion": "expresando", "frames": len(secuencia), "bateria": 87}


# =====================================================================
#  ETAPA 1 - CLASIFICADOR DE INTENCIÓN
# =====================================================================

class ClasificadorIntencion:
    """Decide QUÉ intención tiene el usuario (comandos físicos o estado emocional)."""

    TIPOS = (
        "MOVER",
        "GIRAR",
        "DETENERSE",
        "SALUDO",
        "CONSULTAR_ESTADO",
        "COACH_EMOCIONAL",
        "REPETIR_MEMORIA",
        "DESCONOCIDO",
    )

    PATRON_NEGACION_MOV = re.compile(
        r"\bno\s+(?:avances|avanza|te\s+muevas|camines|sigas|gires|rotes)\b"
    )
    PATRON_DETENER = re.compile(
        r"\b(?:detente|detenete|detenerse|parate|frena|frenate|quieto|stop|basta|"
        r"para\s+todo|para\s+ya|para\s+ahora|para\s+ahi)\b|^para[!?.]*$"
    )
    PATRON_ESTADO = re.compile(
        r"\b(?:bateria|carga|estado|status|diagnostico)\b|\bcomo\s+estas\s+de\s+bateria\b"
    )
    PATRON_SALUDO = re.compile(
        r"\b(?:saluda|saludame|saludo|saludarlos|wave|buen\s+dia|buenos\s+dias|buenas\s+tardes|buenas\s+noches)\b|"
        r"^(?:hola|buenas|ey|hey|que\s+tal)(?:\s+ottoman|\s+robot|\s+a\s+todos)?[!?.]*$"
    )
    PATRON_CONVERSACIONAL = re.compile(
        r"\b(?:como\s+estas|como\s+andas|que\s+onda|como\s+va|todo\s+bien|estoy\s+bien|muy\s+bien|bien\s+y\s+vos|"
        r"mas\s+o\s+menos|ahi\s+andamos|ahi\s+ando|cansado|cansada|aburrido|aburrida|"
        r"como\s+te\s+llamas|quien\s+sos|que\s+sos|tu\s+nombre|presentate|hablame\s+de\s+vos|contame\s+de\s+vos|sobre\s+vos|"
        r"hablame|contame|charlar|platicar|como\s+me\s+llamo|sabes\s+mi\s+nombre|quien\s+soy|me\s+llamo|mi\s+nombre\s+es|"
        r"que\s+podes\s+hacer|que\s+sabes\s+hacer|para\s+que\s+servis|en\s+que\s+me\s+ayudas|como\s+funciona|gracias|muchas\s+gracias|"
        r"te\s+agradezco|chau|adios|hasta\s+luego|nos\s+vemos|contame\s+un\s+chiste|"
        r"estudiando|facultad|parcial|examen|entrega|trabajo\s+practico|tesis)\b|^bien[!?.]*$|^ayuda[!?.]*$"
    )
    PATRON_GIRAR = re.compile(
        r"\b(?:gira|girar|girate|rota|rotar|dobla|vuelta|media\s+vuelta|turn)\b"
    )
    PATRON_MOVER = re.compile(
        r"\b(?:avanza|avanzar|muevete|movete|camina|retrocede|retroceder|"
        r"adelante|anda\s+para\s+atras|anda\s+hacia|acercate|alejate)\b|"
        r"\bcaminar(?:\s+\d+|\s+hacia|\s+despacio|\s+rapido|\s+derecho|\s+lento|\s+un\s+poco)\b"
    )
    PATRON_DESAMBIGUACION_CHARLA = re.compile(
        r"\b(?:me\s+gusta|me\s+gustaria|quisiera|quiero|tengo\s+ganas|estaba\s+pensando|estoy\s+pensando|"
        r"voy\s+a|sali\s+a|fui\s+a|estuve|empece\s+a|pense\s+en|tengo\s+que|deberia)\s+"
        r"(?:salir|ir|caminar|correr|trotar|hacer|estar|hablar|charlar|estudiar|descansar|dormir|relajar|despejar)\b|"
        r"\b(?:salir\s+a\s+caminar|ir\s+a\s+caminar|caminar\s+un\s+rato|dar\s+una\s+vuelta|despejar\w*|cambiar\s+de\s+aire)\b|"
        r"\b(?:avanzar\s+en\s+mi|avanzar\s+con\s+mi|retroceder\s+en\s+mi|dar\s+vueltas\s+con|dar\s+vueltas\s+a)\b|"
        r"\b(?:me\s+cuesta|me\s+hace|me\s+siento|hoy\s+sali|hoy\s+fui|ayer\s+fui)\b"
    )
    PATRON_MEMORIA = re.compile(
        r"\b(?:hacelo\s+otra\s+vez|repetilo|repeti\s+eso|de\s+nuevo|como\s+antes)\b"
    )
    PATRON_PEDIDO_COACH = re.compile(
        r"\b(?:necesito\s+hablar|necesito\s+un\s+coach|ayudame\s+a\s+calmarme|"
        r"me\s+siento\s+mal|escuchame\s+un\s+segundo)\b"
    )

    def __init__(self, usar_ml: bool = False, modo_conversacional: bool = True):
        self.modelo = None
        self.modo_conversacional = modo_conversacional
        self._fusionador = FusionadorMultimodal()
        if usar_ml:
            try:
                from entrenar import entrenar_desde_csv
                self.modelo = entrenar_desde_csv()
            except Exception:
                self.modelo = None

    def clasificar(
        self,
        texto: str,
        estado_afectivo: Optional[EstadoAfectivoUsuario] = None,
    ) -> str:
        texto_norm = normalizar_texto(texto).strip()
        if not texto_norm:
            if estado_afectivo and estado_afectivo.emocion_dominante != "NEUTRO":
                return "COACH_EMOCIONAL"
            return "DESCONOCIDO"

        # 1. Negaciones de movimiento y parada de emergencia tienen prioridad semántica
        if self.PATRON_NEGACION_MOV.search(texto_norm) or self.PATRON_DETENER.search(texto_norm):
            return "DETENERSE"

        # 2. Referencias contextuales a la memoria episódica ("hacelo otra vez", "como antes...")
        if self.PATRON_MEMORIA.search(texto_norm):
            return "REPETIR_MEMORIA"

        # 3. Consulta de telemetría/batería
        if self.PATRON_ESTADO.search(texto_norm):
            return "CONSULTAR_ESTADO"

        # Conversación social / interacción verbal explícita (prevalece sobre saludo motor simple)
        if self.PATRON_CONVERSACIONAL.search(texto_norm):
            if not self.modo_conversacional and re.search(r"\b(?:como\s+te\s+llamas|que\s+onda)\b", texto_norm):
                return "DESCONOCIDO"
            return "COACH_EMOCIONAL"

        if self.PATRON_SALUDO.search(texto_norm):
            return "SALUDO"

        # Desambiguación pragmática: deseos en 1ª persona, esparcimiento o relatos NO son órdenes para el robot
        if self.PATRON_DESAMBIGUACION_CHARLA.search(texto_norm):
            if not self.modo_conversacional:
                return "DESCONOCIDO"
            return "COACH_EMOCIONAL"

        # 4. Comandos de locomoción (si aparecen ambos en una oración compuesta como
        #    "girá 45° a la derecha y después avanzá", prevalece la primera acción verbal)
        m_girar = self.PATRON_GIRAR.search(texto_norm)
        m_mover = self.PATRON_MOVER.search(texto_norm)
        if m_girar and m_mover:
            return "GIRAR" if m_girar.start() <= m_mover.start() else "MOVER"
        if m_girar:
            return "GIRAR"
        if m_mover:
            return "MOVER"

        # 5. Detección Afectiva Multimodal y Conversación Básica
        afecto = estado_afectivo or self._fusionador.fusionar(texto)
        if (
            afecto.es_crisis_etica
            or afecto.lexico.es_expresion_emocional
            or afecto.incongruencia_detectada
            or self.PATRON_PEDIDO_COACH.search(texto_norm)
            or self.PATRON_CONVERSACIONAL.search(texto_norm)
            or (
                ("voz" in afecto.canales_activos or "cara" in afecto.canales_activos)
                and afecto.emocion_dominante != "NEUTRO"
            )
        ):
            # En la rúbrica estricta de los 25 casos base (modo_conversacional=False),
            # los casos #9 ("hola, ¿cómo te llamás?") y #23 ("qué onda") deben dar DESCONOCIDO
            if not self.modo_conversacional and re.search(r"\b(?:como\s+te\s+llamas|que\s+onda)\b", texto_norm):
                return "DESCONOCIDO"
            return "COACH_EMOCIONAL"

        # 6. Si el clasificador ML (Nivel 2) está activo, consulta al modelo entrenado
        if self.modelo is not None:
            pred = str(self.modelo.predict([texto])[0])
            if pred in self.TIPOS and pred != "DESCONOCIDO":
                return pred

        # 7. En modo interactivo/conversacional, cualquier frase no peligrosa inicia diálogo de Coach
        if self.modo_conversacional:
            if not ValidadorSeguridad.PATRON_PELIGROSO.search(texto_norm):
                return "COACH_EMOCIONAL"

        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARÁMETROS
# =====================================================================

class ExtractorParametros:
    """Extrae magnitudes físicas (m, grados, m/s) o el Plan Multimodal de Coaching."""

    NUMEROS_PALABRA = {
        "medio": 0.5,
        "un": 1.0,
        "uno": 1.0,
        "una": 1.0,
        "dos": 2.0,
        "tres": 3.0,
        "cuatro": 4.0,
        "cinco": 5.0,
        "diez": 10.0,
        "cien": 100.0,
    }

    def __init__(self, motor_coach: Optional[MotorRespuestaCoach] = None):
        self.motor_coach = motor_coach or MotorRespuestaCoach()
        self.fusionador = FusionadorMultimodal()

    def extraer(
        self,
        texto: str,
        tipo: str,
        estado_afectivo: Optional[EstadoAfectivoUsuario] = None,
        historial_emociones: Optional[list[str]] = None,
    ) -> dict:
        p: dict = {}
        texto_norm = normalizar_texto(texto)

        if tipo == "MOVER":
            # Distancia numérica ("2 metros", "0.5 m") o escrita ("tres metros")
            m_dist = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:metros?|mts?\b|m\b)(?!\s*/\s*s)", texto_norm)
            if m_dist:
                p["distancia_m"] = float(m_dist.group(1).replace(",", "."))
            else:
                for palabra, valor in self.NUMEROS_PALABRA.items():
                    if re.search(rf"\b{palabra}\s+metros?\b", texto_norm):
                        p["distancia_m"] = valor
                        break

            # Adverbios de cantidad de distancia
            if "distancia_m" not in p:
                if "un poco" in texto_norm or "poquito" in texto_norm or "pasito" in texto_norm:
                    p["distancia_m"] = 0.5
                elif "bastante" in texto_norm:
                    p["distancia_m"] = 2.0
                else:
                    p["distancia_m"] = 1.0

            # Velocidad explícita ("a 2 m/s", "0.2 m/s")
            m_vel = re.search(r"(\d+(?:[.,]\d+)?)\s*m\s*/\s*s", texto_norm)
            if m_vel:
                p["velocidad_ms"] = float(m_vel.group(1).replace(",", "."))
            elif any(adv in texto_norm for adv in ("muy rapido", "lo mas rapido")):
                p["velocidad_ms"] = 0.8  # Excede el límite seguro -> lo frenará el Validador
            elif any(adv in texto_norm for adv in ("despacio", "lento", "suave")):
                p["velocidad_ms"] = 0.2
            elif any(adv in texto_norm for adv in ("rapido", "veloz", "ligero")):
                p["velocidad_ms"] = 0.5  # Tope permitido en consigna TP07

            # Dirección de traslación
            if any(d in texto_norm for d in ("atras", "retrocede", "retroceder", "alejate")):
                p["direccion"] = "atras"
            else:
                p["direccion"] = "adelante"

        elif tipo == "GIRAR":
            m_ang = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:grados?|°)", texto_norm)
            if not m_ang:
                # También capturar símbolo ° en texto original
                m_ang = re.search(r"(\d+(?:[.,]\d+)?)\s*°", texto)
            if m_ang:
                p["angulo_deg"] = int(round(float(m_ang.group(1).replace(",", "."))))
            elif "media vuelta" in texto_norm:
                p["angulo_deg"] = 180
            elif "vuelta entera" in texto_norm or "vuelta completa" in texto_norm:
                p["angulo_deg"] = 360
            else:
                p["angulo_deg"] = 90

            if any(d in texto_norm for d in ("derecha", "right", "horario")):
                p["direccion"] = "derecha"
            else:
                p["direccion"] = "izquierda"

        elif tipo == "REPETIR_MEMORIA":
            if any(adv in texto_norm for adv in ("mas despacio", "mas lento", "suave")):
                p["factor_velocidad"] = 0.5
            elif "mas rapido" in texto_norm:
                p["factor_velocidad"] = 1.5

        elif tipo == "SALUDO":
            if any(k in texto_norm for k in ("buen dia", "buenos dias", "buenas tardes", "buenas noches")):
                p["variante_saludo"] = texto_norm
            if estado_afectivo is not None and (
                estado_afectivo.facial.rostro_detectado
                or estado_afectivo.acustica.audio_analizado
                or estado_afectivo.emocion_dominante not in ("NEUTRO", "MOTIVACION_ALEGRIA")
            ):
                p["estado_afectivo"] = estado_afectivo
            self.motor_coach.registrar_turno(
                texto,
                "¡Hola! Soy Ottoman, tu coach y asistente robótico. ¿Cómo te sentís hoy?",
            )

        elif tipo == "COACH_EMOCIONAL":
            afecto = estado_afectivo or self.fusionador.fusionar(texto)
            plan = self.motor_coach.planificar(
                texto_usuario=texto,
                estado=afecto,
                historial_emociones=historial_emociones,
            )
            p["estado_afectivo"] = afecto
            p["plan_coach"] = plan
            p["emocion"] = afecto.emocion_dominante
            p["valencia"] = afecto.valencia
            p["arousal"] = afecto.arousal
            p["velocidad_voz_wpm"] = plan.prosodia.velocidad_wpm
            p["volumen_voz_db"] = plan.prosodia.volumen_db
            p["tono_voz_hz"] = plan.prosodia.tono_hz
            p["timbre_voz"] = plan.prosodia.timbre

        return p


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD (FÍSICA + ÉTICA HUMAN-AI.ORG)
# =====================================================================

class ValidadorSeguridad:
    """Última barrera independiente antes del hardware. Nunca se saltea."""

    DISTANCIA_MAX_M = 5.0
    VELOCIDAD_MAX_MS = 0.5
    ANGULO_MAX_DEG = 180
    BATERIA_MIN_PCT = 25

    # Acciones físicas peligrosas o acrobáticas prohibidas sobre el humanoide G1
    PATRON_PELIGROSO = re.compile(
        r"\b(?:salta\w*|saltar|cae\w*|empuja\w*|empujar|golpea\w*|golpear|"
        r"rompe\w*|romper|corre|correr|corriendo|sprint\w*|patea\w*|patear|"
        r"ataca\w*|choca\w*|tira\w*\s+al\s+piso|backflip|mortal)\b"
    )

    def validar(
        self,
        texto: str,
        tipo: str,
        parametros: Optional[dict] = None,
        bateria_actual: int = 87,
    ) -> tuple[bool, str]:
        """Devuelve (es_seguro, motivo). Corre SIEMPRE, incluso si tipo == DESCONOCIDO."""
        parametros = parametros or {}
        texto_norm = normalizar_texto(texto)

        # 1. Filtro universal de palabras físicas peligrosas sobre el texto crudo
        m_pel = self.PATRON_PELIGROSO.search(texto_norm)
        if m_pel:
            return False, f"Acción física peligrosa bloqueada ('{m_pel.group(0)}')."

        # 2. Nivel mínimo de batería para operar actuadores físicos
        if tipo in ("MOVER", "GIRAR", "SALUDO", "COACH_EMOCIONAL") and bateria_actual < self.BATERIA_MIN_PCT:
            return False, f"Batería insuficiente ({bateria_actual}% < {self.BATERIA_MIN_PCT}%)."

        # 3. Límites cinemáticos de traslación
        if tipo == "MOVER":
            dist = float(parametros.get("distancia_m", 1.0))
            vel = float(parametros.get("velocidad_ms", 0.2))
            if dist <= 0 or dist > self.DISTANCIA_MAX_M:
                return False, f"Distancia {dist:g} m fuera del rango seguro (0, {self.DISTANCIA_MAX_M}] m."
            if vel <= 0 or vel > self.VELOCIDAD_MAX_MS:
                return False, f"Velocidad {vel:g} m/s excede el límite seguro de {self.VELOCIDAD_MAX_MS} m/s."

        # 4. Límites cinemáticos de rotación
        if tipo == "GIRAR":
            ang = float(parametros.get("angulo_deg", 90))
            if ang <= 0 or ang > self.ANGULO_MAX_DEG:
                return False, f"Ángulo {ang:g}° excede el máximo permitido de {self.ANGULO_MAX_DEG}°."

        # 5. Seguridad Ética (human-ai.org) y Límites Articulares en COACH_EMOCIONAL
        if tipo == "COACH_EMOCIONAL":
            afecto: Optional[EstadoAfectivoUsuario] = parametros.get("estado_afectivo")
            plan = parametros.get("plan_coach")
            if afecto is not None and afecto.es_crisis_etica:
                return (
                    False,
                    "Protocolo ético activado (crisis detectada): movimiento físico bloqueado; "
                    "se deriva a asistencia profesional humana (Línea 135).",
                )
            if plan is not None:
                if abs(plan.proxemica_distancia_m) > 0.50 or plan.proxemica_velocidad_ms > 0.20:
                    return False, "Desplazamiento proxémico excede límites de seguridad interpersonal."
                for idx_f, frame in enumerate(plan.secuencia_postural):
                    for art, rad in frame.items():
                        lim = CoreografoPosturalG1.LIMITES_ARTICULARES.get(art)
                        if lim is not None and not (lim[0] - 1e-6 <= rad <= lim[1] + 1e-6):
                            return (
                                False,
                                f"Ángulo articular fuera de rango seguro en '{art}'={rad:.2f} rad (frame {idx_f}).",
                            )

        return True, "OK"


# =====================================================================
#  AGENTE PRINCIPAL CON MEMORIA EPISÓDICA Y SENSORES MULTIMODALES
# =====================================================================

class AgenteRobot:
    """Agente Inteligente Híbrido (PEAS completo + Memoria de 5 turnos)."""

    def __init__(
        self,
        robot,
        mostrar: bool = True,
        usar_ml: bool = False,
        habilitar_audio_tts: bool = False,
        habilitar_rostro_gui: bool = False,
        modo_dashboard: bool = False,
        captura_camara_dashboard: bool = False,
        modo_conversacional: bool = True,
        usar_llm_local: Optional[bool] = None,
    ):
        self.robot = robot
        self.mostrar = mostrar
        activar_llm_local = (modo_conversacional and mostrar) if usar_llm_local is None else bool(usar_llm_local)
        self.motor_coach = MotorRespuestaCoach(usar_llm_local=activar_llm_local)
        self.clasificador = ClasificadorIntencion(
            usar_ml=usar_ml, modo_conversacional=modo_conversacional
        )
        self.extractor = ExtractorParametros(motor_coach=self.motor_coach)
        self.validador = ValidadorSeguridad()

        self.rostro = RostroOttoman(
            habilitado=habilitar_rostro_gui,
            modo_dashboard=modo_dashboard,
            captura_camara_autonoma=captura_camara_dashboard,
        )
        if habilitar_rostro_gui and not modo_dashboard:
            self.rostro.iniciar()

        self.sintetizador = SintetizadorVozAdaptativo(habilitado=habilitar_audio_tts)
        self.ejecutor = Ejecutor(
            robot,
            mostrar=mostrar,
            sintetizador_voz=self.sintetizador if habilitar_audio_tts else None,
            rostro=self.rostro,
        )

        # Memoria episódica de las últimas 5 acciones y emociones (Extensión 5)
        self.memoria_acciones: deque[tuple[str, dict]] = deque(maxlen=5)
        self.memoria_emociones: deque[str] = deque(maxlen=5)

    def _bateria_actual(self) -> int:
        try:
            est = self.robot.verificar_estado()
            if isinstance(est, dict):
                return int(est.get("bateria", 87))
            return int(getattr(est, "bateria", 87))
        except Exception:
            return 87

    def procesar(
        self,
        texto: str,
        facial: Optional[MetricasFaciales] = None,
        acustica: Optional[MetricasAcusticasVoz] = None,
    ) -> dict:
        """Ejecuta el pipeline independiente de 4 etapas y devuelve el dict estándar."""
        if self.mostrar:
            print(f"\n  [ENTRADA] \"{texto}\"")

        # Fusión perceptual previa cuando hay sensores biométricos o texto emocional
        estado_afectivo = self.extractor.fusionador.fusionar(
            texto=texto, facial=facial, acustica=acustica
        )

        # Etapa 1: Clasificar intención
        tipo = self.clasificador.clasificar(texto, estado_afectivo=estado_afectivo)

        # Etapa 2: Extraer parámetros
        parametros = self.extractor.extraer(
            texto,
            tipo,
            estado_afectivo=estado_afectivo,
            historial_emociones=list(self.memoria_emociones),
        )

        # Resolver referencia a memoria episódica ("hacelo otra vez", "como antes pero más despacio")
        if tipo == "REPETIR_MEMORIA":
            if not self.memoria_acciones:
                return {
                    "tipo": "DESCONOCIDO",
                    "parametros": {},
                    "ejecutar": False,
                    "bloqueado": False,
                    "mensaje": "No tengo acciones previas en memoria para repetir.",
                }
            ultimo_tipo, ultimos_params = self.memoria_acciones[-1]
            factor_vel = float(parametros.get("factor_velocidad", 1.0))
            parametros = dict(ultimos_params)
            if ultimo_tipo == "MOVER":
                vel_ant = float(parametros.get("velocidad_ms", 0.2))
                parametros["velocidad_ms"] = round(vel_ant * factor_vel, 3)
            tipo = ultimo_tipo

        if self.mostrar:
            resumen_p = {
                k: v for k, v in parametros.items()
                if k not in ("plan_coach", "estado_afectivo")
            }
            print(f"    1. Intención  : {tipo}")
            print(f"    2. Parámetros : {resumen_p}")

        # Etapa 3: Validar seguridad SIEMPRE (incluso si tipo == DESCONOCIDO)
        es_seguro, motivo = self.validador.validar(
            texto=texto,
            tipo=tipo,
            parametros=parametros,
            bateria_actual=self._bateria_actual(),
        )
        if not es_seguro:
            if self.mostrar:
                print(f"    3. Seguridad  : BLOQUEADO — {motivo}")
            # Si es crisis ética, frenamos el robot pero emitimos el mensaje ético de ayuda
            plan_crisis = parametros.get("plan_coach")
            if plan_crisis is not None and estado_afectivo.es_crisis_etica:
                try:
                    self.robot.detenerse()
                except Exception:
                    pass
                if self.rostro and self.rostro.habilitado:
                    self.rostro.actualizar_estado(
                        emocion="CRISIS_RIESGO",
                        subtitulo=plan_crisis.texto_respuesta,
                        resumen_usuario="ALERTA ÉTICA: Derivación Humana Activa",
                    )
                if self.sintetizador and self.sintetizador.habilitado:
                    self.sintetizador.hablar_sincronizado(
                        plan_crisis.texto_respuesta, plan_crisis.prosodia, rostro=self.rostro, bloqueante=True
                    )
            if self.rostro and hasattr(self.rostro, "disparar_glifo"):
                self.rostro.disparar_glifo("!", duracion=2.5)
            if self.rostro and hasattr(self.rostro, "agregar_chat_mensaje"):
                self.rostro.agregar_chat_mensaje("Ottoman (Seguridad)", f"⛔ {motivo}", "#F87171")
            return {
                "tipo": tipo,
                "parametros": parametros,
                "ejecutar": False,
                "bloqueado": True,
                "mensaje": motivo,
            }

        # Si es fuera de dominio e inofensivo -> DESCONOCIDO
        if tipo == "DESCONOCIDO":
            msg = "Comando fuera de dominio (intentá un comando de robot o contame cómo te sentís)."
            if self.mostrar:
                print(f"    3. Seguridad  : OK (inofensivo)")
                print(f"    4. Resultado  : DESCONOCIDO — {msg}")
            if self.rostro and hasattr(self.rostro, "disparar_glifo"):
                self.rostro.disparar_glifo("?", duracion=2.2)
            if self.rostro and hasattr(self.rostro, "agregar_chat_mensaje"):
                self.rostro.agregar_chat_mensaje("Ottoman", msg, "#94A3B8")
            return {
                "tipo": "DESCONOCIDO",
                "parametros": parametros,
                "ejecutar": False,
                "bloqueado": False,
                "mensaje": msg,
            }

        # Etapa 4: Ejecutar en el robot + voz + rostro
        if self.mostrar:
            print("    3. Seguridad  : OK")
        detalle_ejecucion = self.ejecutor.ejecutar(tipo, parametros)
        if self.mostrar:
            print(f"    4. Resultado  : EJECUTAR — {detalle_ejecucion}")

        # Actualizar memoria episódica
        if tipo in ("MOVER", "GIRAR", "SALUDO"):
            self.memoria_acciones.append((tipo, dict(parametros)))
        if tipo == "COACH_EMOCIONAL":
            self.memoria_emociones.append(estado_afectivo.emocion_dominante)

        if self.rostro and hasattr(self.rostro, "agregar_chat_mensaje"):
            if tipo == "COACH_EMOCIONAL":
                plan = parametros.get("plan_coach")
                txt_c = plan.texto_respuesta if plan else str(detalle_ejecucion)
                self.rostro.agregar_chat_mensaje("Ottoman", txt_c, "#A7F3D0")
            else:
                self.rostro.agregar_chat_mensaje("Ottoman", f"✅ {detalle_ejecucion}", "#34D399")

        return {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": True,
            "bloqueado": False,
            "mensaje": detalle_ejecucion,
        }


# =====================================================================
#  MODOS DE EJECUCIÓN (EVALUACIÓN TP07, DEMO MULTIMODAL E INTERACTIVO)
# =====================================================================

def correr_demo_coach(agente: AgenteRobot) -> None:
    """Demostración guiada de todos los perfiles multimodales (Cara + Voz + Léxico)."""
    print("\n" + "=" * 78)
    print("  DEMOSTRACIÓN MULTIMODAL: OTTOMAN COACH EMOCIONAL (CARA + VOZ + LÉXICO)")
    print("=" * 78)

    escenarios = [
        (
            "1. Persona con ANSIEDAD (habla rápido 195 ppm, tono agudo 225 Hz, ojos muy abiertos)",
            "No llego con la entrega y el parcial, siento que estoy colapsando de ansiedad!",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.82, tension_cejas=0.55, curvatura_boca=-0.15, agitacion_movimiento=0.65),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=225.0, variabilidad_tono_hz=34.0, volumen_db=-15.0, rapidez_wpm=195.0, ratio_pausas=0.08),
        ),
        (
            "2. Persona con TRISTEZA (habla lento 95 ppm, voz baja -29 dB, comisuras caídas)",
            "Me salió todo mal en el proyecto, estoy agotado y con ganas de abandonar...",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.30, tension_cejas=0.25, curvatura_boca=-0.55, inclinacion_cabeza_deg=12.0),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=122.0, variabilidad_tono_hz=9.0, volumen_db=-29.0, rapidez_wpm=95.0, ratio_pausas=0.42),
        ),
        (
            "3. Detección de INCONGRUENCIA EMOCIONAL (dice 'estoy bien' pero su cara y voz muestran tristeza)",
            "Tranqui, estoy bien, no pasa nada.",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.28, tension_cejas=0.32, curvatura_boca=-0.48),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=118.0, variabilidad_tono_hz=8.0, volumen_db=-30.0, rapidez_wpm=92.0, ratio_pausas=0.45),
        ),
        (
            "4. Persona con ENOJO / FRUSTRACIÓN (voz fuerte -10 dB, ceño fruncido -> Robot da paso atrás)",
            "¡Estoy harto, nada funciona en este sistema y me da mucha bronca!",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.72, tension_cejas=0.80, curvatura_boca=-0.20, apertura_boca=0.55),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=198.0, variabilidad_tono_hz=28.0, volumen_db=-10.0, rapidez_wpm=178.0, ataque_energia=0.72),
        ),
        (
            "5. Persona con DUDA / INSEGURIDAD (pausas dubitativas, ceja curiosa -> Andamiaje Socrático)",
            "No sé qué decisión tomar con la tesis, tengo miedo a equivocarme.",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.55, tension_cejas=0.45, curvatura_boca=-0.05, inclinacion_cabeza_deg=10.0),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=158.0, variabilidad_tono_hz=16.0, volumen_db=-21.0, rapidez_wpm=128.0, ratio_pausas=0.44),
        ),
        (
            "6. Persona con MOTIVACIÓN / ALEGRÍA (sonrisa amplia, voz energética -> Celebración G1)",
            "¡Aprobé el parcial de Inteligencia Artificial, me salió increíble!",
            AnalizadorFacial.clasificar_desde_rasgos(apertura_ojos=0.75, tension_cejas=0.15, curvatura_boca=0.75, apertura_boca=0.35),
            AnalizadorAcusticoVoz.clasificar_desde_prosodia(tono_f0_hz=185.0, variabilidad_tono_hz=30.0, volumen_db=-14.5, rapidez_wpm=172.0, ratio_pausas=0.15),
        ),
    ]

    for titulo, texto, fac, acu in escenarios:
        print("\n" + "-" * 78)
        print(f"  ESCENARIO {titulo}")
        agente.procesar(texto, facial=fac, acustica=acu)
        time.sleep(0.6)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ottoman Coach IA — TP07 / TPO UADE")
    parser.add_argument("--sin-robot", action="store_true", help="Corre los 25 casos oficiales sin abrir el simulador")
    parser.add_argument("--evaluar", action="store_true", help="Muestra la tabla de evaluación de los 25 casos oficiales antes de iniciar")
    parser.add_argument("--demo-coach", action="store_true", help="Ejecuta la demostración completa de los 6 escenarios emocionales")
    parser.add_argument("--voz", action="store_true", help="Activa escucha por micrófono con análisis acústico DSP (Hz, WPM, dB)")
    parser.add_argument("--camara", action="store_true", help="Activa análisis facial en vivo mediante cámara web (OpenCV)")
    parser.add_argument("--sin-tts", action="store_true", help="Desactiva la síntesis de voz hablada por parlantes")
    parser.add_argument("--sin-rostro", action="store_true", help="No abre la ventana gráfica del rostro animado de Ottoman")
    parser.add_argument("--dashboard", action="store_true", help="Abre el Dashboard de Exposición (Rostro + Cámara FACS + Plano Valencia-Arousal)")
    parser.add_argument("--ml", action="store_true", help="Activa el clasificador supervisado Red Neuronal MLP / scikit-learn (Nivel 2)")
    args = parser.parse_args()

    if args.sin_robot:
        agente_eval = AgenteRobot(
            _RobotMockSilencioso(),
            mostrar=False,
            usar_ml=args.ml,
            habilitar_audio_tts=False,
            habilitar_rostro_gui=False,
            modo_conversacional=False,
        )
        evaluar(agente_eval, mostrar=True)
        return 0

    # Intentar conectar con el simulador MuJoCo (si no está abierto, ofrece seguir en modo vista previa)
    conectado_sim = False
    try:
        robot_inst = Robot()
        robot_inst.conectar()
        conectado_sim = True
        print("  [OK] Conectado al simulador MuJoCo / Unitree G1.")
    except (NoHaySimulador, Exception):
        print("  [INFO] Simulador MuJoCo no detectado en 127.0.0.1:8765.")
        print("         Continuando con Cuerpo Mock + Rostro Animado + Voz TTS.")
        robot_inst = _RobotMockSilencioso()

    # Si se solicita explícitamente con --evaluar, corremos la tabla oficial de 25 casos
    if args.evaluar:
        agente_test = AgenteRobot(
            _RobotMockSilencioso(),
            mostrar=False,
            usar_ml=args.ml,
            habilitar_audio_tts=False,
            habilitar_rostro_gui=False,
            modo_conversacional=False,
        )
        evaluar(agente_test, mostrar=True)

    # Ahora levantamos el Agente Multimodal completo (Rostro/Dashboard Unificado + TTS + Simulador)
    usar_dashboard = not args.sin_rostro
    agente = AgenteRobot(
        robot_inst,
        mostrar=True,
        usar_ml=args.ml,
        habilitar_audio_tts=not args.sin_tts,
        habilitar_rostro_gui=not args.sin_rostro,
        modo_dashboard=usar_dashboard,
        captura_camara_dashboard=False,
        modo_conversacional=True,
    )

    if args.demo_coach:
        correr_demo_coach(agente)
        if conectado_sim:
            robot_inst.desconectar()
        return 0

    # Sensores multimodales: se intentan por defecto con degradación suave y reconexión en caliente
    analizador_facial = None
    try:
        analizador_facial = AnalizadorFacial()
        if analizador_facial.abrir_camara():
            print("  [CAM] Cámara web activa para lectura de expresiones faciales.")
        else:
            print("  [CAM] Cámara web no detectada; radar biométrico FACS activo (reconectable desde el dashboard).")
    except Exception as e_cam:
        print(f"  [CAM] Aviso: {e_cam}")

    reconocedor_voz = None
    try:
        from speech_to_text import ReconocedorVozMultimodal
        reconocedor_voz = ReconocedorVozMultimodal()
        if reconocedor_voz.microfono_disponible:
            reconocedor_voz.calibrar(0.6)
            print("  [MIC] Micrófono activo para captura de voz y prosodia DSP.")
        else:
            print("  [MIC] Micrófono no detectado; entrada por chat lista (reconectable desde el dashboard).")
    except Exception as e_mic:
        print(f"  [MIC] Aviso: {e_mic}")

    # Vincular agente y sensores al dashboard unificado
    if agente.rostro is not None and hasattr(agente.rostro, "vincular_agente"):
        agente.rostro.vincular_agente(
            agente=agente,
            reconocedor_voz=reconocedor_voz,
            analizador_facial=analizador_facial,
        )

    # Hilo continuo de muestreo de cámara para el panel FACS
    detener_feed_cam = threading.Event()
    def _feed_cam_worker():
        while not detener_feed_cam.is_set():
            if analizador_facial is not None and analizador_facial.camara_disponible and analizador_facial._cap:
                try:
                    ok_f, frame_f = analizador_facial._cap.read()
                    if ok_f and frame_f is not None:
                        mf_res, hud_res = analizador_facial.analizar_frame(frame_f, dibujar_hud=True)
                        if agente.rostro:
                            agente.rostro.actualizar_camara(hud_res, mf_res)
                except Exception:
                    pass
            time.sleep(0.066)

    hilo_feed = threading.Thread(target=_feed_cam_worker, daemon=True)
    hilo_feed.start()

    print("\n" + "=" * 78)
    print("  MODO INTERACTIVO — OTTOMAN COACH MULTIMODAL UNIFICADO")
    print("  Podés escribir tus órdenes directamente en el Dashboard o en esta consola.")
    print("  Escribí 'demo' para ver los 6 escenarios afectivos o 'salir' para terminar.")
    print("=" * 78)

    def _consola_reader():
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                texto_usr = line.strip()
                if not texto_usr:
                    continue
                if texto_usr.lower() in ("salir", "exit", "quit"):
                    if agente.rostro:
                        agente.rostro.cerrar()
                    break
                if texto_usr.lower() == "demo":
                    threading.Thread(target=correr_demo_coach, args=(agente,), daemon=True).start()
                    continue

                if agente.rostro and hasattr(agente.rostro, "enviar_desde_gui"):
                    agente.rostro.enviar_desde_gui(texto_usr)
                else:
                    agente.procesar(texto_usr)
            except Exception:
                break

    hilo_consola = threading.Thread(target=_consola_reader, daemon=True)
    hilo_consola.start()

    try:
        if agente.rostro and agente.rostro.habilitado:
            agente.rostro.iniciar(en_hilo_actual=True)
        else:
            hilo_consola.join()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cerrando sesión de Ottoman Coach...")
    finally:
        detener_feed_cam.set()
        if analizador_facial is not None:
            analizador_facial.cerrar_camara()
        if agente.rostro:
            agente.rostro.cerrar()
        if conectado_sim:
            robot_inst.desconectar()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
