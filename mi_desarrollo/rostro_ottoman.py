"""Rostro Digital Animado para Humanizar a Ottoman (Unitree G1).

El Unitree G1 cuenta físicamente con un visor oscuro sin rasgos faciales móviles.
En Interacción Humano-Robot (HRI), dotar al agente de una interfaz facial expresiva
aumenta significativamente la confianza, la alianza terapéutica y la legibilidad
de sus intenciones afectivas (Breazeal, MIT Media Lab; principios human-ai.org).

Este módulo renderiza en tiempo real (~40 FPS en hilo dedicado no bloqueante):
  - Ojos expresivos con interpolación suave, pupilas dinámicas y parpadeo orgánico.
  - Cejas articuladas que reflejan empatía, calma, curiosidad o alegría.
  - Boca / Onda acústica sincronizada con la locución del robot (Lip-Sync).
  - Halo visual de co-regulación respiratoria ("Inhalá... Exhalá...") ante ansiedad.
  - Panel HUD inferior con la telemetría multimodal detectada en la persona.
"""

from __future__ import annotations

import math
import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class PresetFacialRobot:
    """Geometría y cromática objetivo del rostro de Ottoman para cada estado."""
    nombre: str
    color_rgb: tuple[int, int, int]
    apertura_ojo: float       # 0.20 (semicerrado calmo) .. 1.15 (abierto vivo)
    arco_feliz: float         # 0.0 (elipse normal) .. 1.0 (ojo sonriente ^ ^)
    angulo_ceja_izq: float    # grados (+ sube borde interno = empatía)
    angulo_ceja_der: float    # grados (- sube borde interno = empatía)
    altura_ceja: float        # offset vertical en px
    curvatura_boca: float     # -1.0 (seria) .. 0.0 (serena) .. +1.0 (sonrisa amplia)
    guia_respiracion: bool    # muestra halo rítmico de inhalar/exhalar
    intervalo_parpadeo: float # segundos promedio entre parpadeos


PRESETS_ROSTRO: dict[str, PresetFacialRobot] = {
    "NEUTRO": PresetFacialRobot(
        nombre="Escucha Atenta",
        color_rgb=(56, 189, 248),      # Cian suave
        apertura_ojo=0.90,
        arco_feliz=0.0,
        angulo_ceja_izq=2.0,
        angulo_ceja_der=-2.0,
        altura_ceja=0.0,
        curvatura_boca=0.22,
        guia_respiracion=False,
        intervalo_parpadeo=4.0,
    ),
    "ANSIEDAD_ESTRES": PresetFacialRobot(
        nombre="Co-regulación y Calma Respiratoria",
        color_rgb=(96, 165, 250),      # Azul sereno profundo
        apertura_ojo=0.68,
        arco_feliz=0.15,
        angulo_ceja_izq=8.0,
        angulo_ceja_der=-8.0,
        altura_ceja=-4.0,
        curvatura_boca=0.28,
        guia_respiracion=True,
        intervalo_parpadeo=5.2,
    ),
    "TRISTEZA_DESANIMO": PresetFacialRobot(
        nombre="Empatía Cálida y Contención",
        color_rgb=(251, 191, 36),      # Ámbar cálido
        apertura_ojo=0.82,
        arco_feliz=0.10,
        angulo_ceja_izq=16.0,          # Cejas inclinadas compasivas (/ \)
        angulo_ceja_der=-16.0,
        altura_ceja=-3.0,
        curvatura_boca=0.35,           # Sonrisa suave contenedora
        guia_respiracion=False,
        intervalo_parpadeo=4.5,
    ),
    "ENOJO_FRUSTRACION": PresetFacialRobot(
        nombre="Serenidad Ecuánime (Desescalada)",
        color_rgb=(52, 211, 153),      # Verde equilibrio
        apertura_ojo=0.88,
        arco_feliz=0.0,
        angulo_ceja_izq=4.0,
        angulo_ceja_der=-4.0,
        altura_ceja=2.0,
        curvatura_boca=0.12,           # Expresión pacífica no reactiva
        guia_respiracion=False,
        intervalo_parpadeo=4.2,
    ),
    "DUDA_INSEGURIDAD": PresetFacialRobot(
        nombre="Mentoría Estructurada",
        color_rgb=(34, 211, 238),      # Turquesa brillante
        apertura_ojo=0.98,
        arco_feliz=0.05,
        angulo_ceja_izq=10.0,          # Leve asimetría reflexiva/curiosa
        angulo_ceja_der=3.0,
        altura_ceja=-6.0,
        curvatura_boca=0.40,
        guia_respiracion=False,
        intervalo_parpadeo=3.8,
    ),
    "MOTIVACION_ALEGRIA": PresetFacialRobot(
        nombre="Celebración y Entusiasmo",
        color_rgb=(250, 204, 21),      # Dorado energético
        apertura_ojo=1.05,
        arco_feliz=0.85,               # Ojos felices arqueados (^ ^)
        angulo_ceja_izq=-6.0,
        angulo_ceja_der=6.0,
        altura_ceja=-10.0,
        curvatura_boca=0.90,           # Sonrisa amplia
        guia_respiracion=False,
        intervalo_parpadeo=3.2,
    ),
    "CRISIS_RIESGO": PresetFacialRobot(
        nombre="Protocolo de Contención Ética",
        color_rgb=(129, 140, 248),     # Índigo calmo
        apertura_ojo=0.85,
        arco_feliz=0.0,
        angulo_ceja_izq=12.0,
        angulo_ceja_der=-12.0,
        altura_ceja=-2.0,
        curvatura_boca=0.15,
        guia_respiracion=True,
        intervalo_parpadeo=4.8,
    ),
}


