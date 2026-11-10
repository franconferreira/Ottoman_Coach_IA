"""Demo Standalone: Simulación 3D de Posturas y Gesticulación del Humanoide Unitree G1.

Permite experimentar visualmente y en tiempo real:
  1. Postura Base Neutra vs Otras actitudes emocionales (Alegría, Tristeza, Ansiedad).
  2. Idle Breathing: Respiración sutil continua cuando el robot está en reposo.
  3. Co-Speech Gestures: Gesticulación coordinada de brazos, codos, muñecas y dedos
     cuando el robot está hablando (con velocidad y amplitud moduladas).
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from pathlib import Path
from typing import Optional

import mujoco
from PIL import Image, ImageTk


class DemoPosturasG1:
    def __init__(self):
        self.ancho_render = 560
        self.alto_render = 480

        # Estado cinemático
        self.emocion_actual = "NEUTRO"
        self.hablando = False
        self.multiplicador_energia = 1.0   # 0.5 (calmo) .. 1.0 (medio) .. 1.8 (vivo)

        # Cargar MuJoCo
        self._inicializar_simulador()

        # Construir Interfaz Gráfica Tkinter
        self.root = tk.Tk()
        self.root.title("Demo 3D — Posturas y Gesticulación Humanoide Unitree G1")
        self.root.geometry("820x680")
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

        # Poses objetivo actuales (para lerp suave)
        self.pose_actual = {
            "waist_pitch": 0.0,
            "waist_yaw": 0.0,
            "left_shoulder_pitch": 0.20,
            "right_shoulder_pitch": 0.20,
            "left_shoulder_roll": 0.15,
            "right_shoulder_roll": -0.15,
            "left_elbow": -0.35,
            "right_elbow": -0.35,
            "left_wrist_roll": 0.0,
            "right_wrist_roll": 0.0,
            "manos": 0.05,
        }

    def _construir_ui(self):
        # Título superior
        lbl_titulo = tk.Label(
            self.root,
            text="UNITREE G1 — DEMO DE POSTURA Y GESTICULACIÓN AL HABLAR",
            bg="#070B14", fg="#38BDF8", font=("Segoe UI", 11, "bold"), pady=8
        )
        lbl_titulo.pack()

        # Canvas central para el visor 3D
        self.canvas = tk.Canvas(
            self.root, width=self.ancho_render, height=self.alto_render,
            bg="#060911", highlightbackground="#1E293B", highlightthickness=2
        )
        self.canvas.pack(pady=4)

        # Barra de telemetría en vivo
        self.lbl_telemetria = tk.Label(
            self.root,
            text="Modo: NEUTRO | Estado: EN REPOSO (Idle Breathing 0.25 Hz)",
            bg="#0D1322", fg="#A7F3D0", font=("Consolas", 9, "bold"),
            padx=12, pady=4, relief="ridge"
        )
        self.lbl_telemetria.pack(fill="x", padx=40, pady=4)

        # Panel de controles interactivos
        frame_controles = tk.Frame(self.root, bg="#070B14", pady=4)
        frame_controles.pack()

        # Botón Toggle Hablando
        self.btn_hablar = tk.Button(
            frame_controles,
            text="🗣️ HABLANDO: NO (En Reposo)",
            bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 10, "bold"),
            padx=16, pady=6, relief="flat", cursor="hand2",
            command=self._toggle_hablando
        )
        self.btn_hablar.grid(row=0, column=0, columnspan=2, padx=8, pady=4)

        # Selector de Velocidad / Energía
        frame_energia = tk.Frame(frame_controles, bg="#070B14")
        frame_energia.grid(row=0, column=2, columnspan=3, padx=8, pady=4)
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

        # Fila de Presets Emocionales
        frame_emociones = tk.Frame(self.root, bg="#070B14", pady=4)
        frame_emociones.pack()
        tk.Label(frame_emociones, text="Actitud Emocional:", bg="#070B14", fg="#94A3B8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=6)

        emociones = [
            ("🔵 NEUTRO", "NEUTRO", "#38BDF8"),
            ("🟡 ALEGRÍA", "MOTIVACION_ALEGRIA", "#FBBF24"),
            ("🟠 TRISTEZA", "TRISTEZA_DESANIMO", "#93C5FD"),
            ("🟢 ANSIEDAD", "ANSIEDAD_ESTRES", "#6EE7B7"),
        ]
        for txt_b, emo_clave, col_b in emociones:
            b = tk.Button(
                frame_emociones, text=txt_b, bg="#0F172A", fg=col_b,
                font=("Segoe UI", 8, "bold"), padx=10, pady=3, relief="flat", cursor="hand2",
                command=lambda e=emo_clave: self._set_emocion(e)
            )
            b.pack(side="left", padx=3)

    def _toggle_hablando(self):
        self.hablando = not self.hablando
        if self.hablando:
            self.btn_hablar.config(
                text="🗣️ HABLANDO: SÍ (Gesticulando al compás)",
                bg="#0284C7", fg="#FFFFFF"
            )
        else:
            self.btn_hablar.config(
                text="🗣️ HABLANDO: NO (En Reposo)",
                bg="#1E293B", fg="#F8FAFC"
            )
        self._actualizar_telemetria()

    def _set_emocion(self, emo: str):
        self.emocion_actual = emo
        self._actualizar_telemetria()

    def _actualizar_telemetria(self):
        estado_h = "HABLANDO (Co-speech Gestures activos)" if self.hablando else "EN REPOSO (Idle Breathing)"
        freq = 0.25 if not self.hablando else (1.6 * self.multiplicador_energia)
        self.lbl_telemetria.config(
            text=f"Modo: {self.emocion_actual} | {estado_h} | Cadencia: {freq:.2f} Hz | Energía: x{self.multiplicador_energia:.1f}"
        )

    def loop(self):
        ahora = time.monotonic()
        dt = min(0.06, max(0.001, ahora - self._ultimo_tiempo))
        self._ultimo_tiempo = ahora

        # 1. Definir Postura Base objetivo según la emoción elegida
        if self.emocion_actual == "MOTIVACION_ALEGRIA":
            # Torso erguido, hombros abiertos y elevados, palmas abiertas
            base_obj = {
                "waist_pitch": -0.04,
                "waist_yaw": 0.0,
                "left_shoulder_pitch": 0.28,
                "right_shoulder_pitch": 0.28,
                "left_shoulder_roll": 0.32,
                "right_shoulder_roll": -0.32,
                "left_elbow": -0.55,
                "right_elbow": -0.55,
                "left_wrist_roll": 0.30,
                "right_wrist_roll": -0.30,
                "manos": 0.25,
            }
        elif self.emocion_actual == "TRISTEZA_DESANIMO":
            # Inclinación empática de torso (+0.18 rad), brazos recogidos, codos cerca
            base_obj = {
                "waist_pitch": 0.18,
                "waist_yaw": 0.0,
                "left_shoulder_pitch": 0.12,
                "right_shoulder_pitch": 0.12,
                "left_shoulder_roll": 0.08,
                "right_shoulder_roll": -0.08,
                "left_elbow": -0.22,
                "right_elbow": -0.22,
                "left_wrist_roll": 0.0,
                "right_wrist_roll": 0.0,
                "manos": 0.05,
            }
        elif self.emocion_actual == "ANSIEDAD_ESTRES":
            # Co-regulación: postura relajada, hombros descansados, palmas hacia abajo
            base_obj = {
                "waist_pitch": 0.02,
                "waist_yaw": 0.0,
                "left_shoulder_pitch": 0.18,
                "right_shoulder_pitch": 0.18,
                "left_shoulder_roll": 0.18,
                "right_shoulder_roll": -0.18,
                "left_elbow": -0.38,
                "right_elbow": -0.38,
                "left_wrist_roll": -0.20,
                "right_wrist_roll": 0.20,
                "manos": 0.10,
            }
        else:  # NEUTRO
            # Postura canónica de escucha atenta
            base_obj = {
                "waist_pitch": 0.0,
                "waist_yaw": 0.0,
                "left_shoulder_pitch": 0.20,
                "right_shoulder_pitch": 0.20,
                "left_shoulder_roll": 0.15,
                "right_shoulder_roll": -0.15,
                "left_elbow": -0.32,
                "right_elbow": -0.32,
                "left_wrist_roll": 0.0,
                "right_wrist_roll": 0.0,
                "manos": 0.05,
            }

        # Transición suave (lerp) hacia la postura base
        vel_lerp = 4.0 * dt
        for k, v in base_obj.items():
            self.pose_actual[k] += (v - self.pose_actual[k]) * min(1.0, vel_lerp)

        # 2. Modulación armónica continua
        if self.hablando:
            # Co-speech gesture: oscilaciones vivas asimétricas según energía
            vel_onda = (3.5 * self.multiplicador_energia)
            self._fase_gesto = (self._fase_gesto + dt * vel_onda) % (2.0 * math.pi)
            f = self._fase_gesto

            amp_hombro = 0.16 * self.multiplicador_energia
            amp_codo = 0.14 * self.multiplicador_energia

            mod_l_sh = amp_hombro * math.sin(f)
            mod_r_sh = amp_hombro * math.sin(f + 0.9)
            mod_l_el = amp_codo * math.cos(f)
            mod_r_el = amp_codo * math.cos(f + 0.9)
            mod_dedos = 0.20 * abs(math.sin(f * 0.8))
            mod_torso = 0.02 * math.sin(f * 0.5)
        else:
            # Idle breathing: respiración sutil continua a ~0.25 Hz
            f_resp = ahora * 1.57  # ~4 segundos por ciclo respiratorio
            mod_torso = 0.025 * math.sin(f_resp)
            mod_l_sh = 0.025 * math.sin(f_resp)
            mod_r_sh = 0.025 * math.sin(f_resp)
            mod_l_el = 0.015 * math.cos(f_resp)
            mod_r_el = 0.015 * math.cos(f_resp)
            mod_dedos = 0.04 * (1.0 + math.sin(f_resp))

        # 3. Aplicar articulaciones resultantes en MuJoCo
        p = self.pose_actual
        if "waist_pitch" in self.jmap:
            self.data.qpos[self.jmap["waist_pitch"]] = p["waist_pitch"] + mod_torso
        if "left_shoulder_pitch" in self.jmap:
            self.data.qpos[self.jmap["left_shoulder_pitch"]] = p["left_shoulder_pitch"] + mod_l_sh
        if "right_shoulder_pitch" in self.jmap:
            self.data.qpos[self.jmap["right_shoulder_pitch"]] = p["right_shoulder_pitch"] + mod_r_sh
        if "left_shoulder_roll" in self.jmap:
            self.data.qpos[self.jmap["left_shoulder_roll"]] = p["left_shoulder_roll"]
        if "right_shoulder_roll" in self.jmap:
            self.data.qpos[self.jmap["right_shoulder_roll"]] = p["right_shoulder_roll"]
        if "left_elbow" in self.jmap:
            self.data.qpos[self.jmap["left_elbow"]] = p["left_elbow"] + mod_l_el
        if "right_elbow" in self.jmap:
            self.data.qpos[self.jmap["right_elbow"]] = p["right_elbow"] + mod_r_el
        if "left_wrist_roll" in self.jmap:
            self.data.qpos[self.jmap["left_wrist_roll"]] = p["left_wrist_roll"]
        if "right_wrist_roll" in self.jmap:
            self.data.qpos[self.jmap["right_wrist_roll"]] = p["right_wrist_roll"]

        # Dedos Inspire RH56 (apertura / flexión armónica)
        apertura_dedos = max(0.02, min(1.2, p["manos"] + mod_dedos))
        for lado in ("left", "right"):
            for dedo in ("index", "middle", "ring", "pinky"):
                k_dedo = f"{lado}_hand_{dedo}"
                if k_dedo in self.jmap:
                    self.data.qpos[self.jmap[k_dedo]] = apertura_dedos

        # 4. Renderizar escena offscreen en el hilo principal
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
