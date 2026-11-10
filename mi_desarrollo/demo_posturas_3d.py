"""Demo Standalone: Simulación 3D de Posturas y Gesticulación Teatral del Humanoide Unitree G1.

Permite experimentar visualmente y en tiempo real:
  1. Roles Animatrónicos Teatrales (Disney Imagineering / Show Action Sequencing):
     - 🎉 Compañero de Festejo (Usuario Alegre)
     - 💛 Contenedor Empático (Usuario Triste)
     - 🛡️ Pacificador / Desescalada (Usuario Enojado)
     - 🌊 Guía de Respiración y Sosiego (Usuario Ansioso)
  2. Grandes Arcos Expresivos (30° a 60° en torso, hombros, codos y palmas).
  3. Modulación continua por Sliders de Valencia y Arousal.
  4. Modo Habla (Co-speech beats) vs Modo Reposo (Idle Breathing).
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
from coach_emocional import CoreografoPosturalG1, RepertorioAnimatronicoG1


class DemoPosturasG1:
    def __init__(self):
        self.ancho_render = 560
        self.alto_render = 440

        # Estado cinemático y afectivo
        self.emocion_actual = "NEUTRO"
        self.valencia = 0.0
        self.arousal = 0.0
        self.hablando = False
        self.multiplicador_energia = 1.0

        # Secuenciador teatral (Show Action Sequencing)
        self.modo_teatral = False
        self._secuencia_actual: list[dict[str, float]] = []
        self._idx_secuencia = 0
        self._duracion_step = 0.70
        self._ultimo_tiempo_pose = time.monotonic()

        # Cargar MuJoCo
        self._inicializar_simulador()

        # Construir Interfaz Gráfica Tkinter
        self.root = tk.Tk()
        self.root.title("Demo 3D — Animatrónica Teatral Humanoide Unitree G1 (Disney Style)")
        self.root.geometry("880x750")
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
            text="UNITREE G1 — EXPRESIVIDAD ANIMATRÓNICA TEATRAL (DISNEY STYLE)",
            bg="#070B14", fg="#38BDF8", font=("Segoe UI", 11, "bold"), pady=4
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
            text="Modo: NEUTRO | Estado: EN REPOSO | Coreografía: Ninguna",
            bg="#0D1322", fg="#A7F3D0", font=("Consolas", 9, "bold"),
            padx=12, pady=4, relief="ridge"
        )
        self.lbl_telemetria.pack(fill="x", padx=30, pady=2)

        # Panel de Controles
        frame_controles = tk.Frame(self.root, bg="#070B14", pady=2)
        frame_controles.pack()

        # Botón Toggle Hablando
        self.btn_hablar = tk.Button(
            frame_controles,
            text="🗣️ HABLANDO: NO (En Reposo)",
            bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 9, "bold"),
            padx=14, pady=3, relief="flat", cursor="hand2",
            command=self._toggle_hablando
        )
        self.btn_hablar.grid(row=0, column=0, padx=6, pady=2)

        # Selector de Energía
        frame_energia = tk.Frame(frame_controles, bg="#070B14")
        frame_energia.grid(row=0, column=1, padx=6, pady=2)
        tk.Label(frame_energia, text="Energía:", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=3)

        def _set_energia(val: float):
            self.multiplicador_energia = val
            self._actualizar_telemetria()

        tk.Button(frame_energia, text="Calmo (0.8x)", bg="#1E293B", fg="#93C5FD", font=("Segoe UI", 8),
                  command=lambda: _set_energia(0.60)).pack(side="left", padx=2)
        tk.Button(frame_energia, text="Normal (1.0x)", bg="#1E293B", fg="#A7F3D0", font=("Segoe UI", 8),
                  command=lambda: _set_energia(1.0)).pack(side="left", padx=2)
        tk.Button(frame_energia, text="Enérgico (1.6x)", bg="#1E293B", fg="#FDE047", font=("Segoe UI", 8),
                  command=lambda: _set_energia(1.60)).pack(side="left", padx=2)

        # =============================================================
        # 1. FILA DE ROLES TEATRALES COMPLEMENTARIOS (GRANDES ARCOS)
        # =============================================================
        frame_roles = tk.Frame(self.root, bg="#0B1120", padx=8, pady=4, highlightbackground="#334155", highlightthickness=1)
        frame_roles.pack(fill="x", padx=25, pady=3)
        tk.Label(
            frame_roles,
            text="🎭 ROLES TEATRALES (Disney Imagineering):",
            bg="#0B1120", fg="#FCD34D", font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=6)

        roles_info = [
            ("🎉 Festejo (Usuario Alegre)", "MOTIVACION_ALEGRIA", "#FDE047"),
            ("💛 Contención (Usuario Triste)", "TRISTEZA_DESANIMO", "#93C5FD"),
            ("🛡️ Pacificador (Usuario Enojado)", "ENOJO_FRUSTRACION", "#34D399"),
            ("🌊 Calma (Usuario Ansioso)", "ANSIEDAD_ESTRES", "#67E8F9"),
        ]
        for txt_r, rol_clave, col_btn in roles_info:
            b = tk.Button(
                frame_roles, text=txt_r, bg="#1E293B", fg=col_btn,
                font=("Segoe UI", 8, "bold"), padx=8, pady=3, relief="flat", cursor="hand2",
                command=lambda r=rol_clave: self._activar_rol_teatral(r)
            )
            b.pack(side="left", padx=3)

        # =============================================================
        # 2. SLIDERS CONTINUOS DE VALENCIA Y AROUSAL
        # =============================================================
        frame_sliders = tk.Frame(self.root, bg="#070B14", pady=2)
        frame_sliders.pack()

        tk.Label(frame_sliders, text="Valencia (Displacer ↔ Placer):", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8)).grid(row=0, column=0, padx=4)
        self.scale_valencia = tk.Scale(
            frame_sliders, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=160, bg="#0D1322", fg="#38BDF8", highlightthickness=0,
            command=lambda v: self._al_cambiar_slider()
        )
        self.scale_valencia.set(0.0)
        self.scale_valencia.grid(row=0, column=1, padx=4)

        tk.Label(frame_sliders, text="Arousal (Calma ↔ Activación):", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8)).grid(row=0, column=2, padx=4)
        self.scale_arousal = tk.Scale(
            frame_sliders, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=160, bg="#0D1322", fg="#FBBF24", highlightthickness=0,
            command=lambda v: self._al_cambiar_slider()
        )
        self.scale_arousal.set(0.0)
        self.scale_arousal.grid(row=0, column=3, padx=4)

        # =============================================================
        # 3. PRESETS BÁSICOS
        # =============================================================
        frame_presets = tk.Frame(self.root, bg="#070B14", pady=2)
        frame_presets.pack()
        tk.Label(frame_presets, text="Presets Rápidos:", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        presets = [
            ("🔵 Neutro", "NEUTRO", 0.0, 0.0, "#38BDF8"),
            ("🟡 Alegría", "MOTIVACION_ALEGRIA", 0.70, 0.60, "#FBBF24"),
            ("🟠 Tristeza", "TRISTEZA_DESANIMO", -0.65, -0.45, "#93C5FD"),
            ("🟢 Ansiedad", "ANSIEDAD_ESTRES", -0.35, 0.65, "#6EE7B7"),
            ("🔴 Enojo", "ENOJO_FRUSTRACION", -0.70, 0.75, "#F87171"),
        ]
        for txt_p, emo_k, v_val, a_val, col_p in presets:
            tk.Button(
                frame_presets, text=txt_p, bg="#0F172A", fg=col_p,
                font=("Segoe UI", 8), padx=7, pady=2, relief="flat", cursor="hand2",
                command=lambda e=emo_k, v=v_val, a=a_val: self._set_emocion_preset(e, v, a)
            ).pack(side="left", padx=2)

    def _activar_rol_teatral(self, rol: str):
        self.emocion_actual = rol
        self.modo_teatral = True
        sec, dur, _, _ = CoreografoPosturalG1.obtener_coreografia(rol)
        self._secuencia_actual = list(sec)
        self._idx_secuencia = 0
        self._duracion_step = max(0.40, float(dur))
        self._ultimo_tiempo_pose = time.monotonic()

        va_presets = {
            "MOTIVACION_ALEGRIA": (0.70, 0.60),
            "TRISTEZA_DESANIMO": (-0.65, -0.45),
            "ANSIEDAD_ESTRES": (-0.35, 0.65),
            "ENOJO_FRUSTRACION": (-0.70, 0.75),
            "NEUTRO": (0.0, 0.0),
        }
        if rol in va_presets:
            v, a = va_presets[rol]
            self.valencia = v
            self.arousal = a
            self.scale_valencia.set(v)
            self.scale_arousal.set(a)
        self._actualizar_telemetria()

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
        self.modo_teatral = False
        self.emocion_actual = emo
        self.valencia = val
        self.arousal = aro
        self.scale_valencia.set(val)
        self.scale_arousal.set(aro)
        self._actualizar_telemetria()

    def _al_cambiar_slider(self):
        self.modo_teatral = False
        self.valencia = float(self.scale_valencia.get())
        self.arousal = float(self.scale_arousal.get())
        self._actualizar_telemetria()

    def _actualizar_telemetria(self):
        estado_h = "HABLANDO (Ademanes Co-speech)" if self.hablando else "EN REPOSO (Idle Breathing)"
        if self.modo_teatral and self._secuencia_actual:
            paso_txt = f"🎭 Show Action [{self._idx_secuencia + 1}/{len(self._secuencia_actual)}]"
        else:
            paso_txt = "Cinemática Continua"
        self.lbl_telemetria.config(
            text=f"Modo: {self.emocion_actual} (V={self.valencia:+.2f}, A={self.arousal:+.2f}) | {estado_h} | {paso_txt}"
        )

    def loop(self):
        ahora = time.monotonic()
        dt = min(0.06, max(0.001, ahora - self._ultimo_tiempo))
        self._ultimo_tiempo = ahora

        if self.modo_teatral and self._secuencia_actual:
            # Secuenciador teatral: transiciona entre poses de gran arco cada duracion_step segundos
            if ahora - self._ultimo_tiempo_pose > self._duracion_step:
                self._idx_secuencia = (self._idx_secuencia + 1) % len(self._secuencia_actual)
                self._ultimo_tiempo_pose = ahora
                self._actualizar_telemetria()

            target_pose = self._secuencia_actual[self._idx_secuencia]
            for art, val in target_pose.items():
                if art in self.jmap:
                    adr = self.jmap[art]
                    actual = float(self.data.qpos[adr])
                    self.data.qpos[adr] = actual + (val - actual) * min(1.0, dt * 5.0)
        else:
            # Cinemática continua
            if self.hablando:
                vel_onda = (3.0 + 1.2 * max(0.0, self.arousal)) * self.multiplicador_energia
                self._fase_gesto = (self._fase_gesto + dt * vel_onda) % (2.0 * math.pi)
                fase = self._fase_gesto
            else:
                fase = ahora * 1.57

            pose_continua = CoreografoPosturalG1.generar_postura_continua(
                valencia=self.valencia,
                arousal=self.arousal,
                fase_tiempo=fase,
                hablando=self.hablando,
                energia=self.multiplicador_energia,
            )
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
