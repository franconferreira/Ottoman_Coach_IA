"""Visor y Estudio Interactivo 3D — Humanoide Unitree G1 (Ottoman Coach IA)
UADE — Inteligencia Artificial (TPO Final)

Permite inspeccionar, probar y visualizar el 100% de las animaciones, roles,
emotes teatrales, locomoción bípeda, gestos de manos diestras (Inspire RH56 6-DoF)
y capas biomecánicas vivas (respiración diafragmática, sway pendular, contrapposto
y gesticulación co-speech modulada por arousal).
"""

from __future__ import annotations

import math
import sys
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

import mujoco
from PIL import Image, ImageTk

# Importar motor postural y afectivo
_dir_actual = Path(__file__).resolve().parent
if str(_dir_actual) not in sys.path:
    sys.path.insert(0, str(_dir_actual))

import coach_emocional
from coach_emocional import (
    CoreografoPosturalG1,
    RepertorioAnimatronicoG1,
    _mano_relajada_organica,
    _mano_pulgar_arriba,
    _mano_puno_victoria,
    _mano_empatica_pecho,
    _mano_pacificador,
    _mano_senalamiento,
    _mano_declamatoria,
    _pose_neutra_suave,
)


class VisorEstudio3DG1:
    """Estudio visual integral de animaciones y biomecánica 3D del Unitree G1."""

    def __init__(self):
        self.ancho_render = 620
        self.alto_render = 480

        # Estados de control y biomecánica
        self.pausado = False
        self.velocidad_animacion = 1.0
        self.hablando = False
        self.multiplicador_energia = 1.0

        # Capas vivas opcionales
        self.activar_respiracion = True
        self.activar_sway = True

        # Plano afectivo Russell
        self.valencia = 0.0
        self.arousal = 0.0
        self.emocion_activa = "NEUTRO"

        # Modos de animación: 'continuo' | 'secuencia' | 'locomocion'
        self.modo_actual = "continuo"
        self.accion_locomocion = "quieto"  # quieto | caminando | girando | saludando

        # Show Action Sequencing (secuencias de múltiples poses)
        self._secuencia_actual: list[dict[str, float]] = []
        self._idx_secuencia = 0
        self._duracion_step = 0.75
        self._ultimo_tiempo_pose = time.monotonic()
        self._pose_objetivo: dict[str, float] = {}

        # Fases rítmicas
        self._fase_marcha = 0.0
        self._fase_gesto = 0.0
        self._pose_base = _pose_neutra_suave()

        # Mano seleccionada para el banco de manos
        self.mano_objetivo = "right"  # 'right' | 'left' | 'both'

        # Inicializar Simulador MuJoCo
        self._inicializar_simulador()

        # Construir Interfaz Gráfica Tkinter
        self._construir_interfaz()

        self._ultimo_tiempo = time.monotonic()
        self._photo_ref = [None]

        # Iniciar con postura neutra viva
        self.cargar_pose_neutra()

    # =====================================================================
    #  INICIALIZACIÓN DE MUJOCO
    # =====================================================================
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
            raise FileNotFoundError("No se encontró scene_29dof.xml del Unitree G1")

        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        self.model.opt.gravity[:] = 0.0

        # Mapeo de articulaciones
        self.jmap: dict[str, int] = {}
        for i in range(self.model.njnt):
            nom = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, i)
            if nom:
                adr = int(self.model.jnt_qposadr[i])
                self.jmap[nom] = adr
                if nom.endswith("_joint"):
                    self.jmap[nom[:-6]] = adr

        # Renderer y cámara
        self.renderer = mujoco.Renderer(self.model, self.alto_render, self.ancho_render)
        self.camera = mujoco.MjvCamera()
        self.camera.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.set_camara("entero")

        # Cargar postura inicial relajada
        self._aplicar_diccionario_pose(_pose_neutra_suave(), instantaneo=True)

    # =====================================================================
    #  CONSTRUCCIÓN DE LA INTERFAZ GRÁFICA
    # =====================================================================
    def _construir_interfaz(self):
        self.root = tk.Tk()
        self.root.title("Ottoman Coach IA — Estudio de Animación y Biomecánica 3D (Unitree G1)")
        self.root.geometry("1240x840")
        self.root.configure(bg="#0B0F19")
        self.root.minsize(1100, 750)

        # Estilo TTK para pestañas modernas oscuras
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#0B0F19", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1E293B", foreground="#94A3B8",
                        padding=[12, 6], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#0284C7"), ("active", "#334155")],
                  foreground=[("selected", "#FFFFFF"), ("active", "#F8FAFC")])

        # Header Superior
        frame_header = tk.Frame(self.root, bg="#0B0F19", pady=6)
        frame_header.pack(fill="x", padx=16)

        lbl_tit = tk.Label(
            frame_header,
            text="OTTOMAN COACH IA  •  ESTUDIO Y CATÁLOGO DE ANIMACIONES 3D",
            bg="#0B0F19", fg="#38BDF8", font=("Segoe UI", 12, "bold")
        )
        lbl_tit.pack(side="left")

        lbl_sub = tk.Label(
            frame_header,
            text="Unitree G1 Humanoide (29 DoF + Manos Inspire RH56)",
            bg="#0B0F19", fg="#64748B", font=("Segoe UI", 9)
        )
        lbl_sub.pack(side="left", padx=12)

        # Contenedor Principal (Panel Izquierdo: 3D / Panel Derecho: Controles)
        frame_cuerpo = tk.Frame(self.root, bg="#0B0F19")
        frame_cuerpo.pack(fill="both", expand=True, padx=14, pady=4)

        # ==========================================
        #  PANEL IZQUIERDO: VISOR 3D + TELEMETRÍA
        # ==========================================
        frame_izq = tk.Frame(frame_cuerpo, bg="#0B0F19", width=630)
        frame_izq.pack(side="left", fill="both", padx=(0, 10))

        # Canvas 3D MuJoCo
        frame_canvas_border = tk.Frame(frame_izq, bg="#1E293B", padx=2, pady=2)
        frame_canvas_border.pack()
        self.canvas = tk.Canvas(
            frame_canvas_border, width=self.ancho_render, height=self.alto_render,
            bg="#050811", highlightthickness=0
        )
        self.canvas.pack()

        # Barra de Cámaras
        frame_camaras = tk.Frame(frame_izq, bg="#0F172A", pady=4, padx=6)
        frame_camaras.pack(fill="x", pady=(4, 2))

        tk.Label(frame_camaras, text="CÁMARA:", bg="#0F172A", fg="#94A3B8",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        cams = [
            ("🧍 Frontal", "entero"),
            ("🔍 Torso", "torso"),
            ("🖐️ Manos", "manos"),
            ("📐 Perfil 3/4", "perfil"),
        ]
        for nom, clave in cams:
            b = tk.Button(
                frame_camaras, text=nom, bg="#1E293B", fg="#E2E8F0",
                font=("Segoe UI", 8), padx=7, pady=2, relief="flat", cursor="hand2",
                command=lambda k=clave: self.set_camara(k)
            )
            b.pack(side="left", padx=2)

        # Botones de giro manual de cámara
        tk.Button(frame_camaras, text="↶", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 9, "bold"),
                  padx=6, pady=1, relief="flat", cursor="hand2",
                  command=lambda: self.rotar_camara(-15)).pack(side="left", padx=(10, 2))
        tk.Button(frame_camaras, text="↷", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 9, "bold"),
                  padx=6, pady=1, relief="flat", cursor="hand2",
                  command=lambda: self.rotar_camara(15)).pack(side="left", padx=2)
        tk.Button(frame_camaras, text="🔍+", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 8, "bold"),
                  padx=5, pady=1, relief="flat", cursor="hand2",
                  command=lambda: self.zoom_camara(-0.25)).pack(side="left", padx=2)
        tk.Button(frame_camaras, text="🔍-", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 8, "bold"),
                  padx=5, pady=1, relief="flat", cursor="hand2",
                  command=lambda: self.zoom_camara(0.25)).pack(side="left", padx=2)

        # Barra de Transporte / Playback
        frame_transport = tk.Frame(frame_izq, bg="#0F172A", pady=4, padx=6)
        frame_transport.pack(fill="x", pady=2)

        self.btn_pause = tk.Button(
            frame_transport, text="⏸ Pausar", bg="#334155", fg="#F8FAFC",
            font=("Segoe UI", 8, "bold"), padx=10, pady=2, relief="flat", cursor="hand2",
            command=self.toggle_pausa
        )
        self.btn_pause.pack(side="left", padx=3)

        tk.Button(
            frame_transport, text="🔄 Reset Neutro", bg="#1E293B", fg="#F8FAFC",
            font=("Segoe UI", 8), padx=8, pady=2, relief="flat", cursor="hand2",
            command=self.cargar_pose_neutra
        ).pack(side="left", padx=3)

        tk.Label(frame_transport, text="Velocidad:", bg="#0F172A", fg="#94A3B8",
                 font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))

        for v_txt, v_num in [("0.5x", 0.5), ("1.0x", 1.0), ("1.6x", 1.6)]:
            tk.Button(
                frame_transport, text=v_txt, bg="#1E293B", fg="#38BDF8",
                font=("Segoe UI", 8), padx=5, pady=1, relief="flat", cursor="hand2",
                command=lambda val=v_num: self.set_velocidad(val)
            ).pack(side="left", padx=1)

        # Panel de Telemetría en Vivo
        frame_tele = tk.Frame(frame_izq, bg="#050811", relief="solid", bd=1)
        frame_tele.pack(fill="both", expand=True, pady=(4, 0))

        self.lbl_tele_accion = tk.Label(
            frame_tele, text="ESTADO: EN REPOSO ACTIVO | ACCIÓN: REPOSO VIVO",
            bg="#050811", fg="#38BDF8", font=("Consolas", 9, "bold"), anchor="w", padx=8, pady=2
        )
        self.lbl_tele_accion.pack(fill="x")

        self.lbl_tele_pose = tk.Label(
            frame_tele, text="POSE / VARIANTE: Postura Canónica Neutra Suave",
            bg="#050811", fg="#FCD34D", font=("Consolas", 8), anchor="w", padx=8
        )
        self.lbl_tele_pose.pack(fill="x")

        self.lbl_tele_artics = tk.Label(
            frame_tele,
            text="Rodillas: L=0.32 R=0.32 | Torso Pitch: 0.00 | Altura Z: 0.793 m | CoM X: 0.000 m",
            bg="#050811", fg="#94A3B8", font=("Consolas", 8), anchor="w", padx=8, pady=3
        )
        self.lbl_tele_artics.pack(fill="x")

        # ==========================================
        #  PANEL DERECHO: PESTAÑAS DE CONTROLES
        # ==========================================
        frame_der = tk.Frame(frame_cuerpo, bg="#0B0F19")
        frame_der.pack(side="right", fill="both", expand=True)

        self.notebook = ttk.Notebook(frame_der)
        self.notebook.pack(fill="both", expand=True)

        # Pestaña 1: Emotes Teatrales
        tab_emotes = tk.Frame(self.notebook, bg="#0B0F19")
        self.notebook.add(tab_emotes, text=" 🎭 Emotes Teatrales ")
        self._construir_tab_emotes(tab_emotes)

        # Pestaña 2: Locomoción y Físico
        tab_locomocion = tk.Frame(self.notebook, bg="#0B0F19")
        self.notebook.add(tab_locomocion, text=" 🚶 Locomoción ")
        self._construir_tab_locomocion(tab_locomocion)

        # Pestaña 3: Galería de Manos 6-DoF
        tab_manos = tk.Frame(self.notebook, bg="#0B0F19")
        self.notebook.add(tab_manos, text=" 🖐️ Galería Manos 6-DoF ")
        self._construir_tab_manos(tab_manos)

        # Pestaña 4: Capas Vivas y Continuas
        tab_vivas = tk.Frame(self.notebook, bg="#0B0F19")
        self.notebook.add(tab_vivas, text=" 🫁 Capas Vivas y Sliders ")
        self._construir_tab_capas_vivas(tab_vivas)

    # ---------------------------------------------------------------------
    #  PESTAÑA 1: EMOTES TEATRALES (SCROLLABLE)
    # ---------------------------------------------------------------------
    def _construir_tab_emotes(self, parent: tk.Frame):
        canvas_scr = tk.Canvas(parent, bg="#0B0F19", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas_scr.yview)
        frame_scroll = tk.Frame(canvas_scr, bg="#0B0F19")

        frame_scroll.bind(
            "<Configure>",
            lambda e: canvas_scr.configure(scrollregion=canvas_scr.bbox("all"))
        )
        canvas_scr.create_window((0, 0), window=frame_scroll, anchor="nw")
        canvas_scr.configure(yscrollcommand=scrollbar.set)

        canvas_scr.pack(side="left", fill="both", expand=True, padx=(4, 0))
        scrollbar.pack(side="right", fill="y")

        # Configuración de Roles con Colores e Iconos
        roles_config = [
            ("🎉 ALEGRÍA / MOTIVACIÓN", "MOTIVACION_ALEGRIA", "#FDE047", [
                ("Base Festiva (Contrapposto)", "base"),
                ("Var 0: Victoria & Pulgar Triunfal", "var_0"),
                ("Var 1: Apertura Cálida & Felicitación", "var_1"),
                ("Var 2: Complicidad & Señalamiento", "var_2"),
                ("Ademán: Apertura Triunfal (V)", "ademan_A_apertura_triunfal"),
                ("Ademán: Celebración y Pulgar", "ademan_C_celebracion_pulgar"),
            ]),
            ("💛 TRISTEZA / CONTENCIÓN", "TRISTEZA_DESANIMO", "#93C5FD", [
                ("Base Empática (Inclinación Torso)", "base"),
                ("Var 0: Contención Íntima (Mano al Corazón)", "var_0"),
                ("Var 1: Acogida y Apoyo (2 Tiempos)", "var_1"),
                ("Var 2: Acompañamiento Silencioso", "var_2"),
                ("Ademán: Mano al Corazón", "ademan_A_mano_al_corazon"),
                ("Ademán: Acogida y Apoyo al Frente", "ademan_B_acogida_y_apoyo"),
            ]),
            ("🛡️ ENOJO / PACIFICADOR", "ENOJO_FRUSTRACION", "#34D399", [
                ("Base Enraizada (Paso Firme)", "base"),
                ("Var 0: Barrera de Freno / Serenidad", "var_0"),
                ("Var 1: Escucha con Aplomo", "var_1"),
                ("Var 2: Canalización a Tierra", "var_2"),
                ("Ademán: Barrera de Sosiego Frontal", "ademan_A_barrera_de_serenidad"),
                ("Ademán: Escucha con Aplomo", "ademan_B_escucha_con_aplomo"),
            ]),
            ("🌊 ANSIEDAD / SOSIEGO", "ANSIEDAD_ESTRES", "#67E8F9", [
                ("Base Co-regulación (Articulaciones Vivas)", "base"),
                ("Var 0: Metrónomo Respiratorio (Inhalar/Exhalar)", "var_0"),
                ("Var 1: Anclaje a Tierra (Grounding)", "var_1"),
                ("Var 2: Pausa y Sosiego al Pecho", "var_2"),
                ("Ademán: Inhalación Profunda", "ademan_A_inhalacion_profunda"),
                ("Ademán: Exhalación Calma", "ademan_B_exhalacion_calma"),
            ]),
            ("🤔 DUDA / SOCRÁTICO", "DUDA_INSEGURIDAD", "#C084FC", [
                ("Base Reflexiva (Atenta)", "base"),
                ("Var 0: Sopesar Opciones (Balanza Izq/Der)", "var_0"),
                ("Var 1: Indagación Reflexiva Socrática", "var_1"),
                ("Ademán: Sopesar Opción A (Izq)", "ademan_A_sopesar_opcion_a"),
                ("Ademán: Sopesar Opción B (Der)", "ademan_B_sopesar_opcion_b"),
            ]),
            ("⚪ NEUTRO / ATENCIÓN", "NEUTRO", "#E2E8F0", [
                ("Base Reposo Anatómico Natural", "base"),
                ("Var 0: Giro Atención Izquierda", "var_0"),
                ("Var 1: Giro Atención Derecha", "var_1"),
                ("Var 2: Escucha Abierta Frontal", "var_2"),
            ]),
            ("🛑 CRISIS / CONTENCIÓN ÉTICA", "CRISIS_RIESGO", "#F87171", [
                ("Postura de Escucha Ética Receptiva", "base"),
                ("Ademán: Escucha Pacífica", "ademan_A_escucha_pacifica"),
            ]),
        ]

        for tit_seccion, clave_rol, col_tit, botones in roles_config:
            card = tk.Frame(frame_scroll, bg="#111827", pady=4, padx=8, relief="solid", bd=1)
            card.pack(fill="x", pady=4, padx=4)

            # Título de la tarjeta
            lbl_card = tk.Label(
                card, text=tit_seccion, bg="#111827", fg=col_tit,
                font=("Segoe UI", 9, "bold"), anchor="w"
            )
            lbl_card.pack(fill="x", pady=(2, 4))

            # Cuadrícula de botones dentro de la tarjeta
            frame_grid = tk.Frame(card, bg="#111827")
            frame_grid.pack(fill="x")

            for idx, (txt_b, tipo_accion) in enumerate(botones):
                col = idx % 2
                row = idx // 2
                b = tk.Button(
                    frame_grid, text=txt_b, bg="#1E293B", fg="#F8FAFC",
                    activebackground="#0284C7", activeforeground="#FFFFFF",
                    font=("Segoe UI", 8), padx=8, pady=3, relief="flat", cursor="hand2",
                    command=lambda r=clave_rol, act=tipo_accion, nom=txt_b: self.ejecutar_emote(r, act, nom)
                )
                b.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
                frame_grid.columnconfigure(col, weight=1)

    # ---------------------------------------------------------------------
    #  PESTAÑA 2: LOCOMOCIÓN Y FÍSICO
    # ---------------------------------------------------------------------
    def _construir_tab_locomocion(self, parent: tk.Frame):
        p = tk.Frame(parent, bg="#0B0F19", padx=14, pady=12)
        p.pack(fill="both", expand=True)

        lbl = tk.Label(
            p, text="CINEMÁTICA BÍPEDA Y COMANDOS DE ACCIÓN FÍSICA",
            bg="#0B0F19", fg="#38BDF8", font=("Segoe UI", 10, "bold")
        )
        lbl.pack(anchor="w", pady=(0, 8))

        desc = tk.Label(
            p,
            text="Controlá directamente la marcha en dos patas, el giro rotacional y el saludo humanoide.\n"
                 "El simulador coordina caderas, rodillas y contrafase de brazos en tiempo real.",
            bg="#0B0F19", fg="#94A3B8", font=("Segoe UI", 8), justify="left"
        )
        desc.pack(anchor="w", pady=(0, 14))

        botones_loc = [
            ("🚶 Iniciar Marcha Bípeda (Caminar)", "caminando", "#0284C7",
             "Oscilación sinusoidal de caderas (±0.40 rad), flexión de rodillas y braceo rítmico cruzado."),
            ("🔄 Iniciar Giro en el Lugar (Rotar)", "girando", "#0EA5E9",
             "Pivoteo sobre el eje Yaw con zancada lateral amortiguada y compensación pélvica."),
            ("👋 Iniciar Saludo Humanoide a Cámara", "saludando", "#10B981",
             "Brazo derecho elevado al frente, codo en 90° y oscilación rápida de muñeca a 8 Hz."),
            ("⏹️ Detener / Pasar a Reposo Vivo", "quieto", "#EF4444",
             "Frena la marcha o giro suavemente y reanuda el idle breathing y sway orgánico."),
        ]

        for txt_btn, accion, col_bg, explicacion in botones_loc:
            card = tk.Frame(p, bg="#111827", pady=6, padx=10, relief="solid", bd=1)
            card.pack(fill="x", pady=4)

            btn = tk.Button(
                card, text=txt_btn, bg=col_bg, fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"), padx=12, pady=4, relief="flat", cursor="hand2",
                command=lambda a=accion, t=txt_btn: self.set_locomocion(a, t)
            )
            btn.pack(side="left")

            lbl_exp = tk.Label(
                card, text=explicacion, bg="#111827", fg="#CBD5E1",
                font=("Segoe UI", 8), justify="left", wraplength=320
            )
            lbl_exp.pack(side="left", padx=12)

    # ---------------------------------------------------------------------
    #  PESTAÑA 3: GALERÍA DE MANOS 6-DOF (INSPIRE RH56)
    # ---------------------------------------------------------------------
    def _construir_tab_manos(self, parent: tk.Frame):
        p = tk.Frame(parent, bg="#0B0F19", padx=14, pady=10)
        p.pack(fill="both", expand=True)

        lbl = tk.Label(
            p, text="BANCO DE ARQUETIPOS DE MANOS DIESTRAS INSPIRE RH56",
            bg="#0B0F19", fg="#38BDF8", font=("Segoe UI", 10, "bold")
        )
        lbl.pack(anchor="w", pady=(0, 4))

        lbl_desc = tk.Label(
            p,
            text="Cada mano cuenta con 6 articulaciones independientes (Índice, Mayor, Anular, Meñique,\n"
                 "Rotación de Pulgar y Flexión de Pulgar). Se adapta automáticamente al cuerpo.",
            bg="#0B0F19", fg="#94A3B8", font=("Segoe UI", 8), justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(0, 10))

        # Selector de Lado (Izquierda, Derecha, Ambas)
        frame_lado = tk.Frame(p, bg="#111827", pady=5, padx=8)
        frame_lado.pack(fill="x", pady=(0, 8))

        tk.Label(frame_lado, text="APLICAR EN:", bg="#111827", fg="#FCD34D",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        self.var_lado = tk.StringVar(value="both")
        for txt_l, val_l in [("Mano Derecha", "right"), ("Mano Izquierda", "left"), ("Ambas Manos", "both")]:
            r = tk.Radiobutton(
                frame_lado, text=txt_l, value=val_l, variable=self.var_lado,
                bg="#111827", fg="#F8FAFC", selectcolor="#0284C7",
                activebackground="#111827", activeforeground="#FFFFFF",
                font=("Segoe UI", 8), cursor="hand2"
            )
            r.pack(side="left", padx=6)

        # Botón para hacer zoom directo a manos
        tk.Button(
            frame_lado, text="🔍 Enfocar Cámara a Manos", bg="#0284C7", fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"), padx=8, pady=2, relief="flat", cursor="hand2",
            command=lambda: self.set_camara("manos")
        ).pack(side="right", padx=4)

        # Lista de Arquetipos de Manos
        arquetipos = [
            ("1. Cascada Relajada Orgánica", _mano_relajada_organica,
             "Flexión anatómica progresiva (índice 0.22, meñique 0.58) y pulgar semirrotado natural."),
            ("2. Pulgar Arriba 👍 (Thumbs Up)", _mano_pulgar_arriba,
             "Pulgar extendido a 90° con rotación 0.70 y puño cerrado en los otros 4 dedos (1.25 rad)."),
            ("3. Puño Cerrado Victoria ✊", _mano_puno_victoria,
             "Puño victorioso cerrado firme con los 4 dedos en 1.28 rad y pulgar envolvente."),
            ("4. Mano Empática al Pecho / Corazón", _mano_empatica_pecho,
             "Dedos curvados con calidez (0.32 a 0.72 rad) adaptándose a la curvatura del tórax."),
            ("5. Mano Pacificador (Palma Freno ✋)", _mano_pacificador,
             "Dedos extendidos juntos (0.05 rad) con pulgar abierto: barrera universal de sosiego."),
            ("6. Dedo Índice Señalando ☝️", _mano_senalamiento,
             "Índice extendido recto (0.05 rad), restantes recogidos (1.22 rad) con complicidad."),
            ("7. Palma Declamatoria Abierta 🫱", _mano_declamatoria,
             "Apertura escénica en abanico cóncavo (0.10 a 0.32 rad) en actitud de entrega/explicación."),
        ]

        for nom_m, fn_m, desc_m in arquetipos:
            card = tk.Frame(p, bg="#111827", pady=4, padx=8, relief="solid", bd=1)
            card.pack(fill="x", pady=2)

            btn = tk.Button(
                card, text=nom_m, bg="#1E293B", fg="#F8FAFC",
                font=("Segoe UI", 8, "bold"), padx=10, pady=2, relief="flat", cursor="hand2",
                command=lambda f=fn_m, n=nom_m: self.aplicar_arquetipo_mano(f, n)
            )
            btn.pack(side="left")

            lbl_d = tk.Label(
                card, text=desc_m, bg="#111827", fg="#94A3B8",
                font=("Segoe UI", 8), justify="left"
            )
            lbl_d.pack(side="left", padx=8)

    # ---------------------------------------------------------------------
    #  PESTAÑA 4: CAPAS VIVAS Y SLIDERS CONTINUOS
    # ---------------------------------------------------------------------
    def _construir_tab_capas_vivas(self, parent: tk.Frame):
        p = tk.Frame(parent, bg="#0B0F19", padx=14, pady=10)
        p.pack(fill="both", expand=True)

        lbl = tk.Label(
            p, text="DINÁMICAS BIOMECÁNICAS VIVAS Y ESPACIO VALENCIA-AROUSAL",
            bg="#0B0F19", fg="#38BDF8", font=("Segoe UI", 10, "bold")
        )
        lbl.pack(anchor="w", pady=(0, 6))

        # 1. Modo Habla (Co-speech beats)
        card_habla = tk.Frame(p, bg="#111827", pady=8, padx=10, relief="solid", bd=1)
        card_habla.pack(fill="x", pady=4)

        self.btn_hablar = tk.Button(
            card_habla, text="🗣️ MODO HABLA: DESACTIVADO (En Reposo)",
            bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 9, "bold"),
            padx=14, pady=4, relief="flat", cursor="hand2",
            command=self.toggle_habla
        )
        self.btn_hablar.pack(side="left")

        tk.Label(card_habla, text="Energía:", bg="#111827", fg="#94A3B8",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(14, 4))

        for t_e, v_e in [("Calmo (0.6x)", 0.6), ("Normal (1.0x)", 1.0), ("Enérgico (1.6x)", 1.6)]:
            tk.Button(
                card_habla, text=t_e, bg="#1E293B", fg="#38BDF8",
                font=("Segoe UI", 8), padx=6, pady=2, relief="flat", cursor="hand2",
                command=lambda val=v_e: self.set_energia_habla(val)
            ).pack(side="left", padx=2)

        # 2. Checkboxes de Capas Vivas
        card_vivas = tk.Frame(p, bg="#111827", pady=8, padx=10, relief="solid", bd=1)
        card_vivas.pack(fill="x", pady=4)

        self.var_resp = tk.BooleanVar(value=True)
        chk_resp = tk.Checkbutton(
            card_vivas, text="🫁 Respiración Diafragmática Activa (Ciclo ~4s en torso, hombros y dedos)",
            variable=self.var_resp, bg="#111827", fg="#F8FAFC", selectcolor="#0284C7",
            font=("Segoe UI", 8), command=self.actualizar_checks_vivas
        )
        chk_resp.pack(anchor="w", pady=2)

        self.var_sway = tk.BooleanVar(value=True)
        chk_sway = tk.Checkbutton(
            card_vivas, text="⚖️ Balanceo Postural Pendular y Contrapposto (Ciclo ~6.5s en pelvis y peso)",
            variable=self.var_sway, bg="#111827", fg="#F8FAFC", selectcolor="#0284C7",
            font=("Segoe UI", 8), command=self.actualizar_checks_vivas
        )
        chk_sway.pack(anchor="w", pady=2)

        # 3. Sliders de Valencia y Arousal
        card_sliders = tk.Frame(p, bg="#111827", pady=8, padx=10, relief="solid", bd=1)
        card_sliders.pack(fill="x", pady=4)

        tk.Label(
            card_sliders, text="MODULACIÓN CONTINUA SEGÚN PLANO DE RUSSELL:",
            bg="#111827", fg="#FCD34D", font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 4))

        frame_s = tk.Frame(card_sliders, bg="#111827")
        frame_s.pack(fill="x")

        tk.Label(frame_s, text="Valencia (Displacer ↔ Placer):", bg="#111827", fg="#CBD5E1",
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w", padx=4)
        self.scale_val = tk.Scale(
            frame_s, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=180, bg="#0B0F19", fg="#38BDF8", highlightthickness=0,
            command=lambda v: self.al_cambiar_sliders()
        )
        self.scale_val.set(0.0)
        self.scale_val.grid(row=0, column=1, padx=6)

        tk.Label(frame_s, text="Arousal (Calma ↔ Activación):", bg="#111827", fg="#CBD5E1",
                 font=("Segoe UI", 8)).grid(row=0, column=2, sticky="w", padx=4)
        self.scale_aro = tk.Scale(
            frame_s, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal",
            length=180, bg="#0B0F19", fg="#FBBF24", highlightthickness=0,
            command=lambda v: self.al_cambiar_sliders()
        )
        self.scale_aro.set(0.0)
        self.scale_aro.grid(row=0, column=3, padx=6)

    # =====================================================================
    #  MÉTODOS DE CÁMARA
    # =====================================================================
    def set_camara(self, tipo: str):
        if tipo == "entero":
            self.camera.lookat[:] = [0.0, 0.0, 0.70]
            self.camera.distance = 2.15
            self.camera.elevation = -10.0
            self.camera.azimuth = 162.0
        elif tipo == "torso":
            self.camera.lookat[:] = [0.0, 0.0, 0.88]
            self.camera.distance = 1.25
            self.camera.elevation = -6.0
            self.camera.azimuth = 160.0
        elif tipo == "manos":
            self.camera.lookat[:] = [0.05, 0.0, 0.72]
            self.camera.distance = 0.95
            self.camera.elevation = -8.0
            self.camera.azimuth = 152.0
        elif tipo == "perfil":
            self.camera.lookat[:] = [0.0, 0.0, 0.75]
            self.camera.distance = 1.95
            self.camera.elevation = -6.0
            self.camera.azimuth = 95.0

    def rotar_camara(self, delta_azimuth: float):
        self.camera.azimuth = (self.camera.azimuth + delta_azimuth) % 360.0

    def zoom_camara(self, delta_dist: float):
        self.camera.distance = max(0.5, min(4.0, self.camera.distance + delta_dist))

    # =====================================================================
    #  ACCIONES DE ANIMACIÓN Y POSTURA
    # =====================================================================
    def toggle_pausa(self):
        self.pausado = not self.pausado
        if self.pausado:
            self.btn_pause.config(text="▶ Reanudar", bg="#0284C7")
        else:
            self.btn_pause.config(text="⏸ Pausar", bg="#334155")

    def set_velocidad(self, v: float):
        self.velocidad_animacion = v

    def cargar_pose_neutra(self):
        self.modo_actual = "continuo"
        self.accion_locomocion = "quieto"
        self._secuencia_actual = []
        self._idx_secuencia = 0
        self.valencia = 0.0
        self.arousal = 0.0
        self.scale_val.set(0.0)
        self.scale_aro.set(0.0)
        self._pose_base = _pose_neutra_suave()
        self._aplicar_diccionario_pose(self._pose_base, instantaneo=False)
        self.lbl_tele_accion.config(text="ESTADO: EN REPOSO ACTIVO | ACCIÓN: REPOSO VIVO")
        self.lbl_tele_pose.config(text="POSE / VARIANTE: Postura Canónica Neutra Suave")

    def ejecutar_emote(self, rol: str, tipo_accion: str, nombre_visible: str):
        """Ejecuta una postura base, ademán o secuencia de emote del catálogo."""
        self.emocion_activa = rol
        self.accion_locomocion = "quieto"
        rol_datos = RepertorioAnimatronicoG1.ROLES.get(rol, {})

        if tipo_accion == "base":
            # Postura Base del Rol
            self.modo_actual = "continuo"
            self._secuencia_actual = []
            base_dict = dict(_pose_neutra_suave())
            base_dict.update(rol_datos.get("base", {}))
            self._pose_base = base_dict
            self._pose_objetivo = base_dict
            self.lbl_tele_accion.config(text=f"ESTADO: POSTURA BASE | ROL: {rol}")
            self.lbl_tele_pose.config(text=f"POSE / VARIANTE: {nombre_visible}")

        elif tipo_accion.startswith("ademan_"):
            # Ademán estático individual
            clave_ad = tipo_accion[len("ademan_"):]
            ad_dict = rol_datos.get("ademanes", {}).get(clave_ad, {})
            pose_completa = dict(_pose_neutra_suave())
            pose_completa.update(rol_datos.get("base", {}))
            pose_completa.update(ad_dict)
            self.modo_actual = "continuo"
            self._secuencia_actual = []
            self._pose_base = pose_completa
            self._pose_objetivo = pose_completa
            self.lbl_tele_accion.config(text=f"ESTADO: ADEMÁN TEATRAL | ROL: {rol}")
            self.lbl_tele_pose.config(text=f"POSE / VARIANTE: {nombre_visible}")

        elif tipo_accion.startswith("var_"):
            # Secuencia teatral multi-pose (Show Action Sequencing)
            idx_v = int(tipo_accion.split("_")[1])
            vars_list = rol_datos.get("variantes", [])
            if idx_v < len(vars_list):
                pasos = vars_list[idx_v]
                # Construir secuencia completa con base
                sec_comp = []
                for p_dict in pasos:
                    p = dict(_pose_neutra_suave())
                    p.update(rol_datos.get("base", {}))
                    p.update(p_dict)
                    sec_comp.append(p)

                self.modo_actual = "secuencia"
                self._secuencia_actual = sec_comp
                self._idx_secuencia = 0
                self._duracion_step = 0.85
                self._ultimo_tiempo_pose = time.monotonic()
                self._pose_objetivo = dict(sec_comp[0])
                self.lbl_tele_accion.config(text=f"ESTADO: EMOTE TEATRAL EN CURSO | ROL: {rol}")
                self.lbl_tele_pose.config(text=f"POSE / VARIANTE: {nombre_visible} [Paso 1/{len(sec_comp)}]")

    def set_locomocion(self, accion: str, nombre_visible: str):
        """Activa marcha bípeda, giro, saludo o reposo."""
        self.accion_locomocion = accion
        self.modo_actual = "locomocion" if accion != "quieto" else "continuo"
        self._secuencia_actual = []
        self._idx_secuencia = 0

        if accion == "quieto":
            self.cargar_pose_neutra()
        else:
            self.lbl_tele_accion.config(text=f"ESTADO: LOCOMOCIÓN ACTIVA | ACCIÓN: {accion.upper()}")
            self.lbl_tele_pose.config(text=f"COMANDO: {nombre_visible}")

    def aplicar_arquetipo_mano(self, fn_mano, nombre_mano: str):
        """Aplica un preset de mano Inspire RH56 a la mano derecha, izquierda o ambas."""
        lado_sel = self.var_lado.get()
        d_mano = {}
        if lado_sel in ("right", "both"):
            d_mano.update(fn_mano("right"))
        if lado_sel in ("left", "both"):
            d_mano.update(fn_mano("left"))

        self._pose_base.update(d_mano)
        self._pose_objetivo.update(d_mano)
        for art, val in d_mano.items():
            if art in self.jmap:
                self.data.qpos[self.jmap[art]] = val

        self.lbl_tele_accion.config(text=f"ESTADO: GALERÍA DE MANOS 6-DOF | APLICADO A: {lado_sel.upper()}")
        self.lbl_tele_pose.config(text=f"ARQUETIPO: {nombre_mano}")

    def toggle_habla(self):
        self.hablando = not self.hablando
        if self.hablando:
            self.btn_hablar.config(
                text="🗣️ MODO HABLA: ACTIVADO (Co-speech Beats)",
                bg="#0284C7", fg="#FFFFFF"
            )
        else:
            self.btn_hablar.config(
                text="🗣️ MODO HABLA: DESACTIVADO (En Reposo)",
                bg="#1E293B", fg="#F8FAFC"
            )

    def set_energia_habla(self, val: float):
        self.multiplicador_energia = val

    def actualizar_checks_vivas(self):
        self.activar_respiracion = self.var_resp.get()
        self.activar_sway = self.var_sway.get()

    def al_cambiar_sliders(self):
        self.valencia = float(self.scale_val.get())
        self.arousal = float(self.scale_aro.get())
        if self.valencia > 0.25:
            self.emocion_activa = "MOTIVACION_ALEGRIA"
        elif self.valencia < -0.20 and self.arousal < 0.10:
            self.emocion_activa = "TRISTEZA_DESANIMO"
        elif self.valencia < -0.20 and self.arousal >= 0.10:
            self.emocion_activa = "ENOJO_FRUSTRACION"
        elif self.arousal > 0.30:
            self.emocion_activa = "ANSIEDAD_ESTRES"
        else:
            self.emocion_activa = "NEUTRO"

        self.lbl_tele_accion.config(
            text=f"ESTADO: MODULACIÓN RUSSELL f(V, A) | ROL: {self.emocion_activa}"
        )
        self.lbl_tele_pose.config(
            text=f"Valencia: {self.valencia:+.2f} | Arousal: {self.arousal:+.2f}"
        )

    def _aplicar_diccionario_pose(self, pose_dict: dict[str, float], instantaneo: bool = False):
        for k, v in pose_dict.items():
            if k in self.jmap:
                if instantaneo:
                    self.data.qpos[self.jmap[k]] = v
                self._pose_objetivo[k] = v

    # =====================================================================
    #  CICLO PRINCIPAL DE RENDERIZADO Y CINEMÁTICA (~33 FPS)
    # =====================================================================
    def loop(self):
        ahora = time.monotonic()
        raw_dt = min(0.06, max(0.001, ahora - self._ultimo_tiempo))
        self._ultimo_tiempo = ahora

        if not self.pausado:
            dt = raw_dt * self.velocidad_animacion

            # -------------------------------------------------------------
            #  1. MODO SECUENCIA TEATRAL (SHOW ACTION)
            # -------------------------------------------------------------
            if self.modo_actual == "secuencia" and self._secuencia_actual:
                dur_step_ajustada = self._duracion_step / self.velocidad_animacion
                if ahora - self._ultimo_tiempo_pose > dur_step_ajustada:
                    self._idx_secuencia += 1
                    if self._idx_secuencia >= len(self._secuencia_actual):
                        # Transición a reposo continuo de esa emoción
                        self.modo_actual = "continuo"
                        self._pose_base = dict(self._secuencia_actual[-1])
                        self._secuencia_actual = []
                        self._idx_secuencia = 0
                        self.lbl_tele_accion.config(text=f"ESTADO: EMOTE COMPLETADO | REPOSO AFECTIVO: {self.emocion_activa}")
                    else:
                        self._ultimo_tiempo_pose = ahora
                        self.lbl_tele_pose.config(
                            text=f"EMOTE: {self.emocion_activa} [Paso {self._idx_secuencia + 1}/{len(self._secuencia_actual)}]"
                        )

                if self._secuencia_actual and self._idx_secuencia < len(self._secuencia_actual):
                    target = self._secuencia_actual[self._idx_secuencia]
                    for art, val_obj in target.items():
                        if art in self.jmap:
                            adr = self.jmap[art]
                            act = float(self.data.qpos[adr])
                            self.data.qpos[adr] = act + (val_obj - act) * min(1.0, dt * 8.5)

            # -------------------------------------------------------------
            #  2. MODO LOCOMOCIÓN (CAMINAR / GIRAR / SALUDAR)
            # -------------------------------------------------------------
            elif self.modo_actual == "locomocion":
                if self.accion_locomocion == "caminando":
                    self._fase_marcha = (self._fase_marcha + dt * 4.8) % (2.0 * math.pi)
                    f = self._fase_marcha
                    # Caderas
                    if "left_hip_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_hip_pitch"]] = 0.38 * math.sin(f)
                    if "right_hip_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_hip_pitch"]] = 0.38 * math.sin(f + math.pi)
                    # Rodillas
                    if "left_knee" in self.jmap:
                        self.data.qpos[self.jmap["left_knee"]] = max(0.05, 0.46 * math.sin(f + 1.1))
                    if "right_knee" in self.jmap:
                        self.data.qpos[self.jmap["right_knee"]] = max(0.05, 0.46 * math.sin(f + 1.1 + math.pi))
                    # Braceo cruzado
                    if "left_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_shoulder_pitch"]] = 0.20 + 0.32 * math.sin(f + math.pi)
                    if "right_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_pitch"]] = 0.20 + 0.32 * math.sin(f)
                    # Codos semi-flexionados
                    if "left_elbow" in self.jmap:
                        self.data.qpos[self.jmap["left_elbow"]] = 0.35 + 0.12 * math.sin(f + math.pi)
                    if "right_elbow" in self.jmap:
                        self.data.qpos[self.jmap["right_elbow"]] = 0.35 + 0.12 * math.sin(f)

                elif self.accion_locomocion == "girando":
                    self._fase_marcha = (self._fase_marcha + dt * 4.0) % (2.0 * math.pi)
                    f = self._fase_marcha
                    if "left_hip_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_hip_pitch"]] = 0.20 * math.sin(f)
                    if "right_hip_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_hip_pitch"]] = 0.20 * math.sin(f + math.pi)
                    if "left_knee" in self.jmap:
                        self.data.qpos[self.jmap["left_knee"]] = max(0.05, 0.24 * math.sin(f + 1.1))
                    if "right_knee" in self.jmap:
                        self.data.qpos[self.jmap["right_knee"]] = max(0.05, 0.24 * math.sin(f + 1.1 + math.pi))
                    if "waist_yaw" in self.jmap:
                        self.data.qpos[self.jmap["waist_yaw"]] = 0.18 * math.sin(f)

                elif self.accion_locomocion == "saludando":
                    if "right_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_pitch"]] = -1.75
                    if "right_shoulder_roll" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_roll"]] = -0.32
                    if "right_elbow" in self.jmap:
                        self.data.qpos[self.jmap["right_elbow"]] = 0.85
                    if "right_wrist_roll" in self.jmap:
                        self.data.qpos[self.jmap["right_wrist_roll"]] = 0.42 * math.sin(ahora * 8.0)
                    if "left_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_shoulder_pitch"]] = 0.42
                    if "left_elbow" in self.jmap:
                        self.data.qpos[self.jmap["left_elbow"]] = 0.28
                    # Dedos derechos abiertos y amigables
                    for d in ("index", "middle", "ring", "pinky"):
                        kd = f"right_hand_{d}"
                        if kd in self.jmap:
                            self.data.qpos[self.jmap[kd]] = 0.05

            # -------------------------------------------------------------
            #  3. MODO CONTINUO AFECTIVO + CAPAS VIVAS (BREATHING / SWAY / BEATS)
            # -------------------------------------------------------------
            else:
                # Interpolación suave hacia la pose base objetivo
                vel_lerp = dt * 6.5
                for art, val_obj in self._pose_base.items():
                    if art in self.jmap:
                        adr = self.jmap[art]
                        act = float(self.data.qpos[adr])
                        self.data.qpos[adr] = act + (val_obj - act) * min(1.0, vel_lerp)

                # Capa A: Co-speech Gestures si está hablando
                if self.hablando:
                    vel_onda = (3.0 + 1.2 * max(0.0, self.arousal)) * self.multiplicador_energia
                    self._fase_gesto = (self._fase_gesto + dt * vel_onda) % (2.0 * math.pi)
                    f = self._fase_gesto
                    amp_sh = (0.05 + 0.04 * max(0.0, self.arousal)) * self.multiplicador_energia
                    amp_el = (0.08 + 0.06 * max(0.0, self.arousal)) * self.multiplicador_energia

                    if "waist_pitch" in self.jmap:
                        self.data.qpos[self.jmap["waist_pitch"]] += 0.014 * self.multiplicador_energia * math.sin(f)
                    if "left_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_shoulder_pitch"]] += -amp_sh * math.sin(f + 0.35)
                    if "right_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_pitch"]] += -amp_sh * math.sin(f + 0.35 + 0.85)
                    if "left_elbow" in self.jmap:
                        self.data.qpos[self.jmap["left_elbow"]] += amp_el * math.cos(f + 0.80)
                    if "right_elbow" in self.jmap:
                        self.data.qpos[self.jmap["right_elbow"]] += amp_el * math.cos(f + 0.80 + 0.85)

                # Capa B: Respiración diafragmática viva (~4s)
                elif self.activar_respiracion:
                    f_resp = ahora * 1.57  # ~4.0 s ciclo
                    mod_torso = 0.035 * math.sin(f_resp)
                    mod_hombro = 0.025 * math.sin(f_resp + 0.25)
                    mod_codo = 0.020 * math.cos(f_resp)

                    if "waist_pitch" in self.jmap:
                        self.data.qpos[self.jmap["waist_pitch"]] += mod_torso
                    if "left_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["left_shoulder_pitch"]] += mod_hombro
                    if "right_shoulder_pitch" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_pitch"]] += mod_hombro
                    if "left_elbow" in self.jmap:
                        self.data.qpos[self.jmap["left_elbow"]] += mod_codo
                    if "right_elbow" in self.jmap:
                        self.data.qpos[self.jmap["right_elbow"]] += mod_codo

                # Capa C: Balanceo postural pendular y Contrapposto (~6.5s)
                if not self.hablando and self.activar_sway:
                    f_sway = ahora * 0.96  # ~6.5 s ciclo
                    sway_roll = 0.020 * math.sin(f_sway)
                    sway_yaw = 0.012 * math.cos(f_sway * 0.5)

                    if "waist_roll" in self.jmap:
                        self.data.qpos[self.jmap["waist_roll"]] += sway_roll
                    if "waist_yaw" in self.jmap:
                        self.data.qpos[self.jmap["waist_yaw"]] += sway_yaw
                    if "left_shoulder_roll" in self.jmap:
                        self.data.qpos[self.jmap["left_shoulder_roll"]] += -sway_roll * 0.5
                    if "right_shoulder_roll" in self.jmap:
                        self.data.qpos[self.jmap["right_shoulder_roll"]] += -sway_roll * 0.5

        # -------------------------------------------------------------
        #  CINEMÁTICA INVERSA Y GRAVEDAD NATURAL
        # -------------------------------------------------------------
        # 1. Altura Z dinámica: mantiene los pies pegados al piso según flexión de rodillas
        lk = float(self.data.qpos[self.jmap["left_knee"]]) if "left_knee" in self.jmap else 0.0
        rk = float(self.data.qpos[self.jmap["right_knee"]]) if "right_knee" in self.jmap else 0.0
        knee_avg = (lk + rk) / 2.0
        self.data.qpos[2] = 0.793 - (0.045 * knee_avg * knee_avg)

        # 2. Contrapeso de masa en X: retrasa caderas cuando el torso se inclina al frente
        wp = float(self.data.qpos[self.jmap["waist_pitch"]]) if "waist_pitch" in self.jmap else 0.0
        if wp > 0.03:
            self.data.qpos[0] = -0.16 * wp
        else:
            self.data.qpos[0] = 0.0

        # Actualizar telemetría de articulaciones
        self.lbl_tele_artics.config(
            text=f"Rodillas: L={lk:.2f} R={rk:.2f} | Torso Pitch: {wp:+.2f} | Altura Z: {self.data.qpos[2]:.3f}m | CoM X: {self.data.qpos[0]:+.3f}m"
        )

        # -------------------------------------------------------------
        #  RENDERIZADO MUJOCO Y ENVÍO A CANVAS
        # -------------------------------------------------------------
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, camera=self.camera)
        rgb = self.renderer.render()

        img_pil = Image.fromarray(rgb)
        self._photo_ref[0] = ImageTk.PhotoImage(image=img_pil)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo_ref[0])

        self.root.after(30, self.loop)

    def iniciar(self):
        self.root.after(10, self.loop)
        self.root.mainloop()


if __name__ == "__main__":
    app = VisorEstudio3DG1()
    app.iniciar()
