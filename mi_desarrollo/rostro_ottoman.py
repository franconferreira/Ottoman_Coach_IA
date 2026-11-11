"""Rostro Digital Animado, Simulador 3D Embebido y Modo Dashboard Unificado para Ottoman (Unitree G1).

El Unitree G1 cuenta físicamente con un visor oscuro sin rasgos faciales móviles.
En Interacción Humano-Robot (HRI), dotar al agente de una interfaz facial expresiva
aumenta significativamente la confianza, la alianza terapéutica y la legibilidad
de sus intenciones afectivas (Breazeal, MIT Media Lab; principios human-ai.org).

Esta implementación unifica en UNA SOLA PANTALLA (1380x870):
  1. Panel Izquierdo: Simulador Físico 3D Unitree G1 (render MuJoCo cinemático offscreen a 35 FPS
     con seguimiento de cámara, marcha en dos patas, giro, saludo y posturas afectivas).
  2. Panel Central: Interfaz Afectiva — Rostro de Ottoman (ojos, cejas, Lip-Sync, halo
     respiratorio de co-regulación y alerta de enmascaramiento afectivo).
  3. Panel Superior Derecho: Visión FACS OpenCV (webcam en vivo o radar biométrico FACS).
  4. Panel Inferior Derecho: Plano Valencia-Arousal en tiempo real (Modelo de Russell).
  5. Barra de Sensores y Hot-Reconnect: Estado dinámico de cámara, micrófono y robot con
     botones de reconexión en caliente y reseteo de posición.
  6. Panel Inferior de Chat Interactivo: Subtítulos, telemetría acústica/FACS, historial
     de conversación, campo de texto con tecla Enter, botón Enviar, botón Hablar y accesos rápidos.
"""

from __future__ import annotations

import math
import queue
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class PresetFacialRobot:
    """Geometría y cromática objetivo del rostro de Ottoman para cada estado.
    
    Inspirado en la morfología de robot humanoide con visor OLED y ojos LED puros
    (estilo EVE / Cozmo), sin boca ni cejas antropomórficas.
    """
    nombre: str
    color_rgb: tuple[int, int, int]
    apertura_ojo: float       # 0.20 (semicerrado calmo) .. 1.15 (abierto vivo)
    arco_feliz: float         # 0.0 (cápsula normal) .. 1.0 (ojo sonriente ^ ^)
    angulo_ceja_izq: float = 0.0    # retrocompatibilidad
    angulo_ceja_der: float = 0.0    # retrocompatibilidad
    altura_ceja: float = 0.0        # retrocompatibilidad
    curvatura_boca: float = 0.0     # retrocompatibilidad
    guia_respiracion: bool = False  # modulación orgánica de inhalar/exhalar
    intervalo_parpadeo: float = 4.0 # segundos promedio entre parpadeos
    # Parámetros geométricos del visor y ojos LED
    forma_ojo: str = "capsula"      # capsula | arco_feliz | diagonal_enojo | caido_triste | asimetrico_duda | suave_calma | chispa_estrella | entrecerrado_enfoque | ojo_circular_asombro
    inclinacion_ojo: float = 0.0    # grados (+ hacia adentro, - hacia afuera)
    ancho_ojo: float = 72.0         # ancho base del LED en px (modo ojos gigantes)
    alto_ojo: float = 120.0         # alto base del LED en px (modo ojos gigantes)
    escala_asimetrica: float = 1.0  # escala del ojo izquierdo para guiños y asimetría reflexiva
    glifo: Optional[str] = None     # None | "!" | "?" (glifos de personalidad heroica)


PRESETS_ROSTRO: dict[str, PresetFacialRobot] = {
    "NEUTRO": PresetFacialRobot(
        nombre="Escucha Atenta",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.92,
        arco_feliz=0.0,
        angulo_ceja_izq=2.0,
        angulo_ceja_der=-2.0,
        altura_ceja=0.0,
        curvatura_boca=0.22,
        guia_respiracion=False,
        intervalo_parpadeo=4.0,
        forma_ojo="capsula",
        inclinacion_ojo=2.0,
        ancho_ojo=72.0,
        alto_ojo=120.0,
        escala_asimetrica=1.0,
    ),
    "ANSIEDAD_ESTRES": PresetFacialRobot(
        nombre="Co-regulación y Calma Respiratoria",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.74,
        arco_feliz=0.15,
        angulo_ceja_izq=8.0,
        angulo_ceja_der=-8.0,
        altura_ceja=-4.0,
        curvatura_boca=0.28,
        guia_respiracion=True,
        intervalo_parpadeo=5.2,
        forma_ojo="suave_calma",
        inclinacion_ojo=0.0,
        ancho_ojo=78.0,
        alto_ojo=106.0,
        escala_asimetrica=1.0,
    ),
    "TRISTEZA_DESANIMO": PresetFacialRobot(
        nombre="Empatía Cálida y Contención",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.85,
        arco_feliz=0.0,
        angulo_ceja_izq=0.0,
        angulo_ceja_der=0.0,
        altura_ceja=0.0,
        curvatura_boca=0.20,
        guia_respiracion=False,
        intervalo_parpadeo=4.5,
        forma_ojo="parpado_inferior_calido",
        inclinacion_ojo=0.0,
        ancho_ojo=74.0,
        alto_ojo=112.0,
        escala_asimetrica=1.0,
    ),
    "ENOJO_FRUSTRACION": PresetFacialRobot(
        nombre="Serenidad Ecuánime (Desescalada)",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.86,
        arco_feliz=0.0,
        angulo_ceja_izq=4.0,
        angulo_ceja_der=-4.0,
        altura_ceja=2.0,
        curvatura_boca=0.12,
        guia_respiracion=False,
        intervalo_parpadeo=4.2,
        forma_ojo="diagonal_enojo",
        inclinacion_ojo=18.0,
        ancho_ojo=74.0,
        alto_ojo=110.0,
        escala_asimetrica=1.0,
    ),
    "DUDA_INSEGURIDAD": PresetFacialRobot(
        nombre="Mentoría Estructurada",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.88,
        arco_feliz=0.0,
        angulo_ceja_izq=6.0,
        angulo_ceja_der=-6.0,
        altura_ceja=-4.0,
        curvatura_boca=0.20,
        guia_respiracion=False,
        intervalo_parpadeo=3.8,
        forma_ojo="entrecerrado_enfoque",
        inclinacion_ojo=4.0,
        ancho_ojo=74.0,
        alto_ojo=118.0,
        escala_asimetrica=1.0,
    ),
    "MOTIVACION_ALEGRIA": PresetFacialRobot(
        nombre="Celebración y Entusiasmo",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=1.05,
        arco_feliz=0.88,               # Ojos felices arqueados (^ ^)
        angulo_ceja_izq=-6.0,
        angulo_ceja_der=6.0,
        altura_ceja=-10.0,
        curvatura_boca=0.90,
        guia_respiracion=False,
        intervalo_parpadeo=3.2,
        forma_ojo="arco_feliz",
        inclinacion_ojo=0.0,
        ancho_ojo=84.0,
        alto_ojo=96.0,
        escala_asimetrica=1.0,
    ),
    "CRISIS_RIESGO": PresetFacialRobot(
        nombre="Protocolo de Contención Ética",
        color_rgb=(56, 189, 248),      # Azul signature constante (#38BDF8)
        apertura_ojo=0.78,
        arco_feliz=0.0,
        angulo_ceja_izq=12.0,
        angulo_ceja_der=-12.0,
        altura_ceja=-2.0,
        curvatura_boca=0.15,
        guia_respiracion=True,
        intervalo_parpadeo=4.8,
        forma_ojo="suave_calma",
        inclinacion_ojo=-4.0,
        ancho_ojo=74.0,
        alto_ojo=102.0,
        escala_asimetrica=1.0,
    ),
    "ASOMBRO": PresetFacialRobot(
        nombre="Sorpresa Abierta",
        color_rgb=(56, 189, 248),
        apertura_ojo=1.20,
        arco_feliz=0.0,
        guia_respiracion=False,
        forma_ojo="ojo_circular_asombro",
        inclinacion_ojo=0.0,
        ancho_ojo=92.0,
        alto_ojo=120.0,
    ),
    "EUREKA": PresetFacialRobot(
        nombre="Chispa Eureka / Logro",
        color_rgb=(56, 189, 248),
        apertura_ojo=1.15,
        arco_feliz=0.0,
        guia_respiracion=False,
        forma_ojo="chispa_estrella",
        inclinacion_ojo=0.0,
        ancho_ojo=88.0,
        alto_ojo=118.0,
    ),
    "ALERTA": PresetFacialRobot(
        nombre="Énfasis Heroico (!)",
        color_rgb=(56, 189, 248),
        apertura_ojo=1.0,
        arco_feliz=0.0,
        guia_respiracion=False,
        forma_ojo="capsula",
        glifo="!",
    ),
    "PREGUNTA": PresetFacialRobot(
        nombre="Interrogación Curiosa (?)",
        color_rgb=(56, 189, 248),
        apertura_ojo=1.0,
        arco_feliz=0.0,
        guia_respiracion=False,
        forma_ojo="capsula",
        glifo="?",
    ),
    "ENFOQUE": PresetFacialRobot(
        nombre="Análisis Táctico / Enfoque",
        color_rgb=(56, 189, 248),
        apertura_ojo=0.85,
        arco_feliz=0.0,
        guia_respiracion=False,
        forma_ojo="entrecerrado_enfoque",
        ancho_ojo=80.0,
        alto_ojo=110.0,
    ),
    "CALMA": PresetFacialRobot(
        nombre="Serenidad Zen (/ \\)",
        color_rgb=(56, 189, 248),
        apertura_ojo=0.74,
        arco_feliz=0.0,
        guia_respiracion=True,
        forma_ojo="suave_calma",
        ancho_ojo=78.0,
        alto_ojo=106.0,
    ),
}

# Aliases sinónimos para robustez conversacional y HRI
PRESETS_ROSTRO["ALEGRIA"] = PRESETS_ROSTRO["MOTIVACION_ALEGRIA"]
PRESETS_ROSTRO["FELICIDAD"] = PRESETS_ROSTRO["MOTIVACION_ALEGRIA"]
PRESETS_ROSTRO["EMPATIA"] = PRESETS_ROSTRO["TRISTEZA_DESANIMO"]


