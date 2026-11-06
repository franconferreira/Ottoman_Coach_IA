# =====================================================================
#  Optimización Evolutiva mediante Algoritmos Genéticos (Clase 4/5 IA)
#  Ajuste Óptimo de Pesos y Umbrales del FusionadorMultimodal
#
#  Conceptos teóricos de la cátedra aplicados explícitamente:
#    - Cromosoma (Individuo): vector real de 11 genes en R^11.
#    - Gen / Locus / Alelo: cada posición codifica un peso de canal
#      (léxico, voz, cara) o un umbral biométrico de incongruencia.
#    - Fenotipo: instancia normalizada de ConfiguracionPesosFusion.
#    - Función de Aptitud (Fitness): combinación multiobjetivo de
#      F1-Macro emocional (65%), Recall de Incongruencia Afectiva (20%)
#      y precisión geométrica 1 - RMSE/2 en el plano Valencia-Arousal (15%).
#    - Operadores Evolutivos: Selección por Torneo (k=3), Cruza BLX-alpha
#      (Pc = 0.85), Mutación Gaussiana con decaimiento (Pm = 0.22) y
#      Elitismo estricto (top 3 individuos).
#
#  Ejecución directa:
#      python mi_desarrollo/algoritmo_genetico.py
# =====================================================================

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from percepcion_multimodal import (
    AnalizadorAcusticoVoz,
    AnalizadorFacial,
    ConfiguracionPesosFusion,
    FusionadorMultimodal,
    MetricasAcusticasVoz,
    MetricasFaciales,
)

DIR_ACTUAL = Path(__file__).resolve().parent
DIR_GRAFICOS = DIR_ACTUAL.parent / "docs" / "graficos"
RUTA_PESOS_JSON = DIR_ACTUAL / "pesos_fusion_ga.json"

CLASES_AFECTIVAS = (
    "ANSIEDAD_ESTRES",
    "TRISTEZA_DESANIMO",
    "ENOJO_FRUSTRACION",
    "DUDA_INSEGURIDAD",
    "MOTIVACION_ALEGRIA",
    "NEUTRO",
)

# Definición formal de los 11 loci del cromosoma: (nombre_gen, min_alelo, max_alelo)
ESQUEMA_CROMOSOMA: tuple[tuple[str, float, float], ...] = (
    ("w3_lexico", 0.05, 0.90),
    ("w3_voz", 0.05, 0.90),
    ("w3_cara", 0.05, 0.90),
    ("w2v_lexico", 0.10, 0.90),
    ("w2c_lexico", 0.10, 0.90),
    ("inc_lexico", 0.02, 0.75),
    ("inc_voz", 0.10, 0.90),
    ("inc_cara", 0.10, 0.90),
    ("umbral_cara_neg", -0.65, -0.10),
    ("umbral_voz_neg", -0.65, -0.10),
    ("umbral_voz_arousal", 0.25, 0.80),
)


@dataclass
class CasoMultimodalBenchmark:
    """Caso etiquetado con lecturas ruidosas de Cara + Voz + Texto y ground-truth."""
    texto: str
    facial: Optional[MetricasFaciales]
    acustica: Optional[MetricasAcusticasVoz]
    emocion_real: str
    valencia_real: float
    arousal_real: float
    es_incongruente: bool = False


def decodificar_cromosoma(genes: list[float] | np.ndarray) -> ConfiguracionPesosFusion:
    """Transforma el genotipo (vector real de 11 genes) en su fenotipo funcional."""
    valores = {}
    for idx, (nombre, vmin, vmax) in enumerate(ESQUEMA_CROMOSOMA):
        valores[nombre] = float(np.clip(genes[idx], vmin, vmax))
    return ConfiguracionPesosFusion(**valores).normalizado()


def codificar_configuracion(cfg: ConfiguracionPesosFusion) -> list[float]:
    """Convierte una ConfiguracionPesosFusion en su vector cromosómico."""
    d = asdict(cfg)
    return [float(d[nombre]) for nombre, _, _ in ESQUEMA_CROMOSOMA]