def _rgb_hex(rgb: tuple[float, float, float]) -> str:
    r = int(max(0, min(255, round(rgb[0]))))
    g = int(max(0, min(255, round(rgb[1]))))
    b = int(max(0, min(255, round(rgb[2]))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class RostroOttoman:
    """Ventana interactiva del rostro de Ottoman ejecutable en segundo plano."""

    def __init__(self, habilitado: bool = True, titulo: str = "Ottoman G1 — Rostro Afectivo Multimodal"):
        self.habilitado = habilitado
        self.titulo = titulo
        self._cola: queue.Queue[dict] = queue.Queue()
        self._hilo: Optional[threading.Thread] = None
        self._activo = False

        # Estado lógico consultable por tests incluso en modo headless
        self.emocion_actual: str = "NEUTRO"
        self.hablando: bool = False
        self.subtitulo_actual: str = "Listo para escucharte."
        self.resumen_usuario: str = "Sensores listos (Cara + Voz + Léxico)"
        self.resumen_prosodia: str = "Voz Robot: 0% vel | 0 dB | 0 Hz"

    def iniciar(self) -> bool:
        """Levanta la ventana gráfica en un hilo separado si Tkinter está disponible."""
        if not self.habilitado:
            return False
        if self._activo:
            return True

        listo = threading.Event()
        exito = [False]

        def _worker():
            try:
                import tkinter as tk
                root = tk.Tk()
                root.title(self.titulo)
                root.geometry("680x500")
                root.configure(bg="#070B14")
                root.resizable(False, False)
                exito[0] = True
                self._activo = True
                listo.set()
                self._bucle_render(root, tk)
            except Exception:
                self._activo = False
                listo.set()

        self._hilo = threading.Thread(target=_worker, daemon=True)
        self._hilo.start()
        listo.wait(timeout=2.5)
        return exito[0]

    def cerrar(self) -> None:
        self._activo = False
        self._cola.put({"cmd": "cerrar"})

    def actualizar_estado(
        self,
        emocion: str,
        subtitulo: str = "",
        resumen_usuario: str = "",
        resumen_prosodia: str = "",
        hablando: Optional[bool] = None,
    ) -> PresetFacialRobot:
        """Actualiza la expresión facial, subtítulos y telemetría mostrados."""
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

    def set_hablando(self, hablando: bool, subtitulo: str = "") -> None:
        self.hablando = hablando
        if subtitulo:
            self.subtitulo_actual = subtitulo
        if self._activo:
            self._cola.put({
                "cmd": "habla",
                "hablando": hablando,
                "subtitulo": self.subtitulo_actual,
            })

    # -----------------------------------------------------------------
    #  Renderizado vectorial a ~40 FPS en Tkinter Canvas
    # -----------------------------------------------------------------
    def _bucle_render(self, root, tk) -> None:
        canvas = tk.Canvas(root, width=680, height=500, bg="#070B14", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        preset_obj = PRESETS_ROSTRO["NEUTRO"]
        color_act = list(preset_obj.color_rgb)
        apertura_act = preset_obj.apertura_ojo
        arco_act = preset_obj.arco_feliz
        ceja_izq_act = preset_obj.angulo_ceja_izq
        ceja_der_act = preset_obj.angulo_ceja_der
        alt_ceja_act = preset_obj.altura_ceja
        boca_act = preset_obj.curvatura_boca

        t_proximo_parpadeo = time.monotonic() + 3.0
        parpadeo_hasta = 0.0

        def _al_cerrar():
            self._activo = False
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", _al_cerrar)

        def _tick():
            nonlocal preset_obj, color_act, apertura_act, arco_act
            nonlocal ceja_izq_act, ceja_der_act, alt_ceja_act, boca_act
            nonlocal t_proximo_parpadeo, parpadeo_hasta

            if not self._activo:
                try:
                    root.destroy()
                except Exception:
                    pass
                return

            while not self._cola.empty():
                msg = self._cola.get_nowait()
                if msg.get("cmd") == "cerrar":
                    _al_cerrar()
                    return
                if "emocion" in msg:
                    preset_obj = PRESETS_ROSTRO.get(msg["emocion"], PRESETS_ROSTRO["NEUTRO"])

            ahora = time.monotonic()
            # Interpolación suave (suavizado exponencial)
            vel_interp = 0.14
            for i in range(3):
                color_act[i] = _lerp(color_act[i], preset_obj.color_rgb[i], vel_interp)
            apertura_act = _lerp(apertura_act, preset_obj.apertura_ojo, vel_interp)
            arco_act = _lerp(arco_act, preset_obj.arco_feliz, vel_interp)
            ceja_izq_act = _lerp(ceja_izq_act, preset_obj.angulo_ceja_izq, vel_interp)
            ceja_der_act = _lerp(ceja_der_act, preset_obj.angulo_ceja_der, vel_interp)
            alt_ceja_act = _lerp(alt_ceja_act, preset_obj.altura_ceja, vel_interp)
            boca_act = _lerp(boca_act, preset_obj.curvatura_boca, vel_interp)

            # Parpadeo orgánico
            if ahora >= t_proximo_parpadeo:
                parpadeo_hasta = ahora + 0.14
                t_proximo_parpadeo = ahora + preset_obj.intervalo_parpadeo * random.uniform(0.75, 1.25)

            factor_parpadeo = 0.08 if ahora < parpadeo_hasta else 1.0

            col_principal = _rgb_hex((color_act[0], color_act[1], color_act[2]))
            col_tenue = _rgb_hex((color_act[0] * 0.25, color_act[1] * 0.25, color_act[2] * 0.25))

            canvas.delete("all")

            # Marco del visor estilo casco Unitree G1
            canvas.create_rectangle(30, 22, 650, 365, fill="#0D1322", outline=col_tenue, width=3)
            canvas.create_text(
                340, 44,
                text=f"OTTOMAN G1  •  MODO: {preset_obj.nombre.upper()}",
                fill=col_principal,
                font=("Segoe UI", 10, "bold"),
            )

            # Guía visual de respiración (ciclo de 8 segundos: 4s inhala, 4s exhala)
            if preset_obj.guia_respiracion:
                fase_resp = 0.5 * (1.0 - math.cos(2.0 * math.pi * (ahora % 8.0) / 8.0))
                radio_halo = 115 + 32 * fase_resp
                canvas.create_oval(
                    340 - radio_halo, 190 - radio_halo * 0.65,
                    340 + radio_halo, 190 + radio_halo * 0.65,
                    outline=col_tenue, width=3, dash=(6, 4)
                )
                texto_resp = "INHALÁ SUAVE..." if (ahora % 8.0) < 4.0 else "EXHALÁ LENTO..."
                canvas.create_text(
                    340, 342, text=texto_resp, fill=col_principal, font=("Segoe UI", 10, "italic")
                )

            # Micro-movimiento de mirada viva
            mirada_x = 4.0 * math.sin(ahora * 0.9)
            mirada_y = 2.5 * math.cos(ahora * 0.7)

            # Dibujar Ojos y Cejas (Izquierdo y Derecho)
            for cx_ojo, ang_ceja in ((225, ceja_izq_act), (455, ceja_der_act)):
                cy_ojo = 165
                rx = 46
                ry = max(4.0, 38.0 * apertura_act * factor_parpadeo)

                # Ojo luminoso
                if arco_act > 0.45 and factor_parpadeo > 0.5:
                    # Ojos sonrientes arqueados (^ ^)
                    canvas.create_arc(
                        cx_ojo - rx, cy_ojo - ry, cx_ojo + rx, cy_ojo + ry,
                        start=15, extent=150, style="arc", outline=col_principal, width=9
                    )
                else:
                    canvas.create_oval(
                        cx_ojo - rx, cy_ojo - ry, cx_ojo + rx, cy_ojo + ry,
                        fill=col_principal, outline=""
                    )
                    # Pupila / reflejo interior para calidez humana
                    if ry > 12:
                        canvas.create_oval(
                            cx_ojo - 14 + mirada_x, cy_ojo - 14 + mirada_y,
                            cx_ojo + 14 + mirada_x, cy_ojo + 14 + mirada_y,
                            fill="#0D1322", outline=""
                        )
                        canvas.create_oval(
                            cx_ojo - 20 + mirada_x, cy_ojo - 18 + mirada_y,
                            cx_ojo - 8 + mirada_x, cy_ojo - 6 + mirada_y,
                            fill="#FFFFFF", outline=""
                        )

                # Ceja articulada
                rad = math.radians(ang_ceja)
                largo_ceja = 52
                dx = largo_ceja * math.cos(rad)
                dy = largo_ceja * math.sin(rad)
                y_ceja = cy_ojo - 58 + alt_ceja_act
                canvas.create_line(
                    cx_ojo - dx, y_ceja + dy,
                    cx_ojo + dx, y_ceja - dy,
                    fill=col_principal, width=7, capstyle="round"
                )

            # Dibujar Boca / Onda de Voz Sincronizada (Lip-Sync)
            cy_boca = 278
            if self.hablando:
                # Barras de onda armónica moduladas + contorno bucal vivo
                n_barras = 15
                ancho_total = 170
                x0 = 340 - ancho_total // 2
                for b in range(n_barras):
                    envolvente = math.sin(math.pi * (b + 0.5) / n_barras)
                    amp = (6.0 + 22.0 * abs(math.sin(ahora * 13.0 + b * 0.7))) * envolvente
                    xb = x0 + b * (ancho_total / (n_barras - 1))
                    canvas.create_line(
                        xb, cy_boca - amp, xb, cy_boca + amp,
                        fill=col_principal, width=5, capstyle="round"
                    )
            else:
                # Curva bezier suave de sonrisa / serenidad
                despl_curva = 26.0 * boca_act
                puntos = [
                    275, cy_boca - despl_curva * 0.35,
                    340, cy_boca + despl_curva,
                    405, cy_boca - despl_curva * 0.35,
                ]
                canvas.create_line(
                    *puntos, smooth=True, fill=col_principal, width=7, capstyle="round"
                )

            # Panel HUD inferior: Subtítulo + Telemetría Multimodal
            canvas.create_rectangle(30, 378, 650, 484, fill="#111827", outline="#1F2937", width=2)
            sub_mostrar = (
                self.subtitulo_actual[:86] + "..."
                if len(self.subtitulo_actual) > 89
                else self.subtitulo_actual
            )
            canvas.create_text(
                340, 402,
                text=f"\"{sub_mostrar}\"",
                fill="#F9FAFB",
                font=("Segoe UI", 10, "bold"),
            )
            canvas.create_text(
                340, 434,
                text=self.resumen_usuario,
                fill="#93C5FD",
                font=("Consolas", 9),
            )
            canvas.create_text(
                340, 460,
                text=self.resumen_prosodia,
                fill="#A7F3D0",
                font=("Consolas", 9),
            )

            root.after(25, _tick)

        _tick()
        root.mainloop()
