"""Percepción Multimodal Afectiva: Cara (Computer Vision) + Voz (DSP Acústico) + Léxico.

Este módulo implementa los sensores afectivos del Agente Inteligente Ottoman Coach:
  1. AnalizadorFacial: Visión por computadora (OpenCV FACS geométrico + gradientes)
     para estimar apertura ocular, tensión de cejas, curvatura de boca, inclinación
     cefálica y agitación motora.
  2. AnalizadorAcusticoVoz: Procesamiento digital de señales (DSP con NumPy) sobre el
     audio crudo del micrófono para extraer Tonalidad (F0 en Hz por autocorrelación),
     Intensidad (Volumen RMS en dBFS), Rapidez de habla (WPM efectivas con VAD) y
     proporción de pausas.
  3. AnalizadorLexicoAfectivo: Análisis psicolingüístico y paralingüístico del texto
     en español rioplatense.
  4. FusionadorMultimodal: Proyecta los 3 canales en el Modelo Circumplejo de Russell
     (Valencia x Arousal) y detecta Incongruencia Emocional (enmascaramiento afectivo,
     por ejemplo decir "estoy bien" con cara triste y voz apagada).
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np


def normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas sin tildes conservando signos relevantes."""
    texto_nfd = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto_nfd if unicodedata.category(c) != "Mn")


# =====================================================================
#  ESTRUCTURAS DE DATOS BIOMÉTRICAS Y AFECTIVAS
# =====================================================================

@dataclass
class MetricasFaciales:
    """ Lectura instantánea o promediada del rostro de la persona."""
    rostro_detectado: bool = False
    apertura_ojos: float = 0.5          # 0.0 (cerrados/caídos) .. 1.0 (muy abiertos)
    tension_cejas: float = 0.2          # 0.0 (relajadas) .. 1.0 (ceño muy fruncido)
    curvatura_boca: float = 0.0         # -1.0 (comisuras caídas) .. +1.0 (sonrisa)
    apertura_boca: float = 0.1          # 0.0 (cerrada) .. 1.0 (abierta/grito)
    inclinacion_cabeza_deg: float = 0.0 # grados de ladeo cefálico
    agitacion_movimiento: float = 0.0   # 0.0 (estático) .. 1.0 (inquieto/ansioso)
    emocion_facial: str = "NEUTRO"
    valencia_facial: float = 0.0        # -1.0 .. +1.0
    arousal_facial: float = 0.0         # -1.0 .. +1.0
    confianza: float = 0.0


@dataclass
class MetricasAcusticasVoz:
    """Parámetros paralingüísticos y prosódicos medidos de la voz del usuario."""
    audio_analizado: bool = False
    tono_f0_hz: float = 155.0           # Frecuencia fundamental promedio (Hz)
    variabilidad_tono_hz: float = 18.0  # Desviación estándar de F0 (Hz)
    volumen_db: float = -20.0           # Energía RMS en dBFS (-60 a 0 dB)
    rapidez_wpm: float = 145.0          # Palabras por minuto en voz activa
    ratio_pausas: float = 0.20          # Fracción de silencio interno (0.0 a 1.0)
    ataque_energia: float = 0.30        # Brusquedad de fonación (0.0 suave .. 1.0 brusco)
    emocion_vocal: str = "NEUTRO"
    valencia_vocal: float = 0.0         # -1.0 .. +1.0
    arousal_vocal: float = 0.0          # -1.0 .. +1.0
    confianza: float = 0.0


@dataclass
class ResultadoLexico:
    """Análisis semántico y emocional del texto dicho o escrito."""
    emocion_lexica: str = "NEUTRO"
    valencia_lexica: float = 0.0
    arousal_lexico: float = 0.0
    intensidad_lexica: float = 0.0
    es_crisis_etica: bool = False
    palabras_clave: list[str] = field(default_factory=list)
    es_expresion_emocional: bool = False


@dataclass
class EstadoAfectivoUsuario:
    """Estado emocional integrado a partir de Cara + Voz + Léxico."""
    emocion_dominante: str = "NEUTRO"
    valencia: float = 0.0               # -1.0 (muy negativo) .. +1.0 (muy positivo)
    arousal: float = 0.0                # -1.0 (apagado/calmo) .. +1.0 (alta activación)
    intensidad: float = 0.5             # 0.0 .. 1.0
    confianza: float = 0.7
    es_crisis_etica: bool = False
    incongruencia_detectada: bool = False
    detalle_incongruencia: str = ""
    canales_activos: list[str] = field(default_factory=lambda: ["lexico"])
    facial: MetricasFaciales = field(default_factory=MetricasFaciales)
    acustica: MetricasAcusticasVoz = field(default_factory=MetricasAcusticasVoz)
    lexico: ResultadoLexico = field(default_factory=ResultadoLexico)

    def a_dict(self) -> dict:
        return asdict(self)


# =====================================================================
#  1. ANALIZADOR FACIAL (COMPUTER VISION - CLASE 11 IA)
# =====================================================================