def generar_benchmark_multimodal(semilla: int = 42) -> list[CasoMultimodalBenchmark]:
    """Construye 180 escenarios multimodales con ruido realista y enmascaramiento."""
    rng = np.random.default_rng(semilla)
    casos: list[CasoMultimodalBenchmark] = []

    textos_por_clase = {
        "ANSIEDAD_ESTRES": [
            "No llego con los parciales, siento mucha ansiedad y presión",
            "Estoy desbordado de estrés con la entrega de hoy",
            "Tengo mil cosas encima y me falta el aire de los nervios",
            "Me agarra pánico pensar en el examen final de mañana",
            "Estoy re ansioso, siento que voy a colapsar",
            "Todo viene muy rápido esta semana, no doy más",
        ],
        "TRISTEZA_DESANIMO": [
            "Me siento muy triste y sin fuerzas para seguir",
            "Hoy tuve un bajón enorme, tengo ganas de abandonar",
            "Estoy agotado y decepcionado porque me salió todo mal",
            "Me siento solo y vacío después de haber desaprobado",
            "No tengo ganas de nada hoy, estoy re desanimado",
            "Fue una semana pesada, vengo muy apagado",
        ],
        "ENOJO_FRUSTRACION": [
            "Estoy harto y con mucha bronca porque nada funciona",
            "Me da rabia e impotencia que se trabe el proyecto",
            "Estoy furioso por lo injusto que fue todo hoy",
            "Es insoportable trabajar así, estoy re irritado",
            "Me saca de quicio renegar diez veces con lo mismo",
            "Qué bronca bárbara, otra vez se rompió la conexión",
        ],
        "DUDA_INSEGURIDAD": [
            "No sé qué decisión tomar con la tesis, tengo dudas",
            "Estoy inseguro y tengo miedo a equivocarme en la defensa",
            "Me cuesta decidir qué camino elegir en el trabajo",
            "Tengo síndrome del impostor y dudo de mi nivel",
            "Estoy confundido entre las dos opciones del proyecto",
            "No me animo a exponer mi propuesta todavía",
        ],
        "MOTIVACION_ALEGRIA": [
            "¡Aprobé la materia, estoy súper feliz y orgulloso!",
            "Me salió increíble la demo del robot, qué alegría",
            "Estoy re motivado y entusiasmado con el equipo",
            "¡Lo logré, pude resolver el problema más difícil!",
            "Estoy re contento porque nos felicitaron en clase",
            "Qué lindo día, salió todo redondo en el laboratorio",
        ],
        "NEUTRO": [
            "La clase empieza a las seis y media en el aula",
            "El archivo quedó guardado en la carpeta principal",
            "Hoy es jueves y tenemos práctica en el laboratorio",
            "El cable de red está conectado sobre el escritorio",
            "Ya revisé el cronograma de fechas del cuatrimestre",
            "La notebook tiene el cargador enchufado en la pared",
        ],
    }

    frases_mascara = [
        "Tranqui, estoy bien, no pasa nada.",
        "Todo bien por suerte, nada grave.",
        "Normal, estoy tranqui hoy.",
        "No pasa nada, está todo bien.",
    ]

    # Prototipos biométricos (cara y voz) + coordenadas reales Russell (V, A)
    prototipos = {
        "ANSIEDAD_ESTRES": {
            "va": (-0.62, +0.76),
            "cara": (0.82, 0.50, -0.14, 0.28, 2.0, 0.65),
            "voz": (222.0, 32.0, -15.5, 196.0, 0.09, 0.35),
        },
        "TRISTEZA_DESANIMO": {
            "va": (-0.72, -0.62),
            "cara": (0.28, 0.26, -0.52, 0.10, 11.0, 0.05),
            "voz": (116.0, 9.0, -29.5, 96.0, 0.44, 0.14),
        },
        "ENOJO_FRUSTRACION": {
            "va": (-0.70, +0.78),
            "cara": (0.72, 0.82, -0.24, 0.52, 1.0, 0.55),
            "voz": (196.0, 27.0, -10.2, 178.0, 0.12, 0.72),
        },
        "DUDA_INSEGURIDAD": {
            "va": (-0.26, +0.08),
            "cara": (0.54, 0.46, -0.06, 0.14, 11.5, 0.15),
            "voz": (156.0, 16.0, -21.0, 128.0, 0.43, 0.22),
        },
        "MOTIVACION_ALEGRIA": {
            "va": (+0.76, +0.58),
            "cara": (0.76, 0.14, +0.72, 0.34, 2.0, 0.30),
            "voz": (184.0, 29.0, -14.8, 172.0, 0.15, 0.34),
        },
        "NEUTRO": {
            "va": (0.00, 0.00),
            "cara": (0.48, 0.20, 0.02, 0.12, 1.5, 0.04),
            "voz": (155.0, 15.0, -20.5, 144.0, 0.22, 0.25),
        },
    }

    def _muestrear_cara(emo: str, escala_ruido: float = 1.0) -> MetricasFaciales:
        ap_o, ten_c, cur_b, ap_b, inc_c, agit = prototipos[emo]["cara"]
        return AnalizadorFacial.clasificar_desde_rasgos(
            apertura_ojos=float(np.clip(ap_o + rng.normal(0, 0.06 * escala_ruido), 0.15, 1.0)),
            tension_cejas=float(np.clip(ten_c + rng.normal(0, 0.07 * escala_ruido), 0.0, 1.0)),
            curvatura_boca=float(np.clip(cur_b + rng.normal(0, 0.08 * escala_ruido), -1.0, 1.0)),
            apertura_boca=float(np.clip(ap_b + rng.normal(0, 0.05 * escala_ruido), 0.05, 1.0)),
            inclinacion_cabeza_deg=float(np.clip(inc_c + rng.normal(0, 2.2 * escala_ruido), -25.0, 25.0)),
            agitacion_movimiento=float(np.clip(agit + rng.normal(0, 0.08 * escala_ruido), 0.0, 1.0)),
        )

    def _muestrear_voz(emo: str, escala_ruido: float = 1.0) -> MetricasAcusticasVoz:
        f0, var_f0, vol, wpm, pausas, ataque = prototipos[emo]["voz"]
        return AnalizadorAcusticoVoz.clasificar_desde_prosodia(
            tono_f0_hz=float(np.clip(f0 + rng.normal(0, 9.0 * escala_ruido), 85.0, 320.0)),
            variabilidad_tono_hz=float(np.clip(var_f0 + rng.normal(0, 3.0 * escala_ruido), 5.0, 55.0)),
            volumen_db=float(np.clip(vol + rng.normal(0, 1.8 * escala_ruido), -42.0, -4.0)),
            rapidez_wpm=float(np.clip(wpm + rng.normal(0, 10.0 * escala_ruido), 70.0, 240.0)),
            ratio_pausas=float(np.clip(pausas + rng.normal(0, 0.04 * escala_ruido), 0.04, 0.65)),
            ataque_energia=float(np.clip(ataque + rng.normal(0, 0.06 * escala_ruido), 0.05, 0.95)),
        )

    # 1. 120 casos multimodales congruentes y semi-ruidosos (20 por cada una de las 6 clases)
    for emo in CLASES_AFECTIVAS:
        v_gt, a_gt = prototipos[emo]["va"]
        frases = textos_por_clase[emo]
        for i in range(20):
            txt = frases[i % len(frases)]
            modo = i % 5
            if modo in (0, 1, 2):
                # 3 canales activos; en modo==2 un sensor tiene ruido elevado o distracción
                fac = _muestrear_cara("NEUTRO" if (modo == 2 and emo != "NEUTRO" and i % 2 == 0) else emo, 1.2)
                acu = _muestrear_voz("NEUTRO" if (modo == 2 and emo != "NEUTRO" and i % 2 == 1) else emo, 1.2)
            elif modo == 3:
                # 2 canales: texto + voz (sin cámara)
                fac = None
                acu = _muestrear_voz(emo, 1.0)
            else:
                # 2 canales: texto + cara (micrófono ambiente no disponible)
                fac = _muestrear_cara(emo, 1.0)
                acu = None

            casos.append(
                CasoMultimodalBenchmark(
                    texto=txt,
                    facial=fac,
                    acustica=acu,
                    emocion_real=emo,
                    valencia_real=v_gt,
                    arousal_real=a_gt,
                    es_incongruente=False,
                )
            )

    # 2. 45 casos de Enmascaramiento / Incongruencia Afectiva ("Estoy bien" + cuerpo mal)
    emociones_ocultas = ("TRISTEZA_DESANIMO", "ANSIEDAD_ESTRES", "ENOJO_FRUSTRACION")
    for idx_m in range(45):
        emo_oculta = emociones_ocultas[idx_m % len(emociones_ocultas)]
        v_gt, a_gt = prototipos[emo_oculta]["va"]
        txt = frases_mascara[idx_m % len(frases_mascara)]
        submodo = idx_m % 5
        if submodo in (0, 1, 2):
            fac = _muestrear_cara(emo_oculta, 0.9)
            acu = _muestrear_voz(emo_oculta, 0.9)
        elif submodo == 3:
            fac = None
            acu = _muestrear_voz(emo_oculta, 0.85)
        else:
            fac = _muestrear_cara(emo_oculta, 0.85)
            acu = None

        casos.append(
            CasoMultimodalBenchmark(
                texto=txt,
                facial=fac,
                acustica=acu,
                emocion_real=emo_oculta,
                valencia_real=v_gt,
                arousal_real=a_gt,
                es_incongruente=True,
            )
        )

    # 3. 15 casos de frases ambiguas cortas donde la biometría define la emoción real
    frases_ambiguas = [
        "No sé cómo explicar lo que pasó recién en la entrega",
        "Acabo de ver las notas publicadas en el campus",
        "Tenemos que hablar sobre lo que ocurrió en la reunión",
    ]
    for idx_a in range(15):
        emo_real = CLASES_AFECTIVAS[idx_a % 5]  # Las 5 emociones activas
        v_gt, a_gt = prototipos[emo_real]["va"]
        txt = frases_ambiguas[idx_a % len(frases_ambiguas)]
        casos.append(
            CasoMultimodalBenchmark(
                texto=txt,
                facial=_muestrear_cara(emo_real, 0.85),
                acustica=_muestrear_voz(emo_real, 0.85),
                emocion_real=emo_real,
                valencia_real=v_gt,
                arousal_real=a_gt,
                es_incongruente=(emo_real in emociones_ocultas),
            )
        )

    return casos


