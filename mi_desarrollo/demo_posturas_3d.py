"""Demo Standalone: Simulación 3D de Posturas y Gesticulación del Humanoide Unitree G1.

Permite experimentar visualmente y en tiempo real:
  1. Postura Base Neutra vs Otras actitudes emocionales (Alegría, Tristeza, Ansiedad, Enojo).
  2. Idle Breathing: Respiración sutil diafragmática continua cuando el robot está en reposo.
  3. Co-Speech Gestures: Gesticulación coordinada con desfasaje Center-Out (torso precede a hombros y codos).
  4. Sliders continuos de Valencia y Arousal en tiempo real.
"""

from __future__ import annotations

import math
import sys
import time
import tkinter as tk
from pathlib import Path
from typing import Optional

import mujoco
from PIL import Image, ImageTk

# Importar lógica postural y afectiva del coach
_dir_actual = Path(__file__).resolve().parent
if str(_dir_actual) not in sys.path:
    sys.path.insert(0, str(_dir_actual))
from coach_emocional import CoreografoPosturalG1


class DemoPosturasG1:
    def __init__(self):
        self.ancho_render = 560
        self.alto_render = 450

        # Estado cinemático y afectivo
        self.emocion_actual = "NEUTRO"
        self.valencia = 0.0
        self.arousal = 0.0
        self.hablando = False
        self.multiplicador_energia = 1.0   # 0.5 (calmo) .. 1.0 (medio) .. 1.8 (vivo)

        # Cargar MuJoCo
        self._inicializar_simulador()

        # Construir Interfaz Gráfica Tkinter
        self.root = tk.Tk()
        self.root.title("Demo 3D — Posturas y Gesticulación Humanoide Unitree G1 (Laban / Lecoq / McNeill)")
        self.root.geometry("860x730")
        self.root.configure(bg="#070B14")
        self.root.resizable(False, False)

        self._construir_ui()
        self._ultimo_tiempo = time.monotonic()
        self._fase_gesto = 0.0
        self._photo_ref = [None]

    def _inicializar_simulador(self):
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
            raise FileNotFoundError("No se encontró scene_29dof.xml")

        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        self.model.opt.gravity[:] = 0.0
        self.data.qpos[2] = 0.793  # Altura de pie

        # Mapeo de articulaciones
        self.jmap = {}
        for i in range(self.model.njnt):
            nom = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, i)
            if nom:
                adr = int(self.model.jnt_qposadr[i])
                self.jmap[nom] = adr
                if nom.endswith("_joint"):
                    self.jmap[nom[:-6]] = adr

        # Renderer offscreen en el hilo principal
        self.renderer = mujoco.Renderer(self.model, self.alto_render, self.ancho_render)
        self.camera = mujoco.MjvCamera()
        self.camera.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.camera.lookat[:] = [0.0, 0.0, 0.75]
        self.camera.distance = 2.15
        self.camera.elevation = -10.0
        self.camera.azimuth = 162.0

    def _construir_ui(self):
        # Título superior
        lbl_titulo = tk.Label(
            self.root,
            text="UNITREE G1 — EXPRESIVIDAD CORPORAL COMPLETA Y GESTOS CO-VERBALES",
            bg="#070B14", fg="#38BDF8", font=("Segoe UI", 11, "bold"), pady=6
        )
        lbl_titulo.pack()

        # Canvas central para el visor 3D
        self.canvas = tk.Canvas(
            self.root, width=self.ancho_render, height=self.alto_render,
            bg="#060911", highlightbackground="#1E293B", highlightthickness=2
        )
        self.canvas.pack(pady=2)

        # Barra de telemetría en vivo
        self.lbl_telemetria = tk.Label(
            self.root,
            text="Modo: NEUTRO (V=+0.00, A=+0.00) | EN REPOSO (Idle Breathing 0.25 Hz)",
            bg="#0D1322", fg="#A7F3D0", font=("Consolas", 9, "bold"),
            padx=12, pady=4, relief="ridge"
        )
        self.lbl_telemetria.pack(fill="x", padx=40, pady=3)

        # Panel de controles interactivos
        frame_controles = tk.Frame(self.root, bg="#070B14", pady=2)
        frame_controles.pack()

        # Botón Toggle Hablando
        self.btn_hablar = tk.Button(
            frame_controles,
            text="🗣️ HABLANDO: NO (En Reposo)",
            bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 9, "bold"),
            padx=14, pady=4, relief="flat", cursor="hand2",
            command=self._toggle_hablando
        )
        self.btn_hablar.grid(row=0, column=0, padx=8, pady=2)

        # Selector de Velocidad / Energía
        frame_energia = tk.Frame(frame_controles, bg="#070B14")
        frame_energia.grid(row=0, column=1, padx=8, pady=2)
        tk.Label(frame_energia, text="Energía Gestual:", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        def _set_energia(val: float, nombre: str):
            self.multiplicador_energia = val
            self._actualizar_telemetria()

        tk.Button(frame_energia, text="Calmo (0.8 Hz)", bg="#1E293B", fg="#93C5FD", font=("Segoe UI", 8),
                  command=lambda: _set_energia(0.55, "Calmo")).pack(side="left", padx=2)
        tk.Button(frame_energia, text="Normal (1.6 Hz)", bg="#1E293B", fg="#A7F3D0", font=("Segoe UI", 8),
                  command=lambda: _set_energia(1.0, "Normal")).pack(side="left", padx=2)
        tk.Button(frame_energia, text="Enérgico (2.6 Hz)", bg="#1E293B", fg="#FDE047", font=("Segoe UI", 8),
                  command=lambda: _set_energia(1.65, "Enérgico")).pack(side="left", padx=2)

        # Fila de Sliders Continuos de Valencia y Arousal
        frame_sliders = tk.Frame(self.root, bg="#070B14", pady=2)
        frame_sliders.pack()

        tk.Label(frame_sliders, text="Valencia (Displacer ↔ Placer):", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8)).grid(row=0, column=0, padx=6)
        self.scale_valencia = tk.Scale(
            frame_sliders, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=180, bg="#0D1322", fg="#38BDF8", highlightthickness=0,
            command=lambda v: self._al_cambiar_slider()
        )
        self.scale_valencia.set(0.0)
        self.scale_valencia.grid(row=0, column=1, padx=6)

        tk.Label(frame_sliders, text="Arousal (Calma ↔ Activación):", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8)).grid(row=0, column=2, padx=6)
        self.scale_arousal = tk.Scale(
            frame_sliders, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=180, bg="#0D1322", fg="#FBBF24", highlightthickness=0,
            command=lambda v: self._al_cambiar_slider()
        )
        self.scale_arousal.set(0.0)
        self.scale_arousal.grid(row=0, column=3, padx=6)

        # Fila de Presets Emocionales
        frame_emociones = tk.Frame(self.root, bg="#070B14", pady=3)
        frame_emociones.pack()
        tk.Label(frame_emociones, text="Presets Emocionales:", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=6)

        emociones = [
            ("🔵 NEUTRO", "NEUTRO", 0.0, 0.0, "#38BDF8"),
            ("🟡 ALEGRÍA", "MOTIVACION_ALEGRIA", 0.70, 0.60, "#FBBF24"),
            ("🟠 TRISTEZA", "TRISTEZA_DESANIMO", -0.65, -0.45, "#93C5FD"),
            ("🟢 ANSIEDAD", "ANSIEDAD_ESTRES", -0.35, 0.65, "#6EE7B7"),
            ("🔴 ENOJO", "ENOJO_FRUSTRACION", -0.70, 0.75, "#F87171"),
        ]
        for txt_b, emo_clave, v_p, a_p, col_b in emociones:
            b = tk.Button(
                frame_emociones, text=txt_b, bg="#0F172A", fg=col_b,
                font=("Segoe UI", 8, "bold"), padx=9, pady=3, relief="flat", cursor="hand2",
                command=lambda e=emo_clave, v=v_p, a=a_p: self._set_emocion_preset(e, v, a)
            )
            b.pack(side="left", padx=3)

    def _toggle_hablando(self):
        self.hablando = not self.hablando
        if self.hablando:
            self.btn_hablar.config(
                text="🗣️ HABLANDO: SÍ (Co-speech Gestures)",
                bg="#0284C7", fg="#FFFFFF"
            )
        else:
            self.btn_hablar.config(
                text="🗣️ HABLANDO: NO (En Reposo)",
                bg="#1E293B", fg="#F8FAFC"
            )
        self._actualizar_telemetria()

    def _set_emocion_preset(self, emo: str, val: float, aro: float):
        self.emocion_actual = emo
        self.valencia = val
        self.arousal = aro
        self.scale_valencia.set(val)
        self.scale_arousal.set(aro)
        self._actualizar_telemetria()

    def _al_cambiar_slider(self):
        self.valencia = float(self.scale_valencia.get())
        self.arousal = float(self.scale_arousal.get())
        self._actualizar_telemetria()

    def _actualizar_telemetria(self):
        estado_h = "HABLANDO (Co-speech Gestures)" if self.hablando else "EN REPOSO (Idle Breathing)"
        freq = 0.25 if not self.hablando else ((1.4 + 0.8 * max(0.0, self.arousal)) * self.multiplicador_energia)
        self.lbl_telemetria.config(
            text=f"Modo: {self.emocion_actual} (V={self.valencia:+.2f}, A={self.arousal:+.2f}) | {estado_h} | Cadencia: {freq:.2f} Hz"
        )

    def loop(self):
        ahora = time.monotonic()
        dt = min(0.06, max(0.001, ahora - self._ultimo_tiempo))
        self._ultimo_tiempo = ahora

        # Avanzar fase gestual armónica
        if self.hablando:
            vel_onda = (3.0 + 1.2 * max(0.0, self.arousal)) * self.multiplicador_energia
            self._fase_gesto = (self._fase_gesto + dt * vel_onda) % (2.0 * math.pi)
            fase = self._fase_gesto
        else:
            fase = ahora * 1.57  # ~0.25 Hz respiración diafragmática

        # Calcular articulaciones continuas de cuerpo completo mediante CoreografoPosturalG1
        pose_continua = CoreografoPosturalG1.generar_postura_continua(
            valencia=self.valencia,
            arousal=self.arousal,
            fase_tiempo=fase,
            hablando=self.hablando,
            energia=self.multiplicador_energia,
        )

        # Aplicar al estado físico de MuJoCo
        for art, val in pose_continua.items():
            if art in self.jmap:
                self.data.qpos[self.jmap[art]] = val

        # Piernas en posición de pie firme
        for leg in ("left_hip_pitch", "right_hip_pitch", "left_knee", "right_knee"):
            if leg in self.jmap:
                self.data.qpos[self.jmap[leg]] = 0.0

        # Renderizar escena offscreen en el hilo principal
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, camera=self.camera)
        rgb = self.renderer.render()

        # Dibujar frame en Canvas
        img_pil = Image.fromarray(rgb)
        self._photo_ref[0] = ImageTk.PhotoImage(image=img_pil)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo_ref[0])

        self.root.after(30, self.loop)

    def iniciar(self):
        self.root.after(10, self.loop)
        self.root.mainloop()


if __name__ == "__main__":
    demo = DemoPosturasG1()
    demo.iniciar()