class AnalizadorFacial:
    """Extrae unidades de acción facial (FACS aproximadas) con OpenCV."""

    def __init__(self, indice_camara: int = 0):
        self.indice_camara = indice_camara
        self._cap = None
        self._centro_previo: Optional[tuple[float, float]] = None
        self._face_cascade = None
        self._eye_cascade = None
        self._smile_cascade = None
        self._inicializar_cascadas()

    def _inicializar_cascadas(self) -> None:
        try:
            import cv2
            base = cv2.data.haarcascades
            self._face_cascade = cv2.CascadeClassifier(
                base + "haarcascade_frontalface_default.xml"
            )
            self._eye_cascade = cv2.CascadeClassifier(
                base + "haarcascade_eye.xml"
            )
            self._smile_cascade = cv2.CascadeClassifier(
                base + "haarcascade_smile.xml"
            )
        except Exception:
            self._face_cascade = None

    def abrir_camara(self) -> bool:
        """Abre la cámara web local si está disponible."""
        if self._cap is not None and self._cap.isOpened():
            return True
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.indice_camara)
            return bool(self._cap.isOpened())
        except Exception:
            self._cap = None
            return False

    def cerrar_camara(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def analizar_frame(self, frame_bgr: np.ndarray, dibujar_hud: bool = False) -> tuple[MetricasFaciales, np.ndarray]:
        """Analiza un frame BGR y estima expresión facial, valencia y arousal."""
        if frame_bgr is None or frame_bgr.size == 0:
            return MetricasFaciales(rostro_detectado=False), frame_bgr

        try:
            import cv2
        except ImportError:
            return MetricasFaciales(rostro_detectado=False), frame_bgr

        salida = frame_bgr.copy() if dibujar_hud else frame_bgr
        gris = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gris_eq = cv2.equalizeHist(gris)

        caras = []
        if self._face_cascade is not None:
            caras = self._face_cascade.detectMultiScale(
                gris_eq, scaleFactor=1.12, minNeighbors=5, minSize=(70, 70)
            )

        if len(caras) == 0:
            return MetricasFaciales(rostro_detectado=False), salida

        # Seleccionar el rostro principal (mayor área)
        x, y, w, h = max(caras, key=lambda r: r[2] * r[3])
        roi_gris = gris_eq[y : y + h, x : x + w]

        # 1. Agitación motora e inclinación aproximada
        cx, cy = x + w * 0.5, y + h * 0.5
        agitacion = 0.0
        if self._centro_previo is not None:
            dist = math.hypot(cx - self._centro_previo[0], cy - self._centro_previo[1])
            agitacion = float(np.clip(dist / max(1.0, w * 0.12), 0.0, 1.0))
        self._centro_previo = (cx, cy)

        # 2. Región ocular superior (apertura de ojos e inclinación entre ojos)
        mitad_sup = roi_gris[int(h * 0.18) : int(h * 0.55), :]
        ojos = []
        if self._eye_cascade is not None and mitad_sup.size > 0:
            ojos = self._eye_cascade.detectMultiScale(
                mitad_sup, scaleFactor=1.1, minNeighbors=4, minSize=(int(w * 0.12), int(h * 0.08))
            )

        inclinacion_deg = 0.0
        if len(ojos) >= 2:
            ojos_ord = sorted(ojos, key=lambda o: o[0])[:2]
            (ex1, ey1, ew1, eh1), (ex2, ey2, ew2, eh2) = ojos_ord
            apertura_ojos = float(np.clip(((eh1 + eh2) * 0.5) / max(1.0, h * 0.20), 0.15, 1.0))
            dx = (ex2 + ew2 * 0.5) - (ex1 + ew1 * 0.5)
            dy = (ey2 + eh2 * 0.5) - (ey1 + eh1 * 0.5)
            if abs(dx) > 5:
                inclinacion_deg = float(np.clip(math.degrees(math.atan2(dy, dx)), -30.0, 30.0))
        else:
            # Estimación por varianza vertical en banda ocular cuando los párpados caen
            contraste_ocular = float(np.std(mitad_sup)) / 75.0 if mitad_sup.size else 0.45
            apertura_ojos = float(np.clip(contraste_ocular, 0.20, 0.85))

        # 3. Tensión interciliar (glabela / ceño fruncido mediante gradiente vertical Sobel X)
        glabela = roi_gris[int(h * 0.18) : int(h * 0.36), int(w * 0.35) : int(w * 0.65)]
        if glabela.size > 0:
            sobel_x = cv2.Sobel(glabela, cv2.CV_64F, 1, 0, ksize=3)
            energia_pliegues = float(np.mean(np.abs(sobel_x))) / 55.0
            tension_cejas = float(np.clip(energia_pliegues, 0.0, 1.0))
        else:
            tension_cejas = 0.25

        # 4. Región bucal (sonrisa vs comisuras caídas y apertura bucal)
        mitad_inf = roi_gris[int(h * 0.58) : int(h * 0.94), int(w * 0.18) : int(w * 0.82)]
        sonrisas = []
        if self._smile_cascade is not None and mitad_inf.size > 0:
            sonrisas = self._smile_cascade.detectMultiScale(
                mitad_inf, scaleFactor=1.5, minNeighbors=12, minSize=(int(w * 0.25), int(h * 0.10))
            )

        # Análisis geométrico de perfil de oscuridad labial (comisuras izq/der vs centro)
        curvatura_geom = 0.0
        apertura_boca = 0.15
        if mitad_inf.size > 8:
            bh, bw = mitad_inf.shape
            col_izq = mitad_inf[:, : max(1, bw // 4)]
            col_centro = mitad_inf[:, bw // 3 : max(bw // 3 + 1, (2 * bw) // 3)]
            col_der = mitad_inf[:, max(0, (3 * bw) // 4) :]

            y_izq = float(np.argmin(np.mean(col_izq, axis=1))) / max(1, bh)
            y_centro = float(np.argmin(np.mean(col_centro, axis=1))) / max(1, bh)
            y_der = float(np.argmin(np.mean(col_der, axis=1))) / max(1, bh)
            # Si las comisuras (izq/der) están más arriba (menor y) que el centro -> sonrisa (+)
            # Si las comisuras están más abajo (mayor y) que el centro -> tristeza (-)
            curvatura_geom = float(np.clip((y_centro - 0.5 * (y_izq + y_der)) * 3.2, -0.9, 0.9))

            oscuridad_centro = 1.0 - (float(np.percentile(col_centro, 15)) / 255.0)
            apertura_boca = float(np.clip((oscuridad_centro - 0.45) * 2.0, 0.05, 1.0))

        if len(sonrisas) > 0:
            curvatura_boca = float(np.clip(max(0.55, curvatura_geom + 0.45), -1.0, 1.0))
        else:
            curvatura_boca = curvatura_geom

        metricas = self.clasificar_desde_rasgos(
            apertura_ojos=apertura_ojos,
            tension_cejas=tension_cejas,
            curvatura_boca=curvatura_boca,
            apertura_boca=apertura_boca,
            inclinacion_cabeza_deg=inclinacion_deg,
            agitacion_movimiento=agitacion,
        )

        if dibujar_hud:
            color = (255, 200, 60)
            cv2.rectangle(salida, (x, y), (x + w, y + h), color, 2)
            etiqueta = (
                f"{metricas.emocion_facial} "
                f"(V:{metricas.valencia_facial:+.2f} A:{metricas.arousal_facial:+.2f})"
            )
            cv2.putText(
                salida, etiqueta, (x, max(22, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2
            )

        return metricas, salida

    @staticmethod
    def clasificar_desde_rasgos(
        apertura_ojos: float,
        tension_cejas: float,
        curvatura_boca: float,
        apertura_boca: float = 0.15,
        inclinacion_cabeza_deg: float = 0.0,
        agitacion_movimiento: float = 0.0,
    ) -> MetricasFaciales:
        """Mapea unidades de acción facial (FACS) al espacio Valencia-Arousal."""
        valencia = float(
            np.clip(
                0.75 * curvatura_boca
                - 0.45 * max(0.0, tension_cejas - 0.35)
                - 0.20 * max(0.0, 0.35 - apertura_ojos),
                -1.0,
                1.0,
            )
        )
        arousal = float(
            np.clip(
                0.55 * (apertura_ojos - 0.45) * 2.0
                + 0.45 * (tension_cejas - 0.30) * 1.8
                + 0.35 * apertura_boca
                + 0.40 * agitacion_movimiento
                - 0.25 * (abs(inclinacion_cabeza_deg) / 25.0),
                -1.0,
                1.0,
            )
        )

        if curvatura_boca >= 0.35 and valencia >= 0.25:
            emocion = "MOTIVACION_ALEGRIA"
        elif tension_cejas >= 0.62 and curvatura_boca <= 0.05 and arousal >= 0.20:
            emocion = "ENOJO_FRUSTRACION"
        elif apertura_ojos >= 0.68 and arousal >= 0.30 and valencia <= 0.05:
            emocion = "ANSIEDAD_ESTRES"
        elif curvatura_boca <= -0.22 and arousal <= 0.05:
            emocion = "TRISTEZA_DESANIMO"
        elif abs(inclinacion_cabeza_deg) >= 8.0 or (0.38 <= tension_cejas < 0.62 and abs(valencia) < 0.25):
            emocion = "DUDA_INSEGURIDAD"
        else:
            emocion = "NEUTRO"

        confianza = float(np.clip(0.55 + 0.35 * max(abs(valencia), abs(arousal)), 0.50, 0.95))
        return MetricasFaciales(
            rostro_detectado=True,
            apertura_ojos=round(apertura_ojos, 3),
            tension_cejas=round(tension_cejas, 3),
            curvatura_boca=round(curvatura_boca, 3),
            apertura_boca=round(apertura_boca, 3),
            inclinacion_cabeza_deg=round(inclinacion_cabeza_deg, 2),
            agitacion_movimiento=round(agitacion_movimiento, 3),
            emocion_facial=emocion,
            valencia_facial=round(valencia, 3),
            arousal_facial=round(arousal, 3),
            confianza=round(confianza, 3),
        )

    def capturar_rafaga(self, num_frames: int = 5) -> MetricasFaciales:
        """Captura una ráfaga rápida de la cámara y promedia las métricas faciales."""
        if not self.abrir_camara():
            return MetricasFaciales(rostro_detectado=False)

        lecturas: list[MetricasFaciales] = []
        for _ in range(max(1, num_frames)):
            ok, frame = self._cap.read()
            if ok and frame is not None:
                m, _ = self.analizar_frame(frame, dibujar_hud=False)
                if m.rostro_detectado:
                    lecturas.append(m)

        if not lecturas:
            return MetricasFaciales(rostro_detectado=False)

        return AnalizadorFacial.clasificar_desde_rasgos(
            apertura_ojos=float(np.mean([x.apertura_ojos for x in lecturas])),
            tension_cejas=float(np.mean([x.tension_cejas for x in lecturas])),
            curvatura_boca=float(np.mean([x.curvatura_boca for x in lecturas])),
            apertura_boca=float(np.mean([x.apertura_boca for x in lecturas])),
            inclinacion_cabeza_deg=float(np.mean([x.inclinacion_cabeza_deg for x in lecturas])),
            agitacion_movimiento=float(np.mean([x.agitacion_movimiento for x in lecturas])),
        )


# =====================================================================
#  2. ANALIZADOR ACÚSTICO DE VOZ (PROSODIA Y DSP CON NUMPY)
# =====================================================================

class AnalizadorAcusticoVoz:
    """Extrae Tono (F0 Hz), Volumen (dBFS), Rapidez (WPM) y Pausas de la voz."""

    def analizar_pcm(
        self,
        muestras: np.ndarray | bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        texto_transcrito: str = "",
    ) -> MetricasAcusticasVoz:
        """Procesa audio crudo PCM mono y devuelve métricas prosódicas completas."""
        if isinstance(muestras, (bytes, bytearray)):
            if len(muestras) == 0:
                return MetricasAcusticasVoz(audio_analizado=False)
            if sample_width == 2:
                arr = np.frombuffer(muestras, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 4:
                arr = np.frombuffer(muestras, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                arr = (np.frombuffer(muestras, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        else:
            arr = np.asarray(muestras, dtype=np.float32).flatten()

        if arr.size < sample_rate * 0.15:
            return MetricasAcusticasVoz(audio_analizado=False)

        # Remover offset DC
        arr = arr - float(np.mean(arr))

        # Ventaneo cada 30 ms con solapamiento de 15 ms
        win = max(64, int(sample_rate * 0.030))
        hop = max(32, int(sample_rate * 0.015))
        n_frames = max(1, 1 + (len(arr) - win) // hop)

        energias_rms = []
        tonos_f0 = []

        lag_min = max(2, int(sample_rate / 400.0))  # 400 Hz máx voz humana
        lag_max = max(lag_min + 2, int(sample_rate / 75.0))  # 75 Hz mín voz humana

        for i in range(n_frames):
            seg = arr[i * hop : i * hop + win]
            if len(seg) < win:
                break
            rms = float(np.sqrt(np.mean(seg * seg) + 1e-12))
            energias_rms.append(rms)

            # Estimar F0 por autocorrelación solo en segmentos sonoros
            if rms > 0.015 and len(seg) > lag_max:
                seg_w = seg * np.hanning(len(seg))
                corr = np.correlate(seg_w, seg_w, mode="full")[len(seg_w) - 1 :]
                if corr[0] > 1e-9:
                    corr_norm = corr / corr[0]
                    sub = corr_norm[lag_min : min(lag_max, len(corr_norm))]
                    if sub.size > 0:
                        idx_pico = int(np.argmax(sub))
                        val_pico = float(sub[idx_pico])
                        if val_pico >= 0.32:
                            f0 = sample_rate / float(lag_min + idx_pico)
                            if 75.0 <= f0 <= 400.0:
                                tonos_f0.append(f0)

        if not energias_rms:
            return MetricasAcusticasVoz(audio_analizado=False)

        rms_arr = np.array(energias_rms, dtype=np.float32)
        piso_ruido = float(np.percentile(rms_arr, 15))
        umbral_vad = max(0.012, piso_ruido * 2.2)
        activos = rms_arr >= umbral_vad

        # Volumen en dBFS sobre los cuadros con voz activa
        rms_voz = float(np.mean(rms_arr[activos])) if np.any(activos) else float(np.mean(rms_arr))
        volumen_db = float(np.clip(20.0 * math.log10(max(rms_voz, 1e-4)), -55.0, 0.0))

        # Ratio de pausas internas
        indices_activos = np.where(activos)[0]
        if indices_activos.size >= 2:
            tramo_habla = activos[indices_activos[0] : indices_activos[-1] + 1]
            ratio_pausas = float(1.0 - np.mean(tramo_habla))
            duracion_locucion_s = len(tramo_habla) * (hop / float(sample_rate))
        else:
            ratio_pausas = 0.5
            duracion_locucion_s = len(arr) / float(sample_rate)

        # Tonalidad fundamental F0 y su variabilidad
        if tonos_f0:
            tono_f0_hz = float(np.median(tonos_f0))
            variabilidad_tono_hz = float(np.std(tonos_f0))
        else:
            tono_f0_hz = 155.0
            variabilidad_tono_hz = 15.0

        # Ataque de energía (derivada positiva de envolvente RMS)
        diffs_pos = np.maximum(0.0, np.diff(rms_arr))
        ataque_energia = float(np.clip(np.percentile(diffs_pos, 90) * 8.5, 0.0, 1.0)) if diffs_pos.size else 0.25

        # Rapidez de habla (WPM): usa palabras transcritas o picos silábicos de energía
        palabras = re.findall(r"\w+", texto_transcrito)
        if len(palabras) >= 2 and duracion_locucion_s > 0.25:
            rapidez_wpm = float(np.clip((len(palabras) / duracion_locucion_s) * 60.0, 60.0, 260.0))
        else:
            # Estimación acústica de sílabas/s cuando aún no hay texto
            umbral_silaba = float(np.mean(rms_arr)) * 1.15
            cruces = np.sum((rms_arr[:-1] < umbral_silaba) & (rms_arr[1:] >= umbral_silaba))
            silabas_por_seg = cruces / max(0.3, duracion_locucion_s)
            # En español ~2.1 sílabas promedio por palabra
            rapidez_wpm = float(np.clip((silabas_por_seg / 2.1) * 60.0, 70.0, 250.0))

        return self.clasificar_desde_prosodia(
            tono_f0_hz=tono_f0_hz,
            variabilidad_tono_hz=variabilidad_tono_hz,
            volumen_db=volumen_db,
            rapidez_wpm=rapidez_wpm,
            ratio_pausas=ratio_pausas,
            ataque_energia=ataque_energia,
        )

    @staticmethod
    def clasificar_desde_prosodia(
        tono_f0_hz: float,
        variabilidad_tono_hz: float,
        volumen_db: float,
        rapidez_wpm: float,
        ratio_pausas: float = 0.20,
        ataque_energia: float = 0.30,
    ) -> MetricasAcusticasVoz:
        """Proyecta los parámetros acústicos de voz en Valencia y Arousal."""
        # Normalizaciones respecto a voz conversacional neutra (~155 Hz, -20 dB, 145 WPM)
        norm_vel = (rapidez_wpm - 145.0) / 55.0
        norm_vol = (volumen_db - (-20.0)) / 10.0
        norm_f0 = (tono_f0_hz - 160.0) / 65.0

        arousal = float(
            np.clip(
                0.42 * norm_vel
                + 0.35 * norm_vol
                + 0.23 * norm_f0
                + 0.20 * (ataque_energia - 0.30)
                - 0.30 * (ratio_pausas - 0.22),
                -1.0,
                1.0,
            )
        )

        # Voz muy fuerte y brusca -> ira (valencia negativa); voz muy apagada y lenta -> tristeza (valencia negativa)
        # Voz fluida, entonada (variabilidad moderada-alta) y energía moderada -> motivación/alegría
        if volumen_db >= -12.5 and ataque_energia >= 0.45:
            valencia = -0.65
            emocion = "ENOJO_FRUSTRACION"
        elif rapidez_wpm >= 175.0 and tono_f0_hz >= 195.0 and variabilidad_tono_hz >= 22.0:
            valencia = -0.55
            emocion = "ANSIEDAD_ESTRES"
        elif volumen_db <= -26.0 and rapidez_wpm <= 115.0:
            valencia = -0.60
            emocion = "TRISTEZA_DESANIMO"
        elif ratio_pausas >= 0.38 and 110.0 < rapidez_wpm < 155.0:
            valencia = -0.20
            emocion = "DUDA_INSEGURIDAD"
        elif 155.0 <= rapidez_wpm <= 190.0 and -19.0 <= volumen_db <= -12.5 and 18.0 <= variabilidad_tono_hz <= 45.0:
            valencia = +0.55
            emocion = "MOTIVACION_ALEGRIA"
        else:
            valencia = 0.0
            emocion = "NEUTRO"

        confianza = float(np.clip(0.55 + 0.35 * max(abs(arousal), abs(valencia)), 0.50, 0.92))
        return MetricasAcusticasVoz(
            audio_analizado=True,
            tono_f0_hz=round(tono_f0_hz, 1),
            variabilidad_tono_hz=round(variabilidad_tono_hz, 1),
            volumen_db=round(volumen_db, 1),
            rapidez_wpm=round(rapidez_wpm, 1),
            ratio_pausas=round(ratio_pausas, 3),
            ataque_energia=round(ataque_energia, 3),
            emocion_vocal=emocion,
            valencia_vocal=round(valencia, 3),
            arousal_vocal=round(arousal, 3),
            confianza=round(confianza, 3),
        )


# =====================================================================
#  3. ANALIZADOR LÉXICO Y PSICOLINGÜÍSTICO (ESPAÑOL RIOPLATENSE)
# =====================================================================

class AnalizadorLexicoAfectivo:
    """Evalúa el contenido verbal y marcadores paralingüísticos del texto."""

    PATRONES_CRISIS = re.compile(
        r"\b(no quiero vivir|quitarme la vida|suicid\w*|autolesion\w*|lastimarme|"
        r"hacerme dano|matarme|morirme ya)\b"
    )

    LEXICO_EMOCIONAL: dict[str, tuple[float, float, list[str]]] = {
        # Emoción: (valencia_base, arousal_base, patrones_regex)
        "ANSIEDAD_ESTRES": (
            -0.65,
            +0.82,
            [
                r"\bansiedad\b", r"\bansios[oa]\b", r"\bestres\w*\b", r"\bcolaps\w*\b",
                r"\bno llego\b", r"\bpanico\b", r"\babrumad[oa]\b", r"\bdesbordad[oa]\b",
                r"\bnervios[oa]?\b", r"\btaquicardia\b", r"\bno puedo respirar\b",
                r"\bme falta el aire\b", r"\bmil cosas\b", r"\bsobrepasad[oa]\b",
                r"\bangustia\w*\b", r"\bpresion\b", r"\bbloquead[oa] por el examen\b",
            ],
        ),
        "TRISTEZA_DESANIMO": (
            -0.78,
            -0.65,
            [
                r"\btriste\w*\b", r"\bdeprimid[oa]\b", r"\bbajon\w*\b", r"\bllor\w*\b",
                r"\bfracas\w*\b", r"\babandonar\b", r"\brendirme\b", r"\bsol[oa] me siento\b",
                r"\bme siento sol[oa]\b", r"\bagotad[oa]\b", r"\bsin fuerzas\b",
                r"\bsin ganas\b", r"\bme salio todo mal\b", r"\bno sirvo\b",
                r"\bdesanimad[oa]\b", r"\bvacio\b", r"\bcansad[oa] de todo\b",
                r"\bfrustrad[oa] y cansad[oa]\b", r"\bdecepcion\w*\b",
            ],
        ),
        "ENOJO_FRUSTRACION": (
            -0.72,
            +0.78,
            [
                r"\benojad[oa]\b", r"\bbronca\b", r"\bhart[oa]\b", r"\bfurios[oa]\b",
                r"\bodio\b", r"\bpudri\w*\b", r"\bpodrid[oa]\b", r"\binsoportable\b",
                r"\binjusto\b", r"\bme da rabia\b", r"\birritad[oa]\b",
                r"\bimposible trabajar asi\b", r"\bnada funciona\b", r"\bme saca\b",
                r"\bre caliente\b", r"\bimpotencia\b",
            ],
        ),
        "DUDA_INSEGURIDAD": (
            -0.28,
            +0.12,
            [
                r"\bno se que hacer\b", r"\bindecis[oa]\b", r"\bduda\w*\b",
                r"\binsegur[oa]\b", r"\bmiedo a equivocarme\b", r"\bmiedo a fallar\b",
                r"\bconfundid[oa]\b", r"\bperdid[oa]\b", r"\bno me animo\b",
                r"\bque decision tomar\b", r"\bno se si elegir\b", r"\bme cuesta decidir\b",
                r"\bsindrome del impostor\b", r"\bnecesito un consejo\b",
            ],
        ),
        "MOTIVACION_ALEGRIA": (
            +0.80,
            +0.62,
            [
                r"\baprobe\b", r"\bfeliz\b", r"\bcontent[oa]\b", r"\balo?gre\b",
                r"\blo logre\b", r"\bme salio bien\b", r"\borgullos[oa]\b",
                r"\bmotivad[oa]\b", r"\bentusiasmad[oa]\b", r"\bgenial me fue\b",
                r"\bme fue increible\b", r"\bpude resolverlo\b", r"\bre bien\b",
            ],
        ),
    }

    FRASES_ENMASCARAMIENTO = re.compile(
        r"\b(estoy bien|todo bien|no pasa nada|tranqui|normal|nada grave)\b"
    )

    def analizar(self, texto: str) -> ResultadoLexico:
        texto_norm = normalizar_texto(texto).strip()
        if not texto_norm:
            return ResultadoLexico()

        if self.PATRONES_CRISIS.search(texto_norm):
            return ResultadoLexico(
                emocion_lexica="CRISIS_RIESGO",
                valencia_lexica=-1.0,
                arousal_lexico=+0.9,
                intensidad_lexica=1.0,
                es_crisis_etica=True,
                palabras_clave=["alerta_crisis"],
                es_expresion_emocional=True,
            )

        puntajes: dict[str, int] = {}
        halladas: list[str] = []

        for emocion, (_, _, patrones) in self.LEXICO_EMOCIONAL.items():
            cuenta = 0
            for pat in patrones:
                m = re.search(pat, texto_norm)
                if m:
                    cuenta += 1
                    halladas.append(m.group(0))
            if cuenta > 0:
                puntajes[emocion] = cuenta

        # Marcadores paralingüísticos escritos (!, MAYÚSCULAS, ...)
        exclamaciones = texto.count("!")
        puntos_susp = texto.count("...")
        letras = [c for c in texto if c.isalpha()]
        ratio_mayus = (
            sum(1 for c in letras if c.isupper()) / len(letras)
            if len(letras) >= 6
            else 0.0
        )

        if not puntajes:
            return ResultadoLexico(
                emocion_lexica="NEUTRO",
                valencia_lexica=0.08 if self.FRASES_ENMASCARAMIENTO.search(texto_norm) else 0.0,
                arousal_lexico=float(np.clip(0.20 * exclamaciones - 0.15 * puntos_susp, -0.4, 0.5)),
                intensidad_lexica=0.15,
                es_crisis_etica=False,
                palabras_clave=[],
                es_expresion_emocional=False,
            )

        emocion_ganadora = max(puntajes, key=puntajes.get)
        val_base, aro_base, _ = self.LEXICO_EMOCIONAL[emocion_ganadora]

        boost_arousal = min(0.25, 0.08 * exclamaciones + (0.15 if ratio_mayus > 0.5 else 0.0))
        freno_arousal = min(0.20, 0.10 * puntos_susp)
        intensidad = float(np.clip(0.55 + 0.18 * puntajes[emocion_ganadora] + boost_arousal, 0.45, 1.0))

        return ResultadoLexico(
            emocion_lexica=emocion_ganadora,
            valencia_lexica=round(float(np.clip(val_base * intensidad / 0.75, -1.0, 1.0)), 3),
            arousal_lexico=round(float(np.clip(aro_base + boost_arousal - freno_arousal, -1.0, 1.0)), 3),
            intensidad_lexica=round(intensidad, 3),
            es_crisis_etica=False,
            palabras_clave=halladas[:5],
            es_expresion_emocional=True,
        )


# =====================================================================
#  4. FUSIONADOR MULTIMODAL Y DETECTOR DE INCONGRUENCIA AFECTIVA
# =====================================================================

@dataclass
class ConfiguracionPesosFusion:
    """Cromosoma de pesos y umbrales del FusionadorMultimodal (optimizable por AG)."""
    # Pesos con 3 canales activos (se normalizan a suma 1)
    w3_lexico: float = 0.42
    w3_voz: float = 0.30
    w3_cara: float = 0.28
    # Pesos con 2 canales activos (léxico + voz / léxico + cara)
    w2v_lexico: float = 0.55
    w2c_lexico: float = 0.58
    # Pesos en régimen de Incongruencia / Enmascaramiento Afectivo (3 canales)
    inc_lexico: float = 0.12
    inc_voz: float = 0.46
    inc_cara: float = 0.42
    # Umbrales biométricos de detección de enmascaramiento no verbal
    umbral_cara_neg: float = -0.22
    umbral_voz_neg: float = -0.32
    umbral_voz_arousal: float = 0.46

    def normalizado(self) -> "ConfiguracionPesosFusion":
        s3 = max(1e-6, self.w3_lexico + self.w3_voz + self.w3_cara)
        si = max(1e-6, self.inc_lexico + self.inc_voz + self.inc_cara)
        return ConfiguracionPesosFusion(
            w3_lexico=round(float(np.clip(self.w3_lexico / s3, 0.02, 0.96)), 4),
            w3_voz=round(float(np.clip(self.w3_voz / s3, 0.02, 0.96)), 4),
            w3_cara=round(float(np.clip(self.w3_cara / s3, 0.02, 0.96)), 4),
            w2v_lexico=round(float(np.clip(self.w2v_lexico, 0.05, 0.95)), 4),
            w2c_lexico=round(float(np.clip(self.w2c_lexico, 0.05, 0.95)), 4),
            inc_lexico=round(float(np.clip(self.inc_lexico / si, 0.0, 0.80)), 4),
            inc_voz=round(float(np.clip(self.inc_voz / si, 0.05, 0.95)), 4),
            inc_cara=round(float(np.clip(self.inc_cara / si, 0.05, 0.95)), 4),
            umbral_cara_neg=round(float(np.clip(self.umbral_cara_neg, -0.75, -0.08)), 4),
            umbral_voz_neg=round(float(np.clip(self.umbral_voz_neg, -0.75, -0.08)), 4),
            umbral_voz_arousal=round(float(np.clip(self.umbral_voz_arousal, 0.20, 0.85)), 4),
        )


class FusionadorMultimodal:
    """Integra Cara + Voz + Léxico en un EstadoAfectivoUsuario unificado."""

    def __init__(
        self,
        config_pesos: Optional[ConfiguracionPesosFusion] = None,
        cargar_ga: bool = True,
    ):
        self.lexico = AnalizadorLexicoAfectivo()
        if config_pesos is not None:
            self.config = config_pesos.normalizado()
        elif cargar_ga:
            self.config = self._cargar_pesos_ga_o_default()
        else:
            self.config = ConfiguracionPesosFusion().normalizado()

    @staticmethod
    def _cargar_pesos_ga_o_default() -> ConfiguracionPesosFusion:
        import json
        from pathlib import Path

        ruta = Path(__file__).resolve().parent / "pesos_fusion_ga.json"
        if ruta.exists():
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
                campos = datos.get("pesos_optimizados", datos)
                filtrados = {
                    k: float(v)
                    for k, v in campos.items()
                    if k in ConfiguracionPesosFusion.__dataclass_fields__
                }
                if filtrados:
                    return ConfiguracionPesosFusion(**filtrados).normalizado()
            except Exception:
                pass
        return ConfiguracionPesosFusion().normalizado()

    def fusionar(
        self,
        texto: str,
        facial: Optional[MetricasFaciales] = None,
        acustica: Optional[MetricasAcusticasVoz] = None,
    ) -> EstadoAfectivoUsuario:
        res_lex = self.lexico.analizar(texto)
        fac = facial or MetricasFaciales(rostro_detectado=False)
        acu = acustica or MetricasAcusticasVoz(audio_analizado=False)
        cfg = self.config

        if res_lex.es_crisis_etica:
            return EstadoAfectivoUsuario(
                emocion_dominante="CRISIS_RIESGO",
                valencia=-1.0,
                arousal=+0.9,
                intensidad=1.0,
                confianza=0.99,
                es_crisis_etica=True,
                canales_activos=["lexico"],
                facial=fac,
                acustica=acu,
                lexico=res_lex,
            )

        # Ponderación dinámica según sensores activos
        pesos = {"lexico": 1.0, "voz": 0.0, "cara": 0.0}
        canales = ["lexico"]

        if acu.audio_analizado and fac.rostro_detectado:
            s3 = max(1e-6, cfg.w3_lexico + cfg.w3_voz + cfg.w3_cara)
            pesos = {
                "lexico": cfg.w3_lexico / s3,
                "voz": cfg.w3_voz / s3,
                "cara": cfg.w3_cara / s3,
            }
            canales = ["lexico", "voz", "cara"]
        elif acu.audio_analizado:
            pesos = {"lexico": cfg.w2v_lexico, "voz": 1.0 - cfg.w2v_lexico, "cara": 0.0}
            canales = ["lexico", "voz"]
        elif fac.rostro_detectado:
            pesos = {"lexico": cfg.w2c_lexico, "voz": 0.0, "cara": 1.0 - cfg.w2c_lexico}
            canales = ["lexico", "cara"]

        # Detección de Incongruencia Emocional ("Enmascaramiento")
        # Ejemplo: dice "estoy bien / no pasa nada" pero la cara o la voz muestran malestar claro.
        incongruencia = False
        detalle_inc = ""
        señales_no_verbales_neg = []
        if fac.rostro_detectado and fac.valencia_facial <= cfg.umbral_cara_neg:
            señales_no_verbales_neg.append(f"rostro ({fac.emocion_facial.lower()})")
        if acu.audio_analizado and (
            acu.valencia_vocal <= cfg.umbral_voz_neg
            or abs(acu.arousal_vocal) >= cfg.umbral_voz_arousal
        ):
            señales_no_verbales_neg.append(
                f"voz ({acu.rapidez_wpm:.0f} ppm, {acu.volumen_db:.1f} dB, {acu.tono_f0_hz:.0f} Hz)"
            )

        if res_lex.valencia_lexica >= -0.05 and señales_no_verbales_neg:
            # Si las palabras son neutras/positivas pero el cuerpo/voz transmite malestar,
            # aplicamos el vector de pesos de incongruencia (optimizado por Algoritmo Genético).
            incongruencia = True
            detalle_inc = (
                "Tus palabras suenan tranquilas, pero percibo tensión o desánimo en tu "
                + " y ".join(señales_no_verbales_neg)
            )
            if fac.rostro_detectado and acu.audio_analizado:
                si = max(1e-6, cfg.inc_lexico + cfg.inc_voz + cfg.inc_cara)
                pesos = {
                    "lexico": cfg.inc_lexico / si,
                    "voz": cfg.inc_voz / si,
                    "cara": cfg.inc_cara / si,
                }
            elif acu.audio_analizado:
                w_lex_2 = min(0.65, cfg.inc_lexico)
                pesos = {"lexico": w_lex_2, "voz": 1.0 - w_lex_2, "cara": 0.0}
            else:
                w_lex_2 = min(0.65, cfg.inc_lexico)
                pesos = {"lexico": w_lex_2, "voz": 0.0, "cara": 1.0 - w_lex_2}

        valencia = (
            pesos["lexico"] * res_lex.valencia_lexica
            + pesos["voz"] * acu.valencia_vocal
            + pesos["cara"] * fac.valencia_facial
        )
        arousal = (
            pesos["lexico"] * res_lex.arousal_lexico
            + pesos["voz"] * acu.arousal_vocal
            + pesos["cara"] * fac.arousal_facial
        )

        valencia = float(np.clip(valencia, -1.0, 1.0))
        arousal = float(np.clip(arousal, -1.0, 1.0))
        intensidad = float(np.clip(math.hypot(valencia, arousal) / math.sqrt(2.0), 0.15, 1.0))

        # Determinación de la emoción dominante fusionada
        emocion = self._resolver_emocion_circumpleja(
            valencia, arousal, res_lex, fac, acu, incongruencia, pesos
        )

        confianza = float(
            np.clip(
                0.60 + 0.12 * (len(canales) - 1) + 0.20 * intensidad,
                0.55,
                0.98,
            )
        )

        return EstadoAfectivoUsuario(
            emocion_dominante=emocion,
            valencia=round(valencia, 3),
            arousal=round(arousal, 3),
            intensidad=round(intensidad, 3),
            confianza=round(confianza, 3),
            es_crisis_etica=False,
            incongruencia_detectada=incongruencia,
            detalle_incongruencia=detalle_inc,
            canales_activos=canales,
            facial=fac,
            acustica=acu,
            lexico=res_lex,
        )

    @staticmethod
    def _resolver_emocion_circumpleja(
        valencia: float,
        arousal: float,
        lex: ResultadoLexico,
        fac: MetricasFaciales,
        acu: MetricasAcusticasVoz,
        incongruencia: bool,
        pesos: Optional[dict[str, float]] = None,
    ) -> str:
        pesos = pesos or {"lexico": 0.42, "voz": 0.30, "cara": 0.28}

        # Modo solo texto (sin sensores biométricos conectados)
        if not fac.rostro_detectado and not acu.audio_analizado:
            return lex.emocion_lexica if lex.es_expresion_emocional else "NEUTRO"

        radio = math.hypot(valencia, arousal)
        if radio < 0.20 and not lex.es_expresion_emocional:
            return "NEUTRO"

        # Cuadrantes continuos del Modelo Circumplejo de Russell ponderados por canales
        if valencia >= 0.22 and arousal >= 0.08:
            return "MOTIVACION_ALEGRIA"

        if valencia <= -0.18 and arousal >= 0.22:
            evidencia_ira = (
                (pesos["lexico"] if lex.emocion_lexica == "ENOJO_FRUSTRACION" else 0.0)
                + (
                    pesos["voz"]
                    if (acu.audio_analizado and (acu.volumen_db > -13.5 or acu.emocion_vocal == "ENOJO_FRUSTRACION"))
                    else 0.0
                )
                + (
                    pesos["cara"]
                    if (fac.rostro_detectado and (fac.tension_cejas > 0.60 or fac.emocion_facial == "ENOJO_FRUSTRACION"))
                    else 0.0
                )
            )
            if evidencia_ira >= 0.40:
                return "ENOJO_FRUSTRACION"
            return "ANSIEDAD_ESTRES"

        if valencia <= -0.20 and arousal <= -0.06:
            return "TRISTEZA_DESANIMO"

        if -0.45 <= valencia < 0.16 and -0.18 < arousal < 0.28:
            if lex.emocion_lexica == "TRISTEZA_DESANIMO" and arousal < 0.0:
                return "TRISTEZA_DESANIMO"
            evidencia_duda = (
                (pesos["lexico"] if lex.emocion_lexica == "DUDA_INSEGURIDAD" else 0.0)
                + (pesos["voz"] if (acu.audio_analizado and acu.emocion_vocal == "DUDA_INSEGURIDAD") else 0.0)
                + (pesos["cara"] if (fac.rostro_detectado and fac.emocion_facial == "DUDA_INSEGURIDAD") else 0.0)
            )
            if evidencia_duda >= 0.30 or (lex.emocion_lexica == "DUDA_INSEGURIDAD" and not incongruencia):
                return "DUDA_INSEGURIDAD"
            if incongruencia and valencia <= -0.18:
                return "TRISTEZA_DESANIMO"

        if lex.es_expresion_emocional and not incongruencia and radio >= 0.18:
            return lex.emocion_lexica

        return "NEUTRO"