def evaluar_configuracion(
    cfg: ConfiguracionPesosFusion,
    benchmark: list[CasoMultimodalBenchmark],
) -> dict:
    """Calcula el Fitness y las métricas detalladas de un fenotipo sobre el benchmark."""
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    fusionador = FusionadorMultimodal(config_pesos=cfg, cargar_ga=False)

    y_true: list[str] = []
    y_pred: list[str] = []
    errores_cuad: list[float] = []
    incong_reales = 0
    incong_detectadas = 0
    falsas_incong = 0
    congruentes_reales = 0

    for caso in benchmark:
        est = fusionador.fusionar(caso.texto, facial=caso.facial, acustica=caso.acustica)
        y_true.append(caso.emocion_real)
        y_pred.append(est.emocion_dominante)

        err_v = est.valencia - caso.valencia_real
        err_a = est.arousal - caso.arousal_real
        errores_cuad.append(0.5 * (err_v * err_v + err_a * err_a))

        if caso.es_incongruente:
            incong_reales += 1
            if est.incongruencia_detectada and est.emocion_dominante == caso.emocion_real:
                incong_detectadas += 1
        else:
            congruentes_reales += 1
            if est.incongruencia_detectada and caso.emocion_real == "NEUTRO":
                falsas_incong += 1

    acc = float(accuracy_score(y_true, y_pred))
    f1_macro = float(f1_score(y_true, y_pred, labels=list(CLASES_AFECTIVAS), average="macro", zero_division=0))
    rmse_va = math.sqrt(float(np.mean(errores_cuad)))
    recall_incong = incong_detectadas / max(1, incong_reales)
    penalizacion_fp = falsas_incong / max(1, congruentes_reales)

    # Función de Aptitud (Fitness) acotada en [0, 1]
    precision_va = max(0.0, 1.0 - rmse_va / 1.5)
    fitness = (
        0.62 * f1_macro
        + 0.23 * recall_incong
        + 0.15 * precision_va
        - 0.12 * penalizacion_fp
    )
    fitness = float(np.clip(fitness, 0.0, 1.0))

    matriz = confusion_matrix(y_true, y_pred, labels=list(CLASES_AFECTIVAS))
    return {
        "fitness": fitness,
        "accuracy": acc,
        "f1_macro": f1_macro,
        "recall_incongruencia": recall_incong,
        "rmse_va": rmse_va,
        "matriz_confusion": matriz,
        "y_true": y_true,
        "y_pred": y_pred,
    }