def _rgb_hex(rgb: tuple[float, float, float]) -> str:
    r = int(max(0, min(255, round(rgb[0]))))
    g = int(max(0, min(255, round(rgb[1]))))
    b = int(max(0, min(255, round(rgb[2]))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# =====================================================================
#  SIMULADOR FÍSICO CINEMÁTICO 3D EMBEBIDO (UNITREE G1 - 29 DoF)
# =====================================================================

class SimuladorEmbebidoG1:
    """Simulador visual 3D embebido del humanoide Unitree G1.
    
    Renderiza offscreen mediante MuJoCo en tiempo real (~35 FPS) dentro de la interfaz.
    Soporta marcha bípeda cinemática, giro en el lugar, saludo y secuencias posturales
    afectivas (inclinación de torso, elevación de brazos, manos abiertas, pulgares).
    """

    def __init__(self, ancho: int = 428, alto: int = 380):
        self.ancho = ancho
        self.alto = alto
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.altura = 0.793
        self.accion = "quieto"       # quieto | caminando | girando | saludando | postura
        self.bateria = 87
        self.distancia_total = 0.0

        self._vel_lin = 0.0
        self._vel_ang = 0.0
        self._tiempo_restante = 0.0
        self._fase_marcha = 0.0
        self._saludo_hasta = 0.0
        self._secuencia_pasos: list[dict[str, float]] = []
        self._paso_actual_idx = 0
        self._tiempo_paso_restante = 0.0
        self._duracion_step = 0.5
        self._pose_actual: dict[str, float] = {}
        self._pose_objetivo: dict[str, float] = {}
        self._ultimo_tiempo = time.monotonic()
        self._lock = threading.Lock()

        self.hablando: bool = False
        self.valencia: float = 0.0
        self.arousal: float = 0.0
        self.energia_habla: float = 1.0
        self._fase_gesto: float = 0.0
        
        # Animación teatral (Show Action Sequencing)
        self._secuencia_actual: list[dict[str, float]] = []
        self._idx_secuencia = 0
        self._duracion_step = 0.7
        self._ultimo_tiempo_pose = time.monotonic()

        self._pose_base: dict[str, float] = {
            "waist_pitch": 0.0,
            "waist_roll": 0.0,
            "waist_yaw": 0.0,
            "left_shoulder_pitch": 0.42,
            "right_shoulder_pitch": 0.42,
            "left_shoulder_roll": 0.08,
            "right_shoulder_roll": -0.08,
            "left_elbow": 0.28,
            "right_elbow": 0.28,
            "left_wrist_roll": -1.25,
            "right_wrist_roll": 1.25,
            "manos": 0.05,
        }

        # Recursos MuJoCo
        self._disponible = False
        self._model = None
        self._data = None
        self._renderer = None
        self._camera = None
        self._jmap: dict[str, int] = {}
        self._inicializar_mujoco()

    def _inicializar_mujoco(self) -> bool:
        try:
            import mujoco
            base = Path(__file__).resolve().parent.parent
            rutas = [
                base / "entorno" / "sim" / "unitree_mujoco" / "unitree_robots" / "g1" / "scene_29dof.xml",
                Path.cwd() / "entorno" / "sim" / "unitree_mujoco" / "unitree_robots" / "g1" / "scene_29dof.xml",
            ]
            xml_path = None
            for r in rutas:
                if r.exists():
                    xml_path = str(r.resolve())
                    break
            if not xml_path:
                return False

            self._model = mujoco.MjModel.from_xml_path(xml_path)
            self._data = mujoco.MjData(self._model)
            self._model.opt.gravity[:] = 0.0

            # Mapear nombres de articulaciones a sus índices en qpos
            self._jmap = {}
            for i in range(self._model.njnt):
                nombre = mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, i)
                if nombre:
                    adr = int(self._model.jnt_qposadr[i])
                    self._jmap[nombre] = adr
                    if nombre.endswith("_joint"):
                        self._jmap[nombre[:-6]] = adr

            # Pose de pie estándar inicial (postura natural relajada)
            self._data.qpos[2] = self.altura
            if "left_shoulder_pitch" in self._jmap:
                self._data.qpos[self._jmap["left_shoulder_pitch"]] = 0.42
            if "right_shoulder_pitch" in self._jmap:
                self._data.qpos[self._jmap["right_shoulder_pitch"]] = 0.42
            if "left_shoulder_roll" in self._jmap:
                self._data.qpos[self._jmap["left_shoulder_roll"]] = 0.08
            if "right_shoulder_roll" in self._jmap:
                self._data.qpos[self._jmap["right_shoulder_roll"]] = -0.08
            if "left_elbow" in self._jmap:
                self._data.qpos[self._jmap["left_elbow"]] = 0.28
            if "right_elbow" in self._jmap:
                self._data.qpos[self._jmap["right_elbow"]] = 0.28

            mujoco.mj_forward(self._model, self._data)

            self._renderer = None
            self._camera = None
            self._disponible = True
            return True
        except Exception:
            self._disponible = False
            return False

    def fijar_estado_habla(self, hablando: bool, energia: float = 1.0) -> None:
        with self._lock:
            self.hablando = hablando
            self.energia_habla = max(0.4, min(2.0, float(energia)))

    def fijar_estado_afectivo(self, valencia: float, arousal: float) -> None:
        with self._lock:
            self.valencia = max(-1.0, min(1.0, float(valencia)))
            self.arousal = max(-1.0, min(1.0, float(arousal)))

    def fijar_coreografia(self, secuencia: list[dict[str, float]], duracion: float = 0.7) -> None:
        if not secuencia:
            return
        with self._lock:
            self._secuencia_actual = list(secuencia)
            self._idx_secuencia = 0
            self._duracion_step = max(0.3, float(duracion))
            self._ultimo_tiempo_pose = time.monotonic()
            self.accion = "animacion"

    def avanzar(self, velocidad: float = 0.2, tiempo: float = 1.0) -> None:
        with self._lock:
            self._vel_lin = float(velocidad)
            self._tiempo_restante = float(tiempo)
            self.accion = "caminando"

    def girar(self, velocidad: float = 0.5, tiempo: float = 1.0) -> None:
        with self._lock:
            self._vel_ang = float(velocidad)
            self._tiempo_restante = float(tiempo)
            self.accion = "girando"

    def detener(self) -> None:
        with self._lock:
            self._vel_lin = 0.0
            self._vel_ang = 0.0
            self._tiempo_restante = 0.0
            self._secuencia_pasos = []
            self.accion = "quieto"

    def saludar(self, duracion: float = 3.5) -> None:
        with self._lock:
            self._saludo_hasta = time.monotonic() + duracion
            self.accion = "saludando"

    def ejecutar_secuencia(self, secuencia: list[dict[str, float]], duracion_step: float = 0.5) -> None:
        if not secuencia:
            return
        with self._lock:
            self._secuencia_actual = list(secuencia)
            self._idx_secuencia = 0
            self._duracion_step = max(0.2, float(duracion_step))
            self._ultimo_tiempo_pose = time.monotonic()
            self._secuencia_pasos = list(secuencia)
            self._paso_actual_idx = 0
            self._tiempo_paso_restante = self._duracion_step
            self.accion = "animacion"
            self._pose_objetivo = dict(secuencia[0])

    def resetear_posicion(self) -> None:
        with self._lock:
            self.x = 0.0
            self.y = 0.0
            self.yaw = 0.0
            self.accion = "quieto"
            self._vel_lin = 0.0
            self._vel_ang = 0.0
            self._tiempo_restante = 0.0
            self._secuencia_pasos = []
            self._secuencia_actual = []
            self._pose_actual.clear()
            self._pose_objetivo.clear()

    def update(self) -> Optional[np.ndarray]:
        """Avanza cinemática, interpola articulaciones y devuelve frame RGB renderizado."""
        ahora = time.monotonic()
        dt = min(0.08, max(0.001, ahora - self._ultimo_tiempo))
        self._ultimo_tiempo = ahora

        with self._lock:
            if self.accion == "caminando":
                self._tiempo_restante -= dt
                self._fase_marcha = (self._fase_marcha + dt * 5.2) % (2.0 * math.pi)
                dx = self._vel_lin * math.cos(self.yaw) * dt
                dy = self._vel_lin * math.sin(self.yaw) * dt
                self.x += dx
                self.y += dy
                self.distancia_total += abs(self._vel_lin) * dt
                if self._tiempo_restante <= 0.0:
                    self.accion = "quieto"
                    self._vel_lin = 0.0
            elif self.accion == "girando":
                self._tiempo_restante -= dt
                self.yaw += self._vel_ang * dt
                self._fase_marcha = (self._fase_marcha + dt * 4.5) % (2.0 * math.pi)
                if self._tiempo_restante <= 0.0:
                    self.accion = "quieto"
                    self._vel_ang = 0.0
            elif self.accion == "saludando":
                if ahora >= self._saludo_hasta:
                    self.accion = "quieto"
            elif self.accion == "postura":
                if self._secuencia_pasos:
                    self._tiempo_paso_restante -= dt
                    if self._tiempo_paso_restante <= 0.0:
                        self._paso_actual_idx += 1
                        if self._paso_actual_idx < len(self._secuencia_pasos):
                            self._pose_objetivo = dict(self._secuencia_pasos[self._paso_actual_idx])
                            self._tiempo_paso_restante = self._duracion_step
                        else:
                            self.accion = "quieto"
                            self._secuencia_pasos = []

            if not self._disponible or self._model is None or self._data is None:
                return None

            try:
                import mujoco

                # Posición y orientación de la base móvil
                self._data.qpos[0] = self.x
                self._data.qpos[1] = self.y
                self._data.qpos[2] = self.altura
                self._data.qpos[3] = math.cos(self.yaw / 2.0)
                self._data.qpos[4] = 0.0
                self._data.qpos[5] = 0.0
                self._data.qpos[6] = math.sin(self.yaw / 2.0)

                # Animación cinemática según el estado
                if self.accion == "caminando":
                    f = self._fase_marcha
                    if "left_hip_pitch" in self._jmap:
                        self._data.qpos[self._jmap["left_hip_pitch"]] = 0.40 * math.sin(f)
                    if "right_hip_pitch" in self._jmap:
                        self._data.qpos[self._jmap["right_hip_pitch"]] = 0.40 * math.sin(f + math.pi)
                    if "left_knee" in self._jmap:
                        self._data.qpos[self._jmap["left_knee"]] = max(0.0, 0.45 * math.sin(f + 1.1))
                    if "right_knee" in self._jmap:
                        self._data.qpos[self._jmap["right_knee"]] = max(0.0, 0.45 * math.sin(f + 1.1 + math.pi))
                    if "left_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["left_shoulder_pitch"]] = 0.20 + 0.30 * math.sin(f + math.pi)
                    if "right_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["right_shoulder_pitch"]] = 0.20 + 0.30 * math.sin(f)
                elif self.accion == "girando":
                    f = self._fase_marcha
                    if "left_hip_pitch" in self._jmap:
                        self._data.qpos[self._jmap["left_hip_pitch"]] = 0.18 * math.sin(f)
                    if "right_hip_pitch" in self._jmap:
                        self._data.qpos[self._jmap["right_hip_pitch"]] = 0.18 * math.sin(f + math.pi)
                    if "left_knee" in self._jmap:
                        self._data.qpos[self._jmap["left_knee"]] = max(0.0, 0.20 * math.sin(f + 1.1))
                    if "right_knee" in self._jmap:
                        self._data.qpos[self._jmap["right_knee"]] = max(0.0, 0.20 * math.sin(f + 1.1 + math.pi))
                elif self.accion == "saludando":
                    # Saludo humanoide natural con brazo derecho alzado y codo doblado al frente
                    if "right_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["right_shoulder_pitch"]] = -1.75
                    if "right_shoulder_roll" in self._jmap:
                        self._data.qpos[self._jmap["right_shoulder_roll"]] = -0.32
                    if "right_elbow" in self._jmap:
                        self._data.qpos[self._jmap["right_elbow"]] = 0.85
                    if "right_wrist_roll" in self._jmap:
                        self._data.qpos[self._jmap["right_wrist_roll"]] = 0.40 * math.sin(ahora * 8.0)
                    if "left_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["left_shoulder_pitch"]] = 0.42
                    if "left_elbow" in self._jmap:
                        self._data.qpos[self._jmap["left_elbow"]] = 0.28
                    if "waist_pitch" in self._jmap:
                        self._data.qpos[self._jmap["waist_pitch"]] = -0.02
                    for d in ("index", "middle", "ring", "pinky"):
                        kd = f"right_hand_{d}"
                        if kd in self._jmap:
                            self._data.qpos[self._jmap[kd]] = 0.05
                elif self.accion == "postura":
                    for k, v_obj in self._pose_objetivo.items():
                        if k in self._jmap:
                            adr = self._jmap[k]
                            actual = float(self._data.qpos[adr])
                            self._data.qpos[adr] = actual + (v_obj - actual) * min(1.0, dt * 7.0)
                elif self.accion == "animacion":
                    # Show Action Sequencing (Teatral de ciclo único)
                    if self._secuencia_actual:
                        if time.monotonic() - self._ultimo_tiempo_pose > self._duracion_step:
                            self._idx_secuencia += 1
                            if self._idx_secuencia >= len(self._secuencia_actual):
                                # Secuencia teatral completa -> transición a quieto o gesticulación de habla
                                self.accion = "quieto"
                                self._secuencia_actual = []
                                self._idx_secuencia = 0
                            else:
                                self._ultimo_tiempo_pose = time.monotonic()

                        if self._secuencia_actual and self._idx_secuencia < len(self._secuencia_actual):
                            target = self._secuencia_actual[self._idx_secuencia]
                            for k, v_obj in target.items():
                                if k in self._jmap:
                                    adr = self._jmap[k]
                                    actual = float(self._data.qpos[adr])
                                    self._data.qpos[adr] = actual + (v_obj - actual) * min(1.0, dt * 8.5)
                    else:
                        self.accion = "quieto"
                else:
                    # Cinemática Afectiva Continua de Cuerpo Completo (Laban + Lecoq + McNeill)
                    # 1. Definir Postura Base objetivo f(V, A)
                    v = self.valencia
                    a = self.arousal
                    if v < -0.20:
                        # Tristeza / Desánimo: inclinación empática hacia adelante
                        base_obj = {
                            "waist_pitch": 0.14,
                            "waist_roll": 0.03,
                            "waist_yaw": 0.0,
                            "left_shoulder_pitch": 0.46,
                            "right_shoulder_pitch": 0.46,
                            "left_shoulder_roll": 0.06,
                            "right_shoulder_roll": -0.06,
                            "left_elbow": 0.24,
                            "right_elbow": 0.24,
                            "left_wrist_roll": -1.25,
                            "right_wrist_roll": 1.25,
                            "manos": 0.04,
                        }
                    elif v > 0.25:
                        # Motivación / Alegría: expansión torácica erguida
                        base_obj = {
                            "waist_pitch": -0.04,
                            "waist_roll": 0.0,
                            "waist_yaw": 0.0,
                            "left_shoulder_pitch": 0.28,
                            "right_shoulder_pitch": 0.28,
                            "left_shoulder_roll": 0.16,
                            "right_shoulder_roll": -0.16,
                            "left_elbow": 0.38,
                            "right_elbow": 0.38,
                            "left_wrist_roll": -1.15,
                            "right_wrist_roll": 1.15,
                            "manos": 0.18,
                        }
                    elif a > 0.30:
                        # Ansiedad / Estrés: co-regulación y estabilidad
                        base_obj = {
                            "waist_pitch": 0.03,
                            "waist_roll": 0.0,
                            "waist_yaw": 0.0,
                            "left_shoulder_pitch": 0.36,
                            "right_shoulder_pitch": 0.36,
                            "left_shoulder_roll": 0.12,
                            "right_shoulder_roll": -0.12,
                            "left_elbow": 0.34,
                            "right_elbow": 0.34,
                            "left_wrist_roll": -1.25,
                            "right_wrist_roll": 1.25,
                            "manos": 0.08,
                        }
                    else:
                        # Neutro: reposo anatómico natural (palmas hacia los muslos)
                        base_obj = {
                            "waist_pitch": 0.0,
                            "waist_roll": 0.0,
                            "waist_yaw": 0.0,
                            "left_shoulder_pitch": 0.42,
                            "right_shoulder_pitch": 0.42,
                            "left_shoulder_roll": 0.08,
                            "right_shoulder_roll": -0.08,
                            "left_elbow": 0.28,
                            "right_elbow": 0.28,
                            "left_wrist_roll": -1.25,
                            "right_wrist_roll": 1.25,
                            "manos": 0.05,
                        }

                    # Lerp suave hacia la postura base
                    vel_lerp = dt * 4.5
                    for k, val_obj in base_obj.items():
                        self._pose_base[k] += (val_obj - self._pose_base[k]) * min(1.0, vel_lerp)

                    # 2. Modulaciones Dinámicas Armónicas (Center-Out phase lags)
                    if self.hablando:
                        # Co-speech beat gestures
                        vel_onda = (3.0 + 1.2 * max(0.0, a)) * self.energia_habla
                        self._fase_gesto = (self._fase_gesto + dt * vel_onda) % (2.0 * math.pi)
                        f = self._fase_gesto

                        amp_sh = (0.05 + 0.04 * max(0.0, a)) * self.energia_habla
                        amp_el = (0.08 + 0.06 * max(0.0, a)) * self.energia_habla
                        amp_dedos = (0.10 + 0.10 * max(0.0, a)) * self.energia_habla

                        # Torso -> Hombros -> Codos -> Muñecas
                        mod_torso = 0.012 * self.energia_habla * math.sin(f)
                        mod_l_sh = -amp_sh * math.sin(f + 0.35)
                        mod_r_sh = -amp_sh * math.sin(f + 0.35 + 0.85)
                        mod_l_el = amp_el * math.cos(f + 0.80)
                        mod_r_el = amp_el * math.cos(f + 0.80 + 0.85)
                        mod_l_wr = 0.18 * math.sin(f + 1.15)
                        mod_r_wr = -0.18 * math.sin(f + 1.15 + 0.85)
                        mod_dedos = amp_dedos * abs(math.sin((f + 1.15) * 0.5))
                    else:
                        # Idle breathing diafragmático orgánico (~4s) + balanceo postural pendular (~6.5s)
                        f_resp = ahora * 1.57   # Ciclo respiratorio diafragmático (~4s)
                        f_sway = ahora * 0.96   # Ciclo pendular postural orgánico (~6.5s)

                        # Expansión torácica y respiración viva claramente visible
                        mod_torso = 0.038 * math.sin(f_resp)
                        mod_l_sh = 0.028 * math.sin(f_resp + 0.25)
                        mod_r_sh = 0.028 * math.sin(f_resp + 0.25)
                        mod_l_el = 0.022 * math.cos(f_resp)
                        mod_r_el = 0.022 * math.cos(f_resp)
                        mod_l_wr = 0.040 * math.sin(f_resp + 0.50)
                        mod_r_wr = -0.040 * math.sin(f_resp + 0.50)
                        mod_dedos = 0.05 * (0.5 + 0.5 * math.sin(f_resp))

                        # Balanceo postural pendular y contrapposto orgánico (cambio sutil de peso)
                        sway_pelvis_roll = 0.022 * math.sin(f_sway)
                        sway_pelvis_yaw = 0.014 * math.cos(f_sway * 0.5)
                        sway_leg = math.sin(f_sway)

                    # 3. Aplicar a las articulaciones de MuJoCo
                    p = self._pose_base
                    if "waist_pitch" in self._jmap:
                        self._data.qpos[self._jmap["waist_pitch"]] = p["waist_pitch"] + mod_torso
                    if "waist_roll" in self._jmap:
                        self._data.qpos[self._jmap["waist_roll"]] = p["waist_roll"] + (sway_pelvis_roll if not self.hablando else 0.0)
                    if "waist_yaw" in self._jmap:
                        self._data.qpos[self._jmap["waist_yaw"]] = p["waist_yaw"] + (sway_pelvis_yaw if not self.hablando else 0.0)
                    if "left_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["left_shoulder_pitch"]] = p["left_shoulder_pitch"] + mod_l_sh
                    if "right_shoulder_pitch" in self._jmap:
                        self._data.qpos[self._jmap["right_shoulder_pitch"]] = p["right_shoulder_pitch"] + mod_r_sh
                    if "left_shoulder_roll" in self._jmap:
                        sh_roll_mod = (-sway_pelvis_roll * 0.5) if not self.hablando else 0.0
                        self._data.qpos[self._jmap["left_shoulder_roll"]] = p["left_shoulder_roll"] + sh_roll_mod
                    if "right_shoulder_roll" in self._jmap:
                        sh_roll_mod = (-sway_pelvis_roll * 0.5) if not self.hablando else 0.0
                        self._data.qpos[self._jmap["right_shoulder_roll"]] = p["right_shoulder_roll"] + sh_roll_mod
                    if "left_elbow" in self._jmap:
                        self._data.qpos[self._jmap["left_elbow"]] = p["left_elbow"] + mod_l_el
                    if "right_elbow" in self._jmap:
                        self._data.qpos[self._jmap["right_elbow"]] = p["right_elbow"] + mod_r_el
                    if "left_wrist_roll" in self._jmap:
                        self._data.qpos[self._jmap["left_wrist_roll"]] = p["left_wrist_roll"] + mod_l_wr
                    if "right_wrist_roll" in self._jmap:
                        self._data.qpos[self._jmap["right_wrist_roll"]] = p["right_wrist_roll"] + mod_r_wr

                    # Piernas vivas con flexión visible natural y contrapposto orgánico dinámico
                    leg_sway_amp = (0.042 * sway_leg) if not self.hablando else 0.0
                    lk_val = 0.32 + leg_sway_amp
                    rk_val = 0.32 - leg_sway_amp
                    hp_l_val = -0.16 - leg_sway_amp * 0.5
                    hp_r_val = -0.16 + leg_sway_amp * 0.5
                    ap_l_val = -0.16 - leg_sway_amp * 0.5
                    ap_r_val = -0.16 + leg_sway_amp * 0.5
                    hr_l_val = 0.02 + (0.012 * sway_leg if not self.hablando else 0.0)
                    hr_r_val = -0.02 + (0.012 * sway_leg if not self.hablando else 0.0)
                    ar_l_val = -(hr_l_val * 0.5)
                    ar_r_val = -(hr_r_val * 0.5)

                    for leg_joint, leg_val in (
                        ("left_hip_pitch", hp_l_val), ("right_hip_pitch", hp_r_val),
                        ("left_hip_roll", hr_l_val), ("right_hip_roll", hr_r_val),
                        ("left_knee", lk_val), ("right_knee", rk_val),
                        ("left_ankle_pitch", ap_l_val), ("right_ankle_pitch", ap_r_val),
                        ("left_ankle_roll", ar_l_val), ("right_ankle_roll", ar_r_val),
                    ):
                        if leg_joint in self._jmap:
                            self._data.qpos[self._jmap[leg_joint]] = leg_val

                    # Dedos Inspire RH56 con cascada anatómica viva
                    apertura_dedos = max(0.02, min(0.65, p["manos"] + mod_dedos))
                    for lado in ("left", "right"):
                        cascada = {
                            "index": apertura_dedos,
                            "middle": apertura_dedos * 1.20 + 0.04,
                            "ring": apertura_dedos * 1.40 + 0.08,
                            "pinky": apertura_dedos * 1.60 + 0.12,
                        }
                        for dedo, val_dedo in cascada.items():
                            kd = f"{lado}_hand_{dedo}"
                            if kd in self._jmap:
                                self._data.qpos[self._jmap[kd]] = min(1.35, val_dedo)
                        k_tb = f"{lado}_hand_thumb_bend"
                        if k_tb in self._jmap:
                            self._data.qpos[self._jmap[k_tb]] = min(1.10, apertura_dedos * 0.70)
                        k_tr = f"{lado}_hand_thumb_rotation"
                        if k_tr in self._jmap:
                            self._data.qpos[self._jmap[k_tr]] = 0.20

                # Compensación física dinámica de centro de gravedad y rodillas
                lk = float(self._data.qpos[self._jmap["left_knee"]]) if "left_knee" in self._jmap else 0.0
                rk = float(self._data.qpos[self._jmap["right_knee"]]) if "right_knee" in self._jmap else 0.0
                knee_avg = (lk + rk) / 2.0
                self._data.qpos[2] = self.altura - (0.045 * knee_avg * knee_avg)

                wp = float(self._data.qpos[self._jmap["waist_pitch"]]) if "waist_pitch" in self._jmap else 0.0
                if wp > 0.04:
                    self._data.qpos[0] = self.x - 0.16 * wp
                else:
                    self._data.qpos[0] = self.x

                # Inicializar renderer de forma perezosa en el mismo hilo de renderizado
                if self._renderer is None:
                    self._renderer = mujoco.Renderer(self._model, self.alto, self.ancho)
                    self._camera = mujoco.MjvCamera()
                    self._camera.type = mujoco.mjtCamera.mjCAMERA_FREE
                    self._camera.lookat[:] = [0.0, 0.0, 0.75]
                    self._camera.distance = 2.25
                    self._camera.elevation = -11.0
                    self._camera.azimuth = 160.0

                # Cámara suave siguiendo el centro del robot
                self._camera.lookat[0] = self.x
                self._camera.lookat[1] = self.y
                self._camera.lookat[2] = 0.75
                self._camera.azimuth = 160.0 + math.degrees(self.yaw) * 0.35

                mujoco.mj_forward(self._model, self._data)
                self._renderer.update_scene(self._data, camera=self._camera)
                return self._renderer.render()
            except Exception:
                return None


# =====================================================================
#  INTERFAZ GRÁFICA PRINCIPAL — MODO DASHBOARD UNIFICADO
# =====================================================================

class RostroOttoman:
    """Interfaz visual unificada: Rostro Afectivo + Simulador 3D G1 + FACS + Russell + Chat."""

    def __init__(
        self,
        habilitado: bool = True,
        modo_dashboard: bool = True,
        captura_camara_autonoma: bool = False,
        titulo: str = "Ottoman G1 — Sistema Multimodal Unificado (Simulador 3D + Rostro + FACS + Chat)",
    ):
        self.habilitado = habilitado
        self.modo_dashboard = modo_dashboard
        self.captura_camara_autonoma = captura_camara_autonoma
        self.titulo = titulo
        self._cola: queue.Queue[dict] = queue.Queue()
        self._hilo: Optional[threading.Thread] = None
        self._activo = False

        # Simulador 3D G1 embebido
        self.simulador_3d = SimuladorEmbebidoG1(ancho=428, alto=380)

        # Referencias a la lógica y sensores del sistema
        self._agente = None
        self._reconocedor_voz = None
        self._analizador_facial = None

        # Estado dinámico de hardware y sensores
        self.estado_camara: str = "Iniciando..."
        self.estado_microfono: str = "Iniciando..."
        self.estado_simulador: str = "MuJoCo G1 Activo (29-DoF)"

        # Estado afectivo consultable
        self.emocion_actual: str = "NEUTRO"
        self.hablando: bool = False
        self.subtitulo_actual: str = "Listo para escucharte."
        self.resumen_usuario: str = "Sensores listos (Cara + Voz + Léxico)"
        self.resumen_prosodia: str = "Voz Robot: 145 ppm (0%) | +0.0 dB | +0 Hz"

        # Telemetría Russell y FACS
        self.valencia_actual: float = 0.0
        self.arousal_actual: float = 0.0
        self.incongruencia_activa: bool = False
        self.canales_activos: list[str] = ["lexico"]
        self.historial_va: deque[tuple[float, float, str]] = deque(maxlen=8)
        self.historial_chat: deque[tuple[str, str, str]] = deque(maxlen=60)
        self.metricas_faciales_dict: dict = {
            "rostro_detectado": False,
            "apertura_ojos": 0.0,
            "tension_cejas": 0.0,
            "curvatura_boca": 0.0,
            "apertura_boca": 0.0,
            "inclinacion_cabeza_deg": 0.0,
            "emocion_facial": "INACTIVO",
        }
        self._ultimo_frame_rgb: Optional[np.ndarray] = None
        self._lock_frame = threading.Lock()

    def vincular_agente(
        self,
        agente,
        reconocedor_voz=None,
        analizador_facial=None,
    ) -> None:
        """Conecta el agente de IA y los sensores multimodales directamente al dashboard."""
        self._agente = agente
        self._reconocedor_voz = reconocedor_voz
        self._analizador_facial = analizador_facial
        agente.rostro = self

        if analizador_facial is not None and getattr(analizador_facial, "camara_disponible", False):
            self.estado_camara = "ACTIVA (30 FPS)"
        else:
            self.estado_camara = "NO DETECTADA (FACS Radar)"

        if reconocedor_voz is not None and getattr(reconocedor_voz, "microfono_disponible", False):
            self.estado_microfono = "ACTIVO (DSP 16kHz)"
        else:
            self.estado_microfono = "NO DETECTADO (Chat listo)"

        self._cola.put({"cmd": "actualizar_sensores"})

    def reconectar_camara(self) -> bool:
        """Intenta reabrir la cámara web en caliente si el usuario la conectó."""
        if self._analizador_facial is None:
            try:
                from percepcion_multimodal import AnalizadorFacial
                self._analizador_facial = AnalizadorFacial()
            except Exception:
                self.estado_camara = "ERROR AL INICIAR"
                self._cola.put({"cmd": "actualizar_sensores"})
                return False

        exito = self._analizador_facial.abrir_camara()
        if exito:
            self.estado_camara = "ACTIVA (30 FPS)"
            self.agregar_chat_mensaje("Sistema", "Cámara web conectada y calibrada con éxito.", "#34D399")
        else:
            self.estado_camara = "NO DETECTADA (Reintentar)"
            self.agregar_chat_mensaje("Sistema", "No se encontró cámara disponible en el puerto USB.", "#F87171")
        self._cola.put({"cmd": "actualizar_sensores"})
        return exito

    def reconectar_microfono(self) -> bool:
        """Intenta calibrar el micrófono en caliente si el usuario lo conectó."""
        if self._reconocedor_voz is None:
            try:
                from speech_to_text import ReconocedorVozMultimodal
                self._reconocedor_voz = ReconocedorVozMultimodal()
            except Exception:
                self.estado_microfono = "ERROR AL INICIAR"
                self._cola.put({"cmd": "actualizar_sensores"})
                return False

        exito = self._reconocedor_voz.calibrar()
        if exito:
            self.estado_microfono = "ACTIVO (DSP 16kHz)"
            self.agregar_chat_mensaje("Sistema", "Micrófono conectado y calibrado con éxito.", "#34D399")
        else:
            self.estado_microfono = "NO DETECTADO (Reintentar)"
            self.agregar_chat_mensaje("Sistema", "No se detectó dispositivo de audio para micrófono.", "#F87171")
        self._cola.put({"cmd": "actualizar_sensores"})
        return exito

    def agregar_chat_mensaje(self, remitente: str, mensaje: str, color: Optional[str] = None) -> None:
        """Añade un mensaje al historial de conversación en pantalla."""
        if not color:
            if remitente.lower().startswith("vos"):
                color = "#38BDF8"
            elif remitente.lower().startswith("ottoman"):
                color = "#A7F3D0"
            else:
                color = "#CBD5E1"
        self.historial_chat.append((remitente, mensaje, color))
        self._cola.put({"cmd": "nuevo_chat", "remitente": remitente, "mensaje": mensaje, "color": color})

    def enviar_desde_gui(self, texto: str) -> None:
        """Procesa una orden ingresada directamente en la barra de texto del dashboard."""
        texto_limpio = texto.strip()
        if not texto_limpio:
            return
        self.agregar_chat_mensaje("Vos", texto_limpio)

        def _worker():
            try:
                facial = None
                if self._analizador_facial and self._analizador_facial.camara_disponible:
                    facial = self._analizador_facial.capturar_rafaga(2)
                if self._agente:
                    self._agente.procesar(texto_limpio, facial=facial)
            except Exception as exc:
                self.agregar_chat_mensaje("Sistema", f"Error al procesar: {exc}", "#F87171")

        threading.Thread(target=_worker, daemon=True).start()

    def escuchar_desde_gui(self) -> None:
        """Inicia captura de voz por micrófono en segundo plano."""
        if not self._reconocedor_voz or not self._reconocedor_voz.microfono_disponible:
            self.agregar_chat_mensaje("Sistema", "Micrófono no disponible. Usá el chat escrito o pulsá 'Reconectar Mic'.", "#F59E0B")
            return

        self.subtitulo_actual = "Escuchando por micrófono... Hablá ahora."
        self._cola.put({"cmd": "estado", "subtitulo": self.subtitulo_actual})

        def _worker():
            try:
                texto_usr, lectura_voz = self._reconocedor_voz.escuchar_multimodal()
                if texto_usr or (lectura_voz and lectura_voz.audio_analizado):
                    msg = texto_usr if texto_usr else "[Audio analizado]"
                    self.agregar_chat_mensaje("Vos (Voz)", msg)
                    facial = None
                    if self._analizador_facial and self._analizador_facial.camara_disponible:
                        facial = self._analizador_facial.capturar_rafaga(2)
                    if self._agente:
                        self._agente.procesar(texto_usr, facial=facial, acustica=lectura_voz)
                else:
                    self.subtitulo_actual = "No se detectó voz. Podés reintentar o escribir por el chat."
                    self._cola.put({"cmd": "estado", "subtitulo": self.subtitulo_actual})
            except Exception as exc:
                self.subtitulo_actual = f"Error de escucha: {exc}"
                self._cola.put({"cmd": "estado", "subtitulo": self.subtitulo_actual})

        threading.Thread(target=_worker, daemon=True).start()

    def iniciar(self, en_hilo_actual: bool = False) -> bool:
        """Levanta la ventana gráfica unificada.
        
        Si en_hilo_actual=True, corre directamente en el hilo invocador (requerido en Windows
        para que GLFW / MuJoCo 3D comparta el message pump del hilo principal sin errores de contexto).
        Si en_hilo_actual=False, levanta en un hilo dedicado no bloqueante.
        """
        if not self.habilitado:
            return False
        if self._activo:
            return True

        if en_hilo_actual:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.title(self.titulo)
                geom = "1380x870" if self.modo_dashboard else "680x500"
                root.geometry(geom)
                root.configure(bg="#070B14")
                root.resizable(False, False)
                self._activo = True
                self._root = root
                self._bucle_render(root, tk)
                return True
            except Exception:
                self._activo = False
                return False

        listo = threading.Event()
        exito = [False]

        def _worker():
            try:
                import tkinter as tk
                root = tk.Tk()
                root.title(self.titulo)
                geom = "1380x870" if self.modo_dashboard else "680x500"
                root.geometry(geom)
                root.configure(bg="#070B14")
                root.resizable(False, False)
                exito[0] = True
                self._activo = True
                self._root = root
                listo.set()
                self._bucle_render(root, tk)
            except Exception:
                self._activo = False
                listo.set()

        self._hilo = threading.Thread(target=_worker, daemon=True)
        self._hilo.start()
        listo.wait(timeout=3.0)
        return exito[0]

    def cerrar(self) -> None:
        self._activo = False
        self._cola.put({"cmd": "cerrar"})
        if hasattr(self, "_root") and self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
        if self._hilo is not None and self._hilo.is_alive():
            self._hilo.join(timeout=1.0)

    def actualizar_estado(
        self,
        emocion: str,
        subtitulo: str = "",
        resumen_usuario: str = "",
        resumen_prosodia: str = "",
        hablando: Optional[bool] = None,
        valencia: Optional[float] = None,
        arousal: Optional[float] = None,
        incongruencia: Optional[bool] = None,
        canales: Optional[list[str]] = None,
        metricas_faciales: Optional[object] = None,
    ) -> PresetFacialRobot:
        """Actualiza expresión facial, subtítulos y coordenadas Valencia-Arousal."""
        clave = emocion if emocion in PRESETS_ROSTRO else "NEUTRO"
        self.emocion_actual = clave
        if subtitulo:
            self.subtitulo_actual = subtitulo
        if resumen_usuario:
            self.resumen_usuario = resumen_usuario
        if resumen_prosodia:
            self.resumen_prosodia = resumen_prosodia
        if hablando is not None:
            self.hablando = hablando
        if valencia is not None and arousal is not None:
            self.valencia_actual = float(max(-1.0, min(1.0, valencia)))
            self.arousal_actual = float(max(-1.0, min(1.0, arousal)))
            self.simulador_3d.fijar_estado_afectivo(self.valencia_actual, self.arousal_actual)
            self.historial_va.append((self.valencia_actual, self.arousal_actual, clave))
        elif clave in PRESETS_ROSTRO:
            va_presets = {
                "MOTIVACION_ALEGRIA": (0.70, 0.60),
                "TRISTEZA_DESANIMO": (-0.65, -0.45),
                "ANSIEDAD_ESTRES": (-0.40, 0.70),
                "ENOJO_FRUSTRACION": (-0.70, 0.75),
                "DUDA_INSEGURIDAD": (-0.15, 0.20),
                "NEUTRO": (0.0, 0.0),
                "CRISIS_RIESGO": (-0.80, 0.50),
                "ASOMBRO": (0.40, 0.85),
                "EUREKA": (0.80, 0.70),
                "ALERTA": (-0.10, 0.80),
                "PREGUNTA": (0.10, 0.40),
                "ENFOQUE": (0.20, 0.30),
                "CALMA": (0.30, -0.40),
            }
            if clave in va_presets:
                pv, pa = va_presets[clave]
                self.valencia_actual = pv
                self.arousal_actual = pa
                self.simulador_3d.fijar_estado_afectivo(pv, pa)
        if incongruencia is not None:
            self.incongruencia_activa = bool(incongruencia)
        if canales is not None:
            self.canales_activos = list(canales)
        if metricas_faciales is not None:
            self._guardar_metricas_faciales(metricas_faciales)

        if self._activo:
            self._cola.put({
                "cmd": "estado",
                "emocion": clave,
                "subtitulo": self.subtitulo_actual,
                "resumen_usuario": self.resumen_usuario,
                "resumen_prosodia": self.resumen_prosodia,
                "hablando": self.hablando,
            })
        return PRESETS_ROSTRO[clave]

    def actualizar_camara(self, frame_bgr: Optional[np.ndarray], metricas_faciales: Optional[object] = None) -> None:
        """Envía un frame BGR anotado por OpenCV al panel de visión."""
        if metricas_faciales is not None:
            self._guardar_metricas_faciales(metricas_faciales)
        if frame_bgr is not None and frame_bgr.size > 0:
            try:
                import cv2
                frame_peq = cv2.resize(frame_bgr, (230, 164))
                rgb = cv2.cvtColor(frame_peq, cv2.COLOR_BGR2RGB)
                with self._lock_frame:
                    self._ultimo_frame_rgb = rgb
            except Exception:
                pass

    def _guardar_metricas_faciales(self, mf: object) -> None:
        for campo in (
            "rostro_detectado",
            "apertura_ojos",
            "tension_cejas",
            "curvatura_boca",
            "apertura_boca",
            "inclinacion_cabeza_deg",
            "emocion_facial",
        ):
            if hasattr(mf, campo):
                self.metricas_faciales_dict[campo] = getattr(mf, campo)
            elif isinstance(mf, dict) and campo in mf:
                self.metricas_faciales_dict[campo] = mf[campo]

    def set_hablando(self, hablando: bool, subtitulo: str = "") -> None:
        self.hablando = hablando
        self.simulador_3d.fijar_estado_habla(hablando)
        if subtitulo:
            self.subtitulo_actual = subtitulo
        if self._activo:
            self._cola.put({
                "cmd": "habla",
                "hablando": hablando,
                "subtitulo": self.subtitulo_actual,
            })

    def disparar_micro_expresion(
        self,
        forma_ojo: str = "capsula",
        glifo: Optional[str] = None,
        duracion: float = 1.8,
        apertura: Optional[float] = None,
        inclinacion: Optional[float] = None,
    ) -> None:
        """Dispara una micro-expresión conversacional temporal que vuelve suavemente al estado base."""
        if self._activo:
            self._cola.put({
                "cmd": "micro_expresion",
                "forma_ojo": forma_ojo,
                "glifo": glifo,
                "duracion": duracion,
                "apertura": apertura,
                "inclinacion": inclinacion,
            })

    def disparar_glifo(self, glifo: str, duracion: float = 2.0) -> None:
        """Muestra un glifo heroico de personalidad ('!' o '?') en los ojos del visor OLED."""
        self.disparar_micro_expresion(forma_ojo="capsula", glifo=glifo, duracion=duracion)

    # -----------------------------------------------------------------
    #  Renderizado visual y gestión de eventos de la GUI
    # -----------------------------------------------------------------
    def _bucle_render(self, root, tk) -> None:
        from PIL import Image, ImageTk

        ancho_w = 1380 if self.modo_dashboard else 680
        alto_w = 870 if self.modo_dashboard else 500

        # Contenedor superior: Canvas gráfico para los paneles visuales
        alto_canvas = 480 if self.modo_dashboard else 370
        canvas = tk.Canvas(root, width=ancho_w, height=alto_canvas, bg="#070B14", highlightthickness=0)
        canvas.pack(side="top", fill="x")

        # Contenedor intermedio: Barra de estado de sensores y botones de reconexión
        frame_sensores = tk.Frame(root, bg="#0B1120", height=42, padx=14, pady=4)
        frame_sensores.pack(side="top", fill="x")

        lbl_cam = tk.Label(frame_sensores, text=f"📷 Cámara: {self.estado_camara}", bg="#0B1120", fg="#38BDF8", font=("Segoe UI", 9, "bold"))
        lbl_cam.pack(side="left", padx=6)
        btn_cam = tk.Button(frame_sensores, text="[ Reconectar Cámara ]", bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 8),
                            relief="flat", cursor="hand2", command=self.reconectar_camara)
        btn_cam.pack(side="left", padx=4)

        lbl_mic = tk.Label(frame_sensores, text=f"🎙️ Micrófono: {self.estado_microfono}", bg="#0B1120", fg="#34D399", font=("Segoe UI", 9, "bold"))
        lbl_mic.pack(side="left", padx=12)
        btn_mic = tk.Button(frame_sensores, text="[ Reconectar Mic ]", bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 8),
                            relief="flat", cursor="hand2", command=self.reconectar_microfono)
        btn_mic.pack(side="left", padx=4)

        lbl_sim = tk.Label(frame_sensores, text="🤖 Unitree G1: MuJoCo 29-DoF Activo", bg="#0B1120", fg="#FCD34D", font=("Segoe UI", 9, "bold"))
        lbl_sim.pack(side="left", padx=14)
        btn_reset_pos = tk.Button(frame_sensores, text="[ Resetear Posición G1 ]", bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 8),
                                  relief="flat", cursor="hand2", command=self.simulador_3d.resetear_posicion)
        btn_reset_pos.pack(side="left", padx=4)

        # Contenedor inferior: Historial de chat, transcripción de voz y campo de entrada
        frame_chat = tk.Frame(root, bg="#070B14", padx=16, pady=6)
        frame_chat.pack(side="bottom", fill="both", expand=True)

        # Subtítulo y telemetría de voz hablada
        frame_sub = tk.Frame(frame_chat, bg="#0E1626", padx=8, pady=4, bd=1, relief="ridge")
        frame_sub.pack(fill="x", pady=2)
        lbl_subtitulo = tk.Label(frame_sub, text=f"\"{self.subtitulo_actual}\"", bg="#0E1626", fg="#F9FAFB",
                                 font=("Segoe UI", 10, "bold"), anchor="w", justify="left")
        lbl_subtitulo.pack(fill="x")
        lbl_telemetria_voz = tk.Label(frame_sub, text=f"{self.resumen_usuario}  |  {self.resumen_prosodia}",
                                      bg="#0E1626", fg="#93C5FD", font=("Consolas", 8), anchor="w")
        lbl_telemetria_voz.pack(fill="x")

        # Cuadro de historial de mensajes interactivos
        txt_historial = tk.Text(frame_chat, height=6, bg="#0B101E", fg="#E2E8F0", insertbackground="#38BDF8",
                                relief="flat", wrap="word", font=("Segoe UI", 9))
        txt_historial.pack(fill="both", expand=True, pady=4)
        txt_historial.tag_configure("vos", foreground="#38BDF8", font=("Segoe UI", 9, "bold"))
        txt_historial.tag_configure("ottoman", foreground="#A7F3D0", font=("Segoe UI", 9))
        txt_historial.tag_configure("sistema", foreground="#FCD34D", font=("Segoe UI", 8, "italic"))

        def _agregar_texto_historial(remitente: str, texto: str, color: str):
            txt_historial.config(state="normal")
            tag = "vos" if "vos" in remitente.lower() else ("ottoman" if "ottoman" in remitente.lower() else "sistema")
            txt_historial.insert("end", f"[{remitente}]: ", tag)
            txt_historial.insert("end", f"{texto}\n")
            txt_historial.see("end")
            txt_historial.config(state="disabled")

        _agregar_texto_historial("Ottoman", "¡Hola! Estoy listo. Podés escribirme o usar comandos físicos.", "#A7F3D0")

        # Fila de entrada de texto interactivo
        frame_input = tk.Frame(frame_chat, bg="#070B14", pady=4)
        frame_input.pack(fill="x")

        entry_texto = tk.Entry(frame_input, bg="#111827", fg="#F8FAFC", insertbackground="#38BDF8",
                               relief="flat", font=("Segoe UI", 10), bd=4)
        entry_texto.pack(side="left", fill="x", expand=True, padx=(0, 6))
        entry_texto.focus_set()

        def _accion_enviar():
            txt = entry_texto.get()
            if txt.strip():
                entry_texto.delete(0, tk.END)
                self.enviar_desde_gui(txt)

        entry_texto.bind("<Return>", lambda e: _accion_enviar())

        btn_enviar = tk.Button(frame_input, text="ENVIAR ➔", bg="#0284C7", fg="#FFFFFF",
                               font=("Segoe UI", 9, "bold"), padx=12, pady=4, relief="flat", cursor="hand2",
                               command=_accion_enviar)
        btn_enviar.pack(side="left", padx=4)

        btn_hablar = tk.Button(frame_input, text="🎙️ HABLAR", bg="#059669", fg="#FFFFFF",
                               font=("Segoe UI", 9, "bold"), padx=12, pady=4, relief="flat", cursor="hand2",
                               command=self.escuchar_desde_gui)
        btn_hablar.pack(side="left", padx=4)

        # Chips de comandos rápidos
        frame_chips = tk.Frame(frame_chat, bg="#070B14", pady=2)
        frame_chips.pack(fill="x")
        chips = [
            ("🎭 Demo 6 Escenarios", lambda: self.enviar_desde_gui("demo")),
            ("🚶 Avanzar 1m", lambda: self.enviar_desde_gui("avanza 1 metro a velocidad 0.2")),
            ("🔄 Girar 90°", lambda: self.enviar_desde_gui("gira 90 grados a la derecha")),
            ("👋 Saludar", lambda: self.enviar_desde_gui("saluda")),
            ("🛑 Detenerse", lambda: self.enviar_desde_gui("detente")),
        ]
        for txt_chip, cmd_chip in chips:
            b_chip = tk.Button(frame_chips, text=txt_chip, bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8),
                               relief="flat", cursor="hand2", padx=8, pady=2, command=cmd_chip)
            b_chip.pack(side="left", padx=3)

        # Chips interactivos de prueba directa de rostros y expresiones OLED
        frame_caras = tk.Frame(frame_chat, bg="#070B14", pady=2)
        frame_caras.pack(fill="x")
        lbl_caras = tk.Label(frame_caras, text="Expresiones OLED:", bg="#070B14", fg="#64748B", font=("Segoe UI", 8, "bold"))
        lbl_caras.pack(side="left", padx=(2, 4))
        caras_chips = [
            ("😐 Neutro", "NEUTRO"),
            ("😊 Sonrisa", "MOTIVACION_ALEGRIA"),
            ("✨ Eureka", "EUREKA"),
            ("😮 Asombro", "ASOMBRO"),
            ("❗ Alerta", "ALERTA"),
            ("❓ Pregunta", "PREGUNTA"),
            ("🧘 Calma", "CALMA"),
            ("🔍 Enfoque", "ENFOQUE"),
            ("😠 Firme", "ENOJO_FRUSTRACION"),
            ("🥺 Empatía", "TRISTEZA_DESANIMO"),
        ]
        for txt_c, pre_k in caras_chips:
            b_c = tk.Button(
                frame_caras, text=txt_c, bg="#0F172A", fg="#38BDF8", activebackground="#1E293B", activeforeground="#7DD3FC",
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda k=pre_k: self.actualizar_estado(k)
            )
            b_c.pack(side="left", padx=2)

        # Variables de interpolación del rostro (Morfología Robótica EVE/Cozmo)
        preset_obj = PRESETS_ROSTRO["NEUTRO"]
        color_act = list(preset_obj.color_rgb)
        apertura_act = preset_obj.apertura_ojo
        arco_act = preset_obj.arco_feliz
        ceja_izq_act = preset_obj.angulo_ceja_izq
        ceja_der_act = preset_obj.angulo_ceja_der
        alt_ceja_act = preset_obj.altura_ceja
        boca_act = preset_obj.curvatura_boca
        inc_ojo_act = preset_obj.inclinacion_ojo
        ancho_ojo_act = preset_obj.ancho_ojo
        alto_ojo_act = preset_obj.alto_ojo
        asimetria_act = preset_obj.escala_asimetrica
        val_interp = 0.0
        aro_interp = 0.0

        photo_sim_ref = [None]
        photo_cam_ref = [None]
        t_proximo_parpadeo = time.monotonic() + 3.0
        parpadeo_hasta = 0.0

        # Coreografía dinámica y micro-expresiones conversacionales
        forma_ojo_micro: Optional[str] = None
        glifo_micro: Optional[str] = None
        fin_micro_expresion: float = 0.0
        apertura_micro: Optional[float] = None
        inclinacion_micro: Optional[float] = None

        # Idle life: micro-sacadas foveales estocásticas (gaze natural)
        mirada_target_x = 0.0
        mirada_target_y = 0.0
        mirada_cur_x = 0.0
        mirada_cur_y = 0.0
        t_proxima_sacada = time.monotonic() + 2.0

        def _al_cerrar():
            self._activo = False
            photo_sim_ref[0] = None
            photo_cam_ref[0] = None
            try:
                root.quit()
                root.destroy()
            except Exception:
                pass

        root.protocol("WM_DELETE_WINDOW", _al_cerrar)

        def _tick():
            nonlocal preset_obj, color_act, apertura_act, arco_act
            nonlocal ceja_izq_act, ceja_der_act, alt_ceja_act, boca_act
            nonlocal inc_ojo_act, ancho_ojo_act, alto_ojo_act, asimetria_act
            nonlocal val_interp, aro_interp, t_proximo_parpadeo, parpadeo_hasta
            nonlocal forma_ojo_micro, glifo_micro, fin_micro_expresion, apertura_micro, inclinacion_micro
            nonlocal mirada_target_x, mirada_target_y, mirada_cur_x, mirada_cur_y, t_proxima_sacada

            if not self._activo:
                _al_cerrar()
                return

            # Procesar mensajes pendientes de la cola
            while not self._cola.empty():
                try:
                    msg = self._cola.get_nowait()
                except queue.Empty:
                    break
                if msg.get("cmd") == "cerrar":
                    _al_cerrar()
                    return
                elif msg.get("cmd") == "actualizar_sensores":
                    lbl_cam.config(text=f"📷 Cámara: {self.estado_camara}")
                    lbl_mic.config(text=f"🎙️ Micrófono: {self.estado_microfono}")
                elif msg.get("cmd") == "nuevo_chat":
                    _agregar_texto_historial(msg["remitente"], msg["mensaje"], msg.get("color", "#FFFFFF"))
                elif msg.get("cmd") == "habla":
                    h = bool(msg.get("hablando", False))
                    self.simulador_3d.fijar_estado_habla(h)
                    if not h:
                        # Si había una micro-expresión activa durante la locución,
                        # permitimos que persista con gracia hasta 1.8s adicionales (lingering)
                        # en vez de amputarla abruptamente en 0 milisegundos.
                        if fin_micro_expresion > ahora:
                            fin_micro_expresion = max(fin_micro_expresion, ahora + 1.8)
                        else:
                            fin_micro_expresion = 0.0
                            glifo_micro = None
                            forma_ojo_micro = None
                            apertura_micro = None
                            inclinacion_micro = None
                    if "subtitulo" in msg and msg["subtitulo"]:
                        lbl_subtitulo.config(text=f"\"{msg['subtitulo']}\"")
                elif msg.get("cmd") == "micro_expresion":
                    dur = float(msg.get("duracion", 1.8))
                    fin_micro_expresion = time.monotonic() + dur
                    forma_ojo_micro = msg.get("forma_ojo")
                    glifo_micro = msg.get("glifo")
                    apertura_micro = msg.get("apertura")
                    inclinacion_micro = msg.get("inclinacion")
                elif msg.get("cmd") == "estado":
                    if "emocion" in msg:
                        preset_obj = PRESETS_ROSTRO.get(msg["emocion"], PRESETS_ROSTRO["NEUTRO"])
                        fin_micro_expresion = 0.0
                        glifo_micro = None
                        forma_ojo_micro = None
                        apertura_micro = None
                        inclinacion_micro = None
                    if "subtitulo" in msg:
                        lbl_subtitulo.config(text=f"\"{msg['subtitulo']}\"")
                    lbl_telemetria_voz.config(text=f"{self.resumen_usuario}  |  {self.resumen_prosodia}")

            ahora = time.monotonic()
            vel_interp = 0.16

            en_micro = (ahora < fin_micro_expresion)
            forma_ojo_efectiva = forma_ojo_micro if (en_micro and forma_ojo_micro) else preset_obj.forma_ojo
            glifo_efectivo = glifo_micro if (en_micro and glifo_micro) else getattr(preset_obj, "glifo", None)

            target_apertura = apertura_micro if (en_micro and apertura_micro is not None) else preset_obj.apertura_ojo
            target_inclinacion = inclinacion_micro if (en_micro and inclinacion_micro is not None) else preset_obj.inclinacion_ojo

            for i in range(3):
                color_act[i] = _lerp(color_act[i], preset_obj.color_rgb[i], vel_interp)
            apertura_act = _lerp(apertura_act, target_apertura, vel_interp)
            arco_act = _lerp(arco_act, preset_obj.arco_feliz, vel_interp)
            ceja_izq_act = _lerp(ceja_izq_act, preset_obj.angulo_ceja_izq, vel_interp)
            ceja_der_act = _lerp(ceja_der_act, preset_obj.angulo_ceja_der, vel_interp)
            alt_ceja_act = _lerp(alt_ceja_act, preset_obj.altura_ceja, vel_interp)
            boca_act = _lerp(boca_act, preset_obj.curvatura_boca, vel_interp)
            inc_ojo_act = _lerp(inc_ojo_act, target_inclinacion, vel_interp)
            ancho_ojo_act = _lerp(ancho_ojo_act, preset_obj.ancho_ojo, vel_interp)
            alto_ojo_act = _lerp(alto_ojo_act, preset_obj.alto_ojo, vel_interp)
            asimetria_act = _lerp(asimetria_act, preset_obj.escala_asimetrica, vel_interp)
            val_interp = _lerp(val_interp, self.valencia_actual, 0.16)
            aro_interp = _lerp(aro_interp, self.arousal_actual, 0.16)

            # Idle life: micro-sacadas de mirada foveales no lineales
            if ahora >= t_proxima_sacada:
                mirada_target_x = random.uniform(-4.2, 4.2)
                mirada_target_y = random.uniform(-2.2, 2.2)
                t_proxima_sacada = ahora + random.uniform(1.8, 3.8)

            mirada_cur_x = _lerp(mirada_cur_x, mirada_target_x, 0.20)
            mirada_cur_y = _lerp(mirada_cur_y, mirada_target_y, 0.20)
            mirada_x = mirada_cur_x + 0.5 * math.sin(ahora * 2.5)
            mirada_y = mirada_cur_y + 0.3 * math.cos(ahora * 2.0)

            # Pestañeo humanoide con soporte de doble pestañeo casual
            if ahora >= t_proximo_parpadeo:
                parpadeo_hasta = ahora + 0.13
                if random.random() < 0.22:
                    t_proximo_parpadeo = ahora + 0.28
                else:
                    t_proximo_parpadeo = ahora + preset_obj.intervalo_parpadeo * random.uniform(0.75, 1.25)

            factor_parpadeo = 0.08 if ahora < parpadeo_hasta else 1.0
            col_principal = _rgb_hex((color_act[0], color_act[1], color_act[2]))
            col_tenue = _rgb_hex((color_act[0] * 0.25, color_act[1] * 0.25, color_act[2] * 0.25))

            try:
                canvas.delete("all")

                # =========================================================
                #  1. PANEL IZQUIERDO: SIMULADOR FÍSICO 3D (UNITREE G1)
                # =========================================================
                canvas.create_rectangle(16, 12, 456, 472, fill="#0D1322", outline="#1E293B", width=2)
                canvas.create_text(
                    32, 28,
                    text="SIMULADOR FÍSICO 3D — UNITREE G1 (29-DoF)",
                    anchor="w",
                    fill="#38BDF8",
                    font=("Segoe UI", 9, "bold"),
                )

                frame_sim_rgb = self.simulador_3d.update()
                self._ultimo_frame_sim = frame_sim_rgb
                if frame_sim_rgb is not None:
                    try:
                        img_sim_pil = Image.fromarray(frame_sim_rgb)
                        photo_sim_ref[0] = ImageTk.PhotoImage(image=img_sim_pil)
                        canvas.create_image(22, 44, anchor="nw", image=photo_sim_ref[0])
                    except Exception:
                        frame_sim_rgb = None

                if frame_sim_rgb is None:
                    # Wireframe estético fallback si MuJoCo no estuviese disponible
                    canvas.create_rectangle(22, 44, 450, 424, fill="#060911", outline="#334155", width=1)
                    canvas.create_text(
                        236, 234,
                        text="VISTA PREVIA G1 ACTIVA\n(MuJoCo Offscreen Standby)",
                        fill="#64748B",
                        font=("Consolas", 10, "bold"),
                        justify="center",
                    )

                # Barra inferior de telemetría del robot
                s_g1 = self.simulador_3d
                telemetria_g1 = (
                    f"X: {s_g1.x:+.2f}m  Y: {s_g1.y:+.2f}m  Yaw: {math.degrees(s_g1.yaw):+3.0f}°  |  "
                    f"Bat: {s_g1.bateria}%  |  Modo: {s_g1.accion.upper()}"
                )
                canvas.create_text(
                    236, 452,
                    text=telemetria_g1,
                    fill="#94A3B8",
                    font=("Consolas", 8, "bold"),
                )

                # =========================================================
                #  2. PANEL CENTRAL: ROSTRO AFECTIVO DE OTTOMAN (G1 OLED VISOR)
                # =========================================================
                canvas.create_rectangle(470, 12, 910, 472, fill="#0D1322", outline=col_tenue, width=2)
                canvas.create_text(
                    690, 28,
                    text=f"OTTOMAN G1  •  MODO: {preset_obj.nombre.upper()}",
                    fill=col_principal,
                    font=("Segoe UI", 9, "bold"),
                )

                if self.incongruencia_activa:
                    canvas.create_rectangle(520, 42, 860, 66, fill="#451A03", outline="#F59E0B", width=1)
                    canvas.create_text(
                        690, 54,
                        text="⚠ ENMASCARAMIENTO DETECTADO (BIOMETRÍA ≠ TEXTO)",
                        fill="#FCD34D",
                        font=("Segoe UI", 8, "bold"),
                    )

                # Modulación de respiración (co-regulación rítmica 8s)
                if preset_obj.guia_respiracion:
                    fase_resp = 0.5 * (1.0 - math.cos(2.0 * math.pi * (ahora % 8.0) / 8.0))
                    d_resp_visor = 4.0 * fase_resp
                    pulso_resp_ojo = 1.0 + 0.14 * fase_resp
                else:
                    fase_resp = 0.0
                    d_resp_visor = 0.0
                    pulso_resp_ojo = 1.0

                # Modulación acústica por voz hablada (Voice Pulse)
                if self.hablando:
                    pulso_habla = 1.0 + 0.16 * abs(math.sin(ahora * 14.0)) + 0.08 * math.sin(ahora * 22.0)
                else:
                    pulso_habla = 1.0

                # Centro del visor y ojos gigantes
                cx_c = 690
                cy_c = 240

                # Visor OLED (Pantalla curvada completa de cristal negro, sin carcasa exterior)
                vx1 = 486 - d_resp_visor
                vy1 = 66 - d_resp_visor
                vx2 = 894 + d_resp_visor
                vy2 = 422 + d_resp_visor

                canvas.create_oval(
                    vx1, vy1, vx2, vy2,
                    fill="#050811", outline="#1E293B", width=3,
                )
                canvas.create_oval(
                    vx1 + 4, vy1 + 4, vx2 - 4, vy2 - 4,
                    outline=col_principal if preset_obj.guia_respiracion else col_tenue,
                    width=1.8,
                )

                # Centro del visor y ojos gigantes
                cx_c = 690
                cy_c = 240
                h_blink = max(0.04, factor_parpadeo)

                # =============================================================
                #  CASO ESPECIAL: GLIFO HEROICO ÚNICO EN EL CENTRO DEL VISOR
                #  Un solo símbolo gigante (!) o (?) centrado en el medio de la cara
                # =============================================================
                if glifo_efectivo in ("!", "?"):
                    if factor_parpadeo < 0.22:
                        w_linea = (ancho_ojo_act * 1.05)
                        canvas.create_line(
                            cx_c - w_linea + mirada_x, cy_c + mirada_y,
                            cx_c + w_linea + mirada_x, cy_c + mirada_y,
                            fill=col_principal, width=10, capstyle="round",
                        )
                    else:
                        t_sz = int(round(135 * pulso_habla * pulso_resp_ojo))
                        canvas.create_text(
                            cx_c + mirada_x, cy_c + mirada_y,
                            text=glifo_efectivo,
                            font=("Segoe UI", max(36, t_sz), "bold"),
                            fill=col_principal,
                        )

                else:
                    # =========================================================
                    #  OJOS LED GIGANTES (MODO DUAL DE 9 MORFOLOGÍAS)
                    # =========================================================
                    cx_izq = cx_c - 82
                    cx_der = cx_c + 82
                    cy_ojo = cy_c

                    for sig, ox in ((-1, cx_izq), (1, cx_der)):
                        es_izq = (sig == -1)
                        escala_lado = asimetria_act if es_izq else 1.0

                        # Parpadeo rápido (cierre horizontal de párpado electrónico)
                        if factor_parpadeo < 0.22:
                            w_linea = (ancho_ojo_act * 0.65) * escala_lado
                            canvas.create_line(
                                ox - w_linea + mirada_x, cy_ojo + mirada_y,
                                ox + w_linea + mirada_x, cy_ojo + mirada_y,
                                fill=col_principal, width=8, capstyle="round",
                            )
                            continue

                        # Caso A: Chispa / Estrella Eureka
                        if forma_ojo_efectiva == "chispa_estrella":
                            rx = (ancho_ojo_act * 0.54) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.52) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            pts_star = [
                                ox + mirada_x, cy_ojo - ry * 1.08 + mirada_y,
                                ox + rx * 0.30 + mirada_x, cy_ojo - ry * 0.30 + mirada_y,
                                ox + rx * 1.08 + mirada_x, cy_ojo + mirada_y,
                                ox + rx * 0.30 + mirada_x, cy_ojo + ry * 0.30 + mirada_y,
                                ox + mirada_x, cy_ojo + ry * 1.08 + mirada_y,
                                ox - rx * 0.30 + mirada_x, cy_ojo + ry * 0.30 + mirada_y,
                                ox - rx * 1.08 + mirada_x, cy_ojo + mirada_y,
                                ox - rx * 0.30 + mirada_x, cy_ojo - ry * 0.30 + mirada_y,
                            ]
                            canvas.create_polygon(*pts_star, fill=col_principal, outline="", smooth=False)

                        # Caso B: Entrecerrado Enfoque (Análisis táctico y concentración)
                        elif forma_ojo_efectiva == "entrecerrado_enfoque":
                            rx = (ancho_ojo_act * 0.58) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.22) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            if rx > ry + 2:
                                canvas.create_line(
                                    ox - (rx - ry) + mirada_x, cy_ojo + mirada_y,
                                    ox + (rx - ry) + mirada_x, cy_ojo + mirada_y,
                                    width=max(4, int(2 * ry)), fill=col_principal, capstyle="round",
                                )
                            else:
                                canvas.create_oval(
                                    ox - rx + mirada_x, cy_ojo - ry + mirada_y,
                                    ox + rx + mirada_x, cy_ojo + ry + mirada_y,
                                    fill=col_principal, outline="",
                                )

                        # Caso C: Ojo Circular Asombro (Sorpresa genuina abierta y amplia)
                        elif forma_ojo_efectiva == "ojo_circular_asombro":
                            r_circ = min(70.0, (alto_ojo_act * 0.58) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo)
                            canvas.create_oval(
                                ox - r_circ + mirada_x, cy_ojo - r_circ + mirada_y,
                                ox + r_circ + mirada_x, cy_ojo + r_circ + mirada_y,
                                fill=col_principal, outline="",
                            )

                        # Caso D: Arco Feliz (Motivación / Alegría ^ ^)
                        elif forma_ojo_efectiva == "arco_feliz" or (arco_act > 0.45 and forma_ojo_efectiva == "capsula"):
                            rx = (ancho_ojo_act * 0.68) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.52) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            t_vals = [0.18 + i * (math.pi - 0.36) / 8 for i in range(9)]
                            pts_arco = []
                            for t_ang in t_vals:
                                pts_arco.extend([
                                    ox + rx * math.cos(t_ang) + mirada_x,
                                    cy_ojo - ry * math.sin(t_ang) + mirada_y,
                                ])
                            canvas.create_line(*pts_arco, smooth=True, fill=col_principal, width=20, capstyle="round")

                        # Caso E: Diagonal Enojo / Firmeza (\ /)
                        elif forma_ojo_efectiva == "diagonal_enojo":
                            rx = (ancho_ojo_act * 0.50) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.46) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            s = 1 if es_izq else -1
                            d_corte = inc_ojo_act * 0.95
                            pts = [
                                ox - rx + mirada_x, cy_ojo - ry - d_corte * s + mirada_y,
                                ox + rx + mirada_x, cy_ojo - ry + d_corte * s + mirada_y,
                                ox + rx * 0.82 + mirada_x, cy_ojo + ry + mirada_y,
                                ox - rx * 0.82 + mirada_x, cy_ojo + ry + mirada_y,
                            ]
                            canvas.create_polygon(*pts, fill=col_principal, outline="", smooth=False)

                        # Caso F: Párpado Inferior Cálido (Empatía Cálida y Contención / EVE / Cozmo)
                        elif forma_ojo_efectiva in ("parpado_inferior_calido", "caido_triste"):
                            rx = (ancho_ojo_act * 0.48) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.46) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            y_base = cy_ojo + ry * 0.22
                            t_steps = 32
                            pts = []
                            for i in range(t_steps + 1):
                                t_ang = math.pi * i / t_steps
                                px = ox + rx * math.cos(t_ang) + mirada_x
                                py = y_base - ry * 1.08 * math.sin(t_ang) + mirada_y
                                pts.extend([px, py])
                            pts.extend([ox - rx + mirada_x, y_base + mirada_y, ox + rx + mirada_x, y_base + mirada_y])
                            canvas.create_polygon(*pts, fill=col_principal, outline="", smooth=False)

                        # Caso G: Suave Calma (Serenidad Zen / Co-regulación con la parte elevada al medio / \)
                        elif forma_ojo_efectiva == "suave_calma":
                            w_calma = (ancho_ojo_act * 0.68) * pulso_resp_ojo
                            dy_calma = 14.0
                            if es_izq:
                                y_left = cy_ojo + dy_calma
                                y_right = cy_ojo - dy_calma
                            else:
                                y_left = cy_ojo - dy_calma
                                y_right = cy_ojo + dy_calma
                            canvas.create_line(
                                ox - w_calma + mirada_x, y_left + mirada_y,
                                ox + w_calma + mirada_x, y_right + mirada_y,
                                fill=col_principal, width=12, capstyle="round",
                            )

                        # Caso I: Cápsula vertical (Neutro - Pill pura vertical EVE/Cozmo)
                        else:
                            rx = (ancho_ojo_act * 0.48) * pulso_resp_ojo
                            ry = (alto_ojo_act * 0.50) * apertura_act * h_blink * pulso_habla * pulso_resp_ojo
                            if ry > rx + 2:
                                canvas.create_line(
                                    ox + mirada_x, cy_ojo - (ry - rx) + mirada_y,
                                    ox + mirada_x, cy_ojo + (ry - rx) + mirada_y,
                                    width=max(4, int(2 * rx)), fill=col_principal, capstyle="round",
                                )
                            else:
                                canvas.create_oval(
                                    ox - rx + mirada_x, cy_ojo - ry + mirada_y,
                                    ox + rx + mirada_x, cy_ojo + ry + mirada_y,
                                    fill=col_principal, outline="",
                                )

                # 5. Indicadores inferiores de co-regulación o habla
                if preset_obj.guia_respiracion:
                    txt_resp = "INHALÁ SUAVE (4s)..." if (ahora % 8.0) < 4.0 else "EXHALÁ LENTO (4s)..."
                    canvas.create_text(
                        690, 442,
                        text=f"🌀 {txt_resp}  •  CO-REGULACIÓN ACTIVA",
                        fill=col_principal,
                        font=("Segoe UI", 9, "bold italic"),
                    )
                elif self.hablando:
                    onda = " • " * int(2 + 2 * abs(math.sin(ahora * 8.0)))
                    canvas.create_text(
                        690, 442,
                        text=f"🎙️ TRANSMITIENDO VOZ{onda}",
                        fill=col_principal,
                        font=("Segoe UI", 8, "bold"),
                    )

                # =========================================================
                #  3. PANEL DERECHO: VISIÓN FACS Y RUSSELL CARTESIANO
                # =========================================================
                self._dibujar_panel_camara(canvas, photo_cam_ref, ahora, col_principal)
                self._dibujar_panel_russell(canvas, val_interp, aro_interp, ahora, col_principal)

            except Exception as _exc_render:
                pass
            finally:
                if self._activo:
                    root.after(30, _tick)

        _tick()
        root.mainloop()

    def _dibujar_panel_camara(self, canvas, photo_ref: list, ahora: float, col_principal: str) -> None:
        """Renderiza cámara OpenCV en vivo o radar biométrico FACS + barras de unidades de acción."""
        x1, y1, x2, y2 = 924, 12, 1364, 238
        canvas.create_rectangle(x1, y1, x2, y2, fill="#0D1322", outline="#1E293B", width=2)
        canvas.create_text(
            x1 + 14, y1 + 18,
            text="VISIÓN FACS — DETECCIÓN FACIAL (OpenCV)",
            anchor="w",
            fill="#38BDF8",
            font=("Segoe UI", 9, "bold"),
        )

        vx1, vy1 = x1 + 14, y1 + 34
        vx2, vy2 = vx1 + 230, vy1 + 164
        canvas.create_rectangle(vx1, vy1, vx2, vy2, fill="#060911", outline="#334155", width=1)

        frame_copia = None
        with self._lock_frame:
            if self._ultimo_frame_rgb is not None:
                frame_copia = self._ultimo_frame_rgb.copy()

        mf = self.metricas_faciales_dict
        if frame_copia is not None:
            try:
                from PIL import Image, ImageTk
                img_pil = Image.fromarray(frame_copia)
                photo_ref[0] = ImageTk.PhotoImage(image=img_pil)
                canvas.create_image(vx1, vy1, anchor="nw", image=photo_ref[0])
                if mf.get("rostro_detectado"):
                    canvas.create_rectangle(vx1 + 8, vy2 - 22, vx2 - 8, vy2 - 4, fill="#0F172A", outline="#10B981")
                    canvas.create_text(
                        (vx1 + vx2) // 2, vy2 - 13,
                        text=f"ROSTRO DETECTADO: {mf.get('emocion_facial', 'NEUTRO')}",
                        fill="#34D399", font=("Segoe UI", 7, "bold"),
                    )
                else:
                    canvas.create_rectangle(vx1 + 8, vy2 - 22, vx2 - 8, vy2 - 4, fill="#0F172A", outline="#F59E0B")
                    canvas.create_text(
                        (vx1 + vx2) // 2, vy2 - 13,
                        text="CÁMARA ACTIVA • BUSCANDO ROSTRO...",
                        fill="#FBBF24", font=("Segoe UI", 7, "bold"),
                    )
            except Exception:
                frame_copia = None

        if frame_copia is None:
            # Componente de cámara Offline / Sin señal (sin dibujos de caras artificiales)
            cx, cy = (vx1 + vx2) // 2, (vy1 + vy2) // 2 - 10
            # Chasis técnico de cámara desconectada
            canvas.create_rectangle(cx - 30, cy - 18, cx + 30, cy + 18, fill="#0F172A", outline="#334155", width=1.5)
            canvas.create_rectangle(cx - 10, cy - 24, cx + 10, cy - 18, fill="#1E293B", outline="#334155", width=1)
            canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#050811", outline="#475569", width=1.5)
            canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#1E293B", outline="")
            # Barra diagonal indicadora de corte de señal
            canvas.create_line(cx - 35, cy + 24, cx + 35, cy - 24, fill="#F87171", width=2.5, capstyle="round")

            canvas.create_text(cx, cy + 38, text="CÁMARA OFFLINE", fill="#F87171", font=("Segoe UI", 9, "bold"))
            canvas.create_text(cx, cy + 54, text="Sin señal de video USB", fill="#64748B", font=("Segoe UI", 7, "bold"))
            canvas.create_text(
                cx, vy2 - 10,
                text="[ RECONECTAR DESDE EL BOTÓN INFERIOR ]",
                fill="#475569",
                font=("Consolas", 6, "bold"),
            )

        # Barras de Unidades de Acción Facial (FACS Gauges)
        gx = vx2 + 12
        hay_rostro_real = (frame_copia is not None) and bool(mf.get("rostro_detectado", False))

        if hay_rostro_real:
            metricas_barras = [
                ("AU1/5 Ojos", float(mf.get("apertura_ojos", 0.0)), "#38BDF8"),
                ("AU4 Cejas", float(mf.get("tension_cejas", 0.0)), "#F59E0B"),
                ("AU12 Sonrisa", max(0.0, (float(mf.get("curvatura_boca", 0.0)) + 1.0) * 0.5), "#10B981"),
                ("AU25 Boca", float(mf.get("apertura_boca", 0.0)), "#A78BFA"),
            ]
            for idx_b, (etq, valor_norm, col_b) in enumerate(metricas_barras):
                by = vy1 + 6 + idx_b * 40
                v_clip = max(0.0, min(1.0, valor_norm))
                canvas.create_text(gx, by, text=f"{etq} ({v_clip:.2f})", anchor="w", fill="#CBD5E1", font=("Segoe UI", 7, "bold"))
                canvas.create_rectangle(gx, by + 10, x2 - 14, by + 20, fill="#1E293B", outline="")
                ancho_max = (x2 - 14) - gx
                canvas.create_rectangle(gx, by + 10, gx + ancho_max * v_clip, by + 20, fill=col_b, outline="")
        else:
            # Datos en reposo / offline: sin barras de color ni valores inventados
            metricas_inactivas = [
                "AU1/5 Ojos",
                "AU4 Cejas",
                "AU12 Sonrisa",
                "AU25 Boca",
            ]
            for idx_b, etq in enumerate(metricas_inactivas):
                by = vy1 + 6 + idx_b * 40
                canvas.create_text(gx, by, text=f"{etq} [--]", anchor="w", fill="#64748B", font=("Segoe UI", 7, "bold"))
                canvas.create_rectangle(gx, by + 10, x2 - 14, by + 20, fill="#0F172A", outline="#1E293B")
            canvas.create_text(gx, vy2 - 4, text="FACS: DATOS EN REPOSO", anchor="w", fill="#475569", font=("Consolas", 6, "bold"))

        canales_str = " + ".join(c.upper() for c in self.canales_activos)
        canvas.create_text(
            x1 + 14, y2 - 14,
            text=f"Fusión AG: [{canales_str}]",
            anchor="w",
            fill="#A7F3D0",
            font=("Consolas", 8, "bold"),
        )

    def _dibujar_panel_russell(
        self, canvas, valencia: float, arousal: float, ahora: float, col_principal: str
    ) -> None:
        """Dibuja el Plano Circumplejo Valencia-Arousal en tiempo real."""
        x1, y1, x2, y2 = 924, 246, 1364, 472
        canvas.create_rectangle(x1, y1, x2, y2, fill="#0D1322", outline="#1E293B", width=2)
        canvas.create_text(
            x1 + 14, y1 + 18,
            text="PLANO VALENCIA–AROUSAL EN TIEMPO REAL (RUSSELL)",
            anchor="w",
            fill="#A78BFA",
            font=("Segoe UI", 9, "bold"),
        )

        cx = x1 + 150
        cy = y1 + 120
        radio = 84

        canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill="#080D1A", outline="#334155", width=2)
        r_med = radio * 0.55
        canvas.create_oval(cx - r_med, cy - r_med, cx + r_med, cy + r_med, outline="#1E293B", width=1, dash=(3, 3))

        canvas.create_line(cx - radio - 6, cy, cx + radio + 6, cy, fill="#475569", width=1)
        canvas.create_line(cx, cy - radio - 6, cx, cy + radio + 6, fill="#475569", width=1)

        canvas.create_text(cx - 40, cy - 44, text="ANSIEDAD /\nENOJO", fill="#FCA5A5", font=("Segoe UI", 6, "bold"), justify="center")
        canvas.create_text(cx + 40, cy - 44, text="MOTIVACIÓN /\nALEGRÍA", fill="#FDE047", font=("Segoe UI", 6, "bold"), justify="center")
        canvas.create_text(cx - 40, cy + 44, text="TRISTEZA /\nDESÁNIMO", fill="#93C5FD", font=("Segoe UI", 6, "bold"), justify="center")
        canvas.create_text(cx + 40, cy + 44, text="CALMA /\nSERENIDAD", fill="#6EE7B7", font=("Segoe UI", 6, "bold"), justify="center")

        canvas.create_text(cx + radio + 8, cy, text="+V", anchor="w", fill="#94A3B8", font=("Consolas", 7, "bold"))
        canvas.create_text(cx - radio - 8, cy, text="-V", anchor="e", fill="#94A3B8", font=("Consolas", 7, "bold"))
        canvas.create_text(cx, cy - radio - 8, text="+A", fill="#94A3B8", font=("Consolas", 7, "bold"))
        canvas.create_text(cx, cy + radio + 8, text="-A", fill="#94A3B8", font=("Consolas", 7, "bold"))

        hist = list(self.historial_va)
        if len(hist) >= 2:
            pts_hist = []
            for hv, ha, _ in hist:
                pts_hist.extend([cx + hv * radio, cy - ha * radio])
            canvas.create_line(*pts_hist, fill="#64748B", width=2, dash=(3, 2))
            for hv, ha, _ in hist[:-1]:
                px, py = cx + hv * radio, cy - ha * radio
                canvas.create_oval(px - 3, py - 3, px + 3, py + 3, fill="#94A3B8", outline="")

        px_act = cx + valencia * radio
        py_act = cy - arousal * radio
        pulso = 8.0 + 4.0 * abs(math.sin(ahora * 4.2))
        canvas.create_oval(
            px_act - pulso, py_act - pulso, px_act + pulso, py_act + pulso,
            outline=col_principal, width=2,
        )
        canvas.create_oval(
            px_act - 5, py_act - 5, px_act + 5, py_act + 5,
            fill=col_principal, outline="#FFFFFF", width=1,
        )

        tx = cx + radio + 26
        intens = min(1.0, math.hypot(valencia, arousal) / math.sqrt(2.0))
        bloques = [
            ("ESTADO:", self.emocion_actual[:13], col_principal),
            ("VALENCIA:", f"{valencia:+.2f}", "#F8FAFC"),
            ("AROUSAL:", f"{arousal:+.2f}", "#F8FAFC"),
            ("INTENSIDAD:", f"{intens*100:.0f}%", "#38BDF8"),
            ("HISTORIAL:", f"{len(hist)} / 8", "#A7F3D0"),
        ]
        for idx_t, (tit_b, val_b, col_b) in enumerate(bloques):
            by = y1 + 36 + idx_t * 36
            canvas.create_text(tx, by, text=tit_b, anchor="w", fill="#94A3B8", font=("Segoe UI", 7, "bold"))
            canvas.create_text(tx + 75, by, text=val_b, anchor="w", fill=col_b, font=("Consolas", 9, "bold"))


