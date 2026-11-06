"""Rostro Digital Animado y Modo Dashboard de Exposición para Ottoman (Unitree G1).

El Unitree G1 cuenta físicamente con un visor oscuro sin rasgos faciales móviles.
En Interacción Humano-Robot (HRI), dotar al agente de una interfaz facial expresiva
aumenta significativamente la confianza, la alianza terapéutica y la legibilidad
de sus intenciones afectivas (Breazeal, MIT Media Lab; principios human-ai.org).

Modos soportados (~40 FPS en hilo dedicado no bloqueante):
  1. Modo Visor Compacto (680x500): Rostro animado + subtítulos + telemetría.
  2. Modo Dashboard de Exposición (1240x700, --dashboard):
     - Panel Izquierdo: Rostro Animado de Ottoman (ojos, cejas, Lip-Sync, halo
       respiratorio e indicador de incongruencia afectiva).
     - Panel Superior Derecho: Cámara en vivo con detección facial OpenCV FACS
       (y radar biométrico FACS interactivo cuando se opera sin webcam física).
     - Panel Inferior Derecho: Plano Cartesiano Valencia-Arousal (Modelo
       Circumplejo de Russell) en tiempo real con trayectoria histórica de los
       últimos turnos emocionales.
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
    """Interfaz visual del rostro de Ottoman y Dashboard Multimodal en tiempo real."""

    def __init__(
        self,
        habilitado: bool = True,
        modo_dashboard: bool = False,
        captura_camara_autonoma: bool = False,
        titulo: str = "Ottoman G1 — Interfaz Afectiva Multimodal",
    ):
        self.habilitado = habilitado
        self.modo_dashboard = modo_dashboard
        self.captura_camara_autonoma = captura_camara_autonoma
        self.titulo = (
            "Ottoman G1 — Dashboard de Exposición Multimodal (Rostro + Cámara FACS + Russell V-A)"
            if modo_dashboard
            else titulo
        )
        self._cola: queue.Queue[dict] = queue.Queue()
        self._hilo: Optional[threading.Thread] = None
        self._activo = False

        # Estado lógico consultable por tests incluso en modo headless
        self.emocion_actual: str = "NEUTRO"
        self.hablando: bool = False
        self.subtitulo_actual: str = "Listo para escucharte."
        self.resumen_usuario: str = "Sensores listos (Cara + Voz + Léxico)"
        self.resumen_prosodia: str = "Voz Robot: 145 ppm (0%) | +0.0 dB | +0 Hz"

        # Telemetría en tiempo real para el Modo Dashboard
        self.valencia_actual: float = 0.0
        self.arousal_actual: float = 0.0
        self.incongruencia_activa: bool = False
        self.canales_activos: list[str] = ["lexico"]
        self.historial_va: deque[tuple[float, float, str]] = deque(maxlen=8)
        self.metricas_faciales_dict: dict = {
            "rostro_detectado": False,
            "apertura_ojos": 0.50,
            "tension_cejas": 0.20,
            "curvatura_boca": 0.05,
            "apertura_boca": 0.12,
            "inclinacion_cabeza_deg": 0.0,
            "emocion_facial": "NEUTRO",
        }
        self._ultimo_frame_rgb: Optional[np.ndarray] = None
        self._lock_frame = threading.Lock()

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
                geom = "1240x700" if self.modo_dashboard else "680x500"
                root.geometry(geom)
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
            self.historial_va.append((self.valencia_actual, self.arousal_actual, clave))
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
        """Envía un frame BGR ya anotado por OpenCV al panel de cámara del Dashboard."""
        if metricas_faciales is not None:
            self._guardar_metricas_faciales(metricas_faciales)
        if frame_bgr is not None and frame_bgr.size > 0:
            try:
                import cv2
                frame_peq = cv2.resize(frame_bgr, (336, 232))
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
        ancho_w = 1240 if self.modo_dashboard else 680
        alto_w = 700 if self.modo_dashboard else 500
        canvas = tk.Canvas(root, width=ancho_w, height=alto_w, bg="#070B14", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Hilo opcional de cámara en vivo cuando se abre Dashboard con webcam
        hilo_cam = None
        detener_cam = threading.Event()
        if self.modo_dashboard and self.captura_camara_autonoma:
            def _cam_worker():
                try:
                    from percepcion_multimodal import AnalizadorFacial
                    af = AnalizadorFacial()
                    if not af.abrir_camara():
                        return
                    while not detener_cam.is_set() and self._activo:
                        ok, frame = af._cap.read()
                        if ok and frame is not None:
                            m, hud = af.analizar_frame(frame, dibujar_hud=True)
                            self.actualizar_camara(hud, m)
                        time.sleep(0.065)
                    af.cerrar_camara()
                except Exception:
                    pass

            hilo_cam = threading.Thread(target=_cam_worker, daemon=True)
            hilo_cam.start()

        preset_obj = PRESETS_ROSTRO["NEUTRO"]
        color_act = list(preset_obj.color_rgb)
        apertura_act = preset_obj.apertura_ojo
        arco_act = preset_obj.arco_feliz
        ceja_izq_act = preset_obj.angulo_ceja_izq
        ceja_der_act = preset_obj.angulo_ceja_der
        alt_ceja_act = preset_obj.altura_ceja
        boca_act = preset_obj.curvatura_boca
        val_interp = 0.0
        aro_interp = 0.0

        photo_ref = [None]
        t_proximo_parpadeo = time.monotonic() + 3.0
        parpadeo_hasta = 0.0

        def _al_cerrar():
            self._activo = False
            detener_cam.set()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", _al_cerrar)

        def _tick():
            nonlocal preset_obj, color_act, apertura_act, arco_act
            nonlocal ceja_izq_act, ceja_der_act, alt_ceja_act, boca_act
            nonlocal val_interp, aro_interp, t_proximo_parpadeo, parpadeo_hasta

            if not self._activo:
                detener_cam.set()
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
            vel_interp = 0.14
            for i in range(3):
                color_act[i] = _lerp(color_act[i], preset_obj.color_rgb[i], vel_interp)
            apertura_act = _lerp(apertura_act, preset_obj.apertura_ojo, vel_interp)
            arco_act = _lerp(arco_act, preset_obj.arco_feliz, vel_interp)
            ceja_izq_act = _lerp(ceja_izq_act, preset_obj.angulo_ceja_izq, vel_interp)
            ceja_der_act = _lerp(ceja_der_act, preset_obj.angulo_ceja_der, vel_interp)
            alt_ceja_act = _lerp(alt_ceja_act, preset_obj.altura_ceja, vel_interp)
            boca_act = _lerp(boca_act, preset_obj.curvatura_boca, vel_interp)
            val_interp = _lerp(val_interp, self.valencia_actual, 0.16)
            aro_interp = _lerp(aro_interp, self.arousal_actual, 0.16)

            if ahora >= t_proximo_parpadeo:
                parpadeo_hasta = ahora + 0.14
                t_proximo_parpadeo = ahora + preset_obj.intervalo_parpadeo * random.uniform(0.75, 1.25)

            factor_parpadeo = 0.08 if ahora < parpadeo_hasta else 1.0
            col_principal = _rgb_hex((color_act[0], color_act[1], color_act[2]))
            col_tenue = _rgb_hex((color_act[0] * 0.25, color_act[1] * 0.25, color_act[2] * 0.25))

            canvas.delete("all")

            # Coordenadas adaptadas según sea ventana simple o Dashboard completo
            y_visor_fin = 505 if self.modo_dashboard else 365
            cy_ojo = 235 if self.modo_dashboard else 165
            cy_boca = 370 if self.modo_dashboard else 278
            y_hud_ini = 520 if self.modo_dashboard else 378
            y_hud_fin = 678 if self.modo_dashboard else 484

            # 1. PANEL VISOR ROSTRO OTTOMAN G1
            canvas.create_rectangle(24, 20, 656, y_visor_fin, fill="#0D1322", outline=col_tenue, width=3)
            canvas.create_text(
                340, 44,
                text=f"OTTOMAN G1  •  MODO: {preset_obj.nombre.upper()}",
                fill=col_principal,
                font=("Segoe UI", 10, "bold"),
            )

            if self.incongruencia_activa:
                canvas.create_rectangle(170, 62, 510, 86, fill="#451A03", outline="#F59E0B", width=1)
                canvas.create_text(
                    340, 74,
                    text="⚠ ENMASCARAMIENTO AFECTIVO DETECTADO (BIOMETRÍA ≠ TEXTO)",
                    fill="#FCD34D",
                    font=("Segoe UI", 8, "bold"),
                )

            if preset_obj.guia_respiracion:
                fase_resp = 0.5 * (1.0 - math.cos(2.0 * math.pi * (ahora % 8.0) / 8.0))
                radio_halo = 122 + 34 * fase_resp
                canvas.create_oval(
                    340 - radio_halo, (cy_ojo + 45) - radio_halo * 0.65,
                    340 + radio_halo, (cy_ojo + 45) + radio_halo * 0.65,
                    outline=col_tenue, width=3, dash=(6, 4)
                )
                texto_resp = "INHALÁ SUAVE (4s)..." if (ahora % 8.0) < 4.0 else "EXHALÁ LENTO (4s)..."
                canvas.create_text(
                    340, y_visor_fin - 24,
                    text=texto_resp, fill=col_principal, font=("Segoe UI", 10, "italic")
                )

            mirada_x = 4.0 * math.sin(ahora * 0.9)
            mirada_y = 2.5 * math.cos(ahora * 0.7)

            for cx_ojo, ang_ceja in ((225, ceja_izq_act), (455, ceja_der_act)):
                rx = 48 if self.modo_dashboard else 46
                ry = max(4.0, (42.0 if self.modo_dashboard else 38.0) * apertura_act * factor_parpadeo)

                if arco_act > 0.45 and factor_parpadeo > 0.5:
                    canvas.create_arc(
                        cx_ojo - rx, cy_ojo - ry, cx_ojo + rx, cy_ojo + ry,
                        start=15, extent=150, style="arc", outline=col_principal, width=9
                    )
                else:
                    canvas.create_oval(
                        cx_ojo - rx, cy_ojo - ry, cx_ojo + rx, cy_ojo + ry,
                        fill=col_principal, outline=""
                    )
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

                rad = math.radians(ang_ceja)
                largo_ceja = 54
                dx = largo_ceja * math.cos(rad)
                dy = largo_ceja * math.sin(rad)
                y_ceja = cy_ojo - 62 + alt_ceja_act
                canvas.create_line(
                    cx_ojo - dx, y_ceja + dy,
                    cx_ojo + dx, y_ceja - dy,
                    fill=col_principal, width=7, capstyle="round"
                )

            if self.hablando:
                n_barras = 17
                ancho_total = 190
                x0 = 340 - ancho_total // 2
                for b in range(n_barras):
                    envolvente = math.sin(math.pi * (b + 0.5) / n_barras)
                    amp = (6.0 + 25.0 * abs(math.sin(ahora * 13.0 + b * 0.7))) * envolvente
                    xb = x0 + b * (ancho_total / (n_barras - 1))
                    canvas.create_line(
                        xb, cy_boca - amp, xb, cy_boca + amp,
                        fill=col_principal, width=5, capstyle="round"
                    )
            else:
                despl_curva = 28.0 * boca_act
                puntos = [
                    270, cy_boca - despl_curva * 0.35,
                    340, cy_boca + despl_curva,
                    410, cy_boca - despl_curva * 0.35,
                ]
                canvas.create_line(
                    *puntos, smooth=True, fill=col_principal, width=7, capstyle="round"
                )

            # Consola inferior de subtítulos y telemetría
            canvas.create_rectangle(24, y_hud_ini, 656, y_hud_fin, fill="#111827", outline="#1F2937", width=2)
            sub_mostrar = (
                self.subtitulo_actual[:86] + "..."
                if len(self.subtitulo_actual) > 89
                else self.subtitulo_actual
            )
            canvas.create_text(
                340, y_hud_ini + 28,
                text=f"\"{sub_mostrar}\"",
                fill="#F9FAFB",
                font=("Segoe UI", 10, "bold"),
                width=600,
            )
            canvas.create_text(
                340, y_hud_fin - 48,
                text=self.resumen_usuario,
                fill="#93C5FD",
                font=("Consolas", 9),
            )
            canvas.create_text(
                340, y_hud_fin - 22,
                text=self.resumen_prosodia,
                fill="#A7F3D0",
                font=("Consolas", 9),
            )

            # 2. PANELES ADICIONALES EN MODO DASHBOARD DE EXPOSICIÓN (1240x700)
            if self.modo_dashboard:
                self._dibujar_panel_camara(canvas, photo_ref, ahora, col_principal)
                self._dibujar_panel_russell(canvas, val_interp, aro_interp, ahora, col_principal)

            root.after(25, _tick)

        _tick()
        root.mainloop()

    def _dibujar_panel_camara(self, canvas, photo_ref: list, ahora: float, col_principal: str) -> None:
        """Renderiza cámara OpenCV en vivo o malla biométrica FACS + barras AU."""
        x1, y1, x2, y2 = 676, 20, 1216, 338
        canvas.create_rectangle(x1, y1, x2, y2, fill="#0D1322", outline="#1E293B", width=2)
        canvas.create_text(
            x1 + 16, y1 + 20,
            text="VISIÓN POR COMPUTADORA — DETECCIÓN FACIAL FACS (OpenCV)",
            anchor="w",
            fill="#38BDF8",
            font=("Segoe UI", 9, "bold"),
        )

        # Área de video (336x232) a la izquierda del panel derecho
        vx1, vy1 = x1 + 16, y1 + 42
        vx2, vy2 = vx1 + 336, vy1 + 232
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
            except Exception:
                frame_copia = None

        if frame_copia is None:
            # Malla biométrica FACS interactiva en vivo cuando se corre demo o sin webcam física
            cx, cy = (vx1 + vx2) // 2, (vy1 + vy2) // 2 + 4
            # Retícula HUD de escaneo facial
            canvas.create_rectangle(cx - 72, cy - 84, cx + 72, cy + 84, outline="#0EA5E9", width=1, dash=(4, 3))
            # Contorno craneal estilizado
            canvas.create_oval(cx - 58, cy - 72, cx + 58, cy + 72, outline="#38BDF8", width=2)
            ap_o = float(mf.get("apertura_ojos", 0.5))
            ten_c = float(mf.get("tension_cejas", 0.2))
            cur_b = float(mf.get("curvatura_boca", 0.05))
            emo_f = str(mf.get("emocion_facial", "NEUTRO"))

            for sig, ox in ((-1, cx - 23), (1, cx + 23)):
                ry_o = max(3.0, 11.0 * ap_o)
                canvas.create_oval(ox - 13, cy - 16 - ry_o, ox + 13, cy - 16 + ry_o, outline="#7DD3FC", width=2)
                canvas.create_oval(ox - 3, cy - 19, ox + 3, cy - 13, fill="#38BDF8", outline="")
                inclin = -10.0 * ten_c * sig
                canvas.create_line(
                    ox - 15, cy - 34 - inclin, ox + 15, cy - 34 + inclin,
                    fill="#FCD34D" if ten_c > 0.55 else "#38BDF8", width=3, capstyle="round"
                )
            desp_b = 16.0 * cur_b
            canvas.create_line(
                cx - 24, cy + 32 - desp_b * 0.3,
                cx, cy + 32 + desp_b,
                cx + 24, cy + 32 - desp_b * 0.3,
                smooth=True, fill="#34D399" if cur_b >= 0 else "#F87171", width=3, capstyle="round"
            )
            estado_cam = "RADAR FACS SIMULADO ACTIVO" if mf.get("rostro_detectado") else "ESPERANDO ROSTRO / WEBCAM"
            canvas.create_text(
                cx, vy2 - 14,
                text=f"{estado_cam} • [{emo_f}]",
                fill="#94A3B8",
                font=("Consolas", 8),
            )

        # Indicadores de Unidades de Acción Facial (FACS Gauges) a la derecha del video
        gx = vx2 + 16
        metricas_barras = [
            ("AU1/5 Apertura Ojos", float(mf.get("apertura_ojos", 0.5)), "#38BDF8"),
            ("AU4 Tensión Cejas", float(mf.get("tension_cejas", 0.2)), "#F59E0B"),
            ("AU12 Sonrisa / Boca", (float(mf.get("curvatura_boca", 0.0)) + 1.0) * 0.5, "#10B981"),
            ("AU25 Apertura Bucal", float(mf.get("apertura_boca", 0.12)), "#A78BFA"),
        ]
        for idx_b, (etq, valor_norm, col_b) in enumerate(metricas_barras):
            by = vy1 + 14 + idx_b * 52
            v_clip = max(0.0, min(1.0, valor_norm))
            canvas.create_text(gx, by, text=etq, anchor="w", fill="#CBD5E1", font=("Segoe UI", 8))
            canvas.create_rectangle(gx, by + 12, x2 - 16, by + 24, fill="#1E293B", outline="")
            ancho_max = (x2 - 16) - gx
            canvas.create_rectangle(gx, by + 12, gx + ancho_max * v_clip, by + 24, fill=col_b, outline="")

        # Badges de canales multimodales activos abajo del panel
        canales_str = " + ".join(c.upper() for c in self.canales_activos)
        canvas.create_text(
            x1 + 16, y2 - 20,
            text=f"Canales Fusionados (AG): [{canales_str}]",
            anchor="w",
            fill="#A7F3D0",
            font=("Consolas", 8, "bold"),
        )

    def _dibujar_panel_russell(
        self, canvas, valencia: float, arousal: float, ahora: float, col_principal: str
    ) -> None:
        """Dibuja el Plano Circumplejo Valencia-Arousal en tiempo real con trayectoria."""
        x1, y1, x2, y2 = 676, 354, 1216, 678
        canvas.create_rectangle(x1, y1, x2, y2, fill="#0D1322", outline="#1E293B", width=2)
        canvas.create_text(
            x1 + 16, y1 + 20,
            text="PLANO VALENCIA–AROUSAL EN TIEMPO REAL (MODELO DE RUSSELL)",
            anchor="w",
            fill="#A78BFA",
            font=("Segoe UI", 9, "bold"),
        )

        # Centro y radio del mapa cartesiano
        cx = x1 + 195
        cy = y1 + 174
        radio = 116

        # Círculos concéntricos de intensidad afectiva
        canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill="#080D1A", outline="#334155", width=2)
        r_med = radio * 0.55
        canvas.create_oval(cx - r_med, cy - r_med, cx + r_med, cy + r_med, outline="#1E293B", width=1, dash=(3, 3))

        # Ejes cartesianos X (Valencia) e Y (Arousal)
        canvas.create_line(cx - radio - 8, cy, cx + radio + 8, cy, fill="#475569", width=1)
        canvas.create_line(cx, cy - radio - 8, cx, cy + radio + 8, fill="#475569", width=1)

        # Etiquetas de los 4 cuadrantes afectivos
        canvas.create_text(cx - 56, cy - 64, text="ANSIEDAD /\nENOJO", fill="#FCA5A5", font=("Segoe UI", 7, "bold"), justify="center")
        canvas.create_text(cx + 56, cy - 64, text="MOTIVACIÓN /\nALEGRÍA", fill="#FDE047", font=("Segoe UI", 7, "bold"), justify="center")
        canvas.create_text(cx - 56, cy + 64, text="TRISTEZA /\nDESÁNIMO", fill="#93C5FD", font=("Segoe UI", 7, "bold"), justify="center")
        canvas.create_text(cx + 56, cy + 64, text="CALMA /\nSERENIDAD", fill="#6EE7B7", font=("Segoe UI", 7, "bold"), justify="center")

        canvas.create_text(cx + radio + 12, cy, text="+V", anchor="w", fill="#94A3B8", font=("Consolas", 8, "bold"))
        canvas.create_text(cx - radio - 12, cy, text="-V", anchor="e", fill="#94A3B8", font=("Consolas", 8, "bold"))
        canvas.create_text(cx, cy - radio - 12, text="+A", fill="#94A3B8", font=("Consolas", 8, "bold"))
        canvas.create_text(cx, cy + radio + 12, text="-A", fill="#94A3B8", font=("Consolas", 8, "bold"))

        # Dibujar trayectoria histórica de los últimos turnos
        hist = list(self.historial_va)
        if len(hist) >= 2:
            pts_hist = []
            for hv, ha, _ in hist:
                pts_hist.extend([cx + hv * radio, cy - ha * radio])
            canvas.create_line(*pts_hist, fill="#64748B", width=2, dash=(3, 2))
            for hv, ha, _ in hist[:-1]:
                px, py = cx + hv * radio, cy - ha * radio
                canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#94A3B8", outline="")

        # Punto actual interpolado con pulso radar
        px_act = cx + valencia * radio
        py_act = cy - arousal * radio
        pulso = 10.0 + 5.0 * abs(math.sin(ahora * 4.2))
        canvas.create_oval(
            px_act - pulso, py_act - pulso, px_act + pulso, py_act + pulso,
            outline=col_principal, width=2
        )
        canvas.create_oval(
            px_act - 6, py_act - 6, px_act + 6, py_act + 6,
            fill=col_principal, outline="#FFFFFF", width=1
        )

        # Columna derecha de telemetría numérica del plano V-A
        tx = cx + radio + 34
        intens = min(1.0, math.hypot(valencia, arousal) / math.sqrt(2.0))
        bloques = [
            ("ESTADO DOMINANTE", self.emocion_actual, col_principal),
            ("VALENCIA (Placer)", f"{valencia:+.2f}", "#F8FAFC"),
            ("AROUSAL (Activación)", f"{arousal:+.2f}", "#F8FAFC"),
            ("INTENSIDAD AFECTIVA", f"{intens*100:.0f}%", "#38BDF8"),
            ("TURNOS EN MEMORIA", f"{len(hist)} / 8", "#A7F3D0"),
        ]
        for idx_t, (titulo_b, val_b, col_b) in enumerate(bloques):
            by = y1 + 54 + idx_t * 48
            canvas.create_text(tx, by, text=titulo_b, anchor="w", fill="#94A3B8", font=("Segoe UI", 7, "bold"))
            canvas.create_text(tx, by + 17, text=val_b, anchor="w", fill=col_b, font=("Consolas", 10, "bold"))


def exportar_captura_dashboard_png(ruta_salida: Path) -> Path:
    """Genera un render estático de alta resolución del Modo Dashboard para el Informe y PPT."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12.4, 7.0), dpi=180, facecolor="#070B14")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#070B14")
    ax.set_xlim(0, 1240)
    ax.set_ylim(700, 0)  # Coordenadas de pantalla (origen arriba-izquierda)
    ax.axis("off")

    # 1. Marco Visor Izquierdo (Ottoman G1 en modo Co-Regulación Ansiedad)
    ax.add_patch(patches.FancyBboxPatch((24, 20), 632, 485, boxstyle="round,pad=0,rounding_size=8",
                                        facecolor="#0D1322", edgecolor="#1D4ED8", linewidth=2.5))
    ax.text(340, 46, "OTTOMAN G1  •  MODO: CO-REGULACIÓN Y CALMA RESPIRATORIA",
            color="#60A5FA", fontsize=10.5, fontweight="bold", ha="center", va="center")
    ax.add_patch(patches.Rectangle((150, 62), 380, 26, facecolor="#451A03", edgecolor="#F59E0B", linewidth=1.2))
    ax.text(340, 75, "ENMASCARAMIENTO DETECTADO: BIOMETRÍA ≠ TEXTO ('Estoy bien')",
            color="#FCD34D", fontsize=8, fontweight="bold", ha="center", va="center")

    # Halo respiratorio
    ax.add_patch(patches.Ellipse((340, 280), 300, 195, fill=False, edgecolor="#1E3A8A",
                                 linewidth=2.2, linestyle="--"))
    ax.text(340, 480, "INHALÁ SUAVE (4s)...  •  GUÍA DE CO-REGULACIÓN ACTIVA",
            color="#60A5FA", fontsize=9.2, style="italic", ha="center", va="center")

    # Ojos y cejas empáticas
    for cx_o, sig in ((225, 1), (455, -1)):
        ax.add_patch(patches.Ellipse((cx_o, 235), 96, 62, facecolor="#60A5FA", edgecolor="none"))
        ax.add_patch(patches.Circle((cx_o + 3, 235), 14, facecolor="#0D1322"))
        ax.add_patch(patches.Circle((cx_o - 12, 224), 6, facecolor="#FFFFFF"))
        ax.plot([cx_o - 52, cx_o + 52], [176 + 8 * sig, 176 - 8 * sig],
                color="#60A5FA", linewidth=6, solid_capstyle="round")

    # Onda Lip-Sync activa
    for b in range(17):
        env = math.sin(math.pi * (b + 0.5) / 17)
        amp = (7.0 + 22.0 * abs(math.sin(b * 0.85))) * env
        xb = 245 + b * (190 / 16)
        ax.plot([xb, xb], [372 - amp, 372 + amp], color="#60A5FA", linewidth=4, solid_capstyle="round")

    # Consola inferior izquierda
    ax.add_patch(patches.Rectangle((24, 520), 632, 158, facecolor="#111827", edgecolor="#1F2937", linewidth=2))
    ax.text(340, 556,
            "\"Tus palabras suenan tranquilas, pero percibo tensión en tu rostro y voz.\n"
            "Hagamos una pausa juntos: inhalá lento 4 segundos y bajemos un cambio.\"",
            color="#F9FAFB", fontsize=9.2, fontweight="bold", ha="center", va="center")
    ax.text(340, 620, "Usuario -> V:-0.56 A:+0.68 | Cara:ANSIEDAD_ESTRES | Voz:221Hz / 194ppm / -15dB",
            color="#93C5FD", fontsize=8.5, family="monospace", ha="center", va="center")
    ax.text(340, 650, "Voz Ottoman -> 118 ppm (-22%) | -4.5 dB | -18 Hz | Pausa: 0.90s",
            color="#A7F3D0", fontsize=8.5, family="monospace", ha="center", va="center")

    # 2. Panel Superior Derecho: Cámara OpenCV FACS
    ax.add_patch(patches.Rectangle((676, 20), 540, 318, facecolor="#0D1322", edgecolor="#1E293B", linewidth=2))
    ax.text(692, 42, "VISIÓN POR COMPUTADORA — DETECCIÓN FACIAL FACS (OpenCV)",
            color="#38BDF8", fontsize=9.2, fontweight="bold", ha="left", va="center")
    ax.add_patch(patches.Rectangle((692, 62), 336, 232, facecolor="#060911", edgecolor="#334155", linewidth=1.2))
    ax.add_patch(patches.Rectangle((788, 92), 144, 168, fill=False, edgecolor="#38BDF8", linewidth=1.5, linestyle="--"))
    ax.add_patch(patches.Ellipse((860, 176), 112, 140, fill=False, edgecolor="#38BDF8", linewidth=2))
    for ox, sig in ((837, -1), (883, 1)):
        ax.add_patch(patches.Ellipse((ox, 160), 26, 20, fill=False, edgecolor="#7DD3FC", linewidth=1.8))
        ax.add_patch(patches.Circle((ox, 160), 3.5, facecolor="#38BDF8"))
        ax.plot([ox - 14, ox + 14], [142 + 5 * sig, 142 - 5 * sig], color="#FCD34D", linewidth=2.6)
    ax.plot([838, 860, 882], [208, 216, 208], color="#F87171", linewidth=2.6)
    ax.text(860, 280, "FACS HUD ACTIVO • [ANSIEDAD_ESTRES]", color="#94A3B8",
            fontsize=7.8, family="monospace", ha="center", va="center")

    barras = [
        ("AU1/5 Apertura Ojos", 0.82, "#38BDF8"),
        ("AU4 Tensión Cejas", 0.64, "#F59E0B"),
        ("AU12 Curvatura Boca", 0.34, "#10B981"),
        ("AU25 Apertura Bucal", 0.28, "#A78BFA"),
    ]
    for idx_b, (lbl, v_b, col_b) in enumerate(barras):
        by = 76 + idx_b * 52
        ax.text(1044, by, lbl, color="#CBD5E1", fontsize=7.8, ha="left", va="center")
        ax.add_patch(patches.Rectangle((1044, by + 10), 156, 12, facecolor="#1E293B"))
        ax.add_patch(patches.Rectangle((1044, by + 10), 156 * v_b, 12, facecolor=col_b))
    ax.text(692, 318, "Canales Fusionados (AG): [LEXICO + VOZ + CARA]",
            color="#A7F3D0", fontsize=8.2, family="monospace", fontweight="bold", ha="left", va="center")

    # 3. Panel Inferior Derecho: Plano Valencia-Arousal de Russell
    ax.add_patch(patches.Rectangle((676, 354), 540, 324, facecolor="#0D1322", edgecolor="#1E293B", linewidth=2))
    ax.text(692, 376, "PLANO VALENCIA–AROUSAL EN TIEMPO REAL (MODELO DE RUSSELL)",
            color="#A78BFA", fontsize=9.2, fontweight="bold", ha="left", va="center")
    cx, cy, rad = 871, 528, 114
    ax.add_patch(patches.Circle((cx, cy), rad, facecolor="#080D1A", edgecolor="#334155", linewidth=2))
    ax.add_patch(patches.Circle((cx, cy), rad * 0.55, fill=False, edgecolor="#1E293B", linewidth=1, linestyle="--"))
    ax.plot([cx - rad - 8, cx + rad + 8], [cy, cy], color="#475569", linewidth=1)
    ax.plot([cx, cx], [cy - rad - 8, cy + rad + 8], color="#475569", linewidth=1)

    ax.text(cx - 55, cy - 60, "ANSIEDAD /\nENOJO", color="#FCA5A5", fontsize=7.5, fontweight="bold", ha="center", va="center")
    ax.text(cx + 55, cy - 60, "MOTIVACIÓN /\nALEGRÍA", color="#FDE047", fontsize=7.5, fontweight="bold", ha="center", va="center")
    ax.text(cx - 55, cy + 60, "TRISTEZA /\nDESÁNIMO", color="#93C5FD", fontsize=7.5, fontweight="bold", ha="center", va="center")
    ax.text(cx + 55, cy + 60, "CALMA /\nSERENIDAD", color="#6EE7B7", fontsize=7.5, fontweight="bold", ha="center", va="center")

    # Trayectoria histórica de 4 puntos previos hasta el estado actual (-0.56, +0.68)
    tray = [(0.10, 0.05), (-0.22, -0.35), (-0.42, 0.28), (-0.56, 0.68)]
    xs_t = [cx + v * rad for v, _ in tray]
    ys_t = [cy - a * rad for _, a in tray]
    ax.plot(xs_t, ys_t, color="#64748B", linewidth=2, linestyle="--")
    for px_i, py_i in zip(xs_t[:-1], ys_t[:-1]):
        ax.add_patch(patches.Circle((px_i, py_i), 4.5, facecolor="#94A3B8"))
    ax.add_patch(patches.Circle((xs_t[-1], ys_t[-1]), 14, fill=False, edgecolor="#60A5FA", linewidth=2))
    ax.add_patch(patches.Circle((xs_t[-1], ys_t[-1]), 6.5, facecolor="#60A5FA", edgecolor="#FFFFFF", linewidth=1.2))

    bloques_va = [
        ("ESTADO DOMINANTE", "ANSIEDAD_ESTRES", "#60A5FA"),
        ("VALENCIA (Placer)", "-0.56", "#F8FAFC"),
        ("AROUSAL (Activación)", "+0.68", "#F8FAFC"),
        ("INTENSIDAD AFECTIVA", "62%", "#38BDF8"),
        ("TURNOS EN MEMORIA", "4 / 8", "#A7F3D0"),
    ]
    for idx_v, (tit_v, val_v, col_v) in enumerate(bloques_va):
        by = 412 + idx_v * 48
        ax.text(1018, by, tit_v, color="#94A3B8", fontsize=7.5, fontweight="bold", ha="left", va="center")
        ax.text(1018, by + 17, val_v, color=col_v, fontsize=9.8, family="monospace", fontweight="bold", ha="left", va="center")

    fig.savefig(ruta_salida, dpi=180, facecolor="#070B14")
    plt.close(fig)
    return ruta_salida
