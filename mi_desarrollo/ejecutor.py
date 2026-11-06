# =====================================================================
#  Ejecutor Multimodal (TP07 Oficial + Extensión Ottoman Coach)
#
#  Es la cuarta etapa del pipeline: recibe la intención ya clasificada,
#  parametrizada y validada por ValidadorSeguridad, y la traduce en
#  acciones físicas seguras sobre el Unitree G1 + Voz TTS + Rostro Digital.
# =====================================================================

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional

_ENTORNO = Path(__file__).resolve().parent.parent / "entorno"
if str(_ENTORNO) not in sys.path:
    sys.path.insert(0, str(_ENTORNO))

try:
    from sim.safety import ErrorDeSeguridad
except ImportError:
    class ErrorDeSeguridad(ValueError):
        pass


def partir_en_tramos(tiempo_total: float, tope: float) -> list[float]:
    """Divide un movimiento largo en órdenes que no superen el tope de seguridad."""
    if tiempo_total <= tope:
        return [tiempo_total]
    tramos = []
    restante = float(tiempo_total)
    while restante > tope + 1e-9:
        tramos.append(tope)
        restante -= tope
    if restante > 1e-9:
        tramos.append(restante)
    return tramos


class Ejecutor:
    """Traduce intenciones validadas a movimientos del G1, voz prosódica y rostro."""

    def __init__(self, robot, mostrar: bool = True, sintetizador_voz=None, rostro=None):
        self.robot = robot
        self.mostrar = mostrar
        self.perfil = robot.perfil
        self.sintetizador_voz = sintetizador_voz
        self.rostro = rostro

    def ejecutar(self, tipo: str, parametros: Optional[dict] = None) -> str:
        """Envía la intención validada a los actuadores correspondientes."""
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
                self.robot.saludar()
                return "saludo"
            if tipo == "CONSULTAR_ESTADO":
                e = self.robot.verificar_estado()
                return f"estado: {e}"
            if tipo == "COACH_EMOCIONAL":
                return self._ejecutar_coach(parametros)
        except ErrorDeSeguridad as exc:
            return f"RECHAZADO POR EL ROBOT: {exc}"
        return f"no se como ejecutar {tipo}"

    def _mover(self, p: dict) -> str:
        distancia = float(p.get("distancia_m", 0.5))
        velocidad = float(p.get("velocidad_ms", self.perfil.velocidad_max))
        velocidad = min(abs(velocidad), self.perfil.velocidad_max)
        if velocidad <= 0:
            return "velocidad cero: no hay nada que ejecutar"

        signo = -1.0 if p.get("direccion") == "atras" else 1.0
        tiempo_total = abs(distancia) / velocidad
        tramos = partir_en_tramos(tiempo_total, self.perfil.duracion_max)

        self._log(
            f"{distancia:g} m a {velocidad:g} m/s = {tiempo_total:.2f} s"
            + (f", partido en {len(tramos)} tramos" if len(tramos) > 1 else "")
        )
        for i, t in enumerate(tramos, 1):
            self._log(f"  tramo {i}/{len(tramos)}: avanzar({signo * velocidad:+.2f}, {t:.2f})")
            self.robot.avanzar(velocidad=signo * velocidad, tiempo=t)
        return f"avanzo {distancia:g} m en {len(tramos)} orden(es)"

    def _girar(self, p: dict) -> str:
        grados = float(p.get("angulo_deg", 90))
        velocidad = float(p.get("velocidad_giro", self.perfil.velocidad_angular_max))
        velocidad = min(abs(velocidad), self.perfil.velocidad_angular_max)
        if velocidad <= 0:
            return "velocidad de giro cero"

        signo = -1.0 if p.get("direccion") == "derecha" else 1.0
        radianes = math.radians(abs(grados))
        tiempo_total = radianes / velocidad
        tramos = partir_en_tramos(tiempo_total, self.perfil.duracion_max)

        lado = "derecha" if signo < 0 else "izquierda"
        self._log(
            f"{grados:g} grados = {radianes:.4f} rad a la {lado}, "
            f"a {velocidad:g} rad/s = {tiempo_total:.2f} s"
            + (f", partido en {len(tramos)} tramos" if len(tramos) > 1 else "")
        )
        for i, t in enumerate(tramos, 1):
            self._log(f"  tramo {i}/{len(tramos)}: girar({signo * velocidad:+.2f}, {t:.2f})")
            self.robot.girar(velocidad=signo * velocidad, tiempo=t)
        return f"giro {grados:g} grados a la {lado} en {len(tramos)} orden(es)"

    def _ejecutar_coach(self, p: dict) -> str:
        """Ejecuta de forma sincronizada Rostro + Voz Adaptativa + Proxémica + Postura G1."""
        plan = p.get("plan_coach")
        estado = p.get("estado_afectivo")
        if plan is None:
            return "sin plan de coaching generado"

        prosodia = plan.prosodia
        resumen_usr = f"Emoción: {plan.emocion_usuario}"
        if estado is not None:
            partes_canal = [f"V:{estado.valencia:+.2f} A:{estado.arousal:+.2f}"]
            if estado.facial.rostro_detectado:
                partes_canal.append(f"Cara:{estado.facial.emocion_facial}")
            if estado.acustica.audio_analizado:
                partes_canal.append(
                    f"Voz:{estado.acustica.tono_f0_hz:.0f}Hz/{estado.acustica.rapidez_wpm:.0f}ppm/{estado.acustica.volumen_db:.0f}dB"
                )
            resumen_usr = " | ".join(partes_canal)

        resumen_voz_robot = (
            f"Voz Ottoman -> {prosodia.velocidad_wpm} ppm ({prosodia.velocidad_pct:+d}%) | "
            f"{prosodia.volumen_db:+.1f} dB | {prosodia.tono_hz:+d} Hz | "
            f"Pausa: {prosodia.pausa_entre_frases_s:.2f}s"
        )

        # 1. Actualizar Rostro Animado y Dashboard (Cámara FACS + Plano Russell V-A)
        if self.rostro is not None:
            self.rostro.actualizar_estado(
                emocion=plan.preset_rostro,
                subtitulo=plan.texto_respuesta,
                resumen_usuario=resumen_usr,
                resumen_prosodia=resumen_voz_robot,
                valencia=estado.valencia if estado is not None else None,
                arousal=estado.arousal if estado is not None else None,
                incongruencia=estado.incongruencia_detectada if estado is not None else False,
                canales=estado.canales_activos if estado is not None else None,
                metricas_faciales=estado.facial if estado is not None else None,
            )

        self._log(f"Estrategia HRI : {plan.estrategia_hri} [{plan.origen_respuesta}]")
        self._log(f"Modulación Voz : {resumen_voz_robot}")
        self._log(f"Respuesta Coach: \"{plan.texto_respuesta}\"")

        # 2. Lanzar Voz Prosódica en hilo paralelo para sincronizar con el cuerpo
        hilo_voz = None
        if self.sintetizador_voz is not None:
            hilo_voz = self.sintetizador_voz.hablar_sincronizado(
                texto=plan.texto_respuesta,
                prosodia=prosodia,
                rostro=self.rostro,
                bloqueante=False,
            )

        # 3. Ejecutar ajuste proxémico suave (acercarse en tristeza / dar espacio en enojo)
        if abs(plan.proxemica_distancia_m) > 0.01 and plan.proxemica_velocidad_ms > 0:
            vel_segura = min(plan.proxemica_velocidad_ms, self.perfil.velocidad_max)
            signo = 1.0 if plan.proxemica_distancia_m > 0 else -1.0
            dur_prox = min(abs(plan.proxemica_distancia_m) / vel_segura, self.perfil.duracion_max)
            accion_prox = "acercamiento empático" if signo > 0 else "espacio de desescalada"
            self._log(f"Proxémica G1   : {accion_prox} ({plan.proxemica_distancia_m:+.2f} m a {vel_segura:.2f} m/s)")
            self.robot.avanzar(velocidad=signo * vel_segura, tiempo=dur_prox)

        # 4. Ejecutar secuencia cinemática de torso, brazos y dedos Inspire
        ejecutar_poses = getattr(self.robot, "ejecutar_secuencia_poses", None)
        if ejecutar_poses is not None and plan.secuencia_postural:
            self._log(
                f"Kinésica G1    : {len(plan.secuencia_postural)} keyframes articulares "
                f"(torso + brazos + manos, {plan.duracion_step_postura:.2f}s/paso)"
            )
            ejecutar_poses(plan.secuencia_postural, duracion_step=plan.duracion_step_postura)

        if hilo_voz is not None:
            hilo_voz.join(timeout=12.0)

        return (
            f"coach [{plan.emocion_usuario}]: voz={prosodia.velocidad_wpm}ppm/"
            f"{prosodia.volumen_db:+.1f}dB, poses={len(plan.secuencia_postural)}"
        )

    def _log(self, texto: str) -> None:
        if self.mostrar:
            print(f"      [EJECUTOR] {texto}")