# =====================================================================
#  EXPORTADOR DE CAPTURA ESTÁTICA PARA EL INFORME Y PPT
# =====================================================================

def exportar_captura_dashboard_png(ruta_salida: Path) -> Path:
    """Genera un render estático de alta resolución del Modo Dashboard para el Informe y PPT."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13.8, 8.7), dpi=180, facecolor="#070B14")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#070B14")
    ax.set_xlim(0, 1380)
    ax.set_ylim(870, 0)
    ax.axis("off")

    # 1. Panel Izquierdo: Simulador 3D G1
    ax.add_patch(patches.FancyBboxPatch((16, 12), 440, 460, boxstyle="round,pad=0,rounding_size=6",
                                        facecolor="#0D1322", edgecolor="#1E293B", linewidth=2))
    ax.text(32, 28, "SIMULADOR FÍSICO 3D — UNITREE G1 (29-DoF)", color="#38BDF8",
            fontsize=9.5, fontweight="bold", ha="left", va="center")
    ax.add_patch(patches.Rectangle((22, 44), 428, 380, facecolor="#060911", edgecolor="#334155"))
    ax.text(236, 234, "UNITREE G1 EMBEBIDO\n(Render MuJoCo Oficial 35 FPS)",
            color="#60A5FA", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(236, 452, "X: +0.00m  Y: +0.00m  Yaw: +0°  |  Bat: 87%  |  Modo: QUIETO",
            color="#94A3B8", fontsize=8.2, family="monospace", ha="center", va="center")

    # 2. Panel Central: Rostro Afectivo Ottoman (G1 OLED Visor)
    ax.add_patch(patches.FancyBboxPatch((470, 12), 440, 460, boxstyle="round,pad=0,rounding_size=6",
                                        facecolor="#0D1322", edgecolor="#1D4ED8", linewidth=2.5))
    ax.text(690, 28, "OTTOMAN G1  •  MODO: CO-REGULACIÓN Y CALMA RESPIRATORIA",
            color="#38BDF8", fontsize=9.5, fontweight="bold", ha="center", va="center")
    ax.add_patch(patches.Rectangle((520, 42), 340, 24, facecolor="#451A03", edgecolor="#F59E0B", linewidth=1))
    ax.text(690, 54, "ENMASCARAMIENTO DETECTADO: BIOMETRÍA ≠ TEXTO",
            color="#FCD34D", fontsize=7.5, fontweight="bold", ha="center", va="center")

    # Visor negro OLED completo (enfoque en ojos gigantes, sin carcasa exterior)
    ax.add_patch(patches.FancyBboxPatch((486, 66), 408, 356, boxstyle="round,pad=0,rounding_size=60",
                                        facecolor="#050811", edgecolor="#1E293B", linewidth=3.0))
    # Resplandor interior suave
    ax.add_patch(patches.FancyBboxPatch((490, 70), 400, 348, boxstyle="round,pad=0,rounding_size=56",
                                        fill=False, edgecolor="#38BDF8", linewidth=1.8, alpha=0.5))

    # Ojos LED (Calma / Co-regulación respiratoria - líneas zen con parte elevada al medio / \)
    for sig, cx_o in ((-1, 690 - 82), (1, 690 + 82)):
        y_ext = 240 + 7.0
        y_int = 240 - 7.0
        y1_p = y_ext if sig == -1 else y_int
        y2_p = y_int if sig == -1 else y_ext
        ax.plot([cx_o - 30, cx_o + 30], [y1_p, y2_p], color="#38BDF8", linewidth=7.5, solid_capstyle="round")

    ax.text(690, 442, "INHALÁ SUAVE (4s)...  •  GUÍA DE CO-REGULACIÓN ACTIVA",
            color="#38BDF8", fontsize=8.8, style="italic", fontweight="bold", ha="center", va="center")

    # 3. Panel Superior Derecho: Visión FACS OpenCV
    ax.add_patch(patches.FancyBboxPatch((924, 12), 440, 226, boxstyle="round,pad=0,rounding_size=6",
                                        facecolor="#0D1322", edgecolor="#1E293B", linewidth=2))
    ax.text(938, 28, "VISIÓN FACS — DETECCIÓN FACIAL (OpenCV)", color="#38BDF8",
            fontsize=9.0, fontweight="bold", ha="left", va="center")
    ax.add_patch(patches.Rectangle((938, 44), 230, 164, facecolor="#060911", edgecolor="#334155"))
    ax.text(1053, 126, "FACS HUD ACTIVO\n[ANSIEDAD_ESTRES]", color="#94A3B8",
            fontsize=7.8, family="monospace", ha="center", va="center")

    barras = [
        ("AU1/5 Ojos", 0.82, "#38BDF8"),
        ("AU4 Cejas", 0.64, "#F59E0B"),
        ("AU12 Sonrisa", 0.34, "#10B981"),
        ("AU25 Boca", 0.28, "#A78BFA"),
    ]
    for idx_b, (lbl, v_b, col_b) in enumerate(barras):
        by = 56 + idx_b * 38
        ax.text(1182, by, lbl, color="#CBD5E1", fontsize=7.2, ha="left", va="center")
        ax.add_patch(patches.Rectangle((1182, by + 8), 160, 10, facecolor="#1E293B"))
        ax.add_patch(patches.Rectangle((1182, by + 8), 160 * v_b, 10, facecolor=col_b))

    # 4. Panel Inferior Derecho: Plano Valencia-Arousal de Russell
    ax.add_patch(patches.FancyBboxPatch((924, 246), 440, 226, boxstyle="round,pad=0,rounding_size=6",
                                        facecolor="#0D1322", edgecolor="#1E293B", linewidth=2))
    ax.text(938, 262, "PLANO VALENCIA–AROUSAL EN TIEMPO REAL (RUSSELL)", color="#A78BFA",
            fontsize=9.0, fontweight="bold", ha="left", va="center")
    cx, cy, rad = 1074, 366, 82
    ax.add_patch(patches.Circle((cx, cy), rad, facecolor="#080D1A", edgecolor="#334155", linewidth=1.8))
    ax.plot([cx - rad - 6, cx + rad + 6], [cy, cy], color="#475569", linewidth=1)
    ax.plot([cx, cx], [cy - rad - 6, cy + rad + 6], color="#475569", linewidth=1)

    tray = [(0.10, 0.05), (-0.22, -0.35), (-0.42, 0.28), (-0.56, 0.68)]
    xs_t = [cx + v * rad for v, _ in tray]
    ys_t = [cy - a * rad for _, a in tray]
    ax.plot(xs_t, ys_t, color="#64748B", linewidth=1.8, linestyle="--")
    for px_i, py_i in zip(xs_t[:-1], ys_t[:-1]):
        ax.add_patch(patches.Circle((px_i, py_i), 3.5, facecolor="#94A3B8"))
    ax.add_patch(patches.Circle((xs_t[-1], ys_t[-1]), 10, fill=False, edgecolor="#60A5FA", linewidth=2))
    ax.add_patch(patches.Circle((xs_t[-1], ys_t[-1]), 5, facecolor="#60A5FA"))

    # 5. Barra Intermedia de Sensores
    ax.add_patch(patches.Rectangle((16, 480), 1348, 38, facecolor="#0B1120", edgecolor="#1E293B"))
    ax.text(32, 499, "[CAM] Cámara: ACTIVA (30 FPS)   |   [MIC] Micrófono: ACTIVO (DSP 16kHz)   |   [G1] 29-DoF MuJoCo Activo",
            color="#38BDF8", fontsize=8.8, fontweight="bold", ha="left", va="center")

    # 6. Panel Inferior de Chat
    ax.add_patch(patches.Rectangle((16, 526), 1348, 330, facecolor="#0B101E", edgecolor="#1E293B"))
    ax.text(32, 552, "\"Tus palabras dicen 'estoy bien', pero percibo tensión en tu rostro y voz. Hagamos una pausa.\"",
            color="#F9FAFB", fontsize=9.2, fontweight="bold", ha="left", va="center")
    ax.text(32, 580, "[Vos]: Estoy bien... aunque un poco saturado con la entrega del trabajo práctico.",
            color="#38BDF8", fontsize=8.5, ha="left", va="center")
    ax.text(32, 608, "[Ottoman]: Te entiendo. Bajemos un cambio juntos: inhalá lento 4 segundos.",
            color="#A7F3D0", fontsize=8.5, ha="left", va="center")

    fig.savefig(ruta_salida, dpi=180, facecolor="#070B14")
    plt.close(fig)
    return ruta_salida