class OptimizadorGeneticoMultimodal:
    """Motor evolutivo completo (Selección por Torneo + Cruza BLX-α + Mutación + Elitismo)."""

    def __init__(
        self,
        tam_poblacion: int = 60,
        generaciones: int = 50,
        prob_cruza: float = 0.85,
        prob_mutacion: float = 0.22,
        tam_torneo: int = 3,
        elitismo: int = 3,
        semilla: int = 42,
    ):
        self.tam_poblacion = tam_poblacion
        self.generaciones = generaciones
        self.prob_cruza = prob_cruza
        self.prob_mutacion = prob_mutacion
        self.tam_torneo = tam_torneo
        self.elitismo = elitismo
        self.rng = random.Random(semilla)
        self.np_rng = np.random.default_rng(semilla)

    def _individuo_aleatorio(self) -> list[float]:
        return [
            self.rng.uniform(vmin, vmax)
            for _, vmin, vmax in ESQUEMA_CROMOSOMA
        ]

    def _seleccion_torneo(self, poblacion: list[list[float]], aptitudes: list[float]) -> list[float]:
        indices = self.rng.sample(range(len(poblacion)), self.tam_torneo)
        mejor_idx = max(indices, key=lambda idx: aptitudes[idx])
        return list(poblacion[mejor_idx])

    def _cruza_blx_alfa(
        self, padre1: list[float], padre2: list[float], alfa: float = 0.35
    ) -> tuple[list[float], list[float]]:
        if self.rng.random() > self.prob_cruza:
            return list(padre1), list(padre2)

        hijo1, hijo2 = [], []
        for idx, (_, vmin, vmax) in enumerate(ESQUEMA_CROMOSOMA):
            cmin = min(padre1[idx], padre2[idx])
            cmax = max(padre1[idx], padre2[idx])
            rango = cmax - cmin
            bajo = max(vmin, cmin - alfa * rango)
            alto = min(vmax, cmax + alfa * rango)
            hijo1.append(self.rng.uniform(bajo, alto))
            hijo2.append(self.rng.uniform(bajo, alto))
        return hijo1, hijo2

    def _mutar(self, individuo: list[float], progreso_gen: float) -> list[float]:
        mutado = list(individuo)
        # El desvío de mutación disminuye suavemente hacia el final para ajuste fino
        escala = 0.16 * (1.0 - 0.55 * progreso_gen)
        for idx, (_, vmin, vmax) in enumerate(ESQUEMA_CROMOSOMA):
            if self.rng.random() < self.prob_mutacion:
                sigma = (vmax - vmin) * escala
                mutado[idx] = float(np.clip(mutado[idx] + self.rng.gauss(0.0, sigma), vmin, vmax))
        return mutado

    def evolucionar(self, benchmark: list[CasoMultimodalBenchmark]) -> dict:
        poblacion = [self._individuo_aleatorio() for _ in range(self.tam_poblacion)]

        historial_mejor: list[float] = []
        historial_media: list[float] = []
        historial_std: list[float] = []

        mejor_global_genes: list[float] = list(poblacion[0])
        mejor_global_eval: Optional[dict] = None

        for gen in range(self.generaciones):
            evaluaciones = [
                evaluar_configuracion(decodificar_cromosoma(ind), benchmark)
                for ind in poblacion
            ]
            aptitudes = [ev["fitness"] for ev in evaluaciones]

            orden = sorted(range(len(poblacion)), key=lambda i: aptitudes[i], reverse=True)
            mejor_gen_idx = orden[0]

            if mejor_global_eval is None or aptitudes[mejor_gen_idx] > mejor_global_eval["fitness"]:
                mejor_global_genes = list(poblacion[mejor_gen_idx])
                mejor_global_eval = evaluaciones[mejor_gen_idx]

            historial_mejor.append(float(aptitudes[mejor_gen_idx]))
            historial_media.append(float(np.mean(aptitudes)))
            historial_std.append(float(np.std(aptitudes)))

            if gen == self.generaciones - 1:
                break

            progreso = gen / max(1, self.generaciones - 1)
            # Elitismo: los mejores individuos pasan intactos a la siguiente generación
            nueva_poblacion = [list(poblacion[i]) for i in orden[: self.elitismo]]

            while len(nueva_poblacion) < self.tam_poblacion:
                p1 = self._seleccion_torneo(poblacion, aptitudes)
                p2 = self._seleccion_torneo(poblacion, aptitudes)
                h1, h2 = self._cruza_blx_alfa(p1, p2)
                nueva_poblacion.append(self._mutar(h1, progreso))
                if len(nueva_poblacion) < self.tam_poblacion:
                    nueva_poblacion.append(self._mutar(h2, progreso))

            poblacion = nueva_poblacion

        mejor_cfg = decodificar_cromosoma(mejor_global_genes)
        return {
            "mejor_config": mejor_cfg,
            "mejor_eval": mejor_global_eval,
            "historial_mejor": historial_mejor,
            "historial_media": historial_media,
            "historial_std": historial_std,
        }


