"""Control de la mano Inspire (5 dedos) en el G1 REAL via DDS.

Misma firma que simulador.ejecutor_pose.ejecutor_pose:

    ejecutor_pose(pose) -> str

Patron de red tomado del repo UADE (talleres G1):
  ChannelFactoryInitialize(domain=0, interfaz="enp0s31f6"|"eth0"|...)

Mano Inspire (docs Unitree + dfx_inspire_service; NO esta en este repo):
  topic cmd:   rt/inspire/cmd   (MotorCmds_)
  topic state: rt/inspire/state (MotorStates_)
  indices: 0-5 derecha, 6-11 izquierda
  orden: pinky, ring, middle, index, thumb_bend, thumb_rotation
  q: 1.0 abierto, 0.0 cerrado

SUPUESTOS A CONFIRMAR en clase (marcados abajo):
  - Que el servicio inspire_g1 este corriendo en el robot.
  - Interfaz de red exacta del notebook del lab.
  - Que el Ottoman use Inspire RH56 (profe lo confirmo) y no Dex3.
"""

from __future__ import annotations

import time
from typing import Any

# ---------------------------------------------------------------------------
# Configuracion de laboratorio — ajustar el dia de la prueba si hace falta
# ---------------------------------------------------------------------------
DDS_DOMAIN: int = 0          # robot real en el repo UADE usa domain 0
DDS_INTERFAZ: str = "enp0s31f6"  # alternativas tipicas: eth0, Ethernet
TOPIC_INSPIRE_CMD: str = "rt/inspire/cmd"
TOPIC_INSPIRE_STATE: str = "rt/inspire/state"  # solo lectura; no obligatorio
HOLD_SEGUNDOS: float = 0.4   # cuanto mantener cada frame publicado
RATE_HZ: float = 50.0

# Mapeo visible y facil de tocar si el orden en el lab no coincide.
# SUPUESTO A CONFIRMAR: orden oficial RH56 de dfx_inspire_service.
MAPEO_DEDOS_DERECHA: dict[str, int] = {
    "pinky": 0,
    "ring": 1,
    "middle": 2,
    "index": 3,
    "thumb_bend": 4,
    "thumb_rotation": 5,
}
MAPEO_DEDOS_IZQUIERDA: dict[str, int] = {
    "pinky": 6,
    "ring": 7,
    "middle": 8,
    "index": 9,
    "thumb_bend": 10,
    "thumb_rotation": 11,
}


class ErrorConexionRobot(RuntimeError):
    """Fallo claro de conexion / SDK / DDS."""


class EjecutorPoseReal:
    """Publica poses Inspire por DDS. Lazy-connect al primer uso."""

    def __init__(
        self,
        domain: int = DDS_DOMAIN,
        interfaz: str = DDS_INTERFAZ,
        topic_cmd: str = TOPIC_INSPIRE_CMD,
    ):
        self.domain = domain
        self.interfaz = interfaz
        self.topic_cmd = topic_cmd
        self._pub = None
        self._MotorCmds_ = None
        self._MotorCmd_ = None
        self._conectado = False

    def conectar(self) -> None:
        if self._conectado:
            return
        try:
            from unitree_sdk2py.core.channel import (
                ChannelFactoryInitialize,
                ChannelPublisher,
            )
            from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmd_, MotorCmds_
        except ImportError as exc:
            raise ErrorConexionRobot(
                "No esta instalado unitree_sdk2py.\n"
                "  En la PC del lab (Linux):\n"
                "    pip install cyclonedds==0.10.2\n"
                "    git clone https://github.com/unitreerobotics/unitree_sdk2_python\n"
                "    pip install -e unitree_sdk2_python\n"
                "Ver tp07_lsa/README.md"
            ) from exc

        try:
            ChannelFactoryInitialize(self.domain, self.interfaz)
            pub = ChannelPublisher(self.topic_cmd, MotorCmds_)
            pub.Init()
        except Exception as exc:  # noqa: BLE001 — queremos mensaje claro en clase
            raise ErrorConexionRobot(
                f"No pude abrir DDS domain={self.domain} interfaz='{self.interfaz}'.\n"
                "  Revisá: robot encendido, notebook en 192.168.123.x, "
                "interfaz correcta (ip link / ifconfig),\n"
                "  y que inspire_g1 (dfx_inspire_service) este corriendo en el G1.\n"
                f"  Detalle tecnico: {exc}"
            ) from exc

        self._pub = pub
        self._MotorCmds_ = MotorCmds_
        self._MotorCmd_ = MotorCmd_
        self._conectado = True
        print(
            f"  [REAL] Conectado Inspire DDS "
            f"domain={self.domain} iface={self.interfaz} topic={self.topic_cmd}"
        )

    def desconectar(self) -> None:
        self._pub = None
        self._conectado = False

    def _pose_a_vector12(self, pose: dict) -> list[float]:
        """Arma el vector de 12 motores (der 0-5 + izq 6-11), default abierto."""
        q = [1.0] * 12
        for dedo, idx in MAPEO_DEDOS_DERECHA.items():
            if dedo in (pose.get("mano_derecha") or {}):
                q[idx] = float(pose["mano_derecha"][dedo])
        for dedo, idx in MAPEO_DEDOS_IZQUIERDA.items():
            if dedo in (pose.get("mano_izquierda") or {}):
                q[idx] = float(pose["mano_izquierda"][dedo])
        return [max(0.0, min(1.0, v)) for v in q]

    def _publicar(self, vector12: list[float]) -> None:
        motors = []
        for q in vector12:
            motors.append(
                self._MotorCmd_(
                    mode=1,
                    q=float(q),
                    dq=0.0,
                    tau=0.0,
                    kp=0.0,
                    kd=0.0,
                    reserve=[0, 0, 0],
                )
            )
        msg = self._MotorCmds_()
        msg.cmds = motors
        self._pub.Write(msg)

    def ejecutor_pose(
        self,
        pose: dict | list[dict],
        hold: float = HOLD_SEGUNDOS,
    ) -> str:
        self.conectar()
        frames = pose if isinstance(pose, list) else [pose]
        periodo = 1.0 / RATE_HZ
        for frame in frames:
            if not isinstance(frame, dict):
                raise TypeError("cada frame debe ser un dict de pose")
            vector = self._pose_a_vector12(frame)
            fin = time.time() + hold
            while time.time() < fin:
                self._publicar(vector)
                time.sleep(periodo)
        return f"pose real OK (frames={len(frames)}, hold={hold}s)"


# Instancia por defecto (lazy).
_ejecutor_global: EjecutorPoseReal | None = None


def get_ejecutor(
    domain: int = DDS_DOMAIN,
    interfaz: str = DDS_INTERFAZ,
) -> EjecutorPoseReal:
    global _ejecutor_global
    if _ejecutor_global is None:
        _ejecutor_global = EjecutorPoseReal(domain=domain, interfaz=interfaz)
    return _ejecutor_global


def ejecutor_pose(pose: dict | list[dict], **kwargs: Any) -> str:
    """API espejo de simulador.ejecutor_pose.ejecutor_pose."""
    interfaz = kwargs.pop("interfaz", DDS_INTERFAZ)
    domain = kwargs.pop("domain", DDS_DOMAIN)
    hold = kwargs.pop("hold", HOLD_SEGUNDOS)
    robot = kwargs.pop("robot", None)  # ignorado en real (firma compatible)
    _ = robot
    return get_ejecutor(domain=domain, interfaz=interfaz).ejecutor_pose(
        pose, hold=hold
    )


ejecutar_pose = ejecutor_pose