def guardar_graficos_ga(
    resultado_ga: dict,
    eval_ingenuo: dict,
    cfg_ingenuo: ConfiguracionPesosFusion,
    eval_manual: dict,
) -> list[Path]:
    """Genera los gráficos de evolución de fitness, pesos optimizados y matriz de confusión."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []

    gens = np.arange(1, len(resultado_ga["historial_mejor"]) + 1)
    mejor = np.array(resultado_ga["historial_mejor"]) * 100.0
    media = np.array(resultado_ga["historial_media"]) * 100.0
    std = np.array(resultado_ga["historial_std"]) * 100.0

    # 1. Evolución de la Función de Aptitud (Fitness) por Generación
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=180)
    ax.plot(gens, mejor, color="#0284C7", linewidth=2.6, label="Mejor Individuo (Élite AG)")
    ax.plot(gens, media, color="#10B981", linewidth=2.0, linestyle="--", label="Aptitud Promedio de la Población")
    ax.fill_between(
        gens,
        np.clip(media - std, 0, 100),
        np.clip(media + std, 0, 100),
        color="#10B981",
        alpha=0.16,
        label="Dispersión Poblacional (±1σ)",
    )
    ax.axhline(
        eval_manual["fitness"] * 100.0,
        color="#F59E0B",
        linestyle=":",
        linewidth=1.9,
        label=f"Heurística Manual Base ({eval_manual['fitness']*100:.1f}%)",
    )
    ax.axhline(
        eval_ingenuo["fitness"] * 100.0,
        color="#EF4444",
        linestyle="-.",
        linewidth=1.7,
        label=f"Baseline Léxico Sin Calibrar ({eval_ingenuo['fitness']*100:.1f}%)",
    )
    ax.set_title(
        "Evolución del Algoritmo Genético — Optimización de Fusión Multimodal (N=60, G=50)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Generación Evolutiva", fontsize=10.5)
    ax.set_ylabel("Aptitud / Fitness Global (%)", fontsize=10.5)
    ax.grid(True, linestyle="--", alpha=0.32)
    ax.legend(loc="lower right", frameon=True, fontsize=9)
    ax.set_xlim(1, len(gens))
    fig.tight_layout()
    ruta_fit = DIR_GRAFICOS / "ga_evolucion_fitness.png"
    fig.savefig(ruta_fit)
    plt.close(fig)
    rutas.append(ruta_fit)

    # 2. Comparación de Pesos Optimizados vs Baseline Sin Calibrar
    cfg_opt: ConfiguracionPesosFusion = resultado_ga["mejor_config"]
    etiquetas_p = [
        "Léxico\n(3 Canales)",
        "Voz DSP\n(3 Canales)",
        "Cara FACS\n(3 Canales)",
        "Léxico\n(Enmascaram.)",
        "Voz DSP\n(Enmascaram.)",
        "Cara FACS\n(Enmascaram.)",
    ]
    vals_base = [
        cfg_ingenuo.w3_lexico,
        cfg_ingenuo.w3_voz,
        cfg_ingenuo.w3_cara,
        cfg_ingenuo.inc_lexico,
        cfg_ingenuo.inc_voz,
        cfg_ingenuo.inc_cara,
    ]
    vals_opt = [
        cfg_opt.w3_lexico,
        cfg_opt.w3_voz,
        cfg_opt.w3_cara,
        cfg_opt.inc_lexico,
        cfg_opt.inc_voz,
        cfg_opt.inc_cara,
    ]

    x = np.arange(len(etiquetas_p))
    ancho = 0.36
    fig, ax = plt.subplots(figsize=(9.5, 5.0), dpi=180)
    b1 = ax.bar(x - ancho / 2, vals_base, ancho, label="Baseline Léxico No Optimizado", color="#94A3B8")
    b2 = ax.bar(x + ancho / 2, vals_opt, ancho, label="Cromosoma Óptimo Evolucionado (AG)", color="#0EA5E9")
    for barras in (b1, b2):
        for rect in barras:
            h = rect.get_height()
            ax.annotate(
                f"{h:.2f}",
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
            )
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas_p, fontsize=9.5)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Peso Normalizado del Canal Sensorial", fontsize=10.5)
    ax.set_title(
        "Pesos del FusionadorMultimodal: Baseline vs. Cromosoma Evolucionado (AG)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.32)
    ax.legend(frameon=True, fontsize=9.5)
    fig.tight_layout()
    ruta_pesos = DIR_GRAFICOS / "ga_pesos_optimizados.png"
    fig.savefig(ruta_pesos)
    plt.close(fig)
    rutas.append(ruta_pesos)

    # 3. Matriz de Confusión del FusionadorMultimodal Optimizado
    mat = resultado_ga["mejor_eval"]["matriz_confusion"]
    nombres_cortos = ["Ansiedad", "Tristeza", "Enojo", "Duda", "Alegría", "Neutro"]
    fig, ax = plt.subplots(figsize=(7.6, 6.4), dpi=180)
    im = ax.imshow(mat, cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(np.arange(len(nombres_cortos)))
    ax.set_yticks(np.arange(len(nombres_cortos)))
    ax.set_xticklabels(nombres_cortos, rotation=30, ha="right", fontsize=9.5)
    ax.set_yticklabels(nombres_cortos, fontsize=9.5)
    ax.set_xlabel("Emoción Predicha por FusionadorMultimodal (AG)", fontsize=10.5, fontweight="bold")
    ax.set_ylabel("Emoción Real (Ground-Truth Multimodal)", fontsize=10.5, fontweight="bold")
    ax.set_title(
        f"Matriz de Confusión Multimodal Post-AG (Accuracy: {resultado_ga['mejor_eval']['accuracy']*100:.1f}%)",
        fontsize=11.5,
        fontweight="bold",
        pad=12,
    )
    umbral_txt = mat.max() * 0.55
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(
                j,
                i,
                str(mat[i, j]),
                ha="center",
                va="center",
                color="white" if mat[i, j] > umbral_txt else "#0F172A",
                fontsize=10,
                fontweight="bold",
            )
    fig.tight_layout()
    ruta_cm = DIR_GRAFICOS / "matriz_confusion_multimodal.png"
    fig.savefig(ruta_cm)
    plt.close(fig)
    rutas.append(ruta_cm)

    return rutas


def main() -> int:
    print("\n" + "=" * 78)
    print("  ALGORITMO GENÉTICO — OPTIMIZACIÓN DE FUSIÓN MULTIMODAL (OTTOMAN COACH)")
    print("=" * 78)

    benchmark = generar_benchmark_multimodal(semilla=42)
    print(f"  Benchmark Multimodal generado: {len(benchmark)} escenarios con ruido sensorial")
    print(f"  Casos con Enmascaramiento Afectivo ('estoy bien' + biometría alterada): "
          f"{sum(1 for c in benchmark if c.es_incongruente)}")

    # 1. Evaluar Baseline Léxico No Calibrado (prioriza casi solo palabras)
    cfg_ingenuo = ConfiguracionPesosFusion(
        w3_lexico=0.82, w3_voz=0.09, w3_cara=0.09,
        w2v_lexico=0.82, w2c_lexico=0.82,
        inc_lexico=0.72, inc_voz=0.14, inc_cara=0.14,
        umbral_cara_neg=-0.58, umbral_voz_neg=-0.60, umbral_voz_arousal=0.75,
    ).normalizado()
    eval_ingenuo = evaluar_configuracion(cfg_ingenuo, benchmark)

    # 2. Evaluar Heurística Manual Inicial
    cfg_manual = ConfiguracionPesosFusion(
        w3_lexico=0.55, w3_voz=0.25, w3_cara=0.20,
        w2v_lexico=0.62, w2c_lexico=0.65,
        inc_lexico=0.35, inc_voz=0.35, inc_cara=0.30,
        umbral_cara_neg=-0.35, umbral_voz_neg=-0.42, umbral_voz_arousal=0.58,
    ).normalizado()
    eval_manual = evaluar_configuracion(cfg_manual, benchmark)

    # 3. Ejecutar Evolución Genética (N=60 individuos, G=50 generaciones)
    ga = OptimizadorGeneticoMultimodal(
        tam_poblacion=60,
        generaciones=50,
        prob_cruza=0.85,
        prob_mutacion=0.22,
        tam_torneo=3,
        elitismo=3,
        semilla=42,
    )
    resultado = ga.evolucionar(benchmark)
    mejor_cfg: ConfiguracionPesosFusion = resultado["mejor_config"]
    mejor_ev: dict = resultado["mejor_eval"]

    print("\n  " + "-" * 74)
    print(f"  {'Configuración':<34} {'Fitness':>9} {'Acc':>8} {'F1-Mac':>8} {'Incong':>8} {'RMSE':>7}")
    print("  " + "-" * 74)
    for nombre, ev in (
        ("Baseline Léxico (Sin Calibrar)", eval_ingenuo),
        ("Heurística Manual Inicial", eval_manual),
        ("Cromosoma Evolucionado (AG)", mejor_ev),
    ):
        print(
            f"  {nombre:<34} "
            f"{ev['fitness']*100:>8.2f}% "
            f"{ev['accuracy']*100:>7.1f}% "
            f"{ev['f1_macro']*100:>7.1f}% "
            f"{ev['recall_incongruencia']*100:>7.1f}% "
            f"{ev['rmse_va']:>7.3f}"
        )
    print("  " + "-" * 74)

    # Guardar pesos evolucionados en JSON para que FusionadorMultimodal los cargue automáticamente
    datos_salida = {
        "algoritmo": "Algoritmo Genético de Codificación Real (BLX-alpha + Torneo k=3 + Elitismo)",
        "poblacion": 60,
        "generaciones": 50,
        "benchmark_casos": len(benchmark),
        "pesos_optimizados": asdict(mejor_cfg),
        "metricas_ga": {
            "fitness": round(mejor_ev["fitness"], 4),
            "accuracy": round(mejor_ev["accuracy"], 4),
            "f1_macro": round(mejor_ev["f1_macro"], 4),
            "recall_incongruencia": round(mejor_ev["recall_incongruencia"], 4),
            "rmse_valencia_arousal": round(mejor_ev["rmse_va"], 4),
        },
        "metricas_baseline_ingenuo": {
            "fitness": round(eval_ingenuo["fitness"], 4),
            "accuracy": round(eval_ingenuo["accuracy"], 4),
            "f1_macro": round(eval_ingenuo["f1_macro"], 4),
            "recall_incongruencia": round(eval_ingenuo["recall_incongruencia"], 4),
        },
        "metricas_heuristica_manual": {
            "fitness": round(eval_manual["fitness"], 4),
            "accuracy": round(eval_manual["accuracy"], 4),
            "f1_macro": round(eval_manual["f1_macro"], 4),
            "recall_incongruencia": round(eval_manual["recall_incongruencia"], 4),
        },
    }
    RUTA_PESOS_JSON.write_text(json.dumps(datos_salida, indent=2, ensure_ascii=False), encoding="utf-8")
    rutas = guardar_graficos_ga(resultado, eval_ingenuo, cfg_ingenuo, eval_manual)

    print(f"\n  [OK] Cromosoma óptimo persistido en: {RUTA_PESOS_JSON.name}")
    for r in rutas:
        print(f"  [OK] Gráfico generado: docs/graficos/{r.name}")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
